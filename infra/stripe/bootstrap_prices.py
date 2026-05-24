"""Idempotent Stripe Products + Prices bootstrapper for Aethos PS.

Creates the 3 plan tiers (Starter / Growth / Pro) as Stripe Products and the
30 Prices (5 currencies × 2 intervals × 3 tiers) needed for signup. Uses
``lookup_key`` on Prices so re-runs are safe — Stripe matches by lookup_key
and returns the existing Price instead of creating a duplicate.

Numbers come from PLAN §8.6 (monthly) and a standard 10× monthly annual
discount (≈17% off, "2 months free" — the prevailing B2B SaaS convention).

Run:
    cd backend
    set -a && source /path/to/.env && set +a
    uv run python ../infra/stripe/bootstrap_prices.py

Output: a block of ``STRIPE_PRICE_*=price_...`` lines suitable for pasting
into ``.env``. The script does NOT write to ``.env`` itself — that step is
manual so the operator sees exactly what changed.

Closes #94.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import stripe

# ---------------------------------------------------------------------------
# Pricing matrix — PLAN §8.6 plus 10× annual
# ---------------------------------------------------------------------------
# Amounts in *display* units. The script multiplies by 100 (smallest unit)
# for Stripe, which works for all 5 launch currencies (USD/GBP/SGD/AUD use
# cents; INR uses paise — also ×100).

MONTHLY: dict[str, dict[str, int]] = {
    "starter": {"USD": 29, "GBP": 25, "SGD": 39, "INR": 2499, "AUD": 45},
    "growth": {"USD": 79, "GBP": 69, "SGD": 109, "INR": 6999, "AUD": 119},
    "pro": {"USD": 199, "GBP": 179, "SGD": 279, "INR": 17999, "AUD": 299},
}

# Annual = 10 × monthly (≈17% discount, "2 months free").
ANNUAL: dict[str, dict[str, int]] = {
    tier: {currency: amount * 10 for currency, amount in by_currency.items()}
    for tier, by_currency in MONTHLY.items()
}

TIER_DESCRIPTIONS = {
    "starter": "Aethos for Professional Services — Starter tier. Solo or small consulting practice; up to 3 active engagements.",
    "growth": "Aethos for Professional Services — Growth tier. Growing firms; unlimited engagements, full agent suite.",
    "pro": "Aethos for Professional Services — Pro tier. Established firms; SSO, priority support, advanced reports.",
}


@dataclass(frozen=True)
class PriceSpec:
    tier: str  # starter | growth | pro
    interval: str  # monthly | annual
    currency: str  # USD | GBP | SGD | INR | AUD
    amount_display: int  # in display units (dollars, pounds, rupees, etc.)

    @property
    def lookup_key(self) -> str:
        return f"aethos_ps_{self.tier}_{self.interval}_{self.currency.lower()}"

    @property
    def env_key(self) -> str:
        return f"STRIPE_PRICE_{self.tier.upper()}_{self.interval.upper()}_{self.currency.upper()}"

    @property
    def amount_smallest_unit(self) -> int:
        # All 5 launch currencies use ×100 for smallest unit (cents/pence/paise).
        return self.amount_display * 100

    @property
    def stripe_interval(self) -> str:
        return {"monthly": "month", "annual": "year"}[self.interval]


def _build_price_specs() -> list[PriceSpec]:
    out: list[PriceSpec] = []
    for tier, by_currency in MONTHLY.items():
        for currency, amount in by_currency.items():
            out.append(PriceSpec(tier=tier, interval="monthly", currency=currency, amount_display=amount))
    for tier, by_currency in ANNUAL.items():
        for currency, amount in by_currency.items():
            out.append(PriceSpec(tier=tier, interval="annual", currency=currency, amount_display=amount))
    return out


def _ensure_product(tier: str) -> stripe.Product:
    """Idempotently fetch or create a Product for this tier.

    Stripe doesn't have a `lookup_key` on Products, so we search by metadata.
    """
    product_id = f"aethos_ps_{tier}"
    try:
        return stripe.Product.retrieve(product_id)
    except stripe.error.InvalidRequestError:
        # 404 — create
        return stripe.Product.create(
            id=product_id,
            name=f"Aethos PS — {tier.title()}",
            description=TIER_DESCRIPTIONS[tier],
            metadata={"product_family": "aethos_ps", "tier": tier},
        )


def _ensure_price(spec: PriceSpec, product: stripe.Product) -> stripe.Price:
    """Idempotently fetch or create a Price via lookup_key."""
    existing = stripe.Price.list(lookup_keys=[spec.lookup_key], limit=1)
    if existing.data:
        return existing.data[0]
    return stripe.Price.create(
        product=product.id,
        currency=spec.currency.lower(),
        unit_amount=spec.amount_smallest_unit,
        recurring={"interval": spec.stripe_interval},
        lookup_key=spec.lookup_key,
        tax_behavior="exclusive",  # Stripe Tax adds on top — see PLAN §8.6
        nickname=f"{spec.tier.title()} {spec.interval} {spec.currency}",
        metadata={
            "product_family": "aethos_ps",
            "tier": spec.tier,
            "interval": spec.interval,
            "currency": spec.currency,
        },
    )


def main() -> int:
    key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not key:
        print("ERROR: STRIPE_SECRET_KEY not set in env. Source your .env first.", file=sys.stderr)
        return 2
    if not key.startswith("sk_test_"):
        print(
            f"REFUSING to run against non-test key (got: {key[:8]}...). "
            "This script is test-mode only. Override by removing this guard if you really mean it.",
            file=sys.stderr,
        )
        return 3

    stripe.api_key = key

    print("=" * 70)
    print(f"Bootstrapping Stripe (test mode, key={key[:12]}...)")
    print("=" * 70)

    products: dict[str, stripe.Product] = {}
    for tier in ("starter", "growth", "pro"):
        p = _ensure_product(tier)
        products[tier] = p
        print(f"  product  {tier:8s}  {p.id}")

    print()
    env_lines: list[str] = []
    for spec in _build_price_specs():
        price = _ensure_price(spec, products[spec.tier])
        env_lines.append(f"{spec.env_key}={price.id}")
        print(
            f"  price    {spec.tier:8s}  {spec.interval:7s}  "
            f"{spec.currency}  {spec.amount_display:>7,}  {price.id}"
        )

    print()
    print("=" * 70)
    print(".env block — paste this into backend/.env:")
    print("=" * 70)
    print()
    for line in env_lines:
        print(line)
    print()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
