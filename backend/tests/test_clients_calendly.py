import pytest, respx, httpx
from app.models_meeting_tracking import ExternalAccount
from app.clients.calendly_client import CalendlyClient
from app.utils.crypto import fernet

@pytest.mark.asyncio
async def test_calendly_invitee_and_parse(db_session):
    f = fernet()
    token = f.encrypt(b"caltok").decode()
    acct = ExternalAccount(coach_id=3, provider='calendly', access_token_enc=token)
    db_session.add(acct)
    await db_session.flush()

    client = CalendlyClient(db_session, coach_id=3)
    route = respx.get("https://api.calendly.com/invitees/inv123").mock(
        return_value=httpx.Response(200, json={"resource":{"uuid":"inv123","email":"c@example.com","name":"C","status":"active"}})
    )
    inv = await client.get_invitee("inv123")
    assert route.called
    assert inv and inv.email == 'c@example.com'

    # webhook parse
    payload = {"event":"invitee.created","payload":{"invitee":{"uuid":"inv123"}}}
    evt = CalendlyClient.parse_webhook(payload)
    assert evt.invitee_uuid == 'inv123'
