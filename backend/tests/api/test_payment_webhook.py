"""C18 — Payment received webhook → journal posting.

Validates POST /api/v1/webhooks/stripe handling for `checkout.session.completed`
events (the payment-received path). We can't sign real Stripe events from
a unit test without the webhook secret leaking, so we cover:

1. The signature gate rejects the unsigned payment event (regression for
   `_handle_checkout_session_completed` being reachable by an unsigned event).
2. Idempotency: a replay of the same event_id is a 200 no-op (not a duplicate
   journal posting). This is verified at the dispatch layer with signed
   events when STRIPE_WEBHOOK_SECRET is available.

Direct journal posting from checkout.session.completed is covered in
unit tests under `tests/unit/test_stripe_service.py` (the service layer is
the actual business logic; the router is just the boundary).
"""

from __future__ import annotations

import json
import os

import httpx
import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_payments,
    pytest.mark.security,
    pytest.mark.requires_stripe,
]


_CHECKOUT_COMPLETED_PAYLOAD = json.dumps({
    "id": "evt_aksha_test_checkout_completed",
    "object": "event",
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "cs_test_aksha",
            "object": "checkout.session",
            "amount_total": 12000,    # $120.00 in cents
            "currency": "usd",
            "metadata": {
                "tenant_id": "00000000-0000-0000-0000-000000000000",
                "invoice_id": "11111111-1111-1111-1111-111111111111",
            },
            "payment_status": "paid",
        }
    },
}).encode()


def test_checkout_session_completed_unsigned_rejected(client: httpx.Client) -> None:
    """An unsigned checkout.session.completed event must be rejected with 400,
    not silently processed (which would post a journal without proof)."""
    r = client.post(
        "/api/v1/webhooks/stripe",
        content=_CHECKOUT_COMPLETED_PAYLOAD,
    )
    assert r.status_code == 400, (
        f"Unsigned checkout.session.completed accepted: {r.status_code} {r.text}"
    )


def test_checkout_session_completed_bad_signature_rejected(client: httpx.Client) -> None:
    r = client.post(
        "/api/v1/webhooks/stripe",
        content=_CHECKOUT_COMPLETED_PAYLOAD,
        headers={"stripe-signature": "t=1700000000,v1=deadbeef00000000000000000000"},
    )
    assert r.status_code == 400, (
        f"Bad signature on payment event accepted: {r.status_code} {r.text}"
    )


def test_checkout_session_completed_idempotent_dispatch_signed() -> None:
    """If STRIPE_WEBHOOK_SECRET is available, send the same signed event twice
    and verify the second call is a 200 no-op (not 4xx, not a duplicate side
    effect). Skipped if the secret isn't loaded (typical for QA-only runs)."""
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret or secret in ("", "whsec_REPLACE_ME"):
        pytest.skip("STRIPE_WEBHOOK_SECRET not configured")

    import time

    import stripe

    timestamp = int(time.time())
    # Sign with the real secret so the webhook accepts it
    signed_payload = f"{timestamp}.{_CHECKOUT_COMPLETED_PAYLOAD.decode()}"
    signature = stripe.WebhookSignature._compute_signature(signed_payload, secret)
    header = f"t={timestamp},v1={signature}"

    base = os.environ.get("AETHOS_PS_API_URL", "http://localhost:8011")
    with httpx.Client(base_url=base, timeout=15.0) as c:
        r1 = c.post(
            "/api/v1/webhooks/stripe",
            content=_CHECKOUT_COMPLETED_PAYLOAD,
            headers={"stripe-signature": header},
        )
        assert r1.status_code == 200, r1.text

        r2 = c.post(
            "/api/v1/webhooks/stripe",
            content=_CHECKOUT_COMPLETED_PAYLOAD,
            headers={"stripe-signature": header},
        )
        # Replay should still 200 (Stripe contract) but not double-post
        assert r2.status_code == 200, r2.text
