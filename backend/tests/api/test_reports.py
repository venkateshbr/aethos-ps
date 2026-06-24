"""C24 — Reports endpoints (6 endpoints).

AR/AP aging, P&L by project, utilization, WIP, revenue by engagement.

Smoke level: each endpoint must return 200 with a JSON body shaped like
a report object, scoped to tenant A. Cross-tenant tests use tenant B's
JWT and assert different (or empty) data.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_reports,
    pytest.mark.requires_supabase,
]


REPORT_ENDPOINTS = [
    "/api/v1/reports/ar-aging",
    "/api/v1/reports/ap-aging",
    "/api/v1/reports/project-pnl",
    "/api/v1/reports/project-health",
    "/api/v1/reports/capacity-planning",
    "/api/v1/reports/client-profitability",
    "/api/v1/reports/segment-profitability",
    "/api/v1/reports/practice-dashboard",
    "/api/v1/reports/pricing-staffing-recommendations",
    "/api/v1/reports/scope-change-advisor",
    "/api/v1/reports/utilization",
    # /api/v1/reports/wip is xfailed separately (bug #99 — references
    # projects.rate_card_id which does not exist).
    "/api/v1/reports/revenue-by-engagement",
]

REPORT_REQUEST_TIMEOUT = 30.0


@pytest.mark.parametrize("path", REPORT_ENDPOINTS)
def test_report_endpoint_returns_200(client_a: httpx.Client, path: str) -> None:
    """Each report endpoint returns 200 for an authenticated tenant."""
    r = client_a.get(path, timeout=REPORT_REQUEST_TIMEOUT)
    assert r.status_code == 200, f"{path} → {r.status_code} {r.text[:200]}"
    # All reports return JSON objects
    body = r.json()
    assert isinstance(body, (dict, list)), f"{path} returned non-JSON-object: {type(body).__name__}"


def test_wip_report_returns_200(client_a: httpx.Client) -> None:
    """WIP report — currently bug #99 makes it 500."""
    r = client_a.get("/api/v1/reports/wip", timeout=REPORT_REQUEST_TIMEOUT)
    assert r.status_code == 200, f"/reports/wip → {r.status_code} {r.text[:200]}"


_AUTH_CHECK_ENDPOINTS = [*REPORT_ENDPOINTS, "/api/v1/reports/wip"]


@pytest.mark.parametrize("path", _AUTH_CHECK_ENDPOINTS)
def test_report_endpoint_requires_auth(client: httpx.Client, path: str) -> None:
    """Reports must require auth — this is enforced at the FastAPI dependency
    layer BEFORE the handler runs, so bug #99 (wip 500) does not affect this."""
    r = client.get(path)
    assert r.status_code == 401, f"{path} returned {r.status_code} without auth — should be 401"


def test_ar_aging_returns_buckets(client_a: httpx.Client) -> None:
    """AR aging shape: should expose bucket fields (current, 30, 60, 90, 120+)."""
    r = client_a.get("/api/v1/reports/ar-aging", timeout=REPORT_REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    # Body is either a list of clients with aging, or an object with buckets
    if isinstance(body, dict):
        # Look for any of: buckets, items, rows, aging
        assert any(k in body for k in ("buckets", "items", "rows", "aging", "total")), body


def test_project_health_report_shape(client_a: httpx.Client) -> None:
    """Project health returns ranked rows with score, drivers, and metrics."""
    r = client_a.get("/api/v1/reports/project-health", timeout=REPORT_REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert {
            "project_id",
            "project_name",
            "health_score",
            "risk_level",
            "drivers",
            "metrics",
            "recommended_actions",
        } <= set(row)
        assert 0 <= row["health_score"] <= 100


def test_capacity_planning_report_shape(client_a: httpx.Client) -> None:
    """Capacity planning returns employee utilization rows for the work window."""
    r = client_a.get("/api/v1/reports/capacity-planning", timeout=REPORT_REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert {
            "employee_id",
            "employee_name",
            "capacity_hours",
            "logged_hours",
            "utilization_pct",
            "capacity_status",
            "active_assignments",
            "recommended_action",
        } <= set(row)
        assert row["capacity_status"] in {
            "overallocated",
            "full",
            "underutilized",
            "balanced",
        }


def test_client_profitability_report_shape(client_a: httpx.Client) -> None:
    """Client profitability returns component totals and margin status."""
    r = client_a.get("/api/v1/reports/client-profitability", timeout=REPORT_REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert {
            "client_id",
            "client_name",
            "revenue",
            "labor_cost",
            "expense_cost",
            "total_cost",
            "gross_margin",
            "gross_margin_pct",
            "profitability_status",
            "recommended_action",
        } <= set(row)
        assert row["profitability_status"] in {
            "strong",
            "healthy",
            "watch",
            "critical",
        }


def test_segment_profitability_report_shape(client_a: httpx.Client) -> None:
    """Segment profitability supports service-line and client-kind grouping."""
    r = client_a.get(
        "/api/v1/reports/segment-profitability?group_by=client_kind",
        timeout=REPORT_REQUEST_TIMEOUT,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert {
            "segment_type",
            "segment_key",
            "segment_label",
            "revenue",
            "labor_cost",
            "expense_cost",
            "gross_margin",
            "gross_margin_pct",
        } <= set(row)
        assert row["segment_type"] == "client_kind"


def test_practice_dashboard_report_shape(client_a: httpx.Client) -> None:
    """Practice dashboard returns margin, project health, and capacity signals."""
    r = client_a.get("/api/v1/reports/practice-dashboard", timeout=REPORT_REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert {
            "practice_key",
            "practice_label",
            "revenue",
            "gross_margin",
            "profitability_status",
            "active_project_count",
            "critical_project_count",
            "employee_count",
            "capacity_status_counts",
            "recommended_actions",
        } <= set(row)
        assert isinstance(row["recommended_actions"], list)


def test_pricing_staffing_recommendations_report_shape(client_a: httpx.Client) -> None:
    """Pricing/staffing recommendations return auditable evidence and metrics."""
    r = client_a.get(
        "/api/v1/reports/pricing-staffing-recommendations",
        timeout=REPORT_REQUEST_TIMEOUT,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert {
            "recommendation_id",
            "recommendation_type",
            "priority",
            "entity_type",
            "entity_id",
            "entity_name",
            "evidence",
            "metrics",
            "recommended_action",
        } <= set(row)
        assert row["priority"] in {"critical", "high", "medium", "low"}
        assert isinstance(row["evidence"], list)
        assert isinstance(row["metrics"], dict)


def test_scope_change_advisor_report_shape(client_a: httpx.Client) -> None:
    """Scope-change advisor returns current risk and comparable evidence."""
    r = client_a.get("/api/v1/reports/scope-change-advisor", timeout=REPORT_REQUEST_TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert {
            "advisor_id",
            "project_id",
            "project_name",
            "scope_signals",
            "drivers",
            "current_metrics",
            "comparable_projects",
            "suggested_fee_adjustment",
            "suggested_fee_basis",
            "confidence",
            "recommended_action",
        } <= set(row)
        assert isinstance(row["scope_signals"], list)
        assert isinstance(row["current_metrics"], dict)
        assert isinstance(row["comparable_projects"], list)
        assert row["confidence"] in {"high", "medium", "low"}
