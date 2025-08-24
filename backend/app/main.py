from __future__ import annotations
import os
import time
import jwt
import json
from fastapi import APIRouter, HTTPException, Request, FastAPI, HTTPException, UploadFile, File, Query, Request, Body, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator, Field, ValidationError
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
import httpx
from urllib.parse import urlencode
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
import logging
import uuid as _uuid_mod
import contextvars
# Add crypto utils for HMAC tokens
import hmac, hashlib, base64
from uuid import UUID as UUID_t
from sqlalchemy import select, or_, func
# Import password hashing context
from passlib.context import CryptContext
# Added typing and external imports
from typing import Optional, List, Dict
from celery.result import AsyncResult
from app.models import (
    User,
    Meeting,
    Transcript,
    Lead,
    Consent,
    MessageEvent,
    AsyncSessionLocal,
    get_user_by_email,
    create_or_update_user,
    UserOrgRole,  # added
)
from app.integrations import get_fireflies_meeting_details, test_fireflies_api_key
# Delayed import of celery worker to avoid circular import during module initialization
celery_app = None
sync_fireflies_meetings = None

def _lazy_load_worker():  # late binding to prevent circular import
    global celery_app, sync_fireflies_meetings
    if celery_app is None or sync_fireflies_meetings is None:
        from app import worker  # type: ignore
        celery_app = worker.celery_app
    sync_fireflies_meetings = worker.sync_fireflies_meetings
    ingest_fireflies_transcripts = worker.ingest_fireflies_transcripts  # type: ignore
from .config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URL, GOOGLE_CALENDAR_EVENTS_URL

# Import leads router
from app.routers.leads import router as leads_router
from app.routers.webhooks import router as webhooks_router
from app.routers.clients import router as clients_router
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.meeting_tracking import list_review_candidates, resolve_review_candidate
from uuid import UUID as _UUID
from app.services.oauth import build_auth_url, exchange_code, OAuthError
from app.utils.crypto import fernet

# Frontend URL configuration with both www and non-www variants
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
# Create both www and non-www variants for CORS
frontend_origins = [FRONTEND_URL]
if FRONTEND_URL.startswith("https://"):
    if "www." in FRONTEND_URL:
        # If FRONTEND_URL has www, add non-www version
        frontend_origins.append(FRONTEND_URL.replace("://www.", "://"))
    else:
        # If FRONTEND_URL doesn't have www, add www version
        frontend_origins.append(FRONTEND_URL.replace("://", "://www."))

from app.logging import (
    slog,
    set_log_coach,
    set_log_provider,
    set_log_request,
    log_webhook_received,
    log_meeting_upserted,
    log_attendee_resolved,
    log_tokens_refreshed,
)

# Log CORS configuration for debugging
logger = logging.getLogger("coachintel")
logger.info(f"CORS configured for origins: {['http://localhost:3000', 'http://127.0.0.1:3000'] + frontend_origins}")

app = FastAPI(
    title="CoachIntel API",
    root_path="/",
    # Trust proxy headers for proper URL generation
    servers=[{"url": "https://api.coachintel.ai", "description": "Production server"}] if os.getenv("RAILWAY_ENVIRONMENT") else None
)

# -------------------------
# Middleware: payload size limit (default 1MB)
# -------------------------
MAX_PAYLOAD_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(1024 * 1024)))  # 1MB default

@app.middleware("http")
async def limit_payload_size(request: Request, call_next):
    # Only apply to methods that can have bodies
    if request.method in {"POST", "PUT", "PATCH"}:
        # Content-Length fast path
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_PAYLOAD_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})
        # For streaming/no content-length, read but enforce limit via manual buffer
        # Use request.body() which reads entire body once; rely on CL fast path for typical JSON
        if not cl:
            body = await request.body()
            if len(body) > MAX_PAYLOAD_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Payload too large"})
            # Reconstruct scope body for downstream (FastAPI caches body() but be explicit)
            async def receive_gen(first=True, data=body):
                if first:
                    return {"type": "http.request", "body": data, "more_body": False}
                return {"type": "http.request", "body": b"", "more_body": False}
            request._receive = lambda first=True: receive_gen(first)  # type: ignore
    return await call_next(request)

# Trust proxy headers for Railway deployment
@app.middleware("http")
async def trust_proxy_headers(request: Request, call_next):
    # Railway uses proxy headers for HTTPS termination
    if os.getenv("RAILWAY_ENVIRONMENT"):
        # Trust the X-Forwarded-Proto header from Railway's proxy
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto == "https":
            # Update the request URL scheme to https
            request.scope["scheme"] = "https"
    
    response = await call_next(request)
    return response

# Request id + context binding middleware (after proxy adjustment)
@app.middleware("http")
async def request_id_and_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(_uuid_mod.uuid4())
    set_log_request(rid)
    # infer provider from webhook path early
    path = request.url.path.lower()
    if path.startswith("/webhooks/"):
        parts = path.split("/")
        if len(parts) > 2:
            set_log_provider(parts[2])
    try:
        response = await call_next(request)
        response.headers.setdefault("X-Request-Id", rid)
        return response
    finally:
            # clear context for safety (new context per request anyway)
            set_log_coach(None)
            set_log_provider(None)

@app.get("/health/lazy-worker")
async def health_lazy_worker():
    """Health endpoint to verify Celery lazy loader functions without circular import.

    Returns JSON indicating whether the celery app object could be loaded.
    """
    try:
        _lazy_load_worker()
        loaded = celery_app is not None
        return {"status": "ok", "celery_loaded": loaded}
    except Exception as e:  # pragma: no cover - defensive
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------
# HMAC utils for unsubscribe links
# -------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = '=' * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + padding).encode())


def sign_hmac_token(payload: dict, secret: str, expires_in_seconds: int = 60 * 60 * 24 * 30) -> str:
    body = json.dumps({**payload, "exp": int(time.time()) + expires_in_seconds}, separators=(",", ":")).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return f"{_b64url_encode(body)}.{_b64url_encode(sig)}"


def verify_hmac_token(token: str, secret: str) -> dict:
    try:
        body_b64, sig_b64 = token.split(".")
        body = _b64url_decode(body_b64)
        sig = _b64url_decode(sig_b64)
        expected = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Invalid signature")
        data = json.loads(body.decode())
        if int(time.time()) > int(data.get("exp", 0)):
            raise ValueError("Token expired")
        return data
    except Exception as e:
        raise ValueError(f"Invalid token: {e}")

def sign_invite_token(email: str, secret: str, expires_in_seconds: int = 60 * 60 * 24 * 14) -> str:
    """Create a unique HMAC-signed invite token bound to the email with expiry and nonce."""
    nonce = base64.urlsafe_b64encode(os.urandom(16)).decode().rstrip('=')
    payload = {"email": email.lower(), "nonce": nonce}
    return sign_hmac_token(payload, secret, expires_in_seconds)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"] + frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# -------------------------
# Webhook shared security (per-provider secret headers)
# -------------------------
PROVIDER_WEBHOOK_SECRETS = {
    "calendly": os.getenv("CALENDLY_PROVIDER_SECRET"),
    "zoom": os.getenv("ZOOM_PROVIDER_SECRET"),
    "fireflies": os.getenv("FIREFLIES_PROVIDER_SECRET"),
}

