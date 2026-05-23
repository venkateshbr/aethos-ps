"""C15 — Invoice send + Stripe Payment Link.

Tests the contract of POST /invoices/{id}/send. Stripe Connect onboarding
is OPTIONAL — tenants without it should still get a PDF, just no Payment
Link. We don't fully exercise the Stripe side here (#94/#95 unresolved).
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


def test_send_unknown_invoice_returns_404(manager_a: httpx.Client) -> None:
    r = manager_a.post("/api/v1/invoices/00000000-0000-0000-0000-000000000000/send")
    assert r.status_code == 404, r.text


def test_send_cross_tenant_invoice_returns_404(
    manager_a: httpx.Client, world: SeedWorld, api_base_url: str
) -> None:
    """Create invoice as tenant B, then attempt to send as tenant A."""
    b = world.tenant_b.owner
    b_headers = {
        "Authorization": f"Bearer {mint_jwt(user_id=b.user_id, email=b.email, role='owner')}",
        "X-Tenant-ID": world.tenant_b.tenant_id,
    }
    body = {
        "engagement_id": world.tenant_b.engagement_ids[0],
        "client_id": world.tenant_b.client_ids[0],
        "currency": "GBP",
        "lines": [{"description": "x", "quantity": "1", "unit_price": "100.00"}],
    }
    with httpx.Client(base_url=api_base_url, headers=b_headers, timeout=15.0) as c:
        r = c.post("/api/v1/invoices", json=body)
        assert r.status_code == 201, r.text
        inv_id = r.json()["id"]

    r2 = manager_a.post(f"/api/v1/invoices/{inv_id}/send")
    assert r2.status_code == 404, (
        f"Cross-tenant invoice send leak: tenant A got {r2.status_code} on tenant B invoice"
    )


def test_send_requires_auth(client: httpx.Client) -> None:
    r = client.post("/api/v1/invoices/00000000-0000-0000-0000-000000000000/send")
    assert r.status_code == 401, r.text
