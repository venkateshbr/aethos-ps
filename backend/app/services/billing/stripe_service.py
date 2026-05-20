"""Stripe service — wraps the Stripe Python SDK for all SaaS billing operations.

All Stripe SDK calls are synchronous (stripe v15 SDK is synchronous by default;
async wrappers are achieved by running in a thread pool via anyio.to_thread if
needed, but for the initial implementation the service is called from async
FastAPI handlers via await with anyio.to_thread.run_sync or directly since
Stripe calls are network-bound and short).

Design decisions:
- Never commits real Stripe keys in code — always reads from Settings.
- All stripe.StripeError exceptions are caught and re-raised as BillingError
  so the service layer boundary is clean.
- Webhook signature verification raises ValueError (not BillingError) so the
  webhook router can return HTTP 400 without leaking billing internals.
- We never compute monetary amounts in Python — Stripe Prices store the amount;
  we only pass Price IDs. This satisfies the Money Gate.
"""

from __future__ import annotations

import logging

import stripe

from app.core.config import Settings
from app.domain.exceptions import BillingError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Country → base currency mapping (PLAN §8.5)
# ---------------------------------------------------------------------------

_COUNTRY_CURRENCY: dict[str, str] = {
    "US": "USD",
    "GB": "GBP",
    "SG": "SGD",
    "IN": "INR",
    "AU": "AUD",
}


def country_to_currency(country: str) -> str:
    """Return the ISO 4217 currency code for a 2-letter country code.

    Defaults to USD for any country not in the 5 launch markets.
    """
    return _COUNTRY_CURRENCY.get(country.upper(), "USD")


# ---------------------------------------------------------------------------
# StripeService
# ---------------------------------------------------------------------------


