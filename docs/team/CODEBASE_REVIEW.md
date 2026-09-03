# Aethos PS — Backend Codebase Review

> **Owner**: Karya (Backend Engineer)
> **Status**: Snapshot 2026-09-03 from the comprehensive review (issues #491–#528). Owner keeps the catalogs below current.

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

## Snapshot (2026-09-03)

- **Routers**: 40 mounted under `/api/v1` (`app/api/v1/router.py`). Missing vs PLAN §5.2: `suggestions/*` (#497), `POST /invoices/{id}/void` (#517), billing-run `review` step (#515).
- **Services**: 60+ modules; journals only via `domain/journal_helper.post_journal()`; HITL via `services/inbox_service.py`; Nous via `services/atlas_runtime.py` (+ `hermes_client.py`, `atlas_semantic_intent_router.py`, `atlas_deterministic_responses.py`, `atlas_read_packs.py`).
- **Agents** (`app/agents/`): engagement_letter, vendor_invoice, expense_extractor, reporting, intelligence call an LLM; invoice_drafter, collections, project_health, time_entry, revenue_recognition, bill_pay, accrual, fx_remeasurement, prepaid_amortization, recurring_journal, accounting_guardian are deterministic. `billing_run_agent` has an eval pack but no module (#515).
- **Repositories**: 14 modules; many services query Supabase directly.
- **Workers** (`app/workers/`): 11 registered tasks; `reconcile_sent_invoices` unscheduled (#493); no `wip_snapshot_worker` (#525).
- **DB**: 115 migrations (0001–0120, gaps 0023–0026, 0106); RLS on all tenant tables; `billing_runs` has no CREATE TABLE (#492); no BEFORE DELETE guard on posted journals (#504).
- **Quality**: `uv run pytest tests/unit tests/property` → 1,440 passed; ruff clean; zero TODO/FIXME in `app/`.
- **Known rule gaps**: period lock not pre-flighted on AR/AP paths (#500); webhook swallows handler errors (#493); autonomy loop inert (#496/#497); raw document binaries sent to the model (#498).

## Changelog

### [2026-05-19] — Skeleton created.
