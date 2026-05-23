"""C3 — Stripe Connect endpoints (gated by F2/#95).

The OAuth URL endpoint will fail validation when ``STRIPE_CONNECT_CLIENT_ID``
is the placeholder ``ca_REPLACE_ME``. We assert the endpoints are present and
behave correctly given the env state. Once #95 is resolved this suite needs
to be expanded to drive the OAuth callback.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.requires_supabase,
    pytest.mark.requires_stripe,
]


def test_connect_status_endpoint_returns_200(client_a: httpx.Client) -> None:
    """Connect status endpoint must respond 200 — no Connect account is OK."""
    r = client_a.get("/api/v1/stripe/connect/status")
    assert r.status_code == 200, r.text


def test_connect_status_requires_auth(client: httpx.Client) -> None:
    r = client.get("/api/v1/stripe/connect/status")
    assert r.status_code == 401, r.text


@pytest.mark.xfail(
    reason="Bug #95 — STRIPE_CONNECT_CLIENT_ID=ca_REPLACE_ME, OAuth URL gen will return Stripe error",
    strict=False,
)
def test_connect_oauth_url_returns_real_stripe_url(client_a: httpx.Client) -> None:
    """The OAuth URL endpoint must return a real connect.stripe.com link.

    Today it returns either an error or a URL with the placeholder client_id.
    Flips XPASS when #95 lands and the real client_id is in .env.
    """
    r = client_a.get("/api/v1/stripe/connect/oauth-url")
    if r.status_code == 200:
        url = r.json().get("url", "")
        assert "connect.stripe.com" in url, f"Not a real Stripe URL: {url}"
        assert "ca_REPLACE_ME" not in url, f"Placeholder client_id in URL: {url}"
    else:
        # 500 with placeholder is the bug
        assert r.status_code != 500, r.text
