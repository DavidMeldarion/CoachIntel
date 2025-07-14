# Fireflies/Zoom API integration helpers for CoachSync
import os
import httpx

FIRELIES_API_KEY = os.getenv("FIREFLIES_API_KEY")
ZOOM_JWT = os.getenv("ZOOM_JWT")

async def fetch_fireflies_meetings(user_email: str, api_key: str = None):
    """Fetch meetings from Fireflies.ai for a given user."""
    url = f"https://api.fireflies.ai/v1/meetings?user_email={user_email}"
    headers = {"x-api-key": api_key} if api_key else {}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

async def fetch_zoom_meetings(user_id: str, jwt: str = None):
    """Fetch meetings from Zoom for a given user."""
    url = f"https://api.zoom.us/v2/users/{user_id}/meetings"
    headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
