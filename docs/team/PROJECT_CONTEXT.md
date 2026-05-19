# Aethos PS — Project Context

> **Filled from `docs/PLAN.md`. When in doubt, the plan wins.**
> Keep this document load-bearing for agents — repository, stack, conventions, ports, markets, security boundaries.

## Project

- **Name**: Aethos — for Professional Services (`aethos-ps`)
- **Tagline**: "Aethos, for professional services"
- **Repository**: TBD — `venkateshbr/aethos-ps` (or chosen name); founder to confirm
- **Sister product (general ERP)**: `~/dev/aethos` (separate repo, copy-then-adapt sharing, no symlinks)
- **Plan**: [`docs/PLAN.md`](../PLAN.md) — comprehensive product + execution plan; v4 draft pending founder approval

## Launch markets (day 1)

US · UK · Singapore · India · Australia. English-only support, async-only SLA v1. Multi-currency (USD/GBP/SGD/INR/AUD). Per-market tax seed. Stripe Connect Standard in all 5.

## Stack

| Layer | Tech | Version |
| --- | --- | --- |
| Backend | Python · FastAPI · PydanticAI · Pydantic Graph · Pydantic v2 · ARQ workers | Python 3.12+, FastAPI 0.115+ |
| Frontend | Angular 19 · Tailwind v3 · Angular Material (dark slate theme) · NgRx Signals | Angular 19 |
| Database | Supabase (PostgreSQL 15+ with RLS, Auth, Storage, Realtime) | PG 15+ |
| LLM | Anthropic Claude Sonnet 4.6 (default); Opus reserved for reasoning-heavy tasks | — |
| LLM observability | Langfuse (traces, scores, prompt versioning) + Pydantic Logfire | — |
| Payments | Stripe — SaaS subscriptions + Stripe Connect (Standard) + Payment Links + Stripe Tax | — |
| Email | Resend | — |
| Cache / queue | Upstash Redis | — |
| Deploy | Vercel (frontend) · Cloud Run (api + workers) · Supabase managed | — |

## Ports (dev, non-colliding with sister product)

- Backend: `8011`
- Frontend: `4201`

## Repository Layout

```
backend/app/
  api/v1/        FastAPI routers (thin)
  services/      Business logic, accounting rules
  agents/        PydanticAI agents
    graphs/      Pydantic Graph FSM workflows
  models/        Pydantic request/response schemas
  domain/        Money, enums, validation rules, journal patterns
  repositories/  Supabase data access
  events/        Domain event bus + handlers
  workers/       ARQ background workers
  core/          Config, auth, RBAC, middleware
frontend/src/app/
  features/      Lazy-loaded modules (copilot, inbox, engagements, projects, clients, invoices, ...)
  shared/        Reusable components
  core/          Singleton services, guards, interceptors
shared/schemas/  Cross-stack schemas (OpenAPI artifacts)
infra/
  vercel/        Frontend deploy
  cloudrun/      Backend + worker deploy
  supabase/      Supabase project config
docs/
  PLAN.md
  team/          Team artifacts (this folder)
  test/          Scenario documents + agent eval packs
  adr/           Architecture Decision Records
domain_packs/
  professional-services/pack.yaml
agent-harness/   Mirrored generic harness (canonical source ~/dev/agent-harness)
.claude/agents/  Aethos agent definitions (one .md per role)
```

## Critical Rules

- All monetary values use Python `decimal.Decimal`, never `float`. DB type: `NUMERIC(15,2)`.
- API money fields serialize as **strings** in JSON.
- Every financial transaction generates **balanced** journal entries (debits = credits ± 0.01 for FX residuals, otherwise 0).
- Posted transactions are **immutable** — corrections via reversing entries only.
- All tables have `tenant_id` with RLS; every query is tenant-scoped at the app layer **and** RLS-enforced.
- Period lock enforced at API layer — reject any transaction in a locked period.
- Multi-currency: `journal_lines` store both `amount` (foreign) and `base_amount` (tenant base, FX-converted at post time, never recomputed).
- Agent outputs use PydanticAI typed structured outputs.
- Agents **never block** core ERP functions — graceful degradation if AI unavailable.
- Default agent autonomy is **L2 (suggest)**; auto-promotion to L3 only after confidence + correction-rate thresholds met AND admin approves (see PLAN §6.5).
- Never send raw PII (bank account numbers, tax IDs, full card numbers) to external LLM APIs — `mask_pii()` first.

