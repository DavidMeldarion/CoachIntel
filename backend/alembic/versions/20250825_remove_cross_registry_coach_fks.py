"""Remove cross-registry ForeignKey constraints from meeting tracking tables.

Revision ID: 20250825_remove_cross_registry_coach_fks
Revises: 20250824_add_meeting_status_field
Create Date: 2025-08-25

Reason:
  Original meeting tracking models referenced users.id via ForeignKey while
  residing in a separate SQLAlchemy DeclarativeBase registry, leading to
  mapper configuration / reflection issues inside Celery tasks where only
  tracking metadata was loaded. We now store coach_id as a plain INT with
  an index and no FK constraint.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250825_remove_cross_registry_coach_fks'
down_revision = '20250824_add_meeting_status_field'
branch_labels = None
depends_on = None

# Table -> list of (constraint_name, local_column)
FK_TARGETS = [
    ('clients', 'coach_id'),
    ('external_accounts', 'coach_id'),
    ('meetings', 'coach_id'),
    ('review_candidates', 'coach_id'),
    ('client_status_audits', 'coach_id'),
]

# We will attempt to drop any FK that points to users.id for these tables.
# Because constraint names follow naming convention fk_<table>_<col>_users or similar,
# we'll inspect existing constraints dynamically for robustness.

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table, col in FK_TARGETS:
        try:
            fks = inspector.get_foreign_keys(table)
        except Exception:
            continue
        for fk in fks:
            if fk.get('referred_table') == 'users' and col in fk.get('constrained_columns', []):
                cname = fk.get('name')
                if cname:
                    try:
                        op.drop_constraint(cname, table_name=table, type_='foreignkey')
                    except Exception:
                        pass
    # (No column type change required; columns remain INTEGER). Just ensure index exists.
    for table, col in FK_TARGETS:
        # Create index if not already there (idempotent guard by naming convention)
        ix_name = f'ix_{table}_{col}_no_fk'
        existing_indexes = {ix['name'] for ix in inspector.get_indexes(table)}
        if ix_name not in existing_indexes:
            try:
                op.create_index(ix_name, table, [col])
            except Exception:
                pass


def downgrade() -> None:
    # Best-effort re-add of the dropped FKs (CASCADE delete) if needed.
    # NOTE: If application has proceeded assuming no FK constraints, re-adding
    # may fail due to orphaned rows; handle with caution.
    for table, col in FK_TARGETS:
        try:
            op.create_foreign_key(
                f'fk_{table}_{col}_users',
                source_table=table,
                referent_table='users',
                local_cols=[col],
                remote_cols=['id'],
                ondelete='CASCADE',
            )
        except Exception:
            pass
    # Drop helper indexes created in upgrade (optional)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table, col in FK_TARGETS:
        ix_name = f'ix_{table}_{col}_no_fk'
        existing_indexes = {ix['name'] for ix in inspector.get_indexes(table)}
        if ix_name in existing_indexes:
            try:
                op.drop_index(ix_name, table_name=table)
            except Exception:
                pass
