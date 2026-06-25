"""Pydantic request/response models for the Accounting resource.

Manual journal entries use Decimal internally; amounts serialised as strings
in JSON per the Aethos money gate (CLAUDE.md).
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.money import quantise_money

_PERIOD_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")

# ---------------------------------------------------------------------------
# Manual Journal Entry — request models
# ---------------------------------------------------------------------------


class ManualJournalLineIn(BaseModel):
    """A single line (debit or credit) in a manual journal entry request."""

    direction: Literal["DR", "CR"]
    account_id: UUID
    amount: Decimal
    currency: str = "USD"  # ISO 4217
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        result = quantise_money(v)
        if result is None:
            raise ValueError("Amount could not be quantised")
        return result


class ManualJournalEntryIn(BaseModel):
    """Request body for POST /api/v1/accounting/journal-entries."""

    description: str  # Required: short human-readable journal description
    reason: str = Field(
        default="",
        max_length=500,
        validate_default=True,
        description="Business reason/memo explaining why this manual journal is needed.",
    )
    entry_date: date
    lines: list[ManualJournalLineIn]
    reference: str | None = None  # Optional external ref (e.g. "Month-end accrual")

    @model_validator(mode="after")
    def validate_min_lines(self) -> ManualJournalEntryIn:
        if len(self.lines) < 2:
            raise ValueError("Journal entry requires at least 2 lines")
        return self

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        reason = v.strip()
        if len(reason) < 10:
            raise ValueError(
                "Reason is required for manual journal entries and must be at least 10 characters"
            )
        return reason


# ---------------------------------------------------------------------------
# Manual Journal Entry — response models
# ---------------------------------------------------------------------------


class ManualJournalEntryResponse(BaseModel):
    """Response body for a posted manual journal entry."""

    id: str
    entry_number: str
    description: str
    reason: str | None = None
    entry_date: str  # ISO date "YYYY-MM-DD"
    period: str  # "YYYY-MM"
    reference_type: str  # always "manual"
    reference: str | None = None
    created_by: str
    posted_at: str  # ISO datetime
    lines: list[dict]  # serialised journal lines

    @classmethod
    def from_db(cls, je: dict, lines: list[dict]) -> ManualJournalEntryResponse:
        """Build a response from a journal_entry row + its journal_lines rows."""
        return cls(
            id=str(je["id"]),
            entry_number=str(je["entry_number"]),
            description=str(je["description"]),
            reason=str(je["reason"]) if je.get("reason") is not None else None,
            entry_date=str(je["entry_date"]),
            period=str(je["period"]),
            reference_type=str(je["reference_type"]),
            reference=je.get("reference"),
            created_by=str(je["created_by"]),
            posted_at=str(je["posted_at"]),
            lines=[
                {
                    "id": str(line["id"]),
                    "direction": line["direction"],
                    "account_id": str(line["account_id"]),
                    "amount": str(line["amount"]),
                    "currency": line["currency"],
                    "base_amount": str(line["base_amount"]),
                    "description": line.get("description"),
                }
                for line in lines
            ],
        )


class ManualJournalApprovalTaskResponse(BaseModel):
    """Response for a manual journal routed to Inbox approval instead of posting."""

    status: Literal["pending_approval"] = "pending_approval"
    task_id: str | None = None
    suggestion_id: str | None = None
    required_approval_role: str
    approval_policy_reason: str
    total_debits: str
    threshold: str
    message: str


# ---------------------------------------------------------------------------
# Journal Entry list item (used by GET /journal-entries)
# ---------------------------------------------------------------------------


class JournalEntryListItem(BaseModel):
    """Summary row returned by GET /api/v1/accounting/journal-entries."""

    id: str
    entry_number: str
    description: str
    reason: str | None = None
    entry_date: str
    period: str
    reference_type: str
    reference: str | None = None
    created_by: str
    posted_at: str


# ---------------------------------------------------------------------------
# Recurring Journal Templates
# ---------------------------------------------------------------------------


class RecurringJournalTemplateLineIn(BaseModel):
    """One line in a recurring journal template."""

    direction: Literal["DR", "CR"]
    account_id: UUID
    amount: Decimal
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        result = quantise_money(v)
        if result is None:
            raise ValueError("Amount could not be quantised")
        return result


class RecurringJournalTemplateCreate(BaseModel):
    """Request body for creating a recurring journal template."""

    name: str
    description: str | None = None
    schedule_day: int = 31
    start_period: str
    end_period: str | None = None
    currency: str = "USD"
    is_active: bool = True
    lines: list[RecurringJournalTemplateLineIn]

    @field_validator("schedule_day")
    @classmethod
    def validate_schedule_day(cls, v: int) -> int:
        if v < 1 or v > 31:
            raise ValueError("Schedule day must be between 1 and 31")
        return v

    @field_validator("start_period", "end_period")
    @classmethod
    def validate_period(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _PERIOD_PATTERN.match(v):
            raise ValueError("Period must be YYYY-MM")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        currency = v.upper().strip()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("Currency must be a 3-letter ISO code")
        return currency

    @model_validator(mode="after")
    def validate_template(self) -> RecurringJournalTemplateCreate:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Template name is required")
        if self.end_period is not None and self.end_period < self.start_period:
            raise ValueError("End period must be after start period")
        if len(self.lines) < 2:
            raise ValueError("Recurring journal template requires at least 2 lines")

        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for line in self.lines:
            totals[line.direction] += line.amount
        if totals["DR"] != totals["CR"]:
            raise ValueError("Recurring journal template must balance")
        return self


class RecurringJournalTemplateLineResponse(BaseModel):
    id: str
    account_id: str
    direction: Literal["DR", "CR"]
    amount: str
    description: str | None = None
    order_index: int


class RecurringJournalTemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None
    schedule_day: int
    start_period: str
    end_period: str | None
    currency: str
    is_active: bool
    created_by: str | None
    created_at: str | None
    updated_at: str | None
    lines: list[RecurringJournalTemplateLineResponse]
