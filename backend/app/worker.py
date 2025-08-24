import logging
import httpx
import datetime
import os
import ssl
import asyncio
from collections import defaultdict
from typing import Optional, List, Dict, Set
from urllib.parse import urlparse
import itertools
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import or_, cast, Text, select

from app.models import User, Meeting, Transcript, SessionLocal, AsyncSessionLocal  # Use sync + async sessions
from app.integrations import fetch_fireflies_meetings_sync
from app.summarization import summarize_meeting
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URL
import json
from app.services.oauth import refresh_if_needed, OAuthError
from app.utils.crypto import fernet
from app.models_meeting_tracking import ExternalAccount, Meeting as MTMeeting
from app.services.calendar_sync import (
    list_events,
    upsert_events_as_meetings,
    upsert_zoom_meeting,
    upsert_fireflies_meetings,
    upsert_calendly_event,
)

# Prefer a full Redis URL from env (e.g., Upstash rediss://...)
ENV_REDIS_URL = os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "coachintel-redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = ENV_REDIS_URL or f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Log Redis configuration for visibility
logger = logging.getLogger(__name__)
logger.info(f"[Celery] Using Redis at {REDIS_URL}")

celery_app = Celery(
    'worker',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# If using TLS (Upstash rediss://), configure SSL (env-driven verification)
if REDIS_URL.startswith("rediss://"):
    ssl_verify_env = os.getenv("REDIS_SSL_VERIFY", "false").lower() in ("1", "true", "yes")
    cert_reqs = ssl.CERT_REQUIRED if ssl_verify_env else ssl.CERT_NONE
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": cert_reqs}
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": cert_reqs}

# Explicitly disable worker remote control to avoid PUBLISH traffic
celery_app.conf.worker_enable_remote_control = False

# Expire results to limit backend footprint (in seconds)
celery_app.conf.result_expires = int(os.getenv("CELERY_RESULT_EXPIRES", "3600"))

# Core serialization and reliability
celery_app.conf.update(
    result_serializer='json',
    task_serializer='json',
    accept_content=['json'],
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,  # retry forever
    # Task execution safety
    task_track_started=False,            # avoid extra writes/events
    task_acks_late=True,                 # ack after execution for reliability
    task_reject_on_worker_lost=True,     # requeue if worker dies
    task_soft_time_limit=int(os.getenv("CELERY_SOFT_TIME_LIMIT", "600")),  # 10m soft
    task_time_limit=int(os.getenv("CELERY_HARD_TIME_LIMIT", "900")),       # 15m hard
    # Ignore results by default to reduce backend chatter
    task_ignore_result=True,
)

# Tune Celery to reduce Redis command volume
celery_app.conf.update(
    broker_pool_limit=1,                 # single connection to broker
    worker_concurrency=1,                # one consumer (we also run --pool solo)
    worker_prefetch_multiplier=1,        # no aggressive prefetch
    worker_send_task_events=False,       # stop emitting events (avoids PUBLISH)
    task_send_sent_event=False,          # don't send 'task-sent' events
    worker_disable_rate_limits=True,
)

# Prefer long-lived sockets and fewer health checks (helps with Upstash)
health_interval = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "300"))
celery_app.conf.broker_transport_options = {
    **(celery_app.conf.broker_transport_options or {}),
    "health_check_interval": health_interval,
    "socket_keepalive": True,
    "socket_timeout": int(os.getenv("REDIS_SOCKET_TIMEOUT", "300")),
    "socket_connect_timeout": int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "30")),
    "retry_on_timeout": True,
    # If using late acks, ensure messages reappear if not acknowledged in time
    "visibility_timeout": int(os.getenv("REDIS_VISIBILITY_TIMEOUT", "900")),
}
celery_app.conf.result_backend_transport_options = {
    **(celery_app.conf.result_backend_transport_options or {}),
    "health_check_interval": health_interval,
    "retry_on_timeout": True,
}

