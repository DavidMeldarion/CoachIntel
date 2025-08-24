"""add index on meetings (external_refs->>'zoom_meeting_uuid')

Revision ID: 20250824_add_zoom_meeting_uuid_index
Revises: 20250824_add_meeting_attendee_timing_index
Create Date: 2025-08-24
"""
from __future__ import annotations

from alembic import op

revision = '20250824_add_zoom_meeting_uuid_index'
down_revision = '20250824_add_meeting_attendee_timing_index'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Postgres expression index with partial filter to limit to rows having key
    op.execute("CREATE INDEX IF NOT EXISTS ix_meetings_zoom_meeting_uuid ON meetings ((external_refs ->> 'zoom_meeting_uuid')) WHERE external_refs ? 'zoom_meeting_uuid'")

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_meetings_zoom_meeting_uuid")
