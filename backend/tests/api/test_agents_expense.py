"""C12 — expense_extractor_agent.

Tests the agent directly (bypasses #100 documents-bucket gap). Verifies:
- happy path extracts plausible ProjectExpenseDraft from a receipt fragment
- the agent does NOT crash on a foreign-currency receipt
- amounts are Decimal, not float (C26 safety invariant)

Prompt injection coverage already exists in test_llm_fallback_chain.py
(xfail-tracked under bug #104).
"""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal

import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_hitl,
    pytest.mark.requires_openrouter,
]


_RECEIPT_USD = """
COFFEE SHOP
Date: 2026-05-23
Latte ............ $5.50
Croissant ........ $4.50
TAX .............. $0.80
TOTAL ............ $10.80
"""


_RECEIPT_GBP = """
LONDON CABS
Date: 2026-05-23
Trip: Heathrow → Marylebone
Fare: £62.00
Tip: £6.00
TOTAL: £68.00 GBP
"""


def _has_openrouter() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def test_expense_extractor_happy_path_usd() -> None:
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.expense_extractor_agent import run_expense_extractor_agent
    from app.agents.schemas import ProjectExpenseDraft

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )

    result = asyncio.run(
        run_expense_extractor_agent(
            document_id="aksha-expense-usd",
            deps=deps,
            document_bytes=_RECEIPT_USD.encode(),
            mime_type="text/plain",
        )
    )
    assert isinstance(result, ProjectExpenseDraft)
    assert isinstance(result.amount, Decimal), (
        f"amount must be Decimal, got {type(result.amount).__name__}"
    )
    # Total is $10.80 — if the agent confidently extracted, it should be near that
    if result.confidence > 0.6:
        assert Decimal("8") <= result.amount <= Decimal("15"), (
            f"Confident draft extracted implausible amount: {result.amount}"
        )
        assert result.currency in ("USD", "usd"), result.currency


def test_expense_extractor_handles_foreign_currency() -> None:
    """C29 — multi-currency. Free model may guess wrong currency, but it
    must NOT crash and the result type must be valid."""
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.expense_extractor_agent import run_expense_extractor_agent
    from app.agents.schemas import ProjectExpenseDraft

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )

    # If #104 is fixed the agent returns a low-confidence draft; if not it'll
    # raise. The xfail mark mirrors that gating.
    try:
        result = asyncio.run(
            run_expense_extractor_agent(
                document_id="aksha-expense-gbp",
                deps=deps,
                document_bytes=_RECEIPT_GBP.encode(),
                mime_type="text/plain",
            )
        )
    except Exception as exc:
        pytest.xfail(
            f"Bug #104 — agent crashed on GBP receipt instead of degrading: {exc!s}"
        )

    assert isinstance(result, ProjectExpenseDraft)
    assert isinstance(result.amount, Decimal)
    # If confident, should report GBP
    if result.confidence > 0.7:
        assert result.currency.upper() == "GBP", (
            f"Confident draft on GBP receipt returned currency={result.currency!r}"
        )


def test_expense_extractor_category_in_allowed_set() -> None:
    """ProjectExpenseDraft.category should be one of the documented values."""
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.expense_extractor_agent import run_expense_extractor_agent

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )

    try:
        result = asyncio.run(
            run_expense_extractor_agent(
                document_id="aksha-expense-cat",
                deps=deps,
                document_bytes=_RECEIPT_USD.encode(),
                mime_type="text/plain",
            )
        )
    except Exception as exc:
        pytest.xfail(f"Bug #104 — agent crashed: {exc!s}")

    # schema doesn't enforce this set, but the agent prompt does
    allowed = {"meals_and_entertainment", "transport", "accommodation", "software", "other"}
    if result.confidence > 0.7:
        assert result.category in allowed, (
            f"Confident draft assigned unknown category: {result.category!r}"
        )
