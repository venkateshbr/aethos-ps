"""Stripe webhook signature verification (C4).

The webhook must reject invalid signatures with 400 before doing any state
mutation. We test this with three shapes:
1. Missing stripe-signature header → 400
2. Wrong signature → 400
3. Empty body + missing header → 400
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_payments,
    pytest.mark.security,
    pytest.mark.requires_stripe,
]


def test_stripe_webhook_rejects_missing_signature(client: httpx.Client) -> None:
    r = client.post(
        "/api/v1/webhooks/stripe",
        content=b'{"id":"evt_test","type":"customer.subscription.updated"}',
    )
    assert r.status_code == 400, (
        f"Webhook accepted request without signature: {r.status_code} {r.text}"
    )


def test_stripe_webhook_rejects_invalid_signature(client: httpx.Client) -> None:
    r = client.post(
        "/api/v1/webhooks/stripe",
        content=b'{"id":"evt_test","type":"customer.subscription.updated"}',
        headers={"stripe-signature": "t=1234567890,v1=deadbeefnotvalid"},
    )
    assert r.status_code == 400, (
        f"Webhook accepted invalid signature: {r.status_code} {r.text}"
    )


def test_stripe_webhook_rejects_empty_body(client: httpx.Client) -> None:
    r = client.post(
        "/api/v1/webhooks/stripe",
        content=b"",
        headers={"stripe-signature": "t=1234,v1=abc"},
    )
    assert r.status_code == 400, r.text
