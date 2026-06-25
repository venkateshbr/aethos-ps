"""Shared FX helpers for AR payment settlement."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.fx import get_fx_rate_record
from app.domain.money import quantise_money
from supabase import Client


@dataclass(frozen=True)
class PaymentFxAmounts:
    amount: Decimal
    currency: str
    base_amount: Decimal
    base_currency: str
    rate: Decimal
    rate_date: date
    fx_rate_id: str | None = None


def payment_rate_date(paid_at: date | datetime | str | None) -> date:
    if paid_at is None:
        return date.today()
    if isinstance(paid_at, datetime):
        return paid_at.date()
    if isinstance(paid_at, date):
        return paid_at
    value = paid_at.strip()
    if len(value) >= 10:
        return date.fromisoformat(value[:10])
    return date.today()


async def tenant_base_currency(db: Client, tenant_id: str) -> str:
    def _fetch() -> str:
        result = (
            db.table("tenants")
            .select("base_currency")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        row = result.data[0] if result.data else {}
        return str(row.get("base_currency") or "USD").upper()

    return await asyncio.to_thread(_fetch)


async def payment_fx_amounts(
    *,
    db: Client,
    tenant_id: str,
    amount: Decimal,
    currency: str,
    paid_at: date | datetime | str | None,
) -> PaymentFxAmounts:
    payment_currency = currency.upper()
    base_currency = await tenant_base_currency(db, tenant_id)
    rate_date = payment_rate_date(paid_at)
    if payment_currency == base_currency:
        return PaymentFxAmounts(
            amount=amount,
            currency=payment_currency,
            base_amount=amount,
            base_currency=base_currency,
            rate=Decimal("1"),
            rate_date=rate_date,
            fx_rate_id=None,
        )

    rate_record = await get_fx_rate_record(payment_currency, base_currency, rate_date, db)
    base_amount = quantise_money(amount * rate_record.rate)
    if base_amount is None:
        raise ValueError("Payment base amount could not be calculated")
    return PaymentFxAmounts(
        amount=amount,
        currency=payment_currency,
        base_amount=base_amount,
        base_currency=base_currency,
        rate=rate_record.rate,
        rate_date=rate_record.rate_date,
        fx_rate_id=rate_record.id,
    )
