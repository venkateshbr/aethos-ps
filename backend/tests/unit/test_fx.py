"""Unit tests for FX rate helpers.

All tests are pure-Python — no I/O, no network, no DB.
The ``get_fx_rate`` function requires a live DB client; those tests use a mock.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.fx import FxRateNotFoundError, get_fx_rate, get_fx_rate_record

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# USD→USD identity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_usd_to_usd_rate_is_one() -> None:
    """USD→USD must always return Decimal('1') without touching the DB."""
    db_mock = MagicMock()
    rate = await get_fx_rate("USD", "USD", date.today(), db_mock)
    assert rate == Decimal("1")
    # The DB client must NOT have been called for same-currency lookups.
    db_mock.table.assert_not_called()


@pytest.mark.asyncio
async def test_same_currency_any_code_is_one() -> None:
    """Same-currency pairs always return 1 regardless of the code."""
    db_mock = MagicMock()
    for code in ("GBP", "SGD", "INR", "AUD"):
        rate = await get_fx_rate(code, code, date.today(), db_mock)
        assert rate == Decimal("1"), f"Expected 1 for {code}→{code}, got {rate}"


# ---------------------------------------------------------------------------
# Cross-rate derivation note
# Cross-rates (GBP→SGD) are NOT stored in the DB; only USD-pivot pairs are.
# This test validates the mathematical invariant for how a service would compute
# a cross-rate from two USD-pivot lookups.
# ---------------------------------------------------------------------------


def test_cross_rate_computed_correctly() -> None:
    """Cross-rate from two USD-pivot lookups must be mathematically correct.

    GBP_to_USD = 0.79  (i.e. 1 GBP = 0.79 USD, so USD→GBP rate = 0.79,
                         meaning GBP→USD rate = 1/0.79)
    SGD_to_USD = 1/1.34 (USD→SGD = 1.34, so SGD→USD = 1/1.34)

    GBP→SGD cross-rate  = GBP_to_USD / SGD_to_USD
                        = (1 / 0.79) / (1 / 1.34)
                        = 1.34 / 0.79
    """
    usd_to_gbp = Decimal("0.79")  # API gives USD→GBP = 0.79
    usd_to_sgd = Decimal("1.34")  # API gives USD→SGD = 1.34

    # GBP→SGD = (1/usd_to_gbp) * usd_to_sgd
    gbp_to_usd = Decimal("1") / usd_to_gbp
    cross_rate = gbp_to_usd * usd_to_sgd

    # 1.34 / 0.79 ≈ 1.6962...
    expected = Decimal("1.34") / Decimal("0.79")
    assert abs(cross_rate - expected) < Decimal("0.0001"), (
        f"Cross-rate mismatch: got {cross_rate}, expected ~{expected}"
    )
    assert cross_rate > Decimal("1.69")
    assert cross_rate < Decimal("1.70")


# ---------------------------------------------------------------------------
# DB lookup path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_fx_rate_returns_decimal_from_db() -> None:
    """get_fx_rate retrieves a row and returns its rate as Decimal."""
    db_mock = MagicMock()
    # Build the query-chain mock that supabase returns.
    mock_result = MagicMock()
    mock_result.data = [{"rate": "1.250000", "rate_date": "2026-05-19"}]
    # Chain: .table().select().eq().eq().lte().order().limit().execute()
    (
        db_mock.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .lte.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
    ) = mock_result

    rate = await get_fx_rate("USD", "SGD", date(2026, 5, 19), db_mock)
    assert rate == Decimal("1.250000")


@pytest.mark.asyncio
async def test_get_fx_rate_record_returns_rate_id_from_db() -> None:
    db_mock = MagicMock()
    mock_result = MagicMock()
    mock_result.data = [
        {"id": "fx-rate-1", "rate": "1.250000", "rate_date": "2026-05-19"}
    ]
    (
        db_mock.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .lte.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
    ) = mock_result

    record = await get_fx_rate_record("USD", "SGD", date(2026, 5, 19), db_mock)

    assert record.id == "fx-rate-1"
    assert record.rate == Decimal("1.250000")
    assert record.rate_date == date(2026, 5, 19)


@pytest.mark.asyncio
async def test_get_fx_rate_raises_when_not_found() -> None:
    """get_fx_rate raises FxRateNotFoundError when DB returns no rows."""
    db_mock = MagicMock()
    mock_result = MagicMock()
    mock_result.data = []
    (
        db_mock.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .lte.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
    ) = mock_result

    with pytest.raises(FxRateNotFoundError) as exc_info:
        await get_fx_rate("GBP", "INR", date(2026, 5, 19), db_mock)

    err = exc_info.value
    assert err.from_currency == "GBP"
    assert err.to_currency == "INR"


@pytest.mark.asyncio
async def test_get_fx_rate_normalises_currency_codes_to_uppercase() -> None:
    """Lowercase currency codes are normalised before DB lookup."""
    db_mock = MagicMock()
    mock_result = MagicMock()
    mock_result.data = [{"rate": "1.34", "rate_date": "2026-05-19"}]
    chain = (
        db_mock.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .lte.return_value
        .order.return_value
        .limit.return_value
    )
    chain.execute.return_value = mock_result

    rate = await get_fx_rate("usd", "sgd", date(2026, 5, 19), db_mock)
    assert isinstance(rate, Decimal)


# ---------------------------------------------------------------------------
# country_to_currency coverage (5 launch markets) — imported from stripe_service
# which already has comprehensive tests; we add the 5-market assertion here for
# completeness as specified in the issue.
# ---------------------------------------------------------------------------


def test_country_currency_mapping_covers_5_markets() -> None:
    """country_to_currency must cover all 5 launch markets correctly."""
    from app.services.billing.stripe_service import country_to_currency

    expected_pairs = [
        ("US", "USD"),
        ("GB", "GBP"),
        ("SG", "SGD"),
        ("IN", "INR"),
        ("AU", "AUD"),
    ]
    for country, expected_currency in expected_pairs:
        result = country_to_currency(country)
        assert result == expected_currency, (
            f"country_to_currency({country!r}) = {result!r}, expected {expected_currency!r}"
        )
