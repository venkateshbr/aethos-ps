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


class _InsertResult:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _InsertQuery:
    def __init__(self, db: _InsertOnlyDb, table: str) -> None:
        self._db = db
        self._table = table
        self._rows: list[dict] = []

    def insert(self, payload: dict) -> _InsertQuery:
        row = {"id": f"{self._table}-{len(self._db.tables[self._table]) + 1}", **payload}
        self._db.tables[self._table].append(row)
        self._rows = [row]
        return self

    def execute(self) -> _InsertResult:
        return _InsertResult(self._rows)


class _InsertOnlyDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {
            "agent_suggestions": [],
            "hitl_tasks": [],
        }

    def table(self, name: str) -> _InsertQuery:
        return _InsertQuery(self, name)


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
async def test_year_end_close_policy_routes_to_hitl_with_review_payload(
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
        "year": 2026,
        "period": "2026-12",
        "preview": {
            "period": "2026-12",
            "workflow": "year_end_close",
            "ready_to_post": True,
        },
        "year_end_close_preview": {"net_income": "400.00"},
    }
    agent._build_year_end_close_review_payload = AsyncMock(return_value=review_payload)  # type: ignore[method-assign]
    agent._execute_tool = AsyncMock(return_value={"year_end_close_posted": True})
    write_suggestion = AsyncMock(return_value={"id": "sug-year-close-1"})
    monkeypatch.setattr(graph, "write_agent_suggestion", write_suggestion)

    result = await agent._execute_tool_with_policy(
        "prepare_year_end_close",
        {"year": 2026},
    )

    assert result["requires_review"] is True
    assert result["suggestion_id"] == "sug-year-close-1"
    assert result["action_type"] == "copilot_prepare_year_end_close"
    assert result["risk_class"] == "accounting"
    agent._execute_tool.assert_not_awaited()
    suggestion_kwargs = write_suggestion.await_args.kwargs
    assert suggestion_kwargs["output"]["tool_name"] == "prepare_year_end_close"
    assert suggestion_kwargs["output"]["year"] == 2026
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

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
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

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
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

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
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
async def test_inbox_materialises_copilot_year_end_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
    execute_tool = AsyncMock(
        return_value={
            "year_end_close_posted": True,
            "period": "2026-12",
            "journal_entry_id": "journal-ye-2026",
        }
    )
    monkeypatch.setattr(graph.CopilotAgent, "_execute_tool", execute_tool)

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    result = await svc._materialise_copilot_tool(
        {
            "tool_name": "prepare_year_end_close",
            "tool_input": {"year": 2026},
            "requested_by_user_id": "user-1",
        }
    )

    assert result == {"entity_type": "year_end_close", "entity_id": "journal-ye-2026"}
    execute_tool.assert_awaited_once_with(
        "prepare_year_end_close",
        {"year": 2026},
    )


