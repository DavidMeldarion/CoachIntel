import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

# Ensure secrets for test
os.environ.setdefault("CALENDLY_PROVIDER_SECRET", "cal-test")
os.environ.setdefault("ZOOM_PROVIDER_SECRET", "zoom-test")
os.environ.setdefault("FIREFLIES_PROVIDER_SECRET", "fire-test")
os.environ.setdefault("REQUIRE_PROVIDER_WEBHOOK_SECRET", "true")
os.environ.setdefault("PROVIDER_WEBHOOK_HEADER", "X-Webhook-Secret")

client = TestClient(app)


def test_payload_too_large():
    big_body = "x" * (1024 * 1024 + 1)  # 1MB + 1
    r = client.post("/webhooks/calendly", data=big_body, headers={"X-Webhook-Secret": "cal-test"})
    assert r.status_code == 413, r.text


def test_webhook_secret_missing():
    r = client.post("/webhooks/calendly", json={"event": "invitee.created", "payload": {}}, headers={})
    assert r.status_code == 401


def test_webhook_secret_incorrect():
    r = client.post(
        "/webhooks/calendly",
        json={"event": "invitee.created", "payload": {}},
        headers={"X-Webhook-Secret": "wrong"},
    )
    assert r.status_code == 401


def test_webhook_secret_correct():
    r = client.post(
        "/webhooks/calendly",
        json={"event": "invitee.created", "payload": {}},
        headers={"X-Webhook-Secret": "cal-test"},
    )
    # Calendly handler expects more structure; we just assert we pass middleware (202 or 400 from handler)
    assert r.status_code in (202, 400), r.text


def test_other_provider_secret():
    r = client.post(
        "/webhooks/zoom",
        json={"event": "meeting.ended", "payload": {}},
        headers={"X-Webhook-Secret": "zoom-test"},
    )
    assert r.status_code in (202, 400)


def test_fireflies_secret():
    r = client.post(
        "/webhooks/fireflies",
        json={"event": "anything", "payload": {}},
        headers={"X-Webhook-Secret": "fire-test"},
    )
    assert r.status_code in (202, 400)
