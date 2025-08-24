from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict, List
import hmac, hashlib, json, os, time, logging
import base64
import uuid

from app.worker import celery_app  # existing celery instance
from app.models import AsyncSessionLocal
from sqlalchemy import select
from app.models_meeting_tracking import ExternalAccount
from app.services.calendly_ingestion import handle_calendly_webhook

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis import fallback
    redis = None  # noqa

logger = logging.getLogger("webhooks")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)

_redis_client = None  # cached sync redis client

def get_redis():
    """Lazily construct a Redis client for replay protection.

    Falls back to in-memory dict shim if redis lib / server unavailable so tests can monkeypatch.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if redis:
        try:
            _redis_client = redis.Redis.from_url(url, decode_responses=True)
            # lightweight ping to validate (non-fatal)
            try:
                _redis_client.ping()
            except Exception:
                logger.warning("Redis ping failed; replay protection may be degraded")
            return _redis_client
        except Exception:
            logger.warning("Redis init failed; falling back to in-memory replay store")
    # fallback simple dict (NOT multi-process safe)
    class _Mem:
        def __init__(self):
            self.store = {}
        def setex(self, k, ttl, v):
            self.store[k] = (v, time.time() + ttl)
        def get(self, k):
            entry = self.store.get(k)
            if not entry:
                return None
            v, exp = entry
            if time.time() > exp:
                self.store.pop(k, None)
                return None
            return v
    _redis_client = _Mem()
    return _redis_client

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# -------------------------
# Pydantic payloads (minimal)
# -------------------------
class CalendlyEvent(BaseModel):
    event: Literal["invitee.created", "invitee.canceled"]
    payload: Dict[str, Any] = Field(default_factory=dict)
    # Optional explicit coach targeting (fallback heuristic if absent)
    coach_id: Optional[int] = None

class ZoomEvent(BaseModel):
    event: str  # e.g. 'meeting.participant_joined', 'meeting.participant_left', 'meeting.ended'
    payload: Dict[str, Any] = Field(default_factory=dict)

class FirefliesEvent(BaseModel):
    event: Optional[str] = None  # if available
    payload: Dict[str, Any] = Field(default_factory=dict)

# -------------------------
# Signature utilities
# -------------------------

def _canonical_json(data: dict) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode()


def verify_hmac_signature(secret: str, body_bytes: bytes, provided: str | None) -> bool:
    """Generic HMAC-SHA256 hex signature check."""
    if not secret:
        return True
    if not provided:
        return False
    mac = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, provided)


def verify_zoom_signature(secret: str, ts: str | None, body_bytes: bytes, provided: str | None, tolerance_sec: int = 300) -> bool:
    """Verify Zoom style signature: provided = 'v0=hexdigest', payload string = 'v0:{ts}:{body}'."""
    if not secret:
        return True
    if not provided or not ts:
        return False
    try:
        ts_int = int(ts)
    except Exception:
        return False
    now = int(time.time())
    if abs(now - ts_int) > tolerance_sec:
        return False
    base = f"v0:{ts}:{body_bytes.decode()}".encode()
    mac = hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    expected = f"v0={mac}"
    return hmac.compare_digest(expected, provided)

#############################################
# Utility helpers (enqueue, rate limit, auth)
#############################################

def enqueue(task_name: str, payload: dict):
    try:
        celery_app.send_task(task_name, args=[payload])
    except Exception as e:  # pragma: no cover - best effort
        logger.warning("Failed to enqueue %s: %s", task_name, e)


def _redis_safe_exec(func, default):
    try:
        return func()
    except Exception:  # pragma: no cover
        return default


def rate_limit(key: str, limit: int, window_sec: int) -> bool:
    """Simple fixed-window rate limiter using Redis INCR/EXPIRE.

    Returns True if allowed, False if over limit (or treat errors as allowed).
    """
    r = get_redis()
    def _inner():
        count = r.incr(key)
        if count == 1:
            try:
                r.expire(key, window_sec)
            except Exception:  # pragma: no cover
                pass
        return count <= limit
    return _redis_safe_exec(_inner, True)


def debounce(key: str, ttl_sec: int) -> bool:
    """Return True if this key was seen recently (i.e., should debounce/skip)."""
    r = get_redis()
    def _inner():
        if r.get(key):
            return True
        try:
            r.setex(key, ttl_sec, "1")
        except Exception:  # pragma: no cover
            pass
        return False
    return _redis_safe_exec(_inner, False)


def require_admin(token: str | None):
    expected = os.getenv("ADMIN_API_TOKEN")
    if not expected:
        # If no token configured, deny by default (fail-closed) to avoid accidental exposure.
        raise HTTPException(status_code=503, detail="Admin token not configured")
    if token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


# -------------------------
# Calendly webhook
# -------------------------
@router.post("/calendly", status_code=202)
async def calendly_webhook(
    body: CalendlyEvent,
    x_calendly_signature: Optional[str] = Header(None),
    x_calendly_webhook_request_timestamp: Optional[str] = Header(None),
):
    raw = body.model_dump()
    secret = os.getenv("CALENDLY_WEBHOOK_SECRET", "")
    body_bytes = _canonical_json(raw)
    # Timestamp tolerance
    if x_calendly_webhook_request_timestamp:
        try:
            ts = int(x_calendly_webhook_request_timestamp)
            if abs(time.time() - ts) > int(os.getenv("CALENDLY_TIMESTAMP_TOLERANCE", "300")):
                raise HTTPException(status_code=400, detail="Stale webhook (timestamp)")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp header")
    if secret and not verify_hmac_signature(secret, body_bytes, x_calendly_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Replay protection: derive nonce (preferred: invitee uuid if available, else hash of body)
    payload = raw.get("payload") or {}
    invitee_uuid = (
        payload.get("invitee", {}).get("uuid")
        if isinstance(payload.get("invitee"), dict)
        else payload.get("invitee_uuid")
    )
    nonce = invitee_uuid or hashlib.sha256(body_bytes).hexdigest()
    redis_client = get_redis()
    replay_key = f"cal:wh:nonce:{nonce}"
    if redis_client.get(replay_key):
        # Previously seen
        raise HTTPException(status_code=409, detail="Replay detected")
    # store nonce with short TTL (default 1 day)
    ttl = int(os.getenv("CALENDLY_REPLAY_TTL", "86400"))
    try:
        redis_client.setex(replay_key, ttl, "1")
    except Exception:  # pragma: no cover
        pass

    # Provider-wide rate limit (per minute) before heavier DB lookups
    rl_limit = int(os.getenv("WEBHOOK_RATE_LIMIT_PER_MINUTE", "300"))
    if not rate_limit(f"rl:calendly:{int(time.time()//60)}", rl_limit, 60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Short debounce window (handles rapid duplicate bursts distinct from long replay TTL)
    debounce_ttl = int(os.getenv("CALENDLY_DEBOUNCE_SECONDS", "8"))
    if debounce(f"db:calendly:{nonce}", debounce_ttl):
        return {"accepted": True, "nonce": nonce, "debounced": True}

    # Directly process using service layer (multi-account fan-out if coach unspecified)
    results: List[Dict[str, Any]] = []
    async with AsyncSessionLocal() as session:  # type: ignore
        if body.coach_id:
            acct_stmt = select(ExternalAccount).where(ExternalAccount.provider == 'calendly', ExternalAccount.coach_id == body.coach_id)
        else:
            acct_stmt = select(ExternalAccount).where(ExternalAccount.provider == 'calendly')
        accounts = (await session.execute(acct_stmt)).scalars().all()
        if not accounts:
            # Fall back to enqueue for later (legacy) if no accounts resolved
            enqueue("calendly_ingest", raw)
            return {"accepted": True, "nonce": nonce, "processed": False, "reason": "no_accounts"}
        for acct in accounts:
            try:
                res = await handle_calendly_webhook(session, acct.coach_id, raw)
                if res.ok:
                    await session.commit()
                else:
                    await session.rollback()
                results.append({"coach_id": acct.coach_id, "ok": res.ok, "error": res.error, **(res.value or {})})
            except Exception as e:  # pragma: no cover
                await session.rollback()
                results.append({"coach_id": acct.coach_id, "ok": False, "error": str(e)})
    return {"accepted": True, "nonce": nonce, "results": results}

# -------------------------
# Zoom webhook
# -------------------------
@router.post("/zoom", status_code=202)
async def zoom_webhook(
    body: ZoomEvent,
    x_zm_signature: Optional[str] = Header(None),
    x_zm_request_timestamp: Optional[str] = Header(None),
):
    secret = os.getenv("ZOOM_WEBHOOK_SECRET", "")
    body_bytes = _canonical_json(body.model_dump())
    if secret and not verify_zoom_signature(secret, x_zm_request_timestamp, body_bytes, x_zm_signature):
        raise HTTPException(status_code=400, detail="Invalid zoom signature")
    # Rate limit (provider global)
    rl_limit = int(os.getenv("WEBHOOK_RATE_LIMIT_PER_MINUTE", "300"))
    if not rate_limit(f"rl:zoom:{int(time.time()//60)}", rl_limit, 60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    # Debounce based on hash (short TTL)
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    debounce_ttl = int(os.getenv("ZOOM_DEBOUNCE_SECONDS", "5"))
    if debounce(f"db:zoom:{body_hash}", debounce_ttl):
        return {"accepted": True, "debounced": True}
    enqueue("zoom_ingest", body.model_dump())
    return {"accepted": True, "hash": body_hash}

# -------------------------
# Fireflies webhook
# -------------------------
@router.post("/fireflies", status_code=202)
async def fireflies_webhook(body: FirefliesEvent, limit: int = 25):
    # Identify all coaches with fireflies external account and trigger recent ingestion
    rl_limit = int(os.getenv("WEBHOOK_RATE_LIMIT_PER_MINUTE", "300"))
    if not rate_limit(f"rl:fireflies:{int(time.time()//60)}", rl_limit, 60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    raw_bytes = _canonical_json(body.model_dump())
    body_hash = hashlib.sha256(raw_bytes).hexdigest()
    debounce_ttl = int(os.getenv("FIREFLIES_DEBOUNCE_SECONDS", "5"))
    if debounce(f"db:fireflies:{body_hash}", debounce_ttl):
        return {"accepted": True, "debounced": True}
    async with AsyncSessionLocal() as session:  # type: ignore
        acct_stmt = select(ExternalAccount).where(ExternalAccount.provider == 'fireflies')
        accounts = (await session.execute(acct_stmt)).scalars().all()
        coach_ids = [a.coach_id for a in accounts]
    for cid in coach_ids:
        try:
            celery_app.send_task('ingest_fireflies_recent', args=[cid, limit])
        except Exception as e:  # pragma: no cover
            logger.warning("Failed to enqueue fireflies ingestion for coach %s: %s", cid, e)
    enqueue("fireflies_ingest", body.model_dump())  # legacy raw log ingestion
    return {"accepted": True, "fanout": len(coach_ids)}


# -------------------------
# Manual ingestion trigger endpoint
# -------------------------
class IngestionTrigger(BaseModel):
    provider: Literal['google','zoom','calendly','fireflies']
    coach_id: int
    since_iso: Optional[str] = None
    meeting_ids: Optional[List[str]] = None
    event_uuid: Optional[str] = None
    invitee_uuid: Optional[str] = None
    limit: Optional[int] = 25

@router.post("/trigger", status_code=202)
async def manual_ingest(
    trigger: IngestionTrigger,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    # AuthZ
    require_admin(x_admin_token)
    provider = trigger.provider.lower()
    if provider == 'google':
        celery_app.send_task('app.worker.sync_google_calendar', args=[trigger.coach_id, trigger.since_iso])
    elif provider == 'zoom':
        celery_app.send_task('app.worker.sync_zoom_reports', args=[trigger.coach_id, trigger.meeting_ids])
    elif provider == 'fireflies':
        celery_app.send_task('ingest_fireflies_recent', args=[trigger.coach_id, (trigger.limit or 25)])
    elif provider == 'calendly':
        if not trigger.event_uuid:
            raise HTTPException(status_code=400, detail="event_uuid required for calendly provider")
        celery_app.send_task('ingest_calendly_event', args=[trigger.coach_id, trigger.event_uuid, trigger.invitee_uuid])
    else:  # pragma: no cover
        raise HTTPException(status_code=400, detail="Unsupported provider")
    return {"accepted": True, "provider": provider}

