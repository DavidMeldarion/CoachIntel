"""Update review_candidates to new schema (attendee-centric)

Revision ID: 20250823_update_review_candidate_model
Revises: 20250822_add_person_primary_contact_indexes
Create Date: 2025-08-23 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250823_update_review_candidate_model'
down_revision = '20250822_add_person_primary_contact_indexes'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Create new enum type if not exists
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_type t
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE t.typname = 'review_candidate_status'
        ) THEN
            CREATE TYPE review_candidate_status AS ENUM ('open','resolved');
        END IF;
    END
    $$ LANGUAGE plpgsql;
    """)

    if 'review_candidates' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('review_candidates')}
        legacy_cols = {'person_a_id','person_b_id','source','resolved'}
        # Ensure citext extension for raw_email (idempotent)
        op.execute("CREATE EXTENSION IF NOT EXISTS citext")
        # Add new columns if missing
        if 'attendee_source' not in cols:
            op.add_column('review_candidates', sa.Column('attendee_source', sa.String(), nullable=True))
        if 'raw_email' not in cols:
            op.add_column('review_candidates', sa.Column('raw_email', postgresql.CITEXT(), nullable=True))
        if 'raw_phone' not in cols:
            op.add_column('review_candidates', sa.Column('raw_phone', sa.String(), nullable=True))
        if 'raw_name' not in cols:
            op.add_column('review_candidates', sa.Column('raw_name', sa.String(), nullable=True))
        if 'candidate_person_ids' not in cols:
            op.add_column('review_candidates', sa.Column('candidate_person_ids', postgresql.ARRAY(postgresql.UUID()), server_default=sa.text("'{}'"), nullable=False))
        if 'status' not in cols:
            op.add_column('review_candidates', sa.Column('status', sa.Enum('open','resolved', name='review_candidate_status'), server_default=sa.text("'open'"), nullable=False))
            try:
                op.create_index('ix_review_candidates_coach_status_created', 'review_candidates', ['coach_id','status','created_at'])
            except Exception:
                pass
        # Drop legacy unique constraint if exists
        try:
            op.drop_constraint('uq_review_candidate_pair', 'review_candidates', type_='unique')
        except Exception:
            pass
        # Drop legacy FKs referencing persons before dropping columns
        existing_fks = insp.get_foreign_keys('review_candidates')
        fk_by_col = {fk['constrained_columns'][0]: fk['name'] for fk in existing_fks if fk.get('constrained_columns')}
        for legacy_col in ['person_a_id','person_b_id']:
            if legacy_col in cols and legacy_col in fk_by_col:
                try:
                    op.drop_constraint(fk_by_col[legacy_col], 'review_candidates', type_='foreignkey')
                except Exception:
                    pass
        # Drop legacy columns if present (after constraints removed)
        for c in legacy_cols & cols:
            try:
                op.drop_column('review_candidates', c)
            except Exception:
                pass
    else:
        # Create table fresh if it never existed
        op.create_table(
            'review_candidates',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('meeting_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('meetings.id', ondelete='SET NULL'), nullable=True),
            sa.Column('attendee_source', sa.String(), nullable=True),
            sa.Column('raw_email', postgresql.CITEXT(), nullable=True),
            sa.Column('raw_phone', sa.String(), nullable=True),
            sa.Column('raw_name', sa.String(), nullable=True),
            sa.Column('candidate_person_ids', postgresql.ARRAY(postgresql.UUID()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column('reason', sa.String(), nullable=False),
            sa.Column('status', sa.Enum('open','resolved', name='review_candidate_status'), server_default=sa.text("'open'"), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_review_candidates_coach_status_created', 'review_candidates', ['coach_id','status','created_at'])


def downgrade():
    # Non-trivial to restore old schema; perform partial rollback: drop added columns & enum
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if 'review_candidates' in insp.get_table_names():
        for col in ['attendee_source','raw_email','raw_phone','raw_name','candidate_person_ids','status']:
            try:
                op.drop_column('review_candidates', col)
            except Exception:
                pass
    # Drop enum type
    try:
        op.execute("DROP TYPE IF EXISTS review_candidate_status")
    except Exception:
        pass
