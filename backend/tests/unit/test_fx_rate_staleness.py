"""Unit tests for FX rate staleness detection (#183).

Tests:
- is_stale returns True for rates older than 72 hours
- is_stale returns False for rates exactly 72 hours old
- get_fx_rate_with_staleness returns correct metadata
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# is_stale
# ---------------------------------------------------------------------------


def test_rate_is_stale_at_73_hours() -> None:
    from app.services.fx_rate_service import is_stale

    refreshed_at = datetime.now(UTC) - timedelta(hours=73)
    assert is_stale(refreshed_at) is True


def test_rate_not_stale_at_72_hours() -> None:
    from app.services.fx_rate_service import is_stale

    refreshed_at = datetime.now(UTC) - timedelta(hours=72, seconds=59)
    assert is_stale(refreshed_at) is False


def test_rate_not_stale_at_71_hours() -> None:
    from app.services.fx_rate_service import is_stale

    refreshed_at = datetime.now(UTC) - timedelta(hours=71)
    assert is_stale(refreshed_at) is False


def test_rate_is_stale_at_100_hours() -> None:
    from app.services.fx_rate_service import is_stale

    refreshed_at = datetime.now(UTC) - timedelta(hours=100)
    assert is_stale(refreshed_at) is True


def test_rate_fresh_returns_not_stale() -> None:
    from app.services.fx_rate_service import is_stale

    refreshed_at = datetime.now(UTC) - timedelta(hours=1)
    assert is_stale(refreshed_at) is False


# ---------------------------------------------------------------------------
# get_fx_rate_with_staleness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_fx_rate_with_staleness_returns_stale_flag() -> None:
    from datetime import date

    from app.services.fx_rate_service import get_fx_rate_with_staleness

    db = MagicMock()

    stale_date = (datetime.now(UTC) - timedelta(hours=80)).isoformat()

    # First call: get_fx_rate inner lookup
    rate_mock = MagicMock()
    rate_mock.data = [{"rate": "1.25", "rate_date": "2026-06-01"}]

    # Second call: staleness metadata lookup
    meta_mock = MagicMock()
    meta_mock.data = [{"rate_date": "2026-06-01", "created_at": stale_date, "updated_at": stale_date}]

    call_count = 0

    table_chain = MagicMock()
    db.table.return_value = table_chain
    table_chain.select.return_value = table_chain
    table_chain.eq.return_value = table_chain
    table_chain.lte.return_value = table_chain
    table_chain.order.return_value = table_chain
    table_chain.limit.return_value = table_chain

    def execute_side() -> MagicMock:
        nonlocal call_count
        call_count += 1
        return rate_mock if call_count == 1 else meta_mock

    table_chain.execute.side_effect = execute_side

    result = await get_fx_rate_with_staleness("USD", "GBP", date(2026, 6, 15), db)

    assert result["from_currency"] == "USD"
    assert result["to_currency"] == "GBP"
    assert result["rate"] == "1.25"
    assert result["stale"] is True
    metadata_select = table_chain.select.call_args_list[1].args[0]
    assert metadata_select == "rate_date, created_at"
    assert "updated_at" not in metadata_select


@pytest.mark.asyncio
async def test_get_fx_rate_with_staleness_fresh_rate() -> None:
    from datetime import date

    from app.services.fx_rate_service import get_fx_rate_with_staleness

    db = MagicMock()

    fresh_date = (datetime.now(UTC) - timedelta(hours=12)).isoformat()

    rate_mock = MagicMock()
    rate_mock.data = [{"rate": "0.79", "rate_date": "2026-06-15"}]

    meta_mock = MagicMock()
    meta_mock.data = [{"rate_date": "2026-06-15", "created_at": fresh_date, "updated_at": fresh_date}]

    call_count = 0

    table_chain = MagicMock()
    db.table.return_value = table_chain
    table_chain.select.return_value = table_chain
    table_chain.eq.return_value = table_chain
    table_chain.lte.return_value = table_chain
    table_chain.order.return_value = table_chain
    table_chain.limit.return_value = table_chain

    def execute_side() -> MagicMock:
        nonlocal call_count
        call_count += 1
        return rate_mock if call_count == 1 else meta_mock

    table_chain.execute.side_effect = execute_side

    result = await get_fx_rate_with_staleness("USD", "GBP", date(2026, 6, 15), db)

    assert result["stale"] is False
    assert result["rate"] == "0.79"


@pytest.mark.asyncio
async def test_historical_lookup_returns_immutable_rate_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import date

    from app.services import fx_rate_service

    db = MagicMock()
    table_chain = MagicMock()
    db.table.return_value = table_chain
    table_chain.select.return_value = table_chain
    table_chain.eq.return_value = table_chain
    table_chain.lte.return_value = table_chain
    table_chain.order.return_value = table_chain
    table_chain.limit.return_value = table_chain
    refreshed_at = (datetime.now(UTC) - timedelta(hours=12)).isoformat()
    metadata = MagicMock()
    metadata.data = [{"created_at": refreshed_at}]
    table_chain.execute.return_value = metadata

    record_lookup = AsyncMock(
        return_value=SimpleNamespace(
            from_currency="USD",
            to_currency="SGD",
            rate_date=date(2026, 5, 30),
            rate=Decimal("1.350000"),
            id="fx-usd-sgd-2026-05-30",
            source="openexchangerates",
        )
    )
    monkeypatch.setattr(
        fx_rate_service,
        "get_fx_rate_record",
        record_lookup,
        raising=False,
    )
    result = await fx_rate_service.get_fx_rate_with_staleness(
        "usd",
        "sgd",
        date(2026, 5, 31),
        db,
    )

    record_lookup.assert_awaited_once_with("USD", "SGD", date(2026, 5, 31), db)
    assert result == {
        "from_currency": "USD",
        "to_currency": "SGD",
        "rate": "1.350000",
        "refreshed_at": refreshed_at,
        "stale": False,
        "requested_rate_date": "2026-05-31",
        "rate_date": "2026-05-30",
        "fx_rate_id": "fx-usd-sgd-2026-05-30",
        "source": "openexchangerates",
        "staleness_days": 1,
    }
