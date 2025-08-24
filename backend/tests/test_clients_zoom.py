import pytest, respx, httpx
from sqlalchemy import select
from app.models_meeting_tracking import ExternalAccount
from app.clients.zoom_client import ZoomClient
from app.utils.crypto import fernet

@pytest.mark.asyncio
async def test_zoom_participants(db_session):
    f = fernet()
    token = f.encrypt(b"zootok").decode()
    acct = ExternalAccount(coach_id=2, provider='zoom', access_token_enc=token)
    db_session.add(acct)
    await db_session.flush()

    client = ZoomClient(db_session, coach_id=2)
    route = respx.get("https://api.zoom.us/v2/report/meetings/123/participants").mock(
        return_value=httpx.Response(200, json={"participants":[{"name":"User1","user_email":None,"join_time":"2024-02-02T10:00:00Z","leave_time":"2024-02-02T10:30:00Z"}]})
    )
    parts = await client.list_meeting_participants("123")
    assert route.called
    assert len(parts) == 1
    assert parts[0].duration_seconds == 1800
