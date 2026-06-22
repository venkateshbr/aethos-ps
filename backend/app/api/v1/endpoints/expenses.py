"""Project expense endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.expenses import ExpenseCreate, ExpenseResponse
from app.services.expenses_service import ExpensesService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

PROJECT_ID_QUERY = Query(None, description="Optional project_id filter")
DATE_FROM_QUERY = Query(None, description="Inclusive expense_date lower bound")
DATE_TO_QUERY = Query(None, description="Inclusive expense_date upper bound")


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ExpensesService:
    return ExpensesService(db=db, tenant_id=tenant_id)


@router.get("", response_model=list[ExpenseResponse])
async def list_expenses(
    project_id: str | None = PROJECT_ID_QUERY,
    date_from: str | None = DATE_FROM_QUERY,
    date_to: str | None = DATE_TO_QUERY,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ExpensesService = Depends(_service),  # noqa: B008
) -> list[ExpenseResponse]:
    """List project expenses for the current tenant."""
    try:
        return await svc.list_expenses(
            project_id=project_id,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as exc:
        logger.exception("Failed to list expenses")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ExpensesService = Depends(_service),  # noqa: B008
) -> ExpenseResponse:
    """Create a project expense via the top-level endpoint.

    The underlying table requires ``project_id``. The frontend generally uses
    the project-scoped route once a project is selected; this top-level variant
    exists for API consumers that include ``project_id`` in the payload.
    """
    if not payload.project_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="project_id is required for expenses",
        )
    return await svc.create_expense(payload.project_id, payload)