REQUIRE_PROVIDER_WEBHOOK_HEADER = os.getenv("REQUIRE_PROVIDER_WEBHOOK_SECRET", "true").lower() in {"1", "true", "yes"}
PROVIDER_HEADER_NAME = os.getenv("PROVIDER_WEBHOOK_HEADER", "X-Webhook-Secret")

@app.middleware("http")
async def enforce_provider_webhook_secret(request: Request, call_next):
    if not REQUIRE_PROVIDER_WEBHOOK_HEADER:
        return await call_next(request)
    path = request.url.path.lower()
    if path.startswith("/webhooks/"):
        # Determine provider from path: /webhooks/{provider}...
        parts = path.split("/")
        provider = parts[2] if len(parts) > 2 else None
        if provider in PROVIDER_WEBHOOK_SECRETS:
            expected = PROVIDER_WEBHOOK_SECRETS.get(provider)
            # If no expected secret configured, allow (fail-open) but log; otherwise enforce
            if expected:
                provided = request.headers.get(PROVIDER_HEADER_NAME)
                if not provided or not hmac.compare_digest(provided, expected):
                    return JSONResponse(status_code=401, content={"detail": "Invalid or missing webhook secret"})
            else:
                logger.warning("No provider webhook secret configured for %s; allowing request", provider)
    return await call_next(request)

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Enhanced Pydantic models with validation
class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    
    @validator("email")
    def validate_email(cls, v):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

class SignupRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(default="", description="User first name")
    last_name: str = Field(default="", description="User last name")
    
    @validator("email")
    def validate_email(cls, v):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()
    
    @validator("password")
    def validate_password(cls, v):
        import re
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError("Password must contain at least one special character")
        return v
    
    @validator("first_name", "last_name")
    def validate_names(cls, v):
        if v and len(v.strip()) > 50:
            raise ValueError("Name must be less than 50 characters")
        return v.strip() if v else ""

class UserProfileIn(BaseModel):
    email: str = Field(..., description="User email address")
    first_name: str = Field(..., max_length=50, description="User first name")
    last_name: str = Field(..., max_length=50, description="User last name")
    fireflies_api_key: str | None = Field(None, description="Fireflies API key")
    zoom_jwt: str | None = Field(None, description="Zoom JWT token")
    phone: str | None = Field(None, max_length=20, description="Phone number")
    address: str | None = Field(None, max_length=200, description="Address")
    plan: str | None = Field(None, description="User subscription plan")
    
    @validator("email")
    def validate_email(cls, v):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()
    
    @validator("phone")
    def validate_phone(cls, v):
        if v:
            import re
            # Basic phone validation - allows various formats
            pattern = r'^[\+]?[\d\s\-\(\)]{10,20}$'
            if not re.match(pattern, v):
                raise ValueError("Invalid phone number format")
        return v

class UserProfileOut(BaseModel):
    email: str
    first_name: str
    last_name: str
    name: str  # Computed property from first_name + last_name
    fireflies_api_key: str | None = None
    zoom_jwt: str | None = None
    phone: str | None = None
    address: str | None = None
    plan: str | None = None
    # Admin/roles
    site_admin: bool = False
    org_admin_ids: List[int] = []
    # Current org context for the user
    org_id: int | None = None
    
    class Config:
        from_attributes = True  # Pydantic v2 syntax (replaces orm_mode = True)

# -------------------------
# CRM: Public lead capture (waitlist)
# -------------------------
class LeadPublicIn(BaseModel):
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    source: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    consent_email_opt_in: bool | None = None
    consent_sms_opt_in: bool | None = None
    consent_version: str | None = None

    @validator("email")
    def validate_email(cls, v):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @validator("phone")
    def validate_phone(cls, v):
        if v:
            import re
            pattern = r'^[\+]?[\d\s\-\(\)]{10,20}$'
            if not re.match(pattern, v):
                raise ValueError("Invalid phone number format")
        return v

class LeadOut(BaseModel):
    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    status: str
    source: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    last_contacted_at: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# JWT/session verification dependency
