"""Pydantic schemas for immutable financial audit events."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FinancialEventResponse(BaseModel):
    id: str
    tenant_id: str
    event_type: str
    entity_type: str
    entity_id: str
    source_type: str | None = None
    source_id: str | None = None
    actor_user_id: str | None = None
    actor_role: str | None = None
    action: str
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    metadata: dict[str, Any]
    idempotency_key: str | None = None
    previous_event_hash: str | None = None
    event_hash: str
    created_at: str

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> FinancialEventResponse:
        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            event_type=str(row["event_type"]),
            entity_type=str(row["entity_type"]),
            entity_id=str(row["entity_id"]),
            source_type=row.get("source_type"),
            source_id=row.get("source_id"),
            actor_user_id=row.get("actor_user_id"),
            actor_role=row.get("actor_role"),
            action=str(row["action"]),
            before_state=dict(row.get("before_state") or {}),
            after_state=dict(row.get("after_state") or {}),
            metadata=dict(row.get("metadata") or {}),
            idempotency_key=row.get("idempotency_key"),
            previous_event_hash=row.get("previous_event_hash"),
            event_hash=str(row["event_hash"]),
            created_at=str(row["created_at"]),
        )


class FinancialEventListResponse(BaseModel):
    items: list[FinancialEventResponse]
    total: int
