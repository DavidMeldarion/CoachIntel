"""Merge heads after participants/transcript_url/indexes

Revision ID: 16dd9291704c
Revises: 20250721_merge_heads, 20250724_add_meeting_fields
Create Date: 2025-07-24 17:50:38.435721

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '16dd9291704c'
down_revision = ('20250721_merge_heads', '20250724_add_meeting_fields')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
