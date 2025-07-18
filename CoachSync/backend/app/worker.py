# Dummy Celery worker for CoachSync
from celery import Celery
import os
from app.models import User, Meeting, Transcript
from app.integrations import fetch_fireflies_meetings
from app.main import AsyncSessionLocal
import asyncio
from sqlalchemy import select
import datetime

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

celery_app = Celery(
    'worker',
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.beat_schedule = {
    'sync-fireflies-meetings-every-5-minutes': {
        'task': 'worker.sync_fireflies_meetings',
        'schedule': 300.0,  # every 5 minutes
    },
}

@celery_app.task
def transcribe_audio_task(audio_path):
    # Dummy: Transcribe audio
    return f"Transcribed: {audio_path}"

@celery_app.task
def summarize_transcript_task(transcript):
    # Dummy: Summarize transcript
    return f"Summary: {transcript[:30]}..."

@celery_app.task
def sync_fireflies_meetings():
    async def run():
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.fireflies_api_key.isnot(None)))
            users = result.scalars().all()
            for user in users:
                meetings_data = await fetch_fireflies_meetings(user.email, user.fireflies_api_key, limit=50)
                for m in meetings_data.get('meetings', []):
                    # Convert Fireflies timestamp to datetime
                    raw_date = m['date']
                    if isinstance(raw_date, int):
                        # If milliseconds, convert to seconds
                        if raw_date > 1e12:
                            raw_date = raw_date // 1000
                        meeting_date = datetime.datetime.fromtimestamp(raw_date)
                    elif isinstance(raw_date, str):
                        try:
                            meeting_date = datetime.datetime.fromisoformat(raw_date)
                        except Exception:
                            meeting_date = None
                    else:
                        meeting_date = raw_date
                    # Check if meeting already exists
                    existing = await session.execute(select(Meeting).where(Meeting.id == m['id']))
                    if existing.scalar_one_or_none():
                        continue
                    meeting = Meeting(
                        id=m['id'],
                        user_id=user.id,
                        client_name=m['participants'][0]['name'] if m['participants'] else '',
                        title=m['title'],
                        date=meeting_date,
                        duration=m['duration'],
                        source=m['source'],
                        transcript_id=m['id']
                    )
                    session.add(meeting)
                    transcript = Transcript(
                        id=m['id'],
                        meeting_id=m['id'],
                        full_text='',  # Optionally fetch full transcript
                        summary=m['summary'],
                        action_items=m['summary'].get('action_items', [])
                    )
                    session.add(transcript)
            await session.commit()
    asyncio.run(run())
