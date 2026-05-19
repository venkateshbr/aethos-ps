"""Pydantic request/response schemas for the Projects API.

Budget is Decimal in Python and serialised as str in JSON.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    engagement_id: str
    name: str = Field(..., min_length=1, max_length=300)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    budget: Decimal | None = None

    @field_validator("budget", mode="before")
    @classmethod
    def coerce_budget(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        return Decimal(str(v))


class ProjectResponse(BaseModel):
    id: str
    tenant_id: str
    engagement_id: str
    name: str
    currency: str
    budget: str | None  # Decimal serialised as string
    status: str
    created_at: str

    @classmethod
    def from_db(cls, row: dict) -> ProjectResponse:
        budget = row.get("budget")
        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            engagement_id=str(row["engagement_id"]),
            name=row["name"],
            currency=row["currency"],
            budget=str(Decimal(str(budget))) if budget is not None else None,
            status=row["status"],
            created_at=str(row["created_at"]),
        )
