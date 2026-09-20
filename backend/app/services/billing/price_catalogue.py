"""Price catalogue — in-memory mapping of plan x interval x currency -> Stripe Price ID.

The founder creates the real Stripe Prices in the Stripe dashboard for both
test mode (sandbox) and live mode and places the IDs in .env.  This module
reads them from Settings at import time.

Prices are NEVER computed in Python.  We pass Price IDs to Stripe; Stripe
stores the amount and handles tax calculation (Stripe Tax).

Structure
---------
PRICE_IDS[tier][interval][currency] → stripe_price_id (str)

tiers:   "starter" | "growth" | "pro"
interval: "monthly" | "annual"
currency: "USD" | "GBP" | "SGD" | "INR" | "AUD"

Suggested amounts (from PLAN §8.6) — set in the Stripe dashboard:

| Plan    | USD   | GBP   | SGD    | INR     | AUD    |
|---------|-------|-------|--------|---------|--------|
| Starter | $29   | £25   | S$39   | ₹2,499  | A$45   |
| Growth  | $79   | £69   | S$109  | ₹6,999  | A$119  |
| Pro     | $199  | £179  | S$279  | ₹17,999 | A$299  |

Annual prices are at a discounted monthly rate (typically 2 months free).
"""

from __future__ import annotations

from app.core.config import settings
from app.services.billing.stripe_service import country_to_currency


def _build_catalogue() -> dict[str, dict[str, dict[str, str]]]:
    """Build the full price catalogue from Settings at startup."""
    return {
        "starter": {
            "monthly": {
                "USD": settings.stripe_price_starter_monthly_usd,
                "GBP": settings.stripe_price_starter_monthly_gbp,
                "SGD": settings.stripe_price_starter_monthly_sgd,
                "INR": settings.stripe_price_starter_monthly_inr,
                "AUD": settings.stripe_price_starter_monthly_aud,
            },
            "annual": {
                "USD": settings.stripe_price_starter_annual_usd,
                "GBP": settings.stripe_price_starter_annual_gbp,
                "SGD": settings.stripe_price_starter_annual_sgd,
                "INR": settings.stripe_price_starter_annual_inr,
                "AUD": settings.stripe_price_starter_annual_aud,
            },
        },
        "growth": {
            "monthly": {
                "USD": settings.stripe_price_growth_monthly_usd,
                "GBP": settings.stripe_price_growth_monthly_gbp,
                "SGD": settings.stripe_price_growth_monthly_sgd,
                "INR": settings.stripe_price_growth_monthly_inr,
                "AUD": settings.stripe_price_growth_monthly_aud,
            },
            "annual": {
                "USD": settings.stripe_price_growth_annual_usd,
                "GBP": settings.stripe_price_growth_annual_gbp,
                "SGD": settings.stripe_price_growth_annual_sgd,
                "INR": settings.stripe_price_growth_annual_inr,
                "AUD": settings.stripe_price_growth_annual_aud,
            },
        },
        "pro": {
            "monthly": {
                "USD": settings.stripe_price_pro_monthly_usd,
                "GBP": settings.stripe_price_pro_monthly_gbp,
                "SGD": settings.stripe_price_pro_monthly_sgd,
                "INR": settings.stripe_price_pro_monthly_inr,
                "AUD": settings.stripe_price_pro_monthly_aud,
            },
            "annual": {
                "USD": settings.stripe_price_pro_annual_usd,
                "GBP": settings.stripe_price_pro_annual_gbp,
                "SGD": settings.stripe_price_pro_annual_sgd,
                "INR": settings.stripe_price_pro_annual_inr,
                "AUD": settings.stripe_price_pro_annual_aud,
            },
        },
    }


# Module-level singleton built at import time.
PRICE_IDS: dict[str, dict[str, dict[str, str]]] = _build_catalogue()


def get_price_id(tier: str, interval: str, currency: str) -> str | None:
    """Return the Stripe Price ID for the given tier, interval, and currency.

    Returns None when the combination is not found (caller should 422).
    """
    return PRICE_IDS.get(tier, {}).get(interval, {}).get(currency.upper())


def tier_for_price_id(price_id: str, currency: str | None = None) -> str | None:
    """Return the configured signup plan tier for a Stripe Price ID.

    The signup wizard sends only Stripe's ``price_id`` to ``/billing/start-trial``
    because Stripe owns amounts and recurrence. Persisting the selected plan on
    the tenant therefore needs a reverse lookup against the configured catalogue;
    unknown IDs return ``None`` so callers can reject cross-environment or stale
    prices rather than silently falling back to starter. When ``currency`` is
    supplied, the match must also belong to that tenant currency.
    """
    if not price_id:
        return None
    allowed_currency = currency.upper() if currency else None
    for tier, intervals in PRICE_IDS.items():
        for currency_prices in intervals.values():
            if allowed_currency is not None and currency_prices.get(allowed_currency) != price_id:
                continue
            if price_id in currency_prices.values():
                return tier
    return None


def get_prices_for_currency(currency: str) -> list[dict]:
    """Return all plans' price IDs for a given currency.

    Used by ``GET /api/v1/billing/prices`` to build the plan picker payload.
    Each entry:  {tier, monthly_id, annual_id}
    """
    currency = currency.upper()
    result = []
    for tier in ("starter", "growth", "pro"):
        monthly_id = PRICE_IDS.get(tier, {}).get("monthly", {}).get(currency)
        annual_id = PRICE_IDS.get(tier, {}).get("annual", {}).get(currency)
        result.append(
            {
                "tier": tier,
                "monthly_id": monthly_id,
                "annual_id": annual_id,
            }
        )
    return result


def currency_for_country(country: str) -> str:
    """Proxy to country_to_currency — convenience import for routers."""
    return country_to_currency(country)
