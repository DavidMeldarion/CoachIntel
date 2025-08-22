"""add meeting tracking models and citext extension

Revision ID: 20250822_add_meeting_tracking_models
Revises: 20250820_add_consents_meta
Create Date: 2025-08-22 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

# revision identifiers, used by Alembic.
revision = '20250822_add_meeting_tracking_models'
down_revision = '20250820_add_consents_meta'
branch_labels = None
depends_on = None


CLIENT_STATUS_ENUM_NAME = 'client_status'


def upgrade() -> None:
    # 1. Ensure citext extension
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # 2. Create client_status enum only if absent (pure SQL check avoids duplicate errors)
    bind = op.get_bind()
    enum_exists = bind.execute(sa.text(
        """
        SELECT 1 FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = :name AND n.nspname = 'public'
        """
    ), {"name": CLIENT_STATUS_ENUM_NAME}).scalar()
    if not enum_exists:
        op.execute(f"CREATE TYPE public.{CLIENT_STATUS_ENUM_NAME} AS ENUM ('prospect','active','inactive')")

    inspector = sa.inspect(bind)

    def _table_exists(name: str) -> bool:
        return name in inspector.get_table_names()

    # 3. persons table
    if not _table_exists('persons'):
        op.create_table(
            'persons',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('primary_email', postgresql.CITEXT(), nullable=True),
            sa.Column('primary_phone', sa.String(), nullable=True),
            sa.Column('emails', postgresql.ARRAY(postgresql.CITEXT()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column('phones', postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column('email_hashes', postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column('phone_hashes', postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 4. clients table
    client_status_enum = PGEnum('prospect','active','inactive', name=CLIENT_STATUS_ENUM_NAME, create_type=False)
    if not _table_exists('clients'):
        op.create_table(
            'clients',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('person_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('persons.id', ondelete='CASCADE'), nullable=False),
            sa.Column('status', client_status_enum, server_default='prospect', nullable=False),
            sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('coach_id', 'person_id', name='uq_clients_coach_person'),
        )

    # 5. external_accounts table
    if not _table_exists('external_accounts'):
        op.create_table(
            'external_accounts',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('provider', sa.String(), nullable=False),
            sa.Column('access_token_enc', sa.String(), nullable=True),
            sa.Column('refresh_token_enc', sa.String(), nullable=True),
            sa.Column('scopes', postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False),
            sa.Column('external_user_id', sa.String(), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('coach_id', 'provider', name='uq_external_accounts_coach_provider'),
        )

    # 6. meetings table (create or evolve existing legacy schema)
    if not _table_exists('meetings'):
        op.create_table(
            'meetings',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('platform', sa.String(), nullable=True),
            sa.Column('topic', sa.String(), nullable=True),
            sa.Column('join_url', sa.String(), nullable=True),
            sa.Column('ical_uid', sa.String(), nullable=True),
            sa.Column('location', sa.String(), nullable=True),
            sa.Column('external_refs', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
            sa.Column('transcript_status', sa.String(), nullable=True),
        )
    else:
        existing_cols = {c['name'] for c in inspector.get_columns('meetings')}
        # Map of column name -> Column object for additions
        meeting_new_cols = {
            'coach_id': sa.Column('coach_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),  # nullable first then backfill / enforce later
            'started_at': sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            'ended_at': sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
            'platform': sa.Column('platform', sa.String(), nullable=True),
            'topic': sa.Column('topic', sa.String(), nullable=True),
            'join_url': sa.Column('join_url', sa.String(), nullable=True),
            'ical_uid': sa.Column('ical_uid', sa.String(), nullable=True),
            'location': sa.Column('location', sa.String(), nullable=True),
            'external_refs': sa.Column('external_refs', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
            'transcript_status': sa.Column('transcript_status', sa.String(), nullable=True),
        }
        for name, col in meeting_new_cols.items():
            if name not in existing_cols:
                op.add_column('meetings', col)

    # 7. meeting_attendees table
    if not _table_exists('meeting_attendees'):
        # Determine meeting_id column type to match existing meetings.id
        meeting_id_type = postgresql.UUID(as_uuid=True)
        if _table_exists('meetings'):
            try:
                for col in inspector.get_columns('meetings'):
                    if col['name'] == 'id':
                        # If existing is a VARCHAR/Text (legacy), adapt
                        if isinstance(col['type'], sa.String) or 'CHAR' in col['type'].__class__.__name__.upper():
                            meeting_id_type = sa.String()
                        break
            except Exception:
                pass
        op.create_table(
            'meeting_attendees',
            sa.Column('meeting_id', meeting_id_type, sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
            sa.Column('person_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('persons.id', ondelete='SET NULL'), nullable=True),
            sa.Column('source', sa.String(), nullable=False),
            sa.Column('external_attendee_id', sa.String(), nullable=True),
            sa.Column('raw_email', postgresql.CITEXT(), nullable=True),
            sa.Column('raw_phone', sa.String(), nullable=True),
            sa.Column('raw_name', sa.String(), nullable=True),
            sa.Column('role', sa.String(), nullable=True),
            sa.Column('identity_key', sa.String(), sa.Computed("COALESCE(external_attendee_id, raw_email, raw_name)", persisted=True), nullable=False),
            sa.PrimaryKeyConstraint('meeting_id', 'source', 'identity_key', name='pk_meeting_attendee'),
        )

    # 8. Indexes (guarded)
    existing_indexes = {ix['name'] for ix in inspector.get_indexes('persons')} if _table_exists('persons') else set()
    if _table_exists('persons') and 'ix_person_email_hashes' not in existing_indexes:
        op.create_index('ix_person_email_hashes', 'persons', ['email_hashes'], postgresql_using='gin')
    if _table_exists('persons') and 'ix_person_phone_hashes' not in existing_indexes:
        op.create_index('ix_person_phone_hashes', 'persons', ['phone_hashes'], postgresql_using='gin')
    if _table_exists('clients'):
        client_indexes = {ix['name'] for ix in inspector.get_indexes('clients')}
        if 'ix_clients_coach_status' not in client_indexes:
            op.create_index('ix_clients_coach_status', 'clients', ['coach_id', 'status'])
    if _table_exists('external_accounts'):
        ea_indexes = {ix['name'] for ix in inspector.get_indexes('external_accounts')}
        if 'ix_external_accounts_provider' not in ea_indexes:
            op.create_index('ix_external_accounts_provider', 'external_accounts', ['provider'])
    if _table_exists('meetings'):
        meeting_indexes = {ix['name'] for ix in inspector.get_indexes('meetings')}
        existing_meeting_cols = {c['name'] for c in inspector.get_columns('meetings')}
        if 'ix_meeting_ical_uid' not in meeting_indexes and 'ical_uid' in existing_meeting_cols:
            op.create_index('ix_meeting_ical_uid', 'meetings', ['ical_uid'])
        if 'ix_meeting_zoom_meeting_id' not in meeting_indexes and 'external_refs' in existing_meeting_cols:
            op.create_index('ix_meeting_zoom_meeting_id', 'meetings', [sa.text("(external_refs ->> 'zoom_meeting_id')")])
        if 'ix_meetings_coach_started' not in meeting_indexes and {'coach_id','started_at'}.issubset(existing_meeting_cols):
            op.create_index('ix_meetings_coach_started', 'meetings', ['coach_id', 'started_at'])
    if _table_exists('meeting_attendees'):
        ma_indexes = {ix['name'] for ix in inspector.get_indexes('meeting_attendees')}
        if 'ix_meeting_attendees_meeting_source' not in ma_indexes:
            op.create_index('ix_meeting_attendees_meeting_source', 'meeting_attendees', ['meeting_id', 'source'])
def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index('ix_meeting_attendees_meeting_source', table_name='meeting_attendees')
    op.drop_table('meeting_attendees')

    op.drop_index('ix_meetings_coach_started', table_name='meetings')
    op.drop_index('ix_meeting_zoom_meeting_id', table_name='meetings')
    op.drop_index('ix_meeting_ical_uid', table_name='meetings')
    op.drop_table('meetings')

    op.drop_index('ix_external_accounts_provider', table_name='external_accounts')
    op.drop_table('external_accounts')

    op.drop_index('ix_clients_coach_status', table_name='clients')
    op.drop_table('clients')

    op.drop_index('ix_person_phone_hashes', table_name='persons')
    op.drop_index('ix_person_email_hashes', table_name='persons')
    op.drop_table('persons')

    # Optionally drop enum (kept by default). Uncomment to remove:
    # op.execute("DROP TYPE IF EXISTS public.client_status")
    # Leave citext extension in place (harmless if retained).
