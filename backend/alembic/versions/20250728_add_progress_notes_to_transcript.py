"""
Add progress_notes column to transcripts table
"""
from alembic import op
import sqlalchemy as sa

revision = '20250728_add_progress_notes_to_transcript'
down_revision = '16dd9291704c'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('transcripts', sa.Column('progress_notes', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('transcripts', 'progress_notes')
