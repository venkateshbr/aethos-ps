"""Shared Stripe checkout payment recording.

Both the signed webhook and the delayed-payment reconciliation worker use this
module so a paid Checkout Session has one accounting outcome: payment row,
paid invoice, time-entry backlink, AR-clearing journal, and optional FX journal.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from decimal import Decimal
from typing import Any

from app.domain.journal_helper import JournalLineSpec, post_journal
from app.services.fx_gain_loss_service import post_fx_gain_loss_if_needed
from app.services.payment_fx_service import payment_fx_amounts
from supabase import Client

logger = logging.getLogger(__name__)


def stripe_value(obj: object, key: str, default: object | None = None) -> object | None:
    """Read a field from dicts and StripeObject instances."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    getter = getattr(obj, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            try:
                return getter(key)
            except Exception:
                pass
    try:
        return obj[key]  # type: ignore[index]
    except Exception:
        return getattr(obj, key, default)


async def record_checkout_session_payment(
    *,
    db: Client,
    session: object,
    event_id: str | None = None,
    fallback_invoice_id: str | None = None,
    fallback_tenant_id: str | None = None,
    source: str = "stripe_webhook",
) -> dict[str, Any]:
    """Record a paid Checkout Session idempotently.

    Metadata is the primary match path. If a real Stripe Payment Link session
    omits copied metadata, fall back to the Payment Link id stored on invoices
    or to the caller-provided invoice/tenant from reconciliation.
    """
    meta = stripe_value(session, "metadata", {}) or {}
    invoice_id = _as_str(stripe_value(meta, "invoice_id")) or fallback_invoice_id
    tenant_id = _as_str(stripe_value(meta, "tenant_id")) or fallback_tenant_id
    payment_link_id = _as_str(stripe_value(session, "payment_link"))
    payment_intent_id = _as_str(stripe_value(session, "payment_intent"))

    invoice: dict | None = None
    if invoice_id and tenant_id:
        invoice = await _get_invoice(db, invoice_id, tenant_id)

    if invoice is None and payment_link_id:
        invoice = await _get_invoice_by_payment_link(db, payment_link_id, tenant_id)
        if invoice:
            invoice_id = str(invoice["id"])
            tenant_id = str(invoice["tenant_id"])

    if invoice_id is None or tenant_id is None:
        logger.warning(
            "checkout.session.completed missing invoice match fields",
            extra={"event_id": event_id, "source": source, "payment_link_id": payment_link_id},
        )
        return {"status": "missing_metadata", "invoice_id": None, "tenant_id": None}

    if payment_intent_id and await _payment_intent_exists(db, payment_intent_id):
        logger.info(
            "Duplicate checkout.session.completed payment — skipping",
            extra={
                "payment_intent_id": payment_intent_id,
                "event_id": event_id,
                "source": source,
            },
        )
        return {
            "status": "duplicate",
            "invoice_id": invoice_id,
            "tenant_id": tenant_id,
            "payment_intent_id": payment_intent_id,
        }

    if invoice is None:
        invoice = await _get_invoice(db, invoice_id, tenant_id)
    if invoice is None:
        logger.error(
            "Invoice not found for checkout.session.completed",
            extra={
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "event_id": event_id,
                "source": source,
            },
        )
        return {"status": "invoice_not_found", "invoice_id": invoice_id, "tenant_id": tenant_id}

    # A draft/void/cancelled invoice must never be settled — e.g. a paid stale
    # payment link for an invoice voided after it was sent. (#371 AC 6)
    invoice_status = str(invoice.get("status") or "").lower()
    if invoice_status in {"draft", "void", "voided", "cancelled", "canceled"}:
        logger.warning(
            "checkout.session.completed for a non-settleable invoice — refusing to settle",
            extra={
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "event_id": event_id,
                "invoice_status": invoice_status,
            },
        )
        return {
            "status": "invoice_not_settleable",
            "invoice_id": invoice_id,
            "tenant_id": tenant_id,
            "invoice_status": invoice_status,
        }

    amount_total_cents = int(stripe_value(session, "amount_total", 0) or 0)
    amount_received = Decimal(str(amount_total_cents)) / Decimal("100")
    if amount_received <= 0:
        logger.warning(
            "checkout.session.completed has non-positive amount — skipping payment insert",
            extra={"invoice_id": invoice_id, "tenant_id": tenant_id, "event_id": event_id},
        )
        return {"status": "invalid_amount", "invoice_id": invoice_id, "tenant_id": tenant_id}

    currency = str(stripe_value(session, "currency", invoice.get("currency", "usd")) or "usd").upper()
    paid_at_iso = _paid_at_iso(session)
    fx_amounts = await payment_fx_amounts(
        db=db,
        tenant_id=tenant_id,
        amount=amount_received,
        currency=currency,
        paid_at=paid_at_iso,
    )

    await _insert_payment(
        db=db,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        amount=amount_received,
        currency=currency,
        base_amount=fx_amounts.base_amount,
        fx_rate_id=fx_amounts.fx_rate_id,
        paid_at_iso=paid_at_iso,
        payment_intent_id=payment_intent_id,
        source=source,
    )
    await _mark_invoice_paid(db, tenant_id, invoice_id, paid_at_iso)
    await _backlink_time_entries(db, tenant_id, invoice_id)

    actor_uuid = await _system_actor(db, tenant_id)
    journal_posted = False
    if actor_uuid is None:
        logger.error(
            "No tenant_users actor found — cannot post payment journal; payment row exists",
            extra={"invoice_id": invoice_id, "tenant_id": tenant_id},
        )
    else:
        journal_posted = await _post_payment_journal(
            db=db,
            tenant_id=tenant_id,
            invoice=invoice,
            invoice_id=invoice_id,
            amount_received=amount_received,
            currency=currency,
            base_amount=fx_amounts.base_amount,
            fx_rate_id=fx_amounts.fx_rate_id,
            actor_uuid=actor_uuid,
            payment_intent_id=payment_intent_id,
        )

    try:
        await post_fx_gain_loss_if_needed(
            db=db,
            tenant_id=tenant_id,
            invoice=invoice,
            payment_amount=amount_received,
            payment_currency=currency,
            payment_base_amount=fx_amounts.base_amount,
            base_currency=fx_amounts.base_currency,
            payment_date=fx_amounts.rate_date,
        )
    except Exception:
        logger.error(
            "Failed to post FX gain/loss journal — payment journal already attempted",
            exc_info=True,
            extra={"invoice_id": invoice_id, "tenant_id": tenant_id},
        )

    logger.info(
        "Payment recorded from checkout.session.completed",
        extra={
            "invoice_id": invoice_id,
            "tenant_id": tenant_id,
            "amount": str(amount_received),
            "currency": currency,
            "event_id": event_id,
            "source": source,
        },
    )
    return {
        "status": "recorded",
        "invoice_id": invoice_id,
        "tenant_id": tenant_id,
        "payment_intent_id": payment_intent_id,
        "amount": str(amount_received),
        "currency": currency,
        "journal_posted": journal_posted,
    }


