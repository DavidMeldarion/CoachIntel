"""Application configuration using pydantic-settings.

Environment variables are the sole source of truth (12-factor). No secrets committed.
Add new settings thoughtfully; prefer grouping by domain. Use `get_settings()` for DI.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string (async or sync as needed)")
    REDIS_URL: str = Field(..., description="Redis connection URL for cache / Celery broker")
    FERNET_KEY: str = Field(..., min_length=32, description="Base64 urlsafe 32-byte key for encryption (do NOT auto-generate here)")
    LOG_LEVEL: str = Field("INFO", description="Application log level")

    # OAuth / External Provider credentials (client-side + server secret parts)
    OAUTH_GOOGLE_CLIENT_ID: Optional[str] = None
    OAUTH_GOOGLE_CLIENT_SECRET: Optional[str] = None
    OAUTH_GOOGLE_REDIRECT_URI: Optional[AnyHttpUrl] = None

    OAUTH_ZOOM_CLIENT_ID: Optional[str] = None
    OAUTH_ZOOM_CLIENT_SECRET: Optional[str] = None
    OAUTH_ZOOM_REDIRECT_URI: Optional[AnyHttpUrl] = None

    OAUTH_CALENDLY_CLIENT_ID: Optional[str] = None
    OAUTH_CALENDLY_CLIENT_SECRET: Optional[str] = None
    OAUTH_CALENDLY_REDIRECT_URI: Optional[AnyHttpUrl] = None

    OAUTH_FIREFLIES_CLIENT_ID: Optional[str] = None
    OAUTH_FIREFLIES_CLIENT_SECRET: Optional[str] = None
    OAUTH_FIREFLIES_REDIRECT_URI: Optional[AnyHttpUrl] = None

    # Celery
    CELERY_BROKER_URL: Optional[str] = None  # fallback to REDIS_URL if None when wiring
    CELERY_RESULT_BACKEND: Optional[str] = None  # fallback to REDIS_URL if None

    # Celery beat default schedule stubs (tasks to be populated later)
    CELERY_BEAT_SCHEDULE: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            # Example stub tasks (replace with real ones or override via env JSON)
            # 'sync_external_accounts': {
            #     'task': 'app.tasks.sync_external_accounts',
            #     'schedule': 300.0,  # seconds
            # },
            # 'cleanup_expired_tokens': {
            #     'task': 'app.tasks.cleanup_expired_tokens',
            #     'schedule': 3600.0,
            # },
        },
        description="Celery beat schedule mapping (may be overridden by JSON in env var)",
    )

    model_config = SettingsConfigDict(env_file=None, case_sensitive=False, extra="ignore")

    @property
    def effective_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def effective_result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton settings instance.

    Usage: settings = get_settings()
    In FastAPI dependency: `Depends(get_settings)`.
    """
    return Settings()  # pydantic-settings loads from environment automatically


__all__ = ["Settings", "get_settings"]
