"""Unit tests for StripeService and related billing utilities.

All tests use unittest.mock to avoid real Stripe API calls.
No I/O, no network — these run in CI without any credentials.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
import stripe

from app.domain.exceptions import BillingError
from app.services.billing.stripe_service import StripeService, country_to_currency

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def settings_mock() -> MagicMock:
    """Mock Settings with placeholder Stripe keys."""
    mock = MagicMock()
    mock.stripe_secret_key = "sk_test_placeholder"
    mock.stripe_webhook_secret = "whsec_placeholder"
    return mock


@pytest.fixture
def stripe_svc(settings_mock: MagicMock) -> StripeService:
    """StripeService instance backed by mock settings."""
    return StripeService(settings_mock)


# ---------------------------------------------------------------------------
# country_to_currency
# ---------------------------------------------------------------------------


def test_country_to_currency_mapping() -> None:
    """All 5 launch markets map to the correct ISO 4217 currency."""
    assert country_to_currency("US") == "USD"
    assert country_to_currency("GB") == "GBP"
    assert country_to_currency("SG") == "SGD"
    assert country_to_currency("IN") == "INR"
    assert country_to_currency("AU") == "AUD"


def test_country_to_currency_default() -> None:
    """Unknown country defaults to USD."""
    assert country_to_currency("DE") == "USD"
    assert country_to_currency("JP") == "USD"
    assert country_to_currency("XX") == "USD"


def test_country_to_currency_case_insensitive() -> None:
    """Lowercase country codes are accepted."""
    assert country_to_currency("us") == "USD"
    assert country_to_currency("gb") == "GBP"


# ---------------------------------------------------------------------------
# construct_webhook_event — bad signature
# ---------------------------------------------------------------------------


def test_bad_webhook_signature_raises(stripe_svc: StripeService) -> None:
    """Invalid webhook signature must raise ValueError (not BillingError).

    The webhook router catches ValueError and returns HTTP 400.
    """
    with patch(
        "stripe.Webhook.construct_event",
        side_effect=stripe.SignatureVerificationError("bad sig", "bad-header"),
    ):
        with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
            asyncio.run(stripe_svc.construct_webhook_event(b"payload", "bad-sig"))


def test_valid_webhook_signature_returns_event(stripe_svc: StripeService) -> None:
    """Valid payload + signature returns a stripe.Event object."""
    fake_event = MagicMock(spec=stripe.Event)
    fake_event.id = "evt_test_123"
    fake_event.type = "customer.subscription.created"

    with patch("stripe.Webhook.construct_event", return_value=fake_event):
        result = asyncio.run(
            stripe_svc.construct_webhook_event(b'{"id":"evt_test_123"}', "t=123,v1=abc")
        )

    assert result.id == "evt_test_123"
    assert result.type == "customer.subscription.created"


# ---------------------------------------------------------------------------
# create_customer
# ---------------------------------------------------------------------------


def test_create_customer_returns_customer_id(stripe_svc: StripeService) -> None:
    """create_customer returns the Stripe customer ID string."""
    fake_customer = MagicMock()
    fake_customer.id = "cus_test_abc123"

    with patch("stripe.Customer.create", return_value=fake_customer):
        result = asyncio.run(
            stripe_svc.create_customer(
                email="alice@example.com",
                tenant_id="tenant-uuid-001",
                tenant_name="Alice Consulting",
            )
        )

    assert result == "cus_test_abc123"


def test_create_customer_stripe_error_raises_billing_error(stripe_svc: StripeService) -> None:
    """StripeError from customer creation is wrapped in BillingError."""
    stripe_err = stripe.StripeError("Network error")
    stripe_err.code = "api_error"

    with patch("stripe.Customer.create", side_effect=stripe_err):
        with pytest.raises(BillingError, match="Could not create Stripe customer"):
            asyncio.run(
                stripe_svc.create_customer(
                    email="alice@example.com",
                    tenant_id="tenant-uuid-001",
                    tenant_name="Alice Consulting",
                )
            )


# ---------------------------------------------------------------------------
# create_setup_intent
# ---------------------------------------------------------------------------


def test_create_setup_intent_returns_client_secret(stripe_svc: StripeService) -> None:
    """create_setup_intent returns dict with client_secret and setup_intent_id."""
    fake_intent = MagicMock()
    fake_intent.id = "seti_test_001"
    fake_intent.client_secret = "seti_test_001_secret_xyz"

    with patch("stripe.SetupIntent.create", return_value=fake_intent):
        result = asyncio.run(stripe_svc.create_setup_intent("cus_test_abc"))

    assert result["setup_intent_id"] == "seti_test_001"
    assert result["client_secret"] == "seti_test_001_secret_xyz"


def test_create_setup_intent_stripe_error_raises_billing_error(
    stripe_svc: StripeService,
) -> None:
    """StripeError from SetupIntent creation is wrapped in BillingError."""
    err = stripe.StripeError("Card error")
    err.code = "card_error"

    with patch("stripe.SetupIntent.create", side_effect=err):
        with pytest.raises(BillingError):
            asyncio.run(stripe_svc.create_setup_intent("cus_test_abc"))


# ---------------------------------------------------------------------------
# create_subscription
# ---------------------------------------------------------------------------


def test_create_subscription_returns_subscription_data(stripe_svc: StripeService) -> None:
    """create_subscription returns dict with subscription_id, status, trial_end."""
    fake_sub = MagicMock()
    fake_sub.id = "sub_test_001"
    fake_sub.status = "trialing"
    fake_sub.trial_end = 1_718_000_000  # Unix timestamp

    with patch("stripe.Subscription.create", return_value=fake_sub):
        result = asyncio.run(
            stripe_svc.create_subscription(
                customer_id="cus_test_abc",
                price_id="price_starter_monthly_usd",
                trial_period_days=14,
            )
        )

    assert result["subscription_id"] == "sub_test_001"
    assert result["status"] == "trialing"
    assert result["trial_end"] == 1_718_000_000


def test_create_subscription_stripe_error_raises_billing_error(
    stripe_svc: StripeService,
) -> None:
    """StripeError during subscription creation is wrapped in BillingError."""
    err = stripe.StripeError("Subscription error")
    err.code = "subscription_error"

    with patch("stripe.Subscription.create", side_effect=err):
        with pytest.raises(BillingError, match="Could not create subscription"):
            asyncio.run(
                stripe_svc.create_subscription(
                    customer_id="cus_test_abc",
                    price_id="price_starter_monthly_usd",
                )
            )


# ---------------------------------------------------------------------------
# create_billing_portal_session
# ---------------------------------------------------------------------------


def test_create_billing_portal_session_returns_url(stripe_svc: StripeService) -> None:
    """create_billing_portal_session returns the portal URL string."""
    fake_session = MagicMock()
    fake_session.url = "https://billing.stripe.com/session/test_portal_abc"

    with patch("stripe.billing_portal.Session.create", return_value=fake_session):
        url = asyncio.run(
            stripe_svc.create_billing_portal_session(
                customer_id="cus_test_abc",
                return_url="http://localhost:4201/settings/billing",
            )
        )

    assert url == "https://billing.stripe.com/session/test_portal_abc"


# ---------------------------------------------------------------------------
# retrieve_setup_intent
# ---------------------------------------------------------------------------


def test_retrieve_setup_intent_succeeded(stripe_svc: StripeService) -> None:
    """retrieve_setup_intent returns status and payment_method."""
    fake_intent = MagicMock()
    fake_intent.status = "succeeded"
    fake_intent.payment_method = "pm_test_123"

    with patch("stripe.SetupIntent.retrieve", return_value=fake_intent):
        result = asyncio.run(stripe_svc.retrieve_setup_intent("seti_test_001"))

    assert result["status"] == "succeeded"
    assert result["payment_method"] == "pm_test_123"


# ---------------------------------------------------------------------------
# Price catalogue
# ---------------------------------------------------------------------------


def test_price_catalogue_all_tiers_all_currencies() -> None:
    """Price catalogue covers all 3 tiers x 2 intervals x 5 currencies = 30 entries."""
    from app.services.billing.price_catalogue import PRICE_IDS

    tiers = ("starter", "growth", "pro")
    intervals = ("monthly", "annual")
    currencies = ("USD", "GBP", "SGD", "INR", "AUD")

    for tier in tiers:
        for interval in intervals:
            for currency in currencies:
                assert tier in PRICE_IDS, f"Missing tier: {tier}"
                assert interval in PRICE_IDS[tier], f"Missing interval: {tier}/{interval}"
                assert currency in PRICE_IDS[tier][interval], (
                    f"Missing entry: {tier}/{interval}/{currency}"
                )
                # Value must be a non-empty string
                val = PRICE_IDS[tier][interval][currency]
                assert isinstance(val, str) and val, (
                    f"Empty price_id: {tier}/{interval}/{currency}"
                )


def test_get_price_id_known_combination() -> None:
    """get_price_id returns the configured price_id for a known combination."""
    from app.services.billing.price_catalogue import get_price_id

    result = get_price_id("starter", "monthly", "USD")
    assert result is not None
    assert isinstance(result, str)


def test_get_price_id_unknown_combination_returns_none() -> None:
    """get_price_id returns None for unknown tier/interval/currency."""
    from app.services.billing.price_catalogue import get_price_id

    assert get_price_id("enterprise", "monthly", "USD") is None
    assert get_price_id("starter", "weekly", "USD") is None
    assert get_price_id("starter", "monthly", "EUR") is None


def test_get_prices_for_currency_returns_all_tiers() -> None:
    """get_prices_for_currency returns one entry per plan tier."""
    from app.services.billing.price_catalogue import get_prices_for_currency

    plans = get_prices_for_currency("GBP")
    assert len(plans) == 3
    tiers = {p["tier"] for p in plans}
    assert tiers == {"starter", "growth", "pro"}
    for plan in plans:
        assert "monthly_id" in plan
        assert "annual_id" in plan
