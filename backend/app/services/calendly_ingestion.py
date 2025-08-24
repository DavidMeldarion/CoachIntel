from __future__ import annotations
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.calendar_sync import upsert_calendly_event
from app.clients.result import Result, failure


def extract_event_invitee(payload: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Extract scheduled event UUID and invitee UUID from Calendly webhook payload.

    Supports both invitee.created and invitee.canceled; falls back gracefully.
    """
    if not isinstance(payload, dict):
        return None, None
    inv = payload.get('invitee') or {}
    evt = payload.get('event') or {}
    invitee_uuid = inv.get('uuid') if isinstance(inv, dict) else payload.get('invitee_uuid')
    event_uuid = evt.get('uuid') if isinstance(evt, dict) else payload.get('event_uuid')
    return event_uuid, invitee_uuid


async def handle_calendly_webhook(session: AsyncSession, coach_id: int, body: Dict[str, Any]) -> Result[dict]:
    """High-level orchestration: derive event + invitee and upsert.

    Returns Result containing meeting/attendee counts or benign failure if not actionable.
    """
    event_type = body.get('event')
    payload = body.get('payload') or {}
    event_uuid, invitee_uuid = extract_event_invitee(payload)
    if not event_uuid:
        return failure("no_event_uuid")
    return await upsert_calendly_event(session, coach_id, event_uuid, invitee_uuid)

__all__ = ['handle_calendly_webhook','extract_event_invitee']
