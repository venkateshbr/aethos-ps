"""Procrastinate task: daily FX rate refresh.

Fetches daily exchange rates from Open Exchange Rates (free tier) and upserts
the ``fx_rates`` table in Supabase.

Source endpoint: https://open.er-api.com/v6/latest/USD
  - No API key required on the free tier.
  - Response: {"rates": {"GBP": 0.79, "SGD": 1.34, ...}}

Rate model:
  - All rates are stored as USD-pivot pairs.
  - USD→USD = 1.0 (stored explicitly).
  - Cross-rates (e.g. GBP→SGD) are NOT stored — they are computed on-the-fly
    by the service layer from USD-pivot pairs.

Upsert conflict key: (from_currency, to_currency, rate_date).

Returns a summary dict: {"updated": int, "skipped": int, "errors": list[str]}
"""

from __future__ import annotations

import logging
from datetime import UTC, date
from datetime import datetime as dt
from decimal import Decimal, InvalidOperation

import httpx

from app.core.config import settings
from app.core.db import get_service_role_client
from app.workers.procrastinate_app import app

logger = logging.getLogger(__name__)

# The 5 ISO 4217 codes for launch currencies (USD excluded as pivot base — it's 1.0).
_QUOTE_CURRENCIES: frozenset[str] = frozenset({"GBP", "SGD", "INR", "AUD"})

_FX_API_URL = "https://open.er-api.com/v6/latest/USD"

# Source label stored in ``fx_rates.source``.
_SOURCE = "open.er-api.com"


@app.periodic(cron="0 8 * * *")
@app.task(name="fx_refresh_worker", queue="cron")
async def fx_refresh_worker(timestamp: int) -> dict:
    """Fetch and store daily FX rates for the 5 launch currencies.

    Scheduled daily at 08:00 UTC by Procrastinate's periodic registry.
    Can also be triggered manually via the Procrastinate CLI:
        uv run python -m procrastinate --app=app.workers.procrastinate_app.app \
            defer app.workers.fx_refresh.fx_refresh_worker

    Returns:
        {"updated": int, "skipped": int, "errors": list[str]}
    """
    _ = timestamp  # provided by Procrastinate periodic; we use date.today() instead
    today = date.today()
    db = get_service_role_client()
    updated = 0
    skipped = 0
    errors: list[str] = []

    # ------------------------------------------------------------------
    # Check if today's rates are already present (avoid double-refresh).
    # ------------------------------------------------------------------
    existing_check = (
        db.table("fx_rates")
        .select("id")
        .eq("rate_date", today.isoformat())
        .limit(1)
        .execute()
    )
    if existing_check.data:
        logger.warning(
            "fx_refresh_worker: rates for %s already present — skipping refresh.",
            today,
        )
        return {"updated": 0, "skipped": len(_QUOTE_CURRENCIES) + 1, "errors": []}

    # ------------------------------------------------------------------
    # Fetch live rates from Open Exchange Rates.
    # ------------------------------------------------------------------
    params: dict[str, str] = {}
    if settings.openexchangerates_app_id:
        params["app_id"] = settings.openexchangerates_app_id

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(_FX_API_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        error_msg = f"HTTP error fetching FX rates: {exc}"
        logger.error(error_msg)
        return {"updated": 0, "skipped": 0, "errors": [error_msg]}

    raw_rates: dict[str, float] = payload.get("rates", {})

    if not raw_rates:
        error_msg = "FX API returned empty rates payload"
        logger.error(error_msg)
        return {"updated": 0, "skipped": 0, "errors": [error_msg]}

    # ------------------------------------------------------------------
    # Build USD-pivot rows for all required pairs.
    # Pairs to store:
    #   USD→GBP, USD→SGD, USD→INR, USD→AUD  (and USD→USD = 1)
    #   GBP→USD, SGD→USD, INR→USD, AUD→USD  (inverse of the above)
    # ------------------------------------------------------------------
    rows_to_upsert: list[dict] = []

    # USD→USD (always 1.0)
    rows_to_upsert.append(_make_row("USD", "USD", Decimal("1"), today))

    for quote in _QUOTE_CURRENCIES:
        raw = raw_rates.get(quote)
        if raw is None:
            errors.append(f"Rate for {quote} missing from API response")
            continue

        try:
            usd_to_quote = Decimal(str(raw)).quantize(Decimal("0.000001"))
        except InvalidOperation as exc:
            errors.append(f"Invalid rate value for {quote}: {raw!r} — {exc}")
            continue

        if usd_to_quote <= 0:
            errors.append(f"Non-positive rate for USD→{quote}: {usd_to_quote}")
            continue

        # USD → quote (direct from API)
        rows_to_upsert.append(_make_row("USD", quote, usd_to_quote, today))

        # quote → USD (inverse)
        quote_to_usd = (Decimal("1") / usd_to_quote).quantize(Decimal("0.000001"))
        rows_to_upsert.append(_make_row(quote, "USD", quote_to_usd, today))

        # quote → quote (self = 1.0)
        rows_to_upsert.append(_make_row(quote, quote, Decimal("1"), today))

    # ------------------------------------------------------------------
    # Upsert into fx_rates.  Supabase upsert uses on_conflict to resolve
    # (from_currency, to_currency, rate_date) uniqueness.
    # ------------------------------------------------------------------
    if rows_to_upsert:
        try:
            result = (
                db.table("fx_rates")
                .upsert(rows_to_upsert, on_conflict="from_currency,to_currency,rate_date")
                .execute()
            )
            updated = len(result.data) if result.data else len(rows_to_upsert)
        except Exception as exc:
            error_msg = f"Supabase upsert failed: {exc}"
            logger.error(error_msg)
            errors.append(error_msg)
            updated = 0

    summary = {"updated": updated, "skipped": skipped, "errors": errors}
    logger.info(
        "fx_refresh_worker complete — updated=%d skipped=%d errors=%d",
        updated,
        skipped,
        len(errors),
    )
    return summary


def _make_row(
    from_currency: str,
    to_currency: str,
    rate: Decimal,
    rate_date: date,
) -> dict:
    """Build a dict suitable for the ``fx_rates`` table upsert."""
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": str(rate),
        "rate_date": rate_date.isoformat(),
        "source": _SOURCE,
        "fetched_at": dt.now(tz=UTC).isoformat(),
    }