celery_app.conf.beat_schedule = {
    'sync-fireflies-meetings-hourly': {
        'task': 'worker.sync_fireflies_meetings',
        'schedule': crontab(minute=0, hour='*'),
        'args': ()
    },
    'reconcile-meetings-nightly': {
        'task': 'worker.reconcile_meetings',
        'schedule': crontab(minute=0, hour='3'),  # 3am UTC nightly
        'args': ()
    },
    'refresh-google-tokens-every-10-minutes': {
        'task': 'worker.refresh_all_google_tokens',
        'schedule': crontab(minute='*/10'),
        'args': ()
    },
    'refresh-oauth-external-accounts-5m': {
        'task': 'worker.refresh_external_accounts',
        'schedule': crontab(minute='*/5'),
        'args': ()
    },
    # 'summarize-missing-transcripts-every-15-minutes': {
    #     'task': 'worker.summarize_missing_transcripts',
    #     'schedule': crontab(minute='*/15'),
    #     'args': ()
    # },
}

# -------------------------------------------------
# Webhook ingestion task stubs (idempotent wrappers)
# -------------------------------------------------
@celery_app.task(name="calendly_ingest")
def calendly_ingest(payload: dict):  # type: ignore[override]
    """Stub Calendly ingestion.

    TODO: Map invitee -> Meeting / Person enrichment.
    Keep lightweight & idempotent (log only for now).
    """
    try:
        logging.info("[CalendlyIngest] payload=%s", json.dumps(payload))
    except Exception:
        logging.info("[CalendlyIngest] payload (raw repr)=%r", payload)
    return {"status": "ok"}

@celery_app.task(name="zoom_ingest")
def zoom_ingest(payload: dict):  # type: ignore[override]
    try:
        logging.info("[ZoomIngest] payload=%s", json.dumps(payload))
    except Exception:
        logging.info("[ZoomIngest] payload (raw repr)=%r", payload)
    return {"status": "ok"}

@celery_app.task(name="fireflies_ingest")
def fireflies_ingest(payload: dict):  # type: ignore[override]
    try:
        logging.info("[FirefliesIngest] payload=%s", json.dumps(payload))
    except Exception:
        logging.info("[FirefliesIngest] payload (raw repr)=%r", payload)
    return {"status": "ok"}


# -------------------------------------------------
# Provider ingestion tasks (Calendly / Fireflies orchestrators)
# -------------------------------------------------

@celery_app.task(name="ingest_calendly_event")
def ingest_calendly_event(coach_id: int, event_uuid: str, invitee_uuid: str | None = None):
    """Idempotent Calendly event + invitee upsert wrapper."""
    async def _run():
        async with AsyncSessionLocal() as session:  # type: ignore
            from app.services.calendar_sync import upsert_calendly_event
            res = await upsert_calendly_event(session, coach_id, event_uuid, invitee_uuid)
            if res.ok:
                await session.commit()
            else:
                await session.rollback()
            return {"ok": res.ok, "error": res.error, **(res.value or {})}
    return asyncio.run(_run())


@celery_app.task(name="ingest_fireflies_recent")
def ingest_fireflies_recent(coach_id: int, limit: int = 25):
    """Fetch recent Fireflies meetings and upsert."""
    async def _run():
        async with AsyncSessionLocal() as session:  # type: ignore
            from app.services.calendar_sync import upsert_fireflies_meetings
            res = await upsert_fireflies_meetings(session, coach_id, limit)
            if res.ok:
                await session.commit()
            else:
                await session.rollback()
            return {"ok": res.ok, "error": res.error, **(res.value or {})}
    return asyncio.run(_run())


# -------------------------------------------------
# Calendar & meeting sync / reconciliation tasks
# -------------------------------------------------

def _parse_iso_utc(s: Optional[str]) -> datetime.datetime:
    if not s:
        return datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    try:
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return datetime.datetime.utcnow() - datetime.timedelta(hours=24)


@celery_app.task
def sync_google_calendar(coach_id: int, since_iso: Optional[str] = None):
    """Ingest Google Calendar events for a coach since given ISO timestamp.

    Strategy:
      - Default window: since (or 24h back) -> now + 7d (future events helpful for prep).
      - Uses async session + existing list_events/upsert pipeline.
      - Returns counts for observability.
    """
    async def _run() -> dict:
        start = _parse_iso_utc(since_iso)
        now = datetime.datetime.utcnow()
        future = now + datetime.timedelta(days=7)
        async with AsyncSessionLocal() as session:  # type: ignore
            try:
                events_res = await list_events(session, coach_id, 'google', start, future)
                if not events_res.ok:
                    return {"error": events_res.error or "list_failed"}
                events = events_res.value or []
                inserted = await upsert_events_as_meetings(session, coach_id, 'google', events)
                await session.commit()
                return {"events": len(events), "upserted": inserted}
            except Exception as e:  # pragma: no cover
                await session.rollback()
                logging.error("[sync_google_calendar] coach=%s error=%s", coach_id, e)
                return {"error": str(e)}
    return asyncio.run(_run())


