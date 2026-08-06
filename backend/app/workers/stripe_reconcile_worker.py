"""Procrastinate task: nightly Stripe webhook reconciliation.

For invoices stuck in 'sent' state older than 24 hours, checks Stripe for
paid checkout sessions and records the missed payment — catching dropped
webhooks.

Scheduled nightly at 02:00 UTC. Can be triggered manually:
    uv run python -m procrastinate --app=app.workers.procrastinate_app.app \
        defer app.workers.stripe_reconcile_worker.reconcile_sent_invoices \
        --args '{"tenant_id": "<uuid>"}'
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import stripe

from app.core.config import settings
from app.core.db import get_service_role_client
from app.services.billing.stripe_service import StripeService
from app.services.stripe_checkout_payments import record_checkout_session_payment
from app.workers.procrastinate_app import app

logger = logging.getLogger(__name__)


@app.periodic(cron="15 * * * *")
@app.task(name="stripe_reconcile.reconcile_subscription_states", queue="cron")
def reconcile_subscription_states(timestamp: int) -> dict:
    """Converge locally overdue trials with Stripe's current subscription state."""
    if not settings.stripe_secret_key:
        logger.warning("stripe_reconcile_worker: skipping subscriptions — Stripe not configured")
        return {"reconciled": 0, "unchanged": 0, "errors": 0}

    db = get_service_role_client()
    as_of = datetime.fromtimestamp(timestamp, tz=UTC)
    tenants = (
        db.table("tenants")
        .select("id, stripe_subscription_id, stripe_subscription_status, trial_ends_at")
        .eq("stripe_subscription_status", "trialing")
        .lt("trial_ends_at", as_of.isoformat())
        .execute()
        .data
        or []
    )
    stripe_svc = StripeService(settings)
    reconciled = 0
    unchanged = 0
    errors = 0

    for tenant in tenants:
        subscription_id = tenant.get("stripe_subscription_id")
        if not subscription_id:
            unchanged += 1
            continue
        try:
            provider = asyncio.run(stripe_svc.retrieve_subscription(subscription_id))
            update: dict[str, object] = {
                "stripe_subscription_status": provider["status"],
                "stripe_subscription_reconciled_at": as_of.isoformat(),
            }
            if provider.get("trial_end"):
                update["trial_ends_at"] = datetime.fromtimestamp(
                    int(provider["trial_end"]), tz=UTC
                ).isoformat()
            (db.table("tenants").update(update).eq("id", tenant["id"]).execute())
            if provider["status"] == tenant.get("stripe_subscription_status"):
                unchanged += 1
            else:
                reconciled += 1
        except Exception:
            errors += 1
            logger.exception(
                "stripe_reconcile_worker: subscription reconciliation failed",
                extra={"tenant_id": tenant.get("id")},
            )

    return {"reconciled": reconciled, "unchanged": unchanged, "errors": errors}


@app.task(name="stripe_reconcile.reconcile_sent_invoices")
def reconcile_sent_invoices(tenant_id: str, min_age_hours: float = 24) -> dict:
    """Check Stripe for paid sessions on sent invoices older than 24 h.

    For each match, records the same payment row and accounting journal as the
    webhook handler. Duplicate payment intents are skipped by the shared
    payment recorder.

    Returns:
        {"reconciled": int, "skipped": int, "errors": int}
    """
    if not settings.stripe_secret_key:
        logger.warning("stripe_reconcile_worker: skipping — stripe_secret_key not configured")
        return {"reconciled": 0, "skipped": 0, "errors": 0}

    stripe.api_key = settings.stripe_secret_key
    db = get_service_role_client()

    cutoff = (datetime.now(UTC) - timedelta(hours=min_age_hours)).isoformat()
    invoices = (
        db.table("invoices")
        .select("id, invoice_number, stripe_payment_link_id")
        .eq("tenant_id", tenant_id)
        .eq("status", "sent")
        .lt("sent_at", cutoff)
        .is_("paid_at", "null")
        .execute()
        .data
        or []
    )

    reconciled = 0
    skipped = 0
    errors = 0

    for invoice in invoices:
        plink_id: str | None = invoice.get("stripe_payment_link_id")
        if not plink_id:
            skipped += 1
            continue

        try:
            sessions = stripe.checkout.Session.list(payment_link=plink_id, limit=5)
            paid_session = None
            for session in sessions.auto_paging_iter():
                if session.payment_status == "paid":
                    paid_session = session
                    break

            if paid_session is None:
                skipped += 1
                continue

            result = asyncio.run(
                record_checkout_session_payment(
                    db=db,
                    session=paid_session,
                    event_id=getattr(paid_session, "id", None),
                    fallback_invoice_id=invoice["id"],
                    fallback_tenant_id=tenant_id,
                    source="stripe_reconciliation",
                )
            )
            if result["status"] == "recorded":
                reconciled += 1
            elif result["status"] == "duplicate":
                skipped += 1
            else:
                errors += 1
            logger.info(
                "stripe_reconcile_worker: invoice %s session %s result=%s",
                invoice.get("invoice_number", invoice["id"]),
                paid_session.id,
                result["status"],
                extra={"tenant_id": tenant_id, "invoice_id": invoice["id"]},
            )

        except stripe.StripeError as exc:
            errors += 1
            logger.error(
                "stripe_reconcile_worker: Stripe error for invoice %s: %s",
                invoice.get("id"),
                exc,
                extra={"tenant_id": tenant_id},
            )
        except Exception as exc:
            errors += 1
            logger.error(
                "stripe_reconcile_worker: reconciliation error for invoice %s: %s",
                invoice.get("id"),
                exc,
                extra={"tenant_id": tenant_id},
            )

    logger.info(
        "stripe_reconcile_worker: completed tenant=%s reconciled=%d skipped=%d errors=%d",
        tenant_id,
        reconciled,
        skipped,
        errors,
    )
    return {"reconciled": reconciled, "skipped": skipped, "errors": errors}
