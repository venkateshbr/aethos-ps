"""FX rate helpers for multi-currency support.

The canonical data store for FX rates is the ``fx_rates`` table in Supabase.
Rates are stored as USD-pivot pairs (from_currency → to_currency).

USD→USD is a special case that always returns Decimal("1").

Usage in service layer:
    rate = await get_fx_rate("GBP", "USD", invoice_date, db_client)
    base_amount = foreign_amount * rate
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

# Maximum age (in days) before we warn that the rate may be stale.
_STALE_THRESHOLD_DAYS = 3

# The 5 launch currencies.
LAUNCH_CURRENCIES: frozenset[str] = frozenset({"USD", "GBP", "SGD", "INR", "AUD"})


class FxRateNotFoundError(Exception):
    """Raised when no FX rate row exists for the requested currency pair / date."""

    def __init__(self, from_currency: str, to_currency: str, rate_date: date) -> None:
        super().__init__(
            f"No FX rate found for {from_currency}→{to_currency} on {rate_date}"
        )
        self.from_currency = from_currency
        self.to_currency = to_currency
        self.rate_date = rate_date


@dataclass(frozen=True)
class FxRateRecord:
    from_currency: str
    to_currency: str
    rate_date: date
    rate: Decimal
    id: str | None = None
    source: str | None = None


async def get_fx_rate(
    from_currency: str,
    to_currency: str,
    rate_date: date,
    db_client,
) -> Decimal:
    """Look up the FX rate for *from_currency* → *to_currency* on *rate_date*.

    The lookup falls back to the most recent rate available on or before
    *rate_date* to handle weekends and market-closed days gracefully.

    Args:
        from_currency: ISO 4217 source currency code (e.g. "GBP").
        to_currency:   ISO 4217 target currency code (e.g. "USD").
        rate_date:     The date for which the rate is needed.
        db_client:     Supabase client instance.

    Returns:
        The exchange rate as a ``Decimal``.

    Raises:
        FxRateNotFoundError: If no rate row exists for the pair.

    Warns (via logging):
        If the rate found is more than ``_STALE_THRESHOLD_DAYS`` old.
    """
    return (
        await get_fx_rate_record(from_currency, to_currency, rate_date, db_client)
    ).rate


async def get_fx_rate_record(
    from_currency: str,
    to_currency: str,
    rate_date: date,
    db_client,
) -> FxRateRecord:
    """Look up an FX rate row with its immutable provenance id."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    # Fast path: same currency is always 1 and has no fx_rates row.
    if from_currency == to_currency:
        return FxRateRecord(
            from_currency=from_currency,
            to_currency=to_currency,
            rate_date=rate_date,
            rate=Decimal("1"),
            id=None,
            source="identity",
        )

    # Look up on or before rate_date (most recent available).
    result = (
        db_client.table("fx_rates")
        .select("id, rate, rate_date, source")
        .eq("from_currency", from_currency)
        .eq("to_currency", to_currency)
        .lte("rate_date", rate_date.isoformat())
        .order("rate_date", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise FxRateNotFoundError(from_currency, to_currency, rate_date)

    row = result.data[0]
    actual_date = date.fromisoformat(row["rate_date"])
    staleness = rate_date - actual_date

    if staleness > timedelta(days=_STALE_THRESHOLD_DAYS):
        logger.warning(
            "FX rate for %s→%s on %s is %d days old (using rate from %s). "
            "Consider running fx_refresh_worker.",
            from_currency,
            to_currency,
            rate_date,
            staleness.days,
            actual_date,
        )

    return FxRateRecord(
        from_currency=from_currency,
        to_currency=to_currency,
        rate_date=actual_date,
        rate=Decimal(str(row["rate"])),
        id=str(row["id"]) if row.get("id") else None,
        source=str(row["source"]) if row.get("source") else None,
    )
