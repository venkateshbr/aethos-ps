# Runbook — Procrastinate queue DB session budget (#369)

The Procrastinate queue lives inside the Supabase Postgres project. Every API and
worker process opens a **bounded** `PsycopgConnector` pool, so the total
session-pool connections stay under Supabase's **15-session** ceiling with
headroom for a rolling deploy (both old and new stacks live briefly) and operator
diagnostics.

## The budget

Steady-state sessions on Hostinger (asserted by
`backend/tests/unit/test_hostinger_deployment_contract.py`):

| Source | Count | Note |
|---|---|---|
| API | `api_workers (2) × QUEUE_DB_POOL_MAX_SIZE (1)` = **2** | one uvicorn worker per process |
| Worker | `QUEUE_DB_POOL_MAX_SIZE (2)` = **2** | `--concurrency=4` shares this pool |
| LISTEN/NOTIFY | **1** | Procrastinate's notify connection is *outside* the pool |
| **Steady total** | **5** | |
| **Deploy overlap** (×2) + 3 operator | **13** | `(5 × 2) + 3 ≤ 15` ✅ |

Pools are bounded per process and configurable via env — defaults keep the budget
safe; raise them only with the math above re-checked:

| Env var | Default | Applies to |
|---|---|---|
| `QUEUE_API_DB_POOL_MIN_SIZE` / `QUEUE_API_DB_POOL_MAX_SIZE` | 1 / 1 | API |
| `QUEUE_WORKER_DB_POOL_MIN_SIZE` / `QUEUE_WORKER_DB_POOL_MAX_SIZE` | 1 / 2 | worker |
| `QUEUE_API_DB_APPLICATION_NAME` / `QUEUE_WORKER_DB_APPLICATION_NAME` | `aethos-ps-api` / `aethos-ps-worker` | tags `pg_stat_activity` |
| `QUEUE_REQUIRED` | `true` (Hostinger) | fail vs degrade on connector open |

`QUEUE_REQUIRED=true` makes a process **degrade explicitly** (surfaced on
`/health/ready`) rather than block on an oversized implicit pool — the original
failure mode where a new process logged `EMAXCONNSESSION` for 30s then started
with the connector degraded.

## Incident check — "queue connector degraded" / `EMAXCONNSESSION`

1. **Health surface.** `GET /health/ready` → `checks.queue.status`.
   - `ok` → connector healthy; `error` → connector could not open;
   - `overall: degraded` with `queue.required: true` means a queue-backed path
     (document extraction, scheduled finance workflows) is at risk even though the
     plain `/health` HTTP check still passes.
2. **Count live sessions** (Supabase SQL editor / any session-pool connection):
   ```sql
   SELECT application_name, count(*), count(*) FILTER (WHERE state = 'idle') AS idle
   FROM pg_stat_activity
   WHERE application_name LIKE 'aethos-ps-%'
   GROUP BY application_name ORDER BY 1;
   ```
   Expect ≤ ~5 steady, ≤ ~13 mid-deploy. A stuck old stack holding sessions is the
   usual cause of a new process hitting the cap.
3. **Remediate.**
   - Confirm the previous deploy's containers actually stopped (no orphaned
     `aethos-ps-api` / `aethos-ps-worker` sessions lingering).
   - If a burst is legitimate, lower `QUEUE_*_DB_POOL_MAX_SIZE` or reduce API
     workers/worker `--concurrency`, re-checking `(steady × 2) + 3 ≤ 15`.
   - Never raise a pool max without recomputing the budget — the contract test
     `test_hostinger_default_session_budget_preserves_deploy_headroom` guards it.

## Related
- Pool wiring: `backend/app/workers/procrastinate_app.py`, `backend/app/core/config.py`
- Health: `backend/app/main.py` `/health/ready`
- Compose: `docker-compose.hostinger.yml`, `docker-compose.hostinger.registry.yml`
