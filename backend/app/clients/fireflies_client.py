from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import httpx
import logging

from .base import OAuthExternalClient, AccessToken, TokenSourceError
from sqlalchemy import select
from app.models import User

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

    async def _ensure_token(self) -> AccessToken:
        """Return an AccessToken using the user's stored Fireflies API key if present.

        Precedence:
          1. User.fireflies_api_key (plain API key stored on profile)
          2. Fallback to superclass OAuth external account (legacy path)

        Caches the token in self._cached (no expiry for API key)."""
        # If we already cached (API key or OAuth) return it
        if self._cached and (self._cached.expires_at is None):
            return self._cached
        # Try profile API key
        try:
            result = await self.session.execute(select(User.fireflies_api_key).where(User.id == self.coach_id))
            api_key = result.scalar_one_or_none()
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("Fireflies API key lookup failed for user %s: %s", self.coach_id, e)
            api_key = None
        if api_key:
            self._cached = AccessToken(token=api_key, expires_at=None)
            return self._cached
        # Fallback to legacy OAuth workflow (may raise TokenSourceError)
        try:
            return await super()._ensure_token()
        except TokenSourceError:
            # Provide clearer message specific to Fireflies
            raise TokenSourceError(f"No Fireflies API key configured and no external account for coach={self.coach_id}")

    async def list_meetings(self, limit: int = 25) -> List[FirefliesMeetingSummary]:
        tok = await self._ensure_token()
        query = """
        query Transcripts($limit: Int!) {
          transcripts(limit: $limit) {
            id
            title
            date
            duration
            meeting_link
            participants
            summary { overview keywords }
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
            part_objs: List[FirefliesParticipant] = []
            for p in (t.get('participants') or []):
                if isinstance(p, str):
                    part_objs.append(FirefliesParticipant(name=None, email=p, phone=None))
            out.append(FirefliesMeetingSummary(
                id=t.get('id'),
                title=t.get('title'),
                date=t.get('date'),
                duration=t.get('duration'),
                meeting_link=(t.get('meeting_link') or (t.get('meeting_info') or {}).get('meeting_url')),
                participants=part_objs,
                summary=t.get('summary') or {},
            ))
        return out

    async def get_transcript(self, transcript_id: str) -> FirefliesTranscript | None:
        tok = await self._ensure_token()
        primary_query = """
        query Transcript($transcriptId: String!) {
          transcript(id: $transcriptId) {
            id
            title
            date
            participants
            meeting_attendees { displayName email phoneNumber name }
            speakers { id name }
            sentences { index speaker_name text }
            summary { overview keywords }
            meeting_link
          }
        }
        """
        fallback_query = """
        query Transcript($transcriptId: String!) {
          transcript(id: $transcriptId) {
            id
            title
            date
            participants
            sentences { index speaker_name text }
            meeting_link
          }
        }
        """
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {tok.token}"}
        async with httpx.AsyncClient(timeout=40.0) as client:
            resp = await client.post(FIREFLIES_API_URL, json={"query": primary_query, "variables": {"transcriptId": transcript_id}}, headers=headers)
            if resp.status_code >= 400 and 'Cannot query field "attendees"' in resp.text:
                resp = await client.post(FIREFLIES_API_URL, json={"query": fallback_query, "variables": {"transcriptId": transcript_id}}, headers=headers)
        if resp.status_code >= 400:
            logger.warning("Fireflies get_transcript failed %s: %s", resp.status_code, resp.text[:200])
            return None
        t = resp.json().get('data', {}).get('transcript')
        if not t:
            return None
        speakers: List[FirefliesParticipant] = []
        if 'meeting_attendees' in t and isinstance(t.get('meeting_attendees'), list):
            for s in (t.get('meeting_attendees') or []):
                if isinstance(s, dict):
                    name = s.get('name') or s.get('displayName')
                    speakers.append(FirefliesParticipant(name=name, email=s.get('email'), phone=s.get('phoneNumber')))
        elif 'participants' in t:
            parts = t.get('participants') or []
            for p in parts:
                if isinstance(p, str):
                    speakers.append(FirefliesParticipant(name=p, email=None, phone=None))
        sentences = t.get('sentences') or []
        lines: List[str] = []
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
