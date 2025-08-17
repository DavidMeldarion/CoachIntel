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

    # Create PostgreSQL ENUM types
    lead_status = sa.Enum('waitlist', 'invited', 'converted', 'lost', name='lead_status')
    consent_channel = sa.Enum('email', 'sms', name='consent_channel')
    consent_status = sa.Enum('opted_in', 'opted_out', 'unknown', name='consent_status')
    message_channel = sa.Enum('email', 'sms', name='message_channel')
    message_event_type = sa.Enum('send', 'open', 'click', 'bounce', 'complaint', name='message_event_type')

    lead_status.create(bind, checkfirst=True)
    consent_channel.create(bind, checkfirst=True)
    consent_status.create(bind, checkfirst=True)
    message_channel.create(bind, checkfirst=True)
    message_event_type.create(bind, checkfirst=True)

    # Add password column to users (nullable for OAuth-only accounts)
    op.add_column('users', sa.Column('password', sa.String(), nullable=True))

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
    # Note: If you want DESC on occurred_at, create an index manually via op.execute
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

    # Remove password column from users
    op.drop_column('users', 'password')

    # Drop ENUM types
    for enum_name in [
        'message_event_type',
        'message_channel',
        'consent_status',
        'consent_channel',
        'lead_status',
    ]:
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
