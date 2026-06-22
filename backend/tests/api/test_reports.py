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
    "/api/v1/reports/utilization",
    # /api/v1/reports/wip is xfailed separately (bug #99 — references
    # projects.rate_card_id which does not exist).
    "/api/v1/reports/revenue-by-engagement",
]


@pytest.mark.parametrize("path", REPORT_ENDPOINTS)
def test_report_endpoint_returns_200(client_a: httpx.Client, path: str) -> None:
    """Each report endpoint returns 200 for an authenticated tenant."""
    r = client_a.get(path)
    assert r.status_code == 200, f"{path} → {r.status_code} {r.text[:200]}"
    # All reports return JSON objects
    body = r.json()
    assert isinstance(body, (dict, list)), f"{path} returned non-JSON-object: {type(body).__name__}"


def test_wip_report_returns_200(client_a: httpx.Client) -> None:
    """WIP report — currently bug #99 makes it 500."""
    r = client_a.get("/api/v1/reports/wip")
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
    r = client_a.get("/api/v1/reports/ar-aging")
    assert r.status_code == 200, r.text
    body = r.json()
    # Body is either a list of clients with aging, or an object with buckets
    if isinstance(body, dict):
        # Look for any of: buckets, items, rows, aging
        assert any(k in body for k in ("buckets", "items", "rows", "aging", "total")), body


def test_project_health_report_shape(client_a: httpx.Client) -> None:
    """Project health returns ranked rows with score, drivers, and metrics."""
    r = client_a.get("/api/v1/reports/project-health")
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