async def verify_jwt_user(request: Request):
    # JWT/session verification dependency (placed before OAuth routes)


    cookie_header = request.headers.get("cookie", "")
    print(f"[Backend] verify_jwt_user - cookie_header: {cookie_header}")
    
    # Check for NextAuth session token
    next_auth_token = None
    session_token = None
    user_token = None
    
    for cookie in cookie_header.split(";"):
        cookie = cookie.strip()
        if cookie.startswith("__Secure-next-auth.session-token="):
            next_auth_token = cookie.split("__Secure-next-auth.session-token=")[1]
            break
        elif cookie.startswith("next-auth.session-token="):
            next_auth_token = cookie.split("next-auth.session-token=")[1]
            break
        elif cookie.startswith("session="):
            session_token = cookie.split("session=")[1]
        elif cookie.startswith("user="):
            user_token = cookie.split("user=")[1]
    
    # Try NextAuth token first
    if next_auth_token:
        print(f"[Backend] verify_jwt_user - Found NextAuth token: {next_auth_token[:20]}...")
        # Prefer Authorization header bearer with email; fallback to x-user-email
        auth_header = request.headers.get("authorization", "")
        email_header = request.headers.get("x-user-email", "")
        email = None
        if auth_header.startswith("Bearer "):
            email = auth_header.split("Bearer ")[1]
        elif email_header:
            email = email_header
        if email:
            user = await get_user_by_email(email)
            if user:
                print(f"[Backend] verify_jwt_user - Verified NextAuth user via headers: {user.email}")
                return user
        # If we had the cookie but no headers, treat as unauthenticated for now
    
    # Legacy session/user cookies
    if session_token or user_token:
        try:
            payload = jwt.decode(user_token or session_token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            user = await get_user_by_email(email)
            if user:
                print(f"[Backend] verify_jwt_user - Successfully verified legacy user: {user.email}")
                return user
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    # Dev-friendly fallback: allow trusted header-based auth in non-production
    if not os.getenv("RAILWAY_ENVIRONMENT"):
    # Dev-friendly fallback: allow trusted header-based auth in non-production


        email_header = request.headers.get("x-user-email", "")
        auth_header = request.headers.get("authorization", "")
        email = email_header or (auth_header.split("Bearer ")[1] if auth_header.startswith("Bearer ") else None)
        if email:
            user = await get_user_by_email(email)
            if user:
                print(f"[Backend] verify_jwt_user - Fallback header auth for {user.email}")
                return user
    print("[Backend] verify_jwt_user - No token found, raising 401")
    raise HTTPException(status_code=401, detail="Not authenticated")


@app.post("/crm/public/leads", response_model=LeadOut)
async def create_public_lead(payload: LeadPublicIn, request: Request):
    """Public endpoint to capture waitlist leads without auth (org_id is null)."""
    try:
        logger.info("[PublicLead] inbound payload: %s", json.dumps(getattr(payload, 'model_dump', lambda: payload.__dict__)(), default=str))
    except Exception as _e:
        logger.info("[PublicLead] inbound payload (raw): %s", str(payload))
    async with AsyncSessionLocal() as session:
        # Try to find existing lead with same email and no org
        result = await session.execute(
            select(Lead).where(Lead.email == payload.email, Lead.org_id == None)  # noqa: E711
        )
        lead = result.scalar_one_or_none()
        if not lead:
            lead = Lead(
                email=payload.email,
                first_name=payload.first_name,
                last_name=payload.last_name,
                phone=payload.phone,
                status='waitlist',
                source=payload.source or 'waitlist-web',
                utm_source=payload.utm_source,
                utm_medium=payload.utm_medium,
                utm_campaign=payload.utm_campaign,
            )
            session.add(lead)
        else:
            # Update basic fields
            lead.first_name = payload.first_name or lead.first_name
            lead.last_name = payload.last_name or lead.last_name
            lead.phone = payload.phone or lead.phone
            lead.source = payload.source or lead.source
            lead.utm_source = payload.utm_source or lead.utm_source
            lead.utm_medium = payload.utm_medium or lead.utm_medium
            lead.utm_campaign = payload.utm_campaign or lead.utm_campaign

        # Record consent if provided
        # Consent meta for audit (timestamp is in Consent.captured_at)
        consent_meta = {
            'ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'consent_version': payload.consent_version,
        }

        if payload.consent_email_opt_in is not None:
            consent_status = 'opted_in' if payload.consent_email_opt_in else 'opted_out'
            consent = Consent(
                lead=lead,
                channel='email',
                status=consent_status,
                source=payload.source or 'waitlist-web',
                meta=consent_meta,
            )
            session.add(consent)
            try:
                logger.info("[PublicLead] email consent recorded: %s", consent_status)
            except Exception:
                pass

        if payload.consent_sms_opt_in is not None:
            sms_status = 'opted_in' if payload.consent_sms_opt_in else 'opted_out'
            sms_consent = Consent(
                lead=lead,
                channel='sms',
                status=sms_status,
                source=payload.source or 'waitlist-web',
                meta=consent_meta,
            )
            session.add(sms_consent)
            try:
                logger.info("[PublicLead] sms consent recorded: %s", sms_status)
            except Exception:
                pass

        await session.commit()
        await session.refresh(lead)
        try:
            logger.info("[PublicLead] persisted lead id=%s email=%s status=%s", str(lead.id), lead.email, lead.status)
        except Exception:
            pass
        # Return lead
        data = lead.to_dict()
        # Pydantic model expects list for tags
        data['tags'] = data.get('tags') or []
        return LeadOut(**data)

# -------------------------
# End CRM endpoints
# -------------------------

# Include leads router
app.include_router(leads_router)
app.include_router(webhooks_router)
app.include_router(clients_router)

"""Review Candidate API (coach scoped)"""
class ReviewCandidateOut(BaseModel):
    id: str
    coach_id: int
    meeting_id: str | None = None
    attendee_source: str | None = None
    raw_email: str | None = None
    raw_phone: str | None = None
    raw_name: str | None = None
    candidate_person_ids: List[str] = []
    reason: str
    status: str
    created_at: datetime | None = None

@app.get("/review/candidates", response_model=List[ReviewCandidateOut])
async def list_candidates(limit: int = 100, status: str | None = 'open', user: User = Depends(verify_jwt_user)):
    coach_id = user.id
    async with AsyncSessionLocal() as session:
        rows = await list_review_candidates(session, coach_id=coach_id, limit=limit, status=status)
        out: List[ReviewCandidateOut] = []
        for r in rows:
            out.append(ReviewCandidateOut(
                id=str(r.id),
                coach_id=r.coach_id,
                meeting_id=str(r.meeting_id) if r.meeting_id else None,
                attendee_source=r.attendee_source,
                raw_email=r.raw_email,
                raw_phone=r.raw_phone,
                raw_name=r.raw_name,
                candidate_person_ids=[str(pid) for pid in (r.candidate_person_ids or [])],
                reason=r.reason,
                status=r.status,
                created_at=r.created_at,
            ))
        return out


class ChoosePersonIn(BaseModel):
    person_id: str

@app.post("/review/candidates/{candidate_id}/choose_person")
async def choose_person(candidate_id: str, payload: ChoosePersonIn, user: User = Depends(verify_jwt_user)):
    async with AsyncSessionLocal() as session:
        # Ensure candidate belongs to coach
        from app.models_meeting_tracking import ReviewCandidate as RC
        rc = (await session.execute(select(RC).where(RC.id == _UUID(candidate_id), RC.coach_id == user.id))).scalar_one_or_none()
        if not rc:
            raise HTTPException(status_code=404, detail="Candidate not found")
        cand = await resolve_review_candidate(
            session,
            candidate_id=_UUID(candidate_id),
            chosen_person_id=_UUID(payload.person_id),
            create_person=False,
        )
        await session.commit()
        return {"id": str(cand.id), "status": cand.status}


class CreatePersonIn(BaseModel):
    # Optionally allow override raw fields (fallback to candidate raw_*)
    email: str | None = None
    phone: str | None = None
    name: str | None = None

@app.post("/review/candidates/{candidate_id}/create_person")
async def create_person_for_candidate(candidate_id: str, payload: CreatePersonIn, user: User = Depends(verify_jwt_user)):
    async with AsyncSessionLocal() as session:
        from app.models_meeting_tracking import ReviewCandidate as RC
        rc = (await session.execute(select(RC).where(RC.id == _UUID(candidate_id), RC.coach_id == user.id))).scalar_one_or_none()
        if not rc:
            raise HTTPException(status_code=404, detail="Candidate not found")
        if payload.email:
            rc.raw_email = payload.email.lower().strip()
        if payload.phone:
            rc.raw_phone = payload.phone
        if payload.name:
            rc.raw_name = payload.name
        await session.flush()
        cand = await resolve_review_candidate(
            session,
            candidate_id=_UUID(candidate_id),
            chosen_person_id=None,
            create_person=True,
        )
        await session.commit()
        return {"id": str(cand.id), "status": cand.status}

# --------------------------------------------------
# OAuth endpoints (defined after verify_jwt_user to avoid forward ref issues)
# --------------------------------------------------
EXPECTED_SCOPES = {
    'google': {"https://www.googleapis.com/auth/calendar.readonly", "openid", "email", "profile"},
    'zoom': {"meeting:read", "user:read"},
    'calendly': {"default"},
    'fireflies': {"meetings.read"},
}

@app.get("/oauth/{provider}/start")
async def oauth_start(provider: str, user: User = Depends(verify_jwt_user)):
    try:
        url = build_auth_url(provider, user.id)
        return RedirectResponse(url)
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


class OAuthCallbackOut(BaseModel):
    provider: str
    linked: bool
    account_id: str | None = None


@app.get("/oauth/{provider}/callback", response_model=OAuthCallbackOut)
async def oauth_callback(provider: str, code: str | None = None, state: str | None = None, error: str | None = None, user: User = Depends(verify_jwt_user)):
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    try:
        token_data = exchange_code(provider, code)
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    scopes_returned = set(token_data.get('scopes') or [])
    expected = EXPECTED_SCOPES.get(provider.lower())
    if expected and not expected.issubset(scopes_returned):
        missing = sorted(expected - scopes_returned)
        raise HTTPException(status_code=400, detail=f"Missing required scopes: {', '.join(missing)}")
    from app.models_meeting_tracking import ExternalAccount
    async with AsyncSessionLocal() as session:
        f = fernet()
        access_enc = f.encrypt(token_data['access_token'].encode()).decode()
        refresh_enc = token_data.get('refresh_token') and f.encrypt(token_data['refresh_token'].encode()).decode()
        import datetime, sqlalchemy as sa
        exp_dt = datetime.datetime.utcfromtimestamp(token_data['expires_at']).replace(tzinfo=datetime.timezone.utc)
        stmt = sa.select(ExternalAccount).where(ExternalAccount.coach_id == user.id, ExternalAccount.provider == provider)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.access_token_enc = access_enc
            if refresh_enc:
                existing.refresh_token_enc = refresh_enc
            existing.scopes = list(scopes_returned)
            existing.external_user_id = token_data.get('external_user_id') or existing.external_user_id
            existing.expires_at = exp_dt
            account_id = existing.id
        else:
            from uuid import uuid4
            acc = ExternalAccount(
                id=uuid4(),
                coach_id=user.id,
                provider=provider,
                access_token_enc=access_enc,
                refresh_token_enc=refresh_enc,
                scopes=list(scopes_returned),
                external_user_id=token_data.get('external_user_id'),
                expires_at=exp_dt,
            )
            session.add(acc)
            account_id = acc.id
        await session.commit()
    return OAuthCallbackOut(provider=provider, linked=True, account_id=str(account_id))

@app.get("/")
def root():
    return {"message": "CoachIntel backend API"}

# -------------------------
# Unsubscribe endpoint using HMAC token
# -------------------------
UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET", SECRET_KEY)
INVITE_SECRET = os.getenv("INVITE_SECRET", SECRET_KEY)

@app.get("/unsubscribe")
async def unsubscribe(request: Request):
    token = request.query_params.get("t")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")
    try:
        data = verify_hmac_token(token, UNSUBSCRIBE_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {e}")

    email = data.get("email")
    channel = data.get("channel", "email")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid payload")

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Lead).where(Lead.email == email))
        lead = res.scalar_one_or_none()
        if not lead:
            # Render a friendly HTML even if not found
            return HTMLResponse("<h3>You have been unsubscribed.</h3>")
        # Record opt-out consent
        session.add(Consent(lead_id=lead.id, channel=channel, status='opted_out', source='unsubscribe-link'))
        await session.commit()
    return HTMLResponse("<h3>You have been unsubscribed.</h3>")

