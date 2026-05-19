"""Placeholder unit test so the suite runs end-to-end on a fresh checkout.

Delete this file when real unit tests land (likely backend/app/domain/money.py
and backend/app/domain/journal.py).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

pytestmark = pytest.mark.unit


def test_decimal_arithmetic_does_not_drift():
    """Sanity: pure Python Decimal does not lose precision."""
    assert Decimal("10.10") + Decimal("20.20") == Decimal("30.30")


def test_decimal_serialises_as_string():
    """The way we will eventually serialise money."""
    assert f"{Decimal('30.3'):.2f}" == "30.30"
