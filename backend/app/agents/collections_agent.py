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


def draft_collection_email(invoice: dict, deps: AgentDeps) -> CollectionsDraft:
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
    today = date.today()
    due = date.fromisoformat(invoice["due_date"]) if invoice.get("due_date") else today
    days = max(0, (today - due).days)

    # Tone tier
    if days <= 7:
        tone = "gentle"
    elif days <= 30:
        tone = "firm"
    else:
        tone = "final"

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

    if tone == "gentle":
        subject = f"Friendly reminder: Invoice {inv_num} is due"
        body_html = (
            f"<p>Hi {client_name},</p>"
            f"<p>Invoice <strong>{inv_num}</strong> for <strong>{currency} {amount}</strong> "
            f"was due on {due.strftime('%B %d, %Y')}.</p>"
            f"{pay_btn}"
            f"<p>Best, {firm}</p>"
        )
    elif tone == "firm":
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
        tone=tone,
        subject=subject,
        body_html=body_html,
        escalation_recommended=(tone == "final"),
    )
