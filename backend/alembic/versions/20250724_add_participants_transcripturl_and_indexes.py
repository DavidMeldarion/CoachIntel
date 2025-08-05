"""
Revision ID: 20250724_add_participants_transcripturl_and_indexes
Revises: f41a83ef8159
Create Date: 2025-07-24
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250724_add_meeting_fields'
down_revision = 'f41a83ef8159'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('meetings', sa.Column('participants', sa.JSON(), nullable=True))
    op.add_column('meetings', sa.Column('transcript_url', sa.String(), nullable=True))
    op.create_index('ix_meetings_date', 'meetings', ['date'])
    op.create_index('ix_meetings_user_id', 'meetings', ['user_id'])

def downgrade():
    op.drop_index('ix_meetings_date', table_name='meetings')
    op.drop_index('ix_meetings_user_id', table_name='meetings')
    op.drop_column('meetings', 'participants')
    op.drop_column('meetings', 'transcript_url')
