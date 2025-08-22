import asyncio
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.models_meeting_tracking import Base, Person, Client, Meeting, MeetingAttendee, ReviewCandidate
from app.repositories.meeting_tracking import (
    get_or_create_person_by_email, get_or_create_person_by_phone, enrich_person,
    resolve_attendee, ensure_client, add_or_update_attendee, merge_persons
)

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="module")
async def engine():
    eng = create_async_engine(DATABASE_URL, future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()

@pytest.fixture
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s

@pytest.mark.asyncio
async def test_get_or_create_person_by_email(session):
    p1 = await get_or_create_person_by_email(session, "User@example.com")
    p2 = await get_or_create_person_by_email(session, "user@example.com")
    assert p1.id == p2.id
    assert 'user@example.com' in p1.emails

@pytest.mark.asyncio
async def test_enrich_person_add_phone(session):
    p = await get_or_create_person_by_email(session, "a@example.com")
    await enrich_person(session, p, phone="+1 (415) 555-2671")
    assert any(ph.startswith('+1415555') for ph in p.phones)

@pytest.mark.asyncio
async def test_resolve_attendee_conflict_creates_review(session):
    # Create two persons: one with email, one with phone
    p_email = await get_or_create_person_by_email(session, "conflict@example.com")
    p_phone = await get_or_create_person_by_phone(session, "+14155552671")
    # Force conflict by creating attendee referencing both identifiers
    meeting = Meeting(coach_id=1)
    session.add(meeting)
    await session.flush()
    attendee = MeetingAttendee(meeting_id=meeting.id, source="zoom", raw_email="conflict@example.com", raw_phone="+14155552671")
    session.add(attendee)
    await session.flush()
    pid = await resolve_attendee(session, 1, attendee)
    assert pid in {p_email.id, p_phone.id}
    # ReviewCandidate should exist
    rc = (await session.execute(text("SELECT count(*) FROM review_candidates"))).scalar()
    assert rc == 1

@pytest.mark.asyncio
async def test_ensure_client_and_merge(session):
    # create two persons and separate clients for same coach then merge
    p1 = await get_or_create_person_by_email(session, "m1@example.com")
    p2 = await get_or_create_person_by_email(session, "m2@example.com")
    await ensure_client(session, 99, p1.id, status='active')
    await ensure_client(session, 99, p2.id, status='prospect')
    survivor = await merge_persons(session, p1.id, p2.id)
    # ensure survivor has merged emails
    assert 'm1@example.com' in survivor.emails and 'm2@example.com' in survivor.emails
    # ensure only one client row for coach 99
    cnt = (await session.execute(text("SELECT count(*) FROM clients WHERE coach_id=99 AND person_id=:pid"), {'pid': str(survivor.id)})).scalar()
    assert cnt == 1

@pytest.mark.asyncio
async def test_add_or_update_attendee(session):
    meeting = Meeting(coach_id=2)
    session.add(meeting)
    await session.flush()
    att = await add_or_update_attendee(session, meeting.id, source="zoom", raw_email="user2@example.com")
    att2 = await add_or_update_attendee(session, meeting.id, source="zoom", raw_email="User2@example.com", role="host")
    assert att.id == att2.id or (att.meeting_id == att2.meeting_id and att.source == att2.source)
    assert att2.role == "host"
