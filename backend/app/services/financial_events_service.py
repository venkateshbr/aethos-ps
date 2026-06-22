"""Read service for immutable financial audit events."""

from __future__ import annotations

from app.models.financial_events import FinancialEventListResponse, FinancialEventResponse
from supabase import Client


class FinancialEventsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def list_events(
        self,
        *,
        event_type: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FinancialEventListResponse:
        query = (
            self.db.table("financial_events")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .order("created_at", desc=True)
            .limit(min(limit, 250))
            .offset(offset)
        )
        if event_type:
            query = query.eq("event_type", event_type)
        if entity_type:
            query = query.eq("entity_type", entity_type)
        if entity_id:
            query = query.eq("entity_id", entity_id)

        rows = query.execute().data or []
        items = [FinancialEventResponse.from_db(row) for row in rows]
        return FinancialEventListResponse(items=items, total=len(items))
