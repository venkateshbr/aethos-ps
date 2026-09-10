# Aethos PS — Runbook

> **Owner**: Sthira (SRE)
> **Status**: Skeleton. Filled as infra and ops surface (PLAN §12).

## Production topology (Hostinger — current)

> Updated 2026-09-03 (#491). The Vercel / Cloud Run sections that used to live
> here described a topology that was never deployed; the authoritative deploy
> and rollback procedure is [`docs/infra/HOSTINGER_DEPLOYMENT.md`](../infra/HOSTINGER_DEPLOYMENT.md).

| Surface | Provider | Notes |
| --- | --- | --- |
| Edge / TLS | Traefik on the Hostinger VPS | Let's Encrypt; routes `aethos.ishirock.tech` (web) and `timesheet.aethos.ishirock.tech` |
| Frontend | nginx container (`frontend/Dockerfile.prod`) | Angular 20 SPA; `/api` proxied to the private API container |
| Timesheet portal | nginx container (`frontend/Dockerfile.timesheet.prod`) | Second Angular app; host port 4202 |
| Backend API | private FastAPI container (`backend/Dockerfile`) | `:8011` inside the compose network only |
| Workers | private Procrastinate container (same image, worker CMD) | Queues `default,extraction,billing,fx,cron`; see `docs/qa/queue-session-budget-runbook.md` |
| Nous advanced runtime | shared host Hermes `aethos-nous` profile (`integrations/hermes/`) | Enabled by `ATLAS_AI_RUNTIME=hermes_agent`; falls back to the in-process runtime when down |
| Database / Auth / Storage | Supabase managed (PostgreSQL 15+) | RLS + Auth + Storage + Procrastinate task queue (no Redis) |
| Email | Resend | Collections/time reminders today; invoice email delivery is #516 |
| LLM | OpenRouter model chain (`agent_models` in `app/core/config.py`) | No per-tenant budget middleware yet (#503) |
| LLM observability | Langfuse | Traces; scores/datasets not yet wired for learning loops |
| Payments | Stripe (Subs + Connect Standard + Payment Links) | Stripe Tax not integrated |

Compose files: `docker-compose.hostinger.yml` (build from source) and
`docker-compose.hostinger.registry.yml` (pull `ghcr.io/venkateshbr/aethos-ps-*`).
Start/stop helpers: `start-prod.sh`, `stop-prod.sh`.

## Health endpoints

- `GET /health` — liveness, no auth.
- `GET /health/ready` — readiness (DB, queue when `QUEUE_REQUIRED=true` or `EXTRACTION_MODE=async`).
- `GET /api/v1/ping` — API smoke.
- `GET /api/v1/tenants/health` — tenant-scoped operational health (admin); surfaced in Settings → Operational Health.

See [`agent-harness/core/observability-standard.md`](../../agent-harness/core/observability-standard.md).

## SLOs (to be tuned)

- `POST /api/v1/chat/threads/{id}/messages` (SSE) — TTFT < 3s p95, error rate < 1%.
- `POST /api/v1/invoices/{id}/send` — < 3s p95.
- Stripe webhook → invoice paid — < 1s p95.

## Deployment

### Normal deploy
Manual `workflow_dispatch` of `.github/workflows/deploy-hostinger.yml` (builds images, pushes to GHCR, SSHes to the VPS, pulls and restarts the compose stack). Record the deployed SHA in the release note; `AETHOS_EXPECTED_DEPLOY_SHA` is asserted by the production Playwright smoke.

### Rollback
Re-run the deploy workflow with the previous image tag / SHA, or on the VPS: `docker compose -f docker-compose.hostinger.registry.yml pull <service>@<previous tag> && docker compose up -d <service>`. Full procedure in `docs/infra/HOSTINGER_DEPLOYMENT.md`.

### DB migrations
`cd backend && uv run python -m scripts.apply_migrations` (idempotent, see script header) after a verified Supabase backup. Never apply a migration that has not passed the unit contract tests.

## Common operations

### Rotate a secret
- Update the VPS `.env` (or the GitHub environment secret used by the deploy workflow).
- `docker compose up -d` the affected services; verify `/health/ready` and Settings → Operational Health.

### Investigate a customer report
- Get the request/trace ID (response header or Agent Run Ledger).
- Open the Langfuse trace; pivot to container logs by trace ID (`docker compose logs api worker`).

### Reconcile a missed Stripe webhook
- `POST /api/v1/payments/reconcile-stripe` as an admin for the tenant (hourly automation is #493).
- Verify `payments` rows and the DR Bank / CR AR journal were created once.

### Queue backlog / stuck cron jobs
- Follow `docs/qa/queue-session-budget-runbook.md` (session-pool limits, queue names, safe cancellation).

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
- Created `infra/cloudrun/worker-job.yaml` (Cloud Run Job for Procrastinate workers, same image different CMD)
- Created `infra/vercel/vercel.json` (Angular SPA, /api/* proxy to Cloud Run)
- Created `frontend/src/environments/environment{.prod}.ts` + wired `fileReplacements` in angular.json
- Created `.github/workflows/deploy.yml` (parallel API + frontend deploy on push to main)
- Created `infra/cloudrun/setup.sh` (one-time GCP setup — APIs, Secret Manager)
- Recommendation: run Locust load tests (issue #86) before raising minScale or maxScale

### [2026-05-23] — Supabase Storage `documents` bucket provisioned (issue #100)
- Created bucket on project `glcljucaayeesvrsjths`: private, 20 MiB cap, MIME allow-list (PDF / JPEG / PNG / WebP / plain text) matched against `backend/app/api/v1/endpoints/documents.py`.
- Added migration `backend/supabase/migrations/0016_storage_documents_bucket.sql` as the reproducible source of truth (idempotent — `ON CONFLICT DO UPDATE` for the bucket row, `DROP POLICY IF EXISTS` + `CREATE POLICY` for the four RLS policies).
- Added defense-in-depth RLS on `storage.objects` for the `documents` bucket: SELECT/INSERT/UPDATE/DELETE policies require the first path segment (`(storage.foldername(name))[1]`) to be a tenant the authenticated user has an active row for in `public.tenant_users`. Service-role callers (the API upload path) bypass RLS — tenant scoping for writes lives in `get_tenant_id`.
- Added follow-up migration `backend/supabase/migrations/0017_storage_documents_rls_helper.sql` — wraps the membership lookup in `public.is_tenant_member(uuid, uuid)` SECURITY DEFINER SQL function so the Storage policies don't get blocked by `tenant_users`' own RLS (which requires `app.current_tenant_id`, not set in the GoTrue → Storage path). Without this, legit owners saw 404 on their own objects. EXECUTE locked to `authenticated`, `service_role`.
- Added operator runbook `docs/infra/STORAGE_BUCKETS.md` — bucket inventory, provisioning procedures, verification commands, failure-mode triage. Every new bucket the product adds must be listed there with a paired migration.
- Added verification fixture `backend/tests/api/test_storage_rls.py` — proves Tenant A can read its own object via authenticated JWT, Tenant B is denied, service-role still bypasses, and bucket config matches `documents.py` constants. Run via `cd backend && set -a && source .env && set +a && uv run pytest tests/api/test_storage_rls.py -v`.
