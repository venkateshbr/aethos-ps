"""Pydantic request/response schemas for the Engagements API.

Total_value / billing term money fields: Decimal in Python, str in JSON.
All money output goes through ``app.domain.money.serialise_money`` so the
JSON representation is always two decimal places (bug #93).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.domain.money import serialise_money


class BillingTerms(BaseModel):
    fixed_fee_amount: Decimal | None = None
    milestone_total: Decimal | None = None
    retainer_monthly_amount: Decimal | None = None
    retainer_floor: Decimal | None = None
    retainer_rollover: bool | None = None
    cap_amount: Decimal | None = None
    billing_unit: str | None = Field(default=None, max_length=50)
    unit_label: str | None = Field(default=None, max_length=100)
    unit_quantity: Decimal | None = None
    unit_price: Decimal | None = None

    @field_validator(
        "fixed_fee_amount",
        "milestone_total",
        "retainer_monthly_amount",
        "retainer_floor",
        "cap_amount",
        "unit_quantity",
        "unit_price",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        return Decimal(str(v))


_SERVICE_LINE_VALUES = frozenset(
    {"accounting", "tax", "cosec", "payroll", "advisory", "other"}
)


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
        "mixed",
    ]
    currency: str = Field(default="USD", min_length=3, max_length=3)
    total_value: Decimal | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    rate_card_id: str | None = None
    billing_terms: BillingTerms | None = None
    service_line: str | None = None
    service_catalogue_id: str | None = None  # links to service_catalogue (migration 0033)

    @field_validator("service_line", mode="before")
    @classmethod
    def validate_service_line(cls, v: object) -> str | None:
        if v is None:
            return None
        if str(v) not in _SERVICE_LINE_VALUES:
            raise ValueError(
                f"service_line must be one of {sorted(_SERVICE_LINE_VALUES)}, got {v!r}"
            )
        return str(v)

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
    milestone_total: str | None
    retainer_monthly_amount: str | None
    retainer_floor: str | None
    retainer_rollover: bool
    cap_amount: str | None
    billing_unit: str | None = None
    unit_label: str | None = None
    unit_quantity: str | None = None
    unit_price: str | None = None

    @classmethod
    def from_db(cls, row: dict) -> EngagementBillingTermsResponse:
        return cls(
            fixed_fee_amount=serialise_money(row.get("fixed_fee_amount")),
            milestone_total=serialise_money(row.get("milestone_total")),
            retainer_monthly_amount=serialise_money(row.get("retainer_monthly_amount")),
            retainer_floor=serialise_money(row.get("retainer_floor")),
            retainer_rollover=bool(row.get("retainer_rollover")),
            cap_amount=serialise_money(row.get("cap_amount")),
            billing_unit=row.get("billing_unit"),
            unit_label=row.get("unit_label"),
            unit_quantity=(
                str(row["unit_quantity"])
                if row.get("unit_quantity") is not None
                else None
            ),
            unit_price=serialise_money(row.get("unit_price")),
        )


class EngagementResponse(BaseModel):
    id: str
    tenant_id: str
    client_id: str
    code: str | None = None  # human-readable ENG-0001 (migration 0021)
    name: str
    billing_arrangement: str
    currency: str
    total_value: str | None  # Decimal serialised as string
    status: str
    description: str | None = None
    start_date: str | None
    end_date: str | None
    created_at: str
    billing_terms: EngagementBillingTermsResponse | None = None
    service_line: str | None = None
    rate_card_id: str | None = None
    service_catalogue_id: str | None = None  # migration 0033

    @field_validator("total_value", mode="before")
    @classmethod
    def coerce_total_value_to_str(cls, v: object) -> str | None:
        """Accept Decimal/int/float/str inputs and coerce to canonical 2dp str."""
        return serialise_money(v)  # type: ignore[arg-type]

    @classmethod
    def from_db(
        cls,
        row: dict,
        billing_terms_row: dict | None = None,
    ) -> EngagementResponse:
        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            client_id=str(row["client_id"]),
            code=row.get("code"),
            name=row["name"],
            billing_arrangement=row["billing_arrangement"],
            currency=row["currency"],
            total_value=serialise_money(row.get("total_value")),
            status=row["status"],
            description=row.get("description"),
            start_date=str(row["start_date"]) if row.get("start_date") else None,
            end_date=str(row["end_date"]) if row.get("end_date") else None,
            created_at=str(row["created_at"]),
            billing_terms=(
                EngagementBillingTermsResponse.from_db(billing_terms_row)
                if billing_terms_row
                else None
            ),
            service_line=row.get("service_line"),
            rate_card_id=str(row["rate_card_id"]) if row.get("rate_card_id") else None,
            service_catalogue_id=str(row["service_catalogue_id"]) if row.get("service_catalogue_id") else None,
        )


# ---------------------------------------------------------------------------
# Engagement financial summary
# ---------------------------------------------------------------------------


class EngagementSummary(BaseModel):
    """Financial health snapshot for a single engagement.

    All monetary amounts are Decimal-accurate strings (2 dp).
    """

    engagement_id: str
    engagement_name: str
    total_value: str | None  # fixed-fee baseline; None for pure T&M
    currency: str
    billed_to_date: str       # sum of approved/sent/paid invoice totals
    billed_pct: float | None  # billed_to_date / total_value * 100
    wip_hours: float          # unbilled billable hours
    wip_value: str            # wip_hours x avg rate-card rate
    remaining_value: str | None  # total_value - billed_to_date (fixed fee only)
    invoice_count: int
    last_invoice_date: str | None
