import pytest
from uuid import uuid4
from app.models import AsyncSessionLocal, create_or_update_user
from app.models_meeting_tracking import ReviewCandidate

@pytest.fixture
async def user():  # reuse create_or_update against test DB
    return await create_or_update_user(email="testauth@example.com", first_name="Test", last_name="User")

async def _auth_headers(email: str):
    return {"x-user-email": email}

@pytest.mark.asyncio
async def test_review_candidates_list_requires_auth(user):
    # no auth
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get("/review/candidates")
    assert r.status_code in (401, 403)
    # with auth
    r2 = client.get("/review/candidates", headers={"x-user-email": user.email})
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)

@pytest.mark.asyncio
async def test_choose_person_and_create_person_flow(user):
    # Seed a candidate directly (simulate unresolved ambiguity)
    async with AsyncSessionLocal() as session:
        rc = ReviewCandidate(coach_id=user.id, meeting_id=None, attendee_source="zoom", raw_email="ambiguous@example.com", reason="manual_test")
        session.add(rc)
        await session.commit()
        rid = rc.id
    # Create person via endpoint
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.post(f"/review/candidates/{rid}/create_person", headers={"x-user-email": user.email}, json={})
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"
    # Idempotent: second call should 404 (candidate already resolved) or stay resolved
    r2 = client.post(f"/review/candidates/{rid}/create_person", headers={"x-user-email": user.email}, json={})
    assert r2.status_code in (200, 404)

@pytest.mark.asyncio
async def test_choose_person_existing(user):
    async with AsyncSessionLocal() as session:
        # create candidate + a target person via person creation route (reuse create_person endpoint)
        rc = ReviewCandidate(coach_id=user.id, meeting_id=None, attendee_source="zoom", raw_email="select@example.com", reason="manual_test")
        session.add(rc)
        await session.commit()
        cand_id = rc.id
    # First create a person through the create_person endpoint
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r_create = client.post(f"/review/candidates/{cand_id}/create_person", headers={"x-user-email": user.email}, json={})
    assert r_create.status_code == 200
    # Attempt choose_person on already resolved candidate should still return resolved
    r_choose = client.post(f"/review/candidates/{cand_id}/choose_person", headers={"x-user-email": user.email}, json={"person_id": uuid4().hex})
    assert r_choose.status_code in (200, 404)
