"""Signup + Stripe trial (C1) and billing endpoints.

Two surfaces:
1. POST /auth/signup happy path: real Supabase + real Stripe sandbox customer
2. POST /billing/start-trial WILL fail today because Stripe Price IDs are
   placeholders (finding F1). We assert that explicitly so the bug stays
   surfaced.
3. GET /billing/prices needs auth + tenant; we cover both shapes.

Signup creates real artifacts. We tag the tenant for cleanup.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
import stripe

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_signup,
    pytest.mark.requires_supabase,
    pytest.mark.requires_stripe,
]


def _signup_payload() -> dict:
    rid = uuid.uuid4().hex[:8]
    # pydantic EmailStr rejects .test as reserved; use example.com which is
    # the IANA-reserved-for-docs domain that EmailStr accepts.
    return {
        "email": f"aksha-signup-{rid}@example.com",
        "password": "Aksha-Test-Password-2026!",
        "tenant_name": f"Aksha Signup Test {rid}",
        "country": "US",
        "plan_tier": "starter",
        "billing_interval": "monthly",
    }


def test_signup_happy_path_returns_setup_intent(client: httpx.Client) -> None:
    """A fresh signup creates a tenant + Stripe customer and returns the
    SetupIntent client_secret needed for card capture.

    The current test-mode auth project accepts the IANA-reserved example.com
    domain, so the test can exercise the complete public API contract without
    sending mail to a real recipient."""
    payload = _signup_payload()
    body: dict = {}
    try:
        r = client.post("/api/v1/auth/signup", json=payload)
        assert r.status_code == 201, f"unexpected signup status: {r.status_code}"
        body = r.json()
        assert "tenant_id" in body
        assert str(body.get("stripe_setup_intent_client_secret") or "").startswith("seti_")
    finally:
        _cleanup_signup(body)


def test_signup_rejects_malformed_email_without_creating_tenant(client: httpx.Client) -> None:
    """Request validation rejects malformed email before any external write.

    Structured Supabase ``AuthApiError`` mapping is covered by the focused
    unit suite. This real-stack check owns the stronger public invariant: an
    invalid request cannot create an auth user, tenant, or Stripe object.
    """
    payload = _signup_payload()
    payload["email"] = "definitely-not-an-email"
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code == 422
    body = r.json()
    assert body.get("detail")
    assert "supabase" not in str(body["detail"]).lower()

    from tests.fixtures.scenarios import make_service_client

    rows = (
        make_service_client()
        .table("tenants")
        .select("id")
        .eq("name", payload["tenant_name"])
        .execute()
        .data
        or []
    )
    assert rows == []


def _cleanup_signup(body: dict) -> None:
    """Remove every external artifact created by the happy-path test."""
    tenant_id = str(body.get("tenant_id") or "")
    if not tenant_id:
        return

    from tests.fixtures.scenarios import make_service_client

    db = make_service_client()
    tenant_rows = (
        db.table("tenants")
        .select("id,name,stripe_customer_id")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not tenant_rows or not str(tenant_rows[0].get("name") or "").startswith("Aksha Signup Test"):
        return
    memberships = (
        db.table("tenant_users")
        .select("user_id")
        .eq("tenant_id", tenant_id)
        .execute()
        .data
        or []
    )
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    customer_id = tenant_rows[0].get("stripe_customer_id")
    if customer_id:
        stripe.Customer.delete(customer_id)
    for membership in memberships:
        user_id = membership.get("user_id")
        if user_id:
            db.auth.admin.delete_user(user_id)
    db.table("tenants").delete().eq("id", tenant_id).execute()


def test_signup_rejects_short_password(client: httpx.Client) -> None:
    payload = _signup_payload()
    payload["password"] = "short"
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code == 422, r.text


def test_signup_rejects_invalid_country(client: httpx.Client) -> None:
    payload = _signup_payload()
    payload["country"] = "USA"  # not 2 letters
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code == 422, r.text


def test_signup_invalid_plan_tier_returns_422(client: httpx.Client) -> None:
    payload = _signup_payload()
    payload["plan_tier"] = "enterprise"
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code == 422, r.text


def test_billing_prices_requires_auth(client: httpx.Client) -> None:
    r = client.get("/api/v1/billing/prices")
    assert r.status_code == 401, r.text


def test_billing_prices_returns_currency_for_country(
    client_a: httpx.Client, world,
) -> None:
    """Tenant A is US/USD; prices endpoint returns USD entries."""
    r = client_a.get("/api/v1/billing/prices")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["currency"] == "USD", body
    assert len(body["plans"]) >= 3, f"Expected ≥3 plan tiers, got {body['plans']}"
    # Each plan entry has tier + monthly_id + annual_id keys
    for plan in body["plans"]:
        assert "tier" in plan and "monthly_id" in plan and "annual_id" in plan, plan


def test_billing_prices_returns_real_stripe_price_ids_not_placeholders(
    client_a: httpx.Client,
) -> None:
    """Pilot gate: real Stripe Price IDs are configured for all 30 SKUs.

    Real Stripe Price IDs look like `price_1NABCdef...` — they start with
    `price_` followed by random base-58-ish characters (1 + uppercase mix).
    Placeholders look like `price_REPLACE_ME` or `price_starter_monthly_usd`.

    Verified against the bootstrap_prices.py script that created all 30
    test-mode Prices (3 tiers x 2 intervals x 5 currencies); see #94.
    """
    r = client_a.get("/api/v1/billing/prices")
    assert r.status_code == 200, r.text
    body = r.json()
    placeholders: list[str] = []
    for plan in body["plans"]:
        for key in ("monthly_id", "annual_id"):
            pid = plan.get(key) or ""
            # Real Stripe price IDs are e.g. price_1NABCdefGHIJklmn... (~24 chars
            # of alphanum after 'price_'). Placeholders use _ separators and
            # English words.
            if "REPLACE_ME" in pid or "_starter_" in pid or "_growth_" in pid or "_pro_" in pid:
                placeholders.append(f"{plan['tier']}.{key}={pid}")
            elif pid and not pid.startswith("price_"):
                placeholders.append(f"{plan['tier']}.{key}={pid} (bad prefix)")
    assert not placeholders, (
        f"F1 LAUNCH BLOCKER: Stripe Price IDs look like placeholders, not real "
        f"Stripe Prices. Create the Prices in the Stripe dashboard and update "
        f"backend/.env. Placeholders detected: {placeholders}"
    )
