"""Authorization and HITL routing policy for agent tool calls."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.agents.tool_registry import ToolRiskClass
from app.core.rbac import ROLE_HIERARCHY, UserRole

_DEFAULT_ACTION_TYPE = "default"

_MINIMUM_ROLE_BY_RISK: dict[ToolRiskClass, UserRole] = {
    "read_only": UserRole.viewer,
    "draft": UserRole.member,
    "write_low_risk": UserRole.member,
    "write_money_in": UserRole.manager,
    "write_money_out": UserRole.admin,
    "accounting": UserRole.admin,
}

_WRITE_RISKS: frozenset[ToolRiskClass] = frozenset(
    {"write_low_risk", "write_money_in", "write_money_out", "accounting"}
)


@dataclass(frozen=True)
class AgentToolPolicyDecision:
    allowed: bool
    execute_now: bool
    route_to_hitl: bool
    reason: str
    user_role: UserRole
    minimum_role: UserRole
    autonomy_level: int


class AgentToolPolicy:
    """Decides whether an agent tool call may run directly or needs HITL."""

    def __init__(self, db: object, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def decide(
        self,
        *,
        agent_name: str,
        action_type: str,
        tool_name: str,
        risk_class: ToolRiskClass,
        user_id: str,
    ) -> AgentToolPolicyDecision:
        user_role = await self._fetch_user_role(user_id)
        minimum_role = _MINIMUM_ROLE_BY_RISK[risk_class]
        autonomy_level = await self._fetch_autonomy_level(agent_name, action_type)

        if ROLE_HIERARCHY[user_role] < ROLE_HIERARCHY[minimum_role]:
            return AgentToolPolicyDecision(
                allowed=False,
                execute_now=False,
                route_to_hitl=False,
                reason=(
                    f"{tool_name} requires {minimum_role.value} or higher; "
                    f"current role is {user_role.value}"
                ),
                user_role=user_role,
                minimum_role=minimum_role,
                autonomy_level=autonomy_level,
            )

        if risk_class == "read_only":
            return AgentToolPolicyDecision(
                allowed=True,
                execute_now=True,
                route_to_hitl=False,
                reason="read_only_tool",
                user_role=user_role,
                minimum_role=minimum_role,
                autonomy_level=autonomy_level,
            )

        if risk_class in _WRITE_RISKS:
            return AgentToolPolicyDecision(
                allowed=True,
                execute_now=False,
                route_to_hitl=True,
                reason="write_tool_requires_human_review",
                user_role=user_role,
                minimum_role=minimum_role,
                autonomy_level=autonomy_level,
            )

        return AgentToolPolicyDecision(
            allowed=True,
            execute_now=False,
            route_to_hitl=True,
            reason="draft_tool_requires_human_review",
            user_role=user_role,
            minimum_role=minimum_role,
            autonomy_level=autonomy_level,
        )

    async def _fetch_user_role(self, user_id: str) -> UserRole:
        try:
            result = await asyncio.to_thread(
                lambda: self.db.table("tenant_users")
                .select("role")
                .eq("tenant_id", self.tenant_id)
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            rows = getattr(result, "data", None) or []
            if rows:
                return UserRole(rows[0].get("role", UserRole.viewer.value))
        except Exception:
            return UserRole.viewer
        return UserRole.viewer

    async def _fetch_autonomy_level(self, agent_name: str, action_type: str) -> int:
        rows = await self._fetch_autonomy_rows(agent_name, action_type)
        exact = next(
            (row for row in rows if row.get("action_type") == action_type),
            None,
        )
        default = next(
            (row for row in rows if row.get("action_type") == _DEFAULT_ACTION_TYPE),
            None,
        )
        selected = exact or default
        if not selected:
            return 2
        try:
            return int(selected.get("level", 2))
        except (TypeError, ValueError):
            return 2

    async def _fetch_autonomy_rows(self, agent_name: str, action_type: str) -> list[dict]:
        try:
            result = await asyncio.to_thread(
                lambda: self.db.table("agent_autonomy_settings")
                .select("action_type,level")
                .eq("tenant_id", self.tenant_id)
                .eq("agent_name", agent_name)
                .in_("action_type", [action_type, _DEFAULT_ACTION_TYPE])
                .execute()
            )
            return getattr(result, "data", None) or []
        except Exception:
            return []
