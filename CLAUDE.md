# Aethos — Professional Services ERP

## Project Overview
**Aethos for Professional Services** — an agent-first SaaS ERP for PS firms (consulting, advisory, agencies, dev shops, accounting/law firms). Chat is the primary surface; users drop documents (engagement letters, receipts, vendor invoices) and AI agents extract → propose → HITL approve → post. GAAP-compliant double-entry under the hood.

Standalone product in the Aethos family. Sister product (general ERP) lives at `~/dev/aethos`.

## 🚨 MANDATORY FIRST STEP — LOAD THE HARNESS, THEN READ THE PLAN

1. **Load the Agent Harness** in the order specified by [`agent-harness/adapters/claude/CLAUDE.md`](agent-harness/adapters/claude/CLAUDE.md). The harness is the model-neutral, project-agnostic source of truth for HOW we work — TDD discipline, agent evaluation, end-to-end workflows, contract testing, observability, security, quality gates.
2. **Read [`docs/PLAN.md`](docs/PLAN.md)** — source of truth for product scope, data model, agent catalog, HITL flow, Stripe integration, phasing, decisions log.
3. **Read [`docs/team/PROJECT_CONTEXT.md`](docs/team/PROJECT_CONTEXT.md)** — Aethos-specific project facts (stack, ports, conventions, markets).
4. **Read [`docs/team/SDLC_PROTOCOL.md`](docs/team/SDLC_PROTOCOL.md)** — the Aethos-specific overlay on the generic SDLC protocol.

Bring up any conflict with the plan to the Founder before writing code.

## Tech Stack
- **Backend**: Python 3.12+, FastAPI 0.115+, PydanticAI, Pydantic Graph, Pydantic v2, Procrastinate workers (Postgres-backed)
- **Frontend**: Angular 19, Tailwind, Angular Material (dark slate theme), NgRx Signals
- **Database**: Supabase (PostgreSQL 15+ with RLS), supabase-py / supabase-js
- **LLM**: Anthropic Claude Sonnet 4.6 + Langfuse traces (+ Pydantic Logfire)
- **Payments**: Stripe — SaaS subscriptions + Stripe Connect (Standard) + Payment Links + Stripe Tax
- **Email**: Resend
- **Cache / queue**: None — queue lives in Supabase Postgres via Procrastinate
- **Deploy**: Vercel (frontend) · Cloud Run (api + workers) · Supabase managed

## Launch Markets (day 1)
US · UK · Singapore · India · Australia. Multi-currency (USD/GBP/SGD/INR/AUD), per-market tax seed, Stripe Connect available in all 5.

## Architecture
```
backend/app/
  api/v1/        FastAPI routers (thin, no business logic)
  services/      Business logic, accounting rules
  agents/        PydanticAI agents (chat orchestrator + specialists)
  agents/graphs/ Pydantic Graph FSM workflows
  models/        Pydantic request/response schemas
  domain/        Money, enums, validation rules, journal patterns
  repositories/  Supabase data access
  events/        Domain event bus + handlers
  workers/       Procrastinate background workers (extraction, billing-run, collections, fx, autonomy-promoter)
  core/          Config, auth, RBAC, middleware
frontend/src/app/
  features/      Lazy-loaded modules (copilot, inbox, engagements, projects, clients, invoices, billing-runs, expenses, time-entries, payments, reports, people, onboarding, settings)
  shared/        Reusable components
  core/          Singleton services, guards, interceptors
```

## Critical Rules
- ALL monetary values use Python `decimal.Decimal`, NEVER `float`. DB type: `NUMERIC(15,2)`.
- API money fields serialize as **strings** in JSON.
- Every financial transaction generates **balanced** journal entries (debits = credits ± 0.01).
- Posted transactions are **immutable** — corrections via reversing entries only.
- All tables have `tenant_id` with RLS; every query is tenant-scoped.
- Period lock enforced at API layer — reject any transaction in a locked period.
- Multi-currency: `journal_lines` store both `amount` (foreign) and `base_amount` (tenant base, FX-converted).
- Agent outputs use PydanticAI typed structured outputs.
- Agents **never block** core ERP functions — graceful degradation if AI unavailable.
- Default agent autonomy is **L2 (suggest)** — auto-promotion to L3 only after confidence + correction-rate thresholds met AND admin approves (see PLAN §6.5).
- Never send raw PII (bank account numbers, tax IDs, full card numbers) to external LLM APIs — mask first.

