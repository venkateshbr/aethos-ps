"""Tenant AI runtime/model settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.ai_settings import AiSettingsResponse, AiSettingsUpsert
from app.services.ai_settings_service import AiSettingsService
from supabase import Client

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> AiSettingsService:
    return AiSettingsService(db, tenant_id)


@router.get("/effective", response_model=AiSettingsResponse)
async def get_effective_ai_settings(
    _current_user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
    svc: AiSettingsService = Depends(_service),  # noqa: B008
) -> AiSettingsResponse:
    """Return tenant AI settings, falling back to deployment defaults."""
    return await svc.get_effective_settings()


@router.put("/default", response_model=AiSettingsResponse)
async def upsert_ai_settings(
    payload: AiSettingsUpsert,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: AiSettingsService = Depends(_service),  # noqa: B008
) -> AiSettingsResponse:
    """Create or replace tenant AI runtime/model settings."""
    return await svc.upsert_settings(payload)
