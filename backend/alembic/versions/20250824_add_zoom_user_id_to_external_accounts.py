"""add zoom_user_id to external_accounts

Revision ID: 20250824_add_zoom_user_id_to_external_accounts
Revises: 20250824_add_zoom_meeting_uuid_index
Create Date: 2025-08-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '20250824_add_zoom_user_id_to_external_accounts'
down_revision = '20250824_add_zoom_meeting_uuid_index'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('external_accounts') as batch:
        batch.add_column(sa.Column('zoom_user_id', sa.String(), nullable=True))
    op.create_index('ix_external_accounts_zoom_user_id', 'external_accounts', ['zoom_user_id'])

def downgrade() -> None:
    op.drop_index('ix_external_accounts_zoom_user_id', table_name='external_accounts')
    with op.batch_alter_table('external_accounts') as batch:
        batch.drop_column('zoom_user_id')
