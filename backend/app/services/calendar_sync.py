"""Calendar / events ingestion helpers.

Functions:
 - list_events(coach_id, provider, time_min, time_max)
 - upsert_events_as_meetings(coach_id, provider, events)

Currently implemented provider: google (Calendar API events.list)
Extensible for others (zoom, calendly, fireflies) by adding branches.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_meeting_tracking import ExternalAccount, Meeting
from app.utils.crypto import fernet
from app.services.oauth import refresh_if_needed, OAuthError
from app.repositories.meeting_tracking import add_or_update_attendee, resolve_attendee

logger = logging.getLogger("calendar_sync")

GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

async def _get_external_account(session: AsyncSession, coach_id: int, provider: str) -> Optional[ExternalAccount]:
    stmt = select(ExternalAccount).where(ExternalAccount.coach_id == coach_id, ExternalAccount.provider == provider)
    return (await session.execute(stmt)).scalar_one_or_none()


def _parse_rfc3339(dt_str: str | None) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None

async def list_events(session: AsyncSession, coach_id: int, provider: str, time_min: datetime, time_max: datetime, page_size: int = 100) -> List[Dict[str, Any]]:
    provider = provider.lower()
    acct = await _get_external_account(session, coach_id, provider)
    if not acct or not acct.access_token_enc:
        return []
    f = fernet()
    try:
        access_token = f.decrypt(acct.access_token_enc.encode()).decode()
    except Exception:
        logger.warning("Failed to decrypt access token for account %s", getattr(acct, 'id', '?'))
        return []
    if acct.refresh_token_enc and acct.expires_at:
        try:
            refresh_plain = f.decrypt(acct.refresh_token_enc.encode()).decode()
            upd = refresh_if_needed(provider, refresh_plain, int(acct.expires_at.timestamp()))
            if upd:
                access_token = upd['access_token']
                acct.access_token_enc = f.encrypt(access_token.encode()).decode()
                if upd.get('refresh_token') and upd['refresh_token'] != refresh_plain:
                    acct.refresh_token_enc = f.encrypt(upd['refresh_token'].encode()).decode()
                import datetime as _dt
                acct.expires_at = _dt.datetime.utcfromtimestamp(upd['expires_at']).replace(tzinfo=_dt.timezone.utc)
                acct.scopes = upd.get('scopes') or acct.scopes
                await session.flush()
        except OAuthError as e:
            logger.warning("Token refresh failed for account %s: %s", getattr(acct, 'id', '?'), e)
    if provider == 'google':
        params = {
            'timeMin': time_min.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'timeMax': time_max.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'singleEvents': 'true',
            'orderBy': 'startTime',
            'maxResults': str(page_size),
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(GOOGLE_EVENTS_URL, params=params, headers=headers)
        if resp.status_code >= 400:
            logger.warning("Google events list failed %s: %s", resp.status_code, resp.text[:200])
            return []
        data = resp.json()
        return data.get('items', [])
    return []

async def upsert_events_as_meetings(session: AsyncSession, coach_id: int, provider: str, events: List[Dict[str, Any]]) -> int:
    provider = provider.lower()
    count = 0
    for ev in events:
        ext_id = ev.get('id')
        if not ext_id:
            continue
        started_at = _parse_rfc3339((ev.get('start') or {}).get('dateTime') or (ev.get('start') or {}).get('date'))
        ended_at = _parse_rfc3339((ev.get('end') or {}).get('dateTime') or (ev.get('end') or {}).get('date'))
        topic = ev.get('summary')
        join_url = ev.get('hangoutLink')
        conf = ev.get('conferenceData') or {}
        if not join_url and isinstance(conf, dict):
            eps = conf.get('entryPoints') or []
            if eps:
                join_url = eps[0].get('uri')
        stmt = select(Meeting).where(Meeting.coach_id == coach_id, Meeting.external_refs['google_event_id'].astext == ext_id)  # type: ignore
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.started_at = existing.started_at or started_at
            existing.ended_at = existing.ended_at or ended_at
            if topic and not existing.topic:
                existing.topic = topic
            if join_url and not existing.join_url:
                existing.join_url = join_url
            existing.external_refs = {**(existing.external_refs or {}), 'google_event_id': ext_id}
            meeting = existing
        else:
            meeting = Meeting(
                coach_id=coach_id,
                started_at=started_at,
                ended_at=ended_at,
                topic=topic,
                join_url=join_url,
                platform='google_calendar',
                external_refs={'google_event_id': ext_id},
            )
            session.add(meeting)
            await session.flush()
        await _process_event_attendees(session, coach_id, meeting, ev)
        count += 1
    return count

async def _process_event_attendees(session: AsyncSession, coach_id: int, meeting: Meeting, event: Dict[str, Any]):
    attendees = event.get('attendees') or []
    if not isinstance(attendees, list):
        return
    for att in attendees:
        if not isinstance(att, dict):
            continue
        email = att.get('email')
        display = att.get('displayName')
        if not email and not display:
            continue
        ma = await add_or_update_attendee(
            session,
            meeting_id=meeting.id,
            source='google',
            raw_email=email,
            raw_name=display,
        )
        await resolve_attendee(session, coach_id, ma)

__all__ = [
    'list_events', 'upsert_events_as_meetings'
]
