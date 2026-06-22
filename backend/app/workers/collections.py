"""collections_worker — nightly Procrastinate task; drafts/sends dunning emails.

Schedule: daily at 06:00 UTC (configured via Procrastinate periodic decorator).

For each active tenant, queries overdue invoices (status in ['sent','overdue']
with due_date < today) and either:
  - L3 + confidence >= threshold + email known → sends immediately via Resend
  - Otherwise → creates an agent_suggestion / hitl_task for human review

Graceful degradation: per-invoice exceptions are caught and logged; the
worker continues processing remaining invoices.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from app.agents.base import AgentDeps
from app.agents.collections_agent import draft_collection_email
from app.agents.suggestion_writer import write_agent_suggestion
from app.core.config import settings
from app.services.resend_service import ResendService
from app.workers.procrastinate_app import app
from supabase import create_client

logger = logging.getLogger(__name__)

COLLECTIONS_COOLDOWN_DAYS = 7
_DECIDED_COLLECTION_STATUSES = ("pending", "approved", "auto_applied")


@app.periodic(cron="0 6 * * *")
@app.task(name="collections_worker", queue="cron")
async def collections_worker(timestamp: int) -> dict:
    """Nightly dunning email worker.

    Returns
    -------
    ``{"sent": int, "hitl_queued": int, "skipped_duplicates": int}``
    """
    _ = timestamp  # provided by Procrastinate periodic; we use date.today() instead
    db = create_client(settings.supabase_url, settings.supabase_service_role_key)
    resend = ResendService()
    today = date.today().isoformat()

    tenants = (
        db.table("tenants").select("id").eq("status", "active").execute().data or []
    )
    sent = 0
    hitl = 0
    skipped_duplicates = 0

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

                if _recent_collections_action_exists(db, tid, inv["id"], draft.tone):
                    skipped_duplicates += 1
                    logger.info(
                        "collections_worker: duplicate suppressed",
                        extra={
                            "invoice_id": inv["id"],
                            "tenant_id": tid,
                            "tone": draft.tone,
                        },
                    )
                    continue

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
                    suggestion = await write_agent_suggestion(
                        deps,
                        "collections_agent",
                        "send_email",
                        document_id=None,
                        output=draft.model_dump(mode="json"),
                        confidence=draft.confidence,
                        autonomy_level=3,
                        confidence_threshold=threshold,
                        related_entity_type="invoice",
                        related_entity_id=str(inv["id"]),
                    )
                    result = resend.send_email(email, draft.subject, draft.body_html)
                    if result.get("status") == "error":
                        _mark_suggestion_rejected(db, tid, str(suggestion["id"]))
                        raise RuntimeError(
                            f"collections email provider failed: {result.get('error')}"
                        )
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
                        document_id=None,
                        output=draft.model_dump(mode="json"),
                        confidence=draft.confidence,
                        autonomy_level=2,
                        related_entity_type="invoice",
                        related_entity_id=str(inv["id"]),
                    )
                    hitl += 1

            except Exception as e:
                logger.error(
                    "collections_error",
                    extra={"invoice_id": inv.get("id"), "tenant_id": tid, "error": str(e)},
                )

    logger.info(
        "collections_done",
        extra={"sent": sent, "hitl": hitl, "skipped_duplicates": skipped_duplicates},
    )
    return {"sent": sent, "hitl_queued": hitl, "skipped_duplicates": skipped_duplicates}


def _recent_collections_action_exists(
    db,
    tenant_id: str,
    invoice_id: str,
    tone: str,
) -> bool:
    """Suppress repeat reminders for the same invoice/tone within the cooldown."""
    cutoff = (date.today() - timedelta(days=COLLECTIONS_COOLDOWN_DAYS)).isoformat()
    rows = (
        db.table("agent_suggestions")
        .select("id, related_entity_id, output_snapshot")
        .eq("tenant_id", tenant_id)
        .eq("agent_name", "collections_agent")
        .eq("action_type", "send_email")
        .in_("status", list(_DECIDED_COLLECTION_STATUSES))
        .gte("created_at", cutoff)
        .execute()
        .data
        or []
    )
    for row in rows:
        output = row.get("output_snapshot") or {}
        if not isinstance(output, dict):
            continue
        same_invoice = str(row.get("related_entity_id") or output.get("invoice_id")) == str(
            invoice_id
        )
        if same_invoice and output.get("tone") == tone:
            return True
    return False


def _mark_suggestion_rejected(db, tenant_id: str, suggestion_id: str) -> None:
    """Best-effort correction when an audited L3 send fails after insert."""
    try:
        db.table("agent_suggestions").update({"status": "rejected"}).eq(
            "tenant_id", tenant_id
        ).eq("id", suggestion_id).execute()
    except Exception:
        logger.warning(
            "collections_worker: failed to reject failed auto-send suggestion",
            extra={"tenant_id": tenant_id, "suggestion_id": suggestion_id},
        )
