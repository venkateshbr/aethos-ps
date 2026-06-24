"""Pydantic request/response schemas for the Projects API.

Budget is Decimal in Python and serialised as a 2dp str in JSON via
``app.domain.money.serialise_money`` (bug #93).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.domain.money import serialise_money

ProjectStatus = Literal["planning", "active", "on_hold", "completed", "cancelled"]


class ProjectCreate(BaseModel):
    engagement_id: str
    name: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    # None → inherit from the parent engagement at create time (#160). The
    # frontend create form has no currency field, so callers that don't ship
    # one get the engagement's currency. Explicit 3-letter ISO is still
    # accepted for callers that need to override.
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    budget: Decimal | None = None
    budget_hours: Decimal | None = Field(
        default=None,
        validation_alias=AliasChoices("budget_hours", "estimated_hours"),
    )
    status: ProjectStatus = "planning"
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("budget", "budget_hours", mode="before")
    @classmethod
    def coerce_decimal(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        return Decimal(str(v))


class ProjectResponse(BaseModel):
    id: str
    tenant_id: str
    engagement_id: str
    code: str | None = None  # human-readable PRJ-0001 (migration 0021)
    name: str
    description: str | None = None
    currency: str
    budget: str | None  # Decimal serialised as string
    budget_hours: str | None = None
    status: str
    start_date: date | None = None
    end_date: date | None = None
    created_at: str

    @classmethod
    def from_db(cls, row: dict) -> ProjectResponse:
        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            engagement_id=str(row["engagement_id"]),
            code=row.get("code"),
            name=row["name"],
            description=row.get("description"),
            currency=row["currency"],
            budget=serialise_money(row.get("budget")),
            budget_hours=str(row["budget_hours"]) if row.get("budget_hours") is not None else None,
            status=row["status"],
            start_date=row.get("start_date"),
            end_date=row.get("end_date"),
            created_at=str(row["created_at"]),
        )


PhaseStatus = Literal["planning", "active", "completed", "cancelled"]


class ProjectPhaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    status: PhaseStatus = "planning"
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None
    order_index: int = Field(default=0, ge=0)
    deliverable_name: str | None = Field(default=None, max_length=300)
    deliverable_acceptance_criteria: str | None = Field(default=None, max_length=2000)
    percent_complete: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    revenue_recognition_amount: Decimal | None = Field(default=None, ge=0)

    @field_validator(
        "budget",
        "percent_complete",
        "revenue_recognition_amount",
        mode="before",
    )
    @classmethod
    def coerce_phase_decimal(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        return Decimal(str(v))


class ProjectPhaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    status: PhaseStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None
    order_index: int | None = Field(default=None, ge=0)
    deliverable_name: str | None = Field(default=None, max_length=300)
    deliverable_acceptance_criteria: str | None = Field(default=None, max_length=2000)
    percent_complete: Decimal | None = Field(default=None, ge=0, le=100)
    revenue_recognition_amount: Decimal | None = Field(default=None, ge=0)

    @field_validator(
        "budget",
        "percent_complete",
        "revenue_recognition_amount",
        mode="before",
    )
    @classmethod
    def coerce_optional_phase_decimal(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        return Decimal(str(v))


class ProjectPhaseResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    name: str
    description: str | None = None
    status: str
    start_date: date | None = None
    end_date: date | None = None
    budget: str | None = None
    order_index: int
    deliverable_name: str | None = None
    deliverable_acceptance_criteria: str | None = None
    percent_complete: str
    revenue_recognition_amount: str | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_db(cls, row: dict) -> ProjectPhaseResponse:
        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            project_id=str(row["project_id"]),
            name=row["name"],
            description=row.get("description"),
            status=row.get("status", "planning"),
            start_date=row.get("start_date"),
            end_date=row.get("end_date"),
            budget=serialise_money(row.get("budget")),
            order_index=int(row.get("order_index") or 0),
            deliverable_name=row.get("deliverable_name"),
            deliverable_acceptance_criteria=row.get("deliverable_acceptance_criteria"),
            percent_complete=str(row.get("percent_complete") or "0"),
            revenue_recognition_amount=serialise_money(
                row.get("revenue_recognition_amount")
            ),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
