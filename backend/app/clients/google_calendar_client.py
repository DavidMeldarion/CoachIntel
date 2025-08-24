from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import httpx
import logging

from .base import OAuthExternalClient

logger = logging.getLogger("google_client")

BASE_CAL_URL = "https://www.googleapis.com/calendar/v3/calendars"
GOOGLE_EVENTS_URL = f"{BASE_CAL_URL}/primary/events"
WATCH_URL_SUFFIX = "events/watch"
CHANNELS_STOP_URL = "https://www.googleapis.com/calendar/v3/channels/stop"

@dataclass
class GoogleEventAttendee:
    email: Optional[str]
    display_name: Optional[str]
    response_status: Optional[str] = None

@dataclass
class GoogleEvent:
    id: str
    ical_uid: Optional[str]
    summary: Optional[str]
    start: Optional[datetime]
    end: Optional[datetime]
    hangout_link: Optional[str]
    attendees: List[GoogleEventAttendee]
    organizer_email: Optional[str]
    raw: Dict[str, Any]

class GoogleCalendarClient(OAuthExternalClient):
    def __init__(self, session, coach_id: int):
        super().__init__(session, coach_id, provider='google')

    async def list_events(self, time_min: datetime, time_max: datetime, page_size: int = 200) -> List[GoogleEvent]:
        events, _next_sync, _ = await self.incremental_sync(time_min=time_min, time_max=time_max, page_size=page_size)
        return events

    async def incremental_sync(
        self,
        time_min: datetime,
        time_max: datetime,
        page_size: int = 250,
        sync_token: Optional[str] = None,
        page_token: Optional[str] = None,
    ) -> Tuple[List[GoogleEvent], Optional[str], Optional[str]]:
        """Perform an incremental sync.

        Returns (events, nextSyncToken, nextPageToken).
        If a 410 GONE is received, caller should reset stored sync token and retry full sync.
        """
        tok = await self._ensure_token()
        params: Dict[str, Any] = {
            'singleEvents': 'true',
            'maxResults': str(page_size),
            'showDeleted': 'false',
        }
        if sync_token:
            params['syncToken'] = sync_token
        else:
            params['timeMin'] = time_min.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            params['timeMax'] = time_max.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            params['orderBy'] = 'startTime'
        if page_token:
            params['pageToken'] = page_token
        headers = {"Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(GOOGLE_EVENTS_URL, params=params, headers=headers)
        if resp.status_code == 410:
            # sync token invalid -> caller must clear
            raise InvalidSyncToken("Sync token invalid (410)")
        if resp.status_code >= 500:
            # simple backoff + retry once
            await _sleep_backoff()
            async with httpx.AsyncClient(timeout=30.0) as client:
                retry = await client.get(GOOGLE_EVENTS_URL, params=params, headers=headers)
            if retry.status_code >= 400:
                logger.warning("Google incremental_sync failed %s: %s", retry.status_code, retry.text[:200])
                return [], None, None
            resp = retry
        elif resp.status_code >= 400:
            logger.warning("Google incremental_sync failed %s: %s", resp.status_code, resp.text[:200])
            return [], None, None
        payload = resp.json()
        items = payload.get('items', [])
        out: List[GoogleEvent] = []
        for ev in items:
            start = _parse_dt((ev.get('start') or {}).get('dateTime') or (ev.get('start') or {}).get('date'))
            end = _parse_dt((ev.get('end') or {}).get('dateTime') or (ev.get('end') or {}).get('date'))
            attendees_raw = ev.get('attendees') or []
            attendees: List[GoogleEventAttendee] = []
            if isinstance(attendees_raw, list):
                for a in attendees_raw:
                    if isinstance(a, dict):
                        attendees.append(GoogleEventAttendee(email=a.get('email'), display_name=a.get('displayName'), response_status=a.get('responseStatus')))
            out.append(GoogleEvent(
                id=ev.get('id'),
                ical_uid=ev.get('iCalUID') or ev.get('icalUID') or ev.get('ical_uid'),
                summary=ev.get('summary'),
                start=start,
                end=end,
                hangout_link=ev.get('hangoutLink'),
                attendees=attendees,
                organizer_email=(ev.get('organizer') or {}).get('email'),
                raw=ev,
            ))
        return out, payload.get('nextSyncToken'), payload.get('nextPageToken')

    async def start_watch(self, webhook_address: str, channel_id: str, token: Optional[str] = None) -> Dict[str, Any]:
        tok = await self._ensure_token()
        body = {
            'id': channel_id,
            'type': 'web_hook',
            'address': webhook_address,
        }
        if token:
            body['token'] = token
        headers = {"Authorization": f"Bearer {tok.token}", 'Content-Type': 'application/json'}
        url = f"{BASE_CAL_URL}/primary/{WATCH_URL_SUFFIX}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=body, headers=headers)
        if resp.status_code >= 400:
            raise WatchError(f"Failed to start watch: {resp.status_code} {resp.text[:200]}")
        return resp.json()

    async def stop_watch(self, channel_id: str, resource_id: str):
        tok = await self._ensure_token()
        body = {"id": channel_id, "resourceId": resource_id}
        headers = {"Authorization": f"Bearer {tok.token}", 'Content-Type': 'application/json'}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(CHANNELS_STOP_URL, json=body, headers=headers)
        if resp.status_code >= 400:
            raise WatchError(f"Failed to stop watch: {resp.status_code} {resp.text[:200]}")

class InvalidSyncToken(Exception):
    pass

class WatchError(Exception):
    pass

def _parse_dt(val: str | None) -> Optional[datetime]:
    if not val:
        return None
    try:
        if val.endswith('Z'):
            val = val[:-1] + '+00:00'
        return datetime.fromisoformat(val)
    except Exception:
        return None

async def _sleep_backoff():
    # simple deterministic backoff (could be random) for retry
    import asyncio
    await asyncio.sleep(1.0)
