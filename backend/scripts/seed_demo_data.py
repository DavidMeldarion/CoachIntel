"""Seed demo data for meeting tracking / identity resolution tests.

Creates:
  - One coach user (email: demo_coach@example.com)
  - Two persons & clients (one email-only, one phone-only)
  - One meeting with Google external_refs
  - Two attendees (email-only + phone-only) and runs identity resolution
Prints a concise summary at the end.

Usage (from backend directory with env configured):
  python -m scripts.seed_demo_data
or
  python scripts/seed_demo_data.py

Requires env vars for DB (ASYNC_DATABASE_URL / DATABASE_URL) already set.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.models import User
from app.models import AsyncSessionLocal, create_or_update_user
from app.models_meeting_tracking import Person, Client, Meeting, MeetingAttendee
from app.repositories.meeting_tracking import (
    get_or_create_person_by_email,
    get_or_create_person_by_phone,
    ensure_client,
    upsert_meeting,
    add_or_update_attendee,
    resolve_attendee,
)
from sqlalchemy import select

EMAIL_1 = "alice.client@example.com"
PHONE_2 = "+15551234567"  # US demo number
COACH_EMAIL = "demo_coach@example.com"
GOOGLE_EVENT_ID = "demo-google-event-1"


async def seed() -> None:
    # 1. Ensure coach user exists
    coach: User = await create_or_update_user(email=COACH_EMAIL, first_name="Demo", last_name="Coach", plan="plus")  # type: ignore
    coach_id = coach.id

    # 1a. Wipe any prior demo seed data for idempotency
    async with AsyncSessionLocal() as session:  # type: ignore
        force_wipe = ("DEMO_SEED_FORCE_WIPE" in __import__("os").environ)
        # Delete existing demo meeting(s)
        from sqlalchemy import delete
        demo_meetings = await session.execute(
            select(Meeting).where(
                Meeting.coach_id == coach_id,
                Meeting.external_refs['google_event_id'].astext == GOOGLE_EVENT_ID  # type: ignore
            )
        )
        demo_meetings = demo_meetings.scalars().all()
        if demo_meetings:
            await session.execute(
                Meeting.__table__.delete().where(Meeting.id.in_([m.id for m in demo_meetings]))
            )
        # Identify demo persons by primary identifiers
        person_rows = (await session.execute(
            select(Person).where(
                (Person.primary_email == EMAIL_1) | (Person.primary_phone == PHONE_2)
            )
        )).scalars().all()
        removed_person_ids = []
        for p in person_rows:
            # Remove client for this coach if it exists
            client_rows = (await session.execute(select(Client).where(Client.coach_id == coach_id, Client.person_id == p.id))).scalars().all()
            for c in client_rows:
                await session.execute(Client.__table__.delete().where(Client.id == c.id))
            # Safe person removal: only if no other clients or meeting attendances remain (unless force)
            other_client = (await session.execute(select(Client).where(Client.person_id == p.id))).first()
            attendance = (await session.execute(select(MeetingAttendee).where(MeetingAttendee.person_id == p.id))).first()
            if force_wipe or (not other_client and not attendance):
                await session.execute(Person.__table__.delete().where(Person.id == p.id))
                removed_person_ids.append(str(p.id))
        await session.commit()
        if demo_meetings or removed_person_ids:
            print(f"[wipe] Removed meetings={len(demo_meetings)} persons={len(removed_person_ids)} (force={force_wipe})")

    # 2. Work within a single session for meeting tracking entities to create fresh demo data
    async with AsyncSessionLocal() as session:  # type: ignore
        # Persons (email-only, phone-only)
        p1: Person = await get_or_create_person_by_email(session, EMAIL_1)
        p2: Optional[Person] = await get_or_create_person_by_phone(session, PHONE_2)
        assert p2 is not None, "Phone normalization failed for demo phone"

        # Ensure clients
        await ensure_client(session, coach_id, p1.id)
        await ensure_client(session, coach_id, p2.id)

        # 3. Upsert meeting
        meeting = await upsert_meeting(
            session,
            coach_id=coach_id,
            platform="google_calendar",
            external_refs={"google_event_id": GOOGLE_EVENT_ID},
            started_at=datetime.now(timezone.utc),
            topic="Demo Discovery Call",
            join_url="https://meet.google.com/demo-room",
        )

        # 4. Add attendees (raw only)
        att_email: MeetingAttendee = await add_or_update_attendee(
            session,
            meeting_id=meeting.id,
            source="google",
            raw_email=EMAIL_1,
            raw_name="Alice Client",
        )
        att_phone: MeetingAttendee = await add_or_update_attendee(
            session,
            meeting_id=meeting.id,
            source="google",
            raw_phone=PHONE_2,
            raw_name="Bob Prospect",
        )

        # 5. Identity resolution (should link to existing persons)
        pid1 = await resolve_attendee(session, coach_id, att_email)
        pid2 = await resolve_attendee(session, coach_id, att_phone)

        await session.commit()

    # Re-open to assemble summary (fresh objects)
    async with AsyncSessionLocal() as session:  # type: ignore
        meeting_row = (await session.execute(select(Meeting).where(Meeting.external_refs['google_event_id'].astext == GOOGLE_EVENT_ID))).scalar_one()  # type: ignore
        attendees = (await session.execute(select(MeetingAttendee).where(MeetingAttendee.meeting_id == meeting_row.id))).scalars().all()
        # Map person details
        person_ids = {a.person_id for a in attendees if a.person_id}
        persons = {}
        if person_ids:
            for p in (await session.execute(select(Person).where(Person.id.in_(list(person_ids))))).scalars().all():
                persons[p.id] = p
        # Clients
        client_rows = (await session.execute(select(Client).where(Client.coach_id == coach_id))).scalars().all()
        client_map = {c.person_id: c for c in client_rows}

    # Print summary
    print("\n=== Demo Seed Summary ===")
    print(f"Coach: id={coach_id} email={COACH_EMAIL}")
    print("Persons:")
    for pid, label in [(pid1, 'email-only'), (pid2, 'phone-only')]:
        p = persons.get(pid)
        if not p:
            continue
        print(f" - {label}: person_id={p.id} primary_email={p.primary_email} primary_phone={p.primary_phone} emails={p.emails} phones={p.phones}")
    print(f"Clients (coach scope): {len(client_map)} total")
    print(f"Meeting: id={meeting_row.id} topic={meeting_row.topic} external_refs={meeting_row.external_refs}")
    print("Attendees:")
    for a in attendees:
        p = persons.get(a.person_id) if a.person_id else None
        print(
            f" - source={a.source} raw_email={a.raw_email} raw_phone={a.raw_phone} raw_name={a.raw_name} "
            f"-> person_id={a.person_id} primary_email={getattr(p, 'primary_email', None)} primary_phone={getattr(p, 'primary_phone', None)}"
        )
    print("==========================\n")


def main():  # pragma: no cover
    asyncio.run(seed())


if __name__ == "__main__":  # pragma: no cover
    main()
