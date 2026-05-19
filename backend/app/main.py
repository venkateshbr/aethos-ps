"""Aethos PS — FastAPI application entry point.

Start locally:
    uv run uvicorn app.main:app --reload --port 8011
"""

from __future__ import annotations

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
    yield
    # Teardown hooks (DB pool close, etc.) added here by Sthira as infra lands


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

    TODO (Sthira): wire real DB ping and Redis ping once infra is provisioned.
    """
    return {"status": "ready", "checks": {"db": "unchecked", "redis": "unchecked"}}
