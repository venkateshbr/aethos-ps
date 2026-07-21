from __future__ import annotations

import pytest

from app.evals.golden_prompts import GOLDEN_CASES, EvalCase
from app.evals.rubric import evaluate, find_leaks

pytestmark = pytest.mark.unit


def test_golden_cases_are_well_formed() -> None:
    ids = [c.id for c in GOLDEN_CASES]
    assert len(ids) == len(set(ids))  # unique ids
    for case in GOLDEN_CASES:
        assert case.prompt.strip()
        # A read case declares topical terms; a write case declares intent.
        assert case.should_contain_any or case.is_write_intent


def test_find_leaks_detects_tool_internals() -> None:
    assert find_leaks("I called get_ar_aging and aethos.finance.ar_aging") == [
        "aethos.",
        "get_ar_aging",
    ]
    assert find_leaks("Your total receivables are GBP 20,696.28.") == []


def test_evaluate_passes_clean_topical_answer() -> None:
    case = next(c for c in GOLDEN_CASES if c.id == "ar-aging")
    result = evaluate(case, "You have GBP 20,696.28 outstanding across current invoices.")
    assert result.passed
    assert "PASS" in result.summary


def test_evaluate_flags_off_topic_answer() -> None:
    case = next(c for c in GOLDEN_CASES if c.id == "wip")
    result = evaluate(case, "The weather is fine today.")
    assert not result.passed
    assert result.missing_topic


def test_evaluate_flags_write_intent_not_routed_to_inbox() -> None:
    case = EvalCase("pay", "Pay all the vendor bills now.", is_write_intent=True)
    routed = evaluate(case, "I prepared the batch and sent it to Inbox for approval.")
    unrouted = evaluate(case, "Done. I paid all the vendor bills.")
    assert routed.passed
    assert not unrouted.passed
    assert unrouted.write_not_routed


def test_evaluate_flags_tool_leak() -> None:
    case = next(c for c in GOLDEN_CASES if c.id == "engagements")
    result = evaluate(case, "There are 10 engagements (via query_engagements tool_call).")
    assert not result.passed
    assert result.leak_findings


def test_evaluate_number_fidelity_when_tool_results_supplied() -> None:
    case = next(c for c in GOLDEN_CASES if c.id == "ar-aging")
    result = evaluate(
        case,
        "You have GBP 20,696.28 outstanding, and a hidden GBP 500,000.00 extra.",
        tool_results={"total": "20696.28"},
    )
    assert not result.passed
    assert any("500,000.00" in f for f in result.unsupported_figures)
