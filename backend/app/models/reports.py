"""Pydantic models for financial report responses.

Money fields are serialised as two-decimal-place strings (never float)
following the Aethos money rule in CLAUDE.md.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TrialBalanceLine(BaseModel):
    """One row in the trial balance — one account's DR/CR totals."""

    account_code: str
    account_name: str
    account_type: str  # asset / liability / equity / revenue / expense
    total_dr: str  # Decimal serialised as string via serialise_money()
    total_cr: str
    net: str  # positive = debit balance, negative = credit balance


class TrialBalanceReport(BaseModel):
    """Full trial balance report payload returned by the API."""

    as_of_period: str | None  # YYYY-MM or None (all-time cumulative)
    lines: list[TrialBalanceLine]
    grand_total_dr: str
    grand_total_cr: str
    is_balanced: bool  # abs(grand_total_dr - grand_total_cr) <= 0.01
    generated_at: datetime
