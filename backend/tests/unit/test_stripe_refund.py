"""Unit tests for Stripe refund reversal (#371 AC 4)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe

import app.services.stripe_checkout_payments as scp
from app.services.stripe_checkout_payments import record_charge_refund

pytestmark = pytest.mark.asyncio

_MOD = "app.services.stripe_checkout_payments"


def _charge(payload: dict) -> stripe.StripeObject:
    return stripe.StripeObject.construct_from(payload, "sk_test_placeholder")


def _original_payment() -> dict:
    return {
        "id": "pay-1", "tenant_id": "t1", "invoice_id": "inv-1",
        "amount": "125.00", "currency": "USD", "base_amount": "125.00", "fx_rate_id": None,
    }


async def test_full_refund_reverses_settlement() -> None:
    db = MagicMock()
    charge = _charge({"payment_intent": "pi_1", "amount": 12500, "amount_refunded": 12500,
                      "refunded": True})
    with (
        patch(f"{_MOD}._get_payments_by_intent", new=AsyncMock(return_value=[_original_payment()])),
        patch(f"{_MOD}._system_actor", new=AsyncMock(return_value="user-1")),
        patch(f"{_MOD}._get_invoice", new=AsyncMock(return_value={"id": "inv-1", "invoice_number": "INV-1"})),
        patch(f"{_MOD}._post_refund_journal", new=AsyncMock(return_value=True)) as journal,
        patch(f"{_MOD}._insert_refund_payment", new=AsyncMock()) as neg_payment,
        patch(f"{_MOD}._rollback_invoice_to_open", new=AsyncMock()) as rollback,
    ):
        result = await record_charge_refund(db=db, charge=charge, event_id="evt_r1")

    assert result == {"status": "refunded", "invoice_id": "inv-1", "tenant_id": "t1",
                      "amount": "125.00"}
    journal.assert_awaited_once()
    assert journal.await_args.kwargs["amount"] == Decimal("125.00")
    neg_payment.assert_awaited_once()
    rollback.assert_awaited_once_with(db, "t1", "inv-1")


async def test_partial_refund_is_not_auto_reversed() -> None:
    db = MagicMock()
    charge = _charge({"payment_intent": "pi_1", "amount": 12500, "amount_refunded": 5000})
    with patch(f"{_MOD}._post_refund_journal", new=AsyncMock()) as journal:
        result = await record_charge_refund(db=db, charge=charge, event_id="evt_r2")
    assert result["status"] == "partial_refund_manual_review"
    journal.assert_not_awaited()


async def test_refund_for_unknown_intent_skips() -> None:
    db = MagicMock()
    charge = _charge({"payment_intent": "pi_x", "amount": 12500, "amount_refunded": 12500,
                      "refunded": True})
    with patch(f"{_MOD}._get_payments_by_intent", new=AsyncMock(return_value=[])):
        result = await record_charge_refund(db=db, charge=charge, event_id="evt_r3")
    assert result["status"] == "payment_not_found"


async def test_duplicate_refund_is_idempotent() -> None:
    db = MagicMock()
    charge = _charge({"payment_intent": "pi_1", "amount": 12500, "amount_refunded": 12500,
                      "refunded": True})
    payments = [_original_payment(), {"id": "pay-2", "tenant_id": "t1", "invoice_id": "inv-1",
                                      "amount": "-125.00", "currency": "USD", "base_amount": "-125.00"}]
    with (
        patch(f"{_MOD}._get_payments_by_intent", new=AsyncMock(return_value=payments)),
        patch(f"{_MOD}._post_refund_journal", new=AsyncMock()) as journal,
    ):
        result = await record_charge_refund(db=db, charge=charge, event_id="evt_r4")
    assert result["status"] == "duplicate_refund"
    journal.assert_not_awaited()


async def test_no_refund_amount_is_noop() -> None:
    db = MagicMock()
    charge = _charge({"payment_intent": "pi_1", "amount": 12500, "amount_refunded": 0})
    result = await record_charge_refund(db=db, charge=charge, event_id="evt_r5")
    assert result["status"] == "no_refund"


async def test_refund_journal_reverses_ar_and_bank() -> None:
    # The reversal must DR 1200 (AR reinstated) / CR 1100 (cash returned).
    db = MagicMock()
    captured: dict = {}

    def _fake_post_journal(**kwargs):
        captured.update(kwargs)

    with (
        patch(f"{_MOD}._get_account_ids_by_codes",
              new=AsyncMock(return_value={"1100": "bank-acct", "1200": "ar-acct"})),
        patch(f"{_MOD}.post_journal", side_effect=_fake_post_journal),
    ):
        ok = await scp._post_refund_journal(
            db=db, tenant_id="t1", invoice={"invoice_number": "INV-1"}, invoice_id="inv-1",
            amount=Decimal("125.00"), currency="USD", base_amount=Decimal("125.00"),
            fx_rate_id=None, actor_uuid="user-1", payment_intent_id="pi_1",
        )

    assert ok is True
    assert captured["reference_type"] == "refund"
    lines = {ln.direction: ln.account_code for ln in captured["lines"]}
    assert lines == {"DR": "1200", "CR": "1100"}
