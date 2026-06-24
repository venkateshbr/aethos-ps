"""Procrastinate App — Postgres-backed task queue.

Replaces ARQ (Redis-backed). Lives entirely inside the Supabase Postgres
project so we don't have to operate a separate Redis service. Procrastinate
uses LISTEN/NOTIFY for near-real-time job pickup and a polling fallback
when the connection drops.

Start a worker locally:
    cd backend
    set -a && source .env && set +a
    uv run python -m procrastinate --app=app.workers.procrastinate_app.app worker

Defer a job from application code:
    from app.workers.document_extraction import extract_document_worker
    await extract_document_worker.defer_async(document_id=..., tenant_id=...)

The FastAPI app opens the connector at startup and closes it at shutdown
(see app/main.py). Workers open their own connector via the CLI above.
"""

from __future__ import annotations

from procrastinate import App, PsycopgConnector

from app.core.config import settings

# The connector is created with a *placeholder* DSN at import time so the
# module loads cleanly even when DATABASE_URL is unset (tests, build-time
# linting, CLI tools that don't actually defer). Real DSN is injected at
# startup via app.replace_connector() when DATABASE_URL is present.
_connector = PsycopgConnector(conninfo=settings.database_url or "postgresql://placeholder/placeholder")

app = App(
    connector=_connector,
    import_paths=[
        "app.workers.document_extraction",
        "app.workers.fx_refresh",
        "app.workers.collections",
        "app.workers.autonomy_promoter",
        "app.workers.stripe_reconcile_worker",
        "app.workers.billing_run_worker",
        "app.workers.close_scheduler_worker",
        "app.workers.finance_ops_manager_worker",
        "app.workers.project_health_worker",
        "app.workers.intelligence_worker",
        "app.workers.time_entry_reminder_worker",
    ],
)