# -------------------------
# Invite links (create/validate/redeem)
# -------------------------

class InviteCreateIn(BaseModel):
    email: str
    expires_in_days: int | None = 14

    @validator("email")
    def _v_email(cls, v):
        import re
        if not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', v or ""):
            raise ValueError("Invalid email")
        return v.lower()

class InviteOut(BaseModel):
    email: str
    token: str
    invite_url: str
    expires_at: int

class InviteRedeemIn(BaseModel):
    token: str

class InviteValidateOut(BaseModel):
    ok: bool
    email: str | None = None
    error: str | None = None

def _require_admin(user: User):
    # Simple guard: site_admin can create invites. Extend as needed.
    if not bool(getattr(user, 'site_admin', False)):
        raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/invites", response_model=InviteOut)
async def create_invite(body: InviteCreateIn, user: User = Depends(verify_jwt_user)):
    _require_admin(user)
    try:
        # Ensure the email exists as a lead (gatekeeping: waitlist vetted)
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Lead).where(Lead.email == body.email))
            lead = res.scalar_one_or_none()
            if not lead:
                raise HTTPException(status_code=400, detail="Lead not found for this email")
            # Optionally flip status to invited
            try:
                if getattr(lead, 'status', None) != 'invited':
                    lead.status = 'invited'
                    lead.last_contacted_at = datetime.utcnow()
                    session.add(lead)
                    await session.commit()
            except Exception:
                # Non-fatal; continue
                pass
        days = body.expires_in_days or 14
        seconds = int(days) * 24 * 60 * 60
        token = sign_invite_token(body.email, INVITE_SECRET, seconds)
        # Decode token body to extract exp using helper that handles padding
        try:
            body_b64 = token.split('.')[0]
            exp = int(json.loads(_b64url_decode(body_b64).decode()).get("exp", 0))
        except Exception:
            # Fallback if decoding fails: compute from now + seconds
            exp = int(time.time()) + seconds
        invite_url = f"{FRONTEND_URL.rstrip('/')}/signup?invite={token}"
        return InviteOut(email=body.email, token=token, invite_url=invite_url, expires_at=exp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create invite: {e}")

@app.get("/invites/validate", response_model=InviteValidateOut)
async def validate_invite(t: str = Query(..., alias="token")):
    try:
        data = verify_hmac_token(t, INVITE_SECRET)
        return InviteValidateOut(ok=True, email=data.get("email"))
    except Exception as e:
        return InviteValidateOut(ok=False, error=str(e))

@app.post("/invites/redeem")
async def redeem_invite(body: InviteRedeemIn):
    try:
        data = verify_hmac_token(body.token, INVITE_SECRET)
        email = (data.get("email") or "").lower()
        if not email:
            raise HTTPException(status_code=400, detail="Invalid invite payload")
        # Create the user shell if not exists; do not set password here, OAuth will verify identity.
        user = await get_user_by_email(email)
        if not user:
            user = await create_or_update_user(email=email, first_name="", last_name="")
        return {"ok": True, "email": email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid invite: {e}")

    # (Removed misplaced EXPECTED_SCOPES block)
@app.get("/external-meetings/{source}/{meeting_id}")
async def get_meeting_details(
    source: str,
    meeting_id: str,
    user: User = Depends(verify_jwt_user)
):
    """
    Get detailed information for a specific meeting.
    
    Path Parameters:
    - source: "fireflies" or "zoom" 
    - meeting_id: ID of the meeting/transcript
    """
    if source == "fireflies":
        fireflies_key = user.fireflies_api_key or os.getenv("FIREFLIES_API_KEY")
        result = await get_fireflies_meeting_details(meeting_id, fireflies_key)
        return result
    elif source == "zoom":
        return {"error": "Zoom meeting details not implemented yet"}
    else:
        return {"error": "Invalid source. Must be 'fireflies' or 'zoom'"}

@app.get("/user/{email}", response_model=UserProfileOut)
async def get_user(email: str):
    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Fetch org_admin_ids
    org_admin_ids: List[int] = []
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(UserOrgRole.org_id).where(
                    UserOrgRole.user_id == user.id,
                    UserOrgRole.role == 'admin'
                )
            )
            org_admin_ids = [row[0] for row in res.fetchall()]
    except Exception as e:
        logger.warning(f"Failed to load org admin roles for {email}: {e}")
    
    return UserProfileOut(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        name=user.name,
        fireflies_api_key=user.fireflies_api_key,
        zoom_jwt=user.zoom_jwt,
        phone=user.phone,
        address=user.address,
        plan=getattr(user, 'plan', None),
        site_admin=bool(getattr(user, 'site_admin', False)),
        org_admin_ids=org_admin_ids,
        org_id=getattr(user, 'org_id', None),
    )

@app.post("/user", response_model=UserProfileOut)
async def upsert_user(profile: UserProfileIn):
    existing = await get_user_by_email(profile.email)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    user = await create_or_update_user(
        email=profile.email,
        first_name=profile.first_name,
        last_name=profile.last_name,
        fireflies_api_key=profile.fireflies_api_key,
        zoom_jwt=profile.zoom_jwt,
        phone=profile.phone,
        address=profile.address,
    )
    # Fetch org_admin_ids (likely empty for new users)
    org_admin_ids: List[int] = []
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(UserOrgRole.org_id).where(
                    UserOrgRole.user_id == user.id,
                    UserOrgRole.role == 'admin'
                )
            )
            org_admin_ids = [row[0] for row in res.fetchall()]
    except Exception as e:
        logger.warning(f"Failed to load org admin roles for {profile.email}: {e}")
    
    return UserProfileOut(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        name=user.name,
        fireflies_api_key=user.fireflies_api_key,
        zoom_jwt=user.zoom_jwt,
        phone=user.phone,
        address=user.address,
        plan=getattr(user, 'plan', None),
        site_admin=bool(getattr(user, 'site_admin', False)),
        org_admin_ids=org_admin_ids,
        org_id=getattr(user, 'org_id', None),
    )

