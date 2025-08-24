from __future__ import annotations
"""Fireflies transcripts listing + attendee upsert helpers.

Implements the GraphQL queries specified:
 1) Transcripts list with filtering + paging (skip/limit)
 2) Transcript by id (including attendees)

Public functions:
 - list_transcripts(user_id, participant_email=None, from_date=None, to_date=None, limit=50)
 - get_transcript(transcript_id)
 - upsert_attendees_from_transcript(user_id, transcript)

Behavior:
 - Uses per-user (coach) stored API key (User.fireflies_api_key)
 - Raises RuntimeError on missing key
 - Retries transient HTTP/GraphQL failures with exponential backoff
 - Normalizes attendee emails (lower) & phone numbers (E.164) then ensures Client records
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User  # fireflies_api_key lives here
from app.repositories.meeting_tracking import (
    get_or_create_person_by_email,
    get_or_create_person_by_phone,
    ensure_client,
)
from app.utils.crypto import e164

logger = logging.getLogger("fireflies_transcripts")

FIREFLIES_GRAPHQL_ENDPOINT = "https://api.fireflies.ai/graphql"

TRANSCRIPTS_QUERY = (
    """query Transcripts($limit:Int,$skip:Int,$fromDate:DateTime,$toDate:DateTime,$participant:String){\n"
    "  transcripts(limit:$limit, skip:$skip, fromDate:$fromDate, toDate:$toDate, participant_email:$participant){\n"
    "    id title date duration meeting_url\n"
    "    attendees { email displayName phoneNumber name }\n"
    "    speakers { id name }\n"
    "    summary { overview keywords }\n"
    "  }\n"
    "}"""
)

TRANSCRIPT_BY_ID_QUERY = (
    """query TranscriptById($id:String!){\n"
    "  transcript(id:$id){\n"
    "    id title date duration meeting_url\n"
    "    attendees { email displayName phoneNumber name }\n"
    "    speakers { id name }\n"
    "    summary { overview keywords }\n"
    "    sentences { speaker_name text }\n"
    "  }\n"
    "}"""
)

class FirefliesGraphQLError(RuntimeError):
    pass

async def _fetch_api_key(session: AsyncSession, user_id: int) -> str:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.fireflies_api_key:
        raise RuntimeError("Fireflies API key not configured for user")
    return user.fireflies_api_key

async def _graphql_post(api_key: str, query: str, variables: Dict[str, Any], timeout: float = 20.0, retries: int = 3) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    attempt = 0
    delay = 1.0
    last_err: Exception | None = None
    while attempt <= retries:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(FIREFLIES_GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}, headers=headers)
            if resp.status_code >= 500:
                raise FirefliesGraphQLError(f"Server error {resp.status_code}")
            data = resp.json()
            if 'errors' in data:
                # Do not retry validation errors
                raise FirefliesGraphQLError(str(data['errors']))
            return data.get('data') or {}
        except FirefliesGraphQLError as e:
            last_err = e
            # Only retry if looks transient
            if "Server error" in str(e) and attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
                attempt += 1
                continue
            raise
        except Exception as e:  # network/timeouts
            last_err = e
            if attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
                attempt += 1
                continue
            raise FirefliesGraphQLError(f"GraphQL request failed: {e}") from e
    assert last_err  # pragma: no cover
    raise FirefliesGraphQLError(str(last_err))

def _iso(dt_val: datetime | None) -> Optional[str]:
    if not dt_val:
        return None
    if dt_val.tzinfo:
        return dt_val.astimezone().isoformat()
    return dt_val.isoformat() + 'Z'

async def list_transcripts(
    session: AsyncSession,
    user_id: int,
    participant_email: Optional[str] = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 50,
    page_size: int = 50,
    max_pages: int = 40,
) -> List[Dict[str, Any]]:
    """List transcripts for a coach (user) with optional filtering.

    Accumulates pages using skip/limit until overall 'limit' reached or pages exhausted.
    """
    api_key = await _fetch_api_key(session, user_id)
    collected: List[Dict[str, Any]] = []
    skip = 0
    remaining = limit
    page = 0
    while remaining > 0 and page < max_pages:
        take = min(page_size, remaining)
        variables = {
            "limit": take,
            "skip": skip,
            "fromDate": _iso(from_date),
            "toDate": _iso(to_date),
            "participant": participant_email.lower().strip() if participant_email else None,
        }
        data = await _graphql_post(api_key, TRANSCRIPTS_QUERY, variables)
        batch = (data.get('transcripts') if isinstance(data, dict) else None) or []
        if not batch:
            break
        collected.extend(batch)
        got = len(batch)
        remaining -= got
        skip += got
        page += 1
        if got < take:
            break
    return collected

async def get_transcript(session: AsyncSession, user_id: int, transcript_id: str) -> Dict[str, Any] | None:
    api_key = await _fetch_api_key(session, user_id)
    data = await _graphql_post(api_key, TRANSCRIPT_BY_ID_QUERY, {"id": transcript_id})
    t = data.get('transcript') if isinstance(data, dict) else None
    return t

async def upsert_attendees_from_transcript(session: AsyncSession, user_id: int, transcript: Dict[str, Any]) -> int:
    """Ensure attendees from a transcript exist as Clients for the coach.

    Returns number of attendees processed (created or matched). Emails lower-cased.
    """
    attendees = (transcript or {}).get('attendees') or []
    processed = 0
    for a in attendees:
        if not isinstance(a, dict):
            continue
        email = a.get('email') or a.get('displayName')  # fallback maybe email stored in displayName sometimes
        phone = a.get('phoneNumber')
        person = None
        if email:
            try:
                person = await get_or_create_person_by_email(session, email.lower().strip())
            except Exception as e:  # pragma: no cover
                logger.warning("fireflies attendee email error %s: %s", email, e)
                continue
        elif phone:
            norm = e164(phone)
            if not norm:
                continue
            person = await get_or_create_person_by_phone(session, norm)
        else:
            continue
        if person:
            await ensure_client(session, coach_id=user_id, person_id=person.id)
            processed += 1
    return processed

__all__ = [
    'list_transcripts', 'get_transcript', 'upsert_attendees_from_transcript',
    'TRANSCRIPTS_QUERY', 'TRANSCRIPT_BY_ID_QUERY', 'FirefliesGraphQLError'
]
