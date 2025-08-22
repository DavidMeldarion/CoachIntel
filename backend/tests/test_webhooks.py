import json
import os
from fastapi.testclient import TestClient
import pytest

# Import app instance
from app.main import app

# Monkeypatch redis for deterministic replay tests
class DummyRedis:
    def __init__(self):
        self.store = {}
    def setex(self, k, ttl, v):
        self.store[k] = v
    def get(self, k):
        return self.store.get(k)

client = TestClient(app)

@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv('CALENDLY_WEBHOOK_SECRET', 'secret')
    monkeypatch.setenv('ZOOM_WEBHOOK_SECRET', 'zsecret')
    # ensure redis fallback used
    import app.routers.webhooks as wh
    wh._redis_client = DummyRedis()
    yield


def test_calendly_valid_and_replay(monkeypatch):
    payload = {"event": "invitee.created", "payload": {"invitee_uuid": "abc-123"}}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    import hmac, hashlib
    sig = hmac.new(b'secret', body, hashlib.sha256).hexdigest()
    # first call ok
    r = client.post('/webhooks/calendly', json=payload, headers={'X-Calendly-Signature': sig, 'X-Calendly-Webhook-Request-Timestamp': str(int(__import__('time').time()))})
    assert r.status_code == 202
    # replay
    r2 = client.post('/webhooks/calendly', json=payload, headers={'X-Calendly-Signature': sig, 'X-Calendly-Webhook-Request-Timestamp': str(int(__import__('time').time()))})
    assert r2.status_code == 409


def test_calendly_bad_signature():
    payload = {"event": "invitee.created", "payload": {}}
    r = client.post('/webhooks/calendly', json=payload, headers={'X-Calendly-Signature': 'bad'})
    assert r.status_code == 400


def test_zoom_signature(monkeypatch):
    payload = {"event": "meeting.started", "payload": {}}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    import hmac, hashlib, time
    ts = str(int(time.time()))
    base = f"v0:{ts}:{body.decode()}".encode()
    sig = 'v0=' + hmac.new(b'zsecret', base, hashlib.sha256).hexdigest()
    r = client.post('/webhooks/zoom', json=payload, headers={'X-Zm-Signature': sig, 'X-Zm-Request-Timestamp': ts})
    assert r.status_code == 202
    # bad
    r2 = client.post('/webhooks/zoom', json=payload, headers={'X-Zm-Signature': 'v0=bad', 'X-Zm-Request-Timestamp': ts})
    assert r2.status_code == 400


def test_fireflies_simple():
    payload = {"event": "anything", "payload": {}}
    r = client.post('/webhooks/fireflies', json=payload)
    assert r.status_code == 202
