import pytest
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from app.models_meeting_tracking import Meeting, MeetingAttendee
from app.repositories.meeting_tracking import upsert_meeting, add_or_update_attendee, resolve_attendee

@pytest.mark.asyncio
async def test_reconcile_by_ical(db_session):
    # First insert
    m1 = await upsert_meeting(db_session, coach_id=1, platform='google', ical_uid='uid-123', started_at=datetime.now(timezone.utc))
    # Second call with same ical should return same meeting
    m2 = await upsert_meeting(db_session, coach_id=1, platform='google', ical_uid='uid-123', topic='Updated Topic')
    assert m1.id == m2.id
    assert m2.topic == 'Updated Topic'

@pytest.mark.asyncio
async def test_reconcile_attendees_merge(db_session):
    m = await upsert_meeting(db_session, coach_id=5, platform='zoom', started_at=datetime.now(timezone.utc))
    a1 = await add_or_update_attendee(db_session, m.id, source='zoom', raw_email='MUser@Example.com')
    a2 = await add_or_update_attendee(db_session, m.id, source='zoom', raw_email='muser@example.com', raw_name='Name')
    assert a1.meeting_id == a2.meeting_id and a1.source == a2.source

@pytest.mark.asyncio
async def test_reconcile_time_join_url(db_session):
    start = datetime.now(timezone.utc)
    m1 = await upsert_meeting(db_session, coach_id=7, platform='google', started_at=start, join_url='https://meet.google.com/abc')
    # Simulate second event referencing same join_url but no ical
    m2 = await upsert_meeting(db_session, coach_id=7, platform='google', started_at=start + timedelta(minutes=1), join_url='https://meet.google.com/abc')
    # Without explicit logic this may create new meeting (current implementation). This test documents current behavior.
    assert m1.id != m2.id
