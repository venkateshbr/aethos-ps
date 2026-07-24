"""Unit tests for the durable rev-rec schedule math + service (#408)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.revenue_recognition_schedule_service import (
    RevenueRecognitionScheduleService,
    RevenueScheduleError,
    add_months,
    months_between,
    period_release_amount,
    straight_line_amounts,
)

pytestmark = pytest.mark.unit


def test_straight_line_split_sums_to_total_with_last_absorbing_rounding() -> None:
    amounts = straight_line_amounts(Decimal("1000.00"), 3)
    assert amounts == [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]
    assert sum(amounts) == Decimal("1000.00")


def test_months_between_and_add_months_roll_over_years() -> None:
    assert months_between("2026-01", "2026-01") == 0
    assert months_between("2026-01", "2026-12") == 11
    assert months_between("2026-06", "2027-01") == 7
    assert months_between("2026-06", "2026-05") == -1
    assert add_months("2026-11", 3) == "2027-02"
    assert add_months("2026-06", 0) == "2026-06"


def test_period_release_in_range_and_out_of_range() -> None:
    args = dict(total=Decimal("1200.00"), periods=12, start_period="2026-01",
               recognized_to_date=Decimal("0"))
    # Month 1: 1/12 of 1200 = 100.
    assert period_release_amount(period="2026-01", **args) == Decimal("100.00")
    # Before start / after end → nothing.
    assert period_release_amount(period="2025-12", **args) == Decimal("0.00")
    assert period_release_amount(period="2027-01", **args) == Decimal("0.00")


def test_period_release_catches_up_missed_periods() -> None:
    # Nothing recognized yet, but we are at month 3 (index 2) → release the
    # cumulative target (300), not just one month.
    release = period_release_amount(
        total=Decimal("1200.00"), periods=12, start_period="2026-01",
        period="2026-03", recognized_to_date=Decimal("0"),
    )
    assert release == Decimal("300.00")


def test_period_release_zero_when_already_recognized_through_period() -> None:
    release = period_release_amount(
        total=Decimal("1200.00"), periods=12, start_period="2026-01",
        period="2026-03", recognized_to_date=Decimal("300.00"),
    )
    assert release == Decimal("0.00")


def test_final_period_settles_the_remainder_exactly() -> None:
    release = period_release_amount(
        total=Decimal("1000.00"), periods=3, start_period="2026-01",
        period="2026-03", recognized_to_date=Decimal("666.66"),
    )
    assert release == Decimal("333.34")  # 1000 - 666.66


class _Result:
    def __init__(self, data): self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows
        self._payload = None

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def insert(self, payload):
        self._payload = payload
        return self

    def update(self, payload):
        self._payload = payload
        return self

    def execute(self):
        if self._payload is not None:
            return _Result([{**self._payload, "id": "sched-1"}])
        return _Result(self._rows)


class _Db:
    def __init__(self, rows=None):
        self._rows = rows or []

    def table(self, _name):
        return _Query(self._rows)


def test_create_schedule_derives_end_period_and_validates() -> None:
    svc = RevenueRecognitionScheduleService(_Db(), "t1")
    row = svc.create_schedule(
        total_amount=Decimal("1200.00"), base_total_amount=Decimal("1200.00"),
        currency="USD", base_currency="USD", start_period="2026-01", periods=12,
    )
    assert row["end_period"] == "2026-12"
    assert row["recognized_to_date"] == "0.00"
    assert row["status"] == "active"

    with pytest.raises(RevenueScheduleError):
        svc.create_schedule(
            total_amount=Decimal("100"), base_total_amount=Decimal("100"),
            currency="USD", base_currency="USD", start_period="2026-13", periods=1,
        )
