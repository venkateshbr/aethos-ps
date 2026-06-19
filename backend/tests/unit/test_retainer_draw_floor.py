"""Unit tests for retainer-draw floor alert (#177).

When billing_arrangement == 'retainer_draw' and the draw would take the
retainer balance below billing_terms.retainer_floor, the draft summary
must include a warning. The draft is NOT blocked — only warned.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.agents.base import AgentDeps
from app.agents.invoice_drafter_agent import InvoiceDraft, draft_invoice

pytestmark = pytest.mark.unit

# Patch _apply_tax to be a no-op so tax-rate DB queries never fire.
_NO_TAX = patch(
    "app.agents.invoice_drafter_agent._apply_tax",
    side_effect=lambda lines, deps, currency: lines,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deps(db: MagicMock) -> AgentDeps:
    return AgentDeps(tenant_id="tenant-1", user_id="user-1", db=db)


def _engagement_retainer_draw(billing_terms: dict) -> dict:
    return {
        "id": "eng-rd-1",
        "name": "Retainer Draw Engagement",
        "client_id": "client-1",
        "currency": "USD",
        "billing_arrangement": "retainer_draw",
        "rate_card_id": None,
        "engagement_billing_terms": billing_terms,
        "clients": {"id": "client-1", "name": "ACME Corp"},
    }


def _set_engagement_mock(db: MagicMock, eng: dict) -> None:
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        eng
    ]


# ---------------------------------------------------------------------------
# Test 1: floor alert when balance after draw is below retainer_floor
# ---------------------------------------------------------------------------


def test_retainer_draw_floor_alert_when_balance_falls_below_floor() -> None:
    """Warning is added to summary when post-draw balance would be below floor."""
    billing_terms = {
        "retainer_monthly_amount": "2000.00",  # this is the draw amount
        "retainer_floor": "500.00",
    }
    db = MagicMock()
    eng = _engagement_retainer_draw(billing_terms)
    _set_engagement_mock(db, eng)

    # T&M lines mock — no projects so _draft_tm_lines returns []
    # The retainer_monthly_amount is 2000 and current_balance
    # is also set via retainer_current_balance (1500), so balance_after = 1500 - 2000 = -500
    # which is < floor 500 → warning expected.
    billing_terms_with_balance = {
        "retainer_monthly_amount": "2000.00",
        "retainer_floor": "500.00",
        "retainer_current_balance": "1500.00",
    }
    eng["engagement_billing_terms"] = billing_terms_with_balance
    _set_engagement_mock(db, eng)

    deps = _make_deps(db)

    with (
        patch(
            "app.agents.invoice_drafter_agent._draft_tm_lines",
            return_value=[],
        ),
        _NO_TAX,
    ):
        draft = draft_invoice("eng-rd-1", deps)

    assert isinstance(draft, InvoiceDraft)
    assert draft.billing_arrangement == "retainer_draw"
    # Summary must contain the warning
    assert "Warning" in draft.summary
    assert "retainer balance" in draft.summary.lower() or "floor" in draft.summary.lower()
    assert "500" in draft.summary  # floor value
    # Draft is NOT blocked — no error field
    assert draft.error is None


# ---------------------------------------------------------------------------
# Test 2: no warning when balance stays at or above floor
# ---------------------------------------------------------------------------


def test_retainer_draw_no_floor_alert_when_balance_above_floor() -> None:
    """No warning in summary when post-draw balance stays at or above floor."""
    billing_terms = {
        "retainer_monthly_amount": "1000.00",
        "retainer_floor": "500.00",
        "retainer_current_balance": "2000.00",  # 2000 - 1000 = 1000 >= 500 → no warning
    }
    db = MagicMock()
    eng = _engagement_retainer_draw(billing_terms)
    _set_engagement_mock(db, eng)

    deps = _make_deps(db)

    with (
        patch(
            "app.agents.invoice_drafter_agent._draft_tm_lines",
            return_value=[],
        ),
        _NO_TAX,
    ):
        draft = draft_invoice("eng-rd-1", deps)

    assert isinstance(draft, InvoiceDraft)
    assert draft.billing_arrangement == "retainer_draw"
    # Warning should NOT appear
    assert "Warning" not in draft.summary
    assert draft.error is None


# ---------------------------------------------------------------------------
# Test 3: no warning when retainer_floor is absent (no floor configured)
# ---------------------------------------------------------------------------


def test_retainer_draw_no_floor_alert_when_no_floor_configured() -> None:
    """No warning when retainer_floor is not configured in billing_terms."""
    billing_terms = {
        "retainer_monthly_amount": "2000.00",
        # no retainer_floor key → no floor check
        "retainer_current_balance": "500.00",
    }
    db = MagicMock()
    eng = _engagement_retainer_draw(billing_terms)
    _set_engagement_mock(db, eng)

    deps = _make_deps(db)

    with (
        patch(
            "app.agents.invoice_drafter_agent._draft_tm_lines",
            return_value=[],
        ),
        _NO_TAX,
    ):
        draft = draft_invoice("eng-rd-1", deps)

    assert "Warning" not in draft.summary
    assert draft.error is None


# ---------------------------------------------------------------------------
# Test 4: balance exactly at floor → no warning (floor is a minimum, not strict)
# ---------------------------------------------------------------------------


def test_retainer_draw_no_warning_when_balance_equals_floor() -> None:
    """Exactly at floor: no warning (boundary is inclusive — at-floor is allowed)."""
    billing_terms = {
        "retainer_monthly_amount": "1500.00",
        "retainer_floor": "500.00",
        "retainer_current_balance": "2000.00",  # 2000 - 1500 = 500 == floor → no warning
    }
    db = MagicMock()
    eng = _engagement_retainer_draw(billing_terms)
    _set_engagement_mock(db, eng)

    deps = _make_deps(db)

    with (
        patch(
            "app.agents.invoice_drafter_agent._draft_tm_lines",
            return_value=[],
        ),
        _NO_TAX,
    ):
        draft = draft_invoice("eng-rd-1", deps)

    assert "Warning" not in draft.summary
    assert draft.error is None
