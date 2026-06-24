"""Tenant middleware and dependency for Aethos PS.

Every authenticated HTTP request must carry a tenant context **and** prove the
caller is a member of the claimed tenant.

Two layers cooperate:

1. ``TenantMiddleware`` — runs on every request, populates ``tenant_id_var``
   and ``trace_id_var`` so log lines are correlated. **It does NOT enforce
   security** — the value it stashes is the raw, untrusted ``X-Tenant-ID``
   header and may be wrong or absent. Treat ``tenant_id_var`` as a logging
   hint only.

2. ``get_tenant_id`` FastAPI dependency — runs only on protected routes that
   inject it. It decodes the JWT (via ``get_current_user``), then verifies
   the JWT subject is an active member of the claimed tenant by querying
   ``tenant_users``. Raises 401 (no JWT) / 403 (no header) / 404 (not a
   member, or soft-deleted membership).

Why a dependency rather than middleware:

- The DB lookup is only paid on authenticated routes (every endpoint that
  needs tenant scoping already injects ``get_tenant_id``). Public endpoints
  (``/health``, ``/api/v1/auth/signup``, Stripe webhooks) don't pay the cost.
- FastAPI deduplicates ``Depends`` per request, so multiple injections in
  one request hit the DB only once. We also stash the verified value on
  ``request.state`` to keep the contract explicit.
- Membership is **NOT cached across requests** — revocation must take effect
  on the next request, not on a TTL boundary.

History: prior to issue #90 this module trusted the raw ``X-Tenant-ID``
header without any cross-check, which allowed cross-tenant data reads if an
attacker knew (or guessed) another tenant's UUID. The membership check
introduced here closes that hole.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Depends, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.logging import tenant_id_var, trace_id_var
from supabase import Client

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Populate ``tenant_id_var`` and ``trace_id_var`` for every request.

    The value stashed in ``tenant_id_var`` is the **raw** ``X-Tenant-ID``
    header for log correlation only. Security enforcement lives in the
    ``get_tenant_id`` dependency, which cross-checks the header against
    the JWT subject's ``tenant_users`` membership.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # ------------------------------------------------------------------
        # Trace ID — use incoming header if present, else generate
        # ------------------------------------------------------------------
        incoming_trace_id = request.headers.get("X-Request-ID", "")
        trace_id = incoming_trace_id if incoming_trace_id else uuid.uuid4().hex
        trace_token = trace_id_var.set(trace_id)

        # ------------------------------------------------------------------
        # Tenant ID — populated for log correlation only. NOT authoritative.
        # The get_tenant_id dependency below re-reads the header and verifies
        # membership against the JWT subject before any service code runs.
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
# Membership lookup
# ---------------------------------------------------------------------------

# Sentinel placed on request.state to avoid a duplicate DB lookup when the
# membership check is reached more than once in the same request (defensive —
# FastAPI's Depends caching already covers the common case).
_VERIFIED_TENANT_STATE_KEY = "_aethos_verified_tenant_id"
_VERIFIED_TENANT_ROLE_STATE_KEY = "_aethos_verified_tenant_role"


def _lookup_active_membership(
    db: Client,
    *,
    user_id: str,
    tenant_id: str,
) -> dict[str, str] | None:
    """Return active ``tenant_users`` membership details for this request.

    This is intentionally only request-scoped; revocation still takes effect on
    the next request. A short retry loop absorbs transient Supabase connection
    resets so RBAC does not downgrade a valid owner/admin to viewer because one
    TLS handshake failed.
    """
    for attempt in range(3):
        try:
            result = (
                db.table("tenant_users")
                .select("id, role")
                .eq("user_id", user_id)
                .eq("tenant_id", tenant_id)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            if result.data:
                row = result.data[0]
                return {"id": row["id"], "role": row["role"]}
            return None
        except Exception:  # pragma: no cover - exercised with fake DB in unit tests
            if attempt < 2:
                time.sleep(0.2 * (attempt + 1))
                continue
            # Treat persistent DB/network errors as "not a member" — fail closed.
            # We log at error level so SRE alerts pick it up rather than silently
            # denying.
            logger.exception(
                "tenant_users membership lookup failed",
                extra={"user_id": user_id, "tenant_id": tenant_id},
            )
            return None

    return None


def _is_active_member(
    db: Client,
    *,
    user_id: str,
    tenant_id: str,
) -> bool:
    """Return True iff ``user_id`` has an active (non soft-deleted) row in
    ``tenant_users`` for ``tenant_id``.

    Uses the service-role client so the lookup itself is not subject to RLS
    (RLS would require ``app.current_tenant_id`` to already be set, which is
    what we are about to verify — a chicken-and-egg). The query is narrow:
    one row by ``(user_id, tenant_id)`` with ``deleted_at IS NULL``, backed
    by the partial index ``idx_tenant_users_user_id``.
    """
    return _lookup_active_membership(db, user_id=user_id, tenant_id=tenant_id) is not None


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_tenant_id(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> str:
    """Return the verified ``tenant_id`` for the current request.

    Enforces, in order:

    - JWT must be present and valid (``get_current_user`` raises 401 first).
    - ``X-Tenant-ID`` header must be present and a syntactically valid UUID
      (otherwise 403).
    - The JWT subject must have an active (non soft-deleted) row in
      ``tenant_users`` for the claimed tenant (otherwise 404).

    The 404 is deliberate: returning 403 would leak that the tenant exists
    but the caller is not a member. 404 is consistent with how list
    endpoints already return empty for foreign-tenant resources.

    Inject on every endpoint that operates on tenant data. Public endpoints
    (health, signup, webhooks) MUST NOT inject this.
    """
    # ------------------------------------------------------------------
    # Per-request memoization (defensive — Depends already dedupes)
    # ------------------------------------------------------------------
    cached: str | None = getattr(request.state, _VERIFIED_TENANT_STATE_KEY, None)
    if cached is not None:
        return cached

    # ------------------------------------------------------------------
    # Header presence + shape
    # ------------------------------------------------------------------
    raw_tenant_id = request.headers.get("X-Tenant-ID", "").strip()
    if not raw_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context missing — include X-Tenant-ID header",
        )
    try:
        # Normalise so a malformed UUID never hits the DB layer.
        tenant_uuid = str(uuid.UUID(raw_tenant_id))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-Tenant-ID header",
        ) from exc

    # ------------------------------------------------------------------
    # JWT subject ↔ tenant membership cross-check
    # ------------------------------------------------------------------
    membership = _lookup_active_membership(
        db,
        user_id=current_user.user_id,
        tenant_id=tenant_uuid,
    )
    if membership is None:
        # Log at warning — this is either an honest typo (UI bug) or a spoof
        # attempt. Either way the SRE / Dhruva pipeline should see it.
        logger.warning(
            "Tenant membership check failed",
            extra={
                "user_id": current_user.user_id,
                "claimed_tenant_id": tenant_uuid,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Pin the verified value on request.state for any later in-request reads.
    setattr(request.state, _VERIFIED_TENANT_STATE_KEY, tenant_uuid)
    setattr(request.state, _VERIFIED_TENANT_ROLE_STATE_KEY, membership["role"])
    # Also refresh the logging context var so subsequent log lines carry the
    # verified id (the middleware may have stashed an unverified header value).
    tenant_id_var.set(tenant_uuid)
    return tenant_uuid
