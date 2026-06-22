"""Unit tests for agent tool authorization/HITL policy."""

from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest

from app.core.rbac import UserRole
from app.services.agent_tool_policy import AgentToolPolicy


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.filters: list[tuple[str, object]] = []
        self.in_filters: list[tuple[str, list[object]]] = []

    def select(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def eq(self, column: str, value: object) -> _Query:
        self.filters.append((column, value))
        return self

    def is_(self, column: str, value: object) -> _Query:
        self.filters.append((column, value))
        return self

    def in_(self, column: str, values: list[object]) -> _Query:
        self.in_filters.append((column, values))
        return self

    def limit(self, _limit: int) -> _Query:
        return self

    def execute(self) -> SimpleNamespace:
        rows = self.rows
        for column, value in self.filters:
            if value == "null":
                rows = [row for row in rows if row.get(column) is None]
            else:
                rows = [row for row in rows if row.get(column) == value]
        for column, values in self.in_filters:
            rows = [row for row in rows if row.get(column) in values]
        return SimpleNamespace(data=rows)


class _Db:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(list(self.tables.get(name, [])))


@pytest.mark.asyncio
async def test_read_only_tool_executes_for_viewer() -> None:
    policy = AgentToolPolicy(
        _Db({"tenant_users": [{"tenant_id": "tenant-1", "user_id": "user-1", "role": "viewer"}]}),
        tenant_id="tenant-1",
    )

    decision = await policy.decide(
        agent_name="copilot_agent",
        action_type="copilot_query_engagements",
        tool_name="query_engagements",
        risk_class="read_only",
        user_id="user-1",
    )

    assert decision.allowed is True
    assert decision.execute_now is True
    assert decision.route_to_hitl is False
    assert decision.user_role == UserRole.viewer


@pytest.mark.asyncio
async def test_write_money_in_routes_to_hitl_for_manager() -> None:
    policy = AgentToolPolicy(
        _Db(
            {
                "tenant_users": [{"tenant_id": "tenant-1", "user_id": "user-1", "role": "manager"}],
                "agent_autonomy_settings": [
                    {
                        "tenant_id": "tenant-1",
                        "agent_name": "copilot_agent",
                        "action_type": "default",
                        "level": 2,
                    }
                ],
            }
        ),
        tenant_id="tenant-1",
    )

    decision = await policy.decide(
        agent_name="copilot_agent",
        action_type="copilot_update_rate_card",
        tool_name="update_rate_card",
        risk_class="write_money_in",
        user_id="user-1",
    )

    assert decision.allowed is True
    assert decision.execute_now is False
    assert decision.route_to_hitl is True
    assert decision.autonomy_level == 2
    assert decision.minimum_role == UserRole.manager


@pytest.mark.asyncio
async def test_write_money_in_denies_member() -> None:
    policy = AgentToolPolicy(
        _Db({"tenant_users": [{"tenant_id": "tenant-1", "user_id": "user-1", "role": "member"}]}),
        tenant_id="tenant-1",
    )

    decision = await policy.decide(
        agent_name="copilot_agent",
        action_type="copilot_update_rate_card",
        tool_name="update_rate_card",
        risk_class="write_money_in",
        user_id="user-1",
    )

    assert decision.allowed is False
    assert decision.execute_now is False
    assert decision.route_to_hitl is False
    assert decision.minimum_role == UserRole.manager
    assert "requires manager" in decision.reason


@pytest.mark.asyncio
async def test_exact_action_autonomy_level_overrides_default() -> None:
    policy = AgentToolPolicy(
        _Db(
            {
                "tenant_users": [{"tenant_id": "tenant-1", "user_id": "user-1", "role": "manager"}],
                "agent_autonomy_settings": [
                    {
                        "tenant_id": "tenant-1",
                        "agent_name": "copilot_agent",
                        "action_type": "default",
                        "level": 2,
                    },
                    {
                        "tenant_id": "tenant-1",
                        "agent_name": "copilot_agent",
                        "action_type": "copilot_update_rate_card",
                        "level": 3,
                    },
                ],
            }
        ),
        tenant_id="tenant-1",
    )

    decision = await policy.decide(
        agent_name="copilot_agent",
        action_type="copilot_update_rate_card",
        tool_name="update_rate_card",
        risk_class="write_money_in",
        user_id="user-1",
    )

    assert decision.autonomy_level == 3


@pytest.mark.asyncio
async def test_disabled_agent_blocks_tool_before_execution() -> None:
    policy = AgentToolPolicy(
        _Db(
            {
                "tenant_users": [{"tenant_id": "tenant-1", "user_id": "user-1", "role": "admin"}],
                "agent_autonomy_settings": [
                    {
                        "tenant_id": "tenant-1",
                        "agent_name": "copilot_agent",
                        "action_type": "default",
                        "level": 2,
                        "is_enabled": False,
                    }
                ],
            }
        ),
        tenant_id="tenant-1",
    )

    decision = await policy.decide(
        agent_name="copilot_agent",
        action_type="copilot_query_engagements",
        tool_name="query_engagements",
        risk_class="read_only",
        user_id="user-1",
    )

    assert decision.allowed is False
    assert decision.execute_now is False
    assert decision.reason == "agent_disabled"


@pytest.mark.asyncio
async def test_disabled_tool_blocks_only_exact_action() -> None:
    policy = AgentToolPolicy(
        _Db(
            {
                "tenant_users": [{"tenant_id": "tenant-1", "user_id": "user-1", "role": "admin"}],
                "agent_autonomy_settings": [
                    {
                        "tenant_id": "tenant-1",
                        "agent_name": "copilot_agent",
                        "action_type": "default",
                        "level": 2,
                        "is_enabled": True,
                    },
                    {
                        "tenant_id": "tenant-1",
                        "agent_name": "copilot_agent",
                        "action_type": "copilot_update_rate_card",
                        "level": 2,
                        "is_enabled": False,
                    },
                ],
            }
        ),
        tenant_id="tenant-1",
    )

    denied = await policy.decide(
        agent_name="copilot_agent",
        action_type="copilot_update_rate_card",
        tool_name="update_rate_card",
        risk_class="write_money_in",
        user_id="user-1",
    )
    allowed = await policy.decide(
        agent_name="copilot_agent",
        action_type="copilot_query_engagements",
        tool_name="query_engagements",
        risk_class="read_only",
        user_id="user-1",
    )

    assert denied.allowed is False
    assert denied.reason == "tool_disabled:update_rate_card"
    assert allowed.allowed is True


@pytest.mark.asyncio
async def test_open_tool_circuit_blocks_exact_action() -> None:
    future = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=5)).isoformat()
    policy = AgentToolPolicy(
        _Db(
            {
                "tenant_users": [{"tenant_id": "tenant-1", "user_id": "user-1", "role": "admin"}],
                "agent_autonomy_settings": [
                    {
                        "tenant_id": "tenant-1",
                        "agent_name": "copilot_agent",
                        "action_type": "copilot_update_rate_card",
                        "level": 2,
                        "is_enabled": True,
                        "circuit_open_until": future,
                    },
                ],
            }
        ),
        tenant_id="tenant-1",
    )

    decision = await policy.decide(
        agent_name="copilot_agent",
        action_type="copilot_update_rate_card",
        tool_name="update_rate_card",
        risk_class="write_money_in",
        user_id="user-1",
    )

    assert decision.allowed is False
    assert decision.reason == "tool_circuit_open:update_rate_card"
