## CoachIntel Backend – AI Code Generation House Rules

Authoritative guardrails for any AI‐assisted code generation in this repository. Follow strictly. Reject or refactor outputs that violate these rules.

### 1. Stack & Versions
| Layer | Tech |
|-------|------|
| API | FastAPI (async) |
| ORM | SQLAlchemy 2.x (declarative, async session) |
| Schemas | Pydantic v2 |
| Migrations | Alembic |
| Tasks | Celery (Redis broker), result backend as configured |
| DB | PostgreSQL |
| Caching / Queue | Redis |
| Python | >= 3.11 |
| Testing | pytest, httpx AsyncClient, factory_boy |
| Lint/Format | ruff + black (run ruff --fix, then black) |
| Logging | structlog |
| Security | Fernet encryption for PII, hashed lookup columns |

### 2. Project Layout (Do NOT invent new top-level buckets)
```
app/
  api/        # FastAPI routers (thin controllers)
  db/         # Session, engine, base, repository helpers
  models/     # SQLAlchemy models only (no business logic side effects)
  schemas/    # Pydantic models (request/response/internal)
  services/   # Pure/business logic functions orchestrating repos
  tasks/      # Celery task definitions (idempotent)
  core/       # Settings, logging config, security utils
```
Keep routers small: parameter parsing, dependency injection, call service, return schema.

### 3. Coding Standards
1. Fully type‑hint all functions (inputs + return). Use `typing.Annotated` for dependency metadata where helpful.
2. No silent `# type: ignore` unless justified with a comment.
3. Prefer `collections.abc` types (`Sequence`, `Mapping`) over concrete lists/dicts in signatures when read-only.
4. Avoid circular imports; if needed, move shared types to a neutral module.
5. No `print()` – always structured logging via structlog.
6. Keep functions small (< ~40 LOC). Extract helpers.

### 4. Environment & Configuration
Use `pydantic-settings` settings object in `app/core/settings.py` (or equivalent). Load only from:
* Environment variables
* Secret manager / injected runtime secrets

Never hard‑code tokens, keys, URLs with secrets. Provide placeholders in docs, not code.

### 5. Data Modeling & PII
Emails and phone numbers: store BOTH
* Encrypted column (Fernet at rest) – decrypt only at service edge when needed.
* Deterministic hash column (e.g., SHA-256 with salt from settings) for equality lookups / uniqueness.

Do NOT index raw encrypted values; index the hash column. Never log raw PII. Mask in logs (e.g., local part truncated for email).

### 6. Repositories & Services Pattern
Repository (db layer):
* Pure CRUD + query composition (no business branching, no logging except error contexts).
* Accept an explicit `AsyncSession` (injected via dependency) – never create sessions ad hoc inside functions.

Service layer (`app/services`):
* Orchestrates repositories, applies business rules, handles idempotency, emits domain events (if any), schedules Celery tasks.
* Return Pydantic schema(s) or primitives. Do not return raw ORM instances directly to API layer.

### 7. API Layer (Routers)
* Input/Output strictly typed with Pydantic schemas.
* Dependency injection with `Depends` for: session, current user, settings, etc.
* No raw SQL or business logic here.
* All endpoints that mutate state must be idempotent or provide an idempotency key header (`Idempotency-Key`). If re‑run, they must yield the same persisted result (safe upsert / no duplicate side effects).

### 8. Idempotency Rules
Examples:
* Ingest/webhook handlers: Upsert by external provider unique id.
* Celery tasks: Guard with natural key or redis lock to prevent duplicate heavy work.
* Use `ON CONFLICT DO UPDATE` (SQLAlchemy ORM pattern via `insert().on_conflict_do_update`) where appropriate.
* Never assume at‑most‑once delivery from external systems.

### 9. Pydantic v2 Usage
* Use `model_config = ConfigDict(from_attributes=True)` for ORM reading DTOs.
* Separate: Create / Update / Read / Internal schemas. Do not overload one model for all.
* Use validators / field serializers sparingly; prefer explicit transformation functions in services.

### 10. Tasks (Celery)
* Task functions must be pure relative to inputs + database (no hidden global state).
* Always catch and log exceptions with structured context; let retries happen if configured.
* Idempotent: if re-executed, produce no duplicate side effects (enforce via natural key checks).

