import pytest
from uuid import uuid4
from app.models import create_or_update_user, AsyncSessionLocal
from app.models_meeting_tracking import ReviewCandidate, Person
from app.repositories.meeting_tracking import get_or_create_person_by_email
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
async def coach_a():
    return await create_or_update_user(email="coachA@example.com", first_name="A", last_name="Coach")

@pytest.fixture
async def coach_b():
    return await create_or_update_user(email="coachB@example.com", first_name="B", last_name="Coach")

async def _auth(email: str):
    return {"x-user-email": email}

@pytest.mark.asyncio
async def test_choose_person_existing_person_resolves(coach_a):
    # Create existing person candidate should map to
    async with AsyncSessionLocal() as session:
        person = Person(primary_email="existing@example.com", emails=["existing@example.com"], email_hashes=["dummy"])
        session.add(person)
        await session.flush()
        rc = ReviewCandidate(coach_id=coach_a.id, meeting_id=None, attendee_source="zoom", raw_email="existing@example.com", reason="ambiguous")
        session.add(rc)
        await session.commit()
        cand_id = rc.id
        person_id = person.id
    r = client.post(f"/review/candidates/{cand_id}/choose_person", headers={"x-user-email": coach_a.email}, json={"person_id": str(person_id)})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "resolved"

@pytest.mark.asyncio
async def test_unauthorized_rejected(coach_a):
    # Create candidate
    async with AsyncSessionLocal() as session:
        rc = ReviewCandidate(coach_id=coach_a.id, meeting_id=None, attendee_source="zoom", raw_email="unauth@example.com", reason="ambiguous")
        session.add(rc)
        await session.commit()
        cand_id = rc.id
    # No auth
    r = client.post(f"/review/candidates/{cand_id}/create_person", json={})
    assert r.status_code in (401, 403)
    # Auth ok
    r2 = client.post(f"/review/candidates/{cand_id}/create_person", headers={"x-user-email": coach_a.email}, json={})
    assert r2.status_code == 200

@pytest.mark.asyncio
async def test_cross_user_access_404(coach_a, coach_b):
    async with AsyncSessionLocal() as session:
        rc = ReviewCandidate(coach_id=coach_a.id, meeting_id=None, attendee_source="zoom", raw_email="cross@example.com", reason="ambiguous")
        session.add(rc)
        await session.commit()
        cand_id = rc.id
    # Coach B should not see candidate owned by coach A
    r = client.post(f"/review/candidates/{cand_id}/choose_person", headers={"x-user-email": coach_b.email}, json={"person_id": str(uuid4())})
    assert r.status_code == 404

@pytest.mark.asyncio
async def test_invalid_candidate_uuid():
    r = client.post(f"/review/candidates/{uuid4()}/choose_person", headers={"x-user-email": "nonexistent@example.com"}, json={"person_id": str(uuid4())})
    # Either 401 (user not found) or 404 if user created implicitly later; accept both
    assert r.status_code in (401, 404)
