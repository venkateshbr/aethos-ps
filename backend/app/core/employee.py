"""``get_current_employee`` dependency for the Timesheet Portal (issue #134, P4).

Portal endpoints are NOT gated by ``require_role`` — an 'employee' sits at the
bottom of the role hierarchy and would be rejected. Instead they inject this
dependency, which:

1. Verifies tenant membership (via ``get_tenant_id``) and a valid JWT.
2. Resolves the caller's ``employees`` row by ``user_id`` within that tenant.
3. Raises 403 if the authenticated user has no employee record — i.e. they are
   not a portal-enabled worker.

The returned row is the authoritative identity for all self-only timesheet
operations: the caller may only ever read/write their own ``employee_id``.
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from supabase import Client

logger = logging.getLogger(__name__)


def get_current_employee(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> dict:
    """Return the ``employees`` row for the authenticated portal user."""
    result = (
        db.table("employees")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("user_id", current_user.user_id)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning(
            "Portal access by a user with no employee record",
            extra={"user_id": current_user.user_id, "tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No employee profile is linked to this account.",
        )
    return result.data[0]
