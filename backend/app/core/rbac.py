"""Role-Based Access Control for Aethos PS.

Roles mirror the ``user_role`` enum in the DB (migration 0001 plus additive
role migrations). The hierarchy is ordinal for normal ERP access gates:
owner > admin > manager > approver > member > viewer/auditor > employee.

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

import logging
from enum import StrEnum

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import (
    _VERIFIED_TENANT_ROLE_STATE_KEY,
    _VERIFIED_TENANT_STATE_KEY,
    _lookup_active_membership,
)
from supabase import Client

logger = logging.getLogger(__name__)


class UserRole(StrEnum):
    owner = "owner"
    admin = "admin"
    manager = "manager"
    approver = "approver"
    member = "member"
    auditor = "auditor"
    viewer = "viewer"
    employee = "employee"


ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.owner: 6,
    UserRole.admin: 5,
    UserRole.manager: 4,
    UserRole.approver: 3,
    UserRole.member: 2,
    UserRole.viewer: 1,
    UserRole.auditor: 1,
    UserRole.employee: 0,
}

_APPROVER_MANAGER_LEVEL_ROLES: frozenset[UserRole] = frozenset(
    {
        UserRole.manager,
        UserRole.approver,
        UserRole.member,
        UserRole.viewer,
        UserRole.auditor,
    }
)


def role_meets_minimum(user_role: UserRole, minimum: UserRole) -> bool:
    """Return True when ``user_role`` passes a normal hierarchy gate."""
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY[minimum]


def role_allows_approval(user_role: UserRole, required_role: UserRole) -> bool:
    """Return True when ``user_role`` can decide an Inbox/approval item.

    ``approver`` is intentionally not a general ``manager`` for CRUD screens,
    but can decide manager-threshold review work. Admin/owner thresholds still
    require admin/owner hierarchy.
    """
    if role_meets_minimum(user_role, required_role):
        return True
    if user_role == UserRole.approver and required_role in _APPROVER_MANAGER_LEVEL_ROLES:
        return True
    return False


def _coerce_role(role_value: object, current_user: CurrentUser, *, from_membership: bool) -> UserRole:
    """Convert a role string to ``UserRole``; unknowns collapse to ``viewer``.

    When the authoritative membership role disagrees with the JWT's
    ``app_metadata.role`` claim, log it (the claim is *rejected* in favour of
    membership) so stale/cross-tenant tokens are observable. (#378 AC 2)
    """
    try:
        resolved = UserRole(str(role_value).strip())
    except ValueError:
        return UserRole.viewer
    if from_membership:
        jwt_role = (current_user.role or "").strip()
        if jwt_role and jwt_role not in {"anon", "authenticated"} and jwt_role != resolved.value:
            logger.warning(
                "jwt_role_membership_mismatch",
                extra={
                    "user_id": current_user.user_id,
                    "jwt_role": jwt_role,
                    "membership_role": resolved.value,
                },
            )
    return resolved


def _resolve_role(current_user: CurrentUser, request: Request, db: Client) -> UserRole:
    """Return the effective UserRole for this request.

    The **active-tenant membership is authoritative** (#378 AC 2): for any
    tenant-scoped request the role comes from the caller's ``tenant_users`` row
    for the *targeted* tenant, never the (possibly stale or cross-tenant)
    ``app_metadata.role`` claim in the JWT. The JWT role is only a best-effort
    fallback when there is no tenant context to verify against (non-tenant-scoped
    endpoints, or JWT-hook-only setups where the DB row was not yet seeded).
    """
    raw_tenant_id = request.headers.get("X-Tenant-ID", "").strip()

    # 1. Membership role verified for this tenant (cached by get_tenant_id's
    #    cross-check) — the authoritative source.
    cached_tenant_id = getattr(request.state, _VERIFIED_TENANT_STATE_KEY, None)
    cached_role = getattr(request.state, _VERIFIED_TENANT_ROLE_STATE_KEY, None)
    if raw_tenant_id and cached_tenant_id == raw_tenant_id and cached_role:
        return _coerce_role(cached_role, current_user, from_membership=True)

    # 2. A tenant is targeted but not yet verified here — resolve from the DB and
    #    trust the membership over the JWT claim.
    if raw_tenant_id:
        membership = _lookup_active_membership(
            db,
            user_id=current_user.user_id,
            tenant_id=raw_tenant_id,
        )
        if membership is not None:
            setattr(request.state, _VERIFIED_TENANT_STATE_KEY, raw_tenant_id)
            setattr(request.state, _VERIFIED_TENANT_ROLE_STATE_KEY, membership["role"])
            return _coerce_role(membership["role"], current_user, from_membership=True)
        # Targeted a tenant the caller is not an active member of → no authority.
        return UserRole.viewer

    # 3. No tenant context at all — best-effort JWT role (nothing to verify).
    raw_role = (current_user.role or "").strip()
    try:
        return UserRole(raw_role)
    except ValueError:
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

        if not role_meets_minimum(user_role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role: requires {minimum.value} or higher",
            )
        return CurrentUser(
            user_id=current_user.user_id,
            email=current_user.email,
            role=user_role.value,
        )

    # Expose the gate so the executable authz-matrix contract test can assert the
    # required role of each sensitive handler without the live stack. (#378 AC 7)
    _check.aethos_min_role = minimum  # type: ignore[attr-defined]
    return Depends(_check)
