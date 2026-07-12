"""FX rate service — tenant-scoped lookup with immutable provenance.

Wraps the domain-level ``get_fx_rate_record`` helper and adds:
- requested-date versus matched-date staleness
- immutable row id and source provenance
- Endpoint-friendly response dict
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from app.domain.fx import get_fx_rate_record
from supabase import Client

logger = logging.getLogger(__name__)

_STALE_HOURS = 72


def is_stale(refreshed_at: datetime) -> bool:
    """Return True if the rate was last refreshed more than 72 hours ago."""
    now = datetime.now(UTC)
    age = now - refreshed_at
    age_hours = int(age.total_seconds() // 3600)
    return age_hours > _STALE_HOURS


async def get_fx_rate_with_staleness(
    from_currency: str,
    to_currency: str,
    rate_date: date,
    db: Client,
) -> dict:
    """Look up an FX rate and return it with staleness metadata.

    Returns
    -------
    dict with keys:
        from_currency, to_currency, rate (str), refreshed_at (ISO str), stale
        (bool), requested_rate_date (ISO date), rate_date (matched ISO date),
        fx_rate_id (immutable row id or None), source, and staleness_days.

    Raises
    ------
    FxRateNotFoundError if no rate exists.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    record = await get_fx_rate_record(from_currency, to_currency, rate_date, db)

    # Fetch the rate row to get refreshed_at / rate_date. The migration only
    # guarantees created_at on fx_rates; fetched_at may exist in newer DBs, but
    # updated_at is not part of the base schema.
    result = (
        db.table("fx_rates")
        .select("rate_date, created_at")
        .eq("from_currency", from_currency)
        .eq("to_currency", to_currency)
        .lte("rate_date", rate_date.isoformat())
        .order("rate_date", desc=True)
        .limit(1)
        .execute()
    )

    row = result.data[0] if result.data else {}
    refreshed_at_str: str = row.get("created_at") or datetime.now(UTC).isoformat()
    try:
        refreshed_at = datetime.fromisoformat(refreshed_at_str.replace("Z", "+00:00"))
        if refreshed_at.tzinfo is None:
            refreshed_at = refreshed_at.replace(tzinfo=UTC)
    except (ValueError, AttributeError):
        refreshed_at = datetime.now(UTC)

    staleness_days = max((rate_date - record.rate_date).days, 0)
    # Preserve the legacy response contract: ``stale`` describes source-row
    # refresh age. Historical requested-vs-matched lag is ``staleness_days``.
    stale = is_stale(refreshed_at)
    if stale:
        logger.warning(
            "fx_rate_service: rate %s→%s is stale (last refreshed %s)",
            from_currency,
            to_currency,
            refreshed_at_str,
        )

    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": str(record.rate),
        "refreshed_at": refreshed_at.isoformat(),
        "stale": stale,
        "requested_rate_date": rate_date.isoformat(),
        "rate_date": record.rate_date.isoformat(),
        "fx_rate_id": record.id,
        "source": record.source or "unknown",
        "staleness_days": staleness_days,
    }
