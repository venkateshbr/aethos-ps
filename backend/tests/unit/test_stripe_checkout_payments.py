"""Shared Stripe checkout payment recording regressions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe

from app.domain.fx import FxRateNotFoundError
from app.services.payment_fx_service import PaymentFxAmounts
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
        ) as payment_journal,
        patch(
            "app.services.stripe_checkout_payments.post_fx_gain_loss_if_needed",
            new=AsyncMock(),
        ) as fx_gain_loss,
        patch(
            "app.services.stripe_checkout_payments.payment_fx_amounts",
            new=AsyncMock(
                return_value=PaymentFxAmounts(
                    amount=Decimal("125.00"),
                    currency="USD",
                    base_amount=Decimal("125.00"),
                    base_currency="USD",
                    rate=Decimal("1"),
                    rate_date=date(2026, 6, 25),
                    fx_rate_id=None,
                )
            ),
        ) as payment_fx,
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
    assert insert.await_args.kwargs["base_amount"] == Decimal("125.00")
    assert insert.await_args.kwargs["fx_rate_id"] is None
    assert insert.await_args.kwargs["payment_intent_id"] == "pi_test_fallback"
    payment_fx.assert_awaited_once()
    payment_journal.assert_awaited_once()
    assert payment_journal.await_args.kwargs["base_amount"] == Decimal("125.00")
    assert payment_journal.await_args.kwargs["fx_rate_id"] is None
    fx_gain_loss.assert_awaited_once()
    assert fx_gain_loss.await_args.kwargs["payment_base_amount"] == Decimal("125.00")
    assert fx_gain_loss.await_args.kwargs["base_currency"] == "USD"


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


@pytest.mark.asyncio
async def test_missing_payment_fx_rate_rejects_before_insert() -> None:
    db = MagicMock()
    invoice = {
        "id": "inv-001",
        "tenant_id": "tenant-001",
        "invoice_number": "INV-001",
        "currency": "GBP",
    }
    session = _session(
        {
            "id": "cs_test_missing_fx",
            "metadata": {"invoice_id": "inv-001", "tenant_id": "tenant-001"},
            "payment_intent": "pi_test_missing_fx",
            "amount_total": 10000,
            "currency": "gbp",
        }
    )

    with (
        patch(
            "app.services.stripe_checkout_payments._get_invoice",
            new=AsyncMock(return_value=invoice),
        ),
        patch(
            "app.services.stripe_checkout_payments._payment_intent_exists",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.services.stripe_checkout_payments.payment_fx_amounts",
            new=AsyncMock(
                side_effect=FxRateNotFoundError("GBP", "USD", date(2026, 6, 25))
            ),
        ),
        patch("app.services.stripe_checkout_payments._insert_payment", new=AsyncMock()) as insert,
        pytest.raises(FxRateNotFoundError),
    ):
        await record_checkout_session_payment(
            db=db,
            session=session,
            event_id="evt_test_missing_fx",
        )

    insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_void_invoice_is_not_settled() -> None:
    """#371 AC 6 — a void invoice (e.g. paid via a stale link after voiding) must
    not be settled: no payment, no AR journal, no mark-paid."""
    db = MagicMock()
    void_invoice = {
        "id": "inv-001", "tenant_id": "tenant-001", "currency": "USD", "status": "void",
    }
    session = _session(
        {
            "id": "cs_void",
            "metadata": {"invoice_id": "inv-001", "tenant_id": "tenant-001"},
            "amount_total": 12500,
            "currency": "usd",
            "payment_intent": "pi_void",
        }
    )
    with (
        patch(
            "app.services.stripe_checkout_payments._get_invoice",
            new=AsyncMock(return_value=void_invoice),
        ),
        patch(
            "app.services.stripe_checkout_payments._payment_intent_exists",
            new=AsyncMock(return_value=False),
        ),
        patch("app.services.stripe_checkout_payments._insert_payment", new=AsyncMock()) as insert,
        patch(
            "app.services.stripe_checkout_payments._post_payment_journal",
            new=AsyncMock(return_value=True),
        ) as journal,
        patch(
            "app.services.stripe_checkout_payments._mark_invoice_paid", new=AsyncMock()
        ) as mark_paid,
    ):
        result = await record_checkout_session_payment(
            db=db, session=session, event_id="evt_void", source="unit_test",
        )

    assert result["status"] == "invoice_not_settleable"
    assert result["invoice_status"] == "void"
    insert.assert_not_awaited()
    journal.assert_not_awaited()
    mark_paid.assert_not_awaited()
