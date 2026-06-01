"""Pydantic request/response schemas for the Projects API.

Budget is Decimal in Python and serialised as a 2dp str in JSON via
``app.domain.money.serialise_money`` (bug #93).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.money import serialise_money


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
    code: str | None = None  # human-readable PRJ-0001 (migration 0021)
    name: str
    currency: str
    budget: str | None  # Decimal serialised as string
    status: str
    created_at: str

    @classmethod
    def from_db(cls, row: dict) -> ProjectResponse:
        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            engagement_id=str(row["engagement_id"]),
            code=row.get("code"),
            name=row["name"],
            currency=row["currency"],
            budget=serialise_money(row.get("budget")),
            status=row["status"],
            created_at=str(row["created_at"]),
        )