class StripeService:
    """Wraps the Stripe Python SDK for Aethos SaaS billing.

    Usage
    -----
    Instantiate once per request (or as a singleton) via dependency injection:

        stripe_svc = StripeService(settings)
        customer_id = await stripe_svc.create_customer(email, tenant_id, name)
    """

    def __init__(self, settings: Settings) -> None:
        stripe.api_key = settings.stripe_secret_key
        self.webhook_secret = settings.stripe_webhook_secret
        self._settings = settings

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------

    async def create_customer(
        self,
        email: str,
        tenant_id: str,
        tenant_name: str,
    ) -> str:
        """Create a Stripe Customer and return the ``customer_id``.

        Metadata stores ``tenant_id`` so webhook handlers can look up the
        tenant without an extra DB query.
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=tenant_name,
                metadata={"tenant_id": tenant_id},
            )
        except stripe.StripeError as exc:
            logger.error(
                "Stripe customer creation failed",
                extra={"stripe_code": exc.code, "tenant_id": tenant_id},
            )
            raise BillingError(
                f"Could not create Stripe customer: {exc.user_message or str(exc)}",
                code=exc.code or "stripe_error",
            ) from exc
        logger.info(
            "Stripe customer created",
            extra={"stripe_customer_id": customer.id, "tenant_id": tenant_id},
        )
        return customer.id

    # ------------------------------------------------------------------
    # Setup Intent — card capture without immediate charge
    # ------------------------------------------------------------------

    async def create_setup_intent(self, customer_id: str) -> dict:
        """Create a Stripe SetupIntent for card capture.

        Returns ``{client_secret, setup_intent_id}``.  The ``client_secret``
        is passed to the frontend Stripe.js to render the card element.
        """
        try:
            intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=["card"],
                usage="off_session",  # card will be charged for recurring subs
            )
        except stripe.StripeError as exc:
            logger.error(
                "Stripe SetupIntent creation failed",
                extra={"stripe_customer_id": customer_id, "stripe_code": exc.code},
            )
            raise BillingError(
                f"Could not create SetupIntent: {exc.user_message or str(exc)}",
                code=exc.code or "stripe_error",
            ) from exc
        return {
            "client_secret": intent.client_secret,
            "setup_intent_id": intent.id,
        }

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_period_days: int = 14,
    ) -> dict:
        """Create a Stripe Subscription with a trial period.

        Returns ``{subscription_id, status, trial_end}`` where ``trial_end``
        is a Unix timestamp (int) or None.
        """
        try:
            sub = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                trial_period_days=trial_period_days,
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice.payment_intent"],
            )
        except stripe.StripeError as exc:
            logger.error(
                "Stripe subscription creation failed",
                extra={"stripe_customer_id": customer_id, "stripe_code": exc.code},
            )
            raise BillingError(
                f"Could not create subscription: {exc.user_message or str(exc)}",
                code=exc.code or "stripe_error",
            ) from exc
        logger.info(
            "Stripe subscription created",
            extra={
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": sub.id,
                "status": sub.status,
            },
        )
        return {
            "subscription_id": sub.id,
            "status": sub.status,
            "trial_end": sub.trial_end,
        }

    # ------------------------------------------------------------------
    # Attach payment method to customer
    # ------------------------------------------------------------------

    async def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str,
    ) -> None:
        """Attach a confirmed SetupIntent payment method to the customer and
        set it as the default for future invoices.
        """
        try:
            pm = stripe.PaymentMethod.retrieve(payment_method_id)
            pm.attach(customer=customer_id)
            stripe.Customer.modify(
                customer_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )
        except stripe.StripeError as exc:
            logger.error(
                "Failed to attach payment method",
                extra={
                    "stripe_customer_id": customer_id,
                    "stripe_code": exc.code,
                },
            )
            raise BillingError(
                f"Could not attach payment method: {exc.user_message or str(exc)}",
                code=exc.code or "stripe_error",
            ) from exc

    # ------------------------------------------------------------------
    # Retrieve SetupIntent
    # ------------------------------------------------------------------

    async def retrieve_setup_intent(self, setup_intent_id: str) -> dict:
        """Retrieve a SetupIntent and return its status and payment method."""
        try:
            intent = stripe.SetupIntent.retrieve(setup_intent_id)
        except stripe.StripeError as exc:
            raise BillingError(
                f"Could not retrieve SetupIntent: {exc.user_message or str(exc)}",
                code=exc.code or "stripe_error",
            ) from exc
        return {
            "status": intent.status,
            "payment_method": intent.payment_method,
        }

    # ------------------------------------------------------------------
    # Webhook
    # ------------------------------------------------------------------

    async def construct_webhook_event(
        self,
        payload: bytes,
        sig_header: str,
    ) -> stripe.Event:
        """Verify the Stripe webhook signature and parse the event.

        Raises ``ValueError`` on invalid signature so the webhook router can
        return HTTP 400 without any state change.  Never logs the raw payload
        (may contain PII / card data).
        """
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=self.webhook_secret,
            )
        except stripe.SignatureVerificationError as exc:
            logger.warning(
                "Stripe webhook signature verification failed",
                extra={"sig_header_prefix": sig_header[:20] if sig_header else ""},
            )
            raise ValueError("Invalid Stripe webhook signature") from exc
        except Exception as exc:
            logger.error("Stripe webhook parse error", exc_info=True)
            raise ValueError(f"Webhook parse error: {exc}") from exc
        return event

    # ------------------------------------------------------------------
    # Billing portal
    # ------------------------------------------------------------------

    async def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """Create a Stripe Customer Portal session and return the URL."""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
        except stripe.StripeError as exc:
            raise BillingError(
                f"Could not create billing portal session: {exc.user_message or str(exc)}",
                code=exc.code or "stripe_error",
            ) from exc
        return session.url

    # ------------------------------------------------------------------
    # Stripe Connect Standard — onboarding (issue #51)
    # ------------------------------------------------------------------

    async def create_connect_oauth_url(
        self,
        tenant_id: str,
        redirect_uri: str,
        country: str,
    ) -> str:
        """Return the Stripe Connect OAuth authorization URL.

        The ``state`` parameter is set to ``tenant_id`` so the return handler
        can look up the tenant without additional state storage.

        The ``redirect_uri`` must be registered in the Stripe dashboard under
        Connect → Settings → Redirects.

        Args:
            tenant_id: The tenant UUID — embedded as OAuth state parameter.
            redirect_uri: The callback URL Stripe will redirect to after auth.
            country: 2-letter ISO country code for pre-filling the onboarding form.

        Returns:
            Fully-formed OAuth authorization URL string.
        """
        from urllib.parse import urlencode

        params = {
            "response_type": "code",
            "client_id": self._settings.stripe_connect_client_id,
            "scope": "read_write",
            "redirect_uri": redirect_uri,
            "state": tenant_id,
            "stripe_user[country]": country,
        }
        base = "https://connect.stripe.com/oauth/authorize"
        return f"{base}?{urlencode(params)}"

    async def exchange_connect_code(self, code: str) -> dict:
        """Exchange the OAuth authorization code for a Stripe account ID.

        Args:
            code: The ``code`` query parameter from the OAuth callback.

        Returns:
            ``{"stripe_connect_account_id": str, "access_token": str}``

        Raises:
            BillingError: If the token exchange fails (invalid code, etc.).
        """
        try:
            response = stripe.OAuth.token(
                grant_type="authorization_code",
                code=code,
            )
        except stripe.StripeError as exc:
            logger.error(
                "Stripe Connect OAuth token exchange failed",
                extra={"stripe_code": getattr(exc, "code", "unknown")},
            )
            raise BillingError(
                f"Stripe Connect onboarding failed: {getattr(exc, 'user_message', None) or str(exc)}",
                code=getattr(exc, "code", None) or "stripe_error",
            ) from exc

        return {
            "stripe_connect_account_id": response.stripe_user_id,
            "access_token": response.access_token,
        }

    async def get_connect_account(self, connect_account_id: str) -> dict:
        """Retrieve Connect account details (charges_enabled, payouts_enabled).

        Args:
            connect_account_id: The Stripe ``acct_`` account ID.

        Returns:
            ``{"charges_enabled": bool, "payouts_enabled": bool}``
        """
        try:
            account = stripe.Account.retrieve(connect_account_id)
        except stripe.StripeError as exc:
            logger.error(
                "Failed to retrieve Stripe Connect account",
                extra={
                    "connect_account_id": connect_account_id,
                    "stripe_code": getattr(exc, "code", "unknown"),
                },
            )
            raise BillingError(
                f"Could not retrieve Connect account: {getattr(exc, 'user_message', None) or str(exc)}",
                code=getattr(exc, "code", None) or "stripe_error",
            ) from exc

        return {
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,
        }
