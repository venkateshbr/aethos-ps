"""Period lock enforcement — raises 422 if the given date is in a locked period."""

from __future__ import annotations

import asyncio
from datetime import date

from fastapi import HTTPException, status

from supabase import Client


async def assert_period_open(db: Client, tenant_id: str, entry_date: date) -> None:
    """Raise 422 with code period_locked if tenant has locked the period containing entry_date."""
    period = entry_date.strftime("%Y-%m")

    def _check() -> bool:
        result = (
            db.table("period_locks")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("period", period)
            .limit(1)
            .execute()
        )
        return bool(result.data)

    locked = await asyncio.to_thread(_check)
    if locked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "period_locked", "period": period},
        )
