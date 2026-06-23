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
    invoices = [{"engagement_id": "eng-1", "total": "10000.00", "currency": "USD"}]
    expenses = [
        {"project_id": "proj-1", "amount": "3000.00"},
        {"project_id": "proj-1", "amount": "2000.00"},
    ]

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
    time_entries = [
        {"project_id": "proj-2", "hours": "5.0"},
        {"project_id": "proj-2", "hours": "3.0"},
    ]
    rate_lines = [{"rate_card_id": "rc-1", "rate": "150.00"}]

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


def test_backlog_forecast_uses_contract_billing_wip_and_milestones(
    mock_db: MagicMock,
) -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _route_tables(
        mock_db,
        {
            "engagements": [
                {
                    "id": "eng-risk",
                    "name": "Risky Transformation",
                    "client_id": "client-acme",
                    "billing_arrangement": "fixed_fee",
                    "total_value": "10000.00",
                    "currency": "USD",
                    "service_line": "advisory",
                    "status": "active",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-30",
                    "clients": {"id": "client-acme", "name": "Acme Corp"},
                }
            ],
            "projects": [
                {
                    "id": "proj-risk",
                    "name": "Risky Project",
                    "engagement_id": "eng-risk",
                    "budget": "10000.00",
                    "budget_hours": "100.00",
                    "status": "active",
                    "start_date": "2026-06-01",
                    "end_date": yesterday,
                    "currency": "USD",
                }
            ],
            "engagement_billing_terms": [],
            "invoices": [
                {
                    "engagement_id": "eng-risk",
                    "total": "6000.00",
                    "status": "approved",
                    "issue_date": "2026-06-15",
                }
            ],
            "project_phases": [
                {
                    "id": "phase-risk",
                    "project_id": "proj-risk",
                    "name": "Discovery",
                    "status": "active",
                    "start_date": "2026-06-01",
                    "end_date": yesterday,
                    "budget": "2500.00",
                    "order_index": 1,
                }
            ],
        },
    )
    svc = _make_svc(mock_db)
    svc.wip = MagicMock(
        return_value=[
            {
                "project_id": "proj-risk",
                "project_name": "Risky Project",
                "wip_value": "1500.00",
            }
        ]
    )
    svc.project_health_scores = MagicMock(
        return_value=[
            {
                "project_id": "proj-risk",
                "risk_level": "at_risk",
                "health_score": 55,
            }
        ]
    )

    result = svc.backlog_forecast()

    assert len(result) == 1
    row = result[0]
    assert row["contracted_value"] == "10000.00"
    assert row["billed_to_date"] == "6000.00"
    assert row["unbilled_wip"] == "1500.00"
    assert row["recognized_backlog"] == "4000.00"
    assert row["delivery_backlog"] == "2500.00"
    assert row["overdue_milestone_count"] == 1
    assert row["risk_level"] == "critical"


def test_milestone_risk_includes_overdue_and_near_due_items(
    mock_db: MagicMock,
) -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    near_due = (date.today() + timedelta(days=5)).isoformat()
    _route_tables(
        mock_db,
        {
            "projects": [
                {
                    "id": "proj-risk",
                    "name": "Risky Project",
                    "engagement_id": "eng-risk",
                    "status": "active",
                    "start_date": "2026-06-01",
                    "end_date": near_due,
                    "engagements": {
                        "id": "eng-risk",
                        "name": "Risky Transformation",
                        "service_line": "advisory",
                    },
                }
            ],
            "project_phases": [
                {
                    "id": "phase-overdue",
                    "project_id": "proj-risk",
                    "name": "Discovery",
                    "status": "active",
                    "start_date": "2026-06-01",
                    "end_date": yesterday,
                    "budget": "2500.00",
                    "order_index": 1,
                },
                {
                    "id": "phase-near",
                    "project_id": "proj-risk",
                    "name": "Board Pack",
                    "status": "active",
                    "start_date": "2026-06-01",
                    "end_date": near_due,
                    "budget": "2500.00",
                    "order_index": 2,
                },
            ],
        },
    )
    svc = _make_svc(mock_db)
    svc.project_health_scores = MagicMock(
        return_value=[
            {
                "project_id": "proj-risk",
                "risk_level": "critical",
                "health_score": 35,
            }
        ]
    )

    result = svc.milestone_risk()

    assert [row["milestone_id"] for row in result] == ["phase-overdue", "phase-near"]
    assert result[0]["risk_level"] == "critical"
    assert result[0]["days_until_due"] == -1
    assert result[1]["risk_level"] == "critical"
    assert result[1]["days_until_due"] == 5


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


