import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.models_meeting_tracking import Person, Client, Meeting, MeetingAttendee

# Simple factory helpers (avoid external deps) for tests

def person_factory(email: Optional[str] = None, phone: Optional[str] = None) -> Person:
    return Person(
        primary_email=email.lower() if email else None,
        primary_phone=phone,
        emails=[email.lower()] if email else [],
        phones=[phone] if phone else [],
        email_hashes=[],
        phone_hashes=[],
    )

def meeting_factory(coach_id: int = 1, started: Optional[datetime] = None, duration_min: int = 30, platform: str = 'zoom') -> Meeting:
    started = started or datetime.now(timezone.utc)
    return Meeting(
        coach_id=coach_id,
        started_at=started,
        ended_at=started + timedelta(minutes=duration_min),
        platform=platform,
        external_refs={},
    )

def attendee_factory(meeting_id, source: str = 'zoom', email: Optional[str] = None, name: Optional[str] = None) -> MeetingAttendee:
    return MeetingAttendee(
        meeting_id=meeting_id,
        source=source,
        raw_email=email.lower() if email else None,
        raw_name=name,
    )

def client_factory(coach_id: int, person_id) -> Client:
    return Client(coach_id=coach_id, person_id=person_id, status='prospect')
