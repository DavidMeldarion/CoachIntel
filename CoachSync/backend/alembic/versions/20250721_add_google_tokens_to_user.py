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
    op.add_column('users', sa.Column('google_access_token_encrypted', sa.String(), nullable=True))
    op.add_column('users', sa.Column('google_refresh_token_encrypted', sa.String(), nullable=True))
    op.add_column('users', sa.Column('google_token_expiry', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('users', 'google_access_token_encrypted')
    op.drop_column('users', 'google_refresh_token_encrypted')
    op.drop_column('users', 'google_token_expiry')
