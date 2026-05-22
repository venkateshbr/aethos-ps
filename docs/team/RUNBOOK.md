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

## Deployment

### Prerequisites
- GCP project with billing enabled
- Cloud Run + Container Registry + Secret Manager APIs enabled (run `infra/cloudrun/setup.sh <PROJECT_ID>`)
- All secret values populated in Secret Manager secret `aethos-ps-secrets` (see setup script output for required keys)
- GitHub repository secrets set: `GCP_PROJECT_ID`, `GCP_SA_KEY`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

### Normal deploy
Push to `main` — `.github/workflows/deploy.yml` builds the Docker image, pushes to GCR, deploys to Cloud Run, and deploys the Angular SPA to Vercel in parallel.

### Manual deploy (emergency / hotfix)
```bash
# API — build, push, deploy
cd backend
docker build -t gcr.io/${PROJECT_ID}/aethos-ps-api:latest .
docker push gcr.io/${PROJECT_ID}/aethos-ps-api:latest
gcloud run deploy aethos-ps-api \
  --image gcr.io/${PROJECT_ID}/aethos-ps-api:latest \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated

# Frontend — build, deploy
cd frontend && npm ci && npx ng build --configuration=production
npx vercel --prod --yes
```

### Rollback
```bash
# List revisions
gcloud run revisions list --service aethos-ps-api --region asia-northeast1

# Route 100% traffic to a previous revision
gcloud run services update-traffic aethos-ps-api \
  --to-revisions=<REVISION_NAME>=100 \
  --region asia-northeast1
```

### DB migrations
`supabase migration up` — manual gate; Sthira runs after backup verification.

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

### [2026-05-23] — Production deployment infrastructure added (issue #85)
- Created `backend/Dockerfile` (multi-stage, non-root user, health check, Cloud Run PORT env var)
- Created `infra/cloudrun/api-service.yaml` (Knative service, minScale=1, all secrets via Secret Manager)
- Created `infra/cloudrun/worker-job.yaml` (Cloud Run Job for ARQ workers, same image different CMD)
- Created `infra/vercel/vercel.json` (Angular SPA, /api/* proxy to Cloud Run)
- Created `frontend/src/environments/environment{.prod}.ts` + wired `fileReplacements` in angular.json
- Created `.github/workflows/deploy.yml` (parallel API + frontend deploy on push to main)
- Created `infra/cloudrun/setup.sh` (one-time GCP setup — APIs, Secret Manager)
- Recommendation: run Locust load tests (issue #86) before raising minScale or maxScale
