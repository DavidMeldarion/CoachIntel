import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

# NOTE: This is a HIGH-LEVEL outline test; real HTTP calls would be mocked.
# Here we just assert function wiring does not raise with missing account.

async def test_incremental_sync_no_account(db_session):
    from app.services.calendar_sync import incremental_google_sync
    res = await incremental_google_sync(db_session, coach_id=99999, time_min=datetime.now(timezone.utc)-timedelta(days=1), time_max=datetime.now(timezone.utc)+timedelta(days=1))
    assert not res.ok
    assert 'No google external account' in res.error
