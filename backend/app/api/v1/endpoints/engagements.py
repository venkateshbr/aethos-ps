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


@router.post("/{id}/draft-invoice")
async def draft_invoice_endpoint(
    id: str,
    period_start: str | None = Query(
        default=None, description="Period start date YYYY-MM-DD"
    ),
    period_end: str | None = Query(
        default=None, description="Period end date YYYY-MM-DD"
    ),
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> dict:
    """Draft an invoice for an engagement based on its billing arrangement.

    Calculates all unbilled items (time entries, expenses, milestones) and
    applies the tenant's default tax rate. Returns an InvoiceDraft — this
    does NOT create an invoice record; use POST /invoices to persist.

    Requires member role or above.
    """
    from datetime import date as _date

    from app.agents.base import AgentDeps
    from app.agents.invoice_drafter_agent import draft_invoice

    deps = AgentDeps(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        db=db,
    )

    ps: _date | None = None
    pe: _date | None = None
    try:
        if period_start:
            ps = _date.fromisoformat(period_start)
        if period_end:
            pe = _date.fromisoformat(period_end)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date format: {exc}",
        ) from exc

    try:
        invoice_draft = draft_invoice(id, deps, ps, pe)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("draft_invoice failed for engagement %s tenant %s", id, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    return invoice_draft.model_dump(mode="json")
