"""add consents.meta json column

Revision ID: 20250820_add_consents_meta
Revises: 20250821_add_site_admin_and_user_org_roles
Create Date: 2025-08-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250820_add_consents_meta'
down_revision = '20250821_add_site_admin_and_user_org_roles'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('consents', sa.Column('meta', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('consents', 'meta')
