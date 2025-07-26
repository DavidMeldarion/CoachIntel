# Backend (FastAPI + Celery)

This is the FastAPI backend for CoachSync, with Celery for background jobs (transcription, summarization).

## Features Scaffolded
- Dummy REST endpoints for:
  - Audio upload
  - Transcription trigger
  - Summarization trigger
  - Session/timeline fetch
- Celery worker setup (with Redis)
- PostgreSQL integration (SQLAlchemy, async)
- S3-compatible storage placeholder
- Email sending placeholder

## Getting Started

1. Create a virtualenv and install dependencies:
   ```sh
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the FastAPI server:
   ```sh
   uvicorn app.main:app --reload
   ```
3. Run the Celery worker:
   ```sh
   celery -A app.worker worker --loglevel=info
   ```

## Structure
- `/app` — FastAPI app, routers, models, tasks
- `/worker` — Celery tasks

## Env Vars
- See `../.env.example` for required variables

---

This is a placeholder. Actual implementation will follow after project scaffolding.
