import logging
import httpx
import datetime
import os
import ssl
from celery import Celery
from celery.schedules import crontab
from app.models import User, Meeting, Transcript, SessionLocal  # Use sync session
from app.integrations import fetch_fireflies_meetings_sync
from app.summarization import summarize_meeting
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URL
from sqlalchemy import or_, cast, Text

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

# If using TLS (Upstash rediss://), configure SSL
if REDIS_URL.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

celery_app.conf.result_expires = 3600  # 1 hour expiry for task results
celery_app.conf.update(
    result_serializer='json',
    task_serializer='json',
    accept_content=['json'],
    broker_connection_retry_on_startup=True,
    # Reduce health check frequency to cut Redis command volume
    broker_transport_options={
        "health_check_interval": 120
    },
    result_backend_transport_options={
        "retry_on_timeout": True,
        "health_check_interval": 120,
    },
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
)

# Prefer long-lived sockets and fewer health checks (helps with Upstash)
celery_app.conf.broker_transport_options = {
    **(celery_app.conf.broker_transport_options or {}),
    "health_check_interval": 300,
    "socket_keepalive": True,
    "socket_timeout": 300,
}
celery_app.conf.result_backend_transport_options = {
    **(celery_app.conf.result_backend_transport_options or {}),
    "health_check_interval": 300,
    "retry_on_timeout": True,
}

celery_app.conf.beat_schedule = {
    'sync-fireflies-meetings-hourly': {
        'task': 'worker.sync_fireflies_meetings',
        'schedule': crontab(minute=0, hour='*'),
        'args': ()
    },
    'refresh-google-tokens-every-10-minutes': {
        'task': 'worker.refresh_all_google_tokens',
        'schedule': crontab(minute='*/10'),
        'args': ()
    },
    # 'summarize-missing-transcripts-every-15-minutes': {
    #     'task': 'worker.summarize_missing_transcripts',
    #     'schedule': crontab(minute='*/15'),
    #     'args': ()
    # },
}

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
                transcript.action_items = summary.get("action_items", [])
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
    now = datetime.utcnow()
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

# @celery_app.task
# def transcribe_audio_task(audio_path):
#     # Dummy: Transcribe audio
#     return f"Transcribed: {audio_path}"

# @celery_app.task
# def summarize_transcript_task(transcript):
#     # Dummy: Summarize transcript
#     return f"Summary: {transcript[:30]}..."

@celery_app.task(bind=True, ignore_result=False)
def sync_fireflies_meetings(self, user_email=None, api_key=None):
    session = SessionLocal()
    try:
        self.update_state(state="PROGRESS", meta={"step": "start"})
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
            if 'error' in meetings_data:
                logging.error(f"Fireflies API returned error for user {user.email}: {meetings_data['error']} | Details: {meetings_data.get('details')}")
                continue
            for m in meetings_data.get('meetings', []):
                raw_date = m['date']
                if isinstance(raw_date, int):
                    if raw_date > 1e12:
                        raw_date = raw_date // 1000
                    meeting_date = datetime.datetime.fromtimestamp(raw_date)
                elif isinstance(raw_date, str):
                    try:
                        meeting_date = datetime.fromisoformat(raw_date)
                    except Exception:
                        meeting_date = None
                else:
                    meeting_date = raw_date
                meeting_id = m['id']
                # Use full_text from GraphQL response only
                full_text = m.get('full_text', '')
                # Idempotency: update or create Meeting and Transcript by meeting_id and user_id
                existing_meeting = session.query(Meeting).filter(Meeting.id == meeting_id, Meeting.user_id == user.id).one_or_none()
                if existing_meeting:
                    existing_meeting.client_name = m['participants'][0]['name'] if m['participants'] else ''
                    existing_meeting.title = m['title']
                    existing_meeting.date = meeting_date
                    existing_meeting.duration = m['duration']
                    existing_meeting.source = m['source']
                    existing_meeting.transcript_id = meeting_id
                    session.merge(existing_meeting)
                else:
                    meeting = Meeting(
                        id=meeting_id,
                        user_id=user.id,
                        client_name=m['participants'][0]['name'] if m['participants'] else '',
                        title=m['title'],
                        date=meeting_date,
                        duration=m['duration'],
                        source=m['source'],
                        transcript_id=meeting_id
                    )
                    session.add(meeting)
                existing_transcript = session.query(Transcript).filter(Transcript.id == meeting_id).one_or_none()
                if existing_transcript:
                    existing_transcript.summary = m['summary']
                    existing_transcript.action_items = m['summary'].get('action_items', [])
                    existing_transcript.full_text = full_text
                    session.merge(existing_transcript)
                else:
                    transcript = Transcript(
                        id=meeting_id,
                        meeting_id=meeting_id,
                        full_text=full_text,
                        summary=m['summary'],
                        action_items=m['summary'].get('action_items', [])
                    )
                    session.add(transcript)
        session.commit()
        self.update_state(state="SUCCESS", meta={"status": "completed"})
    finally:
        session.close()
    return {"status": "success"}
