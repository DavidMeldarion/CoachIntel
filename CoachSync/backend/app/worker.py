# Dummy Celery worker for CoachSync
from celery import Celery

celery_app = Celery(
    'worker',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@celery_app.task
def transcribe_audio_task(audio_path):
    # Dummy: Transcribe audio
    return f"Transcribed: {audio_path}"

@celery_app.task
def summarize_transcript_task(transcript):
    # Dummy: Summarize transcript
    return f"Summary: {transcript[:30]}..."