def test_client_group_profitability_rolls_up_member_clients(mock_db: MagicMock) -> None:
    """Client group profitability aggregates member client facts."""
    _route_tables(
        mock_db,
        {
            "client_groups": [
                {
                    "id": "group-acme",
                    "name": "Acme Family Office",
                    "group_type": "family_office",
                    "primary_client_id": "client-acme",
                    "billing_client_id": "client-acme",
                    "currency": "USD",
                    "status": "active",
                },
            ],
            "client_group_members": [
                {
                    "id": "member-acme",
                    "group_id": "group-acme",
                    "client_id": "client-acme",
                    "relationship_role": "parent",
                    "is_primary": True,
                    "clients": {
                        "id": "client-acme",
                        "name": "Acme Corp",
                        "kind": "customer",
                    },
                },
                {
                    "id": "member-bravo",
                    "group_id": "group-acme",
                    "client_id": "client-bravo",
                    "relationship_role": "portfolio_company",
                    "is_primary": False,
                    "clients": {
                        "id": "client-bravo",
                        "name": "Bravo Ltd",
                        "kind": "both",
                    },
                },
            ],
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
    result = svc.client_group_profitability(
        period_start="2026-06-01",
        period_end="2026-06-30",
    )

    assert len(result) == 1
    row = result[0]
    assert row["client_group_id"] == "group-acme"
    assert row["client_group_name"] == "Acme Family Office"
    assert row["group_type"] == "family_office"
    assert row["member_count"] == 2
    assert [member["client_id"] for member in row["members"]] == [
        "client-acme",
        "client-bravo",
    ]
    assert row["service_lines"] == ["advisory", "tax"]
    assert Decimal(row["revenue"]) == Decimal("15000.00")
    assert Decimal(row["labor_cost"]) == Decimal("1600.00")
    assert Decimal(row["expense_cost"]) == Decimal("1500.00")
    assert Decimal(row["gross_margin"]) == Decimal("11900.00")
    assert row["gross_margin_pct"] == 79.3
    assert row["client_count"] == 2


def test_practice_dashboard_combines_financial_health_and_capacity(
    mock_db: MagicMock,
) -> None:
    """Practice dashboard combines service-line margin, risk, and capacity."""
    svc = _make_svc(mock_db)
    svc.segment_profitability = MagicMock(
        return_value=[
            {
                "segment_key": "advisory",
                "revenue": "10000.00",
                "labor_cost": "3000.00",
                "expense_cost": "1000.00",
                "total_cost": "4000.00",
                "gross_margin": "6000.00",
                "gross_margin_pct": 60.0,
                "profitability_status": "strong",
                "recommended_action": "Protect this relationship.",
                "client_count": 2,
                "engagement_count": 3,
                "project_count": 4,
                "invoice_count": 5,
            }
        ]
    )
    svc.project_health_scores = MagicMock(
        return_value=[
            {
                "project_id": "proj-critical",
                "service_line": "advisory",
                "health_score": 42,
                "risk_level": "critical",
                "recommended_actions": ["Escalate delivery risk."],
            },
            {
                "project_id": "proj-healthy",
                "service_line": "advisory",
                "health_score": 90,
                "risk_level": "healthy",
                "recommended_actions": [],
            },
        ]
    )
    svc.capacity_planning = MagicMock(
        return_value=[
            {
                "employee_id": "emp-over",
                "practice_area": "advisory",
                "capacity_hours": "40.00",
                "logged_hours": "46.00",
                "billable_hours": "44.00",
                "capacity_status": "overallocated",
                "recommended_action": "Rebalance assignments.",
            }
        ]
    )

    result = svc.practice_dashboard(
        period_start="2026-06-01",
        period_end="2026-06-30",
    )

    assert len(result) == 1
    row = result[0]
    assert row["practice_key"] == "advisory"
    assert row["practice_label"] == "Advisory"
    assert Decimal(row["gross_margin"]) == Decimal("6000.00")
    assert row["active_project_count"] == 2
    assert row["critical_project_count"] == 1
    assert row["avg_project_health_score"] == 66.0
    assert row["employee_count"] == 1
    assert Decimal(row["capacity_hours"]) == Decimal("40.00")
    assert Decimal(row["logged_hours"]) == Decimal("46.00")
    assert row["avg_utilization_pct"] == 115.0
    assert row["capacity_status_counts"]["overallocated"] == 1
    assert "Escalate delivery risk." in row["recommended_actions"]
    assert "Rebalance overallocated staff before accepting new work." in row["recommended_actions"]


def test_pricing_staffing_recommendations_composes_margin_health_and_capacity(
    mock_db: MagicMock,
) -> None:
    """Recommendations stay evidence-backed by composing existing reports."""
    svc = _make_svc(mock_db)
    svc._profitability_facts = MagicMock(return_value={})
    svc._client_profitability_from_facts = MagicMock(
        return_value=[
            {
                "client_id": "client-acme",
                "client_name": "Acme Corp",
                "service_lines": ["advisory"],
                "revenue": "10000.00",
                "total_cost": "9000.00",
                "gross_margin_pct": 10.0,
                "labor_hours": "50.00",
            },
            {
                "client_id": "client-healthy",
                "client_name": "Healthy Co",
                "service_lines": ["tax"],
                "revenue": "20000.00",
                "total_cost": "9000.00",
                "gross_margin_pct": 55.0,
                "labor_hours": "30.00",
            },
        ]
    )
    svc._segment_profitability_from_facts = MagicMock(
        return_value=[
            {
                "segment_key": "advisory",
                "segment_label": "Advisory",
                "revenue": "12000.00",
                "labor_cost": "8500.00",
                "expense_cost": "1340.00",
                "total_cost": "9840.00",
                "gross_margin": "2160.00",
                "gross_margin_pct": 18.0,
                "profitability_status": "critical",
                "recommended_action": "Review practice margin.",
                "client_count": 1,
                "engagement_count": 1,
                "project_count": 1,
                "invoice_count": 1,
            }
        ]
    )
    svc.project_health_scores = MagicMock(
        return_value=[
            {
                "project_id": "proj-risk",
                "project_name": "Risky Project",
                "service_line": "advisory",
                "health_score": 45,
                "risk_level": "critical",
                "drivers": [
                    {
                        "code": "low_margin",
                        "severity": "critical",
                        "summary": "Project margin is below target.",
                    },
                    {
                        "code": "scope_creep",
                        "severity": "watch",
                        "summary": "Recent non-billable time is high.",
                    },
                ],
            }
        ]
    )
    svc.capacity_planning = MagicMock(
        return_value=[
            {
                "employee_id": "emp-over",
                "employee_name": "Asha Rao",
                "practice_area": "advisory",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "capacity_hours": "40.00",
                "logged_hours": "52.00",
                "billable_hours": "50.00",
                "utilization_pct": 130.0,
                "billable_utilization_pct": 125.0,
                "capacity_status": "overallocated",
            },
            {
                "employee_id": "emp-under",
                "employee_name": "Ben Low",
                "practice_area": "advisory",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "capacity_hours": "40.00",
                "logged_hours": "10.00",
                "billable_hours": "8.00",
                "utilization_pct": 25.0,
                "billable_utilization_pct": 20.0,
                "capacity_status": "underutilized",
            },
        ]
    )

    result = svc.pricing_staffing_recommendations(
        period_start="2026-06-01",
        period_end="2026-06-30",
    )

    by_id = {row["recommendation_id"]: row for row in result}
    client = by_id["pricing:client:client-acme"]
    assert client["priority"] == "critical"
    assert client["metrics"]["pricing_gap_to_target"] == "5000.00"
    assert client["metrics"]["current_effective_rate"] == "200.00"
    assert client["metrics"]["target_effective_rate"] == "300.00"
    assert client["metrics"]["required_rate_uplift_pct"] == 50.0
    assert "pricing:client:client-healthy" not in by_id

    project = by_id["pricing:project:proj-risk"]
    assert project["priority"] == "critical"
    assert project["metrics"]["driver_codes"] == ["low_margin"]

    staffing = by_id["staffing:employee:emp-over"]
    assert staffing["priority"] == "critical"
    assert staffing["metrics"]["overload_hours"] == "12.00"
    assert staffing["metrics"]["candidate_names"] == ["Ben Low"]

    bench = by_id["staffing:bench:emp-under"]
    assert bench["priority"] == "medium"
    assert bench["metrics"]["available_hours"] == "30.00"

    practice = by_id["practice:advisory"]
    assert practice["priority"] == "critical"
    assert practice["metrics"]["critical_project_count"] == 1


def test_scope_change_advisor_uses_completed_project_comparables(
    mock_db: MagicMock,
) -> None:
    """Scope advisor values overruns with completed-project effective rates."""
    _route_tables(
        mock_db,
        {
            "projects": [
                {
                    "id": "proj-current",
                    "name": "Current Advisory Project",
                    "status": "active",
                    "budget_hours": "100.00",
                    "currency": "USD",
                    "engagements": {
                        "id": "eng-current",
                        "name": "Current Engagement",
                        "billing_arrangement": "capped_tm",
                        "total_value": "25000.00",
                        "service_line": "advisory",
                    },
                },
                {
                    "id": "proj-comp-1",
                    "name": "Comparable One",
                    "status": "completed",
                    "budget_hours": "90.00",
                    "currency": "USD",
                    "engagements": {
                        "id": "eng-comp-1",
                        "name": "Comparable One Engagement",
                        "billing_arrangement": "capped_tm",
                        "total_value": "20000.00",
                        "service_line": "advisory",
                    },
                },
                {
                    "id": "proj-comp-2",
                    "name": "Comparable Two",
                    "status": "completed",
                    "budget_hours": "70.00",
                    "currency": "USD",
                    "engagements": {
                        "id": "eng-comp-2",
                        "name": "Comparable Two Engagement",
                        "billing_arrangement": "time_and_materials",
                        "total_value": "15000.00",
                        "service_line": "advisory",
                    },
                },
                {
                    "id": "proj-tax",
                    "name": "Tax Comparable",
                    "status": "completed",
                    "budget_hours": "60.00",
                    "currency": "USD",
                    "engagements": {
                        "id": "eng-tax",
                        "name": "Tax Engagement",
                        "billing_arrangement": "capped_tm",
                        "total_value": "12000.00",
                        "service_line": "tax",
                    },
                },
            ],
            "time_entries": [
                {
                    "project_id": "proj-comp-1",
                    "hours": "80.00",
                    "billable": True,
                    "billing_status": "billed",
                    "date": "2026-05-01",
                },
                {
                    "project_id": "proj-comp-2",
                    "hours": "60.00",
                    "billable": True,
                    "billing_status": "billed",
                    "date": "2026-05-01",
                },
                {
                    "project_id": "proj-tax",
                    "hours": "40.00",
                    "billable": True,
                    "billing_status": "billed",
                    "date": "2026-05-01",
                },
            ],
        },
    )

    svc = _make_svc(mock_db)
    svc.project_health_scores = MagicMock(
        return_value=[
            {
                "project_id": "proj-current",
                "project_name": "Current Advisory Project",
                "service_line": "advisory",
                "risk_level": "critical",
                "health_score": 45,
                "metrics": {
                    "logged_hours": "120.00",
                    "budget_hours": "100.00",
                    "budget_burn_pct": 120.0,
                    "wip_value": "1500.00",
                    "unbilled_hours": "6.00",
                },
                "drivers": [
                    {
                        "code": "budget_hours_burn",
                        "label": "Budget hours exceeded",
                        "severity": "critical",
                        "impact": 25,
                        "metric": "120.0%",
                        "threshold": "100%",
                        "summary": "Logged hours exceed budget.",
                        "recommended_action": "Review scope.",
                    },
                    {
                        "code": "scope_creep",
                        "label": "Scope creep risk",
                        "severity": "watch",
                        "impact": 10,
                        "metric": "25.0%",
                        "threshold": "20%",
                        "summary": "Recent non-billable time is high.",
                        "recommended_action": "Review non-billable work.",
                    },
                ],
            },
            {
                "project_id": "proj-healthy",
                "project_name": "Healthy Project",
                "service_line": "tax",
                "risk_level": "healthy",
                "health_score": 95,
                "metrics": {},
                "drivers": [],
            },
        ]
    )
    svc.project_pnl = MagicMock(
        return_value=[
            {
                "project_id": "proj-comp-1",
                "revenue": "20000.00",
                "direct_cost": "9000.00",
                "gross_margin_pct": 55.0,
            },
            {
                "project_id": "proj-comp-2",
                "revenue": "15000.00",
                "direct_cost": "7500.00",
                "gross_margin_pct": 50.0,
            },
            {
                "project_id": "proj-tax",
                "revenue": "12000.00",
                "direct_cost": "6000.00",
                "gross_margin_pct": 50.0,
            },
        ]
    )

    result = svc.scope_change_advisor(
        period_start="2026-06-01",
        period_end="2026-06-30",
    )

    assert len(result) == 1
    row = result[0]
    assert row["advisor_id"] == "scope:proj-current"
    assert row["scope_signals"] == ["budget_hours_burn", "scope_creep"]
    assert row["current_metrics"]["overrun_hours"] == "20.00"
    assert row["suggested_fee_adjustment"] == "5000.00"
    assert row["suggested_fee_basis"] == "historical_effective_rate"
    assert row["confidence"] == "medium"
    assert [comp["project_id"] for comp in row["comparable_projects"]] == [
        "proj-comp-1",
        "proj-comp-2",
    ]
    assert row["comparable_projects"][0]["effective_rate"] == "250.00"
    assert "scope-change request" in row["recommended_action"]


def test_action_queue_composes_role_specific_items(
    mock_db: MagicMock,
) -> None:
    """Action queue turns existing report evidence into persona queues."""
    svc = _make_svc(mock_db)
    svc.ar_aging = MagicMock(
        return_value={
            "0_30": "1000.00",
            "31_60": "0.00",
            "61_90": "0.00",
            "over_90": "0.00",
            "total": "1000.00",
        }
    )
    svc.ap_aging = MagicMock(
        return_value={
            "0_30": "500.00",
            "31_60": "0.00",
            "61_90": "0.00",
            "over_90": "250.00",
            "total": "750.00",
        }
    )
    svc.project_health_scores = MagicMock(
        return_value=[
            {
                "project_id": "proj-risk",
                "project_name": "Risky Project",
                "service_line": "advisory",
                "health_score": 42,
                "risk_level": "critical",
                "drivers": [
                    {
                        "summary": "Margin and cap drawdown are critical.",
                    }
                ],
                "recommended_actions": ["Escalate project recovery."],
            }
        ]
    )
    svc.capacity_planning = MagicMock(
        return_value=[
            {
                "employee_id": "emp-over",
                "employee_name": "Asha Rao",
                "practice_area": "advisory",
                "capacity_status": "overallocated",
                "utilization_pct": 130.0,
                "capacity_hours": "40.00",
                "logged_hours": "52.00",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "recommended_action": "Reassign delivery work.",
            }
        ]
    )
    svc.backlog_forecast = MagicMock(
        return_value=[
            {
                "engagement_id": "eng-risk",
                "engagement_name": "Risky Transformation",
                "service_line": "advisory",
                "risk_level": "critical",
                "recognized_backlog": "4000.00",
                "unbilled_wip": "1500.00",
                "overdue_milestone_count": 1,
                "contracted_value": "10000.00",
                "delivery_backlog": "2500.00",
                "consumed_pct": 75.0,
                "recommended_action": "Escalate overdue delivery items.",
            }
        ]
    )
    svc.milestone_risk = MagicMock(
        return_value=[
            {
                "milestone_id": "phase-risk",
                "milestone_name": "Discovery",
                "project_id": "proj-risk",
                "project_name": "Risky Project",
                "service_line": "advisory",
                "due_date": "2026-06-30",
                "days_until_due": -1,
                "risk_level": "critical",
                "project_health_score": 42,
                "project_risk_level": "critical",
                "recommended_action": "Escalate the overdue milestone.",
            }
        ]
    )
    svc.pricing_staffing_recommendations = MagicMock(
        return_value=[
            {
                "recommendation_id": "pricing:client:client-acme",
                "recommendation_type": "pricing",
                "priority": "critical",
                "entity_type": "client",
                "entity_id": "client-acme",
                "entity_name": "Acme Corp",
                "service_line": "advisory",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "evidence": ["Gross margin is 10%."],
                "metrics": {"gross_margin_pct": 10.0},
                "recommended_action": "Reprice before more work.",
            }
        ]
    )
    svc.scope_change_advisor = MagicMock(
        return_value=[
            {
                "project_id": "proj-risk",
                "project_name": "Risky Project",
                "service_line": "advisory",
                "risk_level": "critical",
                "health_score": 42,
                "scope_signals": ["budget_hours_burn"],
                "suggested_fee_adjustment": "5000.00",
                "confidence": "medium",
                "drivers": [{"summary": "Budget hours exceeded."}],
                "recommended_action": "Prepare a scope-change request.",
            }
        ]
    )
    svc.practice_dashboard = MagicMock(
        return_value=[
            {
                "practice_key": "advisory",
                "practice_label": "Advisory",
                "critical_project_count": 1,
                "at_risk_project_count": 1,
                "gross_margin_pct": 18.0,
                "avg_project_health_score": 58.0,
                "recommended_actions": ["Run partner recovery review."],
            }
        ]
    )

    project_manager = svc.action_queue(role="project_manager", limit=20)
    partner = svc.action_queue(role="partner", limit=20)
    ap_clerk = svc.action_queue(role="ap_clerk", limit=20)

    assert {item["source_type"] for item in project_manager} >= {
        "project_health",
        "capacity",
        "milestone_risk",
        "scope_change",
    }
    assert all(item["role"] == "project_manager" for item in project_manager)

    assert {item["source_type"] for item in partner} >= {
        "backlog_forecast",
        "pricing_recommendation",
        "scope_change",
        "practice_dashboard",
    }
    assert all(item["role"] == "partner" for item in partner)

    assert [item["source_type"] for item in ap_clerk] == ["ap_aging"]
    assert ap_clerk[0]["priority"] == "high"
