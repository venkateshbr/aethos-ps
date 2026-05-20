"""Unit tests for the invoice_drafter_agent.

Tests cover all 5 billing arrangements and the capped_tm cap enforcement.
All DB calls are mocked via MagicMock — no real DB needed.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.agents.base import AgentDeps
from app.agents.invoice_drafter_agent import InvoiceDraft, draft_invoice

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deps(db: MagicMock) -> AgentDeps:
    return AgentDeps(tenant_id="tenant-1", user_id="user-1", db=db)


def _engagement(billing_arrangement: str, billing_terms: dict | None = None) -> dict:
    return {
        "id": "eng-1",
        "name": "Test Engagement",
        "client_id": "client-1",
        "currency": "USD",
        "billing_arrangement": billing_arrangement,
        "rate_card_id": None,
        "engagement_billing_terms": billing_terms or {},
        "clients": {"id": "client-1", "name": "ACME Corp"},
    }


def _configure_no_tax(db: MagicMock) -> None:
    """Ensure ALL tax-rate query paths return empty data.

    _apply_tax has two query paths:
    1. Tenant-specific: .eq("tenant_id").eq("is_default").limit(1)
    2. Fallback global:  .is_("tenant_id","null").eq("country").eq("is_default").limit(1)
    Both must return [] so the agent returns lines untaxed.
    """
    # Path 1 — .eq().eq().limit()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    # Path 2 — .is_().eq().eq().limit()
    db.table.return_value.select.return_value.is_.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    # Tenant country lookup — .eq().single()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"country": "US"}


def _make_db_for_fixed_fee(amount: str = "5000.00") -> MagicMock:
    """DB that returns a fixed-fee engagement and no tax rates."""
    db = MagicMock()
    eng = _engagement("fixed_fee", {"fixed_fee_amount": amount})
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = eng
    _configure_no_tax(db)
    return db


def _make_db_for_retainer(monthly: str = "3000.00") -> MagicMock:
    db = MagicMock()
    eng = _engagement("retainer", {"retainer_monthly_amount": monthly})
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = eng
    _configure_no_tax(db)
    return db


# ---------------------------------------------------------------------------
# Test 1: fixed_fee billing returns single line with correct amount
# ---------------------------------------------------------------------------


def test_draft_fixed_fee_returns_correct_amount() -> None:
    """fixed_fee draft should have one line with the fixed_fee_amount."""
    db = _make_db_for_fixed_fee("5000.00")
    deps = _make_deps(db)

    draft = draft_invoice("eng-1", deps)

    assert isinstance(draft, InvoiceDraft)
    assert draft.billing_arrangement == "fixed_fee"
    assert len(draft.lines) == 1
    assert draft.lines[0].amount == Decimal("5000.00")
    assert draft.subtotal == Decimal("5000.00")
    assert draft.tax_total == Decimal("0")
    assert draft.total == Decimal("5000.00")


# ---------------------------------------------------------------------------
# Test 2: retainer billing returns single monthly retainer line
# ---------------------------------------------------------------------------


def test_draft_retainer_returns_monthly_amount() -> None:
    """retainer draft should have one line with the monthly retainer amount."""
    db = _make_db_for_retainer("3000.00")
    deps = _make_deps(db)

    draft = draft_invoice("eng-1", deps)

    assert isinstance(draft, InvoiceDraft)
    assert draft.billing_arrangement == "retainer"
    assert len(draft.lines) == 1
    assert draft.lines[0].amount == Decimal("3000.00")
    assert draft.subtotal == Decimal("3000.00")
    assert draft.total == Decimal("3000.00")


# ---------------------------------------------------------------------------
# Test 3: milestone billing returns one line per milestone
# ---------------------------------------------------------------------------


def test_draft_milestone_returns_one_line_per_milestone() -> None:
    """milestone draft should have one InvoiceLineItem per milestone."""
    milestones = [
        {"name": "Discovery", "amount": "2000.00"},
        {"name": "Delivery", "amount": "3000.00"},
    ]
    db = MagicMock()
    eng = _engagement("milestone", {"milestones": milestones})
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = eng
    _configure_no_tax(db)

    deps = _make_deps(db)
    draft = draft_invoice("eng-1", deps)

    assert draft.billing_arrangement == "milestone"
    assert len(draft.lines) == 2
    amounts = {line.amount for line in draft.lines}
    assert Decimal("2000.00") in amounts
    assert Decimal("3000.00") in amounts
    assert draft.subtotal == Decimal("5000.00")


# ---------------------------------------------------------------------------
# Test 4: time_and_materials with no time entries returns empty draft
# ---------------------------------------------------------------------------


def test_draft_tm_with_no_entries_returns_empty_lines() -> None:
    """T&M draft with no unbilled time or expenses should have no lines."""
    db = MagicMock()
    eng = _engagement("time_and_materials")
    # Engagement query
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = eng
    # Projects under engagement — empty (also covers tax rate tenant-specific query)
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    _configure_no_tax(db)

    deps = _make_deps(db)
    draft = draft_invoice("eng-1", deps)

    assert draft.billing_arrangement == "time_and_materials"
    assert len(draft.lines) == 0
    assert draft.subtotal == Decimal("0")
    assert draft.total == Decimal("0")


# ---------------------------------------------------------------------------
# Test 5: capped_tm applies cap adjustment when T&M total exceeds cap
# ---------------------------------------------------------------------------


def test_draft_capped_tm_applies_cap_adjustment() -> None:
    """capped_tm draft should add a negative adjustment line when total exceeds cap."""
    db = MagicMock()
    billing_terms = {"cap_amount": "5000.00"}
    eng = _engagement("capped_tm", billing_terms)
    eng["rate_card_id"] = "rc-1"

    # Engagement single query
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = eng

    # We need to return projects, then time_entries, then project_assignments, then expenses
    # The mock chains make this tricky — use side_effect on table() calls
    # Instead we'll patch _draft_tm_lines to return a known value
    from app.agents.invoice_drafter_agent import InvoiceLineItem

    high_value_lines = [
        InvoiceLineItem(
            description="Senior Consultant — 100h @ 100",
            quantity=Decimal("100"),
            unit_price=Decimal("100.00"),
            amount=Decimal("10000.00"),
        )
    ]

    with patch("app.agents.invoice_drafter_agent._draft_tm_lines", return_value=high_value_lines), \
         patch("app.agents.invoice_drafter_agent._apply_tax", side_effect=lambda lines, deps, currency: lines):
        deps = _make_deps(db)
        draft = draft_invoice("eng-1", deps)

    # Should have original line + cap adjustment
    assert draft.billing_arrangement == "capped_tm"
    amounts = [line.amount for line in draft.lines]
    assert Decimal("10000.00") in amounts
    # Cap adjustment should be -(10000 - 5000) = -5000
    assert Decimal("-5000.00") in amounts
    # Net subtotal should be 5000
    assert draft.subtotal == Decimal("5000.00")
