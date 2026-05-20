"""bill_pay_agent — proposes payment batches.

ALWAYS L2 (suggest): money-out actions are too sensitive for auto-apply.
The proposal is always written as an agent_suggestion with hitl_required=True.

# Prahari review required — see docs/team/SECURITY_REVIEW.md
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from pydantic import BaseModel, Field

from app.agents.base import AgentDeps

logger = logging.getLogger(__name__)


class BillPayProposal(BaseModel):
    proposed_bill_ids: list[str]
    proposed_pay_date: str  # ISO date string
    total_amount: Decimal
    currency: str
    rationale: str
    confidence: float = Field(default=0.92, ge=0.0, le=1.0)
    early_pay_discount_captured: bool = False
    flagged_for_review: list[dict] = []  # bills with unusual amounts


def propose_payment_batch(
    deps: AgentDeps,
    due_within_days: int = 7,
) -> BillPayProposal:
    """Propose a batch of bills to pay based on due dates.

    Logic:
    1. Find approved bills due within ``due_within_days`` days.
    2. If none found, fall back to all approved bills (up to 20).
    3. Flag any bill over $50,000 for mandatory human review.

    Returns a BillPayProposal — always L2 (HITL required for money-out).
    """
    db = deps.db

    cutoff = (date.today() + timedelta(days=due_within_days)).isoformat()
    bills = (
        db.table("bills")
        .select("id, bill_number, total, currency, due_date, vendor_invoice_number, client_id")
        .eq("tenant_id", deps.tenant_id)
        .eq("status", "approved")
        .is_("deleted_at", "null")
        .lte("due_date", cutoff)
        .execute()
        .data
        or []
    )

    if not bills:
        # Fall back to all approved bills if nothing is due soon
        bills = (
            db.table("bills")
            .select("id, bill_number, total, currency, due_date, vendor_invoice_number, client_id")
            .eq("tenant_id", deps.tenant_id)
            .eq("status", "approved")
            .is_("deleted_at", "null")
            .limit(20)
            .execute()
            .data
            or []
        )

    total = sum(Decimal(str(b["total"])) for b in bills)
    currency = bills[0]["currency"] if bills else "USD"

    # Earliest due date among bills that have one
    due_dates = [b["due_date"] for b in bills if b.get("due_date")]
    proposed_pay_date = min(due_dates) if due_dates else date.today().isoformat()

    flagged: list[dict] = []
    for b in bills:
        if Decimal(str(b.get("total", "0"))) > Decimal("50000"):
            flagged.append(
                {
                    "bill_id": b["id"],
                    "bill_number": b.get("bill_number", ""),
                    "reason": "high value — manual review recommended",
                }
            )

    logger.info(
        "bill_pay_agent_proposed",
        extra={
            "tenant_id": deps.tenant_id,
            "bill_count": len(bills),
            "total": str(total),
            "flagged_count": len(flagged),
        },
    )

    return BillPayProposal(
        proposed_bill_ids=[b["id"] for b in bills],
        proposed_pay_date=proposed_pay_date,
        total_amount=total,
        currency=currency,
        rationale=(
            f"Proposing {len(bills)} bill(s) due within {due_within_days} days. "
            f"Total: {currency} {total}."
            + (f" {len(flagged)} high-value bill(s) flagged for review." if flagged else "")
        ),
        flagged_for_review=flagged,
    )
