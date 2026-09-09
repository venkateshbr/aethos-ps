# Aethos PS — Backend instructions (Karya / Aksha / Prahari / Sthira)

Read the root [`CLAUDE.md`](../CLAUDE.md) first. This file is the backend-specific overlay referenced by `docs/team/SDLC_PROTOCOL.md`.

## Stack (as built)
- Python 3.12, FastAPI, Pydantic v2, `supabase-py`, Procrastinate (Postgres queue), PyJWT (ADR 0002), Stripe SDK, Resend, Langfuse, `openai` SDK against OpenRouter. **No PydanticAI / Pydantic Graph.**
- Nous runtime: `app/services/atlas_runtime.py` builds either `CopilotAgent` (`app/agents/copilot/graph.py`, `ATLAS_AI_RUNTIME=aethos_basic`) or `HermesClient` (`app/services/hermes_client.py`, `hermes_agent`, with circuit breaker + fallback). Before the model runs: `atlas_semantic_intent_router.py` → `atlas_deterministic_responses.py` / `atlas_read_packs.py`. Hermes calls back into `/api/v1/atlas-tools` (HMAC bearer, `aethos_hermes_tool_token`).

## Layout
```
app/api/v1/endpoints/  thin routers (auth deps only; no business logic)
app/services/          business logic; inbox_service = HITL materialisers; *_read_service = Nous read packs
app/repositories/      Supabase access (many services still query directly — prefer repos for new code)
app/domain/            money.py (Decimal), journal_helper.post_journal (ONLY journal writer), pii.py, fx.py, bank_routing.py
app/agents/            extraction/drafting/close agents, tool_registry.py (risk classes), suggestion_writer.py (→ agent_suggestions + hitl_tasks)
app/workers/           Procrastinate tasks; register in procrastinate_app.py import_paths; periodic via @app.periodic
app/core/              config.py (pydantic-settings), auth.py (JWT), tenant.py (membership check), rbac.py, permissions.py, rate_limit.py
app/evals/             offline eval gate (golden prompts + rubric) — CI runs scripts/agent_eval_gate.py
supabase/migrations/   0001–0120; every tenant table has RLS; policies use is_tenant_member()
```

## Non-negotiable rules
- Money: `Decimal` only; API money fields are strings; `NUMERIC(15,2)` in DB.
- Journals: never insert into `journal_entries`/`journal_lines` directly — call `post_journal()` (guardian + atomic RPC). Never UPDATE/DELETE posted journals; reverse instead.
- Period lock: call `period_lock_service.assert_period_open()` at the top of any service method dated into an accounting period (see #500 for the paths still missing it).
- Tenant scoping: every query `.eq("tenant_id", tenant_id)` even under the service-role client (RLS is bypassed there).
- Invoice/bill numbers: DB triggers (`fn_next_invoice_number`, `fn_next_bill_number`); never assign in Python.
- Agents: proposals go through `suggestion_writer.write_agent_suggestion()`; autonomy level must come from `agent_tool_policy`, not a literal (#497); mask text with `domain/pii.mask_pii` before any model call.
- Stripe: verify signatures before any mutation; pass `idempotency_key` on writes (#502); never acknowledge a webhook whose handler failed (#493).
- Security-sensitive paths (auth, tenant, webhooks, billing, agent tools, RLS migrations) require Prahari review.

## Commands
```bash
uv run uvicorn app.main:app --reload --port 8011
uv run pytest tests/unit tests/property -q        # CI set, no DB
uv run ruff check .
set -a && source ../.env && set +a && uv run pytest tests/api -q   # real stack on :8011
uv run python -m scripts.agent_eval_gate           # offline eval gate
uv run python -m procrastinate --app=app.workers.procrastinate_app.app worker
uv run python -m scripts.apply_migrations          # apply migrations (see header)
```

## Tests
See [`tests/README.md`](tests/README.md). Contract tests for every router live in `tests/unit/test_*_api_contract.py`; add one when adding an endpoint. Real-stack evidence (`tests/api`) is required to close backend issues.

## Gotchas
- PostgREST `is` accepts only null/true/false — use `.neq("status", "pending")`, never `.not_.is_(...)` (see #395/#496).
- `CurrentUser` has `user_id`, not `id` (#501).
- `billing_runs` CREATE TABLE lives in migration `0122_billing_runs_table.sql` (#492, applied to production 2026-09-03); `tests/unit/test_migration_chain_contract.py` guards the chain.
- Queue names published by the app must match the worker's `--queues` list (see `docs/qa/queue-session-budget-runbook.md`).
