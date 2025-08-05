"""
Revision ID: 20250721_alter_alembic_version_num_length
Revises: 20250718meetings
Create Date: 2025-07-21
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250721_alter_alembic_version_num_length'
down_revision = '20250718meetings'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('alembic_version', 'version_num', type_=sa.String(length=50), existing_type=sa.String(length=32))

def downgrade():
    op.alter_column('alembic_version', 'version_num', type_=sa.String(length=32), existing_type=sa.String(length=50))
