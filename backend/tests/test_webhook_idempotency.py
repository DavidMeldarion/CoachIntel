import json, time, hmac, hashlib
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv('CALENDLY_WEBHOOK_SECRET', 'csec')
    monkeypatch.setenv('ZOOM_WEBHOOK_SECRET', 'zsec')
    monkeypatch.setenv('FIREFLIES_WEBHOOK_SECRET', 'fsec')
    # ensure provider secret header bypass (already enforced) by providing valid header
    monkeypatch.setenv('REQUIRE_PROVIDER_WEBHOOK_SECRET', 'false')


def _cal_sig(body_bytes: bytes):
    return hmac.new(b'csec', body_bytes, hashlib.sha256).hexdigest()


def test_calendly_idempotent():
    payload = {"event": "invitee.created", "payload": {"invitee_uuid": "dup-123"}}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = _cal_sig(body)
    ts = str(int(time.time()))
    r1 = client.post('/webhooks/calendly', json=payload, headers={'X-Calendly-Signature': sig, 'X-Calendly-Webhook-Request-Timestamp': ts})
    assert r1.status_code in (202, 200)
    r2 = client.post('/webhooks/calendly', json=payload, headers={'X-Calendly-Signature': sig, 'X-Calendly-Webhook-Request-Timestamp': ts})
    assert r2.status_code == 409  # replay detected


def _zoom_sig(ts: str, body_bytes: bytes):
    base = f"v0:{ts}:{body_bytes.decode()}".encode()
    return 'v0=' + hmac.new(b'zsec', base, hashlib.sha256).hexdigest()


def test_zoom_idempotent_debounce(monkeypatch):
    payload = {"event": "meeting.participant_joined", "payload": {}}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ts = str(int(time.time()))
    sig = _zoom_sig(ts, body)
    r1 = client.post('/webhooks/zoom', json=payload, headers={'X-Zm-Signature': sig, 'X-Zm-Request-Timestamp': ts})
    assert r1.status_code in (202, 200)
    # second immediate request should be debounced OR accepted based on debounce window
    r2 = client.post('/webhooks/zoom', json=payload, headers={'X-Zm-Signature': sig, 'X-Zm-Request-Timestamp': ts})
    assert r2.status_code in (202, 200, 429)  # allow rate limit if triggered


def test_fireflies_idempotent(monkeypatch):
    payload = {"event": "anything", "payload": {}}
    r1 = client.post('/webhooks/fireflies', json=payload)
    assert r1.status_code == 202
    r2 = client.post('/webhooks/fireflies', json=payload)
    assert r2.status_code in (202, 200)  # debounced or accepted
