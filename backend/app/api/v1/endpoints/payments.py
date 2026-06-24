"""Payments router — AR payment receipts and reconciliation operations."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.workers.stripe_reconcile_worker import reconcile_sent_invoices
from supabase import Client

router = APIRouter()


@router.get("", summary="List AR payment receipts for the tenant")
def list_payments(
    limit: int = 50,
    tenant_id: str = Depends(get_tenant_id),
    _: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: Client = Depends(get_user_rls_client),  # noqa: B008
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


@router.post("/reconcile-stripe", summary="Run Stripe payment reconciliation for this tenant")
async def reconcile_stripe_payments(
    min_age_hours: float = Query(default=24, ge=0, le=720),
    tenant_id: str = Depends(get_tenant_id),
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> dict:
    """Run the delayed-webhook Stripe reconciliation worker for one tenant.

    Operators use the default 24-hour window. E2E can pass ``min_age_hours=0``
    after completing a Stripe test-mode checkout to verify the same path without
    waiting overnight.
    """
    return await asyncio.to_thread(
        reconcile_sent_invoices,
        tenant_id,
        min_age_hours,
    )
