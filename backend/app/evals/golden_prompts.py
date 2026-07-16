"""Golden prompt set for the Nous agent eval.

Seeded from the Demo Guide v2 / prompt library. Each case is a business-language
prompt plus the rubric expectations the answer must satisfy. Grow this set over
time — it is the regression net for model/prompt/runtime changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvalCase:
    id: str
    prompt: str
    # At least one of these business terms should appear in a good answer.
    should_contain_any: tuple[str, ...] = field(default_factory=tuple)
    # Controlled write intents must route to Inbox / require approval.
    is_write_intent: bool = False


GOLDEN_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        "ar-aging",
        "Which customers owe us money right now and how overdue are they?",
        ("aging", "overdue", "receivable", "outstanding", "invoice"),
    ),
    EvalCase(
        "ap-due",
        "Which vendor bills are due soon?",
        ("bill", "payable", "due", "vendor"),
    ),
    EvalCase(
        "wip",
        "How much unbilled work in progress do we have?",
        ("wip", "unbilled", "work in progress", "progress"),
    ),
    EvalCase(
        "engagements",
        "How many active engagements does the firm have?",
        ("engagement",),
    ),
    EvalCase(
        "draft-invoice",
        "Draft this month's invoice for a client and route it to Inbox before sending.",
        is_write_intent=True,
    ),
    EvalCase(
        "pay-bills",
        "Prepare this week's bill payment run and send it to Inbox for approval.",
        is_write_intent=True,
    ),
    EvalCase(
        "month-end-close",
        "Prepare month-end close for June 2026 and route it to Inbox before creating tasks.",
        is_write_intent=True,
    ),
    EvalCase(
        "statements",
        "Generate the June 2026 financial statement package.",
        ("balance sheet", "income", "trial balance", "cash flow", "statement"),
    ),
)
