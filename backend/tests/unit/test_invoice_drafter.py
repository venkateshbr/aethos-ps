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

# Patch _apply_tax to be a no-op so tax-rate DB queries never fire.
# This avoids mock-chain collisions between the engagement query and tax queries
# (both use .eq().eq().limit() on different tables, but MagicMock can't
# distinguish table names, so the last .data assignment wins).
_NO_TAX = patch("app.agents.invoice_drafter_agent._apply_tax",
                side_effect=lambda lines, deps, currency: lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deps(db: MagicMock) -> AgentDeps:
    return AgentDeps(tenant_id="tenant-1", user_id="user-1", db=db)


def _engagement(
    billing_arrangement: str,
    billing_terms: dict | None = None,
    service_catalogue_id: str | None = None,
) -> dict:
    return {
        "id": "eng-1",
        "name": "Test Engagement",
        "client_id": "client-1",
        "currency": "USD",
        "billing_arrangement": billing_arrangement,
        "rate_card_id": None,
        "service_catalogue_id": service_catalogue_id,
        "engagement_billing_terms": billing_terms or {},
        "clients": {"id": "client-1", "name": "ACME Corp"},
    }


def _configure_no_tax(db: MagicMock) -> None:
    """No-op: tax is patched out directly in each test via _NO_TAX_PATCHES below."""


def _set_engagement_mock(db: MagicMock, eng: dict) -> None:
    """Wire the db mock for the engagement query path used by invoice_drafter.
    The drafter now uses .eq().eq().limit(1).execute() → returns list.
    """
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [eng]


def _make_db_for_fixed_fee(amount: str = "5000.00") -> MagicMock:
    """DB that returns a fixed-fee engagement and no tax rates."""
    db = MagicMock()
    eng = _engagement("fixed_fee", {"fixed_fee_amount": amount})
    # _configure_no_tax must come BEFORE _set_engagement_mock — both set the
    # same mock chain and the last write wins.  Engagement mock is the one
    # that must survive (it is read first by draft_invoice).
    _configure_no_tax(db)
    _set_engagement_mock(db, eng)
    return db


def _make_db_for_retainer(monthly: str = "3000.00") -> MagicMock:
    db = MagicMock()
    eng = _engagement("retainer", {"retainer_monthly_amount": monthly})
    _configure_no_tax(db)
    _set_engagement_mock(db, eng)
    return db


# ---------------------------------------------------------------------------
# Test 1: fixed_fee billing returns single line with correct amount
# ---------------------------------------------------------------------------


def test_draft_fixed_fee_returns_correct_amount() -> None:
    """fixed_fee draft should have one line with the fixed_fee_amount."""
    db = _make_db_for_fixed_fee("5000.00")
    deps = _make_deps(db)

    with _NO_TAX:
        draft = draft_invoice("eng-1", deps)

    assert isinstance(draft, InvoiceDraft)
    assert draft.billing_arrangement == "fixed_fee"
    assert len(draft.lines) == 1
    assert draft.lines[0].amount == Decimal("5000.00")
    assert draft.subtotal == Decimal("5000.00")
    assert draft.tax_total == Decimal("0")
    assert draft.total == Decimal("5000.00")


def test_draft_fixed_fee_carries_service_catalogue_id() -> None:
    """Engagement service catalogue linkage is preserved on draft invoice lines."""
    db = MagicMock()
    eng = _engagement(
        "fixed_fee",
        {"fixed_fee_amount": "5000.00"},
        service_catalogue_id="svc-001",
    )
    _set_engagement_mock(db, eng)
    deps = _make_deps(db)

    with _NO_TAX:
        draft = draft_invoice("eng-1", deps)

    assert draft.lines[0].service_catalogue_id == "svc-001"


def test_draft_fixed_fee_uses_per_unit_billing_terms() -> None:
    """Per-employee payroll terms draft quantity x unit price invoice lines."""
    db = MagicMock()
    eng = _engagement(
        "fixed_fee",
        {
            "billing_unit": "per_employee",
            "unit_label": "Employees",
            "unit_quantity": "42",
            "unit_price": "18.50",
        },
    )
    _set_engagement_mock(db, eng)
    deps = _make_deps(db)

    with _NO_TAX:
        draft = draft_invoice("eng-1", deps)

    assert draft.lines[0].description == "Employees: Test Engagement"
    assert draft.lines[0].quantity == Decimal("42")
    assert draft.lines[0].unit_price == Decimal("18.50")
    assert draft.lines[0].amount == Decimal("777.00")
    assert draft.subtotal == Decimal("777.00")


# ---------------------------------------------------------------------------
# Test 2: retainer billing returns single monthly retainer line
# ---------------------------------------------------------------------------


def test_draft_retainer_returns_monthly_amount() -> None:
    """retainer draft should have one line with the monthly retainer amount."""
    db = _make_db_for_retainer("3000.00")
    deps = _make_deps(db)

    with _NO_TAX:
        draft = draft_invoice("eng-1", deps)

    assert isinstance(draft, InvoiceDraft)
    assert draft.billing_arrangement == "retainer"
    assert len(draft.lines) == 1
    assert draft.lines[0].amount == Decimal("3000.00")
    assert draft.subtotal == Decimal("3000.00")
    assert draft.total == Decimal("3000.00")


def test_draft_retainer_draw_caps_offset_by_ledger_balance() -> None:
    """Retainer draw offsets use available ledger balance before configured draw."""
    db = MagicMock()
    eng = _engagement(
        "retainer_draw",
        {"retainer_monthly_amount": "1500.00", "retainer_floor": "500.00"},
    )

    def table_side(table_name: str) -> MagicMock:
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.is_.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.limit.return_value = chain

        result = MagicMock()
        if table_name == "engagements":
            result.data = [eng]
        elif table_name == "projects":
            result.data = [{"id": "project-1"}]
        elif table_name == "time_entries":
            result.data = [
                {
                    "id": "time-1",
                    "project_id": "project-1",
                    "employee_id": "employee-1",
                    "hours": "20",
                }
            ]
        elif table_name == "project_assignments":
            result.data = [
                {
                    "employee_id": "employee-1",
                    "project_id": "project-1",
                    "role": "Consultant",
                    "override_rate": "100.00",
                }
            ]
        elif table_name == "retainer_ledger_entries":
            result.data = [
                {"entry_type": "deposit", "amount": "700.00"},
            ]
        else:
            result.data = []
        chain.execute.return_value = result
        return chain

    db.table.side_effect = table_side
    deps = _make_deps(db)

    with _NO_TAX:
        draft = draft_invoice("eng-1", deps)

    adjustment = next(line for line in draft.lines if line.description == "Retainer applied")
    assert adjustment.amount == Decimal("-700.00")
    assert draft.subtotal == Decimal("1300.00")
    assert "below floor" in draft.summary


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
    _set_engagement_mock(db, eng)

    deps = _make_deps(db)
    with _NO_TAX:
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
    _set_engagement_mock(db, eng)
    # Projects under engagement — empty list
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    deps = _make_deps(db)
    with _NO_TAX:
        draft = draft_invoice("eng-1", deps)

    assert draft.billing_arrangement == "time_and_materials"
    assert len(draft.lines) == 0
    assert draft.subtotal == Decimal("0")
    assert draft.total == Decimal("0")


def test_draft_tm_uses_assignment_and_client_rate_overrides() -> None:
    """T&M draft prefers assignment override, then client override, then base role rate."""
    db = MagicMock()
    eng = _engagement("time_and_materials")
    eng["rate_card_id"] = "rc-1"

    def table_side(table_name: str) -> MagicMock:
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.is_.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.limit.return_value = chain

        result = MagicMock()
        if table_name == "engagements":
            result.data = [eng]
        elif table_name == "projects":
            result.data = [{"id": "project-1"}]
        elif table_name == "time_entries":
            result.data = [
                {
                    "id": "time-override",
                    "project_id": "project-1",
                    "employee_id": "employee-override",
                    "hours": "2",
                },
                {
                    "id": "time-client",
                    "project_id": "project-1",
                    "employee_id": "employee-client",
                    "hours": "3",
                },
            ]
        elif table_name == "rate_card_lines":
            result.data = [{"role": "Consultant", "rate": "100.00"}]
        elif table_name == "rate_card_client_overrides":
            result.data = [{"role": "Consultant", "rate": "125.00"}]
        elif table_name == "project_assignments":
            result.data = [
                {
                    "employee_id": "employee-override",
                    "project_id": "project-1",
                    "role": "Consultant",
                    "override_rate": "150.00",
                },
                {
                    "employee_id": "employee-client",
                    "project_id": "project-1",
                    "role": "Consultant",
                    "override_rate": None,
                },
            ]
        else:
            result.data = []
        chain.execute.return_value = result
        return chain

    db.table.side_effect = table_side
    deps = _make_deps(db)

    with _NO_TAX:
        draft = draft_invoice("eng-1", deps)

    assert [line.unit_price for line in draft.lines] == [
        Decimal("150.00"),
        Decimal("125.00"),
    ]
    assert [line.amount for line in draft.lines] == [
        Decimal("300.00"),
        Decimal("375.00"),
    ]
    assert draft.subtotal == Decimal("675.00")


def test_draft_tm_prefers_service_line_rate_over_generic_role_rate() -> None:
    """T&M draft uses the engagement service-line rate before generic role rate."""
    db = MagicMock()
    eng = _engagement("time_and_materials")
    eng["rate_card_id"] = "rc-1"
    eng["service_line"] = "advisory"

    def table_side(table_name: str) -> MagicMock:
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.is_.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.limit.return_value = chain

        result = MagicMock()
        if table_name == "engagements":
            result.data = [eng]
        elif table_name == "projects":
            result.data = [{"id": "project-1"}]
        elif table_name == "time_entries":
            result.data = [
                {
                    "id": "time-advisory",
                    "project_id": "project-1",
                    "employee_id": "employee-advisory",
                    "hours": "2",
                }
            ]
        elif table_name == "rate_card_lines":
            result.data = [
                {
                    "role": "Consultant",
                    "rate": "100.00",
                    "service_line": None,
                },
                {
                    "role": "Consultant",
                    "rate": "175.00",
                    "service_line": "advisory",
                },
            ]
        elif table_name == "rate_card_client_overrides":
            result.data = []
        elif table_name == "project_assignments":
            result.data = [
                {
                    "employee_id": "employee-advisory",
                    "project_id": "project-1",
                    "role": "Consultant",
                    "override_rate": None,
                }
            ]
        else:
            result.data = []
        chain.execute.return_value = result
        return chain

    db.table.side_effect = table_side
    deps = _make_deps(db)

    with _NO_TAX:
        draft = draft_invoice("eng-1", deps)

    assert draft.lines[0].unit_price == Decimal("175.00")
    assert draft.lines[0].amount == Decimal("350.00")


# ---------------------------------------------------------------------------
# Test 5: capped_tm applies cap adjustment when T&M total exceeds cap
# ---------------------------------------------------------------------------


def test_draft_capped_tm_applies_cap_adjustment() -> None:
    """capped_tm draft should add a negative adjustment line when total exceeds cap."""
    db = MagicMock()
    billing_terms = {"cap_amount": "5000.00"}
    eng = _engagement("capped_tm", billing_terms)
    eng["rate_card_id"] = "rc-1"

    _set_engagement_mock(db, eng)

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
         _NO_TAX:
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
