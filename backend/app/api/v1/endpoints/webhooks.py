"""Stripe webhook handler.

POST /api/v1/webhooks/stripe

Security:
- Raw body is read before any parsing (required for Stripe signature verification).
- Signature is verified before any state mutation.
- Unknown event types return 200 (Stripe requires this to stop retrying).
- Idempotency: ``provider_event_id`` is checked before processing; duplicate
  events return 200 immediately.
- Service-role client is used (bypasses RLS) since webhooks are server-to-server
  with no user session — the event metadata carries tenant_id.

Events handled:
- customer.subscription.created     → update tenant billing status
- customer.subscription.updated     → update tenant billing status + trial_ends_at
- customer.subscription.deleted     → mark tenant canceled
- checkout.session.completed        → record payment, post AR journal, mark invoice paid
- account.updated (Connect)         → sync charges_enabled / payouts_enabled for tenant

Never log the full event payload — it may contain card data or PII.
Log only: event_id, event_type, stripe_customer_id (metadata only).
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import asyncio
import datetime
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.db import get_service_role_client
from app.core.stripe_deps import get_stripe_service
from app.repositories.tenant_repo import TenantRepository
from app.services.billing.stripe_service import StripeService
from app.services.stripe_checkout_payments import (
    record_checkout_session_payment,
)
from app.services.stripe_checkout_payments import (
    stripe_value as _stripe_value,
)
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
        await _dispatch(event, tenant_repo, db)
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
    tenant_id: str | None = _extract_tenant_id(event)
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


async def _dispatch(
    event: stripe.Event,
    tenant_repo: TenantRepository,
    db: Client,
) -> None:
    """Route the event to the appropriate handler.  Unknown events are no-ops."""
    event_type: str = event.type

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        await _handle_subscription_upserted(event, tenant_repo)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(event, tenant_repo)
    elif event_type == "checkout.session.completed":
        await _handle_checkout_session_completed(event, db)
    elif event_type == "account.updated":
        await _handle_account_updated(event, tenant_repo, db)
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
        customer = _stripe_value(obj, "customer")
        return str(customer) if customer else None
    except Exception:
        return None


def _extract_tenant_id(event: stripe.Event) -> str | None:
    """Extract tenant_id from Stripe object metadata when present."""
    try:
        obj = event.data.object
        metadata = _stripe_value(obj, "metadata") or {}
        tenant_id = _stripe_value(metadata, "tenant_id")
        return str(tenant_id) if tenant_id else None
    except Exception:
        return None


async def _handle_checkout_session_completed(
    event: stripe.Event,
    db: Client,
) -> None:
    """Handle checkout.session.completed — record payment and post AR journal."""
    await record_checkout_session_payment(
        db=db,
        session=event.data.object,
        event_id=event.id,
        source="stripe_webhook",
    )


async def _handle_account_updated(
    event: stripe.Event,
    tenant_repo: TenantRepository,
    db: Client,
) -> None:
    """Handle account.updated — sync Connect charges_enabled / payouts_enabled.

    Stripe sends this event whenever an account's state changes during
    onboarding (identity verification, bank account added, etc.).

    We look up the tenant by stripe_connect_account_id and update the
    connect status columns.
    """
    account = event.data.object
    connect_account_id: str = account.id
    charges_enabled: bool = getattr(account, "charges_enabled", False)
    payouts_enabled: bool = getattr(account, "payouts_enabled", False)

    # Look up tenant by connect account ID
    def _get_tenant() -> dict | None:
        result = (
            db.table("tenants")
            .select("id, stripe_connect_status")
            .eq("stripe_connect_account_id", connect_account_id)
            .execute()
        )
        return result.data[0] if result.data else None

    tenant = await asyncio.to_thread(_get_tenant)
    if tenant is None:
        logger.debug(
            "account.updated for unknown Connect account — skipping",
            extra={"connect_account_id": connect_account_id, "event_id": event.id},
        )
        return

    new_status = "active" if charges_enabled else "pending"
    await tenant_repo.update_tenant(
        tenant["id"],
        {
            "stripe_connect_status": new_status,
            "stripe_connect_charges_enabled": charges_enabled,
            "stripe_connect_payouts_enabled": payouts_enabled,
        },
    )

    logger.info(
        "Stripe Connect account status synced from account.updated",
        extra={
            "tenant_id": tenant["id"],
            "connect_account_id": connect_account_id,
            "charges_enabled": charges_enabled,
            "payouts_enabled": payouts_enabled,
            "event_id": event.id,
        },
    )
