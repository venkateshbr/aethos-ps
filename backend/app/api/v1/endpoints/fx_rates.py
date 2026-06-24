"""FX rates endpoint — expose current rates with staleness flag.

GET /api/v1/fx-rates/{from_currency}/{to_currency}
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_user_rls_client
from app.core.tenant import get_tenant_id
from app.domain.fx import FxRateNotFoundError
from app.services.fx_rate_service import get_fx_rate_with_staleness
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{from_currency}/{to_currency}")
async def get_fx_rate(
    from_currency: str,
    to_currency: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    _tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_user_rls_client),  # noqa: B008
) -> dict:
    """Return the FX rate for a currency pair with a staleness flag.

    Response schema:
        from_currency: str
        to_currency:   str
        rate:          str   (Decimal serialised as string)
        refreshed_at:  str   (ISO 8601 datetime)
        stale:         bool  (True if rate > 72 h old)
    """
    try:
        return await get_fx_rate_with_staleness(
            from_currency=from_currency,
            to_currency=to_currency,
            rate_date=date.today(),
            db=db,
        )
    except FxRateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No FX rate found for {from_currency.upper()}→{to_currency.upper()}",
        ) from exc
