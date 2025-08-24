"""Centralized logging utilities wrapping structlog configuration and reusable event helpers.

This module exists to avoid circular imports between repositories and the FastAPI `main` module
while still sharing a single structlog configuration & helper functions.

Import order safety: This file should have no side-effects that depend on application models
or the FastAPI `app` instance. Only logging config and helpers.
"""
from __future__ import annotations

import logging
import contextvars
import structlog
from typing import Any

# -------------------------
# ContextVars for request-scoped data
# -------------------------
_request_id_var = contextvars.ContextVar("request_id", default=None)
_coach_id_var = contextvars.ContextVar("coach_id", default=None)
_provider_var = contextvars.ContextVar("provider", default=None)

# Expose a mapping for external access if needed
structlog_context = {
    "request_id": _request_id_var,
    "coach_id": _coach_id_var,
    "provider": _provider_var,
}

# -------------------------
# Processor helper to merge our ContextVars (structlog.contextvars.merge_contextvars only handles ones bound via bind_contextvars)
# We set directly, so pull manually.
# -------------------------

def _add_context(logger, method_name: str, event_dict: dict[str, Any]):  # noqa: D401
    rid = _request_id_var.get()
    if rid:
        event_dict["request_id"] = rid
    cid = _coach_id_var.get()
    if cid is not None:
        event_dict["coach_id"] = cid
    prov = _provider_var.get()
    if prov:
        event_dict["provider"] = prov
    return event_dict

# -------------------------
# One-time structlog configuration (idempotent)
# -------------------------
if not getattr(structlog, "_COACHINTEL_CONFIGURED", False):
    logging_logger = logging.getLogger("coachintel")
    logging_logger.setLevel(logging.INFO)
    if not logging_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging_logger.addHandler(handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    structlog._COACHINTEL_CONFIGURED = True  # type: ignore[attr-defined]

slog = structlog.get_logger()

# -------------------------
# Public helper functions
# -------------------------

def set_log_request(request_id: str | None):
    _request_id_var.set(request_id)

def set_log_coach(coach_id: int | None):
    _coach_id_var.set(coach_id)

def set_log_provider(provider: str | None):
    _provider_var.set(provider)

# Event helpers reused across modules

def log_webhook_received(provider: str, status: str, detail: str | None = None, **extra):
    slog.info("webhook_received", provider=provider, status=status, detail=detail, **extra)

def log_meeting_upserted(meeting_id: str, coach_id: int, source: str, created: bool, **extra):
    slog.info("meeting_upserted", meeting_id=meeting_id, coach_id=coach_id, source=source, created=created, **extra)

def log_attendee_resolved(raw_email: str | None, person_id: str | None, matched: bool, **extra):
    slog.info("attendee_resolved", raw_email=raw_email, person_id=person_id, matched=matched, **extra)

def log_tokens_refreshed(coach_id: int, provider: str, success: bool, rotated: bool | None = None, **extra):
    slog.info("tokens_refreshed", coach_id=coach_id, provider=provider, success=success, rotated=rotated, **extra)
