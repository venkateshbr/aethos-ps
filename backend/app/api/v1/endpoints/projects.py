"""Projects router — list (by engagement or tenant-wide), create, get endpoints.

RBAC:
  GET  → any authenticated user (viewer and above)
  POST → require_role(manager)
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.assignments import (
    AssignmentCreate,
    AssignmentListResponse,
    AssignmentResponse,
)
from app.models.expenses import ExpenseCreate, ExpenseResponse
from app.models.projects import ProjectCreate, ProjectResponse
from app.services.assignments_service import AssignmentsService
from app.services.expenses_service import ExpensesService
from app.services.projects_service import ProjectService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

EngagementIdQuery = Annotated[
    str | None,
    Query(
        description=(
            "Optional filter — when omitted, returns every project in the "
            "current tenant (subject to RLS)."
        ),
    ),
]
LimitQuery = Annotated[int, Query(ge=1, le=500, description="Max rows to return")]
OffsetQuery = Annotated[int, Query(ge=0, description="Pagination offset")]


def _read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ProjectService:
    return ProjectService(db, tenant_id)


def _write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ProjectService:
    return ProjectService(db, tenant_id)


def _assignments_read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> AssignmentsService:
    return AssignmentsService(db, tenant_id)


def _assignments_write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> AssignmentsService:
    return AssignmentsService(db, tenant_id)


def _expenses_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ExpensesService:
    return ExpensesService(db, tenant_id)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    engagement_id: EngagementIdQuery = None,
    limit: LimitQuery = 100,
    offset: OffsetQuery = 0,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ProjectService = Depends(_read_service),  # noqa: B008
) -> list[ProjectResponse]:
    # Bug #91: engagement_id is now optional. When None we list every project
    # in the tenant (RLS still scopes by tenant_id).
    return await svc.list_projects(engagement_id=engagement_id, limit=limit, offset=offset)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ProjectService = Depends(_write_service),  # noqa: B008
) -> ProjectResponse:
    return await svc.create_project(payload)


@router.get("/{id}", response_model=ProjectResponse)
async def get_project(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ProjectService = Depends(_read_service),  # noqa: B008
) -> ProjectResponse:
    project = await svc.get_project(id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    id: str,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ProjectService = Depends(_write_service),  # noqa: B008
) -> None:
    """Soft-delete a project. Returns 409 if unbilled time entries exist."""
    await svc.delete_project(id)


# ---------------------------------------------------------------------------
# Project assignments (issue #134, Phase 2) — the project "team".
# ---------------------------------------------------------------------------


@router.get("/{id}/assignments", response_model=AssignmentListResponse)
async def list_assignments(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: AssignmentsService = Depends(_assignments_read_service),  # noqa: B008
) -> AssignmentListResponse:
    return await svc.list_for_project(id)


@router.post(
    "/{id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    id: str,
    payload: AssignmentCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: AssignmentsService = Depends(_assignments_write_service),  # noqa: B008
) -> AssignmentResponse:
    return await svc.create(id, payload)


@router.delete(
    "/{id}/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_assignment(
    id: str,
    assignment_id: str,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: AssignmentsService = Depends(_assignments_write_service),  # noqa: B008
) -> None:
    await svc.delete(id, assignment_id)


@router.post(
    "/{id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_expense(
    id: str,
    payload: ExpenseCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ExpensesService = Depends(_expenses_service),  # noqa: B008
) -> ExpenseResponse:
    """Create a project-scoped expense."""
    return await svc.create_expense(id, payload)
