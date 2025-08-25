from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID as UUID_t
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload

from app.models import AsyncSessionLocal, User
from app.deps import get_current_user, coach_scope  # shared auth dependencies
from app.models_meeting_tracking import Client, Meeting as MTMeeting, MeetingAttendee, ClientStatusAudit, Person

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientOut(BaseModel):
    id: UUID_t
    status: str
    last_meeting_at: Optional[str] = None
    person_id: UUID_t
    person_name: Optional[str] = None

class ClientListResponse(BaseModel):
    items: List[ClientOut]
    total: int

class MeetingAttendeeOut(BaseModel):
    source: str
    raw_email: Optional[str] = None
    raw_name: Optional[str] = None
    person_id: Optional[UUID_t] = None

class TimelineMeetingOut(BaseModel):
    id: UUID_t
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    topic: Optional[str] = None
    platform: Optional[str] = None
    external_refs: dict
    transcript_status: Optional[str] = None
    attendees: List[MeetingAttendeeOut] = []
    summary_overview: Optional[str] = None

class TimelineResponse(BaseModel):
    items: List[TimelineMeetingOut]
    total: int
    limit: int
    offset: int
class ClientStatusChangeIn(BaseModel):
    status: str
    reason: Optional[str] = None

class ClientStatusChangeOut(BaseModel):
    id: UUID_t
    old_status: Optional[str]
    new_status: str


@router.get("/_debug")
async def clients_debug(user: User = Depends(get_current_user)):
    """Return ingestion/debug stats for the authenticated coach.

    Helps verify whether background tasks are populating meeting tracking tables.
    """
@router.get("", response_model=ClientListResponse)
async def list_clients(
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Email or name fragment"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    coach_id = user.id
    async with AsyncSessionLocal() as session:  # type: ignore
        # Subquery last meeting per person
        lm_subq = (
            select(
                MeetingAttendee.person_id.label('pid'),
                func.max(MTMeeting.started_at).label('last_started_at')
            )
            .join(MTMeeting, MeetingAttendee.meeting_id == MTMeeting.id)
            .where(MTMeeting.coach_id == coach_id)
            .group_by(MeetingAttendee.person_id)
        ).subquery()
        stmt = (
            select(Client, lm_subq.c.last_started_at)
            .where(Client.coach_id == coach_id)
            .join(lm_subq, lm_subq.c.pid == Client.person_id, isouter=True)
        )
        if status:
            stmt = stmt.where(Client.status == status)
        if q:
            ilike = f"%{q}%"
            stmt = stmt.join(Person, Person.id == Client.person_id).where(
                (
                    (Person.primary_email.ilike(ilike)) |
                    (Person.primary_phone.ilike(ilike)) |
                    text(":q_exact = ANY(persons.emails)") |
                    text("EXISTS (SELECT 1 FROM unnest(persons.emails) AS e WHERE e ILIKE :ilike)")
                )
            ).params(ilike=ilike, q_exact=q)
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(total_stmt)).scalar() or 0
        stmt = stmt.options(selectinload(Client.person)).limit(limit).offset(offset)
        rows = (await session.execute(stmt)).all()
        clients_with_lm = [(row[0], row[1]) for row in rows]
        person_ids = [c.person_id for c, _ in clients_with_lm]
        name_map = {}
        if person_ids:
            name_stmt = (
                select(MeetingAttendee.person_id, func.max(MeetingAttendee.raw_name))
                .where(MeetingAttendee.person_id.in_(person_ids), MeetingAttendee.raw_name.is_not(None))
                .group_by(MeetingAttendee.person_id)
            )
            name_rows = await session.execute(name_stmt)
            for pid, raw_name in name_rows.all():
                if raw_name:
                    name_map[pid] = raw_name
        items: List[ClientOut] = []
        for c, last_started_at in clients_with_lm:
            p = c.person
            display = (
                name_map.get(p.id)
                or (p.primary_email if p and p.primary_email else None)
                or (p.emails[0] if p and getattr(p, 'emails', []) else None)
                or str(p.id)[:8]
            )
            items.append(ClientOut(
                id=c.id,
                status=c.status,
                person_id=c.person_id,
                person_name=display,
                last_meeting_at=last_started_at.isoformat() if last_started_at else None,
            ))
        return ClientListResponse(items=items, total=total)


