"""Unit tests for ReportsService.trial_balance() — issue #203.

All tests use MagicMock — no network calls, no real DB, no credentials.

Test matrix:
  1. test_trial_balance_empty_tenant           — no lines → empty, is_balanced=True, zeros
  2. test_trial_balance_balanced               — one balanced journal entry (DR AR / CR Rev)
  3. test_trial_balance_period_filter          — entries in two periods; filter selects only earlier
  4. test_trial_balance_is_balanced_always_true — any validly-posted set of journals is balanced
  5. test_trial_balance_unposted_excluded      — draft (unposted) lines are not counted
  6. test_trial_balance_sorted_by_code         — lines returned in account code order
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-tb-test-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_svc(mock_db: MagicMock):
    from app.services.reports_service import ReportsService

    return ReportsService(mock_db, TENANT_ID)


def _journal_line(
    direction: str,
    base_amount: str,
    code: str,
    name: str,
    account_type: str,
    period: str,
    posted: bool = True,
) -> dict:
    """Construct a fake journal_lines row as PostgREST would return it with embeds."""
    return {
        "direction": direction,
        "base_amount": base_amount,
        "journal_entries": {
            "period": period,
            "posted_at": "2026-06-01T00:00:00+00:00" if posted else None,
        },
        "accounts": {
            "code": code,
            "name": name,
            "account_type": account_type,
        },
    }


def _chain(data: list[dict]) -> MagicMock:
    """Supabase-py fluent query chain that ends with .execute().data == data."""
    result = MagicMock()
    result.data = data

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = result
    return chain


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# 1. Empty tenant
# ---------------------------------------------------------------------------


def test_trial_balance_empty_tenant(mock_db: MagicMock) -> None:
    """A tenant with no journal lines returns an empty report that is balanced."""
    mock_db.table.return_value = _chain([])
    svc = _make_svc(mock_db)
    report = svc.trial_balance()

    assert report.lines == []
    assert report.is_balanced is True
    assert report.grand_total_dr == "0.00"
    assert report.grand_total_cr == "0.00"
    assert report.as_of_period is None


# ---------------------------------------------------------------------------
# 2. Balanced journal entry
# ---------------------------------------------------------------------------


def test_trial_balance_balanced(mock_db: MagicMock) -> None:
    """One posted invoice journal: DR AR 1000 / CR Revenue 1000.

    Verifies:
    - AR account: total_dr=1000.00, total_cr=0.00, net=1000.00
    - Revenue account: total_dr=0.00, total_cr=1000.00, net=-1000.00
    - grand_total_dr == grand_total_cr == 1000.00
    - is_balanced == True
    """
    raw = [
        _journal_line("DR", "1000.00", "1200", "Accounts Receivable", "asset", "2026-06"),
        _journal_line("CR", "1000.00", "4000", "Revenue", "revenue", "2026-06"),
    ]
    mock_db.table.return_value = _chain(raw)
    svc = _make_svc(mock_db)
    report = svc.trial_balance()

    assert report.is_balanced is True
    assert report.grand_total_dr == "1000.00"
    assert report.grand_total_cr == "1000.00"

    by_code = {line.account_code: line for line in report.lines}

    ar = by_code["1200"]
    assert ar.account_name == "Accounts Receivable"
    assert ar.account_type == "asset"
    assert ar.total_dr == "1000.00"
    assert ar.total_cr == "0.00"
    assert ar.net == "1000.00"

    rev = by_code["4000"]
    assert rev.account_name == "Revenue"
    assert rev.account_type == "revenue"
    assert rev.total_dr == "0.00"
    assert rev.total_cr == "1000.00"
    assert rev.net == "-1000.00"


# ---------------------------------------------------------------------------
# 3. Period filter
# ---------------------------------------------------------------------------


def test_trial_balance_period_filter(mock_db: MagicMock) -> None:
    """Entries in 2026-05 and 2026-06: filtering to 2026-05 includes only May.

    The 2026-06 journal (CR Revenue 500) should be excluded, leaving only
    the May AR debit (DR AR 800) and May Revenue credit (CR Revenue 800).
    """
    raw = [
        # May journal — should be included
        _journal_line("DR", "800.00", "1200", "Accounts Receivable", "asset", "2026-05"),
        _journal_line("CR", "800.00", "4000", "Revenue", "revenue", "2026-05"),
        # June journal — should be excluded when filtering to 2026-05
        _journal_line("DR", "500.00", "1200", "Accounts Receivable", "asset", "2026-06"),
        _journal_line("CR", "500.00", "4000", "Revenue", "revenue", "2026-06"),
    ]
    mock_db.table.return_value = _chain(raw)
    svc = _make_svc(mock_db)
    report = svc.trial_balance(as_of_period="2026-05")

    assert report.as_of_period == "2026-05"
    # Only May's 800 should be counted
    assert report.grand_total_dr == "800.00"
    assert report.grand_total_cr == "800.00"
    assert report.is_balanced is True

    by_code = {line.account_code: line for line in report.lines}
    assert by_code["1200"].total_dr == "800.00"
    assert by_code["4000"].total_cr == "800.00"


# ---------------------------------------------------------------------------
# 4. is_balanced invariant
# ---------------------------------------------------------------------------


def test_trial_balance_is_balanced_always_true(mock_db: MagicMock) -> None:
    """The accounting_guardian guarantees every posted set of journal entries
    is balanced. A multi-entry, multi-account journal must pass the invariant.

    Journal:
      DR AR       2500  — invoice raised
      CR Revenue  2000  — revenue earned
      CR Tax Payable 500 — tax portion
    """
    raw = [
        _journal_line("DR", "2500.00", "1200", "Accounts Receivable", "asset", "2026-06"),
        _journal_line("CR", "2000.00", "4000", "Revenue", "revenue", "2026-06"),
        _journal_line("CR", "500.00", "2300", "Sales Tax Payable", "liability", "2026-06"),
    ]
    mock_db.table.return_value = _chain(raw)
    svc = _make_svc(mock_db)
    report = svc.trial_balance()

    assert report.is_balanced is True
    assert Decimal(report.grand_total_dr) == Decimal(report.grand_total_cr)


# ---------------------------------------------------------------------------
# 5. Unposted lines excluded
# ---------------------------------------------------------------------------


def test_trial_balance_unposted_excluded(mock_db: MagicMock) -> None:
    """Draft journal entries (posted_at=None) must NOT appear in the trial balance."""
    raw = [
        # Posted — should appear
        _journal_line("DR", "300.00", "1200", "Accounts Receivable", "asset", "2026-06", posted=True),
        _journal_line("CR", "300.00", "4000", "Revenue", "revenue", "2026-06", posted=True),
        # Draft — must be excluded
        _journal_line("DR", "9999.00", "1200", "Accounts Receivable", "asset", "2026-06", posted=False),
        _journal_line("CR", "9999.00", "4000", "Revenue", "revenue", "2026-06", posted=False),
    ]
    mock_db.table.return_value = _chain(raw)
    svc = _make_svc(mock_db)
    report = svc.trial_balance()

    # Only the posted 300 should be included
    assert report.grand_total_dr == "300.00"
    assert report.grand_total_cr == "300.00"
    assert report.is_balanced is True


# ---------------------------------------------------------------------------
# 6. Sorted by account code
# ---------------------------------------------------------------------------


def test_trial_balance_sorted_by_code(mock_db: MagicMock) -> None:
    """Lines must be sorted by account code ascending (1xxx before 4xxx before 5xxx)."""
    raw = [
        _journal_line("CR", "5000.00", "4000", "Revenue", "revenue", "2026-06"),
        _journal_line("DR", "1000.00", "5000", "Expenses", "expense", "2026-06"),
        _journal_line("DR", "4000.00", "1200", "Accounts Receivable", "asset", "2026-06"),
    ]
    mock_db.table.return_value = _chain(raw)
    svc = _make_svc(mock_db)
    report = svc.trial_balance()

    codes = [line.account_code for line in report.lines]
    assert codes == sorted(codes), f"Lines not sorted by code: {codes}"
    assert codes == ["1200", "4000", "5000"]
