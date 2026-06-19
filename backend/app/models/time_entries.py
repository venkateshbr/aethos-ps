"""Pydantic request/response models for the time_entries resource.

Money / hours rules:
- hours uses Decimal (never float) — precision matters for billing.
- hours serialised as string in JSON responses (consistent with other Decimal fields).
- hours must be > 0 and <= 24 per the DB CHECK constraint.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# NUMERIC(15,2) maximum — enforced on Decimal fields (#194)
_NUMERIC_15_2_MAX = Decimal("999999999999999.99")


class TimeEntryCreate(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=36)
    employee_id: str = Field(..., min_length=1, max_length=36)
    date: date
    hours: Decimal = Field(..., gt=0, le=24, description="Billable hours (> 0, <= 24)")
    description: str = Field(default="", max_length=1000)
    billable: bool = True
    phase_id: str | None = Field(default=None, max_length=36)
    timezone: str = Field(
        default="UTC",
        description="IANA timezone string (e.g. 'America/New_York'). Stored with the entry for display conversion.",
    )

    @field_validator("hours", mode="before")
    @classmethod
    def check_precision(cls, v: object) -> Decimal:
        d = Decimal(str(v))
        if d > _NUMERIC_15_2_MAX:
            raise ValueError(f"Amount exceeds maximum allowed value ({_NUMERIC_15_2_MAX})")
        return d

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("timezone must be a non-empty string")
        return v


class TimeEntryUpdate(BaseModel):
    hours: Decimal | None = Field(default=None, gt=0, le=24)
    description: str | None = Field(default=None, max_length=1000)
    billable: bool | None = None


class TimeEntryResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    employee_id: str
    date: str
    hours: str  # Decimal serialised as string — matches API contract
    description: str
    billable: bool
    billing_status: str
    status: str = "approved"  # approval lifecycle (migration 0021)
    approved_by: str | None = None
    approved_at: str | None = None
    phase_id: str | None = None
    timezone: str = "UTC"  # IANA timezone string for display conversion (#190)
    created_at: str
    updated_at: str | None = None

    @field_validator("hours", mode="before")
    @classmethod
    def decimal_to_str(cls, v: object) -> str:
        """Coerce Decimal / float / int from the DB row to a string."""
        if v is None:
            return "0"
        return str(v)

    @field_validator("date", mode="before")
    @classmethod
    def date_to_str(cls, v: object) -> str:
        if isinstance(v, date):
            return v.isoformat()
        return str(v)


class TimeEntryListResponse(BaseModel):
    items: list[TimeEntryResponse]
    total: int
