"""Remove self-clients (coach listed as their own client).

Revision ID: 20250825_remove_self_clients
Revises: 20250825_create_mt_meetings_table
Create Date: 2025-08-25

Logic:
  Delete any clients row where clients.coach_id = users.id and
  the linked person has primary_email equal to users.email (case-insensitive).
  This cleans up earlier ingestion artifacts before resolve_attendee
  was updated to skip creating such client links.

Downgrade is a no-op (data deletion not reversible without snapshot).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '20250825_remove_self_clients'
down_revision = '20250825_create_mt_meetings_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    delete_sql = """
    DELETE FROM clients c
    USING users u, persons p
    WHERE c.coach_id = u.id
      AND p.id = c.person_id
      AND p.primary_email IS NOT NULL
      AND LOWER(p.primary_email) = LOWER(u.email)
    """
    try:
        bind.execute(sa.text(delete_sql))
    except Exception:
        pass


def downgrade() -> None:  # irreversible cleanup
    pass