### 11. Logging (structlog)
* Use `logger = structlog.get_logger()`.
* Log events at boundaries: request receipt (middleware), service success/failure, external API calls (duration + status), task start/end.
* Include correlation / request ID (dependency inject). No multiline free‑form logs.

### 12. Security
* Never build SQL via string interpolation – always SQLAlchemy Core/ORM.
* Sanitize all external IDs before logging.
* Use parameterized external HTTP calls with explicit timeouts & retries (e.g., httpx client configured centrally).
* Enforce least privilege on DB roles (migration vs runtime).

### 13. Migrations (Alembic)
* All schema changes go through Alembic generated revisions (`alembic revision --autogenerate` then review & edit).
* Never manually mutate tables in runtime code to “fix” data structure.
* If data backfill required, embed in migration (careful with large tables: chunk & commit) or create a one-off script under `scripts/` with idempotent guards.
* Keep migrations deterministic: avoid `datetime.utcnow()` without seeding; store constants.

### 14. Encryption & Hashing Helpers
Centralize Fernet + hashing utilities in `app/core/security.py` (or similar). Services call helpers; models do NOT perform encryption automatically (avoid side effects during instantiation).

### 15. Testing
* Use pytest async tests with `pytest.mark.anyio` or `pytest.mark.asyncio`.
* HTTP layer tests: httpx `AsyncClient(app=fastapi_app, base_url="http://test")`.
* Factory layer: `factory_boy` for models; factories never perform external calls.
* Provide fixtures: db session (transactional rollback per test), settings override, redis mock, celery eager mode.
* Assert idempotency: call endpoints / tasks twice, ensure state unchanged / duplicates absent.
* 100% new/changed code path coverage for critical business functions (enforced in CI threshold—update if needed).

### 16. Performance & Concurrency
* Use `selectinload` / appropriate eager loading to prevent N+1.
* Batch external calls where possible.
* Add DB indexes when creating columns used in filters; reflect in migration.
* Avoid holding transactions open across network calls.

### 17. Dependency Injection Patterns
Provide dependencies for: `async_session`, `current_user`, `settings`, `logger`, `http_client`. Do not instantiate heavy resources per request.

### 18. Prohibited
* Hard‑coded secrets / API keys.
* Business logic in models or migrations (beyond data transforms required).
* Arbitrary `eval`/`exec`, raw SQL strings with concatenated user input.
* Printing, f-strings for logging without structlog context.
* Using synchronous DB or HTTP calls inside async endpoints.

### 19. PR / Generation Review Checklist
Before accepting AI‑generated changes, verify:
1. Types complete & mypy (if used) / Ruff clean.
2. No prints, only structlog.
3. Encryption & hashing applied for new PII fields.
4. Idempotency considered (repeat run test mentally / in code).
5. Migrations present & reviewed; no model drift.
6. Tests added/updated (factories, service tests, API tests) and pass.
7. No unauthorized new dependencies.
8. External calls have timeout + error handling.
9. Configuration via settings, not literals.
10. No internal layering violations (API importing repositories directly unless trivial pass‑through is justified).

### 20. Example Skeletons
Repository function:
```python
async def get_lead_by_external_id(session: AsyncSession, external_id: str) -> Lead | None:
	stmt = select(Lead).where(Lead.external_id == external_id)
	return await session.scalar(stmt)
```

Service function (idempotent upsert):
```python
async def ingest_lead(payload: LeadIngest, session: AsyncSession) -> LeadOut:
	existing = await get_lead_by_external_id(session, payload.external_id)
	if existing:
		existing.name = payload.name  # update mutable fields
		await session.flush()
		return LeadOut.model_validate(existing)
	lead = Lead(
		external_id=payload.external_id,
		name=payload.name,
		email_enc=encrypt_email(payload.email),
		email_hash=hash_email(payload.email),
	)
	session.add(lead)
	await session.flush()
	return LeadOut.model_validate(lead)
```

FastAPI router:
```python
@router.post('/ingest', response_model=LeadOut)
async def ingest_endpoint(data: LeadIngest, session: AsyncSession = Depends(get_session)):
	return await ingest_lead(data, session)
```

### 21. AI Prompting Guidance
When requesting AI code: include purpose, layer (repo/service/api), idempotency expectations, inputs/outputs, edge cases (empty, duplicate, transient failure), and PII handling requirements.

---
Violations: Reject / refactor before merge. This document is the contract for AI contributions.

