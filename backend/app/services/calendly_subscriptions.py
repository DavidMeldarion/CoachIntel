"""Calendly subscription management & webhook helpers."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import httpx, hmac, hashlib, time, logging, os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models_meeting_tracking import ExternalAccount
from app.clients.calendly_client import CalendlyClient
from app.clients.result import Result, success, failure
from app.services.calendar_sync import upsert_calendly_event

logger = logging.getLogger("calendly_subs")

CAL_API = "https://api.calendly.com"

async def create_subscription(session: AsyncSession, coach_id: int, scope: str, url: str, org_or_user_uri: str) -> Result[Dict[str, Any]]:
    scope = scope.lower()
    if scope not in ("organization", "user"):
        return failure("invalid_scope")
    client = CalendlyClient(session, coach_id)
    tok = await client._ensure_token()  # reuse token; assume contains needed scope
    headers = {"Authorization": f"Bearer {tok.token}", "Content-Type": "application/json"}
    body = {
        "url": url,
        "events": ["invitee.created", "invitee.canceled"],
        "scope": scope,
    }
    if scope == "organization":
        body["organization"] = org_or_user_uri
    else:
        body["user"] = org_or_user_uri
    async with httpx.AsyncClient(timeout=20.0) as client_http:
        resp = await client_http.post(f"{CAL_API}/webhook_subscriptions", headers=headers, json=body)
    if resp.status_code >= 400:
        logger.warning("Calendly create_subscription failed %s: %s", resp.status_code, resp.text[:200])
        return failure(f"http_{resp.status_code}")
    data = resp.json().get('resource') or resp.json()
    # Persist subscription + signing key on external account
    acct = (await session.execute(select(ExternalAccount).where(ExternalAccount.coach_id==coach_id, ExternalAccount.provider=='calendly'))).scalar_one_or_none()
    if acct:
        subs = dict(getattr(acct, 'external_refs', {}) or {})
        cal_subs = subs.get('calendly_subscriptions') or []
        cal_subs.append({
            'id': data.get('id') or data.get('uuid'),
            'state': data.get('state'),
            'url': data.get('url'),
        })
        subs['calendly_subscriptions'] = cal_subs
        if data.get('signing_key'):
            subs['calendly_signing_key'] = data.get('signing_key')
        acct.external_refs = subs
        await session.flush()
    return success({'subscription': data})

async def delete_subscription(session: AsyncSession, coach_id: int, subscription_id: str) -> Result[bool]:
    client = CalendlyClient(session, coach_id)
    tok = await client._ensure_token()
    headers = {"Authorization": f"Bearer {tok.token}"}
    async with httpx.AsyncClient(timeout=15.0) as client_http:
        resp = await client_http.delete(f"{CAL_API}/webhook_subscriptions/{subscription_id}", headers=headers)
    if resp.status_code in (204, 200, 202):
        # Remove from refs
        acct = (await session.execute(select(ExternalAccount).where(ExternalAccount.coach_id==coach_id, ExternalAccount.provider=='calendly'))).scalar_one_or_none()
        if acct and acct.external_refs:
            subs = dict(acct.external_refs)
            lst = subs.get('calendly_subscriptions') or []
            subs['calendly_subscriptions'] = [s for s in lst if s.get('id') != subscription_id]
            acct.external_refs = subs
            await session.flush()
        return success(True)
    if resp.status_code == 404:
        return failure('not_found')
    return failure(f"http_{resp.status_code}")

def _get_signing_key(acct: ExternalAccount) -> Optional[str]:
    if not acct or not acct.external_refs:
        return None
    return acct.external_refs.get('calendly_signing_key')

def verify_webhook_signature(signing_key: str | None, raw_body: bytes, provided: str | None) -> bool:
    if not signing_key:
        return True
    if not provided:
        return False
    # Header format: sha256=<hexdigest>
    try:
        algo, hexdigest = provided.split('=', 1)
    except ValueError:
        return False
    if algo.lower() != 'sha256':
        return False
    mac = hmac.new(signing_key.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, hexdigest)

async def handle_invitee_created(session: AsyncSession, coach_id: int, payload: Dict[str, Any]) -> Result[Dict[str, Any]]:
    event_uuid = payload.get('event', {}).get('uuid') if isinstance(payload.get('event'), dict) else payload.get('event_uuid')
    invitee_uuid = payload.get('invitee', {}).get('uuid') if isinstance(payload.get('invitee'), dict) else payload.get('invitee_uuid')
    if not event_uuid:
        return failure('no_event_uuid')
    return await upsert_calendly_event(session, coach_id, event_uuid, invitee_uuid)

async def handle_invitee_canceled(session: AsyncSession, coach_id: int, payload: Dict[str, Any]) -> Result[Dict[str, Any]]:
    # Mark meeting canceled if we can locate it by scheduled event uuid
    event_uuid = payload.get('event', {}).get('uuid') if isinstance(payload.get('event'), dict) else payload.get('event_uuid')
    if not event_uuid:
        return success({'canceled': True, 'meeting_found': False})
    from sqlalchemy import select
    from app.models_meeting_tracking import Meeting
    stmt = select(Meeting).where(Meeting.coach_id==coach_id, Meeting.external_refs['calendly_event_id'].astext==event_uuid)  # type: ignore
    m = (await session.execute(stmt)).scalar_one_or_none()
    if not m:
        return success({'canceled': True, 'meeting_found': False})
    prev = m.status
    m.status = 'canceled'
    await session.flush()
    return success({'canceled': True, 'meeting_found': True, 'previous_status': prev})

__all__ = [
    'create_subscription','delete_subscription','verify_webhook_signature','handle_invitee_created','handle_invitee_canceled'
]
