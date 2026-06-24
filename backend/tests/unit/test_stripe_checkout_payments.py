"""Shared Stripe checkout payment recording regressions."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe

from app.services.stripe_checkout_payments import record_checkout_session_payment

pytestmark = pytest.mark.unit


def _session(payload: dict) -> stripe.StripeObject:
    return stripe.StripeObject.construct_from(payload, "sk_test_placeholder")


@pytest.mark.asyncio
async def test_records_payment_with_payment_link_fallback_when_session_metadata_missing() -> None:
    db = MagicMock()
    invoice = {
        "id": "inv-001",
        "tenant_id": "tenant-001",
        "invoice_number": "INV-001",
        "currency": "USD",
    }
    session = _session(
        {
            "id": "cs_test_fallback",
            "payment_link": "plink_test_001",
            "payment_intent": "pi_test_fallback",
            "amount_total": 12500,
            "currency": "usd",
        }
    )

    with (
        patch(
            "app.services.stripe_checkout_payments._get_invoice",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.stripe_checkout_payments._get_invoice_by_payment_link",
            new=AsyncMock(return_value=invoice),
        ) as by_link,
        patch(
            "app.services.stripe_checkout_payments._payment_intent_exists",
            new=AsyncMock(return_value=False),
        ),
        patch("app.services.stripe_checkout_payments._insert_payment", new=AsyncMock()) as insert,
        patch("app.services.stripe_checkout_payments._mark_invoice_paid", new=AsyncMock()),
        patch("app.services.stripe_checkout_payments._backlink_time_entries", new=AsyncMock()),
        patch(
            "app.services.stripe_checkout_payments._system_actor",
            new=AsyncMock(return_value="user-001"),
        ),
        patch(
            "app.services.stripe_checkout_payments._post_payment_journal",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.stripe_checkout_payments.post_fx_gain_loss_if_needed",
            new=AsyncMock(),
        ),
    ):
        result = await record_checkout_session_payment(
            db=db,
            session=session,
            event_id="evt_test_fallback",
            source="unit_test",
        )

    assert result["status"] == "recorded"
    assert result["invoice_id"] == "inv-001"
    assert result["tenant_id"] == "tenant-001"
    by_link.assert_awaited_once_with(db, "plink_test_001", None)
    insert.assert_awaited_once()
    assert insert.await_args.kwargs["amount"] == Decimal("125")
    assert insert.await_args.kwargs["payment_intent_id"] == "pi_test_fallback"


@pytest.mark.asyncio
async def test_duplicate_payment_intent_skips_mutation() -> None:
    db = MagicMock()
    session = _session(
        {
            "id": "cs_test_duplicate",
            "metadata": {"invoice_id": "inv-001", "tenant_id": "tenant-001"},
            "payment_intent": "pi_test_duplicate",
            "amount_total": 5000,
            "currency": "usd",
        }
    )

    with (
        patch(
            "app.services.stripe_checkout_payments._get_invoice",
            new=AsyncMock(return_value={"id": "inv-001", "tenant_id": "tenant-001"}),
        ),
        patch(
            "app.services.stripe_checkout_payments._payment_intent_exists",
            new=AsyncMock(return_value=True),
        ),
        patch("app.services.stripe_checkout_payments._insert_payment", new=AsyncMock()) as insert,
    ):
        result = await record_checkout_session_payment(
            db=db,
            session=session,
            event_id="evt_test_duplicate",
        )

    assert result["status"] == "duplicate"
    insert.assert_not_awaited()
