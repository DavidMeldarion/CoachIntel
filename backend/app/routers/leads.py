from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, or_, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List

from app.models import AsyncSessionLocal, Lead, Consent, MessageEvent, User
from app.deps import get_current_user
from app.models import (
    LeadListItemOut,
    LeadDetailOut,
    LeadEventOut,
    LeadListResponse,
    LeadExportFilterIn,
    LeadPatchIn,
)
from app.services.export import rows_to_csv

router = APIRouter(prefix="/leads", tags=["leads"]) 

ALLOWED_LEAD_STATUS = {"waitlist", "invited", "converted", "lost"}

def site_admin_only(user: User = Depends(get_current_user)) -> User:
    if not getattr(user, 'site_admin', False):
        raise HTTPException(status_code=403, detail="Forbidden: site admin only")
    return user

# Helper to get latest consent status per channel
async def _latest_consent(session: AsyncSession, lead_id: UUID, channel: str) -> str:
    stmt = (
        select(Consent)
        .where(Consent.lead_id == lead_id, Consent.channel == channel)
        .order_by(Consent.captured_at.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    c = res.scalar_one_or_none()
    return c.status if c else "unknown"

@router.get("/", response_model=LeadListResponse)
async def list_leads(
    q: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    user: User = Depends(site_admin_only),
):
    async with AsyncSessionLocal() as session:
        conds = []
        # Site admin view is strictly public leads (org_id is null)
        conds.append(Lead.org_id == None)  # noqa: E711
        if status:
            if status not in ALLOWED_LEAD_STATUS:
                raise HTTPException(status_code=400, detail="Invalid status filter")
            conds.append(Lead.status == status)
        if q:
            like = f"%{q.lower()}%"
            conds.append(or_(Lead.email.ilike(like), Lead.first_name.ilike(like), Lead.last_name.ilike(like)))
        if tag:
            # Postgres ARRAY contains single tag
            conds.append(Lead.tags.contains([tag]))
        if date_from:
            conds.append(Lead.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            conds.append(Lead.created_at <= datetime.combine(date_to, datetime.max.time()))

        # total
        total_res = await session.execute(select(func.count()).select_from(Lead).where(and_(*conds)))
        total = int(total_res.scalar() or 0)

        # items
        data_stmt = (
            select(Lead)
            .where(and_(*conds))
            .order_by(Lead.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await session.execute(data_stmt)
        rows = res.scalars().all()
        items = [
            LeadListItemOut(
                id=l.id,
                email=l.email,
                first_name=l.first_name,
                last_name=l.last_name,
                phone=l.phone,
                status=l.status,
                tags=list(l.tags or []),
                created_at=l.created_at,
            )
            for l in rows
        ]
        return LeadListResponse(items=items, total=total, limit=limit, offset=offset)

@router.get("/{lead_id}", response_model=LeadDetailOut)
async def get_lead(lead_id: UUID, user: User = Depends(site_admin_only)):
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.id == lead_id, Lead.org_id == None)  # noqa: E711
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        ce = await _latest_consent(session, lead.id, 'email')
        cs = await _latest_consent(session, lead.id, 'sms')
        return LeadDetailOut(
            id=lead.id,
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            phone=lead.phone,
            status=lead.status,
            tags=list(lead.tags or []),
            created_at=lead.created_at,
            source=lead.source,
            utm_source=lead.utm_source,
            utm_medium=lead.utm_medium,
            utm_campaign=lead.utm_campaign,
            notes=lead.notes,
            last_contacted_at=lead.last_contacted_at,
            consent_email=ce,
            consent_sms=cs,
        )

@router.get("/{lead_id}/events", response_model=List[LeadEventOut])
async def get_lead_events(lead_id: UUID, user: User = Depends(site_admin_only)):
    async with AsyncSessionLocal() as session:
        # ensure access
        lead_stmt = select(Lead.id, Lead.org_id).where(Lead.id == lead_id, Lead.org_id == None)  # noqa: E711
        chk = await session.execute(lead_stmt)
        if chk.first() is None:
            raise HTTPException(status_code=404, detail="Lead not found")
        evt_stmt = (
            select(MessageEvent)
            .where(MessageEvent.lead_id == lead_id)
            .order_by(desc(MessageEvent.occurred_at))
        )
        res = await session.execute(evt_stmt)
        evs = res.scalars().all()
        return [
            LeadEventOut(
                id=e.id,
                channel=e.channel,
                type=e.type,
                occurred_at=e.occurred_at,
                meta=e.meta or {},
            )
            for e in evs
        ]

@router.patch("/{lead_id}", response_model=LeadDetailOut)
async def patch_lead(lead_id: UUID, body: LeadPatchIn, user: User = Depends(site_admin_only)):
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.id == lead_id, Lead.org_id == None)  # noqa: E711
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if body.tags is not None:
            # normalize and limit
            lead.tags = [t.strip() for t in body.tags if t and t.strip()][:10]
        if body.phone is not None:
            lead.phone = body.phone.strip() or None
        await session.commit()
        await session.refresh(lead)
        # respond with detail
        ce = await _latest_consent(session, lead.id, 'email')
        cs = await _latest_consent(session, lead.id, 'sms')
        return LeadDetailOut(
            id=lead.id,
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            phone=lead.phone,
            status=lead.status,
            tags=list(lead.tags or []),
            created_at=lead.created_at,
            source=lead.source,
            utm_source=lead.utm_source,
            utm_medium=lead.utm_medium,
            utm_campaign=lead.utm_campaign,
            notes=lead.notes,
            last_contacted_at=lead.last_contacted_at,
            consent_email=ce,
            consent_sms=cs,
        )

@router.patch("/{lead_id}/notes")
async def patch_lead_notes(lead_id: UUID, body: dict, user: User = Depends(site_admin_only)):
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.id == lead_id, Lead.org_id == None)  # noqa: E711
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        notes = (body.get("notes") or "").strip()
        lead.notes = notes
        await session.commit()
        return {"ok": True}

@router.post("/{lead_id}/status")
async def update_status(lead_id: UUID, body: dict, user: User = Depends(site_admin_only)):
    status = (body or {}).get("status")
    if status not in ALLOWED_LEAD_STATUS:
        raise HTTPException(status_code=400, detail="Invalid status value")
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.id == lead_id, Lead.org_id == None)  # noqa: E711
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.status = status
        await session.commit()
        return {"ok": True}

@router.post("/export")
async def export_leads(filters: LeadExportFilterIn, user: User = Depends(site_admin_only)):
    async with AsyncSessionLocal() as session:
        conds = []
        # Site admin export is for public leads only (org_id null)
        conds.append(Lead.org_id == None)  # noqa: E711
        if filters.status:
            conds.append(Lead.status == filters.status)
        if filters.q:
            like = f"%{filters.q.lower()}%"
            conds.append(or_(Lead.email.ilike(like), Lead.first_name.ilike(like), Lead.last_name.ilike(like)))
        if filters.tag:
            conds.append(Lead.tags.contains([filters.tag]))
        if filters.date_from:
            conds.append(Lead.created_at >= datetime.combine(filters.date_from, datetime.min.time()))
        if filters.date_to:
            conds.append(Lead.created_at <= datetime.combine(filters.date_to, datetime.max.time()))
        stmt = select(Lead).where(and_(*conds)).order_by(Lead.created_at.desc())
        res = await session.execute(stmt)
        rows = res.scalars().all()
        def _row(l: Lead):
            return {
                "id": str(l.id),
                "created_at": l.created_at.isoformat() if l.created_at else "",
                "status": l.status,
                "first_name": l.first_name or "",
                "last_name": l.last_name or "",
                "email": l.email,
                "phone": l.phone or "",
                "tags": list(l.tags or []),
                "source": l.source or "",
                "utm_source": l.utm_source or "",
                "utm_medium": l.utm_medium or "",
                "utm_campaign": l.utm_campaign or "",
                "last_contacted_at": l.last_contacted_at.isoformat() if l.last_contacted_at else "",
            }
        csv_text = rows_to_csv([_row(l) for l in rows])
        return Response(content=csv_text, media_type="text/csv", headers={
            "Content-Disposition": f"attachment; filename=leads_export_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        })
