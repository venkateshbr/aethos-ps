"""Unit tests for ReportsService — 6 report methods.

All tests use MagicMock — no network calls, no real DB, no credentials.
Each test covers one report method from reports_service.py.

Issues: #62
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-test-001"


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


def _make_svc(mock_db: MagicMock):
    from app.services.reports_service import ReportsService

    return ReportsService(mock_db, TENANT_ID)


# ---------------------------------------------------------------------------
# Helper — chain builder for supabase query mocks
# ---------------------------------------------------------------------------


def _chain(data: list[dict]) -> MagicMock:
    """Return a MagicMock where any chain of attribute accesses / calls ends
    with .execute().data == data.  Satisfies the fluent supabase-py style."""
    result = MagicMock()
    result.data = data

    chain = MagicMock()
    # Make every method call on the chain return the chain itself, except
    # .execute() which returns result.
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.is_.return_value = chain
    chain.gte.return_value = chain
    chain.lte.return_value = chain
    chain.limit.return_value = chain
    chain.order.return_value = chain
    chain.execute.return_value = result
    return chain


# ---------------------------------------------------------------------------
# 1. AR Aging
# ---------------------------------------------------------------------------


def test_ar_aging_buckets_sum_to_total(mock_db: MagicMock) -> None:
    """AR aging buckets must sum to the total field."""
    today = date.today()

    invoices = [
        # 10 days overdue — 0_30 bucket
        {"id": "inv-1", "total": "500.00", "currency": "USD", "due_date": (today - timedelta(days=10)).isoformat(), "status": "sent"},
        # 45 days overdue — 31_60 bucket
        {"id": "inv-2", "total": "300.00", "currency": "USD", "due_date": (today - timedelta(days=45)).isoformat(), "status": "overdue"},
        # 75 days overdue — 61_90 bucket
        {"id": "inv-3", "total": "200.00", "currency": "USD", "due_date": (today - timedelta(days=75)).isoformat(), "status": "overdue"},
        # 100 days overdue — over_90 bucket
        {"id": "inv-4", "total": "100.00", "currency": "USD", "due_date": (today - timedelta(days=100)).isoformat(), "status": "overdue"},
    ]

    mock_db.table.return_value = _chain(invoices)
    svc = _make_svc(mock_db)
    result = svc.ar_aging()

    assert result["0_30"] == "500.00"
    assert result["31_60"] == "300.00"
    assert result["61_90"] == "200.00"
    assert result["over_90"] == "100.00"

    # total = sum of all buckets
    total = Decimal(result["total"])
    bucket_sum = (
        Decimal(result["0_30"])
        + Decimal(result["31_60"])
        + Decimal(result["61_90"])
        + Decimal(result["over_90"])
    )
    assert total == bucket_sum == Decimal("1100.00")


# ---------------------------------------------------------------------------
# 2. AP Aging — empty result returns zero buckets
# ---------------------------------------------------------------------------


def test_ap_aging_empty_returns_zero_buckets(mock_db: MagicMock) -> None:
    """AP aging with no bills returns all zero-string buckets."""
    mock_db.table.return_value = _chain([])
    svc = _make_svc(mock_db)
    result = svc.ap_aging()

    assert result["0_30"] == "0"
    assert result["31_60"] == "0"
    assert result["61_90"] == "0"
    assert result["over_90"] == "0"
    assert result["total"] == "0"


# ---------------------------------------------------------------------------
# 3. Project P&L — margin computed correctly
# ---------------------------------------------------------------------------


def test_project_pnl_margin_computed(mock_db: MagicMock) -> None:
    """Gross margin = revenue - direct_cost; pct = margin / revenue * 100."""
    projects = [{"id": "proj-1", "name": "Alpha", "engagement_id": "eng-1", "currency": "USD", "budget": "50000.00"}]
    invoices = [{"total": "10000.00", "currency": "USD"}]
    expenses = [{"amount": "3000.00"}, {"amount": "2000.00"}]

    # We need three separate table() calls to return different data:
    # 1st → projects, 2nd → invoices, 3rd → expenses
    call_returns = [
        _chain(projects),
        _chain(invoices),
        _chain(expenses),
    ]
    mock_db.table.side_effect = call_returns

    svc = _make_svc(mock_db)
    result = svc.project_pnl()

    assert len(result) == 1
    row = result[0]
    assert row["project_id"] == "proj-1"
    assert Decimal(row["revenue"]) == Decimal("10000.00")
    assert Decimal(row["direct_cost"]) == Decimal("5000.00")
    assert Decimal(row["gross_margin"]) == Decimal("5000.00")
    assert row["gross_margin_pct"] == 50.0


# ---------------------------------------------------------------------------
# 4. Utilisation — percentage calculated from hours
# ---------------------------------------------------------------------------


def test_utilization_pct_calculated(mock_db: MagicMock) -> None:
    """Utilisation pct = billable_hours / total_hours * 100."""
    entries = [
        {"employee_id": "emp-1", "hours": "8.0", "billable": True},
        {"employee_id": "emp-1", "hours": "2.0", "billable": False},
    ]
    mock_db.table.return_value = _chain(entries)

    svc = _make_svc(mock_db)
    result = svc.utilization()

    assert len(result) == 1
    row = result[0]
    assert row["employee_id"] == "emp-1"
    assert Decimal(row["total_hours"]) == Decimal("10.0")
    assert Decimal(row["billable_hours"]) == Decimal("8.0")
    assert row["utilization_pct"] == 80.0


# ---------------------------------------------------------------------------
# 5. WIP — value = unbilled hours x rate
# ---------------------------------------------------------------------------


def test_wip_value_is_hours_times_rate(mock_db: MagicMock) -> None:
    """WIP value must equal unbilled_hours * avg_rate."""
    # Projects query now embeds the engagement to pick up rate_card_id
    projects = [{"id": "proj-2", "name": "Beta", "engagement_id": "eng-2",
                 "engagements": {"rate_card_id": "rc-1"}}]
    time_entries = [{"hours": "5.0"}, {"hours": "3.0"}]
    rate_lines = [{"rate": "150.00"}]

    # Call order: projects → time_entries → rate_card_lines
    call_returns = [
        _chain(projects),
        _chain(time_entries),
        _chain(rate_lines),
    ]
    mock_db.table.side_effect = call_returns

    svc = _make_svc(mock_db)
    result = svc.wip()

    assert len(result) == 1
    row = result[0]
    assert Decimal(row["unbilled_hours"]) == Decimal("8.0")
    assert Decimal(row["avg_rate"]) == Decimal("150.00")
    assert Decimal(row["wip_value"]) == Decimal("1200.00")


# ---------------------------------------------------------------------------
# 6. Revenue by Engagement — groups by engagement_id
# ---------------------------------------------------------------------------


def test_revenue_by_engagement_groups(mock_db: MagicMock) -> None:
    """Revenue by engagement sums totals per engagement_id correctly."""
    invoices = [
        {"engagement_id": "eng-A", "total": "5000.00", "currency": "USD", "status": "paid", "issue_date": "2026-01-15"},
        {"engagement_id": "eng-A", "total": "3000.00", "currency": "USD", "status": "sent", "issue_date": "2026-02-10"},
        {"engagement_id": "eng-B", "total": "8000.00", "currency": "USD", "status": "paid", "issue_date": "2026-03-05"},
    ]
    mock_db.table.return_value = _chain(invoices)

    svc = _make_svc(mock_db)
    result = svc.revenue_by_engagement()

    by_eng = {r["engagement_id"]: Decimal(r["total_invoiced"]) for r in result}
    assert by_eng["eng-A"] == Decimal("8000.00")
    assert by_eng["eng-B"] == Decimal("8000.00")