@router.get("/{client_id}/timeline", response_model=TimelineResponse)
async def client_timeline(
    client_id: UUID_t,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
        user: User = Depends(get_current_user),
):
    coach_id = user.id
    async with AsyncSessionLocal() as session:  # type: ignore
        c = (await session.execute(select(Client).where(Client.id == client_id, Client.coach_id == coach_id))).scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Client not found")
        # meetings for which client's person appears as attendee
        att_stmt = select(MTMeeting).join(MeetingAttendee, MeetingAttendee.meeting_id == MTMeeting.id).where(
            MeetingAttendee.person_id == c.person_id, MTMeeting.coach_id == coach_id
        )
        total = (await session.execute(att_stmt.with_only_columns(func.count()))).scalar() or 0
        stmt = att_stmt.order_by(MTMeeting.started_at.desc()).limit(limit).offset(offset)
        meetings = (await session.execute(stmt)).scalars().all()
        meeting_ids = [m.id for m in meetings]
        attendees_map = {mid: [] for mid in meeting_ids}
        if meeting_ids:
            att_full_stmt = select(MeetingAttendee).where(MeetingAttendee.meeting_id.in_(meeting_ids))
            att_rows = (await session.execute(att_full_stmt)).scalars().all()
            for a in att_rows:
                attendees_map[a.meeting_id].append(a)
        # Attempt to enrich with legacy transcript summaries (Fireflies) where possible.
        # Legacy Transcript table uses id matching fireflies transcript/meeting id.
        from app.models import Transcript as LegacyTranscript
        fireflies_ids = []
        meet_to_fireflies_id = {}
        for m in meetings:
            if m.platform == 'fireflies':
                ffid = (m.external_refs or {}).get('fireflies_meeting_id')
                if ffid:
                    fireflies_ids.append(ffid)
                    meet_to_fireflies_id[m.id] = ffid
        transcript_map = {}
        if fireflies_ids:
            t_rows = (await session.execute(select(LegacyTranscript).where(LegacyTranscript.id.in_(fireflies_ids)))).scalars().all()
            for t in t_rows:
                # summary is JSON; pick overview if present else None
                overview = None
                try:
                    summ = t.summary or {}
                    if isinstance(summ, dict):
                        overview = summ.get('overview') or None
                except Exception:
                    overview = None
                transcript_map[t.id] = overview

        items: List[TimelineMeetingOut] = []
        for m in meetings:
            overview = None
            ffid = meet_to_fireflies_id.get(m.id)
            if ffid:
                overview = transcript_map.get(ffid)
            items.append(TimelineMeetingOut(
                id=m.id,
                started_at=m.started_at.isoformat() if m.started_at else None,
                ended_at=m.ended_at.isoformat() if m.ended_at else None,
                topic=m.topic,
                platform=m.platform,
                external_refs=m.external_refs or {},
                transcript_status=m.transcript_status,
                attendees=[
                    MeetingAttendeeOut(
                        source=a.source,
                        raw_email=a.raw_email,
                        raw_name=a.raw_name,
                        person_id=a.person_id,
                    ) for a in attendees_map.get(m.id, [])
                ],
                summary_overview=overview,
            ))
        return TimelineResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/{client_id}/status", response_model=ClientStatusChangeOut)
async def change_client_status(
    client_id: UUID_t,
    body: ClientStatusChangeIn,
        user: User = Depends(get_current_user),
):
    coach_id = user.id
    async with AsyncSessionLocal() as session:  # type: ignore
        c = (await session.execute(select(Client).where(Client.id == client_id, Client.coach_id == coach_id))).scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Client not found")
        old = c.status
        c.status = body.status
        audit = ClientStatusAudit(
            client_id=c.id,
            coach_id=coach_id,
            old_status=old,
            new_status=body.status,
            reason=body.reason,
        )
        session.add(audit)
        await session.flush()
        await session.commit()
        return ClientStatusChangeOut(id=c.id, old_status=old, new_status=c.status)
