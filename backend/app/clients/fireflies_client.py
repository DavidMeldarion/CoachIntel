from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import httpx
import logging

from .base import OAuthExternalClient

logger = logging.getLogger("fireflies_client")

FIREFLIES_API_URL = "https://api.fireflies.ai/graphql"

@dataclass
class FirefliesParticipant:
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]

@dataclass
class FirefliesMeetingSummary:
    id: str
    title: Optional[str]
    date: Optional[str]
    duration: Optional[int]
    meeting_link: Optional[str]
    participants: List[FirefliesParticipant]
    summary: Dict[str, Any]

@dataclass
class FirefliesTranscript:
    id: str
    speakers: List[FirefliesParticipant]
    full_text: str
    raw: Dict[str, Any]

class FirefliesClient(OAuthExternalClient):
    def __init__(self, session, coach_id: int):
        super().__init__(session, coach_id, provider='fireflies')

    async def list_meetings(self, limit: int = 25) -> List[FirefliesMeetingSummary]:
        tok = await self._ensure_token()
        query = """
        query($limit: Int!) {
          transcripts(limit: $limit) {
            id
            title
            date
            duration
            meeting_link
            summary { keywords action_items outline shorthand_bullet overview }
            participants { name email user_id }
          }
        }
        """
        payload = {"query": query, "variables": {"limit": limit}}
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=40.0) as client:
            resp = await client.post(FIREFLIES_API_URL, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.warning("Fireflies list_meetings failed %s: %s", resp.status_code, resp.text[:200])
            return []
        data = resp.json().get('data', {}).get('transcripts', [])
        out: List[FirefliesMeetingSummary] = []
        for t in data:
            parts = t.get('participants') or []
            part_objs = []
            for p in parts:
                if isinstance(p, dict):
                    part_objs.append(FirefliesParticipant(name=p.get('name'), email=p.get('email'), phone=None))
            out.append(FirefliesMeetingSummary(
                id=t.get('id'),
                title=t.get('title'),
                date=t.get('date'),
                duration=t.get('duration'),
                meeting_link=t.get('meeting_link'),
                participants=part_objs,
                summary=t.get('summary') or {},
            ))
        return out

    async def get_transcript(self, transcript_id: str) -> FirefliesTranscript | None:
        tok = await self._ensure_token()
        query = """
        query GetTranscript($id: String!) {
          transcript(id: $id) {
            id
            title
            date
            participants { name email user_id }
            sentences { text speaker_name }
          }
        }
        """
        payload = {"query": query, "variables": {"id": transcript_id}}
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=40.0) as client:
            resp = await client.post(FIREFLIES_API_URL, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.warning("Fireflies get_transcript failed %s: %s", resp.status_code, resp.text[:200])
            return None
        t = resp.json().get('data', {}).get('transcript')
        if not t:
            return None
        speakers_raw = t.get('participants') or []
        speakers = []
        for s in speakers_raw:
            if isinstance(s, dict):
                speakers.append(FirefliesParticipant(name=s.get('name'), email=s.get('email'), phone=None))
        sentences = t.get('sentences') or []
        lines = []
        for s in sentences:
            if isinstance(s, dict):
                speaker = s.get('speaker_name') or 'Unknown'
                text = s.get('text') or ''
                if text:
                    lines.append(f"{speaker}: {text}")
        full_text = "\n".join(lines)
        return FirefliesTranscript(
            id=t.get('id'),
            speakers=speakers,
            full_text=full_text,
            raw=t,
        )
