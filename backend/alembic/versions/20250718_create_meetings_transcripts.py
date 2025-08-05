"""create meetings and transcripts tables

Revision ID: 20250718meetings
Revises: 3f2e8a9b5c1d
Create Date: 2025-07-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250718meetings'
down_revision = '3f2e8a9b5c1d'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'meetings',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('client_name', sa.String()),
        sa.Column('title', sa.String()),
        sa.Column('date', sa.DateTime()),
        sa.Column('duration', sa.Integer()),
        sa.Column('source', sa.String()),
        sa.Column('transcript_id', sa.String()),
    )
    op.create_table(
        'transcripts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('meeting_id', sa.String(), sa.ForeignKey('meetings.id')),
        sa.Column('full_text', sa.Text()),
        sa.Column('summary', postgresql.JSON()),
        sa.Column('action_items', postgresql.JSON()),
    )

def downgrade():
    op.drop_table('transcripts')
    op.drop_table('meetings')
