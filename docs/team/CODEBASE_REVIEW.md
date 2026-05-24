# Aethos PS — Backend Codebase Review

> **Owner**: Karya (Backend Engineer)
> **Status**: Skeleton. Updated as the backend surface lands (PLAN §3, §5).

## Quality bar

- Python 3.12+, FastAPI 0.115+, Pydantic v2, PydanticAI, async/await.
- Router → Service → Repository pattern; no business logic in routers.
- `decimal.Decimal` for money; `NUMERIC(15,2)` in DB; strings in JSON.
- Tenant scoping in every query; `app.current_tenant_id` set before any Supabase query.
- PII masking via `mask_pii()` before any LLM call.
- Structured agent outputs (typed Pydantic).
- Graceful degradation if AI unavailable.
- Posted journals immutable; corrections via reversing entries.
- `ruff check` green.
- Package verification skill run before any new third-party import.

## Architecture (current snapshot)

To be filled when first feature ships:
- Service catalog (`app/services/`).
- Agent catalog (`app/agents/`) and their tool surface.
- Repository catalog (`app/repositories/`).
- Procrastinate worker catalog (`app/workers/`).
- DB trigger map (`supabase/migrations/`).

## Review triggers

- After any new FastAPI router, service, or agent.
- After any DB migration or schema change.
- After any change to `app/core/`, `app/domain/`, `app/agents/base.py`.
- Weekly: full backend health review on demand.

## Changelog

### [2026-05-19] — Skeleton created.