@celery_app.task
def sync_zoom_reports(coach_id: int, meeting_ids: Optional[List[str]] = None):
    """Zoom ingestion using typed client.

    If meeting_ids provided, upsert those; otherwise no-op placeholder.
    """
    async def _run() -> dict:
        if not meeting_ids:
            return {"status": "no_meetings_specified"}
        results = []
        async with AsyncSessionLocal() as session:  # type: ignore
            for mid in meeting_ids:
                res = await upsert_zoom_meeting(session, coach_id, mid)
                results.append({"meeting_id": mid, "ok": res.ok, "error": res.error, **(res.value or {})})
            await session.commit()
        return {"processed": len(results), "results": results}
    return asyncio.run(_run())


@celery_app.task
def reconcile_meetings(coach_id: Optional[int] = None, lookback_hours: int = 168, proximity_minutes: int = 5):
    """Reconcile meetings across providers using multi-tier priority rules.

    Priority link rules (applied in order building an undirected graph; components are merged):
      1) Exact iCalUID match (ical_uid field).
      2) Cross-provider meeting IDs: any identical value appearing in external_refs.zoom_meeting_id OR
         external_refs.fireflies_meeting_id (value equality links regardless of key origin).
      3) Fallback: started_at within ±proximity_minutes AND match on join_url domain (coach-scoped).

    Merge behavior:
      - Keeper chosen as earliest started_at (else arbitrary stable ordering).
      - external_refs union (preserve existing keys; add new keys from others).
      - Populate missing core fields (topic/platform/join_url/timestamps) from others if empty.
      - Attendees: union across all meetings; new attendees added to keeper.
      - Identity resolution re-run for any keeper attendees lacking person_id.
      - Non-keeper meetings deleted (cascade removes their attendees once migrated).
    """
    async def _run() -> dict:
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=lookback_hours)
        merged_components = 0
        merged_meetings = 0
        scanned = 0
        async with AsyncSessionLocal() as session:  # type: ignore
            from app.models_meeting_tracking import MeetingAttendee  # local import to avoid cycles
            from app.repositories.meeting_tracking import add_or_update_attendee, resolve_attendee
            try:
                stmt = select(MTMeeting).where(MTMeeting.started_at >= since)
                if coach_id:
                    stmt = stmt.where(MTMeeting.coach_id == coach_id)
                meetings: List[MTMeeting] = (await session.execute(stmt)).scalars().all()
                scanned = len(meetings)
                if not meetings:
                    return {"scanned": 0, "merged_meetings": 0, "merged_components": 0, "status": "ok"}

                # Build adjacency graph
                adj: Dict[str, Set[str]] = defaultdict(set)
                def link(a: MTMeeting, b: MTMeeting):
                    if a.id == b.id:
                        return
                    adj[str(a.id)].add(str(b.id))
                    adj[str(b.id)].add(str(a.id))

                # 1) iCalUID exact
                ical_groups: Dict[str, List[MTMeeting]] = defaultdict(list)
                for m in meetings:
                    if m.ical_uid:
                        ical_groups[m.ical_uid].append(m)
                for g in ical_groups.values():
                    if len(g) > 1:
                        for a, b in itertools.combinations(g, 2):
                            link(a, b)

                # 2) Cross-provider meeting IDs (zoom_meeting_id / fireflies_meeting_id)
                id_map: Dict[str, List[MTMeeting]] = defaultdict(list)
                for m in meetings:
                    refs = m.external_refs or {}
                    for key in ("zoom_meeting_id", "fireflies_meeting_id"):
                        val = refs.get(key)
                        if val:
                            id_map[str(val)].append(m)
                for g in id_map.values():
                    if len(g) > 1:
                        for a, b in itertools.combinations(g, 2):
                            link(a, b)

                # 3) Fallback proximity + join_url domain
                domain_groups: Dict[tuple, List[MTMeeting]] = defaultdict(list)
                for m in meetings:
                    if not m.join_url or not m.started_at:
                        continue
                    try:
                        domain = urlparse(m.join_url).netloc.lower()
                    except Exception:
                        continue
                    if not domain:
                        continue
                    domain_groups[(m.coach_id, domain)].append(m)
                for (_coach, _domain), group in domain_groups.items():
                    group.sort(key=lambda x: x.started_at or datetime.datetime.min.replace(tzinfo=None))
                    for i, m in enumerate(group):
                        for j in range(i + 1, len(group)):
                            n = group[j]
                            if not (m.started_at and n.started_at):
                                continue
                            delta_min = abs((m.started_at - n.started_at).total_seconds()) / 60.0
                            if delta_min <= proximity_minutes:
                                link(m, n)
                            elif (n.started_at - m.started_at).total_seconds() / 60.0 > proximity_minutes:
                                # further items will only be later; break optimization
                                break

                # Connected components (DFS)
                visited: Set[str] = set()
                components: List[List[MTMeeting]] = []
                meeting_by_id = {str(m.id): m for m in meetings}
                for mid in meeting_by_id.keys():
                    if mid in visited:
                        continue
                    stack = [mid]
                    comp_ids: List[str] = []
                    while stack:
                        cur = stack.pop()
                        if cur in visited:
                            continue
                        visited.add(cur)
                        comp_ids.append(cur)
                        for nxt in adj.get(cur, []):
                            if nxt not in visited:
                                stack.append(nxt)
                    if len(comp_ids) > 1:
                        components.append([meeting_by_id[cid] for cid in comp_ids])

                # Merge each component
                for comp in components:
                    comp.sort(key=lambda x: (x.started_at or datetime.datetime.max, str(x.id)))
                    keeper = comp[0]
                    others = comp[1:]
                    changed = False
                    for other in others:
                        # Union external refs
                        krefs = dict(keeper.external_refs or {})
                        for k, v in (other.external_refs or {}).items():
                            if k not in krefs:
                                krefs[k] = v
                                changed = True
                        keeper.external_refs = krefs
                        # Fill blank attributes
                        for attr in ("topic", "platform", "join_url"):
                            if not getattr(keeper, attr) and getattr(other, attr):
                                setattr(keeper, attr, getattr(other, attr))
                                changed = True
                        if (not keeper.started_at or (other.started_at and other.started_at < keeper.started_at)):
                            keeper.started_at = other.started_at
                            changed = True
                        if (not keeper.ended_at or (other.ended_at and (not keeper.ended_at or other.ended_at > keeper.ended_at))):
                            keeper.ended_at = other.ended_at
                            changed = True
                        # Migrate attendees
                        o_attendees = (await session.execute(select(MeetingAttendee).where(MeetingAttendee.meeting_id == other.id))).scalars().all()
                        for att in o_attendees:
                            ident = att.external_attendee_id or att.raw_email or att.raw_name
                            # Check if exists in keeper
                            existing = (await session.execute(select(MeetingAttendee).where(
                                MeetingAttendee.meeting_id == keeper.id,
                                MeetingAttendee.source == att.source
                            ))).scalars().all()
                            found = False
                            for ex in existing:
                                ex_ident = ex.external_attendee_id or ex.raw_email or ex.raw_name
                                if ex_ident == ident:
                                    found = True
                                    break
                            if not found:
                                await add_or_update_attendee(
                                    session,
                                    meeting_id=keeper.id,
                                    source=att.source,
                                    external_attendee_id=att.external_attendee_id,
                                    raw_email=att.raw_email,
                                    raw_phone=att.raw_phone,
                                    raw_name=att.raw_name,
                                    role=att.role,
                                )
                                changed = True
                        await session.delete(other)
                        merged_meetings += 1
                    # Identity resolution for attendees lacking person_id
                    unresolved = (await session.execute(select(MeetingAttendee).where(
                        MeetingAttendee.meeting_id == keeper.id,
                        MeetingAttendee.person_id == None  # noqa: E711
                    ))).scalars().all()
                    for att in unresolved:
                        try:
                            await resolve_attendee(session, keeper.coach_id, att)
                        except Exception:  # pragma: no cover
                            pass
                    if changed:
                        await session.flush()
                    merged_components += 1

                if merged_meetings:
                    await session.commit()
                return {
                    "scanned": scanned,
                    "merged_components": merged_components,
                    "merged_meetings": merged_meetings,
                    "status": "ok",
                }
            except Exception as e:  # pragma: no cover
                await session.rollback()
                logging.error("[reconcile_meetings] error=%s", e)
                return {"error": str(e), "scanned": scanned, "merged_components": merged_components, "merged_meetings": merged_meetings}
    return asyncio.run(_run())