@pytest.mark.asyncio
async def test_inbox_materialises_copilot_finance_ops_action_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
    execute_tool = AsyncMock(return_value={"should_not_execute": True})
    monkeypatch.setattr(graph.CopilotAgent, "_execute_tool", execute_tool)

    db = _InsertOnlyDb()
    svc = InboxService(db, tenant_id="tenant-abc")  # type: ignore[arg-type]
    result = await svc._materialise_copilot_tool(
        {
            "tool_name": "create_finance_ops_action_plan",
            "tool_input": {"period": "2026-06"},
            "requested_by_user_id": "user-1",
            "plan_id": "finance-ops-plan-1",
            "period": "2026-06",
            "action_count": 3,
            "approval_effect": "Approval records manager review only.",
            "action_items": [
                {
                    "action_id": "finance-ops-01-ar",
                    "domain": "AR",
                    "recommendation": "Draft collections reminders.",
                    "suggested_agent": "collections_agent",
                    "suggested_tool": "send_email",
                    "risk_class": "write_money_in",
                    "requires_inbox_approval": True,
                    "rationale": "Two invoices are overdue.",
                    "review_path": "Inbox > Collections",
                },
                {
                    "domain": "AP",
                    "recommendation": "Prepare the bill-pay run.",
                    "suggested_agent": "bill_pay_agent",
                    "suggested_tool": "propose_bill_payment_batch",
                    "risk_class": "write_money_out",
                    "requires_inbox_approval": True,
                    "rationale": "Approved bills are due.",
                    "review_path": "Inbox > Payments",
                },
                {
                    "domain": "Reporting",
                    "recommendation": "Read the dashboard.",
                    "requires_inbox_approval": False,
                },
            ],
        }
    )

    assert result == {
        "entity_type": "finance_ops_action_plan",
        "entity_id": "finance-ops-plan-1",
        "action_count": 3,
        "child_tasks_created": 2,
        "approval_effect": (
            "Approval queued child Inbox work items only; downstream invoices, "
            "payments, journals, statements, and external sends still require "
            "their own specialist approvals."
        ),
    }
    assert len(db.tables["agent_suggestions"]) == 2
    assert len(db.tables["hitl_tasks"]) == 2

    first_suggestion = db.tables["agent_suggestions"][0]
    assert first_suggestion["agent_name"] == "collections_agent"
    assert first_suggestion["action_type"] == "finance_ops_action_item"
    assert first_suggestion["status"] == "pending"
    assert first_suggestion["hitl_required"] is True
    assert first_suggestion["input_snapshot"] == {
        "parent_plan_id": "finance-ops-plan-1",
        "period": "2026-06",
        "source_tool": "create_finance_ops_action_plan",
    }
    assert first_suggestion["output_snapshot"]["finance_ops_action_item"] is True
    assert first_suggestion["output_snapshot"]["parent_plan_id"] == "finance-ops-plan-1"
    assert first_suggestion["output_snapshot"]["action_item_id"] == "finance-ops-01-ar"
    assert first_suggestion["output_snapshot"]["suggested_tool"] == "send_email"
    assert first_suggestion["output_snapshot"]["dispatch_tool"] == "draft_collection_reminders"
    assert first_suggestion["output_snapshot"]["dispatch_input"] == {
        "minimum_days_overdue": 1,
        "limit": 10,
        "tone": "auto",
    }

    first_task = db.tables["hitl_tasks"][0]
    assert first_task["agent_suggestion_id"] == first_suggestion["id"]
    assert first_task["kind"] == "finance_ops_action_item"
    assert first_task["priority"] == "high"
    assert first_task["status"] == "open"
    assert first_task["payload"]["review_path"] == "Inbox > Collections"
    assert "AR" in first_task["title"]
    execute_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_inbox_materialises_finance_ops_action_item_dispatches_collections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
    stage_reminders = AsyncMock(
        return_value={
            "collections_reminders_drafted": True,
            "requires_review": True,
            "tool_name": "draft_collection_reminders",
            "created_review_tasks": 2,
            "message": "Created 2 Inbox review task(s) for collections reminders.",
        }
    )
    execute_with_policy = AsyncMock()
    monkeypatch.setattr(
        graph.CopilotAgent,
        "_draft_collection_reminders",
        stage_reminders,
    )
    monkeypatch.setattr(
        graph.CopilotAgent,
        "_execute_tool_with_policy",
        execute_with_policy,
    )

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    result = await svc._materialise_copilot_tool(
        {
            "finance_ops_action_item": True,
            "parent_plan_id": "finance-ops-plan-1",
            "action_item_id": "finance-ops-plan-1-1",
            "period": "2026-06",
            "domain": "ar",
            "suggested_tool": "send_email",
        },
        user_id="approver-1",
    )

    stage_reminders.assert_awaited_once_with(
        {"minimum_days_overdue": 1, "limit": 10, "tone": "auto"},
    )
    execute_with_policy.assert_not_awaited()
    assert result["entity_type"] == "finance_ops_action_item"
    assert result["entity_id"] == "finance-ops-plan-1-1"
    assert result["parent_plan_id"] == "finance-ops-plan-1"
    assert result["dispatched_tool"] == "draft_collection_reminders"
    assert result["child_review_tasks_created"] == 2
    assert result["dispatch_result"]["created_review_tasks"] == 2
    assert "existing review gates" in result["approval_effect"]


