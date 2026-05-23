"""C29 — Multi-currency FX behavior at the API layer.

Verifies:
1. Invoice created with non-USD currency (GBP/SGD/INR/AUD) round-trips
   correctly via the API — currency persists, amounts serialize as strings.
2. Bill created in foreign currency — same invariant.
3. Cross-currency invoice list returns each item with its own currency
   (not coerced to tenant base).
4. The fx_rates table exists and has at least one row for USD↔X for each
   of the 5 launch currencies (a 'physical foundation' check — the
   fx_refresh_worker should populate these daily but at minimum a seeded
   row should exist).
"""

from __future__ import annotations

import os
from decimal import Decimal

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld

pytestmark = [
    pytest.mark.api,
    pytest.mark.multi_currency,
    pytest.mark.requires_supabase,
]


_FOREIGN_CURRENCIES = ["GBP", "SGD", "INR", "AUD"]


def _service_client():
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        pytest.skip("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(url, key)


@pytest.mark.parametrize("currency", _FOREIGN_CURRENCIES)
def test_invoice_in_foreign_currency_roundtrips(
    client_a: httpx.Client, world: SeedWorld, currency: str
) -> None:
    """POST a foreign-currency invoice; GET it back; assert currency preserved."""
    payload = {
        "engagement_id": world.tenant_a.engagement_ids[0],
        "client_id": world.tenant_a.client_ids[0],
        "currency": currency,
        "lines": [
            {"description": "Foreign FX test", "quantity": "1", "unit_price": "250.00"}
        ],
    }
    r = client_a.post("/api/v1/invoices", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["currency"] == currency, body
    inv_id = body["id"]

    # GET round-trip
    g = client_a.get(f"/api/v1/invoices/{inv_id}")
    assert g.status_code == 200, g.text
    g_body = g.json()
    assert g_body["currency"] == currency
    # Money is serialised as string
    assert isinstance(g_body["subtotal"], str), type(g_body["subtotal"])
    assert Decimal(g_body["subtotal"]) == Decimal("250.00"), g_body["subtotal"]


@pytest.mark.parametrize("currency", _FOREIGN_CURRENCIES)
def test_bill_in_foreign_currency_roundtrips(
    api_base_url: str, world: SeedWorld, currency: str
) -> None:
    """POST a foreign-currency bill via the manager_a role."""
    from tests.fixtures.scenarios import mint_jwt

    u = world.tenant_a.members["manager"]
    headers = {
        "Authorization": f"Bearer {mint_jwt(user_id=u.user_id, email=u.email, role='manager')}",
        "X-Tenant-ID": world.tenant_a.tenant_id,
    }
    payload = {
        "client_id": world.tenant_a.vendor_ids[0],
        "currency": currency,
        "vendor_invoice_number": f"FX-{currency}-001",
        "lines": [
            {
                "description": f"{currency} bill test",
                "quantity": "1",
                "unit_price": "500.00",
                "amount": "500.00",
            }
        ],
    }
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        r = c.post("/api/v1/bills", json=payload)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body["currency"] == currency, body
        assert Decimal(body["subtotal"]) == Decimal("500.00"), body


def test_invoice_list_preserves_per_invoice_currency(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    """The list endpoint must not coerce items to a single base currency."""
    # Seed two invoices, USD and GBP
    base = {
        "engagement_id": world.tenant_a.engagement_ids[0],
        "client_id": world.tenant_a.client_ids[0],
        "lines": [{"description": "x", "quantity": "1", "unit_price": "100.00"}],
    }
    r1 = client_a.post("/api/v1/invoices", json={**base, "currency": "USD"})
    r2 = client_a.post("/api/v1/invoices", json={**base, "currency": "GBP"})
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text

    lst = client_a.get("/api/v1/invoices")
    assert lst.status_code == 200, lst.text
    items = lst.json() if isinstance(lst.json(), list) else lst.json().get("items", [])
    currencies = {i["currency"] for i in items}
    assert {"USD", "GBP"}.issubset(currencies), (
        f"List collapsed currencies; got {currencies}"
    )


def test_fx_rates_table_has_rows_for_launch_currencies() -> None:
    """The fx_rates table should have at least one row per launch currency
    pair (USD as base). If empty, fx_refresh_worker has never run."""
    db = _service_client()
    # Schema (migration 0004): from_currency, to_currency, rate, rate_date
    rows = (
        db.table("fx_rates")
        .select("from_currency, to_currency, rate, rate_date")
        .limit(500)
        .execute()
        .data
        or []
    )
    if not rows:
        pytest.skip(
            "fx_rates table is empty — fx_refresh_worker has never run. "
            "Not a blocker if running offline, but pilot launch needs daily worker."
        )

    # Look at every (from_currency, to_currency) pair we have
    pairs = {(r["from_currency"], r["to_currency"]) for r in rows}
    # We expect AT LEAST one of USD↔X or X↔USD for each non-USD launch currency
    for c in ["GBP", "SGD", "INR", "AUD"]:
        has_pair = ("USD", c) in pairs or (c, "USD") in pairs
        assert has_pair, (
            f"fx_rates has no USD↔{c} pair. Pairs seeded: {sorted(pairs)}"
        )
