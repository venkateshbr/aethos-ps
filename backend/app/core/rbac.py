"""Role-Based Access Control for Aethos PS.

Roles mirror the ``user_role`` enum in the DB (migration 0001).
The hierarchy is ordinal: owner > admin > manager > member > viewer.

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

from fastapi import Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user


class UserRole(StrEnum):
    owner = "owner"
    admin = "admin"
    manager = "manager"
    member = "member"
    viewer = "viewer"


ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.owner: 5,
    UserRole.admin: 4,
    UserRole.manager: 3,
    UserRole.member: 2,
    UserRole.viewer: 1,
}


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

    def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:  # noqa: B008
        try:
            user_role = UserRole(current_user.role)
        except ValueError:
            # Unknown role — treat as lowest privilege
            user_role = UserRole.viewer

        if ROLE_HIERARCHY.get(user_role, 0) < ROLE_HIERARCHY[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role: requires {minimum.value} or higher",
            )
        return current_user

    return Depends(_check)
