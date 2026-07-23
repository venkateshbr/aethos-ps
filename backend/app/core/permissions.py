"""Privilege-based authorization dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.services.security_service import SecurityService
from supabase import Client


def require_privilege(privilege_code: str) -> CurrentUser:
    """Dependency factory that authorizes by enterprise RBAC privilege."""

    async def _check(
        current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
        tenant_id: str = Depends(get_tenant_id),
        db: Client = Depends(get_service_role_client),  # noqa: B008
    ) -> CurrentUser:
        service = SecurityService(db, tenant_id)
        permissions = await service.effective_permissions(current_user.user_id)
        if privilege_code not in set(permissions.privilege_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {privilege_code}",
            )
        # Downstream business rules (for example procurement amount thresholds)
        # still need the verified legacy role. Do not pass through a generic
        # Supabase JWT role such as ``authenticated`` after privilege resolution.
        return CurrentUser(
            user_id=current_user.user_id,
            email=current_user.email,
            role=permissions.legacy_role,
        )

    # Expose the required privilege for the executable authz-matrix contract test
    # (#378 AC 7) — no live stack needed.
    _check.aethos_privilege = privilege_code  # type: ignore[attr-defined]
    return Depends(_check)
