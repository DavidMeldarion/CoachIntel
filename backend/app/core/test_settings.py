"""Test settings helper for CI Postgres.

Provides a lightweight factory to construct a DATABASE_URL pointing at the
GitHub Actions service container (postgres) with a dedicated database.
"""
from __future__ import annotations

import os
from .settings import Settings


def build_test_settings() -> Settings:
    db_host = os.getenv("TEST_DB_HOST", "localhost")
    db_port = os.getenv("TEST_DB_PORT", "5432")
    db_user = os.getenv("TEST_DB_USER", "postgres")
    db_pass = os.getenv("TEST_DB_PASSWORD", "postgres")
    db_name = os.getenv("TEST_DB_NAME", "coachintel_test")
    # Async driver URL for SQLAlchemy + asyncpg
    async_url = f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    redis_url = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/0")
    fernet_key = os.getenv("FERNET_KEY", "".join(["A"*43, "="]))  # CI should override with secure key
    return Settings(
        DATABASE_URL=async_url,
        REDIS_URL=redis_url,
        FERNET_KEY=fernet_key,
    )

__all__ = ["build_test_settings"]
