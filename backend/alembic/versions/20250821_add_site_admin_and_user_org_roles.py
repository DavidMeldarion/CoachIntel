"""add site_admin to users and create user_org_roles table

Revision ID: 20250821_add_site_admin_and_user_org_roles
Revises: 20250820_add_password_to_users
Create Date: 2025-08-21 00:00:00

"""
from alembic import op
import sqlalchemy as sa

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

    # 2) Ensure org_role enum exists (idempotent)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE t.typname = 'org_role' AND n.nspname = 'public'
            ) THEN
                CREATE TYPE public.org_role AS ENUM ('admin', 'member');
            END IF;
        END
        $$ LANGUAGE plpgsql;
        """
    )

    # 3) Create user_org_roles if not exists (raw SQL to avoid Enum recreation issues)
    if not _table_exists(bind, 'user_org_roles'):
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS public.user_org_roles (
                id SERIAL PRIMARY KEY,
                user_id integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                role public.org_role NOT NULL,
                CONSTRAINT uq_user_org_role UNIQUE (user_id, org_id, role)
            );
            """
        )
        op.execute("CREATE INDEX IF NOT EXISTS ix_user_org_roles_user_id ON public.user_org_roles (user_id);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_user_org_roles_org_id ON public.user_org_roles (org_id);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_user_org_roles_role ON public.user_org_roles (role);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_user_org_roles_org_role ON public.user_org_roles (org_id, role);")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Drop user_org_roles and its indexes
    if _table_exists(bind, 'user_org_roles'):
        op.execute("DROP TABLE IF EXISTS public.user_org_roles CASCADE;")

    # Leave enum type in place (safe to keep). Uncomment to drop if desired:
    # op.execute("DROP TYPE IF EXISTS public.org_role;")

    # Remove users.site_admin
    user_cols = {c['name'] for c in inspector.get_columns('users')}
    if 'site_admin' in user_cols:
        # Drop index if exists
        try:
            op.drop_index('ix_users_site_admin', table_name='users')
        except Exception:
            pass
        op.drop_column('users', 'site_admin')
