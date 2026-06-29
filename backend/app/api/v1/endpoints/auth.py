"""Auth router — signup and authentication endpoints.

POST /api/v1/auth/signup  — create Supabase user, tenant, Stripe customer,
                            return SetupIntent client_secret.

The signup flow is idempotent on email: if a Supabase user already exists for
the email we look up their tenant and issue a fresh SetupIntent rather than
returning an error, supporting browser-refresh / retry scenarios gracefully.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from supabase_auth.errors import AuthApiError, AuthWeakPasswordError

from app.core.db import get_service_role_client
from app.core.stripe_deps import get_stripe_service
from app.domain.exceptions import BillingError
from app.models.auth import SignupRequest, SignupResponse
from app.repositories.tenant_repo import TenantRepository
from app.services.billing.stripe_service import StripeService, country_to_currency
from app.services.localization_service import get_market_profile
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Post-signup visibility confirm (bug #132)
# ---------------------------------------------------------------------------
#
# After the signup endpoint inserts a tenant_users row and returns 201, the
# Angular frontend immediately fires an authenticated API call.  On the
# Supabase PostgREST layer (connection pooling, possible read-replica lag)
# there is a ~50-200 ms window where the newly inserted row is not yet
# visible to a fresh connection.  The first request therefore lands inside
# that window and the membership check in get_tenant_id returns zero rows,
# raising 404 "Tenant not found".
#
# Fix: before returning 201 from signup, do one extra read-back via the
# service-role client to confirm the row is visible.  We retry up to 3 times
# with 150 ms spacing (total budget ≤ 450 ms, negligible for a one-time
# signup flow).  This keeps the retry logic off the hot path (every other
# authenticated request goes through _is_active_member once, no retry).

async def _confirm_tenant_user_visible(
    db: Client,
    *,
    user_id: str,
    tenant_id: str,
    retries: int = 3,
    delay: float = 0.15,
) -> bool:
    """Block until the tenant_users row is visible, or exhaust retries.

    Uses asyncio.to_thread so the supabase-py sync client does not block the
    event loop during the wait periods.
    """

    def _read() -> bool:
        result = (
            db.table("tenant_users")
            .select("id")
            .eq("user_id", user_id)
            .eq("tenant_id", tenant_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return bool(result.data)

    for attempt in range(retries):
        visible = await asyncio.to_thread(_read)
        if visible:
            return True
        if attempt < retries - 1:
            logger.debug(
                "tenant_users row not yet visible — retrying",
                extra={"attempt": attempt + 1, "user_id": user_id, "tenant_id": tenant_id},
            )
            await asyncio.sleep(delay)
    return False


# ---------------------------------------------------------------------------
# AuthApiError → HTTPException mapping (bug #97)
# ---------------------------------------------------------------------------
#
# Supabase's gotrue SDK raises ``AuthApiError`` for any 4xx response from the
# auth backend (invalid email, weak password, rate-limit, etc).  Letting it
# bubble up surfaces as HTTP 500 with a stack trace, which is both a poor UX
# and an SLO violation on a public endpoint.  ``_auth_error_to_http`` maps the
# SDK exception to a sanitised :class:`fastapi.HTTPException` we can re-raise.
#
# Mapping precedence is by SDK ``code`` field first, then a substring fallback
# on the human-readable message (older Supabase responses omit ``code``).  The
# detail body is rewritten in user-facing English — we never leak the vendor
# name or the raw SDK error code.

_CODE_TO_STATUS: dict[str, int] = {
    # 409 — conflict (already-registered email or identity)
    "user_already_exists": 409,
    "email_exists": 409,
    "phone_exists": 409,
    "identity_already_exists": 409,
    "conflict": 409,
    # 422 — validation (bad input the caller can fix)
    "weak_password": 422,
    "validation_failed": 422,
    "email_address_invalid": 422,
    "email_address_not_authorized": 422,
    "bad_json": 400,  # malformed payload — caller bug, plain 400
    # 429 — rate limited
    "over_request_rate_limit": 429,
    "over_email_send_rate_limit": 429,
    "over_sms_send_rate_limit": 429,
    # 503 — config disabled (admin must fix)
    "signup_disabled": 503,
    "email_provider_disabled": 503,
    "phone_provider_disabled": 503,
}

_FRIENDLY_DETAIL: dict[int, str] = {
    409: "Email already registered. Try signing in instead.",
    422: "Invalid signup details. Check your email address and password.",
    429: "Too many signup attempts. Please wait a moment and try again.",
    503: "Signup is temporarily unavailable. Please try again later.",
    400: "Could not complete signup. Please check your details and try again.",
}


def _auth_error_to_http(exc: AuthApiError) -> HTTPException:
    """Translate a Supabase ``AuthApiError`` into a sanitised HTTPException.

    Args:
        exc: the SDK exception (covers both :class:`AuthApiError` and its
             :class:`AuthWeakPasswordError` subclass).

    Returns:
        An :class:`HTTPException` with a 4xx/5xx status code and a user-facing
        ``detail`` string.  Never includes the vendor name, the raw error code,
        or any stack-trace fragment.
    """
    code = getattr(exc, "code", None)
    raw_message = (getattr(exc, "message", None) or str(exc) or "").strip()
    lower = raw_message.lower()

    # 1. Map by structured ``code`` field if present.
    http_status: int | None = _CODE_TO_STATUS.get(code) if code else None

    # 2. AuthWeakPasswordError is the only subclass we care about — treat as 422.
    if http_status is None and isinstance(exc, AuthWeakPasswordError):
        http_status = 422

    # 3. Substring fallback for SDK versions that omit ``code``.
    if http_status is None:
        if "already registered" in lower or "already exists" in lower:
            http_status = 409
        elif "rate limit" in lower or "too many" in lower:
            http_status = 429
        elif "invalid" in lower and ("email" in lower or "password" in lower):
            http_status = 422
        elif "weak" in lower and "password" in lower:
            http_status = 422
        elif "disabled" in lower:
            http_status = 503

    if http_status is None:
        http_status = 400

    # Choose detail — prefer a slightly personalised message for the common
    # 409/422 cases, otherwise the canned friendly string. NEVER include the
    # vendor name or the raw SDK code.
    detail = _FRIENDLY_DETAIL[http_status]
    if http_status == 422 and ("password" in lower and "weak" in lower):
        detail = "Password is too weak. Use at least 8 characters with a mix of letters, numbers, and symbols."
    elif http_status == 422 and "email" in lower and "invalid" in lower:
        detail = "Email address is invalid. Please check the spelling and try again."

    headers: dict[str, str] | None = None
    if http_status == 429:
        # Supabase doesn't surface a precise reset time via the SDK exception,
        # so we send a conservative default. The client must back off.
        headers = {"Retry-After": "60"}

    # Log the original (sanitised) error server-side for observability —
    # email domain only, no PII, no message body that might include the email.
    logger.warning(
        "Supabase auth error translated to HTTP %s (code=%s)",
        http_status,
        code or "<none>",
    )

    return HTTPException(status_code=http_status, detail=detail, headers=headers)


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
    market_profile = get_market_profile(payload.country)
    base_currency = (
        market_profile.base_currency if market_profile else country_to_currency(payload.country)
    )
    tenant_country = market_profile.country if market_profile else payload.country
    tenant_timezone = market_profile.timezone if market_profile else "UTC"
    tenant_locale = market_profile.locale if market_profile else "en-US"

    # ------------------------------------------------------------------
    # 1. Create Supabase Auth user (or detect existing)
    #
    # Use the admin API (`auth.admin.create_user`) rather than `auth.sign_up`
    # for a critical reason: `sign_up` mutates the supabase-py client's
    # internal session, replacing the service-role JWT with the new user's
    # authenticated JWT. Subsequent `db.table(...)` calls then run as that
    # authenticated user, which is denied by RLS on the `tenants` table
    # (migration 0015 deny_direct_tenant_access RESTRICTIVE policy) — see
    # bug #121. `admin.create_user` is a service-role endpoint that does
    # NOT mutate the client session, so the same `db` instance keeps
    # service-role privileges for the subsequent tenant insert.
    # ------------------------------------------------------------------
    try:
        admin_response = db.auth.admin.create_user(
            {
                "email": payload.email,
                "password": payload.password,
                "email_confirm": True,  # skip the verification email (Founder disabled it project-wide too — #116)
            }
        )
    except AuthApiError as exc:
        # Bug #97 — translate to a 4xx HTTPException so we never return 500 on
        # a signup-rejection path (invalid email, weak password, rate limit,
        # already-registered, etc).
        raise _auth_error_to_http(exc) from exc

    # admin.create_user always returns the user (or raises on duplicate).
    # We treat a successful return as "new user" — the duplicate path is now
    # handled by the AuthApiError branch above (Supabase raises
    # `email_exists` on duplicate). Idempotency for browser-refresh mid-signup
    # is preserved by the existing-tenant lookup further down.
    user = admin_response.user if hasattr(admin_response, "user") else admin_response
    is_new_user = True
    if not user:
        is_new_user = False

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
                    "country": tenant_country,
                    "timezone": tenant_timezone,
                    "locale": tenant_locale,
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
                    "email": str(payload.email).lower(),
                    "display_name": payload.email.split("@")[0],
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

        # 3c. Confirm tenant_users row is visible before returning 201.
        #
        # Bug #132: PostgREST connection-pool / read-replica lag creates a
        # ~50-200 ms window where the just-inserted row is invisible to a fresh
        # connection.  The Angular frontend fires its first authenticated API
        # call immediately after the signup 201, landing inside this window and
        # getting 404 "Tenant not found" from get_tenant_id.
        #
        # Chosen approach: signup-side confirm (single extra round-trip at
        # signup time only) rather than retry in the get_tenant_id hot path.
        # This keeps every other authenticated request at zero extra cost.
        visible = await _confirm_tenant_user_visible(
            db,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        if not visible:
            logger.error(
                "tenant_users row not visible after retries — possible DB replication lag",
                extra={"tenant_id": tenant_id, "user_id": user_id},
            )
            # Non-fatal: we raise 500 so the frontend retries the whole signup
            # rather than silently returning 201 that will immediately 404.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Provisioning delay — please retry in a moment.",
            )

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
