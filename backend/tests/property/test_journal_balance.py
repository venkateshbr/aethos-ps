"""Property tests for accounting invariant I1: every journal entry balances.

Source: docs/test/accounting_invariants.md §I1.

These tests are unit-level property tests. They do not hit the DB; they exercise
the in-process domain logic. The integration counterpart (real DB triggers,
real accounting_guardian agent) is in tests/integration/test_journal_balance_db.py.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, strategies as st

pytestmark = pytest.mark.property


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


money = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@st.composite
def balanced_lines(draw):
    """Generate a list of (direction, account, amount) that sums DR == CR."""
    n_debits = draw(st.integers(min_value=1, max_value=5))
    n_credits = draw(st.integers(min_value=1, max_value=5))
    debit_amounts = draw(st.lists(money, min_size=n_debits, max_size=n_debits))
    total = sum(debit_amounts)
    # Split total across n_credits credits.
    if n_credits == 1:
        credit_amounts = [total]
    else:
        # Generate n_credits - 1 random splits, ensure they sum to total.
        splits = sorted(
            [draw(st.decimals(min_value=Decimal("0.00"), max_value=total, places=2)) for _ in range(n_credits - 1)]
        )
        credit_amounts = []
        prev = Decimal("0")
        for s in splits:
            credit_amounts.append((s - prev).quantize(Decimal("0.01")))
            prev = s
        credit_amounts.append((total - prev).quantize(Decimal("0.01")))
        # Fix rounding residual: dump into last line.
        diff = total - sum(credit_amounts)
        if diff != 0:
            credit_amounts[-1] = (credit_amounts[-1] + diff).quantize(Decimal("0.01"))

    lines = (
        [("DR", f"acct_dr_{i}", amt) for i, amt in enumerate(debit_amounts)]
        + [("CR", f"acct_cr_{i}", amt) for i, amt in enumerate(credit_amounts)]
    )
    return lines


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@given(balanced_lines())
def test_balanced_lines_produce_balanced_journal(make_journal_entry, lines):
    """Generated balanced lines must build a balanced JournalEntry."""
    je = make_journal_entry(lines)
    assert je.is_balanced(), f"DR={je.debits} CR={je.credits} diff={je.debits - je.credits}"


@given(balanced_lines(), money)
def test_unbalancing_amount_breaks_balance(make_journal_entry, lines, extra_amount):
    """Adding an unmatched debit must break the balance."""
    lines_with_extra = lines + [("DR", "acct_extra", extra_amount)]
    je = make_journal_entry(lines_with_extra)
    assert not je.is_balanced(fx_tolerance=Decimal("0.00"))


@pytest.mark.xfail(
    strict=True,
    reason="accounting_guardian + post_journal not yet implemented — see PLAN §6.2",
)
@given(balanced_lines())
def test_accounting_guardian_accepts_balanced(lines):
    """accounting_guardian must approve a balanced entry. Wired when agent ships."""
    from app.agents.accounting_guardian import validate  # noqa: F401  (will exist later)

    result = validate(lines, tenant_id="test", entry_date="2026-05-19")
    assert result.action == "post"


@pytest.mark.xfail(
    strict=True,
    reason="accounting_guardian not yet implemented",
)
@given(balanced_lines(), money)
def test_accounting_guardian_rejects_imbalanced(lines, extra_amount):
    """accounting_guardian must reject an imbalanced entry."""
    from app.agents.accounting_guardian import validate  # noqa: F401

    bad = lines + [("DR", "acct_extra", extra_amount)]
    result = validate(bad, tenant_id="test", entry_date="2026-05-19")
    assert result.action == "reject"
