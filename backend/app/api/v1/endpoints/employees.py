"""Employees router — CRUD endpoints for the people master (issue #134, Phase 1).

RBAC:
  GET    → any authenticated user (viewer and above)
  POST   → manager and above
  PATCH  → manager and above
  DELETE → manager and above (soft delete only)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.employees import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employees_service import EmployeesService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> EmployeesService:
    return EmployeesService(db, tenant_id)


@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, description="Match name or email"),
    limit: int = Query(default=200, ge=1, le=500),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: EmployeesService = Depends(_service),  # noqa: B008
) -> EmployeeListResponse:
    return await svc.list_employees(status_filter=status_filter, search=search, limit=limit)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: EmployeesService = Depends(_service),  # noqa: B008
) -> EmployeeResponse:
    return await svc.create_employee(payload)


@router.get("/{id}", response_model=EmployeeResponse)
async def get_employee(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: EmployeesService = Depends(_service),  # noqa: B008
) -> EmployeeResponse:
    emp = await svc.get_employee(id)
    if emp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return emp


@router.patch("/{id}", response_model=EmployeeResponse)
async def update_employee(
    id: str,
    payload: EmployeeUpdate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: EmployeesService = Depends(_service),  # noqa: B008
) -> EmployeeResponse:
    return await svc.update_employee(id, payload)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    id: str,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: EmployeesService = Depends(_service),  # noqa: B008
) -> None:
    await svc.delete_employee(id)
