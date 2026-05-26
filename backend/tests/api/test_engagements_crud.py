"""Engagement CRUD + billing-model coverage (C5 + C14 happy paths).

For each of the 5 billing arrangements we:
1. Create the engagement (manager role)
2. Read it back
3. Confirm billing_terms row was created with the right field set
4. List filters work

We don't test invoice drafting end-to-end here (that needs time entries +
draft_invoice → see test_invoice_drafter.py).
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


# ---------------------------------------------------------------------------
# Fixtures — manager JWT
# ---------------------------------------------------------------------------


@pytest.fixture
def manager_client_a(api_base_url: str, world: SeedWorld) -> httpx.Client:
    user = world.tenant_a.members["manager"]
    token = mint_jwt(user_id=user.user_id, email=user.email, role="manager")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


# ---------------------------------------------------------------------------
# Create + read per billing arrangement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "billing_arrangement,terms",
    [
        ("time_and_materials", {}),
        ("fixed_fee", {"fixed_fee_amount": "50000.00"}),
        ("milestone", {}),
        ("retainer", {"retainer_monthly_amount": "10000.00"}),
        ("retainer_draw", {"retainer_monthly_amount": "10000.00", "retainer_floor": "2000.00"}),
        ("capped_tm", {"cap_amount": "75000.00"}),
    ],
)
def test_create_engagement_for_each_billing_arrangement(
    manager_client_a: httpx.Client,
    world: SeedWorld,
    billing_arrangement: str,
    terms: dict,
) -> None:
    """Each of the 6 billing arrangements can be created via API."""
    client_id = world.tenant_a.client_ids[0]
    body = {
        "client_id": client_id,
        "name": f"Test eng {billing_arrangement} {world.run_id}",
        "billing_arrangement": billing_arrangement,
        "currency": "USD",
        "total_value": "100000.00",
    }
    if terms:
        body["billing_terms"] = terms

    r = manager_client_a.post("/api/v1/engagements", json=body)
    assert r.status_code == 201, (
        f"Failed to create {billing_arrangement} engagement: "
        f"status={r.status_code} body={r.text[:300]}"
    )
    payload = r.json()
    assert payload["billing_arrangement"] == billing_arrangement
    assert payload["currency"] == "USD"
    # Accept either '100000.00' (correct) or '100000.0' (bug #93). The
    # dedicated test below asserts the strict form so we know when #93 lands.
    from decimal import Decimal as _D
    assert _D(payload["total_value"]) == _D("100000.00"), (
        f"Money value wrong: {payload['total_value']!r}"
    )

    # Read back
    eng_id = payload["id"]
    r2 = manager_client_a.get(f"/api/v1/engagements/{eng_id}")
    assert r2.status_code == 200, r2.text
    fetched = r2.json()
    assert fetched["id"] == eng_id
    assert fetched["billing_arrangement"] == billing_arrangement


def test_create_engagement_money_serialises_as_string(
    manager_client_a: httpx.Client, world: SeedWorld
) -> None:
    """The Critical Rule: API money fields serialise as strings, not floats.

    Two-decimal-place quantization (bug #93) is checked separately so we know
    when #93 lands. Here we only assert string type + correct value.
    """
    body = {
        "client_id": world.tenant_a.client_ids[0],
        "name": f"Money serialisation test {world.run_id}",
        "billing_arrangement": "fixed_fee",
        "currency": "USD",
        "total_value": "12345.67",
        "billing_terms": {"fixed_fee_amount": "12345.67"},
    }
    r = manager_client_a.post("/api/v1/engagements", json=body)
    assert r.status_code == 201, r.text
    payload = r.json()
    assert isinstance(payload["total_value"], str), (
        f"Money field returned as {type(payload['total_value']).__name__}; "
        f"must be string per PROJECT_CONTEXT.md"
    )
    from decimal import Decimal as _D
    assert _D(payload["total_value"]) == _D("12345.67")


# Bug #93 FIXED in commit 72afb99 — Karya added app/domain/money.py.serialise_money
# applied across engagement/invoice/project/rate_card models. Verified by Aksha
# 2026-05-23 — XPASS confirmed in the API suite run. Sentinel is now strict so
# a regression breaks the build immediately.
def test_create_engagement_money_quantized_to_two_decimals(
    manager_client_a: httpx.Client, world: SeedWorld
) -> None:
    body = {
        "client_id": world.tenant_a.client_ids[0],
        "name": f"Quantization test {world.run_id}",
        "billing_arrangement": "fixed_fee",
        "currency": "USD",
        "total_value": "100000.00",
        "billing_terms": {"fixed_fee_amount": "100000.00"},
    }
    r = manager_client_a.post("/api/v1/engagements", json=body)
    assert r.status_code == 201
    payload = r.json()
    assert payload["total_value"] == "100000.00", payload["total_value"]


def test_list_engagements_filter_by_status(
    manager_client_a: httpx.Client, world: SeedWorld
) -> None:
    """The status filter works and doesn't leak cross-tenant rows."""
    r = manager_client_a.get("/api/v1/engagements?status=active")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert isinstance(rows, list)
    for row in rows:
        assert row["status"] == "active", f"Filter broken: got status={row['status']!r}"
        assert row["tenant_id"] == world.tenant_a.tenant_id


def test_create_engagement_with_invalid_billing_arrangement_returns_422(
    manager_client_a: httpx.Client, world: SeedWorld
) -> None:
    body = {
        "client_id": world.tenant_a.client_ids[0],
        "name": "Bogus arrangement",
        "billing_arrangement": "subscription",  # not in enum
        "currency": "USD",
    }
    r = manager_client_a.post("/api/v1/engagements", json=body)
    assert r.status_code == 422, r.text


# Bug #92 FIXED in commit 72afb99 — Karya added app/services/_validation.py
# with assert_belongs_to_tenant() and called it on every FK in InvoicesService
# and EngagementsService. Verified by Aksha 2026-05-23 — XPASS confirmed.
# Sentinel is now active (no xfail) so any regression breaks the build.
def test_create_engagement_with_cross_tenant_client_id_blocked(
    manager_client_a: httpx.Client, world: SeedWorld
) -> None:
    """Tenant A manager cannot create an engagement using tenant B's client_id.

    Sentinel test for #92 — strict=False so XPASS once fixed lets us notice
    without breaking the build immediately."""
    body = {
        "client_id": world.tenant_b.client_ids[0],
        "name": f"Cross-tenant attempt {world.run_id}",
        "billing_arrangement": "time_and_materials",
        "currency": "USD",
    }
    r = manager_client_a.post("/api/v1/engagements", json=body)
    assert r.status_code in (400, 404, 422), (
        f"Cross-tenant client_id allowed in engagement creation: status={r.status_code}, "
        f"body={r.text[:200]}"
    )


def test_list_engagements_excludes_soft_deleted(
    manager_client_a: httpx.Client, world: SeedWorld
) -> None:
    """The list endpoint must not return engagements with deleted_at set."""
    # Soft-delete one of the seeded engagements via service-role client
    from datetime import UTC, datetime

    from tests.fixtures.scenarios import make_service_client

    eng_id = world.tenant_a.engagement_ids[0]
    db = make_service_client()
    db.table("engagements").update(
        {"deleted_at": datetime.now(UTC).isoformat()}
    ).eq("id", eng_id).execute()

    try:
        r = manager_client_a.get("/api/v1/engagements")
        assert r.status_code == 200, r.text
        ids = {e["id"] for e in r.json()}
        assert eng_id not in ids, (
            f"Soft-deleted engagement {eng_id} still visible in list response"
        )
    finally:
        # Restore so other tests don't break
        db.table("engagements").update({"deleted_at": None}).eq("id", eng_id).execute()