@celery_app.task
def refresh_external_accounts():
    """Periodic refresh of expiring ExternalAccount tokens (providers supporting refresh)."""
    session = SessionLocal()
    try:
        now = datetime.datetime.utcnow().timestamp()
        accounts = session.query(ExternalAccount).filter(ExternalAccount.refresh_token_enc.isnot(None)).all()
        f = fernet()
        refreshed = 0
        for acc in accounts:
            if not acc.expires_at:
                continue
            expires_at_epoch = acc.expires_at.timestamp()
            if expires_at_epoch - now > 600:  # skip if >10m remaining
                continue
            try:
                refresh_token_plain = f.decrypt(acc.refresh_token_enc.encode()).decode()
                upd = refresh_if_needed(acc.provider, refresh_token_plain, int(expires_at_epoch))
                if upd:
                    acc.access_token_enc = f.encrypt(upd['access_token'].encode()).decode()
                    if upd.get('refresh_token') and upd['refresh_token'] != refresh_token_plain:
                        acc.refresh_token_enc = f.encrypt(upd['refresh_token'].encode()).decode()
                    import datetime as dt
                    acc.expires_at = dt.datetime.utcfromtimestamp(upd['expires_at']).replace(tzinfo=dt.timezone.utc)
                    if upd.get('scopes'):
                        acc.scopes = upd['scopes']
                    session.add(acc)
                    refreshed += 1
            except OAuthError as e:
                logging.warning("[OAuthRefresh] provider=%s account=%s failed: %s", acc.provider, acc.id, e)
            except Exception as e:  # pragma: no cover
                logging.error("[OAuthRefresh] unexpected error: %s", e)
        session.commit()
        return {"refreshed": refreshed}
    finally:
        session.close()

