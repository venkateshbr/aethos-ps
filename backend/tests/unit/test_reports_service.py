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


def _route_tables(mock_db: MagicMock, tables: dict[str, list[dict]]) -> None:
    """Route mock_db.table(name) to a chain seeded from ``tables[name]``."""

    def _table(name: str) -> MagicMock:
        return _chain(tables.get(name, []))

    mock_db.table.side_effect = _table


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
    engagements = [
        {"id": "eng-A", "name": "Engagement A"},
        {"id": "eng-B", "name": "Engagement B"},
    ]
    # revenue_by_engagement makes two db.table() calls: invoices then engagements
    mock_db.table.side_effect = [_chain(invoices), _chain(engagements)]

    svc = _make_svc(mock_db)
    result = svc.revenue_by_engagement()

    by_eng = {r["engagement_id"]: Decimal(r["total_invoiced"]) for r in result}
    assert by_eng["eng-A"] == Decimal("8000.00")
    assert by_eng["eng-B"] == Decimal("8000.00")


def test_project_health_scores_rank_riskiest_project_first(mock_db: MagicMock) -> None:
    """Project health score combines budget, margin, WIP, cap, and scope risks."""
    today = date.today().isoformat()
    projects = [
        {
            "id": "proj-risk",
            "name": "Risky Capped Project",
            "engagement_id": "eng-risk",
            "currency": "USD",
            "budget": "100000.00",
            "budget_hours": "100.00",
            "status": "active",
            "engagements": {
                "id": "eng-risk",
                "name": "Risky Engagement",
                "billing_arrangement": "capped_tm",
                "total_value": "1000.00",
                "service_line": "advisory",
            },
        },
        {
            "id": "proj-healthy",
            "name": "Healthy Project",
            "engagement_id": "eng-healthy",
            "currency": "USD",
            "budget": "50000.00",
            "budget_hours": "100.00",
            "status": "active",
            "engagements": {
                "id": "eng-healthy",
                "name": "Healthy Engagement",
                "billing_arrangement": "time_and_materials",
                "total_value": "50000.00",
                "service_line": "tax",
            },
        },
    ]
    time_entries = [
        {
            "project_id": "proj-risk",
            "hours": "15.00",
            "billable": True,
            "billing_status": "unbilled",
            "date": today,
        },
        {
            "project_id": "proj-risk",
            "hours": "15.00",
            "billable": True,
            "billing_status": "unbilled",
            "date": today,
        },
        {
            "project_id": "proj-risk",
            "hours": "15.00",
            "billable": True,
            "billing_status": "unbilled",
            "date": today,
        },
        {
            "project_id": "proj-risk",
            "hours": "15.00",
            "billable": True,
            "billing_status": "unbilled",
            "date": today,
        },
        {
            "project_id": "proj-risk",
            "hours": "15.00",
            "billable": False,
            "billing_status": "non_billable",
            "date": today,
        },
        {
            "project_id": "proj-risk",
            "hours": "15.00",
            "billable": False,
            "billing_status": "non_billable",
            "date": today,
        },
        {
            "project_id": "proj-healthy",
            "hours": "10.00",
            "billable": True,
            "billing_status": "unbilled",
            "date": today,
        },
    ]
    _route_tables(
        mock_db,
        {
            "projects": projects,
            "engagement_billing_terms": [
                {"engagement_id": "eng-risk", "cap_amount": "1000.00"}
            ],
            "time_entries": time_entries,
            "invoices": [
                {
                    "engagement_id": "eng-risk",
                    "total": "920.00",
                    "status": "sent",
                    "issue_date": today,
                }
            ],
        },
    )

    svc = _make_svc(mock_db)
    svc.project_pnl = MagicMock(
        return_value=[
            {
                "project_id": "proj-risk",
                "revenue": "920.00",
                "direct_cost": "800.00",
                "gross_margin_pct": 13.0,
            },
            {
                "project_id": "proj-healthy",
                "revenue": "10000.00",
                "direct_cost": "5000.00",
                "gross_margin_pct": 50.0,
            },
        ]
    )
    svc.wip = MagicMock(
        return_value=[
            {
                "project_id": "proj-risk",
                "unbilled_hours": "8.00",
                "wip_value": "300.00",
            },
            {
                "project_id": "proj-healthy",
                "unbilled_hours": "0.00",
                "wip_value": "0.00",
            },
        ]
    )

    result = svc.project_health_scores()

    assert [row["project_id"] for row in result] == ["proj-risk", "proj-healthy"]
    risky = result[0]
    assert risky["risk_level"] == "critical"
    assert risky["health_score"] < 50
    driver_codes = {driver["code"] for driver in risky["drivers"]}
    assert driver_codes >= {
        "budget_hours_burn",
        "low_margin",
        "cap_drawdown",
        "unbilled_wip",
        "scope_creep",
    }
    assert risky["metrics"]["budget_burn_pct"] == 90.0
    assert risky["metrics"]["cap_used_pct"] == 92.0
    assert result[1]["risk_level"] == "healthy"


