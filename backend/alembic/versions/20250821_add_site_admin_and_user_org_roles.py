"""add site_admin to users and create user_org_roles table

Revision ID: 20250821_add_site_admin_and_user_org_roles
Revises: 20250820_add_password_to_users
Create Date: 2025-08-21 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '20250821_add_site_admin_and_user_org_roles'
down_revision = '20250820_add_password_to_users'
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Add users.site_admin if missing
    user_cols = {c['name'] for c in inspector.get_columns('users')}
    if 'site_admin' not in user_cols:
        op.add_column('users', sa.Column('site_admin', sa.Boolean(), nullable=False, server_default=sa.false()))
        # Remove server_default for cleanliness
        op.alter_column('users', 'site_admin', server_default=None)
        op.create_index('ix_users_site_admin', 'users', ['site_admin'])

    # 2) Create org_role enum if not exists (Postgres)
    # Use a try/except to handle idempotency for enum creation
    enum_name = 'org_role'
    try:
        sa.Enum('admin', 'member', name=enum_name).create(bind, checkfirst=True)
    except Exception:
        pass

    # 3) Create user_org_roles if not exists
    if not _table_exists(bind, 'user_org_roles'):
        op.create_table(
            'user_org_roles',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('role', sa.Enum('admin', 'member', name=enum_name), nullable=False, index=True),
            sa.UniqueConstraint('user_id', 'org_id', 'role', name='uq_user_org_role'),
        )
        op.create_index('ix_user_org_roles_org_role', 'user_org_roles', ['org_id', 'role'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Drop user_org_roles
    if _table_exists(bind, 'user_org_roles'):
        op.drop_index('ix_user_org_roles_org_role', table_name='user_org_roles')
        op.drop_table('user_org_roles')
    # Drop enum type (optional; safe to keep)
    try:
        sa.Enum(name='org_role').drop(bind, checkfirst=True)
    except Exception:
        pass

    # Remove users.site_admin
    user_cols = {c['name'] for c in inspector.get_columns('users')}
    if 'site_admin' in user_cols:
        # Drop index if exists
        try:
            op.drop_index('ix_users_site_admin', table_name='users')
        except Exception:
            pass
        op.drop_column('users', 'site_admin')
