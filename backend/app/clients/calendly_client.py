from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import httpx
import logging

from .base import OAuthExternalClient

logger = logging.getLogger("calendly_client")

CALENDLY_API_BASE = "https://api.calendly.com"

@dataclass
class CalendlyInvitee:
    uuid: str
    email: Optional[str]
    name: Optional[str]
    status: Optional[str]
    raw: Dict[str, Any]

@dataclass
class CalendlyScheduledEvent:
    uri: str
    name: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    location: Optional[str]
    raw: Dict[str, Any]

@dataclass
class CalendlyWebhookEvent:
    event: str
    invitee_uuid: Optional[str]
    payload: Dict[str, Any]

class CalendlyClient(OAuthExternalClient):
    def __init__(self, session, coach_id: int):
        super().__init__(session, coach_id, provider='calendly')

    async def get_invitee(self, invitee_uuid: str) -> CalendlyInvitee | None:
        tok = await self._ensure_token()
        url = f"{CALENDLY_API_BASE}/invitees/{invitee_uuid}"
        headers = {"Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            logger.warning("Calendly get_invitee failed %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json().get('resource') or resp.json()
        return CalendlyInvitee(
            uuid=data.get('uuid'),
            email=data.get('email'),
            name=data.get('name'),
            status=data.get('status'),
            raw=data,
        )

    async def get_scheduled_event(self, event_uuid: str) -> CalendlyScheduledEvent | None:
        tok = await self._ensure_token()
        url = f"{CALENDLY_API_BASE}/scheduled_events/{event_uuid}"
        headers = {"Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            logger.warning("Calendly get_scheduled_event failed %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json().get('resource') or resp.json()
        return CalendlyScheduledEvent(
            uri=data.get('uri'),
            name=data.get('name'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            location=(data.get('location') or {}).get('location') if isinstance(data.get('location'), dict) else None,
            raw=data,
        )

    @staticmethod
    def parse_webhook(payload: Dict[str, Any]) -> CalendlyWebhookEvent:
        event = payload.get('event') or payload.get('event_type') or ''
        invitee_uuid = None
        p = payload.get('payload') or {}
        if isinstance(p, dict):
            invitee_uuid = p.get('invitee', {}).get('uuid') or p.get('invitee_uuid')
        return CalendlyWebhookEvent(event=event, invitee_uuid=invitee_uuid, payload=payload)
