"""Read-only provider webhook audit endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.webhook_events import WebhookEventListResponse
from app.services.webhook_events_service import WebhookEventsService
from supabase import Client

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> WebhookEventsService:
    return WebhookEventsService(db, tenant_id)


@router.get("", response_model=WebhookEventListResponse)
def list_webhook_events(
    provider: str | None = Query(default="stripe", description="Filter by provider"),
    provider_event_id: str | None = Query(default=None, description="Filter by provider event id"),
    event_type: str | None = Query(default=None, description="Filter by provider event type"),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: WebhookEventsService = Depends(_service),  # noqa: B008
) -> WebhookEventListResponse:
    return svc.list_events(
        provider=provider,
        provider_event_id=provider_event_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
