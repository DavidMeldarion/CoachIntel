"""Create mt_meetings tracking table and re-point FK dependencies.

Revision ID: 20250825_create_mt_meetings_table
Revises: 20250825_rename_tracking_meetings_table
Create Date: 2025-08-25

Rationale:
  The rename strategy left no mt_meetings table (original 'meetings' likely legacy).
  This migration creates the dedicated tracking table and (best-effort) copies
  UUID-looking tracking rows from legacy 'meetings' if present.
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20250825_create_mt_meetings_table'
down_revision = '20250825_rename_tracking_meetings_table'
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'mt_meetings' not in tables:
        op.create_table(
            'mt_meetings',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('coach_id', sa.Integer(), nullable=False, index=True),  # intentionally no FK
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('platform', sa.String(), nullable=True),
            sa.Column('topic', sa.String(), nullable=True),
            sa.Column('join_url', sa.String(), nullable=True),
            sa.Column('ical_uid', sa.String(), nullable=True),
            sa.Column('location', sa.String(), nullable=True),
            sa.Column('external_refs', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
            sa.Column('transcript_status', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=True),
        )
        # Indexes
        op.create_index('ix_mt_meetings_ical_uid', 'mt_meetings', ['ical_uid'])
        op.create_index('ix_mt_meetings_coach_started', 'mt_meetings', ['coach_id','started_at'])
        op.create_index('ix_mt_meetings_zoom_meeting_id', 'mt_meetings', [sa.text("(external_refs ->> 'zoom_meeting_id')")])

    # Data backfill (best effort) from legacy 'meetings' if shape matches
    if 'meetings' in tables:
        cols = {c['name']: c for c in inspector.get_columns('meetings')}
        needed = {'id','coach_id','external_refs'}
        if needed.issubset(cols.keys()):
            # Ensure pgcrypto for gen_random_uuid (idempotent)
            try:
                bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            except Exception:
                pass
            # Copy rows assigning a new UUID if legacy id not UUID format; embed original id under external_refs.legacy_id
            copy_sql = """
                INSERT INTO mt_meetings (id, coach_id, started_at, ended_at, platform, topic, join_url, ical_uid, location, external_refs, transcript_status, status)
                SELECT 
                    CASE 
                        WHEN id ~ '^[0-9a-fA-F-]{36}$' THEN id::uuid
                        ELSE gen_random_uuid()
                    END AS id,
                    COALESCE(coach_id, 0) AS coach_id,
                    started_at, ended_at, platform, topic, join_url, ical_uid, location,
                    CASE 
                        WHEN external_refs IS NULL THEN jsonb_build_object('legacy_id', id::text)
                        ELSE external_refs || jsonb_build_object('legacy_id', id::text)
                    END AS external_refs,
                    transcript_status, status
                FROM meetings
                WHERE (external_refs IS NOT NULL AND external_refs::text <> '{}')
                   OR (started_at IS NOT NULL OR ended_at IS NOT NULL OR topic IS NOT NULL)
                ON CONFLICT (id) DO NOTHING
            """
            try:
                bind.execute(sa.text(copy_sql))
            except Exception:
                pass

    # Re-point FKs in dependent tables if they exist
    # meeting_attendees: if meeting_id is VARCHAR, convert to UUID before FK
    tables = set(inspector.get_table_names())
    if 'meeting_attendees' in tables:
        ma_cols = {c['name']: c for c in inspector.get_columns('meeting_attendees')}
        if 'meeting_id' in ma_cols and not isinstance(ma_cols['meeting_id']['type'], postgresql.UUID):
            # Ensure pgcrypto
            try:
                bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            except Exception:
                pass
            # Drop existing PK
            try:
                op.drop_constraint('pk_meeting_attendee', table_name='meeting_attendees', type_='primary')
            except Exception:
                pass
            # Add temp column
            op.add_column('meeting_attendees', sa.Column('meeting_id_uuid', postgresql.UUID(as_uuid=True), nullable=True))
            # Populate
            bind.execute(sa.text("""
                UPDATE meeting_attendees
                SET meeting_id_uuid = CASE
                    WHEN meeting_id ~ '^[0-9a-fA-F-]{36}$' THEN meeting_id::uuid
                    ELSE gen_random_uuid()
                END
            """))
            # Drop old column
            op.drop_column('meeting_attendees', 'meeting_id')
            # Rename
            op.alter_column('meeting_attendees', 'meeting_id_uuid', new_column_name='meeting_id', existing_type=postgresql.UUID(as_uuid=True), nullable=False)
            # Recreate PK
            op.create_primary_key('pk_meeting_attendee', 'meeting_attendees', ['meeting_id', 'source', 'identity_key'])
        # Finally create FK to mt_meetings
        try:
            # Drop any existing FK referencing legacy meetings
            for fk in inspector.get_foreign_keys('meeting_attendees'):
                if fk.get('referred_table') in ('meetings','mt_meetings') and 'meeting_id' in fk.get('constrained_columns', []):
                    try:
                        op.drop_constraint(fk['name'], table_name='meeting_attendees', type_='foreignkey')
                    except Exception:
                        pass
            op.create_foreign_key('fk_meeting_attendees_meeting_id_mt_meetings', 'meeting_attendees', 'mt_meetings', ['meeting_id'], ['id'], ondelete='CASCADE')
        except Exception:
            pass
    # review_candidates: drop FK if incompatible then recreate
    if 'review_candidates' in tables:
        try:
            rc_cols = {c['name']: c for c in inspector.get_columns('review_candidates')}
            # Drop existing FKs first
            for fk in inspector.get_foreign_keys('review_candidates'):
                if fk.get('referred_table') in ('meetings','mt_meetings') and 'meeting_id' in fk.get('constrained_columns', []):
                    try:
                        op.drop_constraint(fk['name'], table_name='review_candidates', type_='foreignkey')
                    except Exception:
                        pass
            # If meeting_id is not UUID yet, convert with mapping
            from sqlalchemy.dialects.postgresql import UUID as PGUUID
            if 'meeting_id' in rc_cols and not isinstance(rc_cols['meeting_id']['type'], PGUUID):
                # Add temp column
                op.add_column('review_candidates', sa.Column('meeting_id_uuid', postgresql.UUID(as_uuid=True), nullable=True))
                # 1. Map legacy string IDs using external_refs.legacy_id
                bind.execute(sa.text("""
                    UPDATE review_candidates rc
                    SET meeting_id_uuid = m.id
                    FROM mt_meetings m
                    WHERE (m.external_refs ->> 'legacy_id') = rc.meeting_id
                """))
                # 2. For rows that look like UUID literal, cast directly if still null
                bind.execute(sa.text("""
                    UPDATE review_candidates
                    SET meeting_id_uuid = meeting_id::uuid
                    WHERE meeting_id_uuid IS NULL AND meeting_id ~ '^[0-9a-fA-F-]{36}$'
                """))
                # 3. Leave others as NULL (cannot map)
                # Drop old column and rename
                op.drop_column('review_candidates', 'meeting_id')
                op.alter_column('review_candidates', 'meeting_id_uuid', new_column_name='meeting_id', existing_type=postgresql.UUID(as_uuid=True), nullable=True)
            # Finally create FK (nullable, SET NULL on delete)
            op.create_foreign_key('fk_review_candidates_meeting_id_mt_meetings', 'review_candidates', 'mt_meetings', ['meeting_id'], ['id'], ondelete='SET NULL')
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    # Drop FKs referencing mt_meetings
    for tbl in ['meeting_attendees','review_candidates']:
        if tbl in tables:
            try:
                for fk in inspector.get_foreign_keys(tbl):
                    if fk.get('referred_table') == 'mt_meetings':
                        try:
                            op.drop_constraint(fk['name'], table_name=tbl, type_='foreignkey')
                        except Exception:
                            pass
            except Exception:
                pass
    if 'mt_meetings' in tables:
        op.drop_index('ix_mt_meetings_zoom_meeting_id', table_name='mt_meetings')
        op.drop_index('ix_mt_meetings_coach_started', table_name='mt_meetings')
        op.drop_index('ix_mt_meetings_ical_uid', table_name='mt_meetings')
        op.drop_table('mt_meetings')
