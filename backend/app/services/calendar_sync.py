"""Calendar / events ingestion helpers using typed external clients.

Public functions:
 - list_events(session, coach_id, provider, time_min, time_max)
 - upsert_events_as_meetings(session, coach_id, provider, events)

Currently implemented provider path delegates to `GoogleCalendarClient`.
Other providers (zoom, calendly, fireflies) can add analogous upsert logic.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_meeting_tracking import Meeting
from app.repositories.meeting_tracking import add_or_update_attendee, resolve_attendee
from app.clients.google_calendar_client import GoogleCalendarClient
from app.clients.zoom_client import ZoomClient
from app.clients.fireflies_client import FirefliesClient
from app.clients.calendly_client import CalendlyClient
from app.clients.result import Result, success, failure

logger = logging.getLogger("calendar_sync")

def _parse_rfc3339(dt_str: str | None) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        from datetime import datetime as _dt
        return _dt.fromisoformat(dt_str)
    except Exception:
        return None

async def list_events(session: AsyncSession, coach_id: int, provider: str, time_min: datetime, time_max: datetime, page_size: int = 100) -> Result[List[Dict[str, Any]]]:
    provider = provider.lower()
    if provider == 'google':
        try:
            client = GoogleCalendarClient(session, coach_id)
            events = await client.list_events(time_min, time_max, page_size)
            # Convert typed events back to dict for backward compatibility
            items: List[Dict[str, Any]] = []
            for ev in events:
                items.append(ev.raw)
            return success(items)
        except Exception as e:  # pragma: no cover
            logger.warning("Google list_events error coach=%s: %s", coach_id, e)
            return failure(str(e))
    return failure(f"Provider {provider} not implemented")

async def upsert_events_as_meetings(session: AsyncSession, coach_id: int, provider: str, events: List[Dict[str, Any]]) -> int:
    provider = provider.lower()
    count = 0
    # Lazy import to avoid circular dependency (main -> worker -> this)
    from app.main import log_meeting_upserted, set_log_coach
    set_log_coach(coach_id)
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
        created = False
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
            created = True
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
        log_meeting_upserted(str(meeting.id), coach_id, 'google_calendar', created=created)
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

async def upsert_zoom_meeting(session: AsyncSession, coach_id: int, meeting_id: str) -> Result[Dict[str, Any]]:
    """Fetch a Zoom meeting + participants and upsert into tracking tables.

    Returns Result with summary counts.
    """
    client = ZoomClient(session, coach_id)
    from app.main import log_meeting_upserted, set_log_coach
    set_log_coach(coach_id)
    try:
        meeting_raw = await client.get_meeting(meeting_id)
        if not meeting_raw:
            return failure("not_found", status_code=404)
        # Parse fields
        start = _parse_rfc3339(meeting_raw.get('start_time'))
        dur_min = meeting_raw.get('duration')
        end = None
        if start and isinstance(dur_min, (int, float)):
            from datetime import timedelta
            end = start + timedelta(minutes=int(dur_min))
        topic = meeting_raw.get('topic')
        join_url = meeting_raw.get('join_url')
        # Locate existing meeting
        stmt = select(Meeting).where(
            Meeting.coach_id == coach_id,
            Meeting.external_refs['zoom_meeting_id'].astext == str(meeting_id)  # type: ignore
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        created = False
        if existing:
            m = existing
            if start and (not m.started_at or start < m.started_at):
                m.started_at = start
            if end and (not m.ended_at or end > m.ended_at):
                m.ended_at = end
            if topic and not m.topic:
                m.topic = topic
            if join_url and not m.join_url:
                m.join_url = join_url
            refs = dict(m.external_refs or {})
            refs.setdefault('zoom_meeting_id', str(meeting_id))
            m.external_refs = refs
        else:
            created = True
            m = Meeting(
                coach_id=coach_id,
                started_at=start,
                ended_at=end,
                topic=topic,
                join_url=join_url,
                platform='zoom',
                external_refs={'zoom_meeting_id': str(meeting_id)},
            )
            session.add(m)
            await session.flush()
        log_meeting_upserted(str(m.id), coach_id, 'zoom', created=created)
        # Participants
        participants = await client.list_meeting_participants(meeting_id)
        added = 0
        for p in participants:
            ident_email = p.email
            display = p.name
            if not (ident_email or display):
                continue
            att = await add_or_update_attendee(
                session,
                meeting_id=m.id,
                source='zoom',
                raw_email=ident_email,
                raw_name=display,
            )
            await resolve_attendee(session, coach_id, att)
            added += 1
        return success({"meeting_id": str(m.id), "participants": added})
    except Exception as e:  # pragma: no cover
        logger.warning("upsert_zoom_meeting error coach=%s meeting=%s: %s", coach_id, meeting_id, e)
        return failure(str(e))


async def upsert_fireflies_meetings(session: AsyncSession, coach_id: int, limit: int = 25) -> Result[Dict[str, Any]]:
    """List recent Fireflies meetings and upsert them with participants."""
    client = FirefliesClient(session, coach_id)
    from app.main import log_meeting_upserted, set_log_coach
    set_log_coach(coach_id)
    try:
        summaries = await client.list_meetings(limit=limit)
        count = 0
        part_total = 0
        for summ in summaries:
            start = _parse_rfc3339(summ.date)
            end = None
            if start and summ.duration:
                from datetime import timedelta
                end = start + timedelta(seconds=int(summ.duration))
            stmt = select(Meeting).where(
                Meeting.coach_id == coach_id,
                Meeting.external_refs['fireflies_meeting_id'].astext == str(summ.id)  # type: ignore
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            created = False
            if existing:
                m = existing
                if start and (not m.started_at or start < m.started_at):
                    m.started_at = start
                if end and (not m.ended_at or end > m.ended_at):
                    m.ended_at = end
                if summ.title and not m.topic:
                    m.topic = summ.title
                if summ.meeting_link and not m.join_url:
                    m.join_url = summ.meeting_link
                refs = dict(m.external_refs or {})
                refs.setdefault('fireflies_meeting_id', summ.id)
                m.external_refs = refs
            else:
                created = True
                m = Meeting(
                    coach_id=coach_id,
                    started_at=start,
                    ended_at=end,
                    topic=summ.title,
                    join_url=summ.meeting_link,
                    platform='fireflies',
                    external_refs={'fireflies_meeting_id': summ.id},
                )
                session.add(m)
                await session.flush()
            log_meeting_upserted(str(m.id), coach_id, 'fireflies', created=created)
            # participants
            for p in summ.participants:
                if not (p.email or p.name):
                    continue
                att = await add_or_update_attendee(
                    session,
                    meeting_id=m.id,
                    source='fireflies',
                    raw_email=p.email,
                    raw_name=p.name,
                )
                await resolve_attendee(session, coach_id, att)
                part_total += 1
            count += 1
        return success({"meetings": count, "participants": part_total})
    except Exception as e:  # pragma: no cover
        logger.warning("upsert_fireflies_meetings error coach=%s: %s", coach_id, e)
        return failure(str(e))


async def upsert_calendly_event(session: AsyncSession, coach_id: int, event_uuid: str, invitee_uuid: str | None = None) -> Result[Dict[str, Any]]:
    """Fetch Calendly scheduled event + invitee (if provided) and upsert.

    If invitee_uuid not provided, attempts to resolve from event payload (not implemented here).
    """
    client = CalendlyClient(session, coach_id)
    from app.main import log_meeting_upserted, set_log_coach
    set_log_coach(coach_id)
    try:
        event = await client.get_scheduled_event(event_uuid)
        if not event:
            return failure("event_not_found", status_code=404)
        invitee = None
        if invitee_uuid:
            invitee = await client.get_invitee(invitee_uuid)
        start = _parse_rfc3339(event.start_time)
        end = _parse_rfc3339(event.end_time)
        stmt = select(Meeting).where(
            Meeting.coach_id == coach_id,
            Meeting.external_refs['calendly_event_uri'].astext == event.uri  # type: ignore
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        created = False
        if existing:
            m = existing
            if start and (not m.started_at or start < m.started_at):
                m.started_at = start
            if end and (not m.ended_at or end > m.ended_at):
                m.ended_at = end
            if event.name and not m.topic:
                m.topic = event.name
            refs = dict(m.external_refs or {})
            refs.setdefault('calendly_event_uri', event.uri)
            if invitee and invitee.uuid:
                refs.setdefault('calendly_invitee_uuid', invitee.uuid)
            m.external_refs = refs
        else:
            created = True
            refs = {'calendly_event_uri': event.uri}
            if invitee and invitee.uuid:
                refs['calendly_invitee_uuid'] = invitee.uuid
            m = Meeting(
                coach_id=coach_id,
                started_at=start,
                ended_at=end,
                topic=event.name,
                join_url=event.location,
                platform='calendly',
                external_refs=refs,
            )
            session.add(m)
            await session.flush()
        log_meeting_upserted(str(m.id), coach_id, 'calendly', created=created)
        added = 0
        if invitee:
            att = await add_or_update_attendee(
                session,
                meeting_id=m.id,
                source='calendly',
                raw_email=invitee.email,
                raw_name=invitee.name,
            )
            await resolve_attendee(session, coach_id, att)
            added += 1
        return success({"meeting_id": str(m.id), "attendees": added})
    except Exception as e:  # pragma: no cover
        logger.warning("upsert_calendly_event error coach=%s event=%s: %s", coach_id, event_uuid, e)
        return failure(str(e))


__all__ = [
    'list_events', 'upsert_events_as_meetings',
    'upsert_zoom_meeting', 'upsert_fireflies_meetings', 'upsert_calendly_event'
]
