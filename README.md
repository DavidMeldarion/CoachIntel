# CoachIntel

CoachIntel is a SaaS web app for personal trainers and fitness coaches to manage 1-on-1 client coaching with AI-powered call transcription, summarization, and workflow automation.

## Quick Start

1. **Setup**: See [SETUP.md](./SETUP.md) for detailed environment configuration
2. **Run**: `docker-compose up -d`
3. **Access**: Frontend at http://localhost:3000, Backend API at http://localhost:8000

## Monorepo Structure

- `/frontend` — Next.js (App Router) + Tailwind CSS UI
- `/backend` — FastAPI REST API, Celery (Redis), background jobs
- PostgreSQL (Docker), Redis (Docker), S3-compatible storage
- Auth: Google OAuth + JWT cookies
- Docker for local dev and deployment

## MVP Features
- Upload recorded coaching calls (audio)
- Automatic transcription (OpenAI Whisper/AssemblyAI)
- Summarize transcript (session summary, action items, progress notes)
- Email summary to coach
- Store transcript/summary in DB
- Timeline of client summaries
- Basic user auth
- Coach dashboard
- Scheduled email digests

## Getting Started

1. Clone the repo
2. See `/frontend/README.md` and `/backend/README.md` for service-specific setup
3. Use Docker Compose for local development (coming soon)

## Folder Structure

- `/frontend` — Next.js app
- `/backend` — FastAPI app, Celery worker, tasks, models
- `/shared` — (optional) shared types, utils
- `.env`, `.envrc` — environment config

## Development
- Each service can be run independently for development
- Use Docker for local orchestration

## Roadmap
- [ ] MVP endpoints and UI
- [ ] Docker Compose setup
- [ ] Production deployment (Railway/Render)

---

See each subfolder for more details.