@celery_app.task
def summarize_missing_transcripts():
    session = SessionLocal()
    try:
        # Only select where summary IS NULL or summary is an empty object
        transcripts = session.query(Transcript).filter(
            or_(Transcript.summary == None, cast(Transcript.summary, Text) == '{}'),
            Transcript.full_text.isnot(None)
        ).all()
        logging.info(f"[Summarization] Found {len(transcripts)} transcripts to summarize.")
        for transcript in transcripts:
            try:
                summary = summarize_meeting(transcript.full_text)
                print (f"Final summary: {summary}")
                transcript.summary = summary
                transcript.action_items = (summary or {}).get("action_items", [])
                session.add(transcript)
                session.commit()
                logging.info(f"[Summarization] Transcript {transcript.id} summarized successfully.")
            except Exception as e:
                logging.error(f"[Summarization] Failed to summarize transcript {transcript.id}: {e}")
    finally:
        session.close()
    return {"status": "summarization complete"}


def refresh_google_token_for_user(user, session):
    access_token, refresh_token, expiry = user.get_google_tokens()
    refresh_threshold = datetime.timedelta(minutes=5)
    now = datetime.datetime.utcnow()
    if refresh_token and expiry and expiry < now + refresh_threshold:
        logging.info(f"[Google Token Refresh] Attempting refresh for user {user.email}")
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        try:
            resp = httpx.post(GOOGLE_TOKEN_URL, data=data, timeout=10.0)
            logging.info(f"[Google Token Refresh] Response status: {resp.status_code}")
            logging.info(f"[Google Token Refresh] Response body: {resp.text}")
            if resp.status_code == 200:
                tokens = resp.json()
                new_access_token = tokens["access_token"]
                expires_in = tokens.get("expires_in", 3600)
                new_expiry = now + datetime.timedelta(seconds=expires_in)
                user.set_google_tokens(new_access_token, refresh_token, new_expiry)
                session.add(user)
                session.commit()
                logging.info(f"[Google Token Refresh] Token refreshed for user {user.email}. New expiry: {new_expiry}")
            else:
                logging.error(f"[Google Token Refresh] Failed for user {user.email}: {resp.text}")
        except Exception as e:
            logging.error(f"[Google Token Refresh] Exception for user {user.email}: {e}")


