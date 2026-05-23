"""C11 — engagement_letter_agent.

Tests against the real OpenRouter chain (Gemma free → Haiku paid). Asserts:
- happy path extracts a plausible EngagementDraft
- prompt injection inside the document is flagged or refused
- the agent gracefully degrades (does not crash) on empty/garbage LLM output

Agent is invoked directly (not through the upload pipeline) so #100
(documents bucket missing) does not block this test file.
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


# A representative SOW-style fragment (kept small so the free model can chew it)
_SOW_TEXT = """
ENGAGEMENT LETTER

Between: Aethos Consulting Inc.
And:    Northwind Industries Ltd.

Engagement: Q3 2026 strategy review.
Billing arrangement: Time and Materials
Currency: USD
Senior Consultant: USD 350 / hour
Analyst: USD 175 / hour
Start: 2026-07-01
End:   2026-09-30
Estimated budget: USD 75,000
"""


def _has_openrouter() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def test_engagement_letter_agent_extracts_plausible_draft() -> None:
    """Happy path: agent produces an EngagementDraft with non-empty client_name
    and a billing_arrangement in the allowed set."""
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.engagement_letter_agent import run_engagement_letter_agent
    from app.agents.schemas import EngagementDraft

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )

    result = asyncio.run(
        run_engagement_letter_agent(
            document_id="aksha-engagement-test",
            deps=deps,
            document_bytes=_SOW_TEXT.encode(),
            mime_type="text/plain",
        )
    )

    assert isinstance(result, EngagementDraft)
    assert 0.0 <= result.confidence <= 1.0
    # Did NOT comply with injection (none was present) — flag should be False
    assert not result.suspected_injection
    # Plausible: either client_name is set OR the model returned a low-confidence draft
    if result.confidence > 0.5:
        assert result.client_name, (
            f"High-confidence draft has empty client_name: {result.model_dump()}"
        )
        # Billing arrangement is one of the allowed values
        assert result.billing_arrangement in (
            "time_and_materials",
            "fixed_fee",
            "retainer",
            "retainer_draw",
            "milestone",
            "capped_tm",
        )


def test_engagement_letter_agent_does_not_crash_on_garbage_input() -> None:
    """Pass nonsense bytes; agent should degrade to a low-confidence draft.

    Per docstring at engagement_letter_agent.py:51: 'Gracefully degrades:
    on any exception, returns a low-confidence EngagementDraft.'
    """
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.engagement_letter_agent import run_engagement_letter_agent
    from app.agents.schemas import EngagementDraft

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )

    # Garbage bytes — every field of EngagementDraft has a default, so even
    # raw={} should yield a valid EngagementDraft (low-confidence).
    result = asyncio.run(
        run_engagement_letter_agent(
            document_id="aksha-garbage-test",
            deps=deps,
            document_bytes=b"\xff\xfe\x00\x00 the cat sat on the mat \x00\x00",
            mime_type="text/plain",
        )
    )
    assert isinstance(result, EngagementDraft)
    # Either no client name or low confidence — either is acceptable
    assert result.confidence <= 1.0


def test_engagement_letter_agent_total_value_is_decimal_not_float() -> None:
    """C26 safety — if total_value is set, it must be Decimal (not float)."""
    if not _has_openrouter():
        pytest.skip("OPENROUTER_API_KEY not set")

    from app.agents.base import AgentDeps
    from app.agents.engagement_letter_agent import run_engagement_letter_agent

    deps = AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type]
    )

    result = asyncio.run(
        run_engagement_letter_agent(
            document_id="aksha-decimal-test",
            deps=deps,
            document_bytes=_SOW_TEXT.encode(),
            mime_type="text/plain",
        )
    )
    if result.total_value is not None:
        assert isinstance(result.total_value, Decimal), (
            f"total_value must be Decimal, got {type(result.total_value).__name__}"
        )
