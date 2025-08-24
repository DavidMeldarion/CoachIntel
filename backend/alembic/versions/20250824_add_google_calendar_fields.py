"""add google calendar watch & sync fields

Revision ID: 20250824_add_google_calendar_fields
Revises: 20250824_add_client_status_audits
Create Date: 2025-08-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '20250824_add_google_calendar_fields'
down_revision = '20250824_add_client_status_audits'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('external_accounts') as batch:
        batch.add_column(sa.Column('calendar_sync_token', sa.String(), nullable=True))
        batch.add_column(sa.Column('calendar_page_token', sa.String(), nullable=True))
        batch.add_column(sa.Column('calendar_channel_id', sa.String(), nullable=True))
        batch.add_column(sa.Column('calendar_resource_id', sa.String(), nullable=True))
        batch.add_column(sa.Column('calendar_channel_expires', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_external_accounts_calendar_channel_id', 'external_accounts', ['calendar_channel_id'])
    op.create_index('ix_external_accounts_calendar_resource_id', 'external_accounts', ['calendar_resource_id'])


def downgrade() -> None:
    op.drop_index('ix_external_accounts_calendar_channel_id', table_name='external_accounts')
    op.drop_index('ix_external_accounts_calendar_resource_id', table_name='external_accounts')
    with op.batch_alter_table('external_accounts') as batch:
        batch.drop_column('calendar_sync_token')
        batch.drop_column('calendar_page_token')
        batch.drop_column('calendar_channel_id')
        batch.drop_column('calendar_resource_id')
        batch.drop_column('calendar_channel_expires')