## SDLC Protocol

- **GitHub Issues** in this repo is the single source of truth for work.
- All work routes through Vishwa (CPTO) — no code without an issue.
- 95% confidence rule: agents do not modify code until ≥ 95% confident.
- Approval gates: Vishwa seeks founder approval before plans; all other agents seek Vishwa's approval before execution.
- Lifecycle: `status:triage → assigned → in-progress → in-qa → in-review → CLOSED`.
- Role-gated issue creation: only Vishwa, Vastu, Netra create `type:feature`.

## Harness Adoption

This project follows the Agent Harness (mirrored at `agent-harness/`). Load order per the agent's adapter — see `agent-harness/adapters/claude/CLAUDE.md` etc.

Key documents agents must read:

1. `agent-harness/core/operating-principles.md`
2. `agent-harness/core/sdlc-protocol.md`
3. `agent-harness/core/roles.yaml`
4. `agent-harness/core/tdd-protocol.md`
5. `agent-harness/core/testing-standard.md`
6. `agent-harness/core/quality-gates.md`
7. `agent-harness/core/e2e-workflow-standard.md`
8. `agent-harness/core/agent-eval-standard.md`
9. `agent-harness/core/contract-testing.md`
10. `agent-harness/core/observability-standard.md`
11. `agent-harness/core/security-review.md`
12. `agent-harness/core/saas-onboarding-payments.md` (for signup / billing / webhook work)
13. This document (`docs/team/PROJECT_CONTEXT.md`)
14. `domain_packs/professional-services/pack.yaml`
15. The relevant scenario document at `docs/test/e2e_<workflow>.md`

## Testing Tools (project picks)

| Layer | Tool |
| --- | --- |
| Backend unit / integration | `pytest` + `pytest-asyncio` |
| Backend property | `hypothesis` |
| Backend API e2e | `pytest` + `httpx` against running API on `:8011` |
| Frontend unit | Jasmine / Karma (Angular default) |
| Frontend e2e | **Playwright** (single-session login, role-based locators, `--headed --slow-mo=300` locally, headless in CI) |
| Agent evals | PydanticAI Evals; eval packs at `docs/test/agent_evals/<agent>.yaml`; results in Langfuse |
| LLM observability | Langfuse (primary) + Pydantic Logfire (dev/local) |
| Contract | JSON Schema diff on `shared/schemas/`; Pact for Copilot ↔ Backend (v1.x, not v1) |
| Load | Locust |

## LLM Cost & Budget

- Per-tenant token budget enforced by middleware.
- Default model: Claude Sonnet 4.6 (not Opus) for extraction agents.
- Cache extraction by document `sha256`.
- Langfuse alerts on per-tenant spend > $X/day.

## Security-Sensitive Areas

Every change touching these triggers Prahari review:

- `backend/app/core/auth*`, `backend/app/core/rbac*`, JWT/session handling
- `backend/app/api/v1/webhooks/*`, especially Stripe and Resend
- `backend/app/services/billing/*`, `backend/app/services/payments/*`
- `backend/app/services/agents/*` tools that write data
- `supabase/migrations/*` if RLS policies change
- `frontend/src/app/core/interceptors/*`, `frontend/src/app/core/guards/*`
- `.env.example`, secret-management code
- Any new external integration (model providers, banks, OAuth)

## Demo Data Discipline

- Test/demo tenant prefix: `test-tenant-<run_id>`.
- Test invoice prefix: `INV-TEST-<seq>`.
- All demo data deletable through admin UI (and a documented script for sweep-clean in CI).
- No real PII or real customer data in seed sets.

## Brand

- Parent brand "Aethos" with services-specific lockup.
- Linear-style minimalism. Dark slate (slate-900/800/700) base palette.
- Brand assets in `frontend/src/assets/brand/`.
