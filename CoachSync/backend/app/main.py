# Dummy FastAPI app for CoachSync backend
from fastapi import FastAPI, UploadFile, File, Query, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from pydantic import BaseModel
import os
import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from datetime import datetime, timedelta
import requests

from .integrations import fetch_fireflies_meetings, fetch_zoom_meetings, get_fireflies_meeting_details
from .models import User, create_or_update_user, get_user_by_email

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
    return [{"id": 1, "summary": "Session 1 summary"}]

@app.post("/transcribe/")
def transcribe():
    # Dummy: Trigger transcription
    return {"status": "transcription started"}

@app.post("/summarize/")
def summarize():
    # Dummy: Trigger summarization
    return {"status": "summarization started"}

@app.get("/external-meetings/")
async def get_external_meetings(
    request: Request,
    source: str = Query(..., description="fireflies or zoom"),
    user: str = Query(..., description="user email for Fireflies or user id for Zoom"),
    limit: int = Query(10, description="Maximum number of meetings to fetch")
):
    """
    Fetch external meetings from Fireflies.ai or Zoom.
    
    Query Parameters:
    - source: "fireflies" or "zoom"
    - user: user email for Fireflies or user id for Zoom
    - limit: maximum number of meetings to return (default 10)
    """
    
    if source == "fireflies":
        # Get the user's stored Fireflies API key from their profile
        user_profile = await get_user_by_email(user)
        if not user_profile or not user_profile.fireflies_api_key:
            return {
                "error": "Fireflies API key not found in user profile. Please add your API key in the profile settings.",
                "meetings": [],
                "total_count": 0,
                "source": "fireflies"
            }
        
        result = await fetch_fireflies_meetings(user, user_profile.fireflies_api_key, limit)
        return result
    elif source == "zoom":
        # Get the user's stored Zoom JWT from their profile
        user_profile = await get_user_by_email(user)
        if not user_profile or not user_profile.zoom_jwt:
            return {
                "error": "Zoom JWT not found in user profile. Please add your Zoom JWT in the profile settings.",
                "meetings": [],
                "total_count": 0,
                "source": "zoom"
            }
        
        result = await fetch_zoom_meetings(user, user_profile.zoom_jwt)
        return result
    else:
        return {"error": "Invalid source. Must be 'fireflies' or 'zoom'", "meetings": [], "total_count": 0}

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
    return JSONResponse({"token": token, "user": user})

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

@app.get("/auth/google")
def google_oauth_start(intent: str = "login"):
    # intent can be "login" or "signup"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": intent  # Pass intent as state parameter
    }
    url = GOOGLE_AUTH_URL + "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    return RedirectResponse(url)

@app.get("/auth/google/callback")
async def google_oauth_callback(code: str, state: str = "login"):
    # Exchange code for token
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    token_resp = requests.post(GOOGLE_TOKEN_URL, data=data)
    if not token_resp.ok:
        raise HTTPException(status_code=400, detail="Failed to get token from Google")
    token_json = token_resp.json()
    access_token = token_json.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token from Google")
    # Get user info
    userinfo_resp = requests.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if not userinfo_resp.ok:
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")
    userinfo = userinfo_resp.json()
    email = userinfo.get("email")
    name = userinfo.get("name", "")
    if not email:
        raise HTTPException(status_code=400, detail="No email from Google userinfo")
      # Check if user exists
    user = await get_user_by_email(email)
    
    # Handle based on intent (login vs signup)
    if state == "signup":
        if user and hasattr(user, 'name'):
            # User already exists, redirect to login with error message
            login_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/login?error=account_exists"
            return RedirectResponse(login_url)
        else:
            # Create new user for signup
            user = await create_or_update_user(email=email, name=name)
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/profile/complete-profile"
    else:  # login
        if user and hasattr(user, 'name'):
            # Existing user login - check if profile is complete
            if user.name and len(user.name.strip().split(" ")) >= 2:
                frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard"
            else:
                frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/profile/complete-profile"
        else:
            # New user via login - create account
            user = await create_or_update_user(email=email, name=name)
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/profile/complete-profile"
    
    # Issue JWT
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    resp = RedirectResponse(frontend_url)
    resp.set_cookie(key="user", value=token, httponly=True, max_age=604800, samesite="lax")
    return resp

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
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")        # Get user from database
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
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
