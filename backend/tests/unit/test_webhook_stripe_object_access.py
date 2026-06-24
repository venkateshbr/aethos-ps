"""Stripe webhook object access regressions."""

from __future__ import annotations

import pytest
import stripe

from app.api.v1.endpoints.webhooks import _extract_tenant_id, _stripe_value

pytestmark = pytest.mark.unit


def test_stripe_value_reads_nested_metadata_stripe_object() -> None:
    session = stripe.StripeObject.construct_from(
        {
            "id": "cs_test_object_access",
            "amount_total": 12500,
            "currency": "usd",
            "metadata": {
                "tenant_id": "tenant-1",
                "invoice_id": "invoice-1",
            },
            "payment_intent": "pi_test_object_access",
        },
        "sk_test_placeholder",
    )

    metadata = _stripe_value(session, "metadata")

    assert _stripe_value(metadata, "tenant_id") == "tenant-1"
    assert _stripe_value(metadata, "invoice_id") == "invoice-1"
    assert _stripe_value(session, "amount_total") == 12500
    assert _stripe_value(session, "currency") == "usd"
    assert _stripe_value(session, "payment_intent") == "pi_test_object_access"


def test_stripe_value_supports_plain_dicts() -> None:
    assert _stripe_value({"invoice_id": "invoice-1"}, "invoice_id") == "invoice-1"
    assert _stripe_value({"invoice_id": "invoice-1"}, "tenant_id", "missing") == "missing"


def test_extract_tenant_id_reads_checkout_metadata() -> None:
    event = stripe.Event.construct_from(
        {
            "id": "evt_test_metadata_tenant",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_metadata_tenant",
                    "metadata": {"tenant_id": "tenant-from-metadata"},
                },
            },
        },
        "sk_test_placeholder",
    )

    assert _extract_tenant_id(event) == "tenant-from-metadata"
