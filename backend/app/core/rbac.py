"""Role-Based Access Control for Aethos PS.

Roles mirror the ``user_role`` enum in the DB (migration 0001).
The hierarchy is ordinal: owner > admin > manager > member > viewer > employee.

``employee`` is the narrow Timesheet-Portal role (migration 0021). It sits at the
BOTTOM of the hierarchy so an employee JWT is rejected by every ``require_role``
gate in the ERP (the lowest ERP gate is ``viewer``). Timesheet endpoints do NOT
use ``require_role`` — they use the ``get_current_employee`` dependency, which
resolves the caller's ``employees`` row. This firewalls portal logins out of all
ERP data (defence in depth).

Usage
-----
    from app.core.rbac import UserRole, require_role

    @router.delete("/{id}")
    async def delete_engagement(
        current_user=require_role(UserRole.admin),
    ):
        ...
"""

from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from supabase import Client


class UserRole(StrEnum):
    owner = "owner"
    admin = "admin"
    manager = "manager"
    member = "member"
    viewer = "viewer"
    employee = "employee"


ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.owner: 5,
    UserRole.admin: 4,
    UserRole.manager: 3,
    UserRole.member: 2,
    UserRole.viewer: 1,
    UserRole.employee: 0,
}


def _resolve_role(current_user: CurrentUser, request: Request, db: Client) -> UserRole:
    """Return the effective UserRole for this request.

    Primary source: ``app_metadata.role`` in the JWT (set by Supabase JWT hook).
    Fallback: DB lookup from ``tenant_users`` using X-Tenant-ID header.

    The fallback handles accounts created via admin APIs (e.g. e2e test setup)
    that bypass the JWT hook, as well as environments where the hook is not yet
    configured.
    """
    try:
        return UserRole(current_user.role)
    except ValueError:
        pass

    # JWT role is absent or unrecognised — fall back to tenant_users table.
    raw_tenant_id = request.headers.get("X-Tenant-ID", "").strip()
    if not raw_tenant_id:
        return UserRole.viewer

    try:
        result = (
            db.table("tenant_users")
            .select("role")
            .eq("user_id", current_user.user_id)
            .eq("tenant_id", raw_tenant_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        if result.data:
            return UserRole(result.data[0]["role"])
    except Exception:
        pass

    return UserRole.viewer


def require_role(minimum: UserRole) -> CurrentUser:
    """Dependency factory: raise 403 if the caller's role is below ``minimum``.

    Returns the ``CurrentUser`` so callers can use it without a second Depends.

    Example::

        @router.post("/billing-runs/{id}/approve")
        async def approve_billing_run(
            run_id: str,
            current_user: CurrentUser = require_role(UserRole.manager),
        ):
            ...
    """

    def _check(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
        db: Client = Depends(get_service_role_client),  # noqa: B008
    ) -> CurrentUser:
        user_role = _resolve_role(current_user, request, db)

        if ROLE_HIERARCHY.get(user_role, 0) < ROLE_HIERARCHY[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role: requires {minimum.value} or higher",
            )
        return current_user

    return Depends(_check)