@app.post("/login")
async def login(request: LoginRequest):
    try:
        # Check if user exists
        user = await get_user_by_email(request.email)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid email or password"}
            )
        
        # Verify password (support both hashed and legacy plain text)
        if user.password:
            # Check if password is hashed (starts with hash algorithm prefix)
            if user.password.startswith("$2b$"):
                # Hashed password - verify with bcrypt
                if not verify_password(request.password, user.password):
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid email or password"}
                    )
            else:
                # Legacy plain text password (for backward compatibility)
                if request.password != user.password:
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid email or password"}
                    )
                # Upgrade to hashed password on successful login
                hashed_password = get_password_hash(request.password)
                await create_or_update_user(
                    email=user.email,
                    password=hashed_password
                )
        else:
            # No password set (OAuth-only user)
            return JSONResponse(
                status_code=401,
                content={"error": "Password login not available for this account. Please use Google sign-in."}
            )
        
        # Issue JWT with updated payload structure
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {"sub": request.email, "exp": expire, "userId": user.email, "email": request.email}
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # Return user data for frontend session creation - no longer setting cookies in backend
        response = JSONResponse({
            "token": token, 
            "user": {
                "id": user.email, 
                "email": request.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "name": user.name,
                "plan": getattr(user, 'plan', None)
            }
        })
        
        return response
        
    except ValidationError as e:
        return JSONResponse(
            status_code=422,
            content={"error": "Validation error", "details": e.errors()}
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

@app.post("/signup")
async def signup(request: SignupRequest):
    try:
        # Check if user already exists
        existing_user = await get_user_by_email(request.email)
        if existing_user:
            return JSONResponse(
                status_code=409,
                content={"error": "User with this email exists"}
            )
        
        # Hash the password
        hashed_password = get_password_hash(request.password)
        
        # Create user with hashed password
        user = await create_or_update_user(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            fireflies_api_key=None,
            zoom_jwt=None,
            phone=None,
            address=None,
            password=hashed_password  # Add password field to create_or_update_user
        )
        
        # Issue JWT with updated payload structure
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {"sub": request.email, "exp": expire, "userId": user.email, "email": request.email}
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # Return user data for frontend session creation - no longer setting cookies in backend
        response = JSONResponse({
            "token": token, 
            "user": {
                "id": user.email, 
                "email": request.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "name": user.name,
                "plan": getattr(user, 'plan', None)
            }
        })
        
        return response
        
    except ValidationError as e:
        return JSONResponse(
            status_code=422,
            content={"error": "Validation error", "details": e.errors()}
        )
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to create user"}
        )

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

@app.get("/auth/google")
def google_oauth_start(request: Request):
    token = request.query_params.get("token")
    print(f"[Google OAuth Start] Received token param: {token}")  # Debug log
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile openid",
        "access_type": "offline",
        "prompt": "consent"
    }
    if token:
        params["state"] = token  # Ensure state param is set
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    print(f"[Google OAuth Start] Redirecting to: {url}")  # Debug log
    return RedirectResponse(url)

@app.get("/auth/google/callback")
async def google_oauth_callback(request: Request, code: str, state: str = None):
    # Exchange code for tokens
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        tokens = resp.json()
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)
    expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    # Fetch user info from Google People API
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()
    email = userinfo.get("email")
    first_name = userinfo.get("given_name", "")
    last_name = userinfo.get("family_name", "")
    if not email:
        print("[OAuth Callback] No email found in Google userinfo.")
        return RedirectResponse(f"{FRONTEND_URL}/login?error=no_email")
    # Find or create user
    user = await get_user_by_email(email)
    if not user:
        user = await create_or_update_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            fireflies_api_key=None,
            zoom_jwt=None,
            phone=None,
            address=None
        )
    user.set_google_tokens(access_token, refresh_token, expiry)
    async with AsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
    # Issue JWT and set cookie
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire, "userId": user.email, "email": email}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # Instead of setting cookies in the backend redirect, redirect with token parameter
    # The frontend will create the session from this token
    response = RedirectResponse(f"{FRONTEND_URL}/dashboard?auth_token={token}")
    
    print(f"[Backend] OAuth success - redirecting to frontend with token for user: {email}")
    
    return response

@app.get("/calendar/events")
async def get_calendar_events(user: User = Depends(verify_jwt_user)):
    access_token, refresh_token, expiry = user.get_google_tokens()
    if not access_token:
        raise HTTPException(status_code=401, detail="No Google Calendar token")
    # Refresh token if expired or will expire in next 5 minutes
    refresh_threshold = timedelta(minutes=5)
    now = datetime.utcnow()
    if expiry and expiry < now + refresh_threshold:
        logger.info(f"[TOKEN REFRESH] Google token expired or expiring soon for user {user.email}. Attempting refresh...")
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=data)
            logger.info(f"[TOKEN REFRESH]Google token refresh response status: {resp.status_code}")
            logger.info(f"[TOKEN REFRESH]Google token refresh response body: {resp.text}")
            if resp.status_code != 200:
                logger.error(f"[TOKEN REFRESH]Failed to refresh Google token for user {user.email}: {resp.text}")
                raise HTTPException(status_code=401, detail=f"[TOKEN REFRESH]Failed to refresh Google token: {resp.text}")
            tokens = resp.json()
        access_token = tokens["access_token"]
        expires_in = tokens.get("expires_in", 3600)
        expiry = now + timedelta(seconds=expires_in)
        logger.info(f"[TOKEN REFRESH]Google token refreshed for user {user.email}. New expiry: {expiry}")
        user.set_google_tokens(access_token, refresh_token, expiry)
        async with AsyncSessionLocal() as session:
            session.add(user)
            await session.commit()
    # Fetch next 5 events
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"maxResults": 5, "orderBy": "startTime", "singleEvents": True, "timeMin": datetime.utcnow().isoformat() + "Z"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_CALENDAR_EVENTS_URL, headers=headers, params=params)
        if resp.status_code == 401:
            # Invalid/expired access token and no refresh possible
            raise HTTPException(status_code=401, detail=f"Google API returned 401 Unauthorized: {resp.text}")
        if resp.status_code == 403:
            raise HTTPException(status_code=403, detail=f"Google API returned 403 Forbidden: {resp.text}")
        resp.raise_for_status()
        events = resp.json().get("items", [])
    return {"events": events}
    
