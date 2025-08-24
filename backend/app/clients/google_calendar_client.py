from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx
import logging

from .base import OAuthExternalClient

logger = logging.getLogger("google_client")

GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

@dataclass
class GoogleEventAttendee:
    email: Optional[str]
    display_name: Optional[str]

@dataclass
class GoogleEvent:
    id: str
    ical_uid: Optional[str]
    summary: Optional[str]
    start: Optional[datetime]
    end: Optional[datetime]
    hangout_link: Optional[str]
    attendees: List[GoogleEventAttendee]
    raw: Dict[str, Any]

class GoogleCalendarClient(OAuthExternalClient):
    def __init__(self, session, coach_id: int):
        super().__init__(session, coach_id, provider='google')

    async def list_events(self, time_min: datetime, time_max: datetime, page_size: int = 200) -> List[GoogleEvent]:
        tok = await self._ensure_token()
        params = {
            'timeMin': time_min.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'timeMax': time_max.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'singleEvents': 'true',  # expands recurring
            'orderBy': 'startTime',
            'maxResults': str(page_size),
        }
        headers = {"Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(GOOGLE_EVENTS_URL, params=params, headers=headers)
        if resp.status_code >= 400:
            logger.warning("Google list_events failed %s: %s", resp.status_code, resp.text[:200])
            return []
        items = resp.json().get('items', [])
        out: List[GoogleEvent] = []
        for ev in items:
            start = _parse_dt((ev.get('start') or {}).get('dateTime') or (ev.get('start') or {}).get('date'))
            end = _parse_dt((ev.get('end') or {}).get('dateTime') or (ev.get('end') or {}).get('date'))
            attendees_raw = ev.get('attendees') or []
            attendees = []
            if isinstance(attendees_raw, list):
                for a in attendees_raw:
                    if isinstance(a, dict):
                        attendees.append(GoogleEventAttendee(email=a.get('email'), display_name=a.get('displayName')))
            out.append(GoogleEvent(
                id=ev.get('id'),
                ical_uid=ev.get('iCalUID') or ev.get('icalUID') or ev.get('ical_uid'),
                summary=ev.get('summary'),
                start=start,
                end=end,
                hangout_link=ev.get('hangoutLink'),
                attendees=attendees,
                raw=ev,
            ))
        return out

def _parse_dt(val: str | None) -> Optional[datetime]:
    if not val:
        return None
    try:
        if val.endswith('Z'):
            val = val[:-1] + '+00:00'
        return datetime.fromisoformat(val)
    except Exception:
        return None
