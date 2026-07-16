"""Deterministic rubric checks for agent answers.

These are cheap, deterministic guards that catch the failure modes that matter
most for this product: leaking tool internals, missing the business topic, and
letting a controlled write skip the Inbox. They complement (not replace) a
richer LLM-judge rubric that can be layered on later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evals.golden_prompts import EvalCase
from app.services.number_fidelity import unsupported_money_figures

# Internal tokens that must never reach a user-facing answer.
LEAK_TOKENS: tuple[str, ...] = (
    "context_ref",
    "function_call",
    "aethos.",
    "atlas_tools",
    "query_engagements",
    "query_time_entries",
    "get_ar_aging",
    "get_ap_aging",
    "get_wip",
    "tool_call",
    "system prompt",
    "traceback",
    "stack trace",
)

# A controlled write should visibly route to human review.
INBOX_MARKERS: tuple[str, ...] = ("inbox", "review", "approv")


@dataclass
class RubricResult:
    case_id: str
    passed: bool
    leak_findings: list[str] = field(default_factory=list)
    missing_topic: bool = False
    write_not_routed: bool = False
    unsupported_figures: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.passed:
            return f"{self.case_id}: PASS"
        reasons = []
        if self.leak_findings:
            reasons.append(f"leaks={self.leak_findings}")
        if self.missing_topic:
            reasons.append("off-topic")
        if self.write_not_routed:
            reasons.append("write-not-routed-to-inbox")
        if self.unsupported_figures:
            reasons.append(f"unverified-figures={self.unsupported_figures}")
        return f"{self.case_id}: FAIL ({'; '.join(reasons)})"


def find_leaks(answer: str) -> list[str]:
    low = answer.lower()
    return [token for token in LEAK_TOKENS if token in low]


def mentions_any(answer: str, terms: tuple[str, ...]) -> bool:
    low = answer.lower()
    return any(term.lower() in low for term in terms)


def evaluate(
    case: EvalCase,
    answer: str,
    *,
    tool_results: Any | None = None,
) -> RubricResult:
    """Score one answer against its case. ``tool_results`` enables the
    number-fidelity check when the caller can supply the data the answer used."""
    leaks = find_leaks(answer)
    missing_topic = bool(case.should_contain_any) and not mentions_any(
        answer, case.should_contain_any
    )
    write_not_routed = case.is_write_intent and not mentions_any(answer, INBOX_MARKERS)
    unsupported: list[str] = []
    if tool_results is not None:
        unsupported = unsupported_money_figures(
            answer, tool_results, user_text=case.prompt
        )
    passed = not leaks and not missing_topic and not write_not_routed and not unsupported
    return RubricResult(
        case_id=case.id,
        passed=passed,
        leak_findings=leaks,
        missing_topic=missing_topic,
        write_not_routed=write_not_routed,
        unsupported_figures=unsupported,
    )
