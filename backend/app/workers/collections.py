"""collections_worker — nightly ARQ task; drafts/sends dunning emails.

Schedule: daily at 06:00 UTC (configured in arq_settings.py).

For each active tenant, queries overdue invoices (status in ['sent','overdue']
with due_date < today) and either:
  - L3 + confidence >= threshold + email known → sends immediately via Resend
  - Otherwise → creates an agent_suggestion / hitl_task for human review

Graceful degradation: per-invoice exceptions are caught and logged; the
worker continues processing remaining invoices.
"""

from __future__ import annotations

import logging
from datetime import date

from app.agents.base import AgentDeps
from app.agents.collections_agent import draft_collection_email
from app.agents.suggestion_writer import write_agent_suggestion
from app.core.config import settings
from app.services.resend_service import ResendService
from supabase import create_client

logger = logging.getLogger(__name__)


async def collections_worker(ctx: dict) -> dict:
    """Nightly dunning email worker.

    Returns
    -------
    ``{"sent": int, "hitl_queued": int}``
    """
    db = create_client(settings.supabase_url, settings.supabase_service_role_key)
    resend = ResendService()
    today = date.today().isoformat()

    tenants = (
        db.table("tenants").select("id").eq("status", "active").execute().data or []
    )
    sent = 0
    hitl = 0

    for t in tenants:
        tid = t["id"]
        deps = AgentDeps(tenant_id=tid, user_id=None, db=db)

        overdue = (
            db.table("invoices")
            .select(
                "id,invoice_number,total,currency,due_date,client_id,stripe_payment_link_url"
            )
            .eq("tenant_id", tid)
            .in_("status", ["sent", "overdue"])
            .lt("due_date", today)
            .execute()
            .data
            or []
        )

        for inv in overdue:
            try:
                draft = draft_collection_email(inv, deps)

                # Resolve client billing email
                client_result = (
                    db.table("clients")
                    .select("billing_address")
                    .eq("id", inv.get("client_id", ""))
                    .execute()
                )
                billing_addr = (
                    (client_result.data[0] if client_result.data else {}).get(
                        "billing_address"
                    )
                    or {}
                )
                email = billing_addr.get("email", "")
                draft.client_email = email

                # Look up autonomy settings for this agent/action
                autonomy_result = (
                    db.table("agent_autonomy_settings")
                    .select("level,confidence_threshold")
                    .eq("tenant_id", tid)
                    .eq("agent_name", "collections_agent")
                    .eq("action_type", "send_email")
                    .execute()
                )
                autonomy_row = autonomy_result.data[0] if autonomy_result.data else {}
                level = autonomy_row.get("level", 2)
                threshold = float(autonomy_row.get("confidence_threshold", 0.80))

                if level >= 3 and draft.confidence >= threshold and email:
                    resend.send_email(email, draft.subject, draft.body_html)
                    sent += 1
                    logger.info(
                        "collections_worker: sent email",
                        extra={
                            "invoice_id": inv["id"],
                            "tenant_id": tid,
                            "tone": draft.tone,
                        },
                    )
                else:
                    await write_agent_suggestion(
                        deps,
                        "collections_agent",
                        "send_email",
                        document_id=inv["id"],
                        output=draft.model_dump(mode="json"),
                        confidence=draft.confidence,
                        autonomy_level=2,
                    )
                    hitl += 1

            except Exception as e:
                logger.error(
                    "collections_error",
                    extra={"invoice_id": inv.get("id"), "tenant_id": tid, "error": str(e)},
                )

    logger.info("collections_done", extra={"sent": sent, "hitl": hitl})
    return {"sent": sent, "hitl_queued": hitl}
