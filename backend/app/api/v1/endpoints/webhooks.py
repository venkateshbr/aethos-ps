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
from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.db import get_service_role_client
from app.core.stripe_deps import get_stripe_service
from app.domain.journal_helper import JournalLineSpec, post_journal
from app.repositories.tenant_repo import TenantRepository
from app.services.billing.stripe_service import StripeService
from app.services.fx_gain_loss_service import post_fx_gain_loss_if_needed
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


def _stripe_value(obj: object, key: str, default: object | None = None) -> object | None:
    """Read a field from dicts and StripeObject instances.

    StripeObject exposes webhook payload fields through attribute and index
    access, but nested objects such as ``metadata`` do not implement ``get``.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    getter = getattr(obj, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            try:
                return getter(key)
            except Exception:
                pass
    try:
        return obj[key]  # type: ignore[index]
    except Exception:
        return getattr(obj, key, default)


async def _handle_checkout_session_completed(
    event: stripe.Event,
    db: Client,
) -> None:
    """Handle checkout.session.completed — record payment and post AR journal.

    Flow:
      1. Extract invoice_id + tenant_id from session metadata (set on Payment Link creation).
      2. Idempotency check on stripe_payment_intent_id in payments table.
      3. Record payment row.
      4. Update invoice status → paid.
      5. Post GL journal: DR 1100 Bank / CR 1200 Accounts Receivable.

    Uses service-role client — no user session in webhook context.
    """
    session = event.data.object
    meta = _stripe_value(session, "metadata", {}) or {}

    invoice_id_raw = _stripe_value(meta, "invoice_id")
    tenant_id_raw = _stripe_value(meta, "tenant_id")
    invoice_id = str(invoice_id_raw) if invoice_id_raw else None
    tenant_id = str(tenant_id_raw) if tenant_id_raw else None

    if not invoice_id or not tenant_id:
        logger.warning(
            "checkout.session.completed missing metadata — skipping",
            extra={"event_id": event.id},
        )
        return

    payment_intent_raw = _stripe_value(session, "payment_intent")
    payment_intent_id = str(payment_intent_raw) if payment_intent_raw else None

    # ------------------------------------------------------------------
    # Idempotency: skip if this payment_intent was already recorded
    # ------------------------------------------------------------------
    def _check_existing() -> bool:
        if not payment_intent_id:
            return False
        result = (
            db.table("payments")
            .select("id")
            .eq("stripe_payment_intent_id", payment_intent_id)
            .execute()
        )
        return bool(result.data)

    already_recorded = await asyncio.to_thread(_check_existing)
    if already_recorded:
        logger.info(
            "Duplicate checkout.session.completed — skipping",
            extra={"payment_intent_id": payment_intent_id, "event_id": event.id},
        )
        return

    # ------------------------------------------------------------------
    # Fetch invoice
    # ------------------------------------------------------------------
    def _get_invoice() -> dict | None:
        result = (
            db.table("invoices")
            .select("*")
            .eq("id", invoice_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None

    invoice = await asyncio.to_thread(_get_invoice)
    if invoice is None:
        logger.error(
            "Invoice not found for checkout.session.completed",
            extra={"invoice_id": invoice_id, "tenant_id": tenant_id, "event_id": event.id},
        )
        return

    # Amount from Stripe is in the smallest currency unit (cents)
    amount_total_cents = int(_stripe_value(session, "amount_total", 0) or 0)
    currency = str(_stripe_value(session, "currency", "usd") or "usd").upper()
    amount_received = Decimal(str(amount_total_cents)) / Decimal("100")

    # ------------------------------------------------------------------
    # Record payment
    # ------------------------------------------------------------------
    payment_data: dict = {
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "amount": str(amount_received),
        "currency": currency,
        "base_amount": str(amount_received),  # FX conversion deferred to fx_refresh_worker
    }
    if payment_intent_id:
        payment_data["stripe_payment_intent_id"] = payment_intent_id

    def _insert_payment() -> None:
        db.table("payments").insert(payment_data).execute()

    await asyncio.to_thread(_insert_payment)

    # ------------------------------------------------------------------
    # Mark invoice as paid + back-link the invoiced time entries.
    # The invoice-create path already stamps invoice_line.time_entry_id, but
    # time_entries.invoice_id / billing_status were never updated — the
    # "what's still unbilled?" view kept returning already-billed rows.
    # ------------------------------------------------------------------
    paid_at_iso = datetime.datetime.now(datetime.UTC).isoformat()

    def _mark_paid() -> None:
        db.table("invoices").update(
            {"status": "paid", "paid_at": paid_at_iso}
        ).eq("id", invoice_id).execute()

    await asyncio.to_thread(_mark_paid)

    def _backlink_time_entries() -> None:
        line_rows = (
            db.table("invoice_lines")
            .select("time_entry_id")
            .eq("invoice_id", invoice_id)
            .execute()
            .data
            or []
        )
        te_ids = [r["time_entry_id"] for r in line_rows if r.get("time_entry_id")]
        if te_ids:
            (
                db.table("time_entries")
                .update({"invoice_id": invoice_id, "billing_status": "billed"})
                .in_("id", te_ids)
                .eq("tenant_id", tenant_id)
                .execute()
            )

    await asyncio.to_thread(_backlink_time_entries)

    # ------------------------------------------------------------------
    # Post journal: DR 1100 Bank / CR 1200 AR
    # ------------------------------------------------------------------
    def _get_accounts() -> dict[str, str]:
        result = (
            db.table("accounts")
            .select("id, code")
            .eq("tenant_id", tenant_id)
            .in_("code", ["1100", "1200"])
            .execute()
        )
        return {r["code"]: r["id"] for r in (result.data or [])}

    acct_map = await asyncio.to_thread(_get_accounts)

    invoice_number = invoice.get("invoice_number", invoice_id[:8])
    journal_lines = [
        JournalLineSpec(
            direction="DR",
            account_code="1100",
            amount=amount_received,
            description=f"Payment received for invoice {invoice_number}",
            account_id=acct_map.get("1100"),
            currency=currency,
        ),
        JournalLineSpec(
            direction="CR",
            account_code="1200",
            amount=amount_received,
            description=f"Payment received for invoice {invoice_number}",
            account_id=acct_map.get("1200"),
            currency=currency,
        ),
    ]

    # journal_entries.created_by is a UUID NOT NULL — the previous literal
    # "system" string raised `invalid input syntax for type uuid: "system"` at
    # insert time, the webhook caught it, and silently dropped the offsetting
    # journal. Payments came in, AR never cleared, Bank never grew. Fall back
    # to a tenant_user UUID so the post lands. (Future: dedicated system actor.)
    def _system_actor() -> str | None:
        result = (
            db.table("tenant_users")
            .select("user_id")
            .eq("tenant_id", tenant_id)
            .order("created_at")
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["user_id"]
        return None

    actor_uuid = await asyncio.to_thread(_system_actor)
    if actor_uuid is None:
        logger.error(
            "No tenant_users actor found — cannot post payment journal; payment row exists",
            extra={"invoice_id": invoice_id, "tenant_id": tenant_id},
        )
        return

    try:
        post_journal(
            db=db,
            tenant_id=tenant_id,
            created_by=actor_uuid,
            description=f"Payment received for invoice {invoice_number}",
            entry_date=datetime.date.today().isoformat(),
            reference_type="payment",
            # reference_id is a UUID column. payment_intent_id is a Stripe id
            # (pi_xxx) — would raise "invalid input syntax for type uuid" and
            # silently drop the offsetting journal again. Always use the
            # invoice UUID; the link to the Stripe payment_intent is preserved
            # on the payments.stripe_payment_intent_id column.
            reference_id=invoice_id,
            lines=journal_lines,
        )
    except Exception:
        # Log but do not fail the webhook — the payment is already recorded.
        # The accounting team can post a correcting entry manually.
        logger.error(
            "Failed to post payment journal — payment recorded, journal skipped",
            exc_info=True,
            extra={
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "payment_intent_id": payment_intent_id,
            },
        )

    # Post FX gain/loss journal if this was a cross-currency payment (#191)
    try:
        await post_fx_gain_loss_if_needed(
            db=db,
            tenant_id=tenant_id,
            invoice=invoice,
            payment_amount=amount_received,
            payment_currency=currency,
        )
    except Exception:
        logger.error(
            "Failed to post FX gain/loss journal — payment journal already posted",
            exc_info=True,
            extra={"invoice_id": invoice_id, "tenant_id": tenant_id},
        )

    logger.info(
        "Payment recorded from checkout.session.completed",
        extra={
            "invoice_id": invoice_id,
            "tenant_id": tenant_id,
            "amount": str(amount_received),
            "currency": currency,
            "event_id": event.id,
        },
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
