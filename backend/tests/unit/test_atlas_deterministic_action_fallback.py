from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints import atlas_tools
from app.core.auth import CurrentUser
from app.services.atlas_deterministic_responses import render_semantic_atlas_response

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_semantic_responder_falls_through_for_unmaterialized_actions() -> None:
    response = await render_semantic_atlas_response(
        db=object(),  # type: ignore[arg-type]
        tenant_id="11111111-1111-1111-1111-111111111111",
        current_user=CurrentUser(
            user_id="22222222-2222-2222-2222-222222222222",
            email="owner@example.com",
            role="owner",
        ),
        thread_id="thread-1",
        message=(
            "Prepare a bill-pay run for approved vendor bills due within 7 days. "
            "Use the propose_bill_payment_batch tool and create the Inbox review task."
        ),
    )

    assert response is None


@pytest.mark.asyncio
async def test_semantic_responder_materializes_finance_ops_action_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    ledger = MagicMock()
    ledger.start_run = AsyncMock(return_value="semantic-run-1")
    ledger.record_tool_invocation = AsyncMock()
    ledger.complete_run = AsyncMock()
    monkeypatch.setattr(
        "app.services.atlas_deterministic_responses.AgentRunLedger",
        lambda *_args, **_kwargs: ledger,
    )

    async def _create_action_plan(
        db: object,
        context: object,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        calls.append({"db": db, "context": context, "arguments": arguments})
        return {
            "requires_review": True,
            "suggestion_id": "suggestion-plan-1",
            "action_type": "copilot_create_finance_ops_action_plan",
            "tool_name": "create_finance_ops_action_plan",
            "risk_class": "draft",
            "message": "Created an Inbox review task before applying this change.",
            "approval_boundary": (
                "No invoice, payment, journal, or email was approved, posted, "
                "paid, or sent directly."
            ),
        }

    monkeypatch.setattr(
        atlas_tools,
        "_create_finance_ops_action_plan",
        _create_action_plan,
    )
    db = object()

    response = await render_semantic_atlas_response(
        db=db,  # type: ignore[arg-type]
        tenant_id="11111111-1111-1111-1111-111111111111",
        current_user=CurrentUser(
            user_id="22222222-2222-2222-2222-222222222222",
            email="owner@example.com",
            role="owner",
        ),
        thread_id="thread-1",
        message=(
            "Create the next recommended finance ops work items for 2026-06. "
            "Route the manager action plan to Inbox for review. "
            "Do not approve invoices, payments, journals, or emails directly."
        ),
    )

    assert response is not None
    assert response.route.intent == "finance_ops_action_plan"
    assert "suggestion-plan-1" in response.text
    assert "Inbox" in response.text
    assert "No invoice, payment, journal, or email was approved" in response.text
    assert len(calls) == 1
    assert calls[0]["db"] is db
    context = calls[0]["context"]
    assert context.tenant_id == "11111111-1111-1111-1111-111111111111"
    assert context.user_id == "22222222-2222-2222-2222-222222222222"
    assert context.thread_id == "thread-1"
    assert calls[0]["arguments"] == {"period": "2026-06", "limit": 5}
    ledger.start_run.assert_awaited_once()
    invocation_call = ledger.record_tool_invocation.await_args
    assert invocation_call.args == ("semantic-run-1",)
    invocation = invocation_call.kwargs
    assert invocation["tool_name"] == "create_finance_ops_action_plan"
    assert invocation["risk_class"] == "draft"
    assert invocation["status"] == "skipped"
    assert invocation["input_payload"] == {"period": "2026-06", "limit": 5}
    assert invocation["output_payload"]["suggestion_id"] == "suggestion-plan-1"
    ledger.complete_run.assert_awaited_once_with(
        "semantic-run-1",
        status="succeeded",
        output_payload=invocation["output_payload"],
    )


@pytest.mark.asyncio
async def test_semantic_responder_does_not_claim_action_plan_when_materialization_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fail_to_create_action_plan(
        db: object,
        context: object,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        del db, context, arguments
        raise TimeoutError("Inbox persistence timed out")

    monkeypatch.setattr(
        atlas_tools,
        "_create_finance_ops_action_plan",
        _fail_to_create_action_plan,
    )

    response = await render_semantic_atlas_response(
        db=object(),  # type: ignore[arg-type]
        tenant_id="11111111-1111-1111-1111-111111111111",
        current_user=CurrentUser(
            user_id="22222222-2222-2222-2222-222222222222",
            email="owner@example.com",
            role="owner",
        ),
        thread_id="thread-1",
        message=(
            "Create the next recommended finance ops work items for 2026-06. "
            "Route the manager action plan to Inbox for review. "
            "Do not approve invoices, payments, journals, or emails directly."
        ),
    )

    assert response is not None
    assert "Unable to prepare" in response.text
    assert "no Inbox review artifact was persisted" in response.text
    assert "Created the next recommended" not in response.text


@pytest.mark.asyncio
async def test_semantic_responder_rejects_action_plan_result_without_artifact_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _return_failed_action_plan(
        db: object,
        context: object,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        del db, context, arguments
        return {
            "requires_review": True,
            "suggestion_id": None,
            "action_type": "copilot_create_finance_ops_action_plan",
            "tool_name": "create_finance_ops_action_plan",
            "hitl_routing_failed": True,
            "error": "Inbox task was not persisted",
            "message": "Created an Inbox review task before applying this change.",
        }

    monkeypatch.setattr(
        atlas_tools,
        "_create_finance_ops_action_plan",
        _return_failed_action_plan,
    )

    response = await render_semantic_atlas_response(
        db=object(),  # type: ignore[arg-type]
        tenant_id="11111111-1111-1111-1111-111111111111",
        current_user=CurrentUser(
            user_id="22222222-2222-2222-2222-222222222222",
            email="owner@example.com",
            role="owner",
        ),
        thread_id="thread-1",
        message=(
            "Create the next recommended finance ops work items for 2026-06. "
            "Route the manager action plan to Inbox for review. "
            "Do not approve invoices, payments, journals, or emails directly."
        ),
    )

    assert response is not None
    assert "no Inbox review artifact was persisted" in response.text
    assert "Created an Inbox review task" not in response.text


@pytest.mark.asyncio
async def test_semantic_responder_materializes_exact_time_log_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = MagicMock()
    ledger.start_run = AsyncMock(return_value="semantic-time-run-1")
    ledger.record_tool_invocation = AsyncMock()
    ledger.complete_run = AsyncMock()
    monkeypatch.setattr(
        "app.services.atlas_deterministic_responses.AgentRunLedger",
        lambda *_args, **_kwargs: ledger,
    )
    calls: list[dict[str, object]] = []

    async def _log_time(
        db: object,
        context: object,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        del db, context
        calls.append(arguments)
        return {
            "requires_review": True,
            "suggestion_id": "suggestion-time-1",
            "action_type": "copilot_log_time_entry",
            "tool_name": "log_time_entry",
            "risk_class": "write_low_risk",
            "message": "Created an Inbox review task before applying this change.",
        }

    monkeypatch.setattr(atlas_tools, "_log_time_entry", _log_time)

    response = await render_semantic_atlas_response(
        db=object(),  # type: ignore[arg-type]
        tenant_id="11111111-1111-1111-1111-111111111111",
        current_user=CurrentUser(
            user_id="22222222-2222-2222-2222-222222222222",
            email="owner@example.com",
            role="owner",
        ),
        thread_id="thread-1",
        message=(
            'Log exactly 4.5 billable hours on project "Nexus Advisory" for '
            '2026-07-11. Use this exact description: "Board pack review". '
            "Use the log_time_entry tool and create the review task without "
            "asking a follow-up question."
        ),
    )

    assert response is not None
    assert response.route.intent == "time_log"
    assert response.tool_name == "log_time_entry"
    assert "suggestion-time-1" in response.text
    assert calls == [
        {
            "project_name": "Nexus Advisory",
            "hours": "4.5",
            "date": "2026-07-11",
            "description": "Board pack review",
            "billable": True,
        }
    ]
    invocation_call = ledger.record_tool_invocation.await_args
    assert invocation_call.args == ("semantic-time-run-1",)
    assert invocation_call.kwargs["tool_name"] == "log_time_entry"
    assert invocation_call.kwargs["risk_class"] == "write_low_risk"
    assert invocation_call.kwargs["status"] == "skipped"
    ledger.complete_run.assert_awaited_once_with(
        "semantic-time-run-1",
        status="succeeded",
        output_payload=invocation_call.kwargs["output_payload"],
        error_message=None,
    )
