"""Read service for tenant-scoped provider webhook audit events."""

from __future__ import annotations

from app.models.webhook_events import WebhookEventListResponse, WebhookEventResponse
from supabase import Client


class WebhookEventsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def list_events(
        self,
        *,
        provider: str | None = "stripe",
        provider_event_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> WebhookEventListResponse:
        query = (
            self.db.table("webhook_events")
            .select("id,provider,provider_event_id,event_type,tenant_id,processed_at,created_at")
            .eq("tenant_id", self.tenant_id)
            .order("processed_at", desc=True)
            .limit(min(limit, 250))
            .offset(offset)
        )
        if provider:
            query = query.eq("provider", provider)
        if provider_event_id:
            query = query.eq("provider_event_id", provider_event_id)
        if event_type:
            query = query.eq("event_type", event_type)

        rows = query.execute().data or []
        items = [WebhookEventResponse.from_db(row) for row in rows]
        return WebhookEventListResponse(items=items, total=len(items))