## SDLC Protocol
- **GitHub Issues** in this repo is the single source of truth for work.
- **All work routes through Vishwa (CPTO)** — no code without an issue.
- **95% confidence rule**: agents do not modify code until ≥ 95% confident; ask clarifying questions until that bar is met.
- **Approval gates**: Vishwa seeks Founder approval before plans; all other agents seek Vishwa approval before execution.
- Lifecycle: `triage → assigned → in-progress → in-qa → in-review → CLOSED`
- **Closure evidence bar** (added 2026-05-26 after #128 RCA — see `docs/team/SDLC_PROTOCOL.md`): UI-touching issues require a passing Playwright spec under `frontend/e2e/` OR a Founder-confirmed browser walkthrough with screenshot. Backend `curl`/`httpx` proof is **not sufficient** for any UI-touching issue — it bypasses the SPA interceptor, routing, and error handling. Backend-only issues still close on real-stack pytest evidence. Applies to Vishwa-during-cap-strike closures too.
- Role-gated issue creation: only Vishwa, Vastu, Netra create `type:feature`. Others create `type:bug`/`task`/`chore`/`spike`.

## Agent skills

### Issue tracker

Work is tracked in GitHub Issues for `venkateshbr/aethos-ps`; use the repository's `gh` workflow. See `docs/agents/issue-tracker.md`.

### Triage labels

Engineering skills map their generic triage states onto this repository's existing `status:*`, assignment, and disposition labels. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context professional-services ERP; use the project context, plan, domain pack, and relevant ADRs/scenario documents. See `docs/agents/domain.md`.

## Agent Team
| Agent | Role | Trigger |
|---|---|---|
| **Vishwa** | CPTO — default orchestrator | Any unaddressed request |
| **Vastu** | Chief Architect | System design, ADRs |
| **Netra** | PM | PRDs, user stories, design-partner outreach |
| **Chitra** | Frontend Design Lead | UI/UX, brand lockup, component specs |
| **Rupa** | UI Engineer | Angular components, NgRx, Tailwind |
| **Karya** | Backend Engineer | FastAPI, services, agents, migrations |
| **Aksha** | SDET | Test plans, pytest, Playwright, agent evals |
| **Sthira** | SRE | Supabase, Cloud Run, Vercel, observability |
| **Prahari** | Security | Auth, Stripe, RLS, agent tools, webhooks |
| **Dhruva** | Data & Analytics | Agent performance, Langfuse, prompt refinement |

## Commands
*(populated as the codebase grows — see PLAN §13 for phasing)*

```
# Backend
cd backend && uv run uvicorn app.main:app --reload --port 8011
cd backend && uv run pytest
cd backend && uv run ruff check .

# Frontend
cd frontend && ng serve --port 4201
cd frontend && ng test
cd frontend && ng lint

# Workers
cd backend && uv run python -m procrastinate --app=app.workers.procrastinate_app.app worker

# E2E (Playwright) — run from repo root
make e2e                      # headless, chromium only (default local ports)
make e2e-headed               # headed with slow-mo for local debugging

# Override target URLs if needed:
# AETHOS_PS_WEB_URL=http://staging.example.com make e2e
```

Environment variables for e2e specs:
| Variable | Default | Purpose |
|---|---|---|
| `AETHOS_PS_WEB_URL` | `http://localhost:4201` | Angular frontend URL |
| `AETHOS_PS_API_URL` | `http://localhost:8011` | FastAPI backend URL |
| `AETHOS_TS_WEB_URL` | `http://localhost:4202` | Timesheets frontend URL |

*(Ports 8011 / 4201 chosen to avoid collision with aethos erpcore's 8010 / 4200.)*

## Key Patterns
- Service layer: Router → Service → Repository. Agents live within Services, never called from Routers.
- Every sub-ledger event (invoice, payment, bill, project_expense) auto-generates GL journals via **PostgreSQL triggers** — do not duplicate in Python.
- PydanticAI agents use `deps_type=AgentDeps` for tenant-scoped DB access.
- Chat orchestrator = Pydantic Graph router → specialist agents.
- HITL pattern: `agent_suggestions` (immutable AI output) + `hitl_tasks` (human work queue).

## Gotchas
- Supabase RLS requires setting `app.current_tenant_id` session var before queries.
- Invoice/bill numbers via DB sequences (RPC) — never generate in app code.
- The `accounting_guardian` agent runs at L3 always and **cannot** be disabled.
- Angular uses dark slate theme — all components conform.
- Agent corrections logged for future training; surfaced to Dhruva weekly.
- FX rates may be stale on weekends — `fx_refresh_worker` runs daily; agents warn if rate > 3 days old.
- Stripe Connect onboarding is OPTIONAL at signup — tenants without it can still use the app, just no payment links on invoices.
