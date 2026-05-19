"""Auth router — signup and authentication endpoints.

POST /api/v1/auth/signup  — create Supabase user, tenant, Stripe customer,
                            return SetupIntent client_secret.

The signup flow is idempotent on email: if a Supabase user already exists for
the email we look up their tenant and issue a fresh SetupIntent rather than
returning an error, supporting browser-refresh / retry scenarios gracefully.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import get_service_role_client
from app.core.stripe_deps import get_stripe_service
from app.domain.exceptions import BillingError
from app.models.auth import SignupRequest, SignupResponse
from app.repositories.tenant_repo import TenantRepository
from app.services.billing.stripe_service import StripeService, country_to_currency
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tenant signup — create user, tenant, Stripe customer, return SetupIntent",
)
async def signup(
    payload: SignupRequest,
    db: Client = Depends(get_service_role_client),  # noqa: B008
    stripe_svc: StripeService = Depends(get_stripe_service),  # noqa: B008
) -> SignupResponse:
    """Onboarding Step 1: create the Supabase user + tenant + Stripe customer.

    Returns the Stripe SetupIntent ``client_secret`` so the frontend can
    render the Stripe.js card element.  The subscription is created in a
    separate call (``POST /api/v1/billing/start-trial``) after the user
    confirms the card.

    Idempotent on email: if the Supabase user already exists (e.g. browser
    refresh mid-signup), we look up the existing tenant and issue a fresh
    SetupIntent instead of failing.
    """
    tenant_repo = TenantRepository(db)
    base_currency = country_to_currency(payload.country)

    # ------------------------------------------------------------------
    # 1. Create Supabase Auth user (or detect existing)
    # ------------------------------------------------------------------
    auth_response = db.auth.sign_up(
        {
            "email": payload.email,
            "password": payload.password,
        }
    )

    # Supabase returns a user even on duplicate if email confirmation is off.
    # Distinguish "new" vs "existing" by checking whether identities is empty
    # (duplicate) or populated (new user).
    user = auth_response.user
    is_new_user = bool(user and user.identities)

    if not user:
        logger.warning(
            "Signup returned no user — possible rate limit or config issue",
            extra={"email_domain": payload.email.split("@")[-1]},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable. Please try again.",
        )

    user_id: str = user.id

    # ------------------------------------------------------------------
    # 2. Idempotency: if user already exists, look up their tenant
    # ------------------------------------------------------------------
    tenant_id: str | None = None
    stripe_customer_id: str | None = None

    if not is_new_user:
        # User already registered — look up existing tenant
        existing_tenant = await tenant_repo.get_by_user_email(payload.email)
        if existing_tenant:
            tenant_id = existing_tenant["id"]
            stripe_customer_id = existing_tenant.get("stripe_customer_id")
            logger.info(
                "Existing user re-requesting signup; re-issuing SetupIntent",
                extra={"tenant_id": tenant_id},
            )

    # ------------------------------------------------------------------
    # 3. Create tenant row (new user path)
    # ------------------------------------------------------------------
    if tenant_id is None:
        tenant_id = str(uuid.uuid4())
        slug = _slugify(payload.tenant_name)

        try:
            await tenant_repo.create_tenant(
                {
                    "id": tenant_id,
                    "name": payload.tenant_name,
                    "slug": slug,
                    "base_currency": base_currency,
                    "country": payload.country,
                    "plan_tier": payload.plan_tier,
                    "status": "provisioning",
                    "stripe_subscription_status": "incomplete",
                }
            )
        except Exception as exc:
            logger.error(
                "Failed to create tenant",
                exc_info=True,
                extra={"tenant_id": tenant_id},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to provision tenant. Please try again.",
            ) from exc

        # 3b. Create tenant_users row (owner)
        try:
            await tenant_repo.create_tenant_user(
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "role": "owner",
                }
            )
        except Exception as exc:
            logger.error(
                "Failed to create tenant_users row",
                exc_info=True,
                extra={"tenant_id": tenant_id, "user_id": user_id},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set up user permissions. Please contact support.",
            ) from exc

    # ------------------------------------------------------------------
    # 4. Create Stripe customer (if not already created)
    # ------------------------------------------------------------------
    if not stripe_customer_id:
        try:
            stripe_customer_id = await stripe_svc.create_customer(
                email=payload.email,
                tenant_id=tenant_id,
                tenant_name=payload.tenant_name,
            )
        except BillingError as exc:
            logger.error(
                "Stripe customer creation failed during signup",
                extra={"tenant_id": tenant_id, "billing_code": exc.code},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not set up billing. Please try again.",
            ) from exc

        # Persist stripe_customer_id on the tenant row
        try:
            await tenant_repo.update_tenant(
                tenant_id,
                {"stripe_customer_id": stripe_customer_id},
            )
        except Exception:
            # Non-fatal: we have the customer_id in memory; we can still proceed.
            logger.error(
                "Failed to persist stripe_customer_id on tenant",
                exc_info=True,
                extra={"tenant_id": tenant_id},
            )

    # ------------------------------------------------------------------
    # 5. Create Stripe SetupIntent and return client_secret
    # ------------------------------------------------------------------
    try:
        setup_intent = await stripe_svc.create_setup_intent(stripe_customer_id)
    except BillingError as exc:
        logger.error(
            "SetupIntent creation failed",
            extra={"tenant_id": tenant_id, "billing_code": exc.code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not initiate card setup. Please try again.",
        ) from exc

    logger.info(
        "Signup complete — SetupIntent issued",
        extra={"tenant_id": tenant_id},
    )
    return SignupResponse(
        tenant_id=tenant_id,
        stripe_setup_intent_client_secret=setup_intent["client_secret"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    """Convert a tenant name to a URL-safe slug."""
    import re

    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    # Ensure uniqueness suffix for DB uniqueness constraint
    return f"{slug}-{uuid.uuid4().hex[:6]}"
