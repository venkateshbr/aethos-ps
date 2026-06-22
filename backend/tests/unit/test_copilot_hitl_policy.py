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
