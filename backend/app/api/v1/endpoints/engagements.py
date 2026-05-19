"""Engagements router — CRUD + status-update endpoints.

RBAC:
  GET    → any authenticated user (viewer and above)
  POST   → require_role(manager)
  PATCH  /status → require_role(admin)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.engagements import (
    EngagementCreate,
    EngagementResponse,
    EngagementStatusUpdate,
)
from app.services.engagements_service import EngagementService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> EngagementService:
    return EngagementService(db, tenant_id)


@router.get("", response_model=list[EngagementResponse])
async def list_engagements(
    status_filter: str | None = Query(
        default=None, alias="status", description="Filter by engagement status"
    ),
    client_id: str | None = Query(default=None, description="Filter by client ID"),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: EngagementService = Depends(_service),  # noqa: B008
) -> list[EngagementResponse]:
    return await svc.list_engagements(status=status_filter, client_id=client_id)


@router.post("", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(
    payload: EngagementCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: EngagementService = Depends(_service),  # noqa: B008
) -> EngagementResponse:
    return await svc.create_engagement(payload)


@router.get("/{id}", response_model=EngagementResponse)
async def get_engagement(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: EngagementService = Depends(_service),  # noqa: B008
) -> EngagementResponse:
    engagement = await svc.get_engagement(id)
    if engagement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found"
        )
    return engagement


@router.patch("/{id}/status", response_model=EngagementResponse)
async def update_engagement_status(
    id: str,
    payload: EngagementStatusUpdate,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: EngagementService = Depends(_service),  # noqa: B008
) -> EngagementResponse:
    engagement = await svc.update_engagement_status(id, payload.status)
    if engagement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found"
        )
    return engagement
