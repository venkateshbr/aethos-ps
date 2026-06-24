"""Collections Agent — drafts dunning emails for overdue invoices.

Tone tiers (based on days_overdue):
  1-7  days -> "gentle"  - friendly reminder
  8-30 days -> "firm"    - payment overdue
  30+  days -> "final"   - urgent notice, escalation_recommended=True

This is a pure-Python drafting function (no LLM call) because the dunning
copy is deterministic and rules-based.  The output is typed via
``CollectionsDraft`` so it slots cleanly into the HITL suggestion pipeline.

Called by ``backend/app/workers/collections.py`` every night.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.agents.base import AgentDeps
from app.models.collections_policy import (
    CollectionsPolicyConfig,
    CollectionTone,
)
from app.services.collections_policy_service import default_collections_policy

logger = logging.getLogger(__name__)


class CollectionsDraft(BaseModel):
    """Typed output of the collections drafting function."""

    invoice_id: str
    client_name: str
    client_email: str
    invoice_number: str
    amount_due: Decimal
    currency: str
    days_overdue: int
    tone: str  # "gentle" | "firm" | "final"
    subject: str
    body_html: str
    escalation_recommended: bool = False
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    policy_id: str | None = None
    policy_source: str = "system_default"
    cooldown_days: int = 7
    max_reminders_per_invoice: int = 3


_AUTO_SEND_TONE_RANK = {"none": 0, "gentle": 1, "firm": 2, "final": 3}


def days_overdue_for_invoice(invoice: dict) -> int:
    """Return non-negative days overdue for an invoice row."""
    today = date.today()
    due = date.fromisoformat(invoice["due_date"]) if invoice.get("due_date") else today
    return max(0, (today - due).days)


def collection_tone_for_days(
    days_overdue: int,
    policy: CollectionsPolicyConfig | None = None,
) -> CollectionTone | None:
    """Resolve the reminder tone for a day count under a collections policy."""
    active_policy = policy or default_collections_policy()
    if not active_policy.is_enabled or days_overdue < active_policy.gentle_after_days:
        return None
    if days_overdue >= active_policy.final_after_days:
        return "final"
    if days_overdue >= active_policy.firm_after_days:
        return "firm"
    return "gentle"


def policy_allows_auto_send(
    policy: CollectionsPolicyConfig | None,
    tone: str,
) -> bool:
    """Return whether policy allows this tone to be sent without HITL."""
    active_policy = policy or default_collections_policy()
    allowed_rank = _AUTO_SEND_TONE_RANK[active_policy.max_auto_send_tone]
    tone_rank = _AUTO_SEND_TONE_RANK.get(tone, 0)
    return allowed_rank > 0 and 0 < tone_rank <= allowed_rank


def draft_collection_email(
    invoice: dict,
    deps: AgentDeps,
    policy: CollectionsPolicyConfig | None = None,
    tone: CollectionTone | None = None,
) -> CollectionsDraft:
    """Draft a dunning email for a single overdue invoice.

    Parameters
    ----------
    invoice:  Row from the ``invoices`` table (must include id, invoice_number,
              total, currency, due_date, client_id, stripe_payment_link_url).
    deps:     Tenant-scoped agent dependencies.

    Returns
    -------
    A fully-populated :class:`CollectionsDraft`.
    """
    active_policy = policy or default_collections_policy()
    due = date.fromisoformat(invoice["due_date"]) if invoice.get("due_date") else date.today()
    days = days_overdue_for_invoice(invoice)

    resolved_tone = tone or collection_tone_for_days(days, active_policy) or "gentle"

    # Fetch client name
    client_result = (
        deps.db.table("clients")
        .select("name")
        .eq("id", invoice.get("client_id", ""))
        .execute()
    )
    client_name = client_result.data[0]["name"] if client_result.data else "Valued Client"

    # Fetch firm name
    tenant_result = (
        deps.db.table("tenants")
        .select("name")
        .eq("id", deps.tenant_id)
        .execute()
    )
    firm = tenant_result.data[0]["name"] if tenant_result.data else "Our Firm"

    amount = Decimal(str(invoice.get("total", "0")))
    currency = invoice.get("currency", "USD")
    inv_num = invoice.get("invoice_number", "INV")

    # Payment button (only rendered when a Stripe payment link exists)
    link = invoice.get("stripe_payment_link_url", "")
    pay_btn = (
        f'<p><a href="{link}" style="background:#10b981;color:#fff;padding:10px 20px;'
        f'border-radius:6px;text-decoration:none;">Pay Now</a></p>'
        if link
        else ""
    )

    if resolved_tone == "gentle":
        subject = f"Friendly reminder: Invoice {inv_num} is due"
        body_html = (
            f"<p>Hi {client_name},</p>"
            f"<p>Invoice <strong>{inv_num}</strong> for <strong>{currency} {amount}</strong> "
            f"was due on {due.strftime('%B %d, %Y')}.</p>"
            f"{pay_btn}"
            f"<p>Best, {firm}</p>"
        )
    elif resolved_tone == "firm":
        subject = f"Payment overdue: Invoice {inv_num} ({days} days past due)"
        body_html = (
            f"<p>Hi {client_name},</p>"
            f"<p>Invoice <strong>{inv_num}</strong> for <strong>{currency} {amount}</strong> "
            f"is {days} days overdue. Please arrange payment promptly.</p>"
            f"{pay_btn}"
            f"<p>{firm}</p>"
        )
    else:
        subject = f"URGENT: Invoice {inv_num} — {days} days overdue"
        body_html = (
            f"<p>Hi {client_name},</p>"
            f"<p>Invoice <strong>{inv_num}</strong> ({currency} {amount}) remains unpaid "
            f"after {days} days. This is our final notice.</p>"
            f"{pay_btn}"
            f"<p>{firm}</p>"
        )

    return CollectionsDraft(
        invoice_id=invoice["id"],
        client_name=client_name,
        client_email="",  # populated by the worker after drafting
        invoice_number=inv_num,
        amount_due=amount,
        currency=currency,
        days_overdue=days,
        tone=resolved_tone,
        subject=subject,
        body_html=body_html,
        escalation_recommended=(resolved_tone == "final"),
        policy_id=active_policy.id,
        policy_source=active_policy.policy_source,
        cooldown_days=active_policy.cooldown_days,
        max_reminders_per_invoice=active_policy.max_reminders_per_invoice,
    )