@pytest.mark.asyncio
async def test_inbox_materialises_finance_ops_action_item_dispatches_bill_pay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
    execute_tool = AsyncMock(
        return_value={
            "requires_review": True,
            "suggestion_id": "sug-bill-pay",
            "tool_name": "propose_bill_payment_batch",
            "action_type": "create_bill_payment_batch",
        }
    )
    monkeypatch.setattr(graph.CopilotAgent, "_execute_tool_with_policy", execute_tool)

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    result = await svc._materialise_copilot_tool(
        {
            "finance_ops_action_item": True,
            "parent_plan_id": "finance-ops-plan-1",
            "action_item_id": "finance-ops-plan-1-2",
            "period": "2026-06",
            "domain": "ap",
            "suggested_tool": "propose_bill_payment_batch",
        },
        user_id="approver-1",
    )

    execute_tool.assert_awaited_once_with(
        "propose_bill_payment_batch",
        {"due_within_days": 7},
    )
    assert result["dispatched_tool"] == "propose_bill_payment_batch"
    assert result["child_review_tasks_created"] == 1


@pytest.mark.asyncio
async def test_inbox_materialises_finance_ops_action_item_dispatches_year_end_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
    execute_tool = AsyncMock(
        return_value={
            "requires_review": True,
            "suggestion_id": "sug-year-close",
            "tool_name": "prepare_year_end_close",
            "action_type": "copilot_prepare_year_end_close",
        }
    )
    monkeypatch.setattr(graph.CopilotAgent, "_execute_tool_with_policy", execute_tool)

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    result = await svc._materialise_copilot_tool(
        {
            "finance_ops_action_item": True,
            "parent_plan_id": "finance-ops-plan-1",
            "action_item_id": "finance-ops-plan-1-year-close",
            "period": "2026-12",
            "domain": "close",
            "suggested_tool": "prepare_year_end_close",
        },
        user_id="approver-1",
    )

    execute_tool.assert_awaited_once_with(
        "prepare_year_end_close",
        {"year": "2026"},
    )
    assert result["dispatched_tool"] == "prepare_year_end_close"
    assert result["child_review_tasks_created"] == 1


@pytest.mark.asyncio
async def test_inbox_finance_ops_action_item_requires_invoice_context() -> None:
    from app.services.inbox_service import InboxService

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    with pytest.raises(HTTPException) as exc:
        await svc._materialise_copilot_tool(
            {
                "finance_ops_action_item": True,
                "parent_plan_id": "finance-ops-plan-1",
                "action_item_id": "finance-ops-plan-1-3",
                "period": "2026-06",
                "domain": "wip",
                "suggested_tool": "draft_invoice",
            },
            user_id="approver-1",
        )

    assert exc.value.status_code == 422
    assert "engagement_id or engagement_name" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_inbox_finance_ops_action_item_requires_invoice_context_for_child_metadata() -> None:
    from app.services.inbox_service import InboxService

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    with pytest.raises(HTTPException) as exc:
        await svc._materialise_copilot_tool(
            {
                "finance_ops_action_item": True,
                "parent_plan_id": "finance-ops-plan-1",
                "action_item_id": "finance-ops-plan-1-3",
                "period": "2026-06",
                "domain": "wip",
                "suggested_tool": "draft_invoice",
                "dispatch_tool": "draft_invoice",
                "dispatch_input": {},
                "source_plan_action": {
                    "domain": "wip",
                    "suggested_tool": "draft_invoice",
                },
            },
            user_id="approver-1",
        )

    assert exc.value.status_code == 422
    assert "engagement_id or engagement_name" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_inbox_finance_ops_action_item_dispatch_error_keeps_task_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
    monkeypatch.setattr(
        graph.CopilotAgent,
        "_execute_tool_with_policy",
        AsyncMock(return_value={"error": "propose_bill_payment_batch requires admin"}),
    )

    svc = InboxService(MagicMock(), tenant_id="tenant-abc")
    with pytest.raises(HTTPException) as exc:
        await svc._materialise_copilot_tool(
            {
                "finance_ops_action_item": True,
                "parent_plan_id": "finance-ops-plan-1",
                "action_item_id": "finance-ops-plan-1-4",
                "period": "2026-06",
                "domain": "ap",
                "suggested_tool": "propose_bill_payment_batch",
            },
            user_id="approver-1",
        )

    assert exc.value.status_code == 409
    assert "Plan Item dispatch failed" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_inbox_materialise_copilot_tool_failure_raises_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.copilot import graph
    from app.services.inbox_service import InboxService

    monkeypatch.setattr(graph, "make_async_llm_client", lambda **_: MagicMock())
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
