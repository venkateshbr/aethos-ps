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

from app.core.config import Settings, settings


def create_queue_app(config: Settings) -> App:
    """Build the queue app with an explicitly bounded database pool."""
    connector = PsycopgConnector(
        conninfo=config.database_url or "postgresql://placeholder/placeholder",
        min_size=config.queue_db_pool_min_size,
        max_size=config.queue_db_pool_max_size,
        kwargs={"application_name": config.queue_db_application_name},
    )
    return App(
        connector=connector,
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


# The placeholder DSN keeps imports safe when DATABASE_URL is unset (tests,
# build-time linting, and CLI commands that do not open the connector).
app = create_queue_app(settings)
