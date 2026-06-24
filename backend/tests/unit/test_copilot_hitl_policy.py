"""Tests for Copilot write-tool HITL routing and materialisation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.rbac import UserRole
from app.services.agent_tool_policy import AgentToolPolicyDecision


class _StaticPolicy:
    def __init__(self, decision: AgentToolPolicyDecision) -> None:
        self.decision = decision

    async def decide(self, **_kwargs: object) -> AgentToolPolicyDecision:
        return self.decision


class _FailingPolicy:
    async def decide(self, **_kwargs: object) -> AgentToolPolicyDecision:
        raise AssertionError("policy should not run for unknown tool names")


def _make_agent():
    from app.agents.copilot.graph import CopilotAgent, CopilotDeps

    with patch("app.agents.copilot.graph.make_async_llm_client", return_value=MagicMock()):
        return CopilotAgent(
            CopilotDeps(
                tenant_id="tenant-abc",
                user_id="00000000-0000-0000-0000-000000000001",
                db_client=MagicMock(),
            )
        )


@pytest.mark.asyncio
async def test_read_only_policy_executes_tool_directly() -> None:
    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=True,
            route_to_hitl=False,
            reason="read_only_tool",
            user_role=UserRole.viewer,
            minimum_role=UserRole.viewer,
            autonomy_level=2,
        )
    )
    agent._execute_tool = AsyncMock(return_value={"count": 0, "engagements": []})

    result = await agent._execute_tool_with_policy("query_engagements", {"limit": 3})

    assert result == {"count": 0, "engagements": []}
    agent._execute_tool.assert_awaited_once_with("query_engagements", {"limit": 3})


@pytest.mark.asyncio
async def test_unknown_tool_bypasses_policy_and_returns_dispatch_error() -> None:
    agent = _make_agent()
    agent.tool_policy = _FailingPolicy()

    result = await agent._execute_tool_with_policy("not_a_real_tool", {})

    assert result == {"error": "Unknown tool: not_a_real_tool"}


@pytest.mark.asyncio
async def test_write_policy_routes_to_hitl_without_executing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.copilot import graph

    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="write_tool_requires_human_review",
            user_role=UserRole.manager,
            minimum_role=UserRole.manager,
            autonomy_level=2,
        )
    )
    agent._execute_tool = AsyncMock(return_value={"updated": True})
    write_suggestion = AsyncMock(return_value={"id": "sug-123"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "update_rate_card",
        {"employee_name": "Sarah", "rate": 425},
    )

    assert result["requires_review"] is True
    assert result["suggestion_id"] == "sug-123"
    assert result["action_type"] == "copilot_update_rate_card"
    assert result["risk_class"] == "write_money_in"
    agent._execute_tool.assert_not_awaited()
    write_suggestion.assert_awaited_once()
    suggestion_kwargs = write_suggestion.await_args.kwargs
    assert suggestion_kwargs["agent_name"] == "copilot_agent"
    assert suggestion_kwargs["confidence"] == 0.0
    assert suggestion_kwargs["autonomy_level"] == 2
    assert suggestion_kwargs["output"]["tool_input"] == {
        "employee_name": "Sarah",
        "rate": 425,
    }


@pytest.mark.asyncio
async def test_draft_invoice_policy_routes_to_hitl_with_review_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="write_money_in_requires_human_review",
            user_role=UserRole.manager,
            minimum_role=UserRole.manager,
            autonomy_level=2,
        )
    )
    review_payload = {
        "invoice_draft": {
            "engagement_id": "eng-1",
            "engagement_name": "Northstar Managed Accounting",
            "client_id": "client-1",
            "currency": "USD",
            "issue_date": "2026-06-30",
            "lines": [
                {
                    "description": "Monthly retainer",
                    "quantity": "1",
                    "unit_price": "12000.00",
                }
            ],
        },
        "preview": {
            "engagement": "Northstar Managed Accounting",
            "currency": "USD",
            "total": "12000.00",
            "line_count": 1,
        },
    }
    agent._build_invoice_draft_payload = AsyncMock(return_value=review_payload)  # type: ignore[method-assign]
    agent._execute_tool = AsyncMock(return_value={"invoice_created": True})
    write_suggestion = AsyncMock(return_value={"id": "sug-invoice-1"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "draft_invoice",
        {"engagement_name": "Northstar", "period_end": "2026-06-30"},
    )

    assert result["requires_review"] is True
    assert result["suggestion_id"] == "sug-invoice-1"
    assert result["action_type"] == "copilot_draft_invoice"
    assert result["risk_class"] == "write_money_in"
    agent._execute_tool.assert_not_awaited()
    agent._build_invoice_draft_payload.assert_awaited_once()
    suggestion_kwargs = write_suggestion.await_args.kwargs
    assert suggestion_kwargs["output"]["tool_name"] == "draft_invoice"
    assert suggestion_kwargs["output"]["tool_input"] == {
        "engagement_name": "Northstar",
        "period_end": "2026-06-30",
    }
    assert suggestion_kwargs["output"]["invoice_draft"] == review_payload["invoice_draft"]
    assert suggestion_kwargs["output"]["preview"] == review_payload["preview"]


@pytest.mark.asyncio
async def test_draft_invoice_policy_returns_error_without_hitl_when_no_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="write_money_in_requires_human_review",
            user_role=UserRole.manager,
            minimum_role=UserRole.manager,
            autonomy_level=2,
        )
    )
    agent._build_invoice_draft_payload = AsyncMock(  # type: ignore[method-assign]
        return_value={"error": "No invoiceable lines were found"}
    )
    write_suggestion = AsyncMock(return_value={"id": "sug-should-not-exist"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "draft_invoice",
        {"engagement_name": "Northstar"},
    )

    assert result == {
        "error": "No invoiceable lines were found",
        "tool_name": "draft_invoice",
        "risk_class": "write_money_in",
    }
    write_suggestion.assert_not_awaited()


@pytest.mark.asyncio
async def test_bill_pay_policy_routes_to_hitl_with_review_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="write_money_out_requires_human_review",
            user_role=UserRole.admin,
            minimum_role=UserRole.admin,
            autonomy_level=2,
        )
    )
    review_payload = {
        "proposed_bill_ids": ["bill-1", "bill-2"],
        "proposed_pay_date": "2026-06-30",
        "total_amount": "3000.00",
        "currency": "USD",
        "rationale": "Two approved bills are due.",
        "preview": {
            "bill_count": 2,
            "currency": "USD",
            "total": "3000.00",
            "proposed_pay_date": "2026-06-30",
        },
    }
    agent._build_bill_payment_batch_payload = AsyncMock(return_value=review_payload)  # type: ignore[method-assign]
    agent._execute_tool = AsyncMock(return_value={"created": True})
    write_suggestion = AsyncMock(return_value={"id": "sug-bill-pay-1"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "propose_bill_payment_batch",
        {"due_within_days": 7},
    )

    assert result["requires_review"] is True
    assert result["suggestion_id"] == "sug-bill-pay-1"
    assert result["action_type"] == "create_bill_payment_batch"
    assert result["risk_class"] == "write_money_out"
    agent._execute_tool.assert_not_awaited()
    suggestion_kwargs = write_suggestion.await_args.kwargs
    assert suggestion_kwargs["agent_name"] == "copilot_agent"
    assert suggestion_kwargs["action_type"] == "create_bill_payment_batch"
    assert suggestion_kwargs["output"]["tool_name"] == "propose_bill_payment_batch"
    assert suggestion_kwargs["output"]["proposed_bill_ids"] == ["bill-1", "bill-2"]
    assert suggestion_kwargs["output"]["preview"] == review_payload["preview"]


@pytest.mark.asyncio
async def test_bill_pay_policy_suppresses_duplicate_review_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="write_money_out_requires_human_review",
            user_role=UserRole.admin,
            minimum_role=UserRole.admin,
            autonomy_level=2,
        )
    )
    agent._build_bill_payment_batch_payload = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "proposed_bill_ids": ["bill-1"],
            "duplicate_suggestion_id": "sug-existing",
        }
    )
    write_suggestion = AsyncMock(return_value={"id": "sug-should-not-exist"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "propose_bill_payment_batch",
        {"due_within_days": 7},
    )

    assert result["requires_review"] is True
    assert result["suggestion_id"] == "sug-existing"
    assert result["duplicate_suppressed"] is True
    write_suggestion.assert_not_awaited()


@pytest.mark.asyncio
async def test_collections_policy_routes_to_collections_inbox_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="write_money_in_requires_human_review",
            user_role=UserRole.manager,
            minimum_role=UserRole.manager,
            autonomy_level=2,
        )
    )
    agent._draft_collection_reminders = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "requires_review": True,
            "target_agent": "collections_agent",
            "action_type": "send_email",
            "created_review_tasks": 2,
        }
    )
    write_suggestion = AsyncMock(return_value={"id": "sug-should-not-exist"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "draft_collection_reminders",
        {"minimum_days_overdue": 30},
    )

    assert result["requires_review"] is True
    assert result["target_agent"] == "collections_agent"
    assert result["action_type"] == "send_email"
    assert result["created_review_tasks"] == 2
    agent._draft_collection_reminders.assert_awaited_once_with(
        {"minimum_days_overdue": 30}
    )
    write_suggestion.assert_not_awaited()


@pytest.mark.asyncio
async def test_month_end_close_policy_routes_to_hitl_with_review_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="accounting_requires_human_review",
            user_role=UserRole.admin,
            minimum_role=UserRole.admin,
            autonomy_level=2,
        )
    )
    review_payload = {
        "period": "2026-06",
        "preview": {
            "period": "2026-06",
            "workflow": "month_end_close",
            "pending_review_count": 3,
        },
        "close_status": {"period": "2026-06"},
    }
    agent._build_month_end_close_review_payload = AsyncMock(return_value=review_payload)  # type: ignore[method-assign]
    agent._execute_tool = AsyncMock(return_value={"close_prepared": True})
    write_suggestion = AsyncMock(return_value={"id": "sug-close-1"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "prepare_month_end_close",
        {"period": "2026-06"},
    )

    assert result["requires_review"] is True
    assert result["suggestion_id"] == "sug-close-1"
    assert result["action_type"] == "copilot_prepare_month_end_close"
    assert result["risk_class"] == "accounting"
    agent._execute_tool.assert_not_awaited()
    suggestion_kwargs = write_suggestion.await_args.kwargs
    assert suggestion_kwargs["output"]["tool_name"] == "prepare_month_end_close"
    assert suggestion_kwargs["output"]["period"] == "2026-06"
    assert suggestion_kwargs["output"]["preview"] == review_payload["preview"]


@pytest.mark.asyncio
async def test_finance_ops_action_plan_policy_routes_to_hitl_with_plan_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph

    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="draft_tool_requires_human_review",
            user_role=UserRole.admin,
            minimum_role=UserRole.member,
            autonomy_level=2,
        )
    )
    plan_payload = {
        "finance_ops_action_plan": True,
        "plan_id": "finance-ops-plan-1",
        "period": "2026-06",
        "action_count": 2,
        "requires_inbox_approval_count": 2,
        "action_items": [
            {
                "domain": "ar",
                "recommendation": "Draft reminders.",
                "suggested_tool": "send_email",
                "risk_class": "write_money_in",
                "requires_inbox_approval": True,
                "rationale": "AR aging total is 1000.00.",
                "review_path": "/app/inbox",
            }
        ],
        "preview": {
            "period": "2026-06",
            "status": "ready_for_review",
            "action_count": 2,
            "requires_inbox_approval_count": 2,
            "domains": "ar, wip",
        },
    }
    agent._build_finance_ops_action_plan_payload = AsyncMock(  # type: ignore[method-assign]
        return_value=plan_payload
    )
    agent._execute_tool = AsyncMock(return_value={"should_not_execute": True})
    write_suggestion = AsyncMock(return_value={"id": "sug-plan-1"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "create_finance_ops_action_plan",
        {"period": "2026-06", "limit": 5},
    )

    assert result["requires_review"] is True
    assert result["suggestion_id"] == "sug-plan-1"
    assert result["action_type"] == "copilot_create_finance_ops_action_plan"
    assert result["risk_class"] == "draft"
    agent._execute_tool.assert_not_awaited()
    suggestion_kwargs = write_suggestion.await_args.kwargs
    assert suggestion_kwargs["action_type"] == "copilot_create_finance_ops_action_plan"
    assert suggestion_kwargs["output"]["tool_name"] == "create_finance_ops_action_plan"
    assert suggestion_kwargs["output"]["finance_ops_action_plan"] is True
    assert suggestion_kwargs["output"]["preview"] == plan_payload["preview"]


@pytest.mark.asyncio
async def test_policy_denial_returns_structured_error() -> None:
    agent = _make_agent()
    agent.tool_policy = _StaticPolicy(
        AgentToolPolicyDecision(
            allowed=False,
            execute_now=False,
            route_to_hitl=False,
            reason="update_rate_card requires manager or higher; current role is member",
            user_role=UserRole.member,
            minimum_role=UserRole.manager,
            autonomy_level=2,
        )
    )

    result = await agent._execute_tool_with_policy("update_rate_card", {"rate": 425})

    assert result["policy_denied"] is True
    assert result["minimum_role"] == "manager"
    assert result["user_role"] == "member"


@pytest.mark.asyncio
async def test_inbox_materialises_copilot_log_time_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda: MagicMock())
    execute_tool = AsyncMock(return_value={"logged": True, "entry_id": "te-1"})
    monkeypatch.setattr(graph.CopilotAgent, "_execute_tool", execute_tool)

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    result = await svc._materialise_copilot_tool(
        {
            "tool_name": "log_time_entry",
            "tool_input": {"project_name": "Nexus", "hours": 2},
            "requested_by_user_id": "user-1",
        }
    )

    assert result == {"entity_type": "time_entry", "entity_id": "te-1"}
    execute_tool.assert_awaited_once_with(
        "log_time_entry",
        {"project_name": "Nexus", "hours": 2},
    )


@pytest.mark.asyncio
async def test_inbox_materialises_copilot_draft_invoice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda: MagicMock())
    persist_draft = AsyncMock(
        return_value={
            "invoice_created": True,
            "invoice_id": "inv-1",
            "invoice_number": "INV-0001",
        }
    )
    execute_tool = AsyncMock(return_value={"invoice_created": True})
    monkeypatch.setattr(graph.CopilotAgent, "_persist_invoice_draft_payload", persist_draft)
    monkeypatch.setattr(graph.CopilotAgent, "_execute_tool", execute_tool)

    payload = {
        "tool_name": "draft_invoice",
        "tool_input": {"engagement_name": "Northstar"},
        "requested_by_user_id": "user-1",
        "invoice_draft": {
            "engagement_id": "eng-1",
            "client_id": "client-1",
            "currency": "USD",
            "issue_date": "2026-06-30",
            "lines": [
                {
                    "description": "Monthly retainer",
                    "quantity": "1",
                    "unit_price": "12000.00",
                }
            ],
        },
    }

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    result = await svc._materialise_copilot_tool(payload)

    assert result == {"entity_type": "invoice", "entity_id": "inv-1"}
    persist_draft.assert_awaited_once_with(payload["invoice_draft"])
    execute_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_inbox_materialises_copilot_month_end_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda: MagicMock())
    execute_tool = AsyncMock(
        return_value={
            "close_prepared": True,
            "period": "2026-06",
            "workflow_status": "waiting_on_human",
        }
    )
    monkeypatch.setattr(graph.CopilotAgent, "_execute_tool", execute_tool)

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    result = await svc._materialise_copilot_tool(
        {
            "tool_name": "prepare_month_end_close",
            "tool_input": {"period": "2026-06"},
            "requested_by_user_id": "user-1",
        }
    )

    assert result == {"entity_type": "month_end_close", "entity_id": "2026-06"}
    execute_tool.assert_awaited_once_with(
        "prepare_month_end_close",
        {"period": "2026-06"},
    )


@pytest.mark.asyncio
async def test_inbox_materialises_copilot_finance_ops_action_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda: MagicMock())
    execute_tool = AsyncMock(return_value={"should_not_execute": True})
    monkeypatch.setattr(graph.CopilotAgent, "_execute_tool", execute_tool)

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    result = await svc._materialise_copilot_tool(
        {
            "tool_name": "create_finance_ops_action_plan",
            "tool_input": {"period": "2026-06"},
            "requested_by_user_id": "user-1",
            "plan_id": "finance-ops-plan-1",
            "action_count": 3,
            "approval_effect": "Approval records manager review only.",
        }
    )

    assert result == {
        "entity_type": "finance_ops_action_plan",
        "entity_id": "finance-ops-plan-1",
        "action_count": 3,
        "approval_effect": "Approval records manager review only.",
    }
    execute_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_inbox_materialise_copilot_tool_failure_raises_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda: MagicMock())
    monkeypatch.setattr(
        graph.CopilotAgent,
        "_execute_tool",
        AsyncMock(return_value={"error": "No active projects found"}),
    )

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")

    with pytest.raises(HTTPException) as exc:
        await svc._materialise_copilot_tool(
            {
                "tool_name": "log_time_entry",
                "tool_input": {"project_name": "Nexus", "hours": 2},
            }
        )

    assert exc.value.status_code == 409
