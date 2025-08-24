from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
import logging

from .base import OAuthExternalClient

logger = logging.getLogger("zoom_client")

ZOOM_BASE = "https://api.zoom.us/v2"

@dataclass
class ZoomParticipant:
    name: Optional[str]
    email: Optional[str]
    join_time: Optional[datetime]
    leave_time: Optional[datetime]
    duration_seconds: Optional[int]
    raw: Dict[str, Any]

class ZoomClient(OAuthExternalClient):
    def __init__(self, session, coach_id: int):
        super().__init__(session, coach_id, provider='zoom')

    async def list_meeting_participants(self, meeting_id: str) -> List[ZoomParticipant]:
        tok = await self._ensure_token()
        url = f"{ZOOM_BASE}/report/meetings/{meeting_id}/participants"
        headers = {"Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            logger.warning("Zoom participants failed %s: %s", resp.status_code, resp.text[:200])
            return []
        data = resp.json()
        parts = data.get('participants', [])
        out: List[ZoomParticipant] = []
        for p in parts:
            if not isinstance(p, dict):
                continue
            jt = _parse_dt(p.get('join_time'))
            lt = _parse_dt(p.get('leave_time'))
            dur = None
            if jt and lt:
                dur = int((lt - jt).total_seconds())
            out.append(ZoomParticipant(
                name=p.get('name'),
                email=p.get('user_email'),  # may be None
                join_time=jt,
                leave_time=lt,
                duration_seconds=dur,
                raw=p,
            ))
        return out

    async def get_meeting(self, meeting_id: str) -> Dict[str, Any] | None:
        tok = await self._ensure_token()
        url = f"{ZOOM_BASE}/meetings/{meeting_id}"
        headers = {"Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            logger.warning("Zoom get_meeting failed %s: %s", resp.status_code, resp.text[:200])
            return None
        return resp.json()

def _parse_dt(val: str | None) -> Optional[datetime]:
    if not val:
        return None
    try:
        # Zoom returns times like '2024-02-12T18:00:00Z'
        if val.endswith('Z'):
            val = val[:-1] + '+00:00'
        return datetime.fromisoformat(val)
    except Exception:
        return None