@app.post("/auth/nextauth-sync")
async def nextauth_sync(request: Request):
    """Sync NextAuth session data with backend database"""
    try:
        data = await request.json()
        email = data.get("email")
        name = data.get("name", "")
        google_access_token = data.get("googleAccessToken")
        google_refresh_token = data.get("googleRefreshToken")
        google_token_expiry_str = data.get("googleTokenExpiry")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        print(f"[Backend] NextAuth sync for user: {email}")
        
        # Parse expiry date
        google_token_expiry = None
        if google_token_expiry_str:
            try:
                # Parse the datetime with timezone and convert to UTC naive datetime
                google_token_expiry = datetime.fromisoformat(google_token_expiry_str.replace('Z', '+00:00'))
                # Convert to UTC and remove timezone info for database storage
                google_token_expiry = google_token_expiry.utctimetuple()
                google_token_expiry = datetime(*google_token_expiry[:6])
            except ValueError:
                print(f"[Backend] Invalid expiry date format: {google_token_expiry_str}")
        
        # Split name into first/last
        name_parts = name.strip().split(' ', 1) if name else ['', '']
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Get or create user
        user = await get_user_by_email(email)
        if user:
            print(f"[Backend] Updating existing user: {email}")
            # Update existing user with new Google tokens
            if google_access_token:
                user.set_google_tokens(google_access_token, google_refresh_token, google_token_expiry)
            # Update name if provided
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            
            async with AsyncSessionLocal() as session:
                session.add(user)
                await session.commit()
        else:
            print(f"[Backend] Creating new user: {email}")
            # Create new user
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                fireflies_api_key=None,
                zoom_jwt=None,
                phone=None,
                address=None
            )
            if google_access_token:
                user.set_google_tokens(google_access_token, google_refresh_token, google_token_expiry)
            
            async with AsyncSessionLocal() as session:
                session.add(user)
                await session.commit()
        
        print(f"[Backend] NextAuth sync completed for user: {email}")
        return {"success": True, "message": "User synced successfully"}
        
    except Exception as e:
        print(f"[Backend] NextAuth sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@app.post("/logout")
async def logout():
    """Clear the authentication cookies"""
    print("[Backend] Logout endpoint called")
    response = JSONResponse({"message": "Logged out successfully"})
    
    # Cookie settings for clearing
    cookie_clear_settings = {
        "httponly": True,
        "max_age": 0,
        "samesite": "lax",  # Use lax for both dev and prod for better compatibility
        "secure": True if os.getenv("RAILWAY_ENVIRONMENT") else False,
        "path": "/",
        "domain": ".coachintel.ai" if os.getenv("RAILWAY_ENVIRONMENT") else None
    }
    
    # Clear both old "user" cookie and new "session" cookie
    response.set_cookie(key="user", value="", **cookie_clear_settings)
    response.set_cookie(key="session", value="", **cookie_clear_settings)
    
    print(f"[Backend] Both cookies cleared with secure={True if os.getenv('RAILWAY_ENVIRONMENT') else False}, samesite={'strict' if os.getenv('RAILWAY_ENVIRONMENT') else 'lax'}")
    return response

@app.get("/me")
async def get_current_user(user: User = Depends(verify_jwt_user)):
    print(f"[Backend] /me endpoint called for user: {user.email}")
    response = JSONResponse({
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "name": user.name,
        "fireflies_api_key": user.fireflies_api_key,
        "zoom_jwt": user.zoom_jwt,
        "phone": user.phone,
        "address": user.address,
        "plan": getattr(user, 'plan', None)
    })
    # Prevent caching of user data
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.options("/user")
async def options_user():
    return {"status": "ok"}

@app.put("/user")  # Remove response_model to avoid serialization issues
async def update_user_profile(request: Request):
    # Extract NextAuth session token or user email from headers
    cookie_header = request.headers.get("cookie", "")
    user_email = request.headers.get("x-user-email", "")
    
    # Check for NextAuth session token first
    next_auth_token = None
    legacy_token = None
    
    for cookie in cookie_header.split(";"):
        cookie = cookie.strip()
        if cookie.startswith("__Secure-next-auth.session-token="):
            next_auth_token = cookie.split("__Secure-next-auth.session-token=")[1]
            break
        elif cookie.startswith("next-auth.session-token="):
            next_auth_token = cookie.split("next-auth.session-token=")[1]
            break
        elif cookie.startswith("user="):
            legacy_token = cookie.split("user=")[1]
    
    email = None
    
    # Require NextAuth cookie + header combo, or legacy JWT
    if next_auth_token and user_email:
        email = user_email
        print(f"[Backend] update_user_profile - Using NextAuth session for user: {email}")
    elif legacy_token:
        # Fallback to legacy JWT verification
        try:
            payload = jwt.decode(legacy_token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            print(f"[Backend] update_user_profile - Using legacy JWT for user: {email}")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    if not email:
        raise HTTPException(status_code=401, detail="No authentication token or user email")
    try:
        data = await request.json()

        # Prevent upgrading to paid plans until billing is implemented
        requested_plan = data.get("plan")
        if requested_plan in {"plus", "pro"}:
            # Explicitly reject paid upgrades for now
            raise HTTPException(status_code=402, detail="Payment required to upgrade plan")
        elif requested_plan not in {None, "free"}:
            # Sanitize any unexpected value
            requested_plan = None

        user = await create_or_update_user(
            email=email,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            fireflies_api_key=data.get("fireflies_api_key"),
            zoom_jwt=data.get("zoom_jwt"),
            phone=data.get("phone"),
            address=data.get("address"),
            plan=requested_plan,
        )
        return {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "name": user.name,
            "fireflies_api_key": user.fireflies_api_key,
            "zoom_jwt": user.zoom_jwt,
            "phone": user.phone,
            "address": user.address,
            "plan": getattr(user, 'plan', None)
        }
    except HTTPException:
        # Re-raise HTTPExceptions like 402 without wrapping
        raise
    except Exception as e:
        print(f"[Backend] update_user_profile - Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user profile")

@app.get("/meetings/")
async def get_user_meetings(user: User = Depends(verify_jwt_user)):
    # Query meetings for this user (and org if available)
    async with AsyncSessionLocal() as session:
        filters = [Meeting.user_id == user.id]
        if getattr(user, 'org_id', None) is not None:
            filters.append(Meeting.org_id == user.org_id)
        result = await session.execute(
            select(Meeting).options(selectinload(Meeting.transcript)).where(*filters)
        )
        meetings = result.scalars().all()
        meeting_list = []
        for m in meetings:
            transcript = None
            if m.transcript:
                transcript = {
                    "full_text": m.transcript.full_text,
                    "summary": m.transcript.summary,
                    "action_items": m.transcript.action_items,
                }
            # Always send ISO 8601 string with Z (UTC) if datetime is not None
            date_str = m.date.isoformat() + 'Z' if m.date and m.date.tzinfo is None else m.date.isoformat() if m.date else None
            meeting_list.append({
                "id": m.id,
                "client_name": m.client_name,
                "title": m.title,
                "date": date_str,
                "duration": m.duration,
                "source": m.source,
                "transcript": transcript
            })
        return {"meetings": meeting_list}

@app.post("/sync/external-meetings")
async def sync_external_meetings(
    source: str = Query(..., description="fireflies | fireflies_transcripts | zoom | google"),
    limit: int = Query(50, ge=1, le=500, description="Max items to ingest (where supported)"),
    meeting_ids: List[str] | None = Body(None, description="Optional list of meeting IDs (zoom reports)"),
    user: User = Depends(verify_jwt_user),
):
    """Dispatch provider-specific ingestion tasks for the authenticated coach.

    Supported sources:
      - fireflies:      legacy meeting + transcript sync (per-user API key) [deprecated]
      - fireflies_transcripts: attendee/client enrichment from transcripts (preferred)
      - zoom:           zoom reports for provided meeting_ids
      - google:         calendar window sync (24h back -> +7d forward)

    Returns JSON with task_id and source.
    """
    _lazy_load_worker()
    user_profile = await get_user_by_email(user.email)
    if not user_profile:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    # Normalize alias
    if source == "fireflies":
        # If API key missing, error early
        if not user_profile.fireflies_api_key:
            return JSONResponse(status_code=400, content={"error": "Fireflies API key not found"})
        try:
            task = sync_fireflies_meetings.delay(user.email, user_profile.fireflies_api_key)  # type: ignore
            return {"task_id": task.id, "status": "queued", "source": source, "mode": "legacy"}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Task queue unavailable: {e}")

    if source == "fireflies_transcripts":
        if not user_profile.fireflies_api_key:
            return JSONResponse(status_code=400, content={"error": "Fireflies API key not found"})
        try:
            from app import worker  # lazy
            task = worker.ingest_fireflies_transcripts.delay(user.id, limit)  # type: ignore
            return {"task_id": task.id, "status": "queued", "source": source}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Task queue unavailable: {e}")

    if source == "zoom":
        if not meeting_ids:
            return JSONResponse(status_code=400, content={"error": "meeting_ids required for zoom"})
        try:
            from app import worker
            task = worker.sync_zoom_reports.delay(user.id, meeting_ids)  # type: ignore
            return {"task_id": task.id, "status": "queued", "source": source, "count": len(meeting_ids)}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Task queue unavailable: {e}")

    if source == "google":
        try:
            from app import worker
            task = worker.sync_google_calendar.delay(user.id)  # type: ignore
            return {"task_id": task.id, "status": "queued", "source": source}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Task queue unavailable: {e}")

    return JSONResponse(status_code=400, content={"error": "Unsupported source"})


@app.post("/sync/fireflies/transcripts")
async def sync_fireflies_transcripts(limit: int = 200, user: User = Depends(verify_jwt_user)):
    """Trigger Fireflies transcripts attendee ingestion for the authenticated coach.

    This pushes a Celery task (ingest_fireflies_transcripts) that enumerates transcripts and upserts attendees into the client index.
    """
    try:
        _lazy_load_worker()
        if not user.fireflies_api_key:
            return JSONResponse(status_code=400, content={"error": "Fireflies API key not configured"})
        # ingest_fireflies_transcripts symbol bound during lazy load
        from app import worker  # local import to access task function attribute if needed
        task = worker.ingest_fireflies_transcripts.delay(user.id, limit)  # type: ignore
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        logger.warning(f"[FirefliesTranscriptsSync] error user={user.id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/sync/status/{task_id}")
def get_sync_status(task_id: str, request: Request):
    # logger.info(f"[SYNC STATUS] Endpoint called for task ID: {task_id} from {request.client.host}:{request.client.port} at {time.time()}")
    # logger.info(f"[SYNC STATUS] All headers: {dict(request.headers)}")
    from .worker import celery_app  # Ensure using the same Celery app instance
    now = time.time()
    result = AsyncResult(task_id, app=celery_app)
    # logger.info(f"[SYNC STATUS] Result: status={result.status}, ready={result.ready()}, successful={result.successful()}, result={result.result}, task_name={getattr(result, 'task_name', None)}")
    response = {"task_id": task_id, "status": result.status, "ready": result.ready(), "successful": result.successful(), "timestamp": now, "task_name": getattr(result, 'task_name', None)}
    if result.status == "FAILURE":
        # logger.error(f"[SYNC STATUS] Task failed: {result.result}")
        response["error"] = str(result.result)
    elif result.status == "SUCCESS":
        if isinstance(result.result, str):
            try:
                parsed = json.loads(result.result)
                if isinstance(parsed, dict):
                    response["summary"] = parsed.get("status") or parsed
                else:
                    response["summary"] = parsed
            except Exception as e:
                # logger.warning(f"[SYNC STATUS] Could not parse string result: {e}")
                response["summary"] = result.result
        elif isinstance(result.result, dict):
            response["summary"] = result.result.get("status") or result.result
        else:
            response["summary"] = result.result
    else:
        # logger.info(f"[SYNC STATUS] Task not complete: status={result.status}")
        pass
    return JSONResponse(content=response, headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache"
    })

@app.get("/test-fireflies")
async def test_fireflies_connection(user: User = Depends(verify_jwt_user)):
    """
    Test Fireflies API key for the authenticated user by making a minimal API call.
    Returns success/failure based on Fireflies API response.
    """
    api_key = user.fireflies_api_key
    if not api_key:
        return JSONResponse(status_code=400, content={"success": False, "error": "No Fireflies API key found for user."})
    result = await test_fireflies_api_key(api_key)
    if result.get("error"):
        return JSONResponse(status_code=400, content={"success": False, "error": result["error"], "details": result.get("details")})
    return {"success": True}

@app.get("/meetings/{meeting_id}")
async def get_meeting_with_transcript(meeting_id: str, user: User = Depends(verify_jwt_user)):
    """
    Return meeting details and full transcript for a given meeting ID (for the authenticated user).
    Logs detailed errors if not found.
    """
    async with AsyncSessionLocal() as session:
        filters = [Meeting.id == meeting_id, Meeting.user_id == user.id]
        if getattr(user, 'org_id', None) is not None:
            filters.append(Meeting.org_id == user.org_id)
        result = await session.execute(
            select(Meeting).options(selectinload(Meeting.transcript)).where(*filters)
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            logging.error(f"Meeting not found: id={meeting_id}, user_id={user.id}, org_id={getattr(user, 'org_id', None)}")
            # Optionally, check if meeting exists for any user
            other_result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
            other_meeting = other_result.scalar_one_or_none()
            if other_meeting:
                logging.error(f"Meeting id={meeting_id} exists but not for user_id={user.id} and org_id={getattr(user, 'org_id', None)}")
            return {"error": "Meeting not found"}
        transcript = None
        if meeting.transcript:
            transcript = {
                "full_text": meeting.transcript.full_text,
                "summary": meeting.transcript.summary,
                "action_items": meeting.transcript.action_items,
            }
        date_str = meeting.date.isoformat() + 'Z' if meeting.date and meeting.date.tzinfo is None else meeting.date.isoformat() if meeting.date else None
        return {
            "id": meeting.id,
            "client_name": meeting.client_name,
            "title": meeting.title,
            "date": date_str,
            "duration": meeting.duration,
            "source": meeting.source,
            "participants": meeting.participants,
            "transcript": transcript
        }

@app.get("/health")
async def health():
    # Check DB
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(1))
    except Exception as e:
        return {"ok": False, "db": False, "error": str(e)}

    # Check Redis broker with a lightweight ping using Celery connection
    try:
        with celery_app.connection_or_acquire() as conn:
            # For Redis, a simple ensure_connection triggers a PING under the hood
            conn.ensure_connection(max_retries=1)
    except Exception as e:
        return {"ok": False, "celery": False, "error": str(e)}

    return {"ok": True, "db": True, "celery": True}

# Plan guard helper
ALLOWED_PLANS = {"free", "plus", "pro"}

def require_plan(user: User, allowed: set[str]):
    plan = getattr(user, 'plan', None) or 'free'
    if plan not in ALLOWED_PLANS:
        plan = 'free'
    if plan not in allowed:
        raise HTTPException(status_code=403, detail=f"Plan '{plan}' is not permitted for this action")



@app.post("/summarize-missing-transcripts", status_code=status.HTTP_202_ACCEPTED)
async def trigger_summarize_missing_transcripts(user: User = Depends(verify_jwt_user)):
    """
    Trigger the Celery task to summarize all missing transcripts for eligible users.
    Requires plan: plus or pro.
    Returns the Celery task id.
    """
    # Enforce plan: Free cannot summarize
    require_plan(user, {"plus", "pro"})
    result = celery_app.send_task('app.worker.summarize_missing_transcripts')
    return {"task_id": result.id, "status": "started"}

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...), user: User = Depends(verify_jwt_user)):
    """Upload audio for transcription (Pro only)."""
    require_plan(user, {"pro"})
    try:
      # For now, accept the file and return 202; storage/transcription handled elsewhere
      size = 0
      chunk = await file.read()
      size = len(chunk)
      return JSONResponse(status_code=202, content={"status": "received", "filename": file.filename, "size": size})
    except Exception as e:
      raise HTTPException(status_code=400, detail=f"Upload failed: {e}")

