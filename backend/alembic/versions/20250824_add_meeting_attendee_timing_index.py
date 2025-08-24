"""add index on meeting_attendees (meeting_id, source, join_time)

Revision ID: 20250824_add_meeting_attendee_timing_index
Revises: 20250824_add_zoom_participant_timing
Create Date: 2025-08-24
"""
from __future__ import annotations

from alembic import op

revision = '20250824_add_meeting_attendee_timing_index'
down_revision = '20250824_add_zoom_participant_timing'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_index('ix_meeting_attendees_meeting_source_join', 'meeting_attendees', ['meeting_id', 'source', 'join_time'])

def downgrade() -> None:
    op.drop_index('ix_meeting_attendees_meeting_source_join', table_name='meeting_attendees')
