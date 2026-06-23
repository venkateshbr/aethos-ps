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
from app.domain.payment_optimization import build_payment_optimization

logger = logging.getLogger(__name__)

_ACTIVE_PROPOSAL_STATUSES = ("pending", "approved", "auto_applied")


class BillPayProposal(BaseModel):
    proposed_bill_ids: list[str]
    proposed_pay_date: str  # ISO date string
    total_amount: Decimal
    currency: str
    rationale: str
    confidence: float = Field(default=0.92, ge=0.0, le=1.0)
    early_pay_discount_captured: bool = False
    flagged_for_review: list[dict] = []  # bills with unusual amounts
    optimization_summary: dict = Field(default_factory=dict)


def find_duplicate_payment_proposal(
    deps: AgentDeps,
    proposed_bill_ids: list[str],
) -> str | None:
    """Return an active matching bill-pay suggestion id, if one exists."""
    target = _normalise_bill_ids(proposed_bill_ids)
    if not target:
        return None

    rows = (
        deps.db.table("agent_suggestions")
        .select("id, output_snapshot")
        .eq("tenant_id", deps.tenant_id)
        .eq("agent_name", "bill_pay_agent")
        .eq("action_type", "create_bill_payment_batch")
        .in_("status", list(_ACTIVE_PROPOSAL_STATUSES))
        .execute()
        .data
        or []
    )
    for row in rows:
        output = row.get("output_snapshot") or {}
        if not isinstance(output, dict):
            continue
        existing = output.get("proposed_bill_ids") or output.get("bill_ids") or []
        if _normalise_bill_ids(existing) == target:
            return str(row["id"])
    return None


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

    # Earliest due date among bills that have one; never propose a past pay date.
    due_dates = [
        date.fromisoformat(str(b["due_date"])[:10])
        for b in bills
        if b.get("due_date")
    ]
    today = date.today()
    proposed_pay_date_value = max(today, min(due_dates)) if due_dates else today
    proposed_pay_date = proposed_pay_date_value.isoformat()
    optimization = build_payment_optimization(
        bills,
        pay_date=proposed_pay_date_value,
    )
    bills = optimization.ranked_bills

    flagged: list[dict] = list(optimization.summary.get("manual_review_flags") or [])

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
            + (f" {len(flagged)} payment review flag(s)." if flagged else "")
        ),
        flagged_for_review=flagged,
        optimization_summary=optimization.summary,
    )


def _normalise_bill_ids(values: list[object]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if value}))
