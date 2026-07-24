"""Offline agent-eval gate + drift report (#407).

Scores the labeled ``eval_fixtures`` corpus with the deterministic rubric and
reports whether the harness still classifies every fixture as labeled. Runs with
no LLM/network, so it can gate CI (see tests/unit/test_eval_gate.py and
scripts/agent_eval_gate.py). The gate guards the *scoring* the live eval depends
on; real model/agent drift is measured by the opt-in live eval.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.evals.eval_fixtures import FIXTURES, ResponseFixture
from app.evals.golden_prompts import GOLDEN_CASES, EvalCase
from app.evals.rubric import evaluate

_CASES: dict[str, EvalCase] = {c.id: c for c in GOLDEN_CASES}


@dataclass
class GateReport:
    total: int = 0
    correct: int = 0
    misclassified: list[str] = field(default_factory=list)
    uncovered_cases: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return 1.0 if self.total == 0 else self.correct / self.total

    @property
    def passed(self) -> bool:
        # The deterministic harness must classify EVERY labeled fixture correctly
        # and every golden case must have at least one fixture.
        return not self.misclassified and not self.uncovered_cases


def _classify(fixture: ResponseFixture) -> bool:
    case = _CASES.get(fixture.case_id)
    if case is None:
        raise KeyError(f"fixture references unknown golden case {fixture.case_id!r}")
    return evaluate(case, fixture.answer).passed


def run_offline_gate(fixtures: tuple[ResponseFixture, ...] = FIXTURES) -> GateReport:
    report = GateReport()
    for fx in fixtures:
        report.total += 1
        actual = _classify(fx)
        if actual == fx.should_pass:
            report.correct += 1
        else:
            report.misclassified.append(
                f"{fx.case_id}: expected {'PASS' if fx.should_pass else 'FAIL'} "
                f"but rubric said {'PASS' if actual else 'FAIL'} — {fx.note or 'no note'}"
            )
    covered = {fx.case_id for fx in fixtures}
    report.uncovered_cases = sorted(c.id for c in GOLDEN_CASES if c.id not in covered)
    return report


def render_markdown(report: GateReport) -> str:
    """Render a small drift dashboard for CI logs / an uploaded artifact."""
    status = "✅ PASS" if report.passed else "❌ FAIL"
    lines = [
        "# Agent-eval offline gate",
        "",
        f"- Result: **{status}**",
        f"- Fixtures classified correctly: **{report.correct}/{report.total}** "
        f"({report.accuracy * 100:.1f}%)",
        f"- Golden cases covered: **{len(GOLDEN_CASES) - len(report.uncovered_cases)}"
        f"/{len(GOLDEN_CASES)}**",
    ]
    if report.uncovered_cases:
        lines.append(f"- ⚠️ Uncovered cases: {', '.join(report.uncovered_cases)}")
    if report.misclassified:
        lines.append("")
        lines.append("## Misclassifications")
        lines.extend(f"- {m}" for m in report.misclassified)
    return "\n".join(lines) + "\n"
