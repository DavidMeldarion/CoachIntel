# CoachSync Monorepo Structure

- `/frontend` — Next.js (App Router) + Tailwind CSS
- `/backend` — FastAPI + Celery + Redis
- `.env.example` — Example environment variables
- `docker-compose.yml` — Local dev orchestration
- `.github/copilot-instructions.md` — Copilot custom instructions

---

## /frontend
- `app/` — App Router pages
- `components/` — UI components
- `lib/` — API helpers

## /backend
- `app/` — FastAPI app, routers, models
- `worker/` — Celery tasks

---

This file is for reference only. See each subfolder for more details.
