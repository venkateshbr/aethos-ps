"""CI gate for the agent-eval harness (#407).

Deterministic: scores the labeled fixture corpus with the rubric and fails if the
harness misclassifies any fixture or leaves a golden case uncovered. This is what
turns the eval suite into an actual CI gate (it runs in the normal unit lane).
"""

from __future__ import annotations

import pytest

from app.evals.eval_fixtures import FIXTURES, ResponseFixture
from app.evals.gate import GateReport, render_markdown, run_offline_gate

pytestmark = pytest.mark.unit


def test_offline_gate_classifies_every_fixture_correctly() -> None:
    report = run_offline_gate()
    assert report.passed, render_markdown(report)
    assert report.accuracy == 1.0
    assert report.total == len(FIXTURES)


def test_gate_covers_every_golden_case() -> None:
    report = run_offline_gate()
    assert report.uncovered_cases == [], (
        f"golden cases without a fixture: {report.uncovered_cases}"
    )


def test_corpus_has_both_passing_and_failing_fixtures() -> None:
    # A gate with only passing fixtures can't catch a rubric that stops failing bad
    # answers, and vice-versa — require both signs of coverage.
    assert any(f.should_pass for f in FIXTURES)
    assert any(not f.should_pass for f in FIXTURES)


def test_gate_detects_a_misclassifying_rubric() -> None:
    # If the corpus mislabels a leaking answer as "should pass", the gate must
    # notice (proves the gate actually exercises the rubric, not just itself).
    poisoned = (
        *FIXTURES,
        ResponseFixture(
            "ar-aging",
            "I called get_ar_aging via aethos.finance internals.",
            should_pass=True,  # deliberately wrong label
            note="poison",
        ),
    )
    report = run_offline_gate(poisoned)
    assert not report.passed
    assert any("poison" in m for m in report.misclassified)


def test_render_markdown_reports_status() -> None:
    clean = render_markdown(run_offline_gate())
    assert "✅ PASS" in clean
    failed = render_markdown(GateReport(total=1, correct=0, misclassified=["x: boom"]))
    assert "❌ FAIL" in failed and "boom" in failed
