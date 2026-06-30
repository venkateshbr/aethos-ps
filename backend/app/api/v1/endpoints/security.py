"""Enterprise RBAC catalog endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.permissions import require_privilege
from app.core.tenant import get_tenant_id
from app.models.security import (
    CurrentUserPermissionsResponse,
    SecurityPrivilegeListResponse,
    SecurityRoleCreateRequest,
    SecurityRoleListResponse,
    SecurityRoleResponse,
)
from app.services.security_service import SecurityService
from supabase import Client

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> SecurityService:
    return SecurityService(db, tenant_id)


@router.get("/roles", response_model=SecurityRoleListResponse)
async def list_security_roles(
    _current_user: CurrentUser = require_privilege("security.roles.read"),  # noqa: B008
    svc: SecurityService = Depends(_service),  # noqa: B008
) -> SecurityRoleListResponse:
    return await svc.list_roles()


@router.post("/roles", response_model=SecurityRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_security_role(
    payload: SecurityRoleCreateRequest,
    current_user: CurrentUser = require_privilege("security.roles.manage"),  # noqa: B008
    svc: SecurityService = Depends(_service),  # noqa: B008
) -> SecurityRoleResponse:
    return await svc.create_role(payload, actor_user_id=current_user.user_id)


@router.get("/privileges", response_model=SecurityPrivilegeListResponse)
async def list_security_privileges(
    _current_user: CurrentUser = require_privilege("security.roles.read"),  # noqa: B008
    svc: SecurityService = Depends(_service),  # noqa: B008
) -> SecurityPrivilegeListResponse:
    return await svc.list_privileges()


@router.get("/me/permissions", response_model=CurrentUserPermissionsResponse)
async def current_user_permissions(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: SecurityService = Depends(_service),  # noqa: B008
) -> CurrentUserPermissionsResponse:
    return await svc.effective_permissions(current_user.user_id)