@app.post("/transcribe/")
async def transcribe(user: User = Depends(verify_jwt_user)):
    """Trigger transcription for an uploaded asset (Pro only)."""
    require_plan(user, {"pro"})
    # Not implemented yet; return 202 to indicate accepted
    return JSONResponse(status_code=202, content={"status": "accepted"})

# -------------------------
# Postmark webhook and event recorder
# -------------------------

async def record_event(lead: Lead, type: str, channel: str = 'email', provider_id: str | None = None, meta: dict | None = None):
    async with AsyncSessionLocal() as session:
        ev = MessageEvent(lead_id=lead.id, channel=channel, type=type, provider_id=provider_id, meta=meta or {})
        session.add(ev)
        await session.commit()

@app.post("/webhooks/postmark")
async def postmark_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message_id = payload.get("MessageID") or payload.get("Message-Id")
    email = (payload.get("Recipient") or payload.get("Email") or "").lower()
    event_type = payload.get("RecordType") or payload.get("Type")

    if not email or not event_type:
        return JSONResponse(status_code=200, content={"ok": True})

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Lead).where(Lead.email == email))
        lead = res.scalar_one_or_none()
        if not lead:
            return JSONResponse(status_code=200, content={"ok": True})
        # Map Postmark events
        event_map = {
            'Open': 'open',
            'Click': 'click',
            'Bounce': 'bounce',
            'SpamComplaint': 'complaint',
            'Delivery': 'send',
            'Transient': 'bounce',
            'Permanent': 'bounce',
        }
        mapped = event_map.get(event_type, None)
        if mapped:
            await record_event(lead, mapped, channel='email', provider_id=message_id, meta=payload)
            # If bounce/complaint, auto opt-out
            if mapped in {"bounce", "complaint"}:
                session.add(Consent(lead_id=lead.id, channel='email', status='opted_out', source='postmark-webhook'))
                await session.commit()

    return JSONResponse(status_code=200, content={"ok": True})