@celery_app.task
def refresh_all_google_tokens():
    session = SessionLocal()
    try:
        users = session.query(User).filter(User.google_refresh_token_encrypted.isnot(None)).all()
        for user in users:
            refresh_google_token_for_user(user, session)
    finally:
        session.close()
    return {"status": "google token refresh complete"}


@celery_app.task(bind=True, ignore_result=False)
def sync_fireflies_meetings(self, user_email=None, api_key=None):
    session = SessionLocal()
    try:
        try:
            self.update_state(state="PROGRESS", meta={"step": "start"})
        except Exception:
            pass

        # Determine user set to process
        if user_email and api_key:
            users = session.query(User).filter(User.email == user_email, User.fireflies_api_key == api_key).all()
        else:
            users = session.query(User).filter(User.fireflies_api_key.isnot(None)).all()

        for user in users:
            try:
                meetings_data = fetch_fireflies_meetings_sync(user.email, user.fireflies_api_key, limit=50)
            except Exception as e:
                logging.error(f"Fireflies API error for user {user.email}: {e}")
                continue

            if isinstance(meetings_data, dict) and meetings_data.get('error'):
                logging.error(
                    f"Fireflies API returned error for user {user.email}: {meetings_data.get('error')} | Details: {meetings_data.get('details')}"
                )
                continue

            org_id = getattr(user, 'org_id', None)

            for m in meetings_data.get('meetings', []):
                # Parse meeting date robustly
                raw_date = m.get('date')
                if isinstance(raw_date, int):
                    # handle ms epoch
                    if raw_date > 1e12:
                        raw_date = raw_date // 1000
                    meeting_date = datetime.datetime.fromtimestamp(raw_date)
                elif isinstance(raw_date, str):
                    try:
                        meeting_date = datetime.datetime.fromisoformat(raw_date)
                    except Exception:
                        meeting_date = None
                else:
                    meeting_date = raw_date if isinstance(raw_date, datetime.datetime) else None

                meeting_id = m.get('id')
                if not meeting_id:
                    # skip invalid entries
                    continue

                participants = m.get('participants') or []
                first_participant_name = ''
                if participants and isinstance(participants, list):
                    first = participants[0]
                    if isinstance(first, dict):
                        first_participant_name = first.get('name', '')

                full_text = m.get('full_text') or ''
                title = m.get('title', '')
                duration = m.get('duration')
                source = m.get('source', 'fireflies')

                summary_obj = m.get('summary') or {}
                if not isinstance(summary_obj, dict):
                    summary_obj = {}
                action_items = summary_obj.get('action_items', [])

                # Idempotency: update or create Meeting and Transcript by meeting_id and user_id
                existing_meeting = session.query(Meeting).filter(Meeting.id == meeting_id, Meeting.user_id == user.id).one_or_none()
                if existing_meeting:
                    existing_meeting.client_name = first_participant_name
                    existing_meeting.title = title
                    existing_meeting.date = meeting_date
                    existing_meeting.duration = duration
                    existing_meeting.source = source
                    existing_meeting.transcript_id = meeting_id
                    if org_id is not None:
                        existing_meeting.org_id = org_id
                    session.merge(existing_meeting)
                else:
                    meeting = Meeting(
                        id=meeting_id,
                        user_id=user.id,
                        org_id=org_id,
                        client_name=first_participant_name,
                        title=title,
                        date=meeting_date,
                        duration=duration,
                        source=source,
                        transcript_id=meeting_id
                    )
                    session.add(meeting)

                existing_transcript = session.query(Transcript).filter(Transcript.id == meeting_id).one_or_none()
                if existing_transcript:
                    existing_transcript.summary = summary_obj
                    existing_transcript.action_items = action_items
                    existing_transcript.full_text = full_text
                    if org_id is not None:
                        existing_transcript.org_id = org_id
                    session.merge(existing_transcript)
                else:
                    transcript = Transcript(
                        id=meeting_id,
                        meeting_id=meeting_id,
                        org_id=org_id,
                        full_text=full_text,
                        summary=summary_obj,
                        action_items=action_items
                    )
                    session.add(transcript)
        session.commit()
        try:
            self.update_state(state="SUCCESS", meta={"status": "completed"})
        except Exception:
            pass
    finally:
        session.close()
    return {"status": "success"}
