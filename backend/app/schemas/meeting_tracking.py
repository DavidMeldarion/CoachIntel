"""Pydantic v2 schemas for meeting tracking & related entities.

All datetimes must be timezone-aware ISO8601. Emails validated & lowercased.
Phones normalized to E.164 (if possible) using `e164` helper.
Tokens in ExternalAccountOut are masked.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator, ConfigDict, field_serializer

from app.utils.crypto import e164, hash_email

# ---------------------------------------------------------------------------
# Common helpers / mixins
# ---------------------------------------------------------------------------
class TZModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def _ensure_tz(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return dt
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise ValueError("Naive datetimes are not allowed; include timezone info")
        return dt

    @field_validator('*', mode='before')
    def _validate_dt(cls, v):  # type: ignore
        if isinstance(v, datetime):
            return cls._ensure_tz(v)
        return v


# ---------------------------------------------------------------------------
# Person
# ---------------------------------------------------------------------------
class PersonIn(BaseModel):
    primary_email: Optional[EmailStr] = None
    primary_phone: Optional[str] = None
    emails: List[EmailStr] = []
    phones: List[str] = []

    @field_validator('emails', mode='after')
    def uniq_lower_emails(cls, v: List[EmailStr]):
        seen = set()
        out: List[EmailStr] = []
        for e in v:
            low = e.lower()
            if low not in seen:
                seen.add(low)
                out.append(EmailStr(low))
        return out

    @field_validator('primary_email', mode='before')
    def lower_primary_email(cls, v):  # type: ignore
        if v is None:
            return v
        return str(v).strip().lower()

    @field_validator('primary_phone', 'phones', mode='after')
    def normalize_phone(cls, v):  # type: ignore
        if v is None:
            return v
        if isinstance(v, list):
            normed = []
            for p in v:
                n = e164(p)
                if n:
                    normed.append(n)
            # dedupe
            return list(dict.fromkeys(normed))
        return e164(v)


class PersonOut(TZModel):
    id: UUID
    primary_email: Optional[EmailStr] = None
    primary_phone: Optional[str] = None
    emails: List[EmailStr] = []
    phones: List[str] = []
    email_hashes: List[str] = []
    phone_hashes: List[str] = []
    created_at: datetime


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class ClientIn(BaseModel):
    person_id: UUID
    status: Optional[str] = None  # 'prospect'|'active'|'inactive'; validated upstream

class ClientOut(TZModel):
    id: UUID
    person_id: UUID
    coach_id: int
    status: str
    first_seen_at: datetime


# ---------------------------------------------------------------------------
# External Account (mask tokens)
# ---------------------------------------------------------------------------
class ExternalAccountOut(TZModel):
    id: UUID
    coach_id: int
    provider: str
    scopes: List[str]
    external_user_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    access_token_enc: Optional[str] = None
    refresh_token_enc: Optional[str] = None

    @staticmethod
    def _mask(val: Optional[str]) -> Optional[str]:
        if not val:
            return val
        # show only first 4 chars and length
        return f"{val[:4]}…({len(val)} chars)" if len(val) > 8 else "***"

    @field_serializer('access_token_enc', 'refresh_token_enc')
    def mask_tokens(self, v: Optional[str]):  # type: ignore
        return self._mask(v)


# ---------------------------------------------------------------------------
# Meeting
# ---------------------------------------------------------------------------
class MeetingIn(BaseModel):
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    platform: Optional[str] = None
    topic: Optional[str] = None
    join_url: Optional[str] = None
    ical_uid: Optional[str] = None
    location: Optional[str] = None
    external_refs: Dict[str, Any] = {}
    transcript_status: Optional[str] = None

    @field_validator('external_refs')
    def ensure_dict(cls, v):  # type: ignore
        return v or {}

    @field_validator('started_at', 'ended_at', mode='after')
    def ensure_tz(cls, v):  # type: ignore
        if v is None:
            return v
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError('Datetime must be timezone-aware')
        return v

class MeetingOut(TZModel):
    id: UUID
    coach_id: int
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    platform: Optional[str] = None
    topic: Optional[str] = None
    join_url: Optional[str] = None
    ical_uid: Optional[str] = None
    location: Optional[str] = None
    external_refs: Dict[str, Any] = {}
    transcript_status: Optional[str] = None


# ---------------------------------------------------------------------------
# Meeting Attendee
# ---------------------------------------------------------------------------
class MeetingAttendeeIn(BaseModel):
    meeting_id: UUID
    person_id: Optional[UUID] = None
    source: str
    external_attendee_id: Optional[str] = None
    raw_email: Optional[EmailStr] = None
    raw_phone: Optional[str] = None
    raw_name: Optional[str] = None
    role: Optional[str] = None

    @field_validator('raw_email', mode='before')
    def lower_email(cls, v):  # type: ignore
        return v.strip().lower() if v else v

    @field_validator('raw_phone', mode='after')
    def norm_phone(cls, v):  # type: ignore
        return e164(v) if v else v

class MeetingAttendeeOut(TZModel):
    meeting_id: UUID
    person_id: Optional[UUID] = None
    source: str
    external_attendee_id: Optional[str] = None
    raw_email: Optional[EmailStr] = None
    raw_phone: Optional[str] = None
    raw_name: Optional[str] = None
    role: Optional[str] = None
    identity_key: str


__all__ = [
    'PersonIn', 'PersonOut', 'ClientIn', 'ClientOut', 'ExternalAccountOut',
    'MeetingIn', 'MeetingOut', 'MeetingAttendeeIn', 'MeetingAttendeeOut'
]
