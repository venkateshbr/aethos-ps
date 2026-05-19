"""Journal entry helpers for building and validating double-entry GL postings.

Usage::

    from app.domain.journal_helper import JournalLineSpec, validate_journal_balance

    lines = [
        JournalLineSpec(direction="DR", account_code="5000", amount=Decimal("1000.00"), description="Expenses"),
        JournalLineSpec(direction="CR", account_code="2000", amount=Decimal("1000.00"), description="Accounts Payable"),
    ]
    assert validate_journal_balance(lines)

Rules enforced here (not in DB triggers, to enable Python-layer validation before INSERT):
- debits must equal credits within a 1-cent tolerance (GAAP rounding tolerance).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class JournalLineSpec:
    """Specification for a single journal line before it is persisted.

    ``direction`` must be "DR" (debit) or "CR" (credit).
    ``account_code`` is the COA code string (e.g. "5000", "2000").
    ``amount`` must be positive; direction carries the sign semantics.
    ``description`` is an optional narrative for the line.
    """

    direction: str  # "DR" or "CR"
    account_code: str
    amount: Decimal
    description: str = ""

    def __post_init__(self) -> None:
        if self.direction not in ("DR", "CR"):
            raise ValueError(f"direction must be 'DR' or 'CR', got {self.direction!r}")
        if self.amount < Decimal("0"):
            raise ValueError(f"amount must be non-negative, got {self.amount}")


def validate_journal_balance(lines: list[JournalLineSpec]) -> bool:
    """Return True if the journal balances (debits == credits within 0.01).

    A balanced journal is required before any GL posting.
    Raises no exceptions — callers should raise HTTPException on False.

    Args:
        lines: List of JournalLineSpec entries to check.

    Returns:
        True if |debits - credits| <= 0.01, False otherwise.
    """
    debits = sum(line.amount for line in lines if line.direction == "DR")
    credits = sum(line.amount for line in lines if line.direction == "CR")
    return abs(debits - credits) <= Decimal("0.01")
