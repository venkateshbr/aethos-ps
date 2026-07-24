"""Durable revenue-recognition schedules — straight-line deferred release (#408).

The revenue_recognition_agent uses these to release *historical* deferred-revenue
balances on a durable plan. Schedule rows live in ``revenue_recognition_schedules``
(migration 0112); the pure helpers here compute the straight-line split and the
amount due for a given close period (with catch-up for missed periods). All
posting stays HITL — ``recognized_to_date`` only advances when a drafted release
is approved and posted. See ADR 0004.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_PERIOD = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
_TWO = Decimal("0.01")


class RevenueScheduleError(ValueError):
    """Raised when a schedule cannot be built safely."""


def _ym(period: str) -> tuple[int, int]:
    if not _PERIOD.match(period):
        raise RevenueScheduleError(f"Invalid period {period!r}; expected YYYY-MM")
    return int(period[:4]), int(period[5:7])


def months_between(start_period: str, period: str) -> int:
    """0-based month index of ``period`` relative to ``start_period`` (may be < 0)."""
    sy, sm = _ym(start_period)
    py, pm = _ym(period)
    return (py - sy) * 12 + (pm - sm)


def add_months(period: str, count: int) -> str:
    """Return the period ``count`` months after ``period`` (count may be 0)."""
    year, month = _ym(period)
    total = (year * 12 + (month - 1)) + count
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def straight_line_amounts(total: Decimal, periods: int) -> list[Decimal]:
    """Split ``total`` into ``periods`` 2dp monthly amounts; last absorbs rounding."""
    if periods < 1:
        raise RevenueScheduleError("periods must be >= 1")
    per = (total / periods).quantize(_TWO, rounding=ROUND_HALF_UP)
    amounts = [per] * (periods - 1)
    amounts.append((total - per * (periods - 1)).quantize(_TWO))
    return amounts


def period_release_amount(
    *,
    total: Decimal,
    periods: int,
    start_period: str,
    period: str,
    recognized_to_date: Decimal,
) -> Decimal:
    """Base-currency amount to recognize for ``period`` under a straight-line plan.

    The target cumulative recognition through ``period`` is the sum of the
    scheduled amounts up to and including that month; the release is that target
    minus what has already been recognized (so a lagging schedule catches up on
    missed periods), floored at zero and never exceeding the remaining balance.
    """
    idx = months_between(start_period, period)
    if idx < 0 or idx >= periods:
        return Decimal("0.00")
    cumulative_target = sum(straight_line_amounts(total, periods)[: idx + 1], Decimal("0"))
    release = cumulative_target - recognized_to_date
    if release <= 0:
        return Decimal("0.00")
    return min(release, total - recognized_to_date).quantize(_TWO)


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------


class RevenueRecognitionScheduleService:
    def __init__(self, db: Any, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def create_schedule(
        self,
        *,
        total_amount: Decimal,
        base_total_amount: Decimal,
        currency: str,
        base_currency: str,
        start_period: str,
        periods: int,
        source_type: str = "manual",
        source_id: str | None = None,
        deferred_account_code: str = "2200",
        revenue_account_code: str = "4000",
        description: str | None = None,
    ) -> dict:
        if periods < 1:
            raise RevenueScheduleError("periods must be >= 1")
        if total_amount < 0:
            raise RevenueScheduleError("total_amount must be >= 0")
        _ym(start_period)  # validate format
        row = {
            "tenant_id": self.tenant_id,
            "source_type": source_type,
            "source_id": source_id,
            "method": "straight_line",
            "currency": currency.upper(),
            "base_currency": base_currency.upper(),
            "start_period": start_period,
            "end_period": add_months(start_period, periods - 1),
            "periods": periods,
            "total_amount": str(total_amount.quantize(_TWO)),
            "base_total_amount": str(base_total_amount.quantize(_TWO)),
            "recognized_to_date": "0.00",
            "deferred_account_code": deferred_account_code,
            "revenue_account_code": revenue_account_code,
            "status": "active",
            "description": description,
        }
        result = self.db.table("revenue_recognition_schedules").insert(row).execute()
        return (result.data or [row])[0]

    def list_active(self) -> list[dict]:
        return (
            self.db.table("revenue_recognition_schedules")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .eq("status", "active")
            .execute()
            .data
            or []
        )

    def mark_recognized(self, schedule_id: str, recognized_to_date: Decimal, total: Decimal) -> None:
        """Advance recognized_to_date; complete the schedule when fully recognized."""
        status = "completed" if recognized_to_date >= total else "active"
        (
            self.db.table("revenue_recognition_schedules")
            .update(
                {
                    "recognized_to_date": str(recognized_to_date.quantize(_TWO)),
                    "status": status,
                }
            )
            .eq("id", schedule_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
