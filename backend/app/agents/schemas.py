"""Structured output schemas for document-extraction agents.

All agent output types live here so they can be imported by routers,
services, and the suggestion writer without circular imports.

Money fields use Decimal; JSON serialization converts them to strings.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class RateCardHint(BaseModel):
    """A single role/rate pair extracted from an engagement letter."""

    role: str
    rate: Decimal


class EngagementDraft(BaseModel):
    """Output of the engagement_letter_agent."""

    client_name: str = ""
    billing_arrangement: str = "time_and_materials"  # time_and_materials / fixed_fee / retainer / retainer_draw / milestone / capped_tm
    currency: str = "USD"
    total_value: Decimal | None = None
    start_date: str | None = None  # ISO date string
    end_date: str | None = None
    rate_card_hints: list[RateCardHint] = []
    scope_summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    suspected_injection: bool = False


class ProjectExpenseDraft(BaseModel):
    """Output of the expense_extractor_agent."""

    vendor: str
    amount: Decimal
    currency: str = "USD"
    category: str  # meals_and_entertainment / transport / accommodation / software / other
    expense_date: str | None = None
    description: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    suspected_injection: bool = False


class BillDraft(BaseModel):
    """Output of the vendor_invoice_agent."""

    vendor_name: str
    vendor_invoice_number: str | None = None
    currency: str = "USD"
    subtotal: Decimal
    tax_total: Decimal = Decimal("0")
    total: Decimal
    issue_date: str | None = None
    due_date: str | None = None
    lines: list[dict] = []  # {description, amount} dicts
    confidence: float = Field(ge=0.0, le=1.0)
    possible_duplicate: bool = False
    anomaly_detected: bool = False
    suspected_injection: bool = False
