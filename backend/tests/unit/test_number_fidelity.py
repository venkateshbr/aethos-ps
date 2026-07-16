from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.number_fidelity import (
    collect_supported_amounts,
    extract_money_figures,
    fidelity_caveat,
    unsupported_money_figures,
)

pytestmark = pytest.mark.unit


def test_extract_money_figures_finds_currency_and_shaped_numbers() -> None:
    text = "AR aging is £20,696.28 across 12 invoices; one is USD 4,500.00 and paid 30 days late."
    figures = extract_money_figures(text)
    joined = " ".join(figures)
    assert "20,696.28" in joined
    assert "4,500.00" in joined


def test_extract_money_ignores_plain_counts_and_percentages() -> None:
    text = "There are 12 invoices, utilization is 64% and it is 30 days overdue."
    # None of these are money-shaped (no currency, no thousands sep, no 2dp).
    assert extract_money_figures(text) == []


def test_collect_supported_amounts_walks_nested_json_and_strings() -> None:
    tool_results = {
        "ar_aging": {"total": "20696.28", "buckets": [{"amount": 4500.0}]},
        "count": 12,
        "flag": True,
    }
    supported = collect_supported_amounts(tool_results)
    assert Decimal("20696.28") in supported
    assert Decimal("4500.00") in supported
    assert Decimal("12.00") in supported
    # bool must never be treated as a money value
    assert Decimal("1.00") not in supported


def test_supported_figure_passes_with_thousands_formatting() -> None:
    answer = "Your AR total is £20,696.28."
    tool_results = {"total": "20696.28"}
    assert unsupported_money_figures(answer, tool_results) == []


def test_hallucinated_figure_is_flagged() -> None:
    answer = "Your AR total is £20,696.28 and profit was £999,999.99."
    tool_results = {"total": "20696.28"}
    unsupported = unsupported_money_figures(answer, tool_results)
    assert any("999,999.99" in f for f in unsupported)
    assert all("20,696.28" not in f for f in unsupported)


def test_fidelity_caveat_lists_unverified_and_is_safe() -> None:
    caveat = fidelity_caveat(["£999,999.99"])
    assert "999,999.99" in caveat
    assert "confirm" in caveat.lower()
    # No internal/tool language leaks into the user-facing caveat.
    assert "tool" not in caveat.lower()


def test_fidelity_caveat_empty_when_all_supported() -> None:
    assert fidelity_caveat([]) == ""