def _as_str(value: object | None) -> str | None:
    return str(value) if value else None


def _paid_at_iso(session: object) -> str:
    created = stripe_value(session, "created")
    if isinstance(created, int | float):
        return datetime.datetime.fromtimestamp(created, tz=datetime.UTC).isoformat()
    return datetime.datetime.now(datetime.UTC).isoformat()


async def _payment_intent_exists(db: Client, payment_intent_id: str) -> bool:
    def _check_existing() -> bool:
        result = (
            db.table("payments")
            .select("id")
            .eq("stripe_payment_intent_id", payment_intent_id)
            .execute()
        )
        return bool(result.data)

    return await asyncio.to_thread(_check_existing)


async def _get_invoice(db: Client, invoice_id: str, tenant_id: str) -> dict | None:
    def _get() -> dict | None:
        result = (
            db.table("invoices")
            .select("*")
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None

    return await asyncio.to_thread(_get)


async def _get_invoice_by_payment_link(
    db: Client,
    payment_link_id: str,
    tenant_id: str | None,
) -> dict | None:
    def _get() -> dict | None:
        query = (
            db.table("invoices")
            .select("*")
            .eq("stripe_payment_link_id", payment_link_id)
            .is_("deleted_at", "null")
            .limit(1)
        )
        if tenant_id:
            query = query.eq("tenant_id", tenant_id)
        result = query.execute()
        return result.data[0] if result.data else None

    return await asyncio.to_thread(_get)


async def _insert_payment(
    *,
    db: Client,
    tenant_id: str,
    invoice_id: str,
    amount: Decimal,
    currency: str,
    base_amount: Decimal,
    fx_rate_id: str | None,
    paid_at_iso: str,
    payment_intent_id: str | None,
    source: str,
) -> None:
    payment_data: dict = {
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "amount": str(amount),
        "currency": currency,
        "base_amount": str(base_amount),
        "fx_rate_id": fx_rate_id,
        "paid_at": paid_at_iso,
        "notes": f"Recorded from {source}",
    }
    if payment_intent_id:
        payment_data["stripe_payment_intent_id"] = payment_intent_id

    await asyncio.to_thread(lambda: db.table("payments").insert(payment_data).execute())


async def _mark_invoice_paid(
    db: Client,
    tenant_id: str,
    invoice_id: str,
    paid_at_iso: str,
) -> None:
    await asyncio.to_thread(
        lambda: db.table("invoices")
        .update({"status": "paid", "paid_at": paid_at_iso})
        .eq("id", invoice_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )


async def _backlink_time_entries(db: Client, tenant_id: str, invoice_id: str) -> None:
    line_rows = await asyncio.to_thread(
        lambda: db.table("invoice_lines")
        .select("time_entry_id")
        .eq("invoice_id", invoice_id)
        .execute()
        .data
        or []
    )
    te_ids = [r["time_entry_id"] for r in line_rows if r.get("time_entry_id")]
    if te_ids:
        await asyncio.to_thread(
            lambda: db.table("time_entries")
            .update({"invoice_id": invoice_id, "billing_status": "billed"})
            .in_("id", te_ids)
            .eq("tenant_id", tenant_id)
            .execute()
        )


async def _system_actor(db: Client, tenant_id: str) -> str | None:
    def _get() -> str | None:
        result = (
            db.table("tenant_users")
            .select("user_id")
            .eq("tenant_id", tenant_id)
            .order("created_at")
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["user_id"]
        return None

    return await asyncio.to_thread(_get)


async def _post_payment_journal(
    *,
    db: Client,
    tenant_id: str,
    invoice: dict,
    invoice_id: str,
    amount_received: Decimal,
    currency: str,
    base_amount: Decimal,
    fx_rate_id: str | None,
    actor_uuid: str,
    payment_intent_id: str | None,
) -> bool:
    acct_map = await _get_account_ids_by_codes(db, tenant_id, ["1100", "1200"])
    invoice_number = invoice.get("invoice_number", invoice_id[:8])
    journal_lines = [
        JournalLineSpec(
            direction="DR",
            account_code="1100",
            amount=amount_received,
            description=f"Payment received for invoice {invoice_number}",
            account_id=acct_map.get("1100"),
            currency=currency,
            base_amount=base_amount,
            fx_rate_id=fx_rate_id,
        ),
        JournalLineSpec(
            direction="CR",
            account_code="1200",
            amount=amount_received,
            description=f"Payment received for invoice {invoice_number}",
            account_id=acct_map.get("1200"),
            currency=currency,
            base_amount=base_amount,
            fx_rate_id=fx_rate_id,
        ),
    ]
    try:
        post_journal(
            db=db,
            tenant_id=tenant_id,
            created_by=actor_uuid,
            description=f"Payment received for invoice {invoice_number}",
            entry_date=datetime.date.today().isoformat(),
            reference_type="payment",
            reference_id=invoice_id,
            lines=journal_lines,
        )
    except Exception:
        logger.error(
            "Failed to post payment journal — payment recorded, journal skipped",
            exc_info=True,
            extra={
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "payment_intent_id": payment_intent_id,
            },
        )
        return False
    return True


async def _get_account_ids_by_codes(
    db: Client,
    tenant_id: str,
    codes: list[str],
) -> dict[str, str]:
    def _get_accounts() -> dict[str, str]:
        result = (
            db.table("accounts")
            .select("id, code")
            .eq("tenant_id", tenant_id)
            .in_("code", codes)
            .execute()
        )
        return {r["code"]: r["id"] for r in (result.data or [])}

    return await asyncio.to_thread(_get_accounts)
