"""Read-only financial audit event endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.auth import CurrentUser
from app.core.db import get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.financial_events import FinancialEventListResponse
from app.services.financial_events_service import FinancialEventsService
from supabase import Client

router = APIRouter()


def _service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> FinancialEventsService:
    return FinancialEventsService(db, tenant_id)


@router.get("", response_model=FinancialEventListResponse)
def list_financial_events(
    event_type: str | None = Query(default=None, description="Filter by event type"),
    entity_type: str | None = Query(default=None, description="Filter by entity type"),
    entity_id: str | None = Query(default=None, description="Filter by entity id"),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: FinancialEventsService = Depends(_service),  # noqa: B008
) -> FinancialEventListResponse:
    return svc.list_events(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )


@router.get("/export")
def export_financial_events(
    event_type: str | None = Query(default=None, description="Filter by event type"),
    entity_type: str | None = Query(default=None, description="Filter by entity type"),
    entity_id: str | None = Query(default=None, description="Filter by entity id"),
    limit: int = Query(default=1000, ge=1, le=1000),
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: FinancialEventsService = Depends(_service),  # noqa: B008
) -> Response:
    content = svc.export_events_csv(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=financial-events.csv"},
    )