def test_capacity_planning_flags_overallocated_and_underutilized(
    mock_db: MagicMock,
) -> None:
    """Capacity report ranks overallocated staff before underutilized staff."""
    period_start = "2026-06-15"
    period_end = "2026-06-21"
    employees = [
        {
            "id": "emp-over",
            "first_name": "Asha",
            "last_name": "Rao",
            "email": "asha@example.com",
            "department": "Advisory",
            "practice_area": "advisory",
            "seniority": "manager",
            "available_hours_per_week": "40.00",
            "status": "active",
        },
        {
            "id": "emp-under",
            "first_name": "Ben",
            "last_name": "Low",
            "email": "ben@example.com",
            "department": "Tax",
            "practice_area": "tax",
            "seniority": "associate",
            "available_hours_per_week": "40.00",
            "status": "active",
        },
    ]
    _route_tables(
        mock_db,
        {
            "employees": employees,
            "time_entries": [
                {
                    "employee_id": "emp-over",
                    "hours": "45.00",
                    "billable": True,
                    "date": "2026-06-16",
                },
                {
                    "employee_id": "emp-under",
                    "hours": "10.00",
                    "billable": True,
                    "date": "2026-06-16",
                },
            ],
            "project_assignments": [
                {
                    "employee_id": "emp-over",
                    "project_id": "proj-1",
                    "role": "Manager",
                    "start_date": "2026-06-01",
                    "end_date": None,
                    "projects": {
                        "id": "proj-1",
                        "name": "Platform Cleanup",
                        "status": "active",
                    },
                }
            ],
        },
    )

    svc = _make_svc(mock_db)
    result = svc.capacity_planning(
        period_start=period_start,
        period_end=period_end,
    )

    assert [row["employee_id"] for row in result] == ["emp-over", "emp-under"]
    assert result[0]["capacity_status"] == "overallocated"
    assert result[0]["utilization_pct"] == 112.5
    assert result[0]["active_assignment_count"] == 1
    assert result[0]["active_assignments"][0]["project_name"] == "Platform Cleanup"
    assert result[1]["capacity_status"] == "underutilized"
    assert result[1]["utilization_pct"] == 25.0


def test_client_profitability_reconciles_revenue_labor_and_expenses(
    mock_db: MagicMock,
) -> None:
    """Client profitability combines finalized revenue, labour, and expenses."""
    _route_tables(
        mock_db,
        {
            "clients": [
                {
                    "id": "client-acme",
                    "name": "Acme Corp",
                    "kind": "customer",
                    "currency": "USD",
                },
                {
                    "id": "client-bravo",
                    "name": "Bravo Ltd",
                    "kind": "both",
                    "currency": "USD",
                },
            ],
            "engagements": [
                {
                    "id": "eng-acme",
                    "client_id": "client-acme",
                    "service_line": "advisory",
                    "currency": "USD",
                },
                {
                    "id": "eng-bravo",
                    "client_id": "client-bravo",
                    "service_line": "tax",
                    "currency": "USD",
                },
            ],
            "projects": [
                {"id": "proj-acme", "engagement_id": "eng-acme", "currency": "USD"},
                {"id": "proj-bravo", "engagement_id": "eng-bravo", "currency": "USD"},
            ],
            "invoices": [
                {
                    "id": "inv-acme",
                    "client_id": "client-acme",
                    "engagement_id": "eng-acme",
                    "total": "10000.00",
                    "currency": "USD",
                    "issue_date": "2026-06-10",
                },
                {
                    "id": "inv-bravo",
                    "client_id": "client-bravo",
                    "engagement_id": "eng-bravo",
                    "total": "5000.00",
                    "currency": "USD",
                    "issue_date": "2026-06-11",
                },
            ],
            "time_entries": [
                {
                    "project_id": "proj-acme",
                    "employee_id": "emp-senior",
                    "hours": "10.00",
                    "date": "2026-06-12",
                },
                {
                    "project_id": "proj-bravo",
                    "employee_id": "emp-manager",
                    "hours": "5.00",
                    "date": "2026-06-12",
                },
            ],
            "employees": [
                {"id": "emp-senior", "cost_rate": "100.00"},
                {"id": "emp-manager", "cost_rate": "120.00"},
            ],
            "project_expenses": [
                {
                    "id": "exp-acme",
                    "project_id": "proj-acme",
                    "amount": "1000.00",
                    "base_amount": None,
                    "currency": "USD",
                    "expense_date": "2026-06-12",
                },
                {
                    "id": "exp-bravo",
                    "project_id": "proj-bravo",
                    "amount": "500.00",
                    "base_amount": None,
                    "currency": "USD",
                    "expense_date": "2026-06-12",
                },
            ],
        },
    )

    svc = _make_svc(mock_db)
    result = svc.client_profitability(
        period_start="2026-06-01",
        period_end="2026-06-30",
    )

    by_client = {row["client_id"]: row for row in result}
    acme = by_client["client-acme"]
    assert acme["client_name"] == "Acme Corp"
    assert acme["service_lines"] == ["advisory"]
    assert Decimal(acme["revenue"]) == Decimal("10000.00")
    assert Decimal(acme["labor_cost"]) == Decimal("1000.00")
    assert Decimal(acme["expense_cost"]) == Decimal("1000.00")
    assert Decimal(acme["total_cost"]) == Decimal("2000.00")
    assert Decimal(acme["gross_margin"]) == Decimal("8000.00")
    assert acme["gross_margin_pct"] == 80.0
    assert acme["profitability_status"] == "strong"
    assert acme["invoice_count"] == 1
    assert acme["project_count"] == 1


