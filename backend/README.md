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

### Middleware / Security Additions

Added request middlewares:

1. Payload size limiter (default 1MB) rejects POST/PUT/PATCH bodies over `MAX_REQUEST_BYTES` (env, default 1048576) with HTTP 413.
2. Provider webhook secret enforcement for `/webhooks/{provider}` paths (calendly, zoom, fireflies):
   - Set `CALENDLY_PROVIDER_SECRET`, `ZOOM_PROVIDER_SECRET`, `FIREFLIES_PROVIDER_SECRET`.
   - Header name configurable via `PROVIDER_WEBHOOK_HEADER` (default `X-Webhook-Secret`).
   - Toggle requirement with `REQUIRE_PROVIDER_WEBHOOK_SECRET` (default `true`). If a given provider's secret var is unset, the request is allowed but a warning is logged.

Related existing HMAC signature headers (e.g. provider native signatures) still apply; this is an additional shared layer.

### Testing

Run middleware tests:
```sh
pytest -q backend/tests/test_middleware.py
```
Tests cover:
- 413 on oversized payload
- 401 on missing / bad webhook secret
- Passing with correct secret per provider
 
### Structured Logging

We use `structlog` with JSON output. Automatic fields:
- `timestamp` ISO UTC
- `level`
- `event` (message key)
- `request_id` (per request middleware; also echoed as `X-Request-Id` header)
- `coach_id` (set when available via `set_log_coach` helper)
- `provider` (for webhook paths)

Helper emitters (in `app.main`):
- `log_webhook_received(provider, status, detail=None, **extra)`
- `log_meeting_upserted(meeting_id, coach_id, source, created, **extra)`
- `log_attendee_resolved(raw_email, person_id, matched, **extra)`
- `log_tokens_refreshed(coach_id, provider, success, rotated=None, **extra)`

Bind coach context if you have a `User` object:
```python
from app.main import set_log_coach
set_log_coach(user.id)
```
All logs are single-line JSON, suitable for ingestion (e.g., Loki, Datadog).
 
### Demo Seed Data

For local inspection or manual testing of meeting tracking + identity resolution you can seed a small demo dataset.

Creates:
- Coach user: `demo_coach@example.com` (plan `plus`)
- Two persons & clients:
   - Email-only person: `alice.client@example.com`
   - Phone-only person: `+15551234567`
- One meeting (Google) with `external_refs.google_event_id = demo-google-event-1`
- Two attendees (one email-only, one phone-only) resolved to the above persons

Run (from `backend/`):
```sh
python -m scripts.seed_demo_data
```

Idempotent: Each run removes any prior demo meeting and associated demo clients; demo persons are removed only if they are not referenced elsewhere. To force deletion of the persons even if referenced (hard reset), set:
```sh
DEMO_SEED_FORCE_WIPE=1 python -m scripts.seed_demo_data
```

You can adjust constants (emails, phone, event id) inside `scripts/seed_demo_data.py` if you need different sample values.

