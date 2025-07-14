# User model for CoachSync
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    fireflies_api_key = Column(String, nullable=True)
    zoom_jwt = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)

# Async engine for FastAPI app
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
if not ASYNC_DATABASE_URL:
    raise RuntimeError("DATABASE_URL or ASYNC_DATABASE_URL environment variable is not set")
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# For Alembic migrations (sync engine)
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
sync_engine = create_engine(SYNC_DATABASE_URL)

async def get_user_by_email(email: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        return user

async def create_or_update_user(email: str, name: str = None, fireflies_api_key: str = None, zoom_jwt: str = None, phone: str = None, address: str = None):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_email(email)
        if user:
            if name:
                user.name = name
            if fireflies_api_key:
                user.fireflies_api_key = fireflies_api_key
            if zoom_jwt:
                user.zoom_jwt = zoom_jwt
            if phone:
                user.phone = phone
            if address:
                user.address = address
        else:
            user = User(email=email, name=name, fireflies_api_key=fireflies_api_key, zoom_jwt=zoom_jwt, phone=phone, address=address)
            session.add(user)
        await session.commit()
        return user
