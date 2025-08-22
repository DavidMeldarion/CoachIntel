"""add btree indexes on persons primary_email/primary_phone

Revision ID: 20250822_add_person_primary_contact_indexes
Revises: 20250822_add_review_candidates_and_phone_indexes
Create Date: 2025-08-22 12:15:00
"""
from alembic import op
import sqlalchemy as sa

revision = '20250822_add_person_primary_contact_indexes'
down_revision = '20250822_add_review_candidates_and_phone_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'persons' in inspector.get_table_names():
        existing = {ix['name'] for ix in inspector.get_indexes('persons')}
        if 'ix_person_primary_email' not in existing:
            op.create_index('ix_person_primary_email', 'persons', ['primary_email'])
        if 'ix_person_primary_phone' not in existing:
            op.create_index('ix_person_primary_phone', 'persons', ['primary_phone'])


def downgrade() -> None:
    op.drop_index('ix_person_primary_phone', table_name='persons')
    op.drop_index('ix_person_primary_email', table_name='persons')
