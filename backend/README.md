# Backend (FastAPI + Celery)

This is the FastAPI backend for CoachIntel, with Celery for background jobs (transcription, summarization).

## Leads (Internal CRM)
New endpoints under the `/leads` prefix (auth required via NextAuth session header `x-user-email`).

- GET `/leads` — list with filters and pagination
  - Query: `q`, `status`, `tag`, `date_from`, `date_to`, `limit` (default 50), `offset` (default 0)
  - Response: `{ items, total, limit, offset }`
- GET `/leads/{id}` — lead detail with latest consents (email/sms) and notes
- GET `/leads/{id}/events` — message events ordered by `occurred_at desc`
- PATCH `/leads/{id}` — partial update for `tags` and `phone` only
- PATCH `/leads/{id}/notes` — update notes (existing route)
- POST `/leads/{id}/status` — update status: `waitlist|invited|converted|lost` (existing route)
- POST `/leads/export` — CSV export (text/csv). Body filters mirror GET `/leads`.

CSV columns: `id,created_at,status,first_name,last_name,email,phone,tags,source,utm_source,utm_medium,utm_campaign,last_contacted_at`

### Performance & Indexing
Ensure DB indexes:
- leads: `(org_id)`, `(org_id, created_at)`, `(status)`, `(created_at)`
- message_events: `(lead_id, occurred_at)`
- Optional: trigram index on `email, first_name, last_name` for faster ILIKE on large datasets.

## Frontend integration
- Admin route: `/admin/leads`
- Env: `NEXT_PUBLIC_API_URL` used by frontend proxy helpers
- API calls flow through Next.js API routes, which forward `x-user-email` to authenticate.

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
