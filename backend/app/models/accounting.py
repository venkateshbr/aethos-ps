"""Pydantic request/response models for the Accounting resource.

Manual journal entries use Decimal internally; amounts serialised as strings
in JSON per the Aethos money gate (CLAUDE.md).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from app.domain.money import quantise_money


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

    description: str  # Required: human-readable reason for the manual entry
    entry_date: date
    lines: list[ManualJournalLineIn]
    reference: str | None = None  # Optional external ref (e.g. "Month-end accrual")

    @model_validator(mode="after")
    def validate_min_lines(self) -> "ManualJournalEntryIn":
        if len(self.lines) < 2:
            raise ValueError("Journal entry requires at least 2 lines")
        return self


# ---------------------------------------------------------------------------
# Manual Journal Entry — response models
# ---------------------------------------------------------------------------


class ManualJournalEntryResponse(BaseModel):
    """Response body for a posted manual journal entry."""

    id: str
    entry_number: str
    description: str
    entry_date: str  # ISO date "YYYY-MM-DD"
    period: str  # "YYYY-MM"
    reference_type: str  # always "manual"
    reference: str | None = None
    created_by: str
    posted_at: str  # ISO datetime
    lines: list[dict]  # serialised journal lines

    @classmethod
    def from_db(cls, je: dict, lines: list[dict]) -> "ManualJournalEntryResponse":
        """Build a response from a journal_entry row + its journal_lines rows."""
        return cls(
            id=str(je["id"]),
            entry_number=str(je["entry_number"]),
            description=str(je["description"]),
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


# ---------------------------------------------------------------------------
# Journal Entry list item (used by GET /journal-entries)
# ---------------------------------------------------------------------------


class JournalEntryListItem(BaseModel):
    """Summary row returned by GET /api/v1/accounting/journal-entries."""

    id: str
    entry_number: str
    description: str
    entry_date: str
    period: str
    reference_type: str
    reference: str | None = None
    created_by: str
    posted_at: str
