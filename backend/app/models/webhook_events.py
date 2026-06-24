"""Pydantic schemas for provider webhook audit events."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WebhookEventResponse(BaseModel):
    id: str
    provider: str
    provider_event_id: str
    event_type: str
    tenant_id: str | None = None
    processed_at: str
    created_at: str

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> WebhookEventResponse:
        return cls(
            id=str(row["id"]),
            provider=str(row["provider"]),
            provider_event_id=str(row["provider_event_id"]),
            event_type=str(row["event_type"]),
            tenant_id=str(row["tenant_id"]) if row.get("tenant_id") else None,
            processed_at=str(row["processed_at"]),
            created_at=str(row["created_at"]),
        )


class WebhookEventListResponse(BaseModel):
    items: list[WebhookEventResponse]
    total: int
