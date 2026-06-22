"""HITL Inbox router.

Endpoints:
  GET    /inbox/tasks                     → list open HITL tasks (paginated)
  GET    /inbox/tasks/{task_id}           → full task detail
  POST   /inbox/tasks/{task_id}/approve   → approve suggestion as-is (manager+)
  POST   /inbox/tasks/{task_id}/approve-with-edits → approve with corrections (manager+)
  POST   /inbox/tasks/{task_id}/reject    → reject suggestion (manager+)
  POST   /inbox/tasks/{task_id}/escalate  → escalate to critical / tenant owner (any auth user)

RBAC:
  read:     any authenticated user
  approve / approve-with-edits / reject: manager and above
  escalate: any authenticated user
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.inbox import (
    ApproveResponse,
    ApproveWithEditsRequest,
    EscalateResponse,
    HitlTaskDetail,
    HitlTaskListResponse,
    RejectRequest,
    RejectResponse,
)
from app.services.inbox_service import InboxService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

_TASK_STATUS_ALIASES = {
    "pending": "open",
}
_TASK_STATUSES = frozenset({"open", "in_progress", "done", "expired"})


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> InboxService:
    return InboxService(db, tenant_id)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


@router.get("/tasks", response_model=HitlTaskListResponse)
async def list_tasks(
    status: str | None = Query("open", description="Task status filter. Use 'all' to see every status."),
    kind: str | None = Query(None, description="Filter by action kind (e.g. create_bill, create_expense)"),
    limit: int = Query(50, ge=1, le=100),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: InboxService = Depends(_service),  # noqa: B008
) -> HitlTaskListResponse:
    status_filter = _normalise_task_status(status)
    return await svc.list_tasks(status_filter=status_filter, kind=kind, limit=limit)


@router.get("/tasks/{task_id}", response_model=HitlTaskDetail)
async def get_task(
    task_id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: InboxService = Depends(_service),  # noqa: B008
) -> HitlTaskDetail:
    task = await svc.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id!r} not found",
        )
    return task


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


@router.post("/tasks/{task_id}/approve", response_model=ApproveResponse)
async def approve_task(
    task_id: str,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: InboxService = Depends(_service),  # noqa: B008
) -> ApproveResponse:
    return await svc.approve(task_id, current_user.user_id)


@router.post("/tasks/{task_id}/approve-with-edits", response_model=ApproveResponse)
async def approve_task_with_edits(
    task_id: str,
    body: ApproveWithEditsRequest,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: InboxService = Depends(_service),  # noqa: B008
) -> ApproveResponse:
    return await svc.approve_with_edits(task_id, body.corrected_payload, current_user.user_id)


@router.post("/tasks/{task_id}/reject", response_model=RejectResponse)
async def reject_task(
    task_id: str,
    body: RejectRequest,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: InboxService = Depends(_service),  # noqa: B008
) -> RejectResponse:
    return await svc.reject(task_id, body.reason, current_user.user_id)


@router.post("/tasks/{task_id}/escalate", response_model=EscalateResponse)
async def escalate_task(
    task_id: str,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: InboxService = Depends(_service),  # noqa: B008
) -> EscalateResponse:
    return await svc.escalate(task_id, current_user.user_id)


def _normalise_task_status(raw_status: str | None) -> str | None:
    if raw_status is None:
        return None
    status_value = raw_status.strip().lower()
    if status_value == "all":
        return None

    status_value = _TASK_STATUS_ALIASES.get(status_value, status_value)
    if status_value not in _TASK_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported task status: {raw_status!r}",
        )
    return status_value
