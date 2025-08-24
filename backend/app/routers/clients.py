from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID as UUID_t
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload

from app.models import AsyncSessionLocal, User
from app.models_meeting_tracking import Client, Meeting as MTMeeting, MeetingAttendee, ClientStatusAudit
# Avoid circular import: import verify_jwt_user inside dependency function
from fastapi import Request

async def _current_user(request: Request) -> User:
    from app.main import verify_jwt_user  # local import to break cycle
    return await verify_jwt_user(request)

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientOut(BaseModel):
    id: UUID_t
    status: str
    last_meeting_at: Optional[str] = None
    person_id: UUID_t

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


@router.get("", response_model=ClientListResponse)
async def list_clients(
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Email or name fragment"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(_current_user),
):
    coach_id = user.id
    async with AsyncSessionLocal() as session:  # type: ignore
        # Base query
        stmt = select(Client).where(Client.coach_id == coach_id)
        if status:
            stmt = stmt.where(Client.status == status)
        if q:
            from app.models_meeting_tracking import Person
            # Search across primary email / phone and ANY element of emails array via unnest + ILIKE
            ilike = f"%{q}%"
            stmt = stmt.join(Person).where(
                (
                    (Person.primary_email.ilike(ilike)) |
                    (Person.primary_phone.ilike(ilike)) |
                    # Fast equality (leverages GIN index on persons.emails)
                    text(":q_exact = ANY(persons.emails)") |
                    # Substring match across any email (falls back to seq scan if needed)
                    text("EXISTS (SELECT 1 FROM unnest(persons.emails) AS e WHERE e ILIKE :ilike)")
                )
            ).params(ilike=ilike, q_exact=q)
        total = (await session.execute(stmt.with_only_columns(func.count()))).scalar() or 0
        # Last meeting computation
        stmt = stmt.options(selectinload(Client.person))
        stmt = stmt.limit(limit).offset(offset)
        rows = (await session.execute(stmt)).scalars().all()
        items: List[ClientOut] = []
        # Gather last meeting via attendees
        person_ids = [c.person_id for c in rows]
        if person_ids:
            lm_stmt = (
                select(func.max(MTMeeting.started_at), MeetingAttendee.person_id)
                .join(MeetingAttendee, MeetingAttendee.meeting_id == MTMeeting.id)
                .where(MTMeeting.coach_id == coach_id, MeetingAttendee.person_id.in_(person_ids))
                .group_by(MeetingAttendee.person_id)
            )
            lm_rows = await session.execute(lm_stmt)
            lm_map = {pid: dt for dt, pid in lm_rows.all()}
        else:
            lm_map = {}
        for c in rows:
            items.append(ClientOut(
                id=c.id,
                status=c.status,
                person_id=c.person_id,
                last_meeting_at=lm_map.get(c.person_id).isoformat() if lm_map.get(c.person_id) else None,
            ))
        return ClientListResponse(items=items, total=total)


@router.get("/{client_id}/timeline", response_model=TimelineResponse)
async def client_timeline(
    client_id: UUID_t,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(_current_user),
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
        items: List[TimelineMeetingOut] = []
        for m in meetings:
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
                ]
            ))
        return TimelineResponse(items=items, total=total, limit=limit, offset=offset)


class ClientStatusChangeIn(BaseModel):
    status: str
    reason: Optional[str] = None

class ClientStatusChangeOut(BaseModel):
    id: UUID_t
    old_status: Optional[str]
    new_status: str

@router.post("/{client_id}/status", response_model=ClientStatusChangeOut)
async def change_client_status(
    client_id: UUID_t,
    body: ClientStatusChangeIn,
    user: User = Depends(_current_user),
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
