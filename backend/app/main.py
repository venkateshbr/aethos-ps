"""Aethos PS — FastAPI application entry point.

Start locally:
    uv run uvicorn app.main:app --reload --port 8011
"""

from __future__ import annotations

import time as _time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.tenant import TenantMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: setup → yield → teardown."""
    configure_logging()

    # Open the Procrastinate connector if a DATABASE_URL is configured.
    # Degrades gracefully when unset (dev / test envs without the queue).
    queue_app = None
    if settings.database_url:
        try:
            from app.workers.procrastinate_app import app as queue_app
            await queue_app.open_async()
        except Exception as exc:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "Procrastinate connector failed to open — defers will degrade: %s", exc
            )
            queue_app = None

    yield

    if queue_app is not None:
        try:
            await queue_app.close_async()
        except Exception:
            pass


app = FastAPI(
    title="Aethos PS API",
    version="0.1.0",
    lifespan=lifespan,
    # Disable interactive docs in production to reduce attack surface
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# Middleware (order matters — outermost registered last in Starlette)
# ---------------------------------------------------------------------------

# CORS must be before TenantMiddleware so pre-flight OPTIONS requests pass through
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenantMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Top-level health endpoints (no auth, no tenant context required)
# ---------------------------------------------------------------------------


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness probe — Cloud Run / Kubernetes."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/health/ready", tags=["ops"])
async def health_ready() -> dict[str, object]:
    """Readiness probe — checked before routing traffic.

    Pings Supabase and the Procrastinate queue (if configured). Returns
    ``status: ready`` only when the DB is reachable; degrades gracefully if
    the queue connector is not configured.
    """
    checks: dict = {}

    try:
        from app.core.config import settings
        from supabase import create_client

        t0 = _time.monotonic()
        db = create_client(settings.supabase_url, settings.supabase_anon_key)
        db.table("tenants").select("id").limit(1).execute()
        checks["db"] = {"status": "ok", "latency_ms": round((_time.monotonic() - t0) * 1000)}
    except Exception as e:
        checks["db"] = {"status": "error", "error": str(e)[:80]}

    # Queue: Procrastinate-on-Postgres. Same DB but a separate connector.
    try:
        from app.core.config import settings

        if settings.database_url:
            from app.workers.procrastinate_app import app as queue_app

            t0 = _time.monotonic()
            await queue_app.check_connection_async()
            checks["queue"] = {
                "status": "ok",
                "latency_ms": round((_time.monotonic() - t0) * 1000),
            }
        else:
            checks["queue"] = {"status": "not_configured"}
    except Exception as e:
        checks["queue"] = {"status": "error", "error": str(e)[:80]}

    overall = "ready" if checks.get("db", {}).get("status") == "ok" else "degraded"
    return {"status": overall, "checks": checks}
