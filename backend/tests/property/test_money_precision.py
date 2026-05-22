"""Property tests for accounting invariant I6: money precision preserved.

Source: docs/test/accounting_invariants.md §I6.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

pytestmark = pytest.mark.property

two_dp_money = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@given(two_dp_money, two_dp_money)
def test_addition_preserves_two_decimal_places(a, b):
    result = a + b
    assert result == result.quantize(Decimal("0.01"))


@given(two_dp_money)
def test_negation_preserves_precision(a):
    result = -a
    assert result == result.quantize(Decimal("0.01"))


@given(two_dp_money, two_dp_money)
def test_subtraction_preserves_two_decimal_places(a, b):
    result = a - b
    assert result == result.quantize(Decimal("0.01"))


@pytest.mark.xfail(
    strict=True,
    reason="Money serialisation helper not yet implemented — see backend/app/domain/money.py (PLAN §3)",
)
@given(two_dp_money)
def test_money_serialises_as_string(a):
    """API serialisation must emit money as a JSON string with 2 decimal places."""
    from app.domain.money import serialise_money

    out = serialise_money(a)
    assert isinstance(out, str)
    assert out == f"{a:.2f}"
