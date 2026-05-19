"""Pydantic request/response schemas for the Engagements API.

Total_value / billing term money fields: Decimal in Python, str in JSON.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BillingTerms(BaseModel):
    fixed_fee_amount: Decimal | None = None
    retainer_monthly_amount: Decimal | None = None
    retainer_floor: Decimal | None = None
    cap_amount: Decimal | None = None

    @field_validator("fixed_fee_amount", "retainer_monthly_amount", "retainer_floor", "cap_amount", mode="before")
    @classmethod
    def coerce_decimal(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        return Decimal(str(v))


class EngagementCreate(BaseModel):
    client_id: str
    name: str = Field(..., min_length=1, max_length=300)
    billing_arrangement: Literal[
        "time_and_materials",
        "fixed_fee",
        "retainer",
        "retainer_draw",
        "milestone",
        "capped_tm",
    ]
    currency: str = Field(default="USD", min_length=3, max_length=3)
    total_value: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    rate_card_id: str | None = None
    billing_terms: BillingTerms | None = None

    @field_validator("total_value", mode="before")
    @classmethod
    def coerce_total_value(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        return Decimal(str(v))


class EngagementStatusUpdate(BaseModel):
    status: Literal["active", "on_hold", "completed", "cancelled"]


class EngagementBillingTermsResponse(BaseModel):
    fixed_fee_amount: str | None
    retainer_monthly_amount: str | None
    retainer_floor: str | None
    cap_amount: str | None

    @classmethod
    def from_db(cls, row: dict) -> EngagementBillingTermsResponse:
        def _str_or_none(v: object) -> str | None:
            return str(Decimal(str(v))) if v is not None else None

        return cls(
            fixed_fee_amount=_str_or_none(row.get("fixed_fee_amount")),
            retainer_monthly_amount=_str_or_none(row.get("retainer_monthly_amount")),
            retainer_floor=_str_or_none(row.get("retainer_floor")),
            cap_amount=_str_or_none(row.get("cap_amount")),
        )


class EngagementResponse(BaseModel):
    id: str
    tenant_id: str
    client_id: str
    name: str
    billing_arrangement: str
    currency: str
    total_value: str | None  # Decimal serialised as string
    status: str
    start_date: str | None
    end_date: str | None
    created_at: str
    billing_terms: EngagementBillingTermsResponse | None = None

    @field_validator("total_value", mode="before")
    @classmethod
    def coerce_total_value_to_str(cls, v: object) -> str | None:
        """Accept Decimal/int/float inputs and coerce to canonical str."""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        return str(Decimal(str(v)))

    @classmethod
    def from_db(
        cls,
        row: dict,
        billing_terms_row: dict | None = None,
    ) -> EngagementResponse:
        tv = row.get("total_value")
        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            client_id=str(row["client_id"]),
            name=row["name"],
            billing_arrangement=row["billing_arrangement"],
            currency=row["currency"],
            total_value=str(Decimal(str(tv))) if tv is not None else None,
            status=row["status"],
            start_date=str(row["start_date"]) if row.get("start_date") else None,
            end_date=str(row["end_date"]) if row.get("end_date") else None,
            created_at=str(row["created_at"]),
            billing_terms=(
                EngagementBillingTermsResponse.from_db(billing_terms_row)
                if billing_terms_row
                else None
            ),
        )
