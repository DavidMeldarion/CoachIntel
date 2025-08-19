import os
import logging
from app.services.providers.postmark_provider import PostmarkProvider
from app.services.sms_service import SmsService
from app.services.email_service import EmailService
from app.models import AsyncSessionLocal, MessageEvent
from sqlalchemy import insert
from datetime import datetime

class NoopEmailProvider:
    def __init__(self):
        self.logger = logging.getLogger("NoopEmailProvider")

    def send(self, to: str, subject: str, html: str, meta: dict | None = None) -> str | None:
        self.logger.info(f"NOOP email to={to} subject={subject} meta={meta}")
        return None

class NoopSmsProvider:
    def __init__(self):
        self.logger = logging.getLogger("NoopSmsProvider")

    def send(self, to: str, body: str, meta: dict | None = None) -> None:
        self.logger.info(f"NOOP sms to={to} body={body} meta={meta}")


def get_email_service():
    """
    Factory for EmailService.
    - EMAIL_PROVIDER=postmark (default): uses POSTMARK_API_KEY; if missing, falls back to Noop.
    - EMAIL_PROVIDER=ses: (placeholder) would use AWS SES (not implemented here).
    """
    provider = os.getenv("EMAIL_PROVIDER", "postmark").lower()
    if provider == "postmark":
        api_key = os.getenv("POSTMARK_API_KEY") or os.getenv("POSTMARK_TOKEN")
        if api_key:
            return PostmarkProvider(api_key)
        return NoopEmailProvider()
    # Placeholder for SES; return noop for now
    return NoopEmailProvider()


def get_sms_service():
    """Factory for SmsService. TWILIO_* envs optional; fallback to noop."""
    # Placeholder: using noop until Twilio or other provider is implemented
    # TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM may be used later
    return NoopSmsProvider()


async def record_event(lead_id: str, channel: str, type: str, meta: dict | None = None, provider_id: str | None = None):
    """Insert a MessageEvent row."""
    async with AsyncSessionLocal() as session:
        evt = MessageEvent(
            lead_id=lead_id,
            channel=channel,
            type=type,
            provider_id=provider_id,
            meta=meta or {},
        )
        session.add(evt)
        await session.commit()

async def send_email_and_record(lead_id: str, to: str, subject: str, html: str, meta: dict | None = None):
    """Send email via provider and record a 'send' MessageEvent on success."""
    provider = get_email_service()
    message_id = None
    try:
        message_id = provider.send(to, subject, html, meta)
    except Exception:
        # Let caller decide on error handling; do not record event on failure
        raise
    await record_event(lead_id=lead_id, channel='email', type='send', meta=meta, provider_id=message_id)

async def send_sms_and_record(lead_id: str, to: str, body: str, meta: dict | None = None):
    """Send SMS via provider (noop for now) and record a 'send' event on success."""
    provider = get_sms_service()
    try:
        provider.send(to, body, meta)
    except Exception:
        raise
    await record_event(lead_id=lead_id, channel='sms', type='send', meta=meta, provider_id=None)
