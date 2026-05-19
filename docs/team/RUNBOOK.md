# Aethos PS — Runbook

> **Owner**: Sthira (SRE)
> **Status**: Skeleton. Filled as infra and ops surface (PLAN §12).

## Production topology

| Surface | Provider | Notes |
| --- | --- | --- |
| Frontend | Vercel | Angular 19 SSR-disabled SPA; preview deploys per PR |
| Backend API | Cloud Run | FastAPI on `:8011` dev / managed port in prod |
| Workers (ARQ) | Cloud Run jobs / always-on container | Document extraction, FX refresh, autonomy promoter, payment reconciliation, collections |
| Database | Supabase (PostgreSQL 15+) | RLS + Auth + Storage + Realtime |
| Cache / queue | Upstash Redis | — |
| Email | Resend | — |
| LLM | Anthropic Claude Sonnet 4.6 | Per-tenant budget enforced in middleware |
| LLM observability | Langfuse | Datasets + scores + drift |
| Payments | Stripe (Subs + Connect + Payment Links + Tax) | — |

## Health endpoints

- `GET /health` — liveness, no auth.
- `GET /health/ready` — readiness (DB, queue, secret store).
- `GET /admin/health` — admin-only; provider statuses.

See [`agent-harness/core/observability-standard.md`](../../agent-harness/core/observability-standard.md).

## SLOs (to be tuned)

- `/api/v1/copilot/chat/stream` — TTFT < 3s p95, error rate < 1%.
- `/api/v1/invoices/{id}/send` — < 3s p95.
- Webhook → invoice paid — < 1s p95.

## Common operations

### Deploy
- Push to `main` after PR merge → Vercel & Cloud Run auto-deploy.
- DB migrations: `supabase migration up` (manual gate via Sthira).

### Rotate a secret
- Update in 1Password / Doppler / Supabase secrets manager.
- Trigger rolling restart of Cloud Run service.
- Verify health endpoint returns expected provider statuses.

### Investigate a customer report
- Get trace ID (in support form or response header).
- Open Langfuse trace for the request.
- Pivot to logs by trace ID.

### Reconcile missed Stripe webhook
- Run `payment_reconciliation_worker` for the affected day.
- Verify `payments` rows created idempotently.

## Alert routing

| Tier | Examples | Channel |
| --- | --- | --- |
| Page | Prod down, payments broken, security incident, SLO burn-rate breach | On-call rotation |
| Ticket | SLO degradation, eval-score drift, queue lag | GitHub Issue with `priority:high` |
| Log | Low-priority anomalies | Logged only |

## Changelog

### [2026-05-19] — Skeleton created.
