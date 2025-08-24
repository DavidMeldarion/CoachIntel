"""Global pytest fixtures configuring a dedicated Postgres test database.

Usage:
  Export TEST_DATABASE_URL prior to running pytest, e.g.
    TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5433/test_db pytest

This file will:
  * Map TEST_DATABASE_URL => ASYNC_DATABASE_URL (async) & DATABASE_URL (sync) env vars
  * Create all tables from both legacy `app.models` Base and new meeting tracking Base
  * Monkeypatch `AsyncSessionLocal` used across the app to the test engine sessionmaker
  * Provide `db_session` fixture for direct DB access in tests
  * Provide `client` fixture returning a FastAPI TestClient bound to the same DB
"""
from __future__ import annotations

import os
import pytest
from typing import AsyncIterator

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip("TEST_DATABASE_URL not set – skipping DB integration tests", allow_module_level=True)

# Derive async & sync URLs. We assume asyncpg driver is used for the async URL.
ASYNC_URL = TEST_DATABASE_URL
SYNC_URL = TEST_DATABASE_URL.replace("+asyncpg", "")

# Ensure env vars expected by application code are present BEFORE importing app modules.
os.environ.setdefault("ASYNC_DATABASE_URL", ASYNC_URL)
os.environ.setdefault("DATABASE_URL", SYNC_URL)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from sqlalchemy import text
from sqlalchemy import create_engine as create_sync_engine

# Import models AFTER env vars set so they pick up test URLs.
from app import models as legacy_models
from app.models_meeting_tracking import Base as TrackingBase  # new declarative base

# Build dedicated async engine (avoid NullPool / autocommit tweaks used in prod)
engine = create_async_engine(ASYNC_URL, echo=False, future=True)
AsyncSessionLocalTest = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Automatic database create / drop
# ---------------------------------------------------------------------------
url_obj = make_url(ASYNC_URL)
db_name = url_obj.database
# Build admin (maintenance) connection URL pointing to 'postgres' default DB (sync driver)
admin_url_obj = url_obj.set(drivername=url_obj.drivername.replace('+asyncpg', ''), database='postgres')
admin_engine = create_sync_engine(admin_url_obj, isolation_level='AUTOCOMMIT', future=True)
_created_db = False

with admin_engine.connect() as conn:
    exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name}).scalar()
    if not exists:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        _created_db = True



@pytest.fixture(scope="session")
def anyio_backend():  # ensure anyio uses asyncio
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def _create_all() -> AsyncIterator[None]:
    """Create all tables for both metadata bases, then drop at end of session."""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(legacy_models.Base.metadata.create_all)
        await conn.run_sync(TrackingBase.metadata.create_all)
    # Monkeypatch globally used session factory
    legacy_models.AsyncSessionLocal = AsyncSessionLocalTest  # type: ignore
    yield
    # Teardown: drop tables then database (only if we created it)
    await engine.dispose()
    if _created_db:
        # Terminate lingering connections then drop
        with admin_engine.connect() as conn:
            conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :n AND pid <> pg_backend_pid()"), {"n": db_name})
            conn.execute(text(f'DROP DATABASE "{db_name}"'))
    admin_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocalTest() as session:
        yield session


@pytest.fixture
def client():
    # Import here so app picks up patched AsyncSessionLocal
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture
async def seed_user(db_session):
    from app.models import create_or_update_user
    user = await create_or_update_user(email="seeduser@example.com", first_name="Seed", last_name="User")
    return user
