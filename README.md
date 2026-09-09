# Aethos — for Professional Services

An agent-first ERP for professional services firms. Aethos Nous can extract and
propose work from engagement letters, vendor invoices, receipts, and business
prompts; operators review controlled actions in Inbox and complete the workflow
in the ERP modules.

This is a standalone product in the **Aethos** family, focused on professional services workflows. Companion product (product/inventory ERP) lives in the [`aethos`](https://github.com/venkateshbr/aethos) repository.

## What it does

- **Engagements & projects** — T&M, fixed-fee, retainer, milestone, capped, mixed
- **Time & expenses** — chat-driven entry; receipts auto-extracted
- **Multi-model invoicing** — Stripe Payment Links when server-side Stripe is configured; Connect optionally routes firm payouts. Without Stripe, "send" only marks the invoice sent and operators record receipts manually; client email delivery and PDF rendering are tracked in #516
- **AP + initial bill payments** — vendor invoice review plus guarded bill-pay batches and offline NACHA/universal CSV export; bank submission remains out of band
- **Double-entry accounting controls** — balanced journals, period locks, close workflows, and financial statements
- **Chat-first agent UX** with HITL approval queue and per-agent autonomy levels
- **5 configured market profiles**: US · UK · Singapore · India · Australia (base currency and per-market tax seed)

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12+ · FastAPI · Pydantic v2 · OpenAI-compatible agent loops (no PydanticAI) · Procrastinate workers (Postgres-backed) |
| Frontend | Angular 20 · Tailwind · Angular Material (dark slate) · separate timesheet portal app |
| Data | Supabase (PostgreSQL 15+, RLS, Auth, Storage, Realtime) |
| Payments | Stripe (SaaS + Connect + Payment Links + Tax) |
| Email | Resend |
| LLM | Configurable Nous runtime through Hermes or Aethos Basic/OpenRouter · Langfuse observability |
| Deploy | Hostinger VPS · Docker Compose · Traefik TLS edge · nginx web/timesheet proxies · private FastAPI, worker, and optional Hermes containers · Supabase |

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
frontend/        Angular 20 (plus projects/timesheet portal)
  src/app/
    core/        Services, guards, interceptors
    shared/      Reusable components (chat bubble, hitl card, money pipe)
    features/    Lazy-loaded modules (copilot, inbox, engagements, ...)
  src/assets/brand/    Logo + palette assets
shared/          Cross-stack schemas
infra/           Hostinger production compose is at repo root; infra/vercel and infra/cloudrun are unused legacy
integrations/hermes/  Hermes (Nous advanced runtime) profile and skills
docs/            Plan, ADRs, agent catalog
```

## Plan

See [`docs/PLAN.md`](docs/PLAN.md) — comprehensive product + execution plan.

## User And QA Guides

- `/app/guides` in the web app — searchable HTML library generated from the maintained Markdown sources below. **Owner/admin only** (`adminGuard`): the library includes the Nous runtime and learning-operations manual, which covers secret rotation and open security gaps. The old public `/guides` path redirects there.
- [`docs/user-guide/platform-user-guide.md`](docs/user-guide/platform-user-guide.md) — user-facing guide to the full platform and operating model.
- [`docs/copilot/prompt-library.md`](docs/copilot/prompt-library.md) — user-facing Nous prompt examples.
- [`docs/infra/HERMES_RUNTIME_OPERATIONS.md`](docs/infra/HERMES_RUNTIME_OPERATIONS.md) — Nous runtime (Hermes) configuration, verification, and the state of the self-learning loop.
- [`docs/qa/enterprise-e2e-scenario-library.md`](docs/qa/enterprise-e2e-scenario-library.md) — enterprise-readiness E2E scenarios to automate as slices land.
- [`docs/qa/launch-e2e-scenario-runbook-2026-06-24.md`](docs/qa/launch-e2e-scenario-runbook-2026-06-24.md) — launch workflow evidence and scenario runbook.
- [`docs/qa/ishantech-production-e2e-runbook-2026-07-11.md`](docs/qa/ishantech-production-e2e-runbook-2026-07-11.md) — current deterministic production E2E script and accounting oracles.
- [`docs/qa/launch-readiness-review-2026-09-09.md`](docs/qa/launch-readiness-review-2026-09-09.md) — **current** launch verdict (NOT READY for paid launch; READY for controlled pilot demos), guide audit, agentic inventory; companions [`docs/DEMO_GUIDE_v3_END_TO_END.md`](docs/DEMO_GUIDE_v3_END_TO_END.md) and [`docs/team/LAUNCH_GAP_IMPLEMENTATION_PLAN.md`](docs/team/LAUNCH_GAP_IMPLEMENTATION_PLAN.md).
- [`docs/qa/prelaunch-platform-validation-runbook-2026-08-05.md`](docs/qa/prelaunch-platform-validation-runbook-2026-08-05.md) — last passed release gate (Demo Guide v2 gate, 2026-08-05).
- [`docs/qa/launch-readiness-audit-2026-07-11.md`](docs/qa/launch-readiness-audit-2026-07-11.md) — historical NO-GO audit; see its 2026-09-03 supersession note for which blockers have since landed.

The library publishes the platform user guide, the Nous prompt library, the
Nous-on-Hermes runtime and learning operations manual, and both demo guides.
Each guide has an **Export PDF** action (print-to-PDF; real text, not a
raster). Run `cd frontend && npm run guides:generate`
after changing those Markdown sources; frontend start and production-build
commands also regenerate the HTML automatically.

## Local Runtime

Use Node 20 for the Angular workspace. The repo pins `.nvmrc` to Node 20.19.0 because Angular 20 rejects unsupported local runtimes such as Node 24.

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

**Guided-pilot ready; not yet signed off for self-serve launch.** Three QA
documents describe launch state and they supersede each other in this order:
the 2026-08-05 pre-launch validation runbook (current release gate, passed on
build `825ed5c`), the 2026-07-11 launch-readiness audit (historical NO-GO;
many blockers have since landed, see its supersession note), and the
2026-06-24 launch scenario runbook (historical). The 2026-09-03 comprehensive
review filed issues #491–#528 for the remaining defects and platform gaps.
The production topology is the Hostinger Docker/Traefik deployment described in
[`docs/infra/HOSTINGER_DEPLOYMENT.md`](docs/infra/HOSTINGER_DEPLOYMENT.md).
The launch owner confirmed the canonical production URL as
`https://aethos.ishirock.tech/`; QA runbooks still use `${PRODUCTION_URL}` as a
replay variable.

Historical reports record substantial backend and Playwright coverage, but
they are not proof that the current production build is launch-ready. In
particular, `backend/tests/e2e/test_engagement_to_cash.py` remains a strict
`xfail`/`NotImplementedError` skeleton, several browser suites use mocked or
API-assisted setup, and the new-tenant production transaction/role/close run is
not yet signed off. Use the current launch-readiness audit for the verdict,
not a historical pass count.
