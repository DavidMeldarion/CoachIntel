import os
import time
import jwt
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator, Field, ValidationError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
import httpx
from urllib.parse import urlencode
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
import logging
from celery.result import AsyncResult
from passlib.context import CryptContext
from .integrations import get_fireflies_meeting_details, test_fireflies_api_key
from .models import User, create_or_update_user, get_user_by_email, Meeting, Transcript, AsyncSessionLocal
from sqlalchemy import select
from app.worker import sync_fireflies_meetings, celery_app, REDIS_URL  # Import Celery task for Fireflies only
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
    
    class Config:
        from_attributes = True  # Pydantic v2 syntax (replaces orm_mode = True)

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
        if cookie.startswith("next-auth.session-token="):
            next_auth_token = cookie.split("next-auth.session-token=")[1]
            break
        elif cookie.startswith("session="):
            session_token = cookie.split("session=")[1]
        elif cookie.startswith("user="):
            user_token = cookie.split("user=")[1]
    
    # Try NextAuth token first
    if next_auth_token:
        print(f"[Backend] verify_jwt_user - Found NextAuth token: {next_auth_token[:20]}...")
        try:
            # NextAuth tokens are JWE (encrypted), so we can't decode them directly
            # Instead, let's extract user email from the Authorization header if present
            auth_header = request.headers.get("authorization", "")
            if auth_header and auth_header.startswith("Bearer "):
                email = auth_header.split("Bearer ")[1]
                user = await get_user_by_email(email)
                if user:
                    print(f"[Backend] verify_jwt_user - Successfully verified NextAuth user: {user.email}")
                    return user
            
            # Fallback: If no Authorization header, check if we have a user email in a custom header
            user_email = request.headers.get("x-user-email", "")
            print(f"[Backend] verify_jwt_user - x-user-email header: '{user_email}'")
            if user_email:
                user = await get_user_by_email(user_email)
                if user:
                    print(f"[Backend] verify_jwt_user - Successfully verified NextAuth user via header: {user.email}")
                    return user
                else:
                    print(f"[Backend] verify_jwt_user - User not found in database: {user_email}")
            
            # If NextAuth token exists but we can't verify the user, return 401
            print("[Backend] verify_jwt_user - NextAuth token found but no user context")
            raise HTTPException(status_code=401, detail="NextAuth session found but user verification failed")
            
        except Exception as e:
            print(f"[Backend] verify_jwt_user - NextAuth verification failed: {e}")
            raise HTTPException(status_code=401, detail="NextAuth session verification failed")
    
    # Fallback to legacy JWT verification for existing sessions
    token = session_token or user_token
    print(f"[Backend] verify_jwt_user - extracted legacy token: {token[:20] if token else None}... (from {'session' if session_token else 'user'} cookie)")
    
    if not token:
        print("[Backend] verify_jwt_user - No token found, raising 401")
        raise HTTPException(status_code=401, detail="No authentication token")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub") or payload.get("email")  # Support both formats
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        print(f"[Backend] verify_jwt_user - Successfully verified legacy user: {user.email}")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

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
    
    # Manually create the response to ensure computed properties are included
    return UserProfileOut(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        name=user.name,  # This will use the computed property
        fireflies_api_key=user.fireflies_api_key,
        zoom_jwt=user.zoom_jwt,
        phone=user.phone,
        address=user.address
    )

@app.post("/user", response_model=UserProfileOut)
async def upsert_user(profile: UserProfileIn):
    # Check if user already exists
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
    
    # Manually create the response to ensure computed properties are included
    return UserProfileOut(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        name=user.name,  # This will use the computed property
        fireflies_api_key=user.fireflies_api_key,
        zoom_jwt=user.zoom_jwt,
        phone=user.phone,
        address=user.address
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
                "name": user.name
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
                content={"error": "User with this email already exists"}
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
                "name": user.name
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
        "address": user.address
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
        if cookie.startswith("next-auth.session-token="):
            next_auth_token = cookie.split("next-auth.session-token=")[1]
            break
        elif cookie.startswith("user="):
            legacy_token = cookie.split("user=")[1]
    
    email = None
    
    # Try NextAuth authentication first
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
        # Get request data
        data = await request.json()
        
        # Update user profile
        user = await create_or_update_user(
            email=email,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            fireflies_api_key=data.get("fireflies_api_key"),
            zoom_jwt=data.get("zoom_jwt"),
            phone=data.get("phone"),
            address=data.get("address")
        )
        
        # Return a simple dictionary instead of Pydantic model
        return {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "name": user.name,
            "fireflies_api_key": user.fireflies_api_key,
            "zoom_jwt": user.zoom_jwt,
            "phone": user.phone,
            "address": user.address
        }
    except Exception as e:
        print(f"[Backend] update_user_profile - Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user profile")

@app.get("/meetings/")
async def get_user_meetings(user: User = Depends(verify_jwt_user)):
    # Query meetings for this user
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Meeting).options(selectinload(Meeting.transcript)).where(Meeting.user_id == user.id)
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
        task = sync_fireflies_meetings.delay(user.email, user_profile.fireflies_api_key)
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
        result = await session.execute(
            select(Meeting).options(selectinload(Meeting.transcript)).where(Meeting.id == meeting_id, Meeting.user_id == user.id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            logging.error(f"Meeting not found: id={meeting_id}, user_id={user.id}")
            # Optionally, check if meeting exists for any user
            other_result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
            other_meeting = other_result.scalar_one_or_none()
            if other_meeting:
                logging.error(f"Meeting id={meeting_id} exists but not for user_id={user.id}")
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
    # Check Celery/Redis
    try:
        # Send a dummy task and check status
        result = celery_app.send_task('worker.sync_fireflies_meetings')
        _ = AsyncResult(result.id)
    except Exception as e:
        return {"ok": False, "celery": False, "error": str(e)}
    return {"ok": True, "db": True, "celery": True}

from fastapi import status

@app.post("/summarize-missing-transcripts", status_code=status.HTTP_202_ACCEPTED)
async def trigger_summarize_missing_transcripts():
    """
    Trigger the Celery task to summarize all missing transcripts.
    Returns the Celery task id.
    """
    result = celery_app.send_task('app.worker.summarize_missing_transcripts')
    return {"task_id": result.id, "status": "started"}
