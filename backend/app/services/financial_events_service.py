"""Read service for immutable financial audit events."""

from __future__ import annotations

import csv
import io
import json

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

    def export_events_csv(
        self,
        *,
        event_type: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 1000,
    ) -> bytes:
        events = self.list_events(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=min(limit, 1000),
            offset=0,
        ).items
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "created_at",
                "event_type",
                "entity_type",
                "entity_id",
                "action",
                "actor_user_id",
                "source_type",
                "source_id",
                "idempotency_key",
                "previous_event_hash",
                "event_hash",
                "metadata_json",
                "before_state_json",
                "after_state_json",
            ]
        )
        for event in events:
            writer.writerow(
                [
                    event.created_at,
                    event.event_type,
                    event.entity_type,
                    event.entity_id,
                    event.action,
                    event.actor_user_id or "",
                    event.source_type or "",
                    event.source_id or "",
                    event.idempotency_key or "",
                    event.previous_event_hash or "",
                    event.event_hash,
                    _stable_json(event.metadata),
                    _stable_json(event.before_state),
                    _stable_json(event.after_state),
                ]
            )
        return output.getvalue().encode("utf-8")


def _stable_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
