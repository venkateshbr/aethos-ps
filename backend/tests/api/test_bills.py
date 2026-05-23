"""C19 — Bills CRUD + approve flow.

Covers POST/GET /api/v1/bills, approve, and the cross-tenant/aging filters.
"""

from __future__ import annotations

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld, mint_jwt

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_billing,
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


@pytest.fixture
def admin_a(api_base_url: str, world: SeedWorld) -> httpx.Client:
    u = world.tenant_a.owner
    h = {
        "Authorization": f"Bearer {mint_jwt(user_id=u.user_id, email=u.email, role='admin')}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=h, timeout=15.0) as c:
        yield c


def _bill_payload(world: SeedWorld) -> dict:
    """Bill schema (per app/models/bills.py): client_id (vendor kind),
    line.amount required (caller computes quantity * unit_price)."""
    return {
        "client_id": world.tenant_a.vendor_ids[0],
        "vendor_invoice_number": f"VEND-{world.run_id[:6]}-001",
        "issue_date": "2026-05-23",
        "due_date": "2026-06-22",
        "currency": "USD",
        "lines": [
            {
                "description": "AWS hosting May",
                "quantity": "1",
                "unit_price": "850.00",
                "amount": "850.00",
            },
            {
                "description": "Slack team",
                "quantity": "8",
                "unit_price": "12.50",
                "amount": "100.00",
            },
        ],
    }


def test_create_bill_with_lines_sums_correctly(manager_a: httpx.Client, world: SeedWorld) -> None:
    from decimal import Decimal

    r = manager_a.post("/api/v1/bills", json=_bill_payload(world))
    assert r.status_code in (200, 201), r.text
    body = r.json()
    # 850 + 100 = 950
    assert Decimal(body["subtotal"]) == Decimal("950.00"), body
    assert body["status"] == "draft"


def test_list_bills_tenant_scoped(manager_a: httpx.Client, world: SeedWorld) -> None:
    r = manager_a.get("/api/v1/bills")
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body.get("items", body) if isinstance(body, dict) else body
    for row in rows:
        assert row["tenant_id"] == world.tenant_a.tenant_id


def test_create_bill_cross_tenant_vendor_blocked(
    manager_a: httpx.Client, world: SeedWorld
) -> None:
    """The #92 sweep — a client_id from tenant B must 404, not pass.

    Bills schema uses ``client_id`` (the clients table holds both customer
    and vendor kinds). Service must verify the client is in the caller's
    tenant before insert.
    """
    payload = _bill_payload(world)
    # Override with tenant B's vendor — the service must reject as 404
    payload["client_id"] = world.tenant_b.vendor_ids[0]
    payload["vendor_invoice_number"] = f"VEND-CROSS-{world.run_id[:6]}"
    r = manager_a.post("/api/v1/bills", json=payload)
    assert r.status_code in (400, 404, 422), (
        f"Cross-tenant client_id accepted by bills: {r.status_code}, body={r.text[:200]}"
    )


def test_bills_aging_tenant_scoped(manager_a: httpx.Client) -> None:
    """Aging report (sub-endpoint of bills) returns 200 for a real tenant."""
    r = manager_a.get("/api/v1/bills/aging")
    assert r.status_code == 200, r.text


def test_manager_cannot_approve_bill_admin_can(
    manager_a: httpx.Client, admin_a: httpx.Client, world: SeedWorld
) -> None:
    """C19 RBAC — only admin/owner can approve a bill (parallel to invoice rule)."""
    payload = _bill_payload(world)
    payload["vendor_invoice_number"] = f"VEND-RBAC-{world.run_id[:6]}"
    r = manager_a.post("/api/v1/bills", json=payload)
    assert r.status_code in (200, 201), r.text
    bill_id = r.json()["id"]

    rm = manager_a.patch(f"/api/v1/bills/{bill_id}/approve")
    assert rm.status_code == 403, f"Manager allowed to approve: {rm.status_code}, body={rm.text[:200]}"

    ra = admin_a.patch(f"/api/v1/bills/{bill_id}/approve")
    assert ra.status_code in (200, 409), ra.text
