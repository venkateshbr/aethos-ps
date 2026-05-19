"""Stripe webhook handler.

POST /api/v1/webhooks/stripe

Security:
- Raw body is read before any parsing (required for Stripe signature verification).
- Signature is verified before any state mutation.
- Unknown event types return 200 (Stripe requires this to stop retrying).
- Idempotency: ``provider_event_id`` is checked before processing; duplicate
  events return 200 immediately.

Events handled:
- customer.subscription.created  → update tenant billing status
- customer.subscription.updated  → update tenant billing status + trial_ends_at
- customer.subscription.deleted  → mark tenant canceled

Never log the full event payload — it may contain card data or PII.
Log only: event_id, event_type, stripe_customer_id (metadata only).
"""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.db import get_service_role_client
from app.core.stripe_deps import get_stripe_service
from app.repositories.tenant_repo import TenantRepository
from app.services.billing.stripe_service import StripeService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/stripe",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook receiver — signature verified, idempotent",
)
async def stripe_webhook(
    request: Request,
    db: Client = Depends(get_service_role_client),  # noqa: B008
    stripe_svc: StripeService = Depends(get_stripe_service),  # noqa: B008
) -> dict:
    """Process a Stripe webhook event.

    Returns ``{"received": True}`` for all events including unknowns —
    Stripe retries on any non-2xx response, so we must not 400/500 on
    events we don't handle.
    """
    # ------------------------------------------------------------------
    # 1. Read raw body and signature header
    # ------------------------------------------------------------------
    payload: bytes = await request.body()
    sig_header: str = request.headers.get("stripe-signature", "")

    # ------------------------------------------------------------------
    # 2. Verify signature
    # ------------------------------------------------------------------
    try:
        event = await stripe_svc.construct_webhook_event(payload, sig_header)
    except ValueError as exc:
        logger.warning("Stripe webhook signature invalid; returning 400")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        ) from exc

    event_id: str = event.id
    event_type: str = event.type

    logger.info(
        "Stripe webhook received",
        extra={"event_id": event_id, "event_type": event_type},
    )

    # ------------------------------------------------------------------
    # 3. Idempotency check — skip if already processed
    # ------------------------------------------------------------------
    tenant_repo = TenantRepository(db)
    existing = await tenant_repo.get_webhook_event(event_id)
    if existing:
        logger.info(
            "Stripe webhook already processed — skipping",
            extra={"event_id": event_id, "event_type": event_type},
        )
        return {"received": True}

    # ------------------------------------------------------------------
    # 4. Dispatch to handler
    # ------------------------------------------------------------------
    try:
        await _dispatch(event, tenant_repo)
    except Exception:
        # Log but do not re-raise — we must return 200 so Stripe stops retrying.
        # The event is still recorded in webhook_events for audit / reconciliation.
        logger.error(
            "Stripe webhook handler error",
            exc_info=True,
            extra={"event_id": event_id, "event_type": event_type},
        )

    # ------------------------------------------------------------------
    # 5. Record processed event (idempotency log)
    # ------------------------------------------------------------------
    stripe_customer_id: str | None = _extract_customer_id(event)
    tenant_id: str | None = None
    if stripe_customer_id:
        tenant = await tenant_repo.get_by_stripe_customer(stripe_customer_id)
        if tenant:
            tenant_id = tenant.get("id")

    try:
        await tenant_repo.record_webhook_event(
            provider_event_id=event_id,
            event_type=event_type,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.error(
            "Failed to record webhook event",
            exc_info=True,
            extra={"event_id": event_id},
        )

    return {"received": True}


# ---------------------------------------------------------------------------
# Internal dispatch
# ---------------------------------------------------------------------------


async def _dispatch(event: stripe.Event, tenant_repo: TenantRepository) -> None:
    """Route the event to the appropriate handler.  Unknown events are no-ops."""
    event_type: str = event.type

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        await _handle_subscription_upserted(event, tenant_repo)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(event, tenant_repo)
    else:
        # Log at DEBUG; returning 200 is correct — Stripe requires it.
        logger.debug(
            "Unhandled Stripe event type — ignoring",
            extra={"event_type": event_type},
        )


async def _handle_subscription_upserted(
    event: stripe.Event,
    tenant_repo: TenantRepository,
) -> None:
    """Handle subscription.created and subscription.updated."""
    sub = event.data.object  # stripe.Subscription
    stripe_customer_id: str = sub.customer

    tenant = await tenant_repo.get_by_stripe_customer(stripe_customer_id)
    if not tenant:
        logger.warning(
            "Subscription event for unknown Stripe customer — skipping",
            extra={"event_id": event.id, "stripe_customer_id": stripe_customer_id},
        )
        return

    update: dict = {
        "stripe_subscription_id": sub.id,
        "stripe_subscription_status": sub.status,
    }
    if sub.trial_end:
        import datetime

        update["trial_ends_at"] = datetime.datetime.fromtimestamp(
            sub.trial_end, tz=datetime.UTC
        ).isoformat()

    await tenant_repo.update_tenant(tenant["id"], update)
    logger.info(
        "Tenant billing status updated from webhook",
        extra={
            "event_id": event.id,
            "tenant_id": tenant["id"],
            "stripe_subscription_status": sub.status,
        },
    )


async def _handle_subscription_deleted(
    event: stripe.Event,
    tenant_repo: TenantRepository,
) -> None:
    """Handle subscription.deleted — mark tenant as canceled."""
    sub = event.data.object
    stripe_customer_id: str = sub.customer

    tenant = await tenant_repo.get_by_stripe_customer(stripe_customer_id)
    if not tenant:
        logger.warning(
            "Subscription deletion event for unknown Stripe customer",
            extra={"event_id": event.id, "stripe_customer_id": stripe_customer_id},
        )
        return

    await tenant_repo.update_tenant(
        tenant["id"],
        {
            "stripe_subscription_status": "canceled",
            "status": "canceled",
        },
    )
    logger.info(
        "Tenant subscription canceled from webhook",
        extra={"event_id": event.id, "tenant_id": tenant["id"]},
    )


def _extract_customer_id(event: stripe.Event) -> str | None:
    """Extract the Stripe customer ID from an event object if present."""
    try:
        obj = event.data.object
        return getattr(obj, "customer", None)
    except Exception:
        return None
