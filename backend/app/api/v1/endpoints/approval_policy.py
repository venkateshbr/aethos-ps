"""Tenant approval policy endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.approval_policy import ApprovalPolicyResponse, ApprovalPolicyUpsert
from app.services.approval_policy_settings_service import ApprovalPolicySettingsService
from supabase import Client

router = APIRouter()


def _read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ApprovalPolicySettingsService:
    return ApprovalPolicySettingsService(db, tenant_id)


def _write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ApprovalPolicySettingsService:
    return ApprovalPolicySettingsService(db, tenant_id)


@router.get("/effective", response_model=ApprovalPolicyResponse)
async def get_effective_approval_policy(
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ApprovalPolicySettingsService = Depends(_read_service),  # noqa: B008
) -> ApprovalPolicyResponse:
    """Return the tenant approval policy, falling back to safe defaults."""
    return await svc.get_effective_policy()


@router.put("/default", response_model=ApprovalPolicyResponse)
async def upsert_default_approval_policy(
    payload: ApprovalPolicyUpsert,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: ApprovalPolicySettingsService = Depends(_write_service),  # noqa: B008
) -> ApprovalPolicyResponse:
    """Create or replace the tenant approval policy."""
    return await svc.upsert_policy(payload)
