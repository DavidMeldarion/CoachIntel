"""add plan to users

Revision ID: 20250814_add_plan_to_users
Revises: 20250728_add_progress_notes_to_transcript
Create Date: 2025-08-14 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250814_add_plan_to_users'
down_revision = '20250728_add_progress_notes_to_transcript'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('plan', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'plan')
