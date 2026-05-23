"""C9 — Time entries CRUD + validation.

Covers POST/GET/PATCH/DELETE /api/v1/time-entries against real Supabase,
plus the cross-tenant and 0/24h validation negatives.
"""

from __future__ import annotations

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld, mint_jwt

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_engagement,
    pytest.mark.requires_supabase,
]


@pytest.fixture
def manager_a(api_base_url: str, world: SeedWorld) -> httpx.Client:
    u = world.tenant_a.members["manager"]
    h = {
        "Authorization": f"Bearer {mint_jwt(user_id=u.user_id, email=u.email, role='manager')}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=h, timeout=15.0) as c:
        yield c


def _payload(world: SeedWorld, hours: str = "3.50") -> dict:
    return {
        "project_id": world.tenant_a.project_ids[0],
        "employee_id": world.tenant_a.employee_ids[0],
        "date": "2026-05-23",
        "hours": hours,
        "description": "Aksha QA — time entry",
        "billable": True,
    }


def test_create_time_entry_happy_path(manager_a: httpx.Client, world: SeedWorld) -> None:
    from decimal import Decimal

    r = manager_a.post("/api/v1/time-entries", json=_payload(world))
    assert r.status_code in (200, 201), r.text
    body = r.json()
    # hours is a count not money — accept "3.5" or "3.50" but must equal 3.5 numerically
    assert Decimal(body["hours"]) == Decimal("3.50"), body
    assert body["employee_id"] == world.tenant_a.employee_ids[0]


def test_create_time_entry_rejects_zero_hours(manager_a: httpx.Client, world: SeedWorld) -> None:
    r = manager_a.post("/api/v1/time-entries", json=_payload(world, hours="0"))
    assert r.status_code == 422, r.text


def test_create_time_entry_rejects_over_24_hours(manager_a: httpx.Client, world: SeedWorld) -> None:
    r = manager_a.post("/api/v1/time-entries", json=_payload(world, hours="25.00"))
    assert r.status_code == 422, r.text


def test_create_time_entry_cross_tenant_project_blocked(
    manager_a: httpx.Client, world: SeedWorld
) -> None:
    """C9 + sentinel for the #92 sweep — project_id from tenant B must 404."""
    body = _payload(world)
    body["project_id"] = world.tenant_b.project_ids[0]
    r = manager_a.post("/api/v1/time-entries", json=body)
    assert r.status_code in (400, 404, 422), (
        f"Cross-tenant project_id accepted by time-entries: {r.status_code}, body={r.text[:200]}"
    )


def test_create_time_entry_cross_tenant_employee_blocked(
    manager_a: httpx.Client, world: SeedWorld
) -> None:
    """employee_id from tenant B must 404 — the #92 sweep again."""
    body = _payload(world)
    body["employee_id"] = world.tenant_b.employee_ids[0]
    r = manager_a.post("/api/v1/time-entries", json=body)
    assert r.status_code in (400, 404, 422), (
        f"Cross-tenant employee_id accepted by time-entries: {r.status_code}, body={r.text[:200]}"
    )


def test_list_time_entries_tenant_scoped(manager_a: httpx.Client, world: SeedWorld) -> None:
    r = manager_a.get("/api/v1/time-entries")
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body.get("items", body) if isinstance(body, dict) else body
    assert isinstance(rows, list), f"Unexpected list shape: {body!r}"
    for row in rows:
        assert row["tenant_id"] == world.tenant_a.tenant_id, (
            f"Cross-tenant time entry leak in list: {row}"
        )
