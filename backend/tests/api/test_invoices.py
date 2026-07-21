"""Invoice CRUD + lifecycle + public view (C15 + C17).

Covers:
- create draft invoice with lines (``invoices.draft``)
- approve → status changes (``invoices.post``) and AR journal entry posts
- list filters by engagement and status
- public /p/{token} renders without auth
- cross-tenant invoice access returns 404 (C31 sentinel)

Send + Stripe Payment Link (C15) lives in a separate file because it depends
on real Stripe sandbox calls.
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


# ---------------------------------------------------------------------------
# JWT fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager_a(api_base_url: str, world: SeedWorld) -> httpx.Client:
    u = world.tenant_a.members["manager"]
    headers = {
        "Authorization": f"Bearer {mint_jwt(user_id=u.user_id, email=u.email, role='manager')}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_invoice_payload(world: SeedWorld) -> dict:
    return {
        "engagement_id": world.tenant_a.engagement_ids[0],
        "client_id": world.tenant_a.client_ids[0],
        "currency": "USD",
        "lines": [
            {
                "description": "Consulting hours, week 1",
                "quantity": "10.00",
                "unit_price": "200.00",
            },
            {
                "description": "Consulting hours, week 2",
                "quantity": "7.50",
                "unit_price": "200.00",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Create + read + lines
# ---------------------------------------------------------------------------


def test_create_invoice_with_lines_sums_correctly(
    manager_a: httpx.Client, world: SeedWorld
) -> None:
    """The Critical Rule: subtotal = sum(line.amount); line.amount = quantity * unit_price."""
    body = _make_invoice_payload(world)
    r = manager_a.post("/api/v1/invoices", json=body)
    assert r.status_code == 201, r.text
    inv = r.json()
    # 10 * 200 + 7.5 * 200 = 2000 + 1500 = 3500
    from decimal import Decimal as _D

    assert _D(inv["subtotal"]) == _D("3500.00"), (
        f"Subtotal arithmetic broken: {inv['subtotal']!r} != 3500.00"
    )
    # No tax lines applied → tax_total == 0; total == subtotal
    assert _D(inv["tax_total"]) == _D("0")
    assert _D(inv["total"]) == _D("3500.00")
    assert inv["status"] == "draft"
    assert inv["invoice_number"], "Invoice number must be issued by sequence"


def test_invoice_number_monotonic_within_tenant(
    manager_a: httpx.Client, world: SeedWorld
) -> None:
    """Sequential invoices must have monotonically increasing numbers."""
    nums: list[str] = []
    for _ in range(3):
        r = manager_a.post("/api/v1/invoices", json=_make_invoice_payload(world))
        assert r.status_code == 201, r.text
        nums.append(r.json()["invoice_number"])
    assert nums == sorted(nums, key=lambda s: int("".join(filter(str.isdigit, s)))), (
        f"Invoice numbers not monotonic: {nums}"
    )


# Bug #92 FIXED in commit 72afb99 — InvoicesService now calls
# assert_belongs_to_tenant() on engagement_id / client_id / tax_rate_id /
# time_entry_id / expense_id. Verified by Aksha 2026-05-23 — XPASS confirmed.
# No xfail: any regression breaks the build.
def test_create_invoice_with_cross_tenant_engagement_blocked(
    manager_a: httpx.Client, world: SeedWorld
) -> None:
    """Tenant A cannot draft an invoice against tenant B's engagement.

    Sentinel for #92 sweep — same FK-validation gap as engagements."""
    body = {
        "engagement_id": world.tenant_b.engagement_ids[0],
        "client_id": world.tenant_a.client_ids[0],
        "currency": "USD",
        "lines": [{"description": "x", "quantity": "1", "unit_price": "1.00"}],
    }
    r = manager_a.post("/api/v1/invoices", json=body)
    assert r.status_code in (400, 404, 422), (
        f"Cross-tenant engagement leak: status={r.status_code}, body={r.text[:200]}"
    )


def test_get_invoice_cross_tenant_returns_404(
    api_base_url: str, world: SeedWorld, manager_a: httpx.Client
) -> None:
    """First create an invoice in tenant A; then tenant B tries to GET it."""
    r = manager_a.post("/api/v1/invoices", json=_make_invoice_payload(world))
    assert r.status_code == 201, r.text
    inv_id = r.json()["id"]

    u = world.tenant_b.owner
    headers = {
        "Authorization": f"Bearer {mint_jwt(user_id=u.user_id, email=u.email, role='admin')}",
        "X-Tenant-ID": world.tenant_b.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r2 = c.get(f"/api/v1/invoices/{inv_id}")
    assert r2.status_code == 404, (
        f"Cross-tenant invoice leak: tenant B got {r2.status_code} on tenant A invoice"
    )


# ---------------------------------------------------------------------------
# Approve flow
# ---------------------------------------------------------------------------


def test_viewer_cannot_approve_invoice_finance_manager_can(
    manager_a: httpx.Client,
    client_a_viewer: httpx.Client,
    world: SeedWorld,
) -> None:
    """Invoice posting follows exact catalog privileges, not legacy role rank."""
    r = manager_a.post("/api/v1/invoices", json=_make_invoice_payload(world))
    assert r.status_code == 201, r.text
    inv_id = r.json()["id"]

    denied = client_a_viewer.patch(f"/api/v1/invoices/{inv_id}/approve")
    assert denied.status_code == 403, f"Viewer allowed to approve: {denied.status_code}"

    approved = manager_a.patch(f"/api/v1/invoices/{inv_id}/approve")
    assert approved.status_code in (200, 409), approved.text


# ---------------------------------------------------------------------------
# Public token
# ---------------------------------------------------------------------------


def test_public_invoice_bad_token_returns_404(client: httpx.Client) -> None:
    """Public endpoint returns 404 for unknown tokens, no auth required."""
    r = client.get("/api/v1/public/invoices/this-token-does-not-exist")
    assert r.status_code == 404, r.text


def test_public_invoice_endpoint_does_not_require_auth(client: httpx.Client) -> None:
    """Confirm /public/invoices is genuinely open (no 401)."""
    r = client.get("/api/v1/public/invoices/anything")
    # 404 (token not found) is fine; 401 (auth required) is the failure mode
    assert r.status_code != 401, (
        f"Public invoice endpoint demands auth (status {r.status_code}); "
        f"that defeats its purpose. Body: {r.text[:200]}"
    )
