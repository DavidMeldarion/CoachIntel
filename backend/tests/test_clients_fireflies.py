import pytest, respx, httpx
from app.models_meeting_tracking import ExternalAccount
from app.clients.fireflies_client import FirefliesClient
from app.utils.crypto import fernet

@pytest.mark.asyncio
async def test_fireflies_list_and_transcript(db_session):
    f = fernet()
    token = f.encrypt(b"fftok").decode()
    acct = ExternalAccount(coach_id=4, provider='fireflies', access_token_enc=token)
    db_session.add(acct)
    await db_session.flush()

    client = FirefliesClient(db_session, coach_id=4)
    list_route = respx.post("https://api.fireflies.ai/graphql").mock(
        return_value=httpx.Response(200, json={"data":{"transcripts":[{"id":"t1","title":"Call","date":"2024-01-01","duration":1200,"meeting_link":"https://m","summary":{},"participants":[{"name":"P1","email":"p1@example.com"}] }]}})
    )
    meetings = await client.list_meetings(limit=5)
    assert list_route.called
    assert meetings and meetings[0].participants[0].email == 'p1@example.com'

    transcript_route = respx.post("https://api.fireflies.ai/graphql").mock(
        return_value=httpx.Response(200, json={"data":{"transcript":{"id":"t1","participants":[{"name":"S1","email":"s1@example.com"}],"sentences":[{"speaker_name":"S1","text":"Hi"}]}}})
    )
    tr = await client.get_transcript("t1")
    assert transcript_route.called
    assert tr and 'S1:' in tr.full_text
