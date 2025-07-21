"""
Merge heads: 20250721_add_google_tokens_to_user and f41a83ef8159

Revision ID: 20250721_merge_heads
Revises: 20250721_add_google_tokens_to_user, f41a83ef8159
Create Date: 2025-07-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250721_merge_heads'
down_revision = ('20250721_add_google_tokens_to_user', 'f41a83ef8159')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
