# Aethos — for Professional Services

An agent-first ERP for professional services firms. Drop your engagement letter, vendor invoice, or receipt into a chat — Aethos's AI agents extract, propose, and post; you approve. Engagement to paid invoice without forms.

This is a standalone product in the **Aethos** family, focused on professional services workflows. Companion product (product/inventory ERP) lives in the [`aethos`](https://github.com/venkateshbr/aethos) repository.

## What it does

- **Engagements & projects** — T&M, fixed-fee, retainer, milestone, capped, mixed
- **Time & expenses** — chat-driven entry; receipts auto-extracted
- **Multi-model invoicing** — Stripe Payment Links on every invoice, Stripe Connect for firm payouts
- **AP + initial bill payments** — vendor invoices extracted, posted, bill-pay batches with NACHA + universal CSV export
- **Full GAAP double-entry** under the hood
- **Chat-first agent UX** with HITL approval queue and per-agent autonomy levels
- **5 launch markets**: US · UK · Singapore · India · Australia (multi-currency, per-market tax seed, Stripe Tax)

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12+ · FastAPI · PydanticAI · Pydantic Graph · Procrastinate workers (Postgres-backed) |
| Frontend | Angular 19 · Tailwind · Angular Material (dark slate) |
| Data | Supabase (PostgreSQL 15+, RLS, Auth, Storage, Realtime) |
| Payments | Stripe (SaaS + Connect + Payment Links + Tax) |
| Email | Resend |
| LLM | Anthropic Claude Sonnet 4.6 + Langfuse traces |
| Deploy | Vercel (web) · Cloud Run (api + workers) · Supabase (queue lives in Postgres — no Redis) |

## Structure

```
backend/         FastAPI + PydanticAI
  app/
    api/v1/      Routers
    services/    Business logic
    agents/      PydanticAI agents + Pydantic Graph workflows
    models/      Pydantic schemas
    domain/      Money, enums, rules, journal patterns
    repositories/  Supabase data access
    events/      Domain events
    workers/     Procrastinate background workers (Postgres-backed queue)
    core/        Config, auth, RBAC
  supabase/migrations/
  tests/
frontend/        Angular 19
  src/app/
    core/        Services, guards, interceptors
    shared/      Reusable components (chat bubble, hitl card, money pipe)
    features/    Lazy-loaded modules (copilot, inbox, engagements, ...)
  src/assets/brand/    Logo + palette assets
shared/          Cross-stack schemas
infra/           Vercel / Cloud Run / Supabase deploy configs
docs/            Plan, ADRs, agent catalog
```

## Plan

See [`docs/PLAN.md`](docs/PLAN.md) — comprehensive product + execution plan.

## Local Runtime

Use Node 20 for the Angular workspace. The repo pins `.nvmrc` to Node 20.19.0 because Angular 19 rejects unsupported local runtimes such as Node 24.

```bash
nvm use
```

## Demo Readiness

Run a clean local demo check against an existing tenant:

```bash
DEMO_TENANT_ID=<tenant-uuid> make demo-ready
```

The target starts any missing local backend/frontend servers, runs
`backend/scripts/seed_demo.py --reset`, checks `/health`, `/api/v1/ping`, and
`/health/ready`, then runs the selected Playwright demo specs. Override specs
with:

```bash
DEMO_TENANT_ID=<tenant-uuid> \
DEMO_E2E_SPECS="e2e/demo-v2-meridian.spec.ts e2e/r2r-reports-render.spec.ts" \
make demo-ready
```

## Status

**Pre-execution.** Plan v3 approved (pending v4 update for brand + repo separation). Ship target: 6 weeks to public beta.
