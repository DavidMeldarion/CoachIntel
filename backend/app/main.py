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
)
from app.integrations import get_fireflies_meeting_details, test_fireflies_api_key
from app.worker import celery_app, sync_fireflies_meetings
from .config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URL, GOOGLE_CALENDAR_EVENTS_URL

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

logger = logging.getLogger("coachintel")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)

# Log CORS configuration for debugging
logger.info(f"CORS configured for origins: {['http://localhost:3000', 'http://127.0.0.1:3000'] + frontend_origins}")

app = FastAPI(
    title="CoachIntel API",
    root_path="/",
    # Trust proxy headers for proper URL generation
    servers=[{"url": "https://api.coachintel.ai", "description": "Production server"}] if os.getenv("RAILWAY_ENVIRONMENT") else None
)

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

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

@app.post("/crm/public/leads", response_model=LeadOut)
async def create_public_lead(payload: LeadPublicIn):
    """Public endpoint to capture waitlist leads without auth (org_id is null)."""
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
        if payload.consent_email_opt_in is not None:
            consent_status = 'opted_in' if payload.consent_email_opt_in else 'opted_out'
            consent = Consent(
                lead=lead,
                channel='email',
                status=consent_status,
                source=payload.source or 'waitlist-web',
            )
            session.add(consent)

        await session.commit()
        await session.refresh(lead)
        # Return lead
        data = lead.to_dict()
        # Pydantic model expects list for tags
        data['tags'] = data.get('tags') or []
        return LeadOut(**data)

# -------------------------
# End CRM endpoints
# -------------------------

# JWT/session verification dependency
async def verify_jwt_user(request: Request):
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
    
    print("[Backend] verify_jwt_user - No token found, raising 401")
    raise HTTPException(status_code=401, detail="Not authenticated")

@app.get("/")
def root():
    return {"message": "CoachIntel backend API"}

# Secure endpoints
# @app.post("/upload-audio/")
# async def upload_audio(file: UploadFile = File(...), user: User = Depends(verify_jwt_user)):
#     # Dummy: Save file, trigger transcription job
#     return {"filename": file.filename, "status": "received"}

# @app.get("/sessions/")
# async def get_sessions(user: User = Depends(verify_jwt_user)):
#     # Dummy: Return list of sessions
#     return [{"id": 1, "summary": "Session 1 summary"}]

# @app.post("/transcribe/")
# async def transcribe(user: User = Depends(verify_jwt_user)):
#     # Dummy: Trigger transcription
#     return {"status": "transcription started"}

