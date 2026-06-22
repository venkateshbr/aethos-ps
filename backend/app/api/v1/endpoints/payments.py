"""Payments router — AR payment receipts (read-only list)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from supabase import Client

router = APIRouter()


@router.get("", summary="List AR payment receipts for the tenant")
def list_payments(
    limit: int = 50,
    tenant_id: str = Depends(get_tenant_id),
    _: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> dict:
    """Return the most-recent payment receipts, joined to invoice number.

    Payments are created automatically by the Stripe webhook when an invoice
    is marked paid. Manual payments can also be recorded via the HITL flow.
    """
    rows = (
        db.table("payments")
        .select("id, invoice_id, amount, currency, base_amount, paid_at, notes, "
                "invoices(invoice_number, status)")
        .eq("tenant_id", tenant_id)
        .order("paid_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )

    items = []
    for r in rows:
        inv = r.get("invoices") or {}
        items.append({
            "id": r["id"],
            "invoice_id": r["invoice_id"],
            "invoice_number": inv.get("invoice_number") if isinstance(inv, dict) else None,
            "amount": str(r["amount"]),
            "currency": r["currency"],
            "base_amount": str(r["base_amount"]),
            "paid_at": r["paid_at"],
            "notes": r.get("notes"),
        })

    return {"items": items, "total": len(items)}
