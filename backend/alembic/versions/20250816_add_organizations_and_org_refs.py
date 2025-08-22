"""add organizations table and org refs

Revision ID: 20250816_add_organizations_and_org_refs
Revises: 20250814_add_plan_to_users
Create Date: 2025-08-16 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250816_add_organizations_and_org_refs'
down_revision = '20250814_add_plan_to_users'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key', name='uq_organizations_key'),
    )
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_key'), 'organizations', ['key'], unique=True)

    op.add_column('users', sa.Column('org_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_users_org_id'), 'users', ['org_id'], unique=False)
    op.create_foreign_key(None, 'users', 'organizations', ['org_id'], ['id'])

    op.add_column('meetings', sa.Column('org_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_meetings_org_id'), 'meetings', ['org_id'], unique=False)
    op.create_foreign_key(None, 'meetings', 'organizations', ['org_id'], ['id'])

    op.add_column('transcripts', sa.Column('org_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_transcripts_org_id'), 'transcripts', ['org_id'], unique=False)
    op.create_foreign_key(None, 'transcripts', 'organizations', ['org_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'transcripts', type_='foreignkey')
    op.drop_index(op.f('ix_transcripts_org_id'), table_name='transcripts')
    op.drop_column('transcripts', 'org_id')

    op.drop_constraint(None, 'meetings', type_='foreignkey')
    op.drop_index(op.f('ix_meetings_org_id'), table_name='meetings')
    op.drop_column('meetings', 'org_id')

    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_org_id'), table_name='users')
    op.drop_column('users', 'org_id')

    op.drop_index(op.f('ix_organizations_key'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_id'), table_name='organizations')
    op.drop_table('organizations')
