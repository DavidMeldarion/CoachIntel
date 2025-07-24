# Dummy FastAPI app for CoachSync backend
from fastapi import FastAPI, UploadFile, File, Query, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from pydantic import BaseModel
import os
import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
import httpx
from urllib.parse import urlencode
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
import logging
from celery.result import AsyncResult

from .integrations import fetch_fireflies_meetings, fetch_zoom_meetings, get_fireflies_meeting_details
from .models import User, create_or_update_user, get_user_by_email, Meeting, Transcript, AsyncSessionLocal
from sqlalchemy import select
from .worker import sync_fireflies_meetings  # Import Celery task for Fireflies only

logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

class UserProfileIn(BaseModel):
    email: str
    first_name: str
    last_name: str
    fireflies_api_key: str | None = None
    zoom_jwt: str | None = None
    phone: str | None = None
    address: str | None = None

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

@app.get("/")
def root():
    return {"message": "CoachSync backend API"}

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...)):
    # Dummy: Save file, trigger transcription job
    return {"filename": file.filename, "status": "received"}

@app.get("/sessions/")
def get_sessions():
    # Dummy: Return list of sessions
    # No logging for routine session checks
    return [{"id": 1, "summary": "Session 1 summary"}]

@app.post("/transcribe/")
def transcribe():
    # Dummy: Trigger transcription
    return {"status": "transcription started"}

@app.post("/summarize/")
def summarize():
    # Dummy: Trigger summarization
    return {"status": "summarization started"}

@app.get("/external-meetings/{source}/{meeting_id}")
async def get_meeting_details(
    source: str,
    meeting_id: str,
    request: Request
):
    """
    Get detailed information for a specific meeting.
    
    Path Parameters:
    - source: "fireflies" or "zoom" 
    - meeting_id: ID of the meeting/transcript
    """
    if source == "fireflies":
        fireflies_key = request.headers.get("x-api-key") or os.getenv("FIREFLIES_API_KEY")
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
async def login(request: Request):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    # TODO: Replace with real user lookup and password check
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    # Dummy check: allow any non-empty email/password
    user = {"email": email}
    # Issue JWT
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # Create response with both JSON data and cookie
    response = JSONResponse({"token": token, "user": user})
    # Use secure=True for production, lax for dev
    response.set_cookie(
        key="user",
        value=token,
        httponly=True,
        max_age=60*60*24*30,  # 30 days
        samesite="lax" if os.getenv("ENVIRONMENT") != "production" else "strict",
        secure=True if os.getenv("ENVIRONMENT") == "production" else False,
        path="/"
    )
    return response

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
        return RedirectResponse("http://localhost:3000/login?error=no_email")
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
    to_encode = {"sub": email, "exp": expire}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    response = RedirectResponse("http://localhost:3000/dashboard")
    response.set_cookie(
        key="user",
        value=token,
        httponly=True,
        max_age=604800,
        samesite="lax",  # Use lax for local dev
        secure=False      # True for HTTPS
    )
    return response

