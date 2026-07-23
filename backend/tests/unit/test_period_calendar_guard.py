"""#379 AC 1 — a period can only be locked once its calendar month has ended."""

from __future__ import annotations

from datetime import date

import pytest

from app.api.v1.endpoints.accounting import _period_has_ended

pytestmark = pytest.mark.unit


def test_fully_elapsed_period_has_ended() -> None:
    assert _period_has_ended("2026-06", today=date(2026, 7, 1)) is True
    assert _period_has_ended("2026-06", today=date(2027, 1, 1)) is True
    assert _period_has_ended("2026-12", today=date(2027, 1, 1)) is True


def test_current_or_future_period_has_not_ended() -> None:
    # Last day of the month is still within the period → not ended.
    assert _period_has_ended("2026-06", today=date(2026, 6, 30)) is False
    assert _period_has_ended("2026-06", today=date(2026, 6, 1)) is False
    assert _period_has_ended("2026-07", today=date(2026, 6, 30)) is False
    assert _period_has_ended("2027-01", today=date(2026, 6, 30)) is False


def test_december_rolls_to_next_year() -> None:
    assert _period_has_ended("2026-12", today=date(2026, 12, 31)) is False
    assert _period_has_ended("2026-12", today=date(2027, 1, 1)) is True
