import logging
import httpx
import datetime
import os
from celery import Celery
from celery.schedules import crontab
from app.models import User, Meeting, Transcript, SessionLocal  # Use sync session
from app.integrations import fetch_fireflies_meetings_sync
from app.summarization import summarize_meeting
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN_URL

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

celery_app = Celery(
    'worker',
    broker=REDIS_URL,
    backend=REDIS_URL
)

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
    'summarize-missing-transcripts-every-15-minutes': {
        'task': 'worker.summarize_missing_transcripts',
        'schedule': crontab(minute='*/15'),
        'args': ()
    },
}

@celery_app.task
def summarize_missing_transcripts():
    session = SessionLocal()
    try:
        transcripts = session.query(Transcript).filter((Transcript.summary == None) | (Transcript.summary == ""), Transcript.full_text.isnot(None)).all()
        for transcript in transcripts:
            try:
                result = summarize_meeting(transcript.full_text)
                transcript.summary = result.get("summary", "")
                transcript.action_items = result.get("action_items", [])
                transcript.progress_notes = result.get("progress_notes", "")
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

@celery_app.task
def sync_fireflies_meetings(user_email=None, api_key=None):
    session = SessionLocal()
    try:
        if user_email and api_key:
            users = session.query(User).filter(User.email == user_email, User.fireflies_api_key == api_key).all()
        else:
            users = session.query(User).filter(User.fireflies_api_key.isnot(None)).all()
        for user in users:
            try:
                meetings_data = fetch_fireflies_meetings_sync(user.email, user.fireflies_api_key, limit=50)
            except Exception as e:
                import logging
                logging.error(f"Fireflies API error for user {user.email}: {e}")
                continue
            if 'error' in meetings_data:
                import logging
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
                existing = session.query(Meeting).filter(Meeting.id == meeting_id, Meeting.user_id == user.id).one_or_none()
                if existing:
                    existing.client_name = m['participants'][0]['name'] if m['participants'] else ''
                    existing.title = m['title']
                    existing.date = meeting_date
                    existing.duration = m['duration']
                    existing.source = m['source']
                    existing.transcript_id = meeting_id
                    transcript_obj = session.query(Transcript).filter(Transcript.id == meeting_id).one_or_none()
                    if transcript_obj:
                        transcript_obj.summary = m['summary']
                        transcript_obj.action_items = m['summary'].get('action_items', [])
                        transcript_obj.full_text = full_text
                    else:
                        transcript = Transcript(
                            id=meeting_id,
                            meeting_id=meeting_id,
                            full_text=full_text,
                            summary=m['summary'],
                            action_items=m['summary'].get('action_items', [])
                        )
                        session.add(transcript)
                    continue
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
                transcript = Transcript(
                    id=meeting_id,
                    meeting_id=meeting_id,
                    full_text=full_text,
                    summary=m['summary'],
                    action_items=m['summary'].get('action_items', [])
                )
                session.add(transcript)
        session.commit()
    finally:
        session.close()
    return {"status": "success"}
