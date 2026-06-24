"""Structured output schemas for document-extraction agents.

All agent output types live here so they can be imported by routers,
services, and the suggestion writer without circular imports.

Money fields use Decimal; JSON serialization converts them to strings.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class _DropNoneForDefaults(BaseModel):
    """Base that drops explicit ``null`` values for fields that have a default.

    LLMs frequently return ``"client_name": null`` rather than omitting the key.
    For a field typed ``str`` (not ``str | None``) that would raise a
    ValidationError and, in the extraction worker, nuke the entire draft to a
    0%-confidence empty result (#146). Stripping ``None`` for fields that carry
    a non-None default lets the default apply instead — a missing field degrades
    that one field, not the whole extraction.
    """

    @model_validator(mode="before")
    @classmethod
    def _strip_none_with_defaults(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for name, field in cls.model_fields.items():
            if cleaned.get(name) is None and field.default is not None and field.is_required() is False:
                cleaned.pop(name, None)
        return cleaned


class RateCardHint(BaseModel):
    """A single role/rate pair extracted from an engagement letter."""

    role: str
    rate: Decimal


class EngagementDraft(_DropNoneForDefaults):
    """Output of the engagement_letter_agent."""

    client_name: str = ""
    engagement_name: str | None = None
    billing_arrangement: str = "time_and_materials"  # time_and_materials / fixed_fee / retainer / retainer_draw / milestone / capped_tm
    currency: str = "USD"
    total_value: Decimal | None = None
    start_date: str | None = None  # ISO date string
    end_date: str | None = None
    first_project_name: str | None = None
    first_project_description: str | None = None
    rate_card_hints: list[RateCardHint] = []
    scope_summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    suspected_injection: bool = False


class ProjectExpenseDraft(_DropNoneForDefaults):
    """Output of the expense_extractor_agent."""

    vendor: str
    amount: Decimal
    currency: str = "USD"
    category: str  # meals_and_entertainment / transport / accommodation / software / other
    expense_date: str | None = None
    description: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    suspected_injection: bool = False


class BillDraft(_DropNoneForDefaults):
    """Output of the vendor_invoice_agent."""

    vendor_name: str
    vendor_invoice_number: str | None = None
    vendor_registration_number: str | None = None  # VAT/ABN/EIN/GST extracted from bill
    vendor_address: str | None = None  # raw address text extracted from bill
    vendor_payment_terms_days: int | None = None  # extracted from bill text (e.g. "Net 30")
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
    tax_id_warnings: list[str] = []  # format / cross-check warnings (non-blocking)


class VendorMatchResult(BaseModel):
    """Output of the vendor identity resolution step inside vendor_invoice_agent.

    ``matched_client_id``: UUID of the existing client/vendor if a match was found,
    else None (agent suggests creating a new vendor).
    ``confidence``: 0.0-1.0.  >=0.95 -> auto-link candidate; 0.70-0.90 -> HITL.
    ``match_reason``: human-readable explanation for the suggestion card.
    """

    matched_client_id: UUID | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    match_reason: str


class GLSuggestion(BaseModel):
    """GL account suggestion for a single bill line item.

    ``account_id``: UUID of the suggested account in the tenant's COA.
    ``account_code``: display code (e.g. "5100").
    ``account_name``: display name (e.g. "Software & SaaS").
    ``confidence``: 0.0-1.0.  <0.75 -> show but don't pre-select; >0.90 -> pre-select.
    """

    account_id: UUID
    account_code: str
    account_name: str
    confidence: float = Field(ge=0.0, le=1.0)
