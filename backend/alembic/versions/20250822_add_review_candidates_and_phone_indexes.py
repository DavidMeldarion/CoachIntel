"""add review_candidates table and phone GIN index

Revision ID: 20250822_add_review_candidates_and_phone_indexes
Revises: 20250822_add_meeting_tracking_models
Create Date: 2025-08-22 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20250822_add_review_candidates_and_phone_indexes'
down_revision = '20250822_add_meeting_tracking_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tables = set(inspector.get_table_names())

    if 'review_candidates' not in tables:
        # Detect meetings.id type (legacy may be VARCHAR instead of UUID)
        meeting_id_type = postgresql.UUID(as_uuid=True)
        if 'meetings' in tables:
            try:
                for col in inspector.get_columns('meetings'):
                    if col['name'] == 'id':
                        if isinstance(col['type'], sa.String) or 'CHAR' in col['type'].__class__.__name__.upper():
                            meeting_id_type = sa.String()
                        break
            except Exception:  # pragma: no cover
                pass
        op.create_table(
            'review_candidates',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('person_a_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('persons.id', ondelete='CASCADE'), nullable=False),
            sa.Column('person_b_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('persons.id', ondelete='CASCADE'), nullable=False),
            sa.Column('meeting_id', meeting_id_type, sa.ForeignKey('meetings.id', ondelete='SET NULL'), nullable=True),
            sa.Column('source', sa.String(), nullable=True),
            sa.Column('reason', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.UniqueConstraint('coach_id', 'person_a_id', 'person_b_id', 'meeting_id', name='uq_review_candidate_pair'),
        )
        op.create_index('ix_review_candidates_coach_created', 'review_candidates', ['coach_id', 'created_at'])

    if 'persons' in tables:
        existing_indexes = {ix['name'] for ix in inspector.get_indexes('persons')}
        if 'ix_person_phones' not in existing_indexes:
            op.create_index('ix_person_phones', 'persons', ['phones'], postgresql_using='gin')
        if 'ix_person_phone_hashes' not in existing_indexes:
            try:
                op.create_index('ix_person_phone_hashes', 'persons', ['phone_hashes'], postgresql_using='gin')
            except Exception:
                pass


def downgrade() -> None:
    op.drop_index('ix_review_candidates_coach_created', table_name='review_candidates')
    op.drop_table('review_candidates')
    try:
        op.drop_index('ix_person_phones', table_name='persons')
    except Exception:
        pass
    # phone_hashes index originally added in prior migration; keep.
