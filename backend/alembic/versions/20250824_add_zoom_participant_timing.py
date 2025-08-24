"""add zoom participant timing fields

Revision ID: 20250824_add_zoom_participant_timing
Revises: 20250824_add_google_calendar_fields
Create Date: 2025-08-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '20250824_add_zoom_participant_timing'
down_revision = '20250824_add_google_calendar_fields'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('meeting_attendees') as batch:
        batch.add_column(sa.Column('join_time', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('leave_time', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('duration_seconds', sa.Integer(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('meeting_attendees') as batch:
        batch.drop_column('join_time')
        batch.drop_column('leave_time')
        batch.drop_column('duration_seconds')
