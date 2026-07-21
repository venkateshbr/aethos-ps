"""FX rates endpoint — expose current or historical rates with provenance.

GET /api/v1/fx-rates/{from_currency}/{to_currency}
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_user_rls_client
from app.core.tenant import get_tenant_id
from app.domain.fx import LAUNCH_CURRENCIES, FxRateNotFoundError
from app.services.fx_rate_service import get_fx_rate_with_staleness
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{from_currency}/{to_currency}")
async def get_fx_rate(
    from_currency: str,
    to_currency: str,
    rate_date: date | None = Query(  # noqa: B008
        default=None,
        description="Historical ISO date (YYYY-MM-DD); defaults to today",
    ),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    _tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_user_rls_client),  # noqa: B008
) -> dict:
    """Return the FX rate available on a date with immutable provenance.

    Response schema:
        from_currency: str
        to_currency:   str
        rate:          str   (Decimal serialised as string)
        refreshed_at:  str   (ISO 8601 datetime)
        stale:         bool  (True if rate > 72 h old)
        requested_rate_date: str (requested ISO date)
        rate_date:     str   (matched ISO date)
        fx_rate_id:    str | None (immutable stored-rate id)
        source:        str   (rate provenance)
        staleness_days: int  (requested date minus matched date)
    """
    normalized_from = from_currency.strip().upper()
    normalized_to = to_currency.strip().upper()
    for currency in (normalized_from, normalized_to):
        if currency not in LAUNCH_CURRENCIES:
            supported = ", ".join(sorted(LAUNCH_CURRENCIES))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported currency {currency}. Supported currencies: {supported}",
            )

    requested_rate_date = rate_date or date.today()
    if requested_rate_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="FX rate date cannot be in the future",
        )

    try:
        return await get_fx_rate_with_staleness(
            from_currency=normalized_from,
            to_currency=normalized_to,
            rate_date=requested_rate_date,
            db=db,
        )
    except FxRateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No FX rate found for {normalized_from}→{normalized_to} "
                f"on or before {requested_rate_date.isoformat()}"
            ),
        ) from exc
