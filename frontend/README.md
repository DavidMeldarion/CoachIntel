# Frontend (Next.js)

This is the Next.js (App Router) + Tailwind CSS frontend for CoachIntel.

## Admin
- Admin route: `/admin/leads` (auth required)
- Env:
  - `NEXT_PUBLIC_API_URL` for direct backend access
- The app proxies requests from `/api/*` to the FastAPI server using server API routes and passes `x-user-email` from the NextAuth session.

## Endpoints used (backend)
- GET `/leads` with filters: `q,status,tag,date_from,date_to,limit,offset`
- GET `/leads/{id}`
- GET `/leads/{id}/events`
- POST `/leads/{id}/status`
- PATCH `/leads/{id}` (phone, tags)
- PATCH `/leads/{id}/notes`
- POST `/leads/export` (CSV)

### Mocking in dev
You can run the FastAPI backend locally or return dummy data from the Next.js API routes if needed.

## Features Scaffolded
- Dummy auth (Google Sign-In placeholder)
- Dashboard page
- Upload page (audio file upload form)
- Timeline page (list of past sessions)

## Getting Started

1. Install dependencies:
   ```sh
   npm install
   ```
2. Run the dev server:
   ```sh
   npm run dev
   ```

## Structure
- `/app` — App Router pages
- `/components` — UI components
- `/lib` — API helpers

## Env Vars
- See `../.env.example` for required variables

---

This is a placeholder. Actual implementation will follow after project scaffolding.
