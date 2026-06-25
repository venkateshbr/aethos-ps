"""Unit tests for shared AR payment FX helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.payment_fx_service import payment_fx_amounts

pytestmark = pytest.mark.unit


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _TenantQuery:
    def __init__(self, base_currency: str) -> None:
        self.base_currency = base_currency

    def select(self, _columns: str) -> _TenantQuery:
        return self

    def eq(self, _key: str, _value: str) -> _TenantQuery:
        return self

    def limit(self, _count: int) -> _TenantQuery:
        return self

    def execute(self) -> _Result:
        return _Result([{"base_currency": self.base_currency}])


class _TenantDb:
    def __init__(self, base_currency: str) -> None:
        self.base_currency = base_currency

    def table(self, name: str) -> _TenantQuery:
        if name != "tenants":
            raise AssertionError(f"unexpected table: {name}")
        return _TenantQuery(self.base_currency)


@pytest.mark.asyncio
async def test_payment_fx_amounts_same_currency_skips_fx_lookup() -> None:
    get_fx_rate = AsyncMock()

    with patch("app.services.payment_fx_service.get_fx_rate", get_fx_rate):
        result = await payment_fx_amounts(
            db=_TenantDb("USD"),  # type: ignore[arg-type]
            tenant_id="tenant-1",
            amount=Decimal("125.00"),
            currency="usd",
            paid_at="2026-06-25T12:00:00+00:00",
        )

    get_fx_rate.assert_not_awaited()
    assert result.currency == "USD"
    assert result.base_currency == "USD"
    assert result.base_amount == Decimal("125.00")
    assert result.rate == Decimal("1")
    assert result.rate_date == date(2026, 6, 25)


@pytest.mark.asyncio
async def test_payment_fx_amounts_converts_foreign_payment_to_base() -> None:
    get_fx_rate = AsyncMock(return_value=Decimal("1.25"))
    db = _TenantDb("USD")

    with patch("app.services.payment_fx_service.get_fx_rate", get_fx_rate):
        result = await payment_fx_amounts(
            db=db,  # type: ignore[arg-type]
            tenant_id="tenant-1",
            amount=Decimal("100.00"),
            currency="GBP",
            paid_at="2026-06-25T12:00:00+00:00",
        )

    get_fx_rate.assert_awaited_once_with(
        "GBP",
        "USD",
        date(2026, 6, 25),
        db,
    )
    assert result.base_amount == Decimal("125.00")
    assert result.rate == Decimal("1.25")
