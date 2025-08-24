"""Zoom participant retrieval & persistence utilities.

Implements:
 - get_past_participants(meeting_uuid)
 - list_ended_instances(meeting_id)
 - upsert_zoom_participants(user_id, meeting_uuid, participants)
 - verify_and_handle_webhook(request) (skeleton)

Relies on existing OAuth token storage in ExternalAccount.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import httpx, logging, urllib.parse, hmac, hashlib, time, json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_meeting_tracking import ExternalAccount, Meeting
from app.repositories.meeting_tracking import add_or_update_attendee, resolve_attendee
from app.clients.base import fetch_account
from app.utils.crypto import fernet
from app.services.oauth import refresh_if_needed, OAuthError

logger = logging.getLogger("zoom_participants")

ZOOM_API = "https://api.zoom.us/v2"

class ZoomAPIError(RuntimeError):
    pass

def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

async def _ensure_access_token(session: AsyncSession, coach_id: int):
    acct = await fetch_account(session, coach_id, 'zoom')
    if not acct or not acct.access_token_enc:
        raise ZoomAPIError("No zoom external account")
    f = fernet()
    access = f.decrypt(acct.access_token_enc.encode()).decode()
    if acct.refresh_token_enc and acct.expires_at:
        try:
            upd = refresh_if_needed('zoom', f.decrypt(acct.refresh_token_enc.encode()).decode(), int(acct.expires_at.timestamp()))
            if upd:
                access = upd['access_token']
                acct.access_token_enc = f.encrypt(access.encode()).decode()
                if upd.get('refresh_token'):
                    acct.refresh_token_enc = f.encrypt(upd['refresh_token'].encode()).decode()
                    acct.expires_at = datetime.utcfromtimestamp(upd['expires_at'])
                    await session.flush()
        except OAuthError as e:  # pragma: no cover
            logger.warning("Zoom token refresh failed coach=%s: %s", coach_id, e)
    return access, acct

def _double_encode_uuid(uuid_str: str) -> str:
    if '/' in uuid_str:
        return urllib.parse.quote(urllib.parse.quote(uuid_str, safe=''), safe='')
    return urllib.parse.quote(uuid_str, safe='')

async def list_ended_instances(session: AsyncSession, coach_id: int, meeting_id: str) -> List[dict]:
    token, _ = await _ensure_access_token(session, coach_id)
    url = f"{ZOOM_API}/past_meetings/{meeting_id}/instances"
    headers = _auth_headers(token)
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code == 404:
        return []
    if resp.status_code >= 400:
        logger.warning("Zoom instances failed %s %s", resp.status_code, resp.text[:160])
        return []
    data = resp.json()
    inst = data.get('meetings') or data.get('instances') or []
    if not isinstance(inst, list):
        return []
    return [i for i in inst if isinstance(i, dict)]

async def get_past_participants(session: AsyncSession, coach_id: int, meeting_uuid: str) -> List[dict]:
    token, _ = await _ensure_access_token(session, coach_id)
    enc_uuid = _double_encode_uuid(meeting_uuid)
    url = f"{ZOOM_API}/past_meetings/{enc_uuid}/participants"
    headers = _auth_headers(token)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return []
        if resp.status_code >= 400:
            if '/' in meeting_uuid and meeting_uuid.count('%') < 2:
                enc_uuid = _double_encode_uuid(meeting_uuid)
                resp = await client.get(f"{ZOOM_API}/past_meetings/{enc_uuid}/participants", headers=headers)
            if resp.status_code >= 400:
                logger.warning("Zoom past participants failed %s %s", resp.status_code, resp.text[:160])
                return []
        data = resp.json()
    parts = data.get('participants') or []
    if not isinstance(parts, list):
        return []
    return [p for p in parts if isinstance(p, dict)]

async def upsert_zoom_participants(session: AsyncSession, coach_id: int, meeting_uuid: str, participants: List[dict]) -> int:
    stmt = select(Meeting).where(Meeting.coach_id == coach_id, Meeting.external_refs['zoom_meeting_uuid'].astext == meeting_uuid)  # type: ignore
    meeting = (await session.execute(stmt)).scalar_one_or_none()
    if not meeting:
        return 0
    added = 0
    for p in participants:
        name = p.get('name') or p.get('user_name')
        email = p.get('user_email')
        jt = _parse_dt(p.get('join_time'))
        lt = _parse_dt(p.get('leave_time'))
        dur = None
        if jt and lt:
            dur = int((lt - jt).total_seconds())
        att = await add_or_update_attendee(
            session,
            meeting_id=meeting.id,
            source='zoom',
            raw_email=email,
            raw_name=name,
            role=p.get('status'),
        )
        changed = False
        if jt and (not getattr(att, 'join_time', None) or jt < att.join_time):
            att.join_time = jt; changed = True
        if lt and (not getattr(att, 'leave_time', None) or lt > att.leave_time):
            att.leave_time = lt; changed = True
        if dur and not getattr(att, 'duration_seconds', None):
            att.duration_seconds = dur; changed = True
        if changed:
            await session.flush()
        await resolve_attendee(session, coach_id, att)
        added += 1
    return added

def _parse_dt(val: str | None) -> Optional[datetime]:
    if not val: return None
    try:
        if val.endswith('Z'): val = val[:-1] + '+00:00'
        return datetime.fromisoformat(val)
    except Exception:
        return None

# Webhook validation skeleton

def verify_and_handle_webhook(secret: str, raw_body: bytes, headers: dict) -> dict:
    try:
        body = json.loads(raw_body.decode())
    except Exception:
        return {"error": "invalid_json"}
    event = body.get('event')
    if event == 'endpoint.url_validation':
        plain = body.get('payload', {}).get('plainToken')
        if not plain: return {"error": "missing_plain_token"}
        mac = hmac.new(secret.encode(), plain.encode(), hashlib.sha256).hexdigest()
        return {"plainToken": plain, "encryptedToken": mac}
    return {"received": True, "event": event}

__all__ = ['get_past_participants','list_ended_instances','upsert_zoom_participants','verify_and_handle_webhook']
