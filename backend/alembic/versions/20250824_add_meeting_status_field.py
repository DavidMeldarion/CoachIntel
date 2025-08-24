"""add meeting status field

Revision ID: 20250824_add_meeting_status_field
Revises: 20250824_add_zoom_user_id_to_external_accounts
Create Date: 2025-08-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '20250824_add_meeting_status_field'
down_revision = '20250824_add_zoom_user_id_to_external_accounts'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('meetings') as batch:
        batch.add_column(sa.Column('status', sa.String(), nullable=True))
    op.create_index('ix_meetings_status', 'meetings', ['status'])

def downgrade() -> None:
    op.drop_index('ix_meetings_status', table_name='meetings')
    with op.batch_alter_table('meetings') as batch:
        batch.drop_column('status')
