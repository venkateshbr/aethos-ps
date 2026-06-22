"""Time entries router — CRUD endpoints.

RBAC:
  GET    → any authenticated user (viewer and above)
  POST   → member and above
  PATCH  → member and above (cannot update billed entries)
  DELETE → manager and above (soft delete only)
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.time_entries import (
    TimeEntryCreate,
    TimeEntryListResponse,
    TimeEntryResponse,
    TimeEntryUpdate,
)
from app.services.time_entries_service import TimeEntriesService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

ProjectIdQuery = Annotated[str | None, Query(description="Filter by project ID")]
EmployeeIdQuery = Annotated[str | None, Query(description="Filter by employee ID")]
DateFromQuery = Annotated[str | None, Query(description="Filter from date YYYY-MM-DD")]
DateToQuery = Annotated[str | None, Query(description="Filter to date YYYY-MM-DD")]
BillingStatusQuery = Annotated[
    str | None,
    Query(description="Filter by billing status: unbilled | billed | non_billable"),
]
LimitQuery = Annotated[int, Query(ge=1, le=500)]


def _read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> TimeEntriesService:
    return TimeEntriesService(db, tenant_id)


def _write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> TimeEntriesService:
    return TimeEntriesService(db, tenant_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=TimeEntryListResponse)
async def list_time_entries(
    project_id: ProjectIdQuery = None,
    employee_id: EmployeeIdQuery = None,
    date_from: DateFromQuery = None,
    date_to: DateToQuery = None,
    billing_status: BillingStatusQuery = None,
    limit: LimitQuery = 100,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: TimeEntriesService = Depends(_read_service),  # noqa: B008
) -> TimeEntryListResponse:
    df: date | None = None
    dt: date | None = None
    try:
        if date_from:
            df = date.fromisoformat(date_from)
        if date_to:
            dt = date.fromisoformat(date_to)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format — expected YYYY-MM-DD",
        ) from exc

    return await svc.list_entries(
        project_id=project_id,
        employee_id=employee_id,
        date_from=df,
        date_to=dt,
        billing_status=billing_status,
        limit=limit,
    )


@router.post("", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    payload: TimeEntryCreate,
    current_user: CurrentUser = require_role(UserRole.member),  # noqa: B008
    svc: TimeEntriesService = Depends(_write_service),  # noqa: B008
) -> TimeEntryResponse:
    return await svc.create_entry(payload, approved_by=current_user.user_id)


@router.get("/{id}", response_model=TimeEntryResponse)
async def get_time_entry(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: TimeEntriesService = Depends(_read_service),  # noqa: B008
) -> TimeEntryResponse:
    entry = await svc.get_entry(id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found",
        )
    return entry


@router.patch("/{id}", response_model=TimeEntryResponse)
async def update_time_entry(
    id: str,
    payload: TimeEntryUpdate,
    _current_user: CurrentUser = require_role(UserRole.member),  # noqa: B008
    svc: TimeEntriesService = Depends(_write_service),  # noqa: B008
) -> TimeEntryResponse:
    return await svc.update_entry(id, payload)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    id: str,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: TimeEntriesService = Depends(_write_service),  # noqa: B008
) -> None:
    await svc.delete_entry(id)
