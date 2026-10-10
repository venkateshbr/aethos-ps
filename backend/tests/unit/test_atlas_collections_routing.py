"""Regression coverage for collections prompts reaching write-capable Copilot tools."""

from __future__ import annotations

import pytest

from app.core.auth import CurrentUser
from app.services.atlas_deterministic_responses import render_semantic_atlas_response
from app.services.atlas_semantic_intent_router import AtlasSemanticIntentRouter

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_draft_collections_prompt_falls_through_to_copilot_tool_runtime() -> None:
    """Draft/send-email requests must not be consumed by the read-only responder."""
    prompt = (
        "Draft collections reminders for invoices more than 30 days overdue. "
        "Use the draft_collection_reminders tool with minimum_days_overdue 30 and limit 10. "
        "Set client_name to \"Copilot Collections Customer abc123 [E2E]\" so only this E2E customer is considered. "
        "Create Inbox review tasks only. Do not send any email without review."
    )

    route = AtlasSemanticIntentRouter().classify(prompt)

    assert route is not None
    assert route.intent == "collections"
    assert route.action_mode == "prepare"
    assert await render_semantic_atlas_response(
        db=object(),  # type: ignore[arg-type]
        tenant_id="tenant-abc",
        current_user=CurrentUser(
            user_id="user-001",
            email="user@example.test",
            role="authenticated",
        ),
        thread_id="thread-001",
        message=prompt,
    ) is None
