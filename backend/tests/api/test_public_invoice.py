"""C17 — Public invoice token endpoint.

The /public/invoices/{token} route is the buyer-facing view of an invoice —
no auth required. Tokens are issued on send; we test bad/missing tokens here,
and the public view of a real invoice token in the Playwright suite.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_billing,
    pytest.mark.requires_supabase,
]


def test_public_invoice_unknown_token_returns_404(client: httpx.Client) -> None:
    r = client.get("/api/v1/public/invoices/totally-not-a-real-token")
    assert r.status_code == 404, r.text


def test_public_invoice_endpoint_no_auth_required(client: httpx.Client) -> None:
    """The whole point of this endpoint is buyer access without an account."""
    r = client.get("/api/v1/public/invoices/anything")
    assert r.status_code != 401, (
        f"Public invoice endpoint demands auth ({r.status_code}) — defeats its purpose"
    )


def test_public_invoice_endpoint_no_tenant_header_required(client: httpx.Client) -> None:
    """Buyers don't know the seller's tenant_id — the endpoint must not 403 on missing header."""
    r = client.get("/api/v1/public/invoices/anything")
    assert r.status_code != 403, (
        f"Public invoice endpoint demands X-Tenant-ID ({r.status_code}) — buyers cannot supply it"
    )


def test_public_invoice_short_token_handled(client: httpx.Client) -> None:
    """An obviously-too-short token must not 500."""
    r = client.get("/api/v1/public/invoices/x")
    assert r.status_code != 500, f"Short token 500: {r.text[:200]}"
    assert r.status_code in (400, 404, 422), r.text
