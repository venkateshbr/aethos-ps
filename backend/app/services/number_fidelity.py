"""Number-fidelity verification for agent answers.

The agents must never invent financial figures. This module provides a
deterministic post-hoc check: given an assistant answer and the tool results
that produced it, it flags any *monetary* figure in the answer that no tool
result supports (within one cent). It is defence-in-depth around the prompt
rule, not a replacement for it — the goal is to catch a hallucinated total
before it reaches a user, or append a visible caveat.

Design choices:
* Only currency-qualified or money-shaped numbers are checked, so plain counts
  ("12 invoices", "30 days", "89%") never trip the guard.
* Supported values are collected recursively from arbitrary tool-result JSON,
  including money serialised as strings (the app's convention).
* Matching is on rounded cents so ``3560.28`` supports ``£3,560.28``.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

_CENTS = Decimal("0.01")

# A money-shaped amount: thousands-separated, or a plain integer/decimal.
_AMOUNT = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d{1,2})?"

# Currency-qualified figure: a symbol or ISO code immediately before the amount.
_CURRENCY_MONEY_RE = re.compile(
    rf"(?:[£$€₹]|\b(?:GBP|USD|EUR|SGD|INR|AUD)\b)\s*(?P<amount>{_AMOUNT})",
    re.IGNORECASE,
)
# A number that is money-shaped on its own: has thousands separators or exactly
# two decimal places. Bare integers and single-decimal numbers are ignored to
# avoid flagging counts, hours, or percentages.
_MONEY_SHAPED_RE = re.compile(
    r"(?<![\w.])(?P<amount>\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+\.\d{2})(?![\w.])"
)


def _to_cents(value: str | int | float | Decimal) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", "").strip()).quantize(_CENTS)
    except (InvalidOperation, ValueError, TypeError):
        return None


def extract_money_figures(text: str) -> list[str]:
    """Return the distinct money-like figure substrings mentioned in ``text``."""
    seen: dict[Decimal, str] = {}
    for match in _CURRENCY_MONEY_RE.finditer(text):
        amount = _to_cents(match.group("amount"))
        if amount is not None and amount not in seen:
            seen[amount] = match.group(0).strip()
    for match in _MONEY_SHAPED_RE.finditer(text):
        amount = _to_cents(match.group("amount"))
        if amount is not None and amount not in seen:
            seen[amount] = match.group("amount")
    return list(seen.values())


def collect_supported_amounts(tool_results: Any) -> set[Decimal]:
    """Recursively collect every numeric value from tool-result data as cents."""
    supported: set[Decimal] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                _walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                _walk(value)
        elif isinstance(node, bool):
            return  # bool is an int subclass — never a money value
        elif isinstance(node, (int, float, Decimal)):
            cents = _to_cents(node)
            if cents is not None:
                supported.add(cents)
        elif isinstance(node, str):
            cents = _to_cents(node)
            if cents is not None:
                supported.add(cents)

    _walk(tool_results)
    return supported


def unsupported_money_figures(
    answer: str,
    tool_results: Any,
    *,
    user_text: str = "",
) -> list[str]:
    """Return money figures stated in ``answer`` that no tool result supports.

    Figures the user supplied in ``user_text`` are treated as supported, so the
    agent restating a number the user gave (e.g. a quoted fee) is not flagged.
    """
    supported = collect_supported_amounts(tool_results)
    for figure in extract_money_figures(user_text):
        cents = _to_cents(_strip_currency(figure))
        if cents is not None:
            supported.add(cents)
    unsupported: list[str] = []
    for figure in extract_money_figures(answer):
        cents = _to_cents(_strip_currency(figure))
        if cents is None:
            continue
        if cents not in supported:
            unsupported.append(figure)
    return unsupported


def _strip_currency(figure: str) -> str:
    return re.sub(r"[£$€₹]|\b(?:GBP|USD|EUR|SGD|INR|AUD)\b", "", figure, flags=re.IGNORECASE)


def fidelity_caveat(unsupported: list[str]) -> str:
    """A short, user-safe caveat listing unverifiable figures (no internals)."""
    if not unsupported:
        return ""
    figures = ", ".join(unsupported)
    return (
        "\n\nNote: I could not verify these figures against current records "
        f"({figures}). Please confirm them against Reports before relying on them."
    )
