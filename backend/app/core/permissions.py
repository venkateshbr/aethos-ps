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
        if not await service.has_privilege(current_user.user_id, privilege_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {privilege_code}",
            )
        return current_user

    return Depends(_check)
