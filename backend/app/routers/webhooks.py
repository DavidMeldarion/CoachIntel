from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict
import hmac, hashlib, json, os, time, logging
import base64
import uuid

from app.worker import celery_app  # existing celery instance

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

# -------------------------
# Celery enqueue wrappers
# -------------------------

def enqueue(task_name: str, payload: dict):
    try:
        celery_app.send_task(task_name, args=[payload])
    except Exception as e:  # pragma: no cover - best effort
        logger.warning("Failed to enqueue %s: %s", task_name, e)

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

    enqueue("calendly_ingest", raw)
    return {"accepted": True, "nonce": nonce}

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
    enqueue("zoom_ingest", body.model_dump())
    return {"accepted": True}

# -------------------------
# Fireflies webhook
# -------------------------
@router.post("/fireflies", status_code=202)
async def fireflies_webhook(body: FirefliesEvent):
    enqueue("fireflies_ingest", body.model_dump())
    return {"accepted": True}

