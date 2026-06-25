"""FX gain/loss service — post realised gain/loss on multi-currency payments.

When a multi-currency invoice is paid, the payment may arrive at a different
exchange rate than the rate used when the invoice was created. The difference
is a realised FX gain (if we received more than expected) or loss (if less).

Journal pattern:
  Gain: DR 1200 AR  /  CR 7900 Realized FX Gain/Loss
  Loss: DR 7900 Realized FX Gain/Loss / CR 1200 AR

The delta is immaterial if |delta| < $0.01 (after rounding HALF_DOWN).
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from decimal import ROUND_HALF_DOWN, Decimal

from app.domain.journal_helper import JournalLineSpec, post_journal
from app.services.payment_fx_service import payment_fx_amounts, tenant_base_currency
from supabase import Client

logger = logging.getLogger(__name__)

_IMMATERIAL_THRESHOLD = Decimal("0.01")


def compute_fx_delta(payment_base: Decimal, invoice_base: Decimal) -> Decimal:
    """Return the realised FX delta (payment_base - invoice_base).

    Positive = gain, negative = loss. Rounded HALF_DOWN so values like
    Decimal("0.005") become 0.00 (immaterial, no journal needed).
    """
    return (payment_base - invoice_base).quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN)


async def post_fx_gain_loss_if_needed(
    *,
    db: Client,
    tenant_id: str,
    invoice: dict,
    payment_amount: Decimal,
    payment_currency: str,
    payment_base_amount: Decimal | None = None,
    base_currency: str | None = None,
    payment_date: datetime.date | str | None = None,
) -> Decimal | None:
    """Post an FX gain/loss journal entry if the payment differs from invoice base.

    Called after a checkout.session.completed event marks an invoice paid.

    Parameters
    ----------
    db:               Service-role DB client.
    tenant_id:        Tenant scope.
    invoice:          The invoice DB row (must include base_total and currency).
    payment_amount:   Amount received in payment_currency (smallest-unit already converted).
    payment_currency: ISO 4217 code of the payment.

    Returns
    -------
    The delta (Decimal) if a journal was posted, or None if skipped.
    """
    payment_currency = payment_currency.upper()

    invoice_base_str = invoice.get("base_total") or invoice.get("total") or "0"
    invoice_base = Decimal(str(invoice_base_str))
    invoice_currency: str = (invoice.get("currency") or payment_currency).upper()
    if (
        payment_base_amount is None
        and invoice_currency == payment_currency
        and invoice_base == payment_amount
    ):
        return None

    if payment_base_amount is None:
        fx_amounts = await payment_fx_amounts(
            db=db,
            tenant_id=tenant_id,
            amount=payment_amount,
            currency=payment_currency,
            paid_at=payment_date,
        )
        payment_base = fx_amounts.base_amount
        base_currency = fx_amounts.base_currency
    else:
        payment_base = payment_base_amount
        base_currency = (base_currency or await tenant_base_currency(db, tenant_id)).upper()
    delta = compute_fx_delta(payment_base, invoice_base)

    if delta.copy_abs() < _IMMATERIAL_THRESHOLD:
        logger.info(
            "fx_gain_loss: immaterial delta %s — skipping journal",
            delta,
            extra={"invoice_id": invoice.get("id"), "tenant_id": tenant_id},
        )
        return None

    invoice_id: str = str(invoice.get("id", ""))
    invoice_number: str = str(invoice.get("invoice_number", invoice_id[:8]))

    def _get_accounts() -> dict[str, str]:
        result = (
            db.table("accounts")
            .select("id, code")
            .eq("tenant_id", tenant_id)
            .in_("code", ["1200", "7900"])
            .execute()
        )
        return {r["code"]: r["id"] for r in (result.data or [])}

    acct_map = await asyncio.to_thread(_get_accounts)

    def _system_actor() -> str | None:
        result = (
            db.table("tenant_users")
            .select("user_id")
            .eq("tenant_id", tenant_id)
            .order("created_at")
            .limit(1)
            .execute()
        )
        return result.data[0]["user_id"] if result.data else None

    actor_uuid = await asyncio.to_thread(_system_actor)
    if actor_uuid is None:
        logger.error(
            "fx_gain_loss: no tenant_users actor — cannot post FX journal",
            extra={"invoice_id": invoice_id, "tenant_id": tenant_id},
        )
        return None

    if delta > Decimal("0"):
        # Gain: DR 1200 AR (reversal) / CR 7900 Realized FX Gain/Loss
        lines = [
            JournalLineSpec(
                direction="DR",
                account_code="1200",
                amount=delta,
                description=f"FX gain on invoice {invoice_number}",
                account_id=acct_map.get("1200"),
                currency=base_currency,
                base_amount=delta,
            ),
            JournalLineSpec(
                direction="CR",
                account_code="7900",
                amount=delta,
                description=f"FX gain on invoice {invoice_number}",
                account_id=acct_map.get("7900"),
                currency=base_currency,
                base_amount=delta,
            ),
        ]
        label = "gain"
    else:
        # Loss: DR 7900 Realized FX Gain/Loss / CR 1200 AR (reversal)
        abs_delta = delta.copy_abs()
        lines = [
            JournalLineSpec(
                direction="DR",
                account_code="7900",
                amount=abs_delta,
                description=f"FX loss on invoice {invoice_number}",
                account_id=acct_map.get("7900"),
                currency=base_currency,
                base_amount=abs_delta,
            ),
            JournalLineSpec(
                direction="CR",
                account_code="1200",
                amount=abs_delta,
                description=f"FX loss on invoice {invoice_number}",
                account_id=acct_map.get("1200"),
                currency=base_currency,
                base_amount=abs_delta,
            ),
        ]
        label = "loss"

    try:
        post_journal(
            db=db,
            tenant_id=tenant_id,
            created_by=actor_uuid,
            description=f"Realised FX {label} on invoice {invoice_number}",
            entry_date=datetime.date.today().isoformat(),
            reference_type="fx_gain_loss",
            reference_id=invoice_id,
            lines=lines,
        )
        logger.info(
            "fx_gain_loss: posted %s journal delta=%s for invoice %s",
            label,
            delta,
            invoice_id,
            extra={"tenant_id": tenant_id},
        )
    except Exception:
        logger.error(
            "fx_gain_loss: failed to post %s journal for invoice %s",
            label,
            invoice_id,
            exc_info=True,
            extra={"tenant_id": tenant_id},
        )
        return None

    return delta
