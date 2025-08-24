import pytest, respx, httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy import insert
from app.models_meeting_tracking import ExternalAccount
from app.clients.google_calendar_client import GoogleCalendarClient
from app.utils.crypto import fernet

@pytest.mark.asyncio
async def test_google_list_events(db_session):
    # Seed ExternalAccount with access token
    f = fernet()
    token = f.encrypt(b"tok123").decode()
    acct = ExternalAccount(coach_id=1, provider='google', access_token_enc=token, scopes=['cal.events'])
    db_session.add(acct)
    await db_session.flush()

    client = GoogleCalendarClient(db_session, coach_id=1)

    start = datetime.now(timezone.utc) - timedelta(days=1)
    end = datetime.now(timezone.utc) + timedelta(days=1)

    route = respx.get("https://www.googleapis.com/calendar/v3/calendars/primary/events").mock(
        return_value=httpx.Response(200, json={"items": [
            {"id":"evt1","iCalUID":"abc123","summary":"Call","start":{"dateTime":start.isoformat()},"end":{"dateTime":end.isoformat()},"hangoutLink":"https://meet.google.com/xyz","attendees":[{"email":"a@example.com","displayName":"A"}]}
        ]})
    )
    events = await client.list_events(start, end)
    assert route.called
    assert len(events) == 1
    evt = events[0]
    assert evt.ical_uid == 'abc123'
    assert evt.attendees and evt.attendees[0].email == 'a@example.com'
