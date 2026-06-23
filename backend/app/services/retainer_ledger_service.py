"""Retainer ledger helpers."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from app.domain.money import serialise_money

_TABLE = "retainer_ledger_entries"
_CREDIT_TYPES = {"deposit", "credit_adjustment"}
_DEBIT_TYPES = {"draw", "debit_adjustment"}


def retainer_balance_for_engagement(
    db,
    tenant_id: str,
    engagement_id: str,
) -> tuple[Decimal, bool]:
    """Return current balance and whether ledger rows exist."""
    rows = (
        db.table(_TABLE)
        .select("entry_type, amount")
        .eq("tenant_id", tenant_id)
        .eq("engagement_id", engagement_id)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    if not isinstance(rows, list):
        return Decimal("0"), False

    balance = Decimal("0")
    for row in rows:
        amount = Decimal(str(row.get("amount") or "0"))
        entry_type = str(row.get("entry_type") or "")
        if entry_type in _CREDIT_TYPES:
            balance += amount
        elif entry_type in _DEBIT_TYPES:
            balance -= amount
    return balance, bool(rows)


async def record_retainer_draw(
    db,
    *,
    tenant_id: str,
    engagement_id: str,
    invoice_id: str,
    amount: Decimal,
    currency: str,
    description: str,
    created_by_user_id: str | None = None,
    created_by_agent: str | None = None,
) -> dict | None:
    """Insert one draw ledger row for an invoice, idempotent by invoice."""
    if amount <= 0:
        return None

    existing = await asyncio.to_thread(
        lambda: db.table(_TABLE)
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("engagement_id", engagement_id)
        .eq("invoice_id", invoice_id)
        .eq("entry_type", "draw")
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
        .data
        or []
    )
    if existing:
        return existing[0]

    payload: dict = {
        "tenant_id": tenant_id,
        "engagement_id": engagement_id,
        "invoice_id": invoice_id,
        "entry_type": "draw",
        "amount": serialise_money(amount),
        "currency": currency,
        "description": description,
        "entry_date": date.today().isoformat(),
    }
    if created_by_user_id:
        payload["created_by_user_id"] = created_by_user_id
    if created_by_agent:
        payload["created_by_agent"] = created_by_agent

    result = await asyncio.to_thread(lambda: db.table(_TABLE).insert(payload).execute())
    return (result.data or [None])[0]
