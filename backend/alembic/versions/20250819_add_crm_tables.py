"""add CRM tables: leads, consents, message_events

Revision ID: 20250819_add_crm_tables
Revises: 20250816_add_organizations_and_org_refs
Create Date: 2025-08-19 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = '20250819_add_crm_tables'
down_revision = '20250816_add_organizations_and_org_refs'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Create PostgreSQL ENUM types idempotently
    op.execute("""
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lead_status') THEN
        CREATE TYPE lead_status AS ENUM ('waitlist', 'invited', 'converted', 'lost');
      END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'consent_channel') THEN
        CREATE TYPE consent_channel AS ENUM ('email', 'sms');
      END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'consent_status') THEN
        CREATE TYPE consent_status AS ENUM ('opted_in', 'opted_out', 'unknown');
      END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_channel') THEN
        CREATE TYPE message_channel AS ENUM ('email', 'sms');
      END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_event_type') THEN
        CREATE TYPE message_event_type AS ENUM ('send', 'open', 'click', 'bounce', 'complaint');
      END IF;
    END $$;
    """)

    # Reuse enums without attempting to create them during table DDL
    lead_status = pg.ENUM('waitlist', 'invited', 'converted', 'lost', name='lead_status', create_type=False)
    consent_channel = pg.ENUM('email', 'sms', name='consent_channel', create_type=False)
    consent_status = pg.ENUM('opted_in', 'opted_out', 'unknown', name='consent_status', create_type=False)
    message_channel = pg.ENUM('email', 'sms', name='message_channel', create_type=False)
    message_event_type = pg.ENUM('send', 'open', 'click', 'bounce', 'complaint', name='message_event_type', create_type=False)

    # leads
    op.create_table(
        'leads',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('status', lead_status, nullable=False, server_default='waitlist'),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('utm_source', sa.String(), nullable=True),
        sa.Column('utm_medium', sa.String(), nullable=True),
        sa.Column('utm_campaign', sa.String(), nullable=True),
        sa.Column('tags', pg.ARRAY(sa.String()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_contacted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('org_id', 'email', name='uq_leads_org_email')
    )
    op.create_index('ix_leads_org_created', 'leads', ['org_id', 'created_at'], unique=False)

    # consents
    op.create_table(
        'consents',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('lead_id', pg.UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', consent_channel, nullable=False),
        sa.Column('status', consent_status, nullable=False, server_default='unknown'),
        sa.Column('captured_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('source', sa.String(), nullable=True),
    )
    op.create_index('ix_consents_org_captured', 'consents', ['org_id', 'captured_at'], unique=False)

    # message_events
    op.create_table(
        'message_events',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('lead_id', pg.UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', message_channel, nullable=False),
        sa.Column('type', message_event_type, nullable=False),
        sa.Column('provider_id', sa.String(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_message_events_lead_occurred', 'message_events', ['lead_id', 'occurred_at'], unique=False)


def downgrade():
    bind = op.get_bind()

    # Drop tables first (they depend on enums)
    op.drop_index('ix_message_events_lead_occurred', table_name='message_events')
    op.drop_table('message_events')

    op.drop_index('ix_consents_org_captured', table_name='consents')
    op.drop_table('consents')

    op.drop_index('ix_leads_org_created', table_name='leads')
    op.drop_table('leads')

    # Drop ENUM types if they exist
    for enum_name in [
        'message_event_type',
        'message_channel',
        'consent_status',
        'consent_channel',
        'lead_status',
    ]:
        op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN DROP TYPE {enum_name}; END IF; END $$;")
