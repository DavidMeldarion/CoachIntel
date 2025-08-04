# User model for CoachIntel
from sqlalchemy import Column, Integer, String, create_engine, select, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
import os
from sqlalchemy.dialects.postgresql import JSON
from cryptography.fernet import Fernet

Base = declarative_base()

# Generate this key once and store securely (e.g., in .env)
FERNET_KEY = os.getenv("FERNET_KEY", Fernet.generate_key().decode())
fernet = Fernet(FERNET_KEY.encode())

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

class Transcript(Base):
    __tablename__ = "transcripts"
    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"))
    full_text = Column(Text)
    summary = Column(JSON)
    action_items = Column(JSON)
    progress_notes = Column(Text)  # New field for cumulative progress notes
    # Relationship
    meeting = relationship("Meeting", back_populates="transcript")

# Async engine for FastAPI app
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
if not ASYNC_DATABASE_URL:
    raise RuntimeError("DATABASE_URL or ASYNC_DATABASE_URL environment variable is not set")
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# For Alembic migrations (sync engine)
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
sync_engine = create_engine(SYNC_DATABASE_URL)

# Synchronous session for Celery worker and scripts
SessionLocal = sessionmaker(sync_engine)

async def get_user_by_email(email: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        return user

async def create_or_update_user(email: str, name: str = None, first_name: str = None, last_name: str = None, fireflies_api_key: str = None, zoom_jwt: str = None, phone: str = None, address: str = None):
    async with AsyncSessionLocal() as session:
        # Get user within the same session to avoid session detachment issues
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
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
        else:
            # Create new user - ensure first_name and last_name are never None due to DB constraints
            if first_name is None and last_name is None and name:
                # Use the name setter to split into first/last
                user = User(email=email, first_name="", last_name="", 
                           fireflies_api_key=fireflies_api_key, zoom_jwt=zoom_jwt, phone=phone, address=address)
                user.name = name  # This will set first_name and last_name
            else:
                # Ensure first_name and last_name are never None
                user = User(email=email, 
                           first_name=first_name or "", 
                           last_name=last_name or "", 
                           fireflies_api_key=fireflies_api_key, 
                           zoom_jwt=zoom_jwt, 
                           phone=phone, 
                           address=address)
            session.add(user)  # Add the new user to the session
        await session.commit()
        await session.refresh(user)
        return user
