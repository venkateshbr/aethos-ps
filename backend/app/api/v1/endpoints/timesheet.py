"""Timesheet Portal router — self-service endpoints for portal employees.

Gated by ``get_current_employee`` (not ``require_role``): the caller must have
an ``employees`` row linked to their login. Every operation is scoped to that
employee — there is no way to read or write another person's time here.

Routes (issue #134, P4):
  GET    /timesheet/my-projects   — projects (with codes) the employee is on
  GET    /timesheet/entries       — the caller's own entries (date-filterable)
  POST   /timesheet/entries       — log time (status=draft, self)
  PATCH  /timesheet/entries/{id}  — edit own draft/rejected entry
  DELETE /timesheet/entries/{id}  — delete own draft/rejected entry
  POST   /timesheet/submit        — submit a week's drafts for approval
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.employee import get_current_employee
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.timesheet import (
    ApprovalActionResponse,
    ApprovalListResponse,
    ApproveRequest,
    MyProjectListResponse,
    RejectRequest,
    SubmitWeekRequest,
    SubmitWeekResponse,
    TimesheetEntryCreate,
    TimesheetEntryListResponse,
    TimesheetEntryResponse,
    TimesheetEntryUpdate,
)
from app.services.timesheet_approvals_service import TimesheetApprovalsService
from app.services.timesheet_service import TimesheetService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _read_service(
    employee: dict = Depends(get_current_employee),  # noqa: B008
    db: Client = Depends(get_user_rls_client),  # noqa: B008
) -> TimesheetService:
    return TimesheetService(
        db, tenant_id=str(employee["tenant_id"]), employee_id=str(employee["id"])
    )


def _write_service(
    employee: dict = Depends(get_current_employee),  # noqa: B008
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> TimesheetService:
    return TimesheetService(
        db, tenant_id=str(employee["tenant_id"]), employee_id=str(employee["id"])
    )


@router.get("/my-projects", response_model=MyProjectListResponse)
async def my_projects(
    svc: TimesheetService = Depends(_read_service),  # noqa: B008
) -> MyProjectListResponse:
    return await svc.my_projects()


@router.get("/entries", response_model=TimesheetEntryListResponse)
async def list_entries(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    svc: TimesheetService = Depends(_read_service),  # noqa: B008
) -> TimesheetEntryListResponse:
    df = dt = None
    try:
        if date_from:
            df = date.fromisoformat(date_from)
        if date_to:
            dt = date.fromisoformat(date_to)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date: {exc}",
        ) from exc
    return await svc.list_entries(date_from=df, date_to=dt)


@router.post("/entries", response_model=TimesheetEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: TimesheetEntryCreate,
    svc: TimesheetService = Depends(_write_service),  # noqa: B008
) -> TimesheetEntryResponse:
    return await svc.create_entry(payload)


@router.patch("/entries/{id}", response_model=TimesheetEntryResponse)
async def update_entry(
    id: str,
    payload: TimesheetEntryUpdate,
    svc: TimesheetService = Depends(_write_service),  # noqa: B008
) -> TimesheetEntryResponse:
    return await svc.update_entry(id, payload)


@router.delete("/entries/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    id: str,
    svc: TimesheetService = Depends(_write_service),  # noqa: B008
) -> None:
    await svc.delete_entry(id)


@router.post("/submit", response_model=SubmitWeekResponse)
async def submit_week(
    payload: SubmitWeekRequest,
    svc: TimesheetService = Depends(_write_service),  # noqa: B008
) -> SubmitWeekResponse:
    return await svc.submit_week(payload.week_start)


# ---------------------------------------------------------------------------
# Approvals (manager+) — issue #134, P5. These run in the main ERP, gated by
# require_role(manager), NOT get_current_employee.
# ---------------------------------------------------------------------------


def _approvals_read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> TimesheetApprovalsService:
    return TimesheetApprovalsService(db, tenant_id)


def _approvals_write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> TimesheetApprovalsService:
    return TimesheetApprovalsService(db, tenant_id)


@router.get("/approvals", response_model=ApprovalListResponse)
async def list_pending_approvals(
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: TimesheetApprovalsService = Depends(_approvals_read_service),  # noqa: B008
) -> ApprovalListResponse:
    return await svc.list_pending()


@router.post("/approvals/approve", response_model=ApprovalActionResponse)
async def approve_entries(
    payload: ApproveRequest,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: TimesheetApprovalsService = Depends(_approvals_write_service),  # noqa: B008
) -> ApprovalActionResponse:
    return await svc.approve(payload.entry_ids, current_user.user_id)


@router.post("/approvals/reject", response_model=ApprovalActionResponse)
async def reject_entries(
    payload: RejectRequest,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: TimesheetApprovalsService = Depends(_approvals_write_service),  # noqa: B008
) -> ApprovalActionResponse:
    return await svc.reject(payload.entry_ids, payload.reason, current_user.user_id)
