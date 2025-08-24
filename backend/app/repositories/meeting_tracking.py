"""Async repository functions for meeting tracking models.

Design goals:
- Idempotent operations (safe to call repeatedly).
- Prefer single round-trip UPSERT patterns (INSERT .. ON CONFLICT DO UPDATE) when feasible.
- Fallback to SELECT+UPDATE only when conditional merge logic required.
- All functions assume an external AsyncSession is passed (no implicit session creation) to allow
  transaction scoping by caller (e.g., API handler or background task).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, literal, case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_meeting_tracking import (
    Person, Client, Meeting, MeetingAttendee, ReviewCandidate
)
from app.utils.crypto import hash_email, hash_phone, e164
from app.logging import (
    set_log_coach as _set_coach_context,
    log_meeting_upserted as _log_meeting_upserted,
    log_attendee_resolved as _log_attendee_resolved,
)


# ---------------------------------------------------------------------------
# Person helpers
# ---------------------------------------------------------------------------
async def get_or_create_person_by_email(session: AsyncSession, email: str) -> Person:
    """Idempotently ensure a Person exists containing the email.

    - Matches by email hash (case-insensitive email).
    - Adds email to arrays if new; also stores hash.
    """
    norm = email.strip().lower()
    h = hash_email(norm)

    # First try to find by hash (GIN index)
    stmt = select(Person).where(func.array_position(Person.email_hashes, h) != None)  # noqa: E711
    res = await session.execute(stmt)
    person = res.scalar_one_or_none()
    if person:
        # ensure email present
        changed = False
        existing_emails_lower = {e.lower(): e for e in (person.emails or [])}
        if norm not in existing_emails_lower:
            person.emails = list(person.emails or []) + [norm]
            changed = True
        if h not in (person.email_hashes or []):
            person.email_hashes = list(person.email_hashes or []) + [h]
            changed = True
        if person.primary_email is None:
            person.primary_email = norm
            changed = True
        if changed:
            await session.flush()
        return person

    # Not found: create
    person = Person(primary_email=norm, emails=[norm], email_hashes=[h])
    session.add(person)
    await session.flush()
    return person


async def get_or_create_person_by_phone(session: AsyncSession, phone: str) -> Optional[Person]:
    norm = e164(phone)
    if not norm:
        return None
    # naive search in array - could add GIN index on phones normalized later
    stmt = select(Person).where(func.array_position(Person.phones, norm) != None)  # noqa: E711
    res = await session.execute(stmt)
    person = res.scalar_one_or_none()
    if person:
        if norm not in (person.phones or []):
            person.phones = list(person.phones or []) + [norm]
            await session.flush()
        if person.primary_phone is None:
            person.primary_phone = norm
            await session.flush()
        return person
    # create
    person = Person(primary_phone=norm, phones=[norm])
    session.add(person)
    await session.flush()
    return person


async def add_email_to_person(session: AsyncSession, person_id: UUID, email: str) -> Person:
    norm = email.strip().lower()
    h = hash_email(norm)
    person = (await session.execute(select(Person).where(Person.id == person_id))).scalar_one()
    changed = False
    existing_emails_lower = {e.lower(): e for e in (person.emails or [])}
    if norm not in existing_emails_lower:
        person.emails = list(person.emails or []) + [norm]
        changed = True
    if h not in (person.email_hashes or []):
        person.email_hashes = list(person.email_hashes or []) + [h]
        changed = True
    if person.primary_email is None:
        person.primary_email = norm
        changed = True
    if changed:
        await session.flush()
    return person


async def add_phone_to_person(session: AsyncSession, person_id: UUID, phone: str) -> Optional[Person]:
    norm = e164(phone)
    if not norm:
        return None
    person = (await session.execute(select(Person).where(Person.id == person_id))).scalar_one()
    changed = False
    if norm not in (person.phones or []):
        person.phones = list(person.phones or []) + [norm]
        changed = True
    if person.primary_phone is None:
        person.primary_phone = norm
        changed = True
    if changed:
        await session.flush()
    return person


async def get_person_by_hash(session: AsyncSession, email_or_phone_hash: str) -> Optional[Person]:
    stmt = select(Person).where(
        (func.array_position(Person.email_hashes, email_or_phone_hash) != None) |  # noqa: E711
        (func.array_position(Person.phone_hashes, email_or_phone_hash) != None)  # noqa: E711
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Identity enrichment helper
# ---------------------------------------------------------------------------
async def enrich_person(session: AsyncSession, person: Person, email: Optional[str] = None, phone: Optional[str] = None) -> Person:
    """Append new identifiers (email / phone) and their hashes safely.
    Flush only if changes applied.
    """
    changed = False
    if email:
        norm = email.strip().lower()
        h = hash_email(norm)
        emails_lower = {e.lower() for e in (person.emails or [])}
        if norm not in emails_lower:
            person.emails = list(person.emails or []) + [norm]
            changed = True
        if h not in (person.email_hashes or []):
            person.email_hashes = list(person.email_hashes or []) + [h]
            changed = True
        if person.primary_email is None:
            person.primary_email = norm
            changed = True
    if phone:
        norm_phone = e164(phone)
        if norm_phone:
            if norm_phone not in (person.phones or []):
                person.phones = list(person.phones or []) + [norm_phone]
                changed = True
            hph = hash_phone(norm_phone)
            if hph and hph not in (person.phone_hashes or []):
                person.phone_hashes = list(person.phone_hashes or []) + [hph]
                changed = True
            if person.primary_phone is None:
                person.primary_phone = norm_phone
                changed = True
    if changed:
        await session.flush()
    return person


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
async def ensure_client(session: AsyncSession, coach_id: int, person_id: UUID, status: str = 'prospect') -> Client:
    # Try insert; on conflict update status if different (simple rule: upgrade/downgrade to provided status)
    ins = insert(Client).values(coach_id=coach_id, person_id=person_id, status=status)
    stmt = ins.on_conflict_do_update(
        index_elements=[Client.coach_id, Client.person_id],
        set_={"status": status}
    ).returning(Client)
    res = await session.execute(stmt)
    client = res.scalar_one()
    return client


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------
async def resolve_attendee(session: AsyncSession, coach_id: int, attendee: MeetingAttendee) -> UUID:
    """Resolve or create a Person for a meeting attendee.

    Algorithm:
    1. If raw_email -> hash lookup; else if raw_phone -> hash lookup.
    2. If both map to different persons, prefer one already a Client of coach (else TODO: review candidate; choose email one).
    3. If none found: create new Person with primary data and hashes.
    4. ensure_client(coach_id, person_id)
    Return person_id.
    """
    email_norm = attendee.raw_email.lower().strip() if attendee.raw_email else None
    phone_norm = e164(attendee.raw_phone) if attendee.raw_phone else None

    email_person = None
    phone_person = None

    if email_norm:
        h_email = hash_email(email_norm)
        email_person = await get_person_by_hash(session, h_email)
    if phone_norm:
        h_phone = hash_phone(phone_norm)  # already normalized
        if h_phone:
            phone_person = await get_person_by_hash(session, h_phone)

    chosen: Optional[Person] = None
    if email_person and phone_person and email_person.id != phone_person.id:
        # conflict: prefer existing client link; else record review candidate then pick email_person
        ec_stmt = select(Client).where(Client.coach_id == coach_id, Client.person_id == email_person.id)
        pc_stmt = select(Client).where(Client.coach_id == coach_id, Client.person_id == phone_person.id)
        email_is_client = (await session.execute(ec_stmt)).first() is not None
        phone_is_client = (await session.execute(pc_stmt)).first() is not None
        if email_is_client and not phone_is_client:
            chosen = email_person
        elif phone_is_client and not email_is_client:
            chosen = phone_person
        else:
            # record review candidate (ordered pair to avoid mirror duplicates)
            a_id, b_id = sorted([email_person.id, phone_person.id], key=lambda x: str(x))
            # check existing
            existing_rc = await session.execute(
                select(ReviewCandidate).where(
                    ReviewCandidate.coach_id == coach_id,
                    ReviewCandidate.person_a_id == a_id,
                    ReviewCandidate.person_b_id == b_id,
                    ReviewCandidate.meeting_id == attendee.meeting_id,
                )
            )
            if not existing_rc.scalar_one_or_none():
                session.add(ReviewCandidate(
                    coach_id=coach_id,
                    person_a_id=a_id,
                    person_b_id=b_id,
                    meeting_id=attendee.meeting_id,
                    source=attendee.source,
                    reason="email_phone_conflict"
                ))
            chosen = email_person  # deterministic default
    else:
        chosen = email_person or phone_person

    if not chosen:
        # create new
        chosen = Person(
            primary_email=email_norm,
            primary_phone=phone_norm,
            emails=[email_norm] if email_norm else [],
            email_hashes=[hash_email(email_norm)] if email_norm else [],
            phones=[phone_norm] if phone_norm else [],
            phone_hashes=[hash_phone(phone_norm)] if phone_norm else [],
        )
        session.add(chosen)
        await session.flush()
    else:
        # enrich with missing identifiers
        await enrich_person(session, chosen, email=email_norm, phone=phone_norm)

    # ensure client linkage
    await ensure_client(session, coach_id, chosen.id)
    _log_attendee_resolved(attendee.raw_email, str(chosen.id) if chosen else None, matched=chosen is not None)
    return chosen.id


# ---------------------------------------------------------------------------
# Merge persons
# ---------------------------------------------------------------------------
async def merge_persons(session: AsyncSession, survivor_id: UUID, mergee_id: UUID) -> Person:
    """Atomically merge two Person records.

    - survivor retains identity; mergee data folded in.
    - emails/phones/hashes unioned (dedup, case-insensitive for emails).
    - meeting_attendees + clients moved to survivor.
    - review_candidates updated to point to survivor (and de-dup self-pairs) / marked resolved.
    - mergee row deleted.
    Caller must commit surrounding transaction; this function flushes only.
    """
    if survivor_id == mergee_id:
        return (await session.execute(select(Person).where(Person.id == survivor_id))).scalar_one()
    persons = (await session.execute(select(Person).where(Person.id.in_([survivor_id, mergee_id])))).scalars().all()
    if len(persons) != 2:
        raise ValueError("Both survivor and mergee persons must exist")
    survivor = next(p for p in persons if p.id == survivor_id)
    mergee = next(p for p in persons if p.id == mergee_id)

    # Union collections
    emails_lower = {e.lower(): e for e in (survivor.emails or [])}
    for e in (mergee.emails or []):
        el = e.lower()
        if el not in emails_lower:
            emails_lower[el] = el
    survivor.emails = list(emails_lower.values())
    phones_set = set(survivor.phones or []) | set(mergee.phones or [])
    survivor.phones = list(phones_set)
    survivor.email_hashes = list(set(survivor.email_hashes or []) | set(mergee.email_hashes or []))
    survivor.phone_hashes = list(set(survivor.phone_hashes or []) | set(mergee.phone_hashes or []))
    # Primary fields
    if survivor.primary_email is None and mergee.primary_email:
        survivor.primary_email = mergee.primary_email
    if survivor.primary_phone is None and mergee.primary_phone:
        survivor.primary_phone = mergee.primary_phone

    # Reassign meeting attendees
    await session.execute(
        MeetingAttendee.__table__.update()
        .where(MeetingAttendee.person_id == mergee_id)
        .values(person_id=survivor_id)
    )
    # Reassign clients (UPSERT ensure uniqueness)
    mergee_clients = (await session.execute(select(Client).where(Client.person_id == mergee_id))).scalars().all()
    for c in mergee_clients:
        await ensure_client(session, c.coach_id, survivor_id, status=c.status)

    # Update review candidates referencing mergee
    rcs = (await session.execute(select(ReviewCandidate).where(
        (ReviewCandidate.person_a_id == mergee_id) | (ReviewCandidate.person_b_id == mergee_id)
    ))).scalars().all()
    for rc in rcs:
        a = rc.person_a_id
        b = rc.person_b_id
        # Replace mergee with survivor
        if a == mergee_id:
            a = survivor_id
        if b == mergee_id:
            b = survivor_id
        if a == b:
            rc.resolved = True
        else:
            # maintain ordering (string compare for stability)
            ordered = sorted([a, b], key=lambda x: str(x))
            rc.person_a_id, rc.person_b_id = ordered[0], ordered[1]

    # Delete mergee
    await session.execute(
        Person.__table__.delete().where(Person.id == mergee_id)
    )
    await session.flush()
    return survivor


# ---------------------------------------------------------------------------
# Meeting
# ---------------------------------------------------------------------------
async def upsert_meeting(
    session: AsyncSession,
    coach_id: int,
    platform: Optional[str] = None,
    external_refs: Optional[dict] = None,
    started_at: Optional[datetime] = None,
    ended_at: Optional[datetime] = None,
    topic: Optional[str] = None,
    join_url: Optional[str] = None,
    ical_uid: Optional[str] = None,
    location: Optional[str] = None,
    transcript_status: Optional[str] = None,
) -> Meeting:
    external_refs = external_refs or {}
    _set_coach_context(coach_id)

    if ical_uid:
        existing_stmt = select(Meeting).where(Meeting.ical_uid == ical_uid)
        existing = (await session.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            changed = False
            for attr, val in dict(
                coach_id=coach_id,
                platform=platform,
                started_at=started_at,
                ended_at=ended_at,
                topic=topic,
                join_url=join_url,
                location=location,
                transcript_status=transcript_status,
            ).items():
                if val is not None and getattr(existing, attr) != val:
                    setattr(existing, attr, val)
                    changed = True
            if external_refs:
                merged = dict(existing.external_refs or {})
                before = merged.copy()
                merged.update({k: v for k, v in external_refs.items() if v is not None})
                if merged != before:
                    existing.external_refs = merged
                    changed = True
            if changed:
                await session.flush()
            _log_meeting_upserted(str(existing.id), coach_id, platform or "unknown", created=False, updated=changed)
            return existing

    m = Meeting(
        coach_id=coach_id,
        platform=platform,
        started_at=started_at,
        ended_at=ended_at,
        topic=topic,
        join_url=join_url,
        ical_uid=ical_uid,
        location=location,
        external_refs=external_refs,
        transcript_status=transcript_status,
    )
    session.add(m)
    await session.flush()
    _log_meeting_upserted(str(m.id), coach_id, platform or "unknown", created=True)
    return m


# ---------------------------------------------------------------------------
# Meeting Attendees
# ---------------------------------------------------------------------------
async def add_or_update_attendee(
    session: AsyncSession,
    meeting_id: UUID,
    source: str,
    external_attendee_id: Optional[str] = None,
    raw_email: Optional[str] = None,
    raw_phone: Optional[str] = None,
    raw_name: Optional[str] = None,
    role: Optional[str] = None,
) -> MeetingAttendee:
    identity_candidate = external_attendee_id or (raw_email.lower().strip() if raw_email else None) or raw_name
    stmt = select(MeetingAttendee).where(
        MeetingAttendee.meeting_id == meeting_id,
        MeetingAttendee.source == source,
    )
    candidates = (await session.execute(stmt)).scalars().all()
    attendee = None
    for c in candidates:
        derived = c.external_attendee_id or c.raw_email or c.raw_name
        if derived == identity_candidate:
            attendee = c
            break
    if attendee:
        changed = False
        for attr, val in dict(
            external_attendee_id=external_attendee_id,
            raw_email=(raw_email.lower().strip() if raw_email else None),
            raw_phone=e164(raw_phone) if raw_phone else None,
            raw_name=raw_name,
            role=role,
        ).items():
            if val is not None and getattr(attendee, attr) != val:
                setattr(attendee, attr, val)
                changed = True
        if changed:
            await session.flush()
        return attendee

    attendee = MeetingAttendee(
        meeting_id=meeting_id,
        source=source,
        external_attendee_id=external_attendee_id,
        raw_email=(raw_email.lower().strip() if raw_email else None),
        raw_phone=e164(raw_phone) if raw_phone else None,
        raw_name=raw_name,
        role=role,
    )
    session.add(attendee)
    await session.flush()
    return attendee


async def link_attendee_person(
    session: AsyncSession,
    meeting_id: UUID,
    source: str,
    external_attendee_id_or_email_or_name: str,
    person_id: UUID,
) -> Optional[MeetingAttendee]:
    stmt = select(MeetingAttendee).where(
        MeetingAttendee.meeting_id == meeting_id,
        MeetingAttendee.source == source,
    )
    rows = (await session.execute(stmt)).scalars().all()
    target = None
    for a in rows:
        ident = a.external_attendee_id or a.raw_email or a.raw_name
        if ident == external_attendee_id_or_email_or_name:
            target = a
            break
    if not target:
        return None
    if target.person_id != person_id:
        target.person_id = person_id
        await session.flush()
    return target


__all__ = [
    'get_or_create_person_by_email', 'get_or_create_person_by_phone', 'add_email_to_person', 'add_phone_to_person',
    'get_person_by_hash', 'enrich_person', 'ensure_client', 'upsert_meeting', 'add_or_update_attendee', 'link_attendee_person',
    'resolve_attendee', 'merge_persons', 'list_review_candidates', 'resolve_review_candidate'
]

# --------------------------------------------------
# Review candidate helpers
# --------------------------------------------------
from uuid import UUID as _UUID  # local alias
from sqlalchemy import select as _select  # reuse

async def list_review_candidates(session: AsyncSession, coach_id: int, limit: int = 100, status: str | None = 'open'):
    stmt = _select(ReviewCandidate).where(ReviewCandidate.coach_id == coach_id)
    if status:
        stmt = stmt.where(ReviewCandidate.status == status)
    stmt = stmt.order_by(ReviewCandidate.created_at.desc()).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()


async def resolve_review_candidate(
    session: AsyncSession,
    candidate_id: _UUID,
    chosen_person_id: _UUID | None = None,
    create_person: bool = False,
):
    cand = (await session.execute(_select(ReviewCandidate).where(ReviewCandidate.id == candidate_id))).scalar_one()
    if cand.status == 'resolved':  # idempotent
        return cand
    person_id = None
    if chosen_person_id:
        person_id = chosen_person_id
    elif create_person:
        # create a new person from raw fields
        email = cand.raw_email.lower().strip() if cand.raw_email else None
        phone = cand.raw_phone
        person = Person(
            primary_email=email,
            primary_phone=phone,
            emails=[email] if email else [],
            email_hashes=[hash_email(email)] if email else [],
            phones=[phone] if phone else [],
            phone_hashes=[hash_phone(phone)] if phone else [],
        )
        session.add(person)
        await session.flush()
        person_id = person.id
    else:
        raise ValueError("Must provide chosen_person_id or set create_person=True")

    # Attach to meeting attendee if meeting + raw identity present
    if cand.meeting_id:
        stmt = select(MeetingAttendee).where(MeetingAttendee.meeting_id == cand.meeting_id)
        rows = (await session.execute(stmt)).scalars().all()
        target = None
        for a in rows:
            ident = a.external_attendee_id or a.raw_email or a.raw_name
            desired = cand.raw_email or cand.raw_name
            if ident and desired and ident.lower() == desired.lower():
                target = a
                break
        if target and target.person_id != person_id:
            target.person_id = person_id
            await session.flush()
    cand.status = 'resolved'
    await session.flush()
    return cand