@app.get("/calendar/events")
async def get_calendar_events(request: Request):
    try:
        # Get user from JWT cookie
        cookie_header = request.headers.get("cookie", "")
        token = None
        for cookie in cookie_header.split(";"):
            if "user=" in cookie:
                token = cookie.split("user=")[1].strip()
                break
        if not token:
            raise HTTPException(status_code=401, detail="No authentication token")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = await get_user_by_email(email)
        if not user:
           raise HTTPException(status_code=401, detail="User not found")
        access_token, refresh_token, expiry = user.get_google_tokens()
        if not access_token:
            raise HTTPException(status_code=401, detail="No Google Calendar token")
        # Refresh token if expired
        if expiry and expiry < datetime.utcnow():
            data = {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(GOOGLE_TOKEN_URL, data=data)
                if resp.status_code != 200:
                    raise HTTPException(status_code=401, detail=f"Failed to refresh Google token: {resp.text}")
                tokens = resp.json()
            access_token = tokens["access_token"]
            expires_in = tokens.get("expires_in", 3600)
            expiry = datetime.utcnow() + timedelta(seconds=expires_in)
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/me")  # Temporarily remove response_model
async def get_current_user(request: Request):
    # Extract JWT token from cookie
    cookie_header = request.headers.get("cookie", "")
    token = None
    for cookie in cookie_header.split(";"):
        if "user=" in cookie:
            token = cookie.split("user=")[1].strip()
            break
    if not token:
        raise HTTPException(status_code=401, detail="No authentication token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # No info/debug logging for routine /me checks
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
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.options("/user")
async def options_user():
    return {"status": "ok"}

@app.put("/user")  # Remove response_model to avoid serialization issues
async def update_user_profile(request: Request):
    # Extract JWT token from cookie
    cookie_header = request.headers.get("cookie", "")
    token = None
    for cookie in cookie_header.split(";"):
        if "user=" in cookie:
            token = cookie.split("user=")[1].strip()
            break
    
    if not token:
        raise HTTPException(status_code=401, detail="No authentication token")
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        
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
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/meetings/")
async def get_user_meetings(request: Request):
    # Extract JWT token from cookie
    cookie_header = request.headers.get("cookie", "")
    token = None
    for cookie in cookie_header.split(";"):
        if "user=" in cookie:
            token = cookie.split("user=")[1].strip()
            break
    if not token:
        raise HTTPException(status_code=401, detail="No authentication token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Query meetings for this user
    async with AsyncSessionLocal() as session:
        from app.models import get_user_by_email
        user = await get_user_by_email(user_email)
        if not user:
            return {"meetings": []}
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
async def sync_external_meetings(request: Request, source: str = Query(..., description="fireflies or zoom")):
    """
    Trigger background sync of Fireflies or Zoom meetings for the authenticated user.
    Persists meetings to the database via Celery task.
    Returns status and task ID.
    """
    cookie_header = request.headers.get("cookie", "")
    token = None
    for cookie in cookie_header.split(";"):
        if "user=" in cookie:
            token = cookie.split("user=")[1].strip()
            break
    if not token:
        logging.warning("[SYNC DEBUG] No authentication token in cookie header.")
        raise HTTPException(status_code=401, detail="No authentication token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if not user_email:
            logging.warning("[SYNC DEBUG] Invalid token payload: missing sub.")
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        logging.warning("[SYNC DEBUG] Token expired.")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        logging.warning("[SYNC DEBUG] Invalid token.")
        raise HTTPException(status_code=401, detail="Invalid token")
    logging.info(f"[SYNC DEBUG] Sync requested for user: {user_email}, source: {source}")
    # Get user profile
    user_profile = await get_user_by_email(user_email)
    if not user_profile:
        logging.error(f"[SYNC DEBUG] User not found: {user_email}")
        return {"error": "User not found"}
    # Trigger Celery task
    if source == "fireflies":
        if not user_profile.fireflies_api_key:
            logging.warning(f"[SYNC DEBUG] No Fireflies API key for user: {user_email}")
            return {"error": "Fireflies API key not found"}
        task = sync_fireflies_meetings.delay(user_email, user_profile.fireflies_api_key)
        logging.info(f"[SYNC DEBUG] Fireflies sync task triggered: {task.id}")
        return {"status": "sync started", "task_id": task.id, "source": source}
    elif source == "zoom":
        logging.error(f"[SYNC DEBUG] Zoom sync is not implemented.")
        return {"error": "Zoom sync is not implemented yet"}
    else:
        logging.error(f"[SYNC DEBUG] Invalid source: {source}")
        return {"error": "Invalid source. Must be 'fireflies' or 'zoom'"}

@app.get("/sync/status/{task_id}")
def get_sync_status(task_id: str):
    """
    Return the status of a Celery sync task by task_id.
    Possible states: PENDING, STARTED, SUCCESS, FAILURE, etc.
    """
    result = AsyncResult(task_id)
    return {"task_id": task_id, "status": result.status, "ready": result.ready(), "successful": result.successful()}
