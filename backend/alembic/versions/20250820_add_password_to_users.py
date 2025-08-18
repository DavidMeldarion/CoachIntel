"""add password to users

Revision ID: 20250820_add_password_to_users
Revises: 20250819_add_crm_tables
Create Date: 2025-08-20 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250820_add_password_to_users'
down_revision = '20250819_add_crm_tables'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('users')}
    if 'password' not in cols:
        op.add_column('users', sa.Column('password', sa.String(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('users')}
    if 'password' in cols:
        op.drop_column('users', 'password')
