# User model for CoachIntel
from sqlalchemy import Column, Integer, String, create_engine, select, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool
import os
from sqlalchemy.dialects.postgresql import JSON
from cryptography.fernet import Fernet
import asyncpg

# New imports for CRM models
from sqlalchemy import Enum as SAEnum, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

# Added typing and pydantic for API DTOs
from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, EmailStr
from uuid import UUID as UUID_t
from datetime import datetime, date
from sqlalchemy import Boolean  # added

Base = declarative_base()

# Generate this key once and store securely (e.g., in .env)
FERNET_KEY = os.getenv("FERNET_KEY", Fernet.generate_key().decode())
fernet = Fernet(FERNET_KEY.encode())

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)  # e.g., "acme-12345"
    name = Column(String, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False) 
    fireflies_api_key = Column(String, nullable=True)
    zoom_jwt = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    
    # Account password (bcrypt hash); may be null for OAuth-only accounts
    password = Column(String, nullable=True)
    
    # Plan tier: 'free' | 'plus' | 'pro'
    plan = Column(String, nullable=True, default="free")

    # Site-wide admin flag (for owner or elevated admins)
    site_admin = Column(Boolean, nullable=False, default=False, index=True)

    # Organization
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)
    org = relationship("Organization")
    
    # Encrypted Google OAuth fields
    google_access_token_encrypted = Column(String, nullable=True)
    google_refresh_token_encrypted = Column(String, nullable=True)
    google_token_expiry = Column(DateTime, nullable=True)
    
    # Relationships
    meetings = relationship("Meeting", back_populates="user")

    @property
    def name(self):
        """Compatibility property to return full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @name.setter 
    def name(self, value):
        """Compatibility setter to split full name into first/last"""
        if value:
            parts = value.strip().split(' ', 1)
            self.first_name = parts[0]
            self.last_name = parts[1] if len(parts) > 1 else ""
        else:
            self.first_name = ""
            self.last_name = ""

    def set_google_tokens(self, access_token, refresh_token, expiry):
        self.google_access_token_encrypted = fernet.encrypt(access_token.encode()).decode()
        self.google_refresh_token_encrypted = fernet.encrypt(refresh_token.encode()).decode()
        self.google_token_expiry = expiry

    def get_google_tokens(self):
        try:
            access = fernet.decrypt(self.google_access_token_encrypted.encode()).decode() if self.google_access_token_encrypted else None
        except Exception:
            access = None
        try:
            refresh = fernet.decrypt(self.google_refresh_token_encrypted.encode()).decode() if self.google_refresh_token_encrypted else None
        except Exception:
            refresh = None
        return access, refresh, self.google_token_expiry

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)
    client_name = Column(String)
    title = Column(String)
    date = Column(DateTime, index=True)
    duration = Column(Integer)
    source = Column(String)
    transcript_id = Column(String)
    participants = Column(JSON, nullable=True)  # List of participant dicts
    transcript_url = Column(String, nullable=True)
    # Relationships
    user = relationship("User", back_populates="meetings")
    transcript = relationship("Transcript", back_populates="meeting", uselist=False)
    org = relationship("Organization")

class Transcript(Base):
    __tablename__ = "transcripts"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"))
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)
    full_text = Column(Text)
    summary = Column(JSON)
    action_items = Column(JSON)
    progress_notes = Column(Text)  # New field for cumulative progress notes
    # Relationship
    meeting = relationship("Meeting", back_populates="transcript")
    org = relationship("Organization")

# -------------------------
# Minimal CRM models
# -------------------------

class Lead(Base):
    __tablename__ = "leads"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)
    org = relationship("Organization")

    email = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    status = Column(SAEnum('waitlist', 'invited', 'converted', 'lost', name='lead_status'), nullable=False, default='waitlist')

    source = Column(String, nullable=True)
    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)

    tags = Column(ARRAY(String), nullable=True, default=list)
    notes = Column(Text, nullable=True)

    last_contacted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    consents = relationship("Consent", back_populates="lead", cascade="all, delete-orphan")
    events = relationship("MessageEvent", back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('org_id', 'email', name='uq_leads_org_email'),
        Index('ix_leads_org_created', 'org_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} email={self.email} status={self.status} org_id={self.org_id}>"

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'org_id': self.org_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'status': self.status,
            'source': self.source,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign,
            'tags': list(self.tags or []),
            'notes': self.notes,
            'last_contacted_at': self.last_contacted_at.isoformat() if self.last_contacted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class Consent(Base):
    __tablename__ = "consents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)
    org = relationship("Organization")

    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False)
    lead = relationship("Lead", back_populates="consents")

    channel = Column(SAEnum('email', 'sms', name='consent_channel'), nullable=False)
    status = Column(SAEnum('opted_in', 'opted_out', 'unknown', name='consent_status'), nullable=False, default='unknown')

    captured_at = Column(DateTime, nullable=False, server_default=func.now())
    source = Column(String, nullable=True)

    __table_args__ = (
        Index('ix_consents_org_captured', 'org_id', 'captured_at'),
    )

    def __repr__(self) -> str:
        return f"<Consent id={self.id} lead_id={self.lead_id} channel={self.channel} status={self.status}>"

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'org_id': self.org_id,
            'lead_id': str(self.lead_id),
            'channel': self.channel,
            'status': self.status,
            'captured_at': self.captured_at.isoformat() if self.captured_at else None,
            'source': self.source,
        }

class MessageEvent(Base):
    __tablename__ = "message_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)
    org = relationship("Organization")

    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False)
    lead = relationship("Lead", back_populates="events")

    channel = Column(SAEnum('email', 'sms', name='message_channel'), nullable=False)
    type = Column(SAEnum('send', 'open', 'click', 'bounce', 'complaint', name='message_event_type'), nullable=False)

    provider_id = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)

    occurred_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        # Note: DESC index sort order will be created in migration (raw SQL) for portability
        Index('ix_message_events_lead_occurred', 'lead_id', 'occurred_at'),
    )

    def __repr__(self) -> str:
        return f"<MessageEvent id={self.id} lead_id={self.lead_id} type={self.type} at={self.occurred_at}>"

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'org_id': self.org_id,
            'lead_id': str(self.lead_id),
            'channel': self.channel,
            'type': self.type,
            'provider_id': self.provider_id,
            'meta': self.meta or {},
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at else None,
        }

# Organization role mapping (delegated admins per org)
class UserOrgRole(Base):
    __tablename__ = "user_org_roles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(SAEnum('admin', 'member', name='org_role'), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'org_id', 'role', name='uq_user_org_role'),
        Index('ix_user_org_roles_org_role', 'org_id', 'role'),
    )

    def __repr__(self) -> str:
        return f"<UserOrgRole user_id={self.user_id} org_id={self.org_id} role={self.role}>"

# -------------------------
# API DTOs (moved from app/schemas.py)
# -------------------------

LeadStatus = Literal["waitlist", "invited", "converted", "lost"]
ConsentStatus = Literal["opted_in", "opted_out", "unknown"]
Channel = Literal["email", "sms"]
EventType = Literal["send", "open", "click", "bounce", "complaint"]

class LeadListItemOut(BaseModel):
    id: UUID_t
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    status: LeadStatus
    tags: List[str] = []
    created_at: datetime

class LeadDetailOut(LeadListItemOut):
    source: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    notes: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    consent_email: ConsentStatus
    consent_sms: ConsentStatus

class LeadEventOut(BaseModel):
    id: UUID_t
    channel: Channel
    type: EventType
    occurred_at: datetime
    meta: Dict = {}

class LeadListResponse(BaseModel):
    items: List[LeadListItemOut]
    total: int
    limit: int
    offset: int

class LeadExportFilterIn(BaseModel):
    status: Optional[str] = None
    q: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    tag: Optional[str] = None

class LeadPatchIn(BaseModel):
    tags: Optional[List[str]] = None
    phone: Optional[str] = None

    class Config:
        orm_mode = True

# Async engine for FastAPI app
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

if not ASYNC_DATABASE_URL and not DATABASE_URL:
    raise RuntimeError("DATABASE_URL or ASYNC_DATABASE_URL environment variable is not set")

# Configure engine specifically for Supabase transaction pooler + Railway
engine = create_async_engine(
    ASYNC_DATABASE_URL, 
    echo=False,  # Disable echo in production to reduce logs
    future=True,
    poolclass=NullPool,  # Critical: No connection pooling with transaction pooler
    connect_args={
        "command_timeout": 30,
        "statement_cache_size": 0,  # Disable prepared statements
        "prepared_statement_cache_size": 0,  # Disable prepared statement cache
    },
    execution_options={
        "compiled_cache": {},  # Disable SQLAlchemy's compiled statement cache
        "autocommit": True,  # Use autocommit mode for transaction pooler
    },
    # Note: pool_size, max_overflow, pool_pre_ping, pool_recycle are not valid with NullPool
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# For Alembic migrations (sync engine)
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
sync_engine = create_engine(SYNC_DATABASE_URL)

# Synchronous session for Celery worker and scripts
SessionLocal = sessionmaker(sync_engine)

async def get_user_by_email(email: str):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            return user
    except Exception as e:
        print(f"Database error in get_user_by_email for {email}: {e}")
        # Return None instead of crashing the app
        return None

async def create_or_update_user(email: str, name: str = None, first_name: str = None, last_name: str = None, fireflies_api_key: str = None, zoom_jwt: str = None, phone: str = None, address: str = None, password: str = None, plan: str | None = None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # Helper: ensure org exists for user
        async def _ensure_org_for_user(display_name: str) -> Organization:
            base = (display_name or email.split('@')[0] or 'org').lower()
            # simple slugify: keep alnum and hyphen
            slug = ''.join(c if c.isalnum() else '-' for c in base).strip('-')
            if not slug:
                slug = 'org'
            # try a few times to get a unique key
            from uuid import uuid4
            for _ in range(5):
                suffix = uuid4().hex[:5]
                key = f"{slug}-{suffix}"
                existing = await session.execute(select(Organization).where(Organization.key == key))
                if existing.scalar_one_or_none() is None:
                    org = Organization(key=key, name=display_name or slug)
                    session.add(org)
                    await session.flush()  # get org.id
                    return org
            # fallback without uniqueness guarantee (very unlikely collision)
            key = f"{slug}-{uuid4().hex[:6]}"
            org = Organization(key=key, name=display_name or slug)
            session.add(org)
            await session.flush()
            return org
        
        if user:
            # Handle name updates - prefer first_name/last_name over name
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if name and not first_name and not last_name:
                user.name = name  # Uses the setter to split name
            if fireflies_api_key is not None:
                user.fireflies_api_key = fireflies_api_key
            if zoom_jwt is not None:
                user.zoom_jwt = zoom_jwt
            if phone is not None:
                user.phone = phone
            if address is not None:
                user.address = address
            if password is not None:
                user.password = password
            if plan is not None:
                user.plan = plan
            # attach org if missing
            if not getattr(user, 'org_id', None):
                display_name = (first_name or user.first_name or '') + (' ' + (last_name or user.last_name) if (last_name or user.last_name) else '')
                org = await _ensure_org_for_user(display_name.strip() or email.split('@')[0])
                user.org_id = org.id
        else:
            # Create new user
            if first_name is None and last_name is None and name:
                user = User(email=email, first_name="", last_name="", 
                           fireflies_api_key=fireflies_api_key, zoom_jwt=zoom_jwt, phone=phone, address=address, password=password,
                           plan=plan or "free")
                user.name = name
            else:
                user = User(email=email, first_name=first_name or "", last_name=last_name or "", 
                           fireflies_api_key=fireflies_api_key, zoom_jwt=zoom_jwt, phone=phone, address=address, password=password,
                           plan=plan or "free")
            # create org and link
            display_name = (first_name or user.first_name or '') + (' ' + (last_name or user.last_name) if (last_name or user.last_name) else '')
            org = await _ensure_org_for_user(display_name.strip() or email.split('@')[0])
            user.org_id = org.id
            session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
