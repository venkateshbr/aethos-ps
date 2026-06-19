"""Pydantic request/response models for billing_runs."""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel


class BillingRunCreate(BaseModel):
    name: str
    period_start: date
    period_end: date
    engagement_filter: dict[str, Any] | None = None


class BillingRunResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    period_start: str
    period_end: str
    status: str
    created_by_agent: str | None
    summary: dict[str, Any] | None
    created_at: str

    @classmethod
    def from_db(cls, row: dict) -> BillingRunResponse:
        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            name=row["name"],
            period_start=str(row["period_start"]),
            period_end=str(row["period_end"]),
            status=row["status"],
            created_by_agent=row.get("created_by_agent"),
            summary=row.get("summary"),
            created_at=str(row["created_at"]),
        )
