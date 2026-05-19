"""Projects router — list (by engagement), create, get endpoints.

RBAC:
  GET  → any authenticated user (viewer and above)
  POST → require_role(manager)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.projects import ProjectCreate, ProjectResponse
from app.services.projects_service import ProjectService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ProjectService:
    return ProjectService(db, tenant_id)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    engagement_id: str = Query(..., description="Filter projects by engagement (required)"),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ProjectService = Depends(_service),  # noqa: B008
) -> list[ProjectResponse]:
    return await svc.list_projects(engagement_id)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ProjectService = Depends(_service),  # noqa: B008
) -> ProjectResponse:
    return await svc.create_project(payload)


@router.get("/{id}", response_model=ProjectResponse)
async def get_project(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ProjectService = Depends(_service),  # noqa: B008
) -> ProjectResponse:
    project = await svc.get_project(id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
