"""Tenant user administration endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import CurrentUser
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.tenant_users import (
    TenantUserAuditEventListResponse,
    TenantUserInviteRequest,
    TenantUserInviteResponse,
    TenantUserListResponse,
    TenantUserResponse,
    TenantUserUpdateRequest,
)
from app.services.tenant_users_service import TenantUsersService
from supabase import Client

router = APIRouter()

IncludeInactiveQuery = Annotated[bool, Query(description="Include deactivated users.")]
LimitQuery = Annotated[int, Query(ge=1, le=500)]


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> TenantUsersService:
    return TenantUsersService(db, tenant_id)


@router.get("", response_model=TenantUserListResponse)
async def list_tenant_users(
    include_inactive: IncludeInactiveQuery = False,
    _current_user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
    svc: TenantUsersService = Depends(_service),  # noqa: B008
) -> TenantUserListResponse:
    return await svc.list_users(include_inactive=include_inactive)


@router.post("", response_model=TenantUserInviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_tenant_user(
    payload: TenantUserInviteRequest,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: TenantUsersService = Depends(_service),  # noqa: B008
) -> TenantUserInviteResponse:
    return await svc.invite_user(payload, actor=current_user)


@router.patch("/{tenant_user_id}", response_model=TenantUserResponse)
async def update_tenant_user(
    tenant_user_id: str,
    payload: TenantUserUpdateRequest,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: TenantUsersService = Depends(_service),  # noqa: B008
) -> TenantUserResponse:
    return await svc.update_user(tenant_user_id, payload, actor=current_user)


@router.delete("/{tenant_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_tenant_user(
    tenant_user_id: str,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: TenantUsersService = Depends(_service),  # noqa: B008
) -> None:
    await svc.deactivate_user(tenant_user_id, actor=current_user)


@router.get("/audit-events", response_model=TenantUserAuditEventListResponse)
async def list_tenant_user_audit_events(
    tenant_user_id: str | None = None,
    limit: LimitQuery = 100,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: TenantUsersService = Depends(_service),  # noqa: B008
) -> TenantUserAuditEventListResponse:
    return await svc.list_audit_events(tenant_user_id=tenant_user_id, limit=limit)
