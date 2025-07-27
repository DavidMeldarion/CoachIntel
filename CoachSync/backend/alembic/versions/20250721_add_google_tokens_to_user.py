"""
Revision ID: 20250721_add_google_tokens_to_user
Revises: 20250721_alter_alembic_version_num_length
Create Date: 2025-07-21
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250721_add_google_tokens_to_user'
down_revision = '20250721_alter_alembic_version_num_length'
branch_labels = None
depends_on = None

def upgrade():
    return
    # Columns already created in initial migration

def downgrade():
    op.drop_column('users', 'google_access_token_encrypted')
    op.drop_column('users', 'google_refresh_token_encrypted')
    op.drop_column('users', 'google_token_expiry')