# -------------------------
# Org Admin management (list/add/remove)
# -------------------------
class OrgAdminAddIn(BaseModel):
    user_email: str

async def _is_org_admin(user_id: int, org_id: int) -> bool:
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(UserOrgRole.id).where(
                    UserOrgRole.user_id == user_id,
                    UserOrgRole.org_id == org_id,
                    UserOrgRole.role == 'admin'
                )
            )
            return res.first() is not None
    except Exception:
        return False

@app.get("/orgs/{org_id}/admins")
async def list_org_admins(org_id: int, user: User = Depends(verify_jwt_user)):
    # Allow site admins or org admins of this org
    if not bool(getattr(user, 'site_admin', False)) and not await _is_org_admin(user.id, org_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User).join(UserOrgRole, UserOrgRole.user_id == User.id)
            .where(UserOrgRole.org_id == org_id, UserOrgRole.role == 'admin')
            .order_by(User.id)
        )
        users = res.scalars().all()
        return [{"id": u.id, "email": u.email, "first_name": u.first_name, "last_name": u.last_name} for u in users]

@app.post("/orgs/{org_id}/admins")
async def add_org_admin(org_id: int, payload: OrgAdminAddIn, user: User = Depends(verify_jwt_user)):
    if not bool(getattr(user, 'site_admin', False)) and not await _is_org_admin(user.id, org_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    # Find or create target user by email
    target = await get_user_by_email(payload.user_email)
    if not target:
        target = await create_or_update_user(email=payload.user_email, first_name="", last_name="")
        if not target:
            raise HTTPException(status_code=400, detail="Failed to create target user")
    async with AsyncSessionLocal() as session:
        # Idempotent upsert
        res = await session.execute(
            select(UserOrgRole).where(
                UserOrgRole.user_id == target.id,
                UserOrgRole.org_id == org_id,
                UserOrgRole.role == 'admin'
            )
        )
        role = res.scalar_one_or_none()
        if not role:
            session.add(UserOrgRole(user_id=target.id, org_id=org_id, role='admin'))
            await session.commit()
    return {"ok": True, "user_id": target.id}

@app.delete("/orgs/{org_id}/admins/{target_user_id}")
async def remove_org_admin(org_id: int, target_user_id: int, user: User = Depends(verify_jwt_user)):
    if not bool(getattr(user, 'site_admin', False)) and not await _is_org_admin(user.id, org_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserOrgRole).where(
                UserOrgRole.user_id == target_user_id,
                UserOrgRole.org_id == org_id,
                UserOrgRole.role == 'admin'
            )
        )
        role = res.scalar_one_or_none()
        if role:
            await session.delete(role)
            await session.commit()
    return {"ok": True}

# -------------------------
# End Org Admin management
# -------------------------
