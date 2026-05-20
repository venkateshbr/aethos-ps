"""Unit tests for the accounting_guardian.

All tests use unittest.mock.MagicMock for the DB client — no real DB needed.

The guardian is an L3 gate — it must:
  1. Pass a balanced journal.
  2. Reject a journal where |DR - CR| > 0.01.
  3. Reject a journal if the period is locked.
  4. Pass (with residual) if 0 < |DR - CR| <= 0.01, routing to account 7900.
  5. Reject a journal that references unknown account IDs.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.agents.accounting_guardian import validate_journal
from app.domain.journal_helper import JournalLineSpec

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(*, locked: bool = False, valid_account_ids: list[str] | None = None) -> MagicMock:
    """Build a mock Supabase client configured for guardian tests."""
    db = MagicMock()

    # period_locks query
    lock_chain = MagicMock()
    lock_chain.execute.return_value.data = [{"id": "lock-1"}] if locked else []
    db.table.return_value.select.return_value.eq.return_value.eq.return_value = lock_chain

    # accounts query for account validity — needs deeper chain
    acct_chain = MagicMock()
    if valid_account_ids is not None:
        acct_chain.execute.return_value.data = [{"id": aid} for aid in valid_account_ids]
    else:
        acct_chain.execute.return_value.data = []
    # accounts table query chain: .table().select().eq().in_() → acct_chain
    db.table.return_value.select.return_value.eq.return_value.in_.return_value = acct_chain

    return db


def _balanced_lines(
    amount: Decimal = Decimal("1000.00"),
    dr_account_id: str | None = "acct-1",
    cr_account_id: str | None = "acct-2",
) -> list[JournalLineSpec]:
    return [
        JournalLineSpec(
            direction="DR",
            account_code="5000",
            account_id=dr_account_id,
            amount=amount,
            description="Expenses",
        ),
        JournalLineSpec(
            direction="CR",
            account_code="2000",
            account_id=cr_account_id,
            amount=amount,
            description="AP",
        ),
    ]


# ---------------------------------------------------------------------------
# Test 1: balanced journal passes
# ---------------------------------------------------------------------------


def test_guardian_passes_balanced_journal() -> None:
    """A perfectly balanced journal should pass with action='post'."""
    lines = _balanced_lines()
    db = MagicMock()

    # period_locks: not locked
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    # accounts: both IDs are valid
    db.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = [
        {"id": "acct-1"},
        {"id": "acct-2"},
    ]

    result = validate_journal(lines, "2026-05-01", "tenant-1", db)

    assert result["action"] == "post"
    assert result["reason"] == ""
    assert result["fx_residual"] is None


# ---------------------------------------------------------------------------
# Test 2: imbalanced journal is rejected
# ---------------------------------------------------------------------------


def test_guardian_rejects_imbalanced_journal() -> None:
    """A journal where |DR - CR| > 0.01 must be rejected."""
    lines = [
        JournalLineSpec(
            direction="DR",
            account_code="5000",
            amount=Decimal("1000.00"),
            description="Expenses",
        ),
        JournalLineSpec(
            direction="CR",
            account_code="2000",
            amount=Decimal("900.00"),  # off by 100 — way over tolerance
            description="AP",
        ),
    ]
    db = MagicMock()

    result = validate_journal(lines, "2026-05-01", "tenant-1", db)

    assert result["action"] == "reject"
    assert "imbalanced" in result["reason"].lower()
    assert result["fx_residual"] is None


# ---------------------------------------------------------------------------
# Test 3: locked period is rejected
# ---------------------------------------------------------------------------


def test_guardian_rejects_locked_period() -> None:
    """A journal for a locked period must be rejected."""
    lines = _balanced_lines()
    db = MagicMock()

    # Simulate locked period
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": "lock-1"}
    ]

    result = validate_journal(lines, "2026-04-15", "tenant-1", db)

    assert result["action"] == "reject"
    assert "locked" in result["reason"].lower()
    assert result["fx_residual"] is None


# ---------------------------------------------------------------------------
# Test 4: FX residual is routed to 7900
# ---------------------------------------------------------------------------


def test_guardian_routes_fx_residual() -> None:
    """A journal with 0 < |DR - CR| <= 0.01 should return post_with_residual."""
    lines = [
        JournalLineSpec(
            direction="DR",
            account_code="5000",
            amount=Decimal("1000.01"),  # 1 cent residual
            description="Expenses (FX)",
        ),
        JournalLineSpec(
            direction="CR",
            account_code="2000",
            amount=Decimal("1000.00"),
            description="AP",
        ),
    ]
    db = MagicMock()

    # Not locked
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    # No account_ids provided → skip account check

    result = validate_journal(lines, "2026-05-01", "tenant-1", db)

    assert result["action"] == "post_with_residual"
    assert result["fx_residual"] == Decimal("0.01")
    assert "7900" in result["reason"]


# ---------------------------------------------------------------------------
# Test 5: unknown account IDs are rejected
# ---------------------------------------------------------------------------


def test_guardian_rejects_unknown_account() -> None:
    """A journal referencing account IDs not in the tenant's COA must be rejected."""
    lines = [
        JournalLineSpec(
            direction="DR",
            account_code="5000",
            account_id="unknown-acct-id",
            amount=Decimal("500.00"),
            description="Expenses",
        ),
        JournalLineSpec(
            direction="CR",
            account_code="2000",
            account_id="acct-2",
            amount=Decimal("500.00"),
            description="AP",
        ),
    ]

    db = MagicMock()
    # Not locked
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    # Only acct-2 is valid — unknown-acct-id is not
    db.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = [
        {"id": "acct-2"}
    ]

    result = validate_journal(lines, "2026-05-01", "tenant-1", db)

    assert result["action"] == "reject"
    assert "unknown-acct-id" in result["reason"]
