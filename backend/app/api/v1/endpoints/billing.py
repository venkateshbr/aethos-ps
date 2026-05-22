"""Billing router — subscription management and price catalogue endpoints.

POST /api/v1/billing/start-trial  — create Stripe subscription after card confirmed
GET  /api/v1/billing/prices        — return plan picker payload for the frontend
POST /api/v1/billing/portal        — create Stripe Customer Portal session URL
"""

from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.stripe_deps import get_stripe_service
from app.core.tenant import get_tenant_id
from app.domain.exceptions import BillingError
from app.models.auth import (
    BillingPortalRequest,
    BillingPortalResponse,
    PriceCatalogueResponse,
    PriceEntry,
    StartTrialRequest,
    StartTrialResponse,
)
from app.repositories.tenant_repo import TenantRepository
from app.services.billing.price_catalogue import currency_for_country, get_prices_for_currency
from app.services.billing.stripe_service import StripeService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/start-trial",
    response_model=StartTrialResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Stripe subscription after card is confirmed via Setup Intent",
)
async def start_trial(
    payload: StartTrialRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
    stripe_svc: StripeService = Depends(get_stripe_service),  # noqa: B008
) -> StartTrialResponse:
    """Onboarding Step 2: called after the frontend confirms the SetupIntent.

    1. Verify the SetupIntent succeeded and extract the confirmed payment method.
    2. Attach the payment method to the Stripe customer as default.
    3. Create the subscription with a 14-day trial.
    4. Update the tenant row with subscription ID and status.
    """
    tenant_repo = TenantRepository(db)

    # ------------------------------------------------------------------
    # 1. Verify the SetupIntent succeeded
    # ------------------------------------------------------------------
    try:
        intent_data = await stripe_svc.retrieve_setup_intent(payload.setup_intent_id)
    except BillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Setup Intent.",
        ) from exc

    if intent_data["status"] != "succeeded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Card setup not complete (status: {intent_data['status']}). "
            "Please complete the card setup before starting the trial.",
        )

    payment_method_id: str | None = intent_data.get("payment_method")
    if not payment_method_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No payment method found on Setup Intent.",
        )

    # ------------------------------------------------------------------
    # 2. Look up the tenant's Stripe customer ID
    # ------------------------------------------------------------------
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    stripe_customer_id: str | None = tenant.get("stripe_customer_id")
    if not stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing not yet set up for this tenant. Please complete signup.",
        )

    # ------------------------------------------------------------------
    # 3. Attach payment method to customer as default
    # ------------------------------------------------------------------
    try:
        await stripe_svc.attach_payment_method(payment_method_id, stripe_customer_id)
    except BillingError as exc:
        logger.error(
            "Failed to attach payment method",
            extra={"tenant_id": tenant_id, "billing_code": exc.code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not attach payment method. Please try again.",
        ) from exc

    # ------------------------------------------------------------------
    # 4. Create subscription with trial
    # ------------------------------------------------------------------
    try:
        sub_data = await stripe_svc.create_subscription(
            customer_id=stripe_customer_id,
            price_id=payload.price_id,
            trial_period_days=14,
        )
    except BillingError as exc:
        logger.error(
            "Subscription creation failed",
            extra={"tenant_id": tenant_id, "billing_code": exc.code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create subscription. Please try again.",
        ) from exc

    # ------------------------------------------------------------------
    # 5. Update tenant row
    # ------------------------------------------------------------------
    update_data: dict = {
        "stripe_subscription_id": sub_data["subscription_id"],
        "stripe_subscription_status": sub_data["status"],
        "status": "active",
    }
    if sub_data.get("trial_end"):
        update_data["trial_ends_at"] = datetime.datetime.fromtimestamp(
            sub_data["trial_end"], tz=datetime.UTC
        ).isoformat()

    try:
        await tenant_repo.update_tenant(tenant_id, update_data)
    except Exception:
        # Log and continue — subscription is created; DB update is secondary.
        logger.error(
            "Failed to persist subscription data on tenant",
            exc_info=True,
            extra={"tenant_id": tenant_id},
        )

    logger.info(
        "Trial subscription started",
        extra={
            "tenant_id": tenant_id,
            "stripe_subscription_id": sub_data["subscription_id"],
            "status": sub_data["status"],
        },
    )
    return StartTrialResponse(
        subscription_id=sub_data["subscription_id"],
        status=sub_data["status"],
        trial_ends_at=sub_data.get("trial_end"),
    )


@router.get(
    "/prices",
    response_model=PriceCatalogueResponse,
    summary="Return the Stripe Price IDs for the caller's tenant currency",
)
async def get_prices(
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> PriceCatalogueResponse:
    """Return the plan picker payload.

    Currency is derived from the tenant's ``country`` column.
    The frontend uses these Price IDs when creating the subscription.
    """
    tenant_repo = TenantRepository(db)
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    country: str = tenant.get("country", "US")
    currency = currency_for_country(country)
    plans_raw = get_prices_for_currency(currency)

    return PriceCatalogueResponse(
        currency=currency,
        plans=[PriceEntry(**p) for p in plans_raw],
    )


@router.post(
    "/portal",
    response_model=BillingPortalResponse,
    summary="Create a Stripe Customer Portal session URL",
)
async def billing_portal(
    payload: BillingPortalRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
    stripe_svc: StripeService = Depends(get_stripe_service),  # noqa: B008
) -> BillingPortalResponse:
    """Return a one-time Stripe Customer Portal URL for self-serve billing management.

    The URL expires after a short period (Stripe default: ~5 min).
    """
    tenant_repo = TenantRepository(db)
    tenant = await tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    stripe_customer_id = tenant.get("stripe_customer_id")
    if not stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing not yet set up for this tenant.",
        )

    try:
        url = await stripe_svc.create_billing_portal_session(
            customer_id=stripe_customer_id,
            return_url=payload.return_url,
        )
    except BillingError as exc:
        logger.error(
            "Failed to create billing portal session",
            extra={"tenant_id": tenant_id, "billing_code": exc.code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not open billing portal. Please try again.",
        ) from exc

    return BillingPortalResponse(url=url)


@router.get(
    "/subscription-status",
    summary="Return trial countdown and subscription status for the app shell badge",
)
def subscription_status(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
    _: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Returns trial countdown and subscription status for the app shell badge."""
    tenant = db.table("tenants").select(
        "trial_ends_at, stripe_subscription_status, plan_tier"
    ).eq("id", tenant_id).execute()
    if not tenant.data:
        return {"status": "unknown", "trial_ends_at": None, "plan_tier": "trial"}
    t = tenant.data[0]
    return {
        "status": t.get("stripe_subscription_status", "trialing"),
        "trial_ends_at": t.get("trial_ends_at"),
        "plan_tier": t.get("plan_tier", "trial"),
    }
