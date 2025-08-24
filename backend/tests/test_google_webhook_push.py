import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta, timezone

pytestmark = pytest.mark.asyncio

async def test_google_webhook_unknown_channel(client):
    r = client.post('/webhooks/google', headers={
        'X-Goog-Channel-ID': 'abc',
        'X-Goog-Resource-ID': 'res'
    })
    assert r.status_code == 200
    assert r.json().get('ignored') is True

async def test_google_webhook_triggers_sync(client, db_session):
    # Insert a fake ExternalAccount with channel info
    from app.models_meeting_tracking import ExternalAccount
    acct = ExternalAccount(coach_id=1, provider='google', calendar_channel_id='c1', calendar_resource_id='r1')
    db_session.add(acct)
    await db_session.flush()
    with patch('app.routers.webhooks.incremental_google_sync', new=AsyncMock(return_value=type('R', (), {'ok': True, 'value': 0}))):
        r = client.post('/webhooks/google', headers={
            'X-Goog-Channel-ID': 'c1',
            'X-Goog-Resource-ID': 'r1'
        })
        assert r.status_code == 200
        data = r.json()
        assert data['ok'] is True
        assert data['synced'] is True
