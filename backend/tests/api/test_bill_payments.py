"""C20 — Bill payments + NACHA/CSV export.

Smoke level: list batches, propose batch (may return empty), require auth.
Real NACHA export tested in C21 bill_pay_agent.
"""

from __future__ import annotations

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_payments,
    pytest.mark.requires_supabase,
]


def test_list_bill_payment_batches_returns_200(client_a: httpx.Client) -> None:
    r = client_a.get("/api/v1/bill-payments/batches")
    assert r.status_code == 200, r.text


def test_list_batches_requires_auth(client: httpx.Client) -> None:
    r = client.get("/api/v1/bill-payments/batches")
    assert r.status_code == 401, r.text


def test_propose_batch_with_empty_bills_handled_gracefully(client_a: httpx.Client) -> None:
    """Proposing with no approved bills must not 500."""
    r = client_a.post("/api/v1/bill-payments/propose", json={})
    # 200 (returned empty proposal), 422 (validation), or 200 with empty list
    # 500 is the failure mode we're guarding against
    assert r.status_code != 500, f"Empty propose 500: {r.text[:200]}"
    assert r.status_code in (200, 201, 400, 422), r.text


def test_get_unknown_batch_returns_404(client_a: httpx.Client) -> None:
    r = client_a.get("/api/v1/bill-payments/batches/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404, r.text


def test_export_unknown_batch_returns_404(client_a: httpx.Client) -> None:
    r = client_a.get("/api/v1/bill-payments/batches/00000000-0000-0000-0000-000000000000/export")
    assert r.status_code == 404, r.text


def test_bill_payment_batches_tenant_scoped(
    client_a: httpx.Client, world: SeedWorld
) -> None:
    r = client_a.get("/api/v1/bill-payments/batches")
    assert r.status_code == 200, r.text
    body = r.json()
    rows = body.get("items", body) if isinstance(body, dict) else body
    if isinstance(rows, list):
        for row in rows:
            assert row.get("tenant_id") == world.tenant_a.tenant_id, (
                f"Cross-tenant batch leak: {row}"
            )
