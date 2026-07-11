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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimitMiddleware, RateLimitRule, build_rate_limiter
from app.core.tenant import TenantMiddleware
from app.services.operational_telemetry import telemetry


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


class RequestTelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        try:
            response: Response = await call_next(request)
        except Exception:
            telemetry.record_request_failure(
                method=request.method,
                path=request.url.path,
                status_code=500,
            )
            raise
        telemetry.record_request_failure(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response


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
            queue_logger = _logging.getLogger(__name__)
            if _queue_required(settings):
                queue_logger.error(
                    "Required Procrastinate connector failed to open — "
                    "aborting startup (error_type=%s)",
                    type(exc).__name__,
                )
                raise
            queue_logger.warning(
                "Procrastinate connector failed to open — defers will degrade "
                "(error_type=%s)",
                type(exc).__name__,
            )
            queue_app = None

    yield

    if queue_app is not None:
        try:
            await queue_app.close_async()
        except Exception:
            pass

    try:
        from app.agents.base import flush_langfuse

        flush_langfuse()
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
app.add_middleware(
    RateLimitMiddleware,
    enabled=settings.rate_limit_enabled,
    limiter=build_rate_limiter(),
    rules=[
        RateLimitRule(
            name="signup",
            method="POST",
            path_prefix="/api/v1/auth/signup",
            max_requests=settings.rate_limit_signup_max_requests,
            window_seconds=settings.rate_limit_window_seconds,
        ),
        RateLimitRule(
            name="public_invoice",
            method="GET",
            path_prefix="/api/v1/public/invoices/",
            max_requests=settings.rate_limit_public_invoice_max_requests,
            window_seconds=settings.rate_limit_window_seconds,
        ),
    ],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestTelemetryMiddleware)

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
    from app.core.config import settings as runtime_settings

    try:
        from supabase import create_client

        t0 = _time.monotonic()
        db = create_client(runtime_settings.supabase_url, runtime_settings.supabase_anon_key)
        db.table("tenants").select("id").limit(1).execute()
        checks["db"] = {"status": "ok", "latency_ms": round((_time.monotonic() - t0) * 1000)}
    except Exception as e:
        checks["db"] = {"status": "error", "error": str(e)[:80]}

    # Queue: Procrastinate-on-Postgres. Same DB but a separate connector.
    queue_required = _queue_required(runtime_settings)
    try:
        if runtime_settings.database_url:
            from app.workers.procrastinate_app import app as queue_app

            t0 = _time.monotonic()
            await queue_app.check_connection_async()
            checks["queue"] = {
                "status": "ok",
                "configured": True,
                "required": queue_required,
                "latency_ms": round((_time.monotonic() - t0) * 1000),
            }
        else:
            checks["queue"] = {
                "status": "not_configured",
                "configured": False,
                "required": queue_required,
            }
    except Exception as e:
        checks["queue"] = {
            "status": "error",
            "configured": bool(runtime_settings.database_url),
            "required": queue_required,
            "error": "connection_failed",
            "error_type": type(e).__name__,
        }

    db_ready = checks.get("db", {}).get("status") == "ok"
    queue_ready = checks.get("queue", {}).get("status") == "ok"
    overall = "ready" if db_ready and (queue_ready or not queue_required) else "degraded"
    return {"status": overall, "checks": checks}


def _queue_required(runtime_settings: object) -> bool:
    if getattr(runtime_settings, "queue_required", False) is True:
        return True
    extraction_mode = str(getattr(runtime_settings, "extraction_mode", "sync") or "sync").lower()
    return extraction_mode == "async"