def test_segment_profitability_groups_by_service_line(mock_db: MagicMock) -> None:
    """Segment profitability exposes data-backed service-line rollups."""
    _route_tables(
        mock_db,
        {
            "clients": [
                {
                    "id": "client-acme",
                    "name": "Acme Corp",
                    "kind": "customer",
                    "currency": "USD",
                },
                {
                    "id": "client-bravo",
                    "name": "Bravo Ltd",
                    "kind": "customer",
                    "currency": "USD",
                },
            ],
            "engagements": [
                {
                    "id": "eng-acme",
                    "client_id": "client-acme",
                    "service_line": "advisory",
                    "currency": "USD",
                },
                {
                    "id": "eng-bravo",
                    "client_id": "client-bravo",
                    "service_line": "tax",
                    "currency": "USD",
                },
            ],
            "projects": [
                {"id": "proj-acme", "engagement_id": "eng-acme", "currency": "USD"},
                {"id": "proj-bravo", "engagement_id": "eng-bravo", "currency": "USD"},
            ],
            "invoices": [
                {
                    "id": "inv-acme",
                    "client_id": "client-acme",
                    "engagement_id": "eng-acme",
                    "total": "10000.00",
                    "currency": "USD",
                    "issue_date": "2026-06-10",
                },
                {
                    "id": "inv-bravo",
                    "client_id": "client-bravo",
                    "engagement_id": "eng-bravo",
                    "total": "5000.00",
                    "currency": "USD",
                    "issue_date": "2026-06-11",
                },
            ],
            "time_entries": [],
            "employees": [],
            "project_expenses": [
                {
                    "id": "exp-acme",
                    "project_id": "proj-acme",
                    "amount": "2000.00",
                    "base_amount": None,
                    "currency": "USD",
                    "expense_date": "2026-06-12",
                },
                {
                    "id": "exp-bravo",
                    "project_id": "proj-bravo",
                    "amount": "500.00",
                    "base_amount": None,
                    "currency": "USD",
                    "expense_date": "2026-06-12",
                },
            ],
        },
    )

    svc = _make_svc(mock_db)
    result = svc.segment_profitability(group_by="service_line")

    by_segment = {row["segment_key"]: row for row in result}
    assert by_segment["advisory"]["segment_label"] == "Advisory"
    assert Decimal(by_segment["advisory"]["revenue"]) == Decimal("10000.00")
    assert Decimal(by_segment["advisory"]["expense_cost"]) == Decimal("2000.00")
    assert Decimal(by_segment["advisory"]["gross_margin"]) == Decimal("8000.00")
    assert by_segment["advisory"]["client_count"] == 1
    assert by_segment["tax"]["segment_label"] == "Tax"
    assert Decimal(by_segment["tax"]["gross_margin"]) == Decimal("4500.00")
