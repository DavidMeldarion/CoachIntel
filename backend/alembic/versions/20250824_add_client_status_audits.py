"""add client_status_audits table

Revision ID: 20250824_add_client_status_audits
Revises: 20250823_update_review_candidate_model
Create Date: 2025-08-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

# revision identifiers, used by Alembic.
revision = '20250824_add_client_status_audits'
down_revision = '20250823_update_review_candidate_model'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    # Reuse existing enum type (created in earlier migration) without attempting to recreate
    client_status_enum = PGEnum('prospect','active','inactive', name='client_status', create_type=False)
    if 'client_status_audits' not in inspector.get_table_names():
        op.create_table(
            'client_status_audits',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('old_status', sa.String(), nullable=True),
            sa.Column('new_status', client_status_enum, nullable=False),
            sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('reason', sa.String(), nullable=True),
        )
    # index (client_id, changed_at)
    existing_indexes = {ix['name'] for ix in inspector.get_indexes('client_status_audits')} if 'client_status_audits' in inspector.get_table_names() else set()
    if 'ix_client_status_audits_client_changed' not in existing_indexes:
        op.create_index('ix_client_status_audits_client_changed', 'client_status_audits', ['client_id','changed_at'])

    # Add GIN index on persons.emails if not present (for q search)
    if 'persons' in inspector.get_table_names():
        person_indexes = {ix['name'] for ix in inspector.get_indexes('persons')}
        if 'ix_persons_emails_gin' not in person_indexes:
            op.execute("CREATE INDEX ix_persons_emails_gin ON persons USING GIN (emails)")


def downgrade() -> None:
    op.drop_index('ix_client_status_audits_client_changed', table_name='client_status_audits')
    op.drop_table('client_status_audits')
    # Keep GIN index (optional to drop)
    op.execute("DROP INDEX IF EXISTS ix_persons_emails_gin")
