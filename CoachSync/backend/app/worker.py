# Dummy Celery worker for CoachSync
from celery import Celery
import os

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

celery_app = Celery(
    'worker',
    broker=REDIS_URL,
    backend=REDIS_URL
)

@celery_app.task
def transcribe_audio_task(audio_path):
    # Dummy: Transcribe audio
    return f"Transcribed: {audio_path}"

@celery_app.task
def summarize_transcript_task(transcript):
    # Dummy: Summarize transcript
    return f"Summary: {transcript[:30]}..."
