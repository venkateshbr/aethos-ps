"""Tenant middleware and dependency for Aethos PS.

Every HTTP request must carry a tenant context before hitting service code.
The middleware resolves the tenant_id from the ``X-Tenant-ID`` header (set by
the Angular interceptor) and sets it in the ``tenant_id_var`` context variable.

A ``trace_id_var`` is also populated from ``X-Request-ID`` (or generated) so
every log line in the same request is correlated.

Future: once the Supabase client is wired, the middleware will validate that
the authenticated user is a member of the claimed tenant.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import tenant_id_var, trace_id_var

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Populate ``tenant_id_var`` and ``trace_id_var`` for every request.

    Resolution order for tenant_id:
    1. ``X-Tenant-ID`` request header (set by Angular interceptor post-login)
    2. Future: decode JWT → look up ``tenant_users`` table
    3. Empty string (public / unauthenticated routes — auth router, health check)

    The middleware never rejects requests — the ``get_tenant_id`` dependency
    raises ``HTTP 403`` if tenant context is required but missing.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # ------------------------------------------------------------------
        # Trace ID — use incoming header if present, else generate
        # ------------------------------------------------------------------
        incoming_trace_id = request.headers.get("X-Request-ID", "")
        trace_id = incoming_trace_id if incoming_trace_id else uuid.uuid4().hex
        trace_token = trace_id_var.set(trace_id)

        # ------------------------------------------------------------------
        # Tenant ID — from header for now; DB lookup added in a later PR
        # ------------------------------------------------------------------
        tenant_id = request.headers.get("X-Tenant-ID", "")
        tenant_token = tenant_id_var.set(tenant_id)

        try:
            response = await call_next(request)
        finally:
            trace_id_var.reset(trace_token)
            tenant_id_var.reset(tenant_token)

        response.headers["X-Trace-ID"] = trace_id
        return response


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_tenant_id() -> str:
    """Return the current tenant_id; raise 403 if missing.

    Inject this dependency on any endpoint that requires tenant scoping.
    Public endpoints (health, auth callbacks) should NOT depend on this.
    """
    tenant_id = tenant_id_var.get("")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context missing — include X-Tenant-ID header",
        )
    return tenant_id
