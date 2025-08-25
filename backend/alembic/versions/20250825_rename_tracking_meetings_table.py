"""Rename tracking meetings table to mt_meetings and update FKs.

Revision ID: 20250825_rename_tracking_meetings_table
Revises: 20250825_remove_cross_registry_coach_fks
Create Date: 2025-08-25
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '20250825_rename_tracking_meetings_table'
down_revision = '20250825_remove_cross_registry_coach_fks'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())
    # Only attempt rename if mt_meetings does not already exist
    if 'meetings' in tables and 'mt_meetings' not in tables:
        cols = {c['name']: c for c in inspector.get_columns('meetings')}
        # Treat as tracking table if it has external_refs JSON column (legacy meetings lacks it)
        has_external_refs = 'external_refs' in cols
        # And id is UUID
        id_is_uuid = 'id' in cols and 'uuid' in str(cols['id']['type']).lower()
        if has_external_refs and id_is_uuid:
            op.rename_table('meetings', 'mt_meetings')
    # Rely on Postgres to auto-update dependent FK constraints on table rename; no manual FK work.


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())
    if 'mt_meetings' in tables and 'meetings' not in tables:
        op.rename_table('mt_meetings', 'meetings')