# @app.post("/summarize/")
# async def summarize(user: User = Depends(verify_jwt_user)):
#     # Dummy: Trigger summarization
#     return {"status": "summarization started"}

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
    
    return UserProfileOut(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        name=user.name,
        fireflies_api_key=user.fireflies_api_key,
        zoom_jwt=user.zoom_jwt,
        phone=user.phone,
        address=user.address,
        plan=getattr(user, 'plan', None)
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
    
    return UserProfileOut(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        name=user.name,
        fireflies_api_key=user.fireflies_api_key,
        zoom_jwt=user.zoom_jwt,
        phone=user.phone,
        address=user.address,
        plan=getattr(user, 'plan', None)
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
async def sync_external_meetings(source: str = Query(..., description="fireflies or zoom"), user: User = Depends(verify_jwt_user)):
    """
    Trigger background sync of Fireflies or Zoom meetings for the authenticated user.
    Persists meetings to the database via Celery task.
    Returns status and task ID.
    """
    # logger.info(f"[SYNC DEBUG] Sync requested for user: {user.email}, source: {source}")
    # Get user profile
    user_profile = await get_user_by_email(user.email)
    if not user_profile:
        logger.error(f"[SYNC DEBUG] User not found: {user.email}")
        return {"error": "User not found"}
    # Trigger Celery task
    if source == "fireflies":
        if not user_profile.fireflies_api_key:
            logger.warning(f"[SYNC DEBUG] No Fireflies API key for user: {user.email}")
            return {"error": "Fireflies API key not found"}
        try:
            task = sync_fireflies_meetings.delay(user.email, user_profile.fireflies_api_key)
        except Exception as e:
            logger.error(f"[SYNC ERROR] Failed to enqueue Celery task: {e}")
            raise HTTPException(status_code=503, detail="Task queue unavailable")
        # logger.info(f"[SYNC DEBUG] Fireflies sync task triggered: {task.id}")
        return {"status": "sync started", "task_id": task.id, "source": source}
    elif source == "zoom":
        logger.error(f"[SYNC DEBUG] Zoom sync is not implemented.")
        return {"error": "Zoom sync is not implemented yet"}
    else:
        logger.error(f"[SYNC DEBUG] Invalid source: {source}")
        return {"error": "Invalid source. Must be 'fireflies' or 'zoom'"}

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
# CRM: Leads router
# -------------------------
leads_router = APIRouter(prefix="/leads", tags=["leads"])

ALLOWED_LEAD_STATUS = {"waitlist", "invited", "converted", "lost"}

class LeadCreate(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    tags: Optional[List[str]] = None
    consent_email: Optional[bool] = None
    consent_sms: Optional[bool] = None

    @validator("email")
    def _valid_email(cls, v):
        import re
        if not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', v or ""):
            raise ValueError("Invalid email format")
        return v.lower()

    @validator("phone")
    def _valid_phone(cls, v):
        if v:
            import re
            if not re.match(r'^[\+]?[\d\s\-\(\)]{10,20}$', v):
                raise ValueError("Invalid phone number format")
        return v

class LeadOut(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str
    tags: List[str] | None = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LeadDetailOut(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str
    tags: List[str] | None = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None
    events: Optional[List[dict]] = None

class LeadStatusUpdate(BaseModel):
    status: str

# Paged response for listing leads
class LeadsPageOut(BaseModel):
    items: List[LeadOut]
    total: int
    limit: int
    offset: int

class LeadNotesIn(BaseModel):
    notes: Optional[str] = None

@leads_router.post("/", response_model=LeadOut)
async def upsert_lead(
    payload: LeadCreate,
    user: User = Depends(verify_jwt_user),
):
    """Upsert a lead by email within the same org. If new, set status=waitlist and
    record consent rows for provided email/sms booleans."""
    org_id = getattr(user, 'org_id', None)
    async with AsyncSessionLocal() as session:
        # Find existing by (org_id, email)
        result = await session.execute(
            select(Lead).where(
                Lead.email == payload.email,
                Lead.org_id == (org_id if org_id is not None else None)  # noqa: E711
            )
        )
        lead = result.scalar_one_or_none()
        is_new = lead is None
        if is_new:
            lead = Lead(
                email=payload.email,
                first_name=payload.first_name,
                last_name=payload.last_name,
                phone=payload.phone,
                status='waitlist',
                source=payload.source,
                utm_source=payload.utm_source,
                utm_medium=payload.utm_medium,
                utm_campaign=payload.utm_campaign,
            )
            if org_id is not None:
                lead.org_id = org_id
            if payload.tags:
                # normalize tags
                norm_tags = [t.strip() for t in payload.tags if t and t.strip()]
                lead.tags = norm_tags
            session.add(lead)
        else:
            # Update fields
            lead.first_name = payload.first_name or lead.first_name
            lead.last_name = payload.last_name or lead.last_name
            lead.phone = payload.phone or lead.phone
            lead.source = payload.source or lead.source
            lead.utm_source = payload.utm_source or lead.utm_source
            lead.utm_medium = payload.utm_medium or lead.utm_medium
            lead.utm_campaign = payload.utm_campaign or lead.utm_campaign
            if payload.tags is not None:
                lead.tags = [t.strip() for t in payload.tags if t and t.strip()]

        # Consents (append history entries)
        def _add_consent(channel: str, opted: bool):
            c = Consent(
                lead=lead,
                channel=channel,
                status='opted_in' if opted else 'opted_out',
                source=payload.source or 'leads-api',
            )
            if org_id is not None:
                c.org_id = org_id
            session.add(c)

        if payload.consent_email is not None:
            _add_consent('email', payload.consent_email)
        if payload.consent_sms is not None:
            _add_consent('sms', payload.consent_sms)

        await session.commit()
        await session.refresh(lead)

        return LeadOut(
            id=str(lead.id),
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            status=lead.status,
            tags=list(lead.tags or []),
            created_at=lead.created_at,
        )

@leads_router.get("/", response_model=LeadsPageOut)
async def list_leads(
    q: Optional[str] = Query(default=None, description="Search email or name"),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(verify_jwt_user),
):
    """Search and list leads for the user's org with pagination metadata.
    Returns a paged object containing items and total.
    """
    org_id = getattr(user, 'org_id', None)
    async with AsyncSessionLocal() as session:
        conditions = []
        if org_id is not None:
            conditions.append(Lead.org_id == org_id)
        else:
            conditions.append(Lead.org_id == None)  # noqa: E711
        if status:
            if status not in ALLOWED_LEAD_STATUS:
                raise HTTPException(status_code=400, detail="Invalid status filter")
            conditions.append(Lead.status == status)
        if q:
            like = f"%{q.lower()}%"
            conditions.append(
                or_(
                    Lead.email.ilike(like),
                    Lead.first_name.ilike(like),
                    Lead.last_name.ilike(like),
                )
            )
        # Total count
        count_stmt = select(func.count()).select_from(Lead).where(*conditions)
        total_res = await session.execute(count_stmt)
        total = int(total_res.scalar() or 0)
        # Page of items
        data_stmt = (
            select(Lead)
            .where(*conditions)
            .order_by(Lead.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(data_stmt)
        rows = result.scalars().all()
        items = [
            LeadOut(
                id=str(l.id),
                email=l.email,
                first_name=l.first_name,
                last_name=l.last_name,
                status=l.status,
                tags=list(l.tags or []),
                created_at=l.created_at,
            )
            for l in rows
        ]
        return LeadsPageOut(items=items, total=total, limit=limit, offset=offset)

@leads_router.get("/{lead_id}", response_model=LeadDetailOut)
async def get_lead_detail(
    lead_id: UUID_t,
    user: User = Depends(verify_jwt_user),
):
    org_id = getattr(user, 'org_id', None)
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.id == lead_id)
        if org_id is not None:
            stmt = stmt.where(Lead.org_id == org_id)
        else:
            stmt = stmt.where(Lead.org_id == None)  # noqa: E711
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        # fetch events separately, most recent first
        evt_stmt = (
            select(MessageEvent)
            .where(MessageEvent.lead_id == lead.id)
            .order_by(MessageEvent.occurred_at.desc())
            .limit(100)
        )
        ev_res = await session.execute(evt_stmt)
        evs = ev_res.scalars().all()
        return LeadDetailOut(
            id=str(lead.id),
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            status=lead.status,
            tags=list(lead.tags or []),
            created_at=lead.created_at,
            notes=lead.notes,
            events=[{"type": e.type, "occurred_at": e.occurred_at} for e in evs],
        )

@leads_router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead_notes(
    lead_id: UUID_t,
    body: LeadNotesIn,
    user: User = Depends(verify_jwt_user),
):
    org_id = getattr(user, 'org_id', None)
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.id == lead_id)
        if org_id is not None:
            stmt = stmt.where(Lead.org_id == org_id)
        else:
            stmt = stmt.where(Lead.org_id == None)  # noqa: E711
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.notes = (body.notes or '').strip()
        await session.commit()
        await session.refresh(lead)
        return LeadOut(
            id=str(lead.id),
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            status=lead.status,
            tags=list(lead.tags or []),
            created_at=lead.created_at,
        )

@leads_router.post("/{lead_id}/status", response_model=LeadOut)
async def update_lead_status(
    lead_id: UUID_t,
    body: LeadStatusUpdate,
    user: User = Depends(verify_jwt_user),
):
    """Update a lead's status after validating it is one of the allowed values."""
    if body.status not in ALLOWED_LEAD_STATUS:
        raise HTTPException(status_code=400, detail="Invalid status value")
    org_id = getattr(user, 'org_id', None)
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.id == lead_id)
        if org_id is not None:
            stmt = stmt.where(Lead.org_id == org_id)
        else:
            stmt = stmt.where(Lead.org_id == None)  # noqa: E711
        result = await session.execute(stmt)
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.status = body.status
        await session.commit()
        await session.refresh(lead)
        return LeadOut(
            id=str(lead.id),
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            status=lead.status,
            tags=list(lead.tags or []),
            created_at=lead.created_at,
        )

# Helper to record message events (for provider callbacks or after sending)
async def record_event(lead_id: str, channel: str, type: str, meta: dict | None = None, provider_id: str | None = None):
    """Insert a MessageEvent row for a lead.
    channel: 'email'|'sms'; type: 'send'|'open'|'click'|'bounce'|'complaint'
    """
    async with AsyncSessionLocal() as session:
        evt = MessageEvent(
            lead_id=lead_id,
            channel=channel,
            type=type,
            provider_id=provider_id,
            meta=meta or {},
        )
        session.add(evt)
        await session.commit()

# -------------------------
# Small HMAC util
# -------------------------
_DEF_PAD = {0: '', 2: '==', 3: '='}

def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip('=')

def _b64url_decode(s: str) -> bytes:
    pad = _DEF_PAD[len(s) % 4]
    return base64.urlsafe_b64decode(s + pad)

def sign_hmac_token(text: str) -> str:
    mac = hmac.new(SECRET_KEY.encode('utf-8'), text.encode('utf-8'), hashlib.sha256).digest()
    return _b64url_encode(mac)

def verify_hmac_token(text: str, token: str) -> bool:
    try:
        expected = sign_hmac_token(text)
        # Constant-time compare
        return hmac.compare_digest(expected, token)
    except Exception:
        return False

# -------------------------
# Unsubscribe endpoint
# -------------------------
@app.get("/unsubscribe")
async def unsubscribe(lead_id: str, token: str):
    """
    GET /unsubscribe?lead_id=...&token=...
    Token is base64url(HMAC_SHA256(lead_id, SECRET_KEY)). If valid, mark email consent as opted_out
    by inserting a new Consent(channel='email', status='opted_out'). Always render a tiny HTML page.
    """
    valid = verify_hmac_token(lead_id, token)
    # Default message regardless of validity to avoid leaking info
    html = "<html><body><p>You're unsubscribed.</p></body></html>"
    if not valid:
        return HTMLResponse(content=html, status_code=200)

    # Proceed to flip consent
    try:
        lid = UUID_t(lead_id)
    except Exception:
        return HTMLResponse(content=html, status_code=200)

    try:
        async with AsyncSessionLocal() as session:
            # Find lead
            result = await session.execute(select(Lead).where(Lead.id == lid))
            lead = result.scalar_one_or_none()
            if lead:
                c = Consent(
                    lead_id=lead.id,
                    org_id=getattr(lead, 'org_id', None),
                    channel='email',
                    status='opted_out',
                    source='unsubscribe',
                )
                session.add(c)
                await session.commit()
                # Optionally record a complaint event? Spec only requires consent change.
        return HTMLResponse(content=html, status_code=200)
    except Exception:
        # Do not log PII; intentionally swallow details
        return HTMLResponse(content=html, status_code=200)

# -------------------------
# Webhooks: Postmark
# -------------------------
@app.post("/webhooks/postmark")
async def postmark_webhook(request: Request):
    """
    Accept Postmark webhooks and record events.
    Expected JSON shapes (examples):
    - Bounce:
      {
        "RecordType": "Bounce",
        "Type": "HardBounce" | "SpamComplaint" | ...,
        "MessageID": "<uuid>",
        "Email": "user@example.com",
        "Tag": "optional-tag",
        "ServerID": 12345,
        "Description": "...",
        "BouncedRecipients": [{"Email": "user@example.com"}],
        "Metadata": {"lead_id": "<uuid>"}
      }
    - Delivery/Open/Click events exist, but here we map only bounces and complaints.
    """
    try:
        payload = await request.json()
    except Exception:
        # Malformed JSON; ignore
        return JSONResponse(status_code=400, content={"ok": False})

    # Avoid logging PII; only log minimal type info
    rec_type = str(payload.get("RecordType", "")).lower()
    p_type = str(payload.get("Type", "")).lower()

    # Only process bounces and spam complaints
    if rec_type != "bounce":
        return JSONResponse({"ok": True})

    event_type = None
    if p_type == "spamcomplaint":
        event_type = "complaint"
    else:
        event_type = "bounce"

    # Attempt to resolve lead: prefer metadata.lead_id; else by email
    lead_uuid = None
    meta = payload.get("Metadata") or {}
    if isinstance(meta, dict) and meta.get("lead_id"):
        try:
            lead_uuid = UUID_t(str(meta.get("lead_id")))
        except Exception:
            lead_uuid = None

    email = payload.get("Email")
    if not lead_uuid and email:
        # Attempt lookup by email (first match)
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Lead).where(Lead.email == email).limit(1))
            lead = res.scalar_one_or_none()
            if lead:
                lead_uuid = lead.id

    if not lead_uuid:
        # Nothing to do
        return JSONResponse({"ok": True})

    provider_id = payload.get("MessageID")
    # Build safe meta (exclude PII fields like Email)
    safe_meta = {
        "record_type": payload.get("RecordType"),
        "type": payload.get("Type"),
        "tag": payload.get("Tag"),
        "server_id": payload.get("ServerID"),
        "description": payload.get("Description"),
    }

    try:
        # Record MessageEvent and flip consent to opted_out for email channel
        await record_event(lead_id=str(lead_uuid), channel='email', type=event_type, meta=safe_meta, provider_id=str(provider_id) if provider_id else None)
        async with AsyncSessionLocal() as session:
            cons = Consent(
                lead_id=lead_uuid,
                channel='email',
                status='opted_out',
                source='postmark-webhook',
            )
            # Attempt to attach org if known
            res = await session.execute(select(Lead).where(Lead.id == lead_uuid))
            lead = res.scalar_one_or_none()
            if lead and getattr(lead, 'org_id', None) is not None:
                cons.org_id = lead.org_id
            session.add(cons)
            await session.commit()
    except Exception:
        # Silent failure; avoid exposing internals
        return JSONResponse({"ok": True})

    return JSONResponse({"ok": True})

# -------------------------
# End Webhooks
# -------------------------
