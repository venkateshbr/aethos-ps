"""Authorization and HITL routing policy for agent tool calls."""

from __future__ import annotations

import asyncio
import datetime
from dataclasses import dataclass

from app.agents.tool_registry import ToolRiskClass
from app.core.rbac import ROLE_HIERARCHY, UserRole
from app.services.security_service import SecurityService

_DEFAULT_ACTION_TYPE = "default"

_MINIMUM_ROLE_BY_RISK: dict[ToolRiskClass, UserRole] = {
    "read_only": UserRole.viewer,
    "draft": UserRole.member,
    "write_low_risk": UserRole.member,
    "write_money_in": UserRole.manager,
    "write_money_out": UserRole.admin,
    "accounting": UserRole.admin,
}

_PRIVILEGE_BY_RISK: dict[ToolRiskClass, str] = {
    "read_only": "atlas.tools.read",
    "draft": "atlas.tools.execute_draft",
    "write_low_risk": "atlas.tools.execute_draft",
    "write_money_in": "atlas.tools.execute_money_in",
    "write_money_out": "atlas.tools.execute_money_out",
    "accounting": "accounting.journal_prepare",
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
        privilege_code = _PRIVILEGE_BY_RISK[risk_class]
        has_privilege = await self._has_tool_privilege(user_id, privilege_code)
        minimum_role = _MINIMUM_ROLE_BY_RISK[risk_class]
        autonomy_rows = await self._fetch_autonomy_rows(agent_name, action_type)
        autonomy_level = self._select_autonomy_level(autonomy_rows, action_type)

        control_reason = self._blocked_by_control(
            rows=autonomy_rows,
            action_type=action_type,
            tool_name=tool_name,
        )
        if control_reason:
            return AgentToolPolicyDecision(
                allowed=False,
                execute_now=False,
                route_to_hitl=False,
                reason=control_reason,
                user_role=user_role,
                minimum_role=minimum_role,
                autonomy_level=autonomy_level,
            )

        if not has_privilege and ROLE_HIERARCHY[user_role] < ROLE_HIERARCHY[minimum_role]:
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

    async def _has_tool_privilege(self, user_id: str, privilege_code: str) -> bool:
        try:
            return await SecurityService(self.db, self.tenant_id).has_privilege(
                user_id,
                privilege_code,
            )
        except Exception:
            return False

    @staticmethod
    def _select_autonomy_level(rows: list[dict], action_type: str) -> int:
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
                .select(
                    "action_type,level,is_enabled,circuit_open_until,circuit_open_reason"
                )
                .eq("tenant_id", self.tenant_id)
                .eq("agent_name", agent_name)
                .in_("action_type", [action_type, _DEFAULT_ACTION_TYPE])
                .execute()
            )
            return getattr(result, "data", None) or []
        except Exception:
            return []

    @staticmethod
    def _blocked_by_control(
        *,
        rows: list[dict],
        action_type: str,
        tool_name: str,
    ) -> str | None:
        default = next(
            (row for row in rows if row.get("action_type") == _DEFAULT_ACTION_TYPE),
            None,
        )
        exact = next(
            (row for row in rows if row.get("action_type") == action_type),
            None,
        )

        if default and default.get("is_enabled") is False:
            return "agent_disabled"
        if exact and exact.get("is_enabled") is False:
            return f"tool_disabled:{tool_name}"

        if default and _circuit_is_open(default.get("circuit_open_until")):
            return "agent_circuit_open"
        if exact and _circuit_is_open(exact.get("circuit_open_until")):
            return f"tool_circuit_open:{tool_name}"

        return None


def _circuit_is_open(value: object) -> bool:
    if not value:
        return False
    try:
        if isinstance(value, datetime.datetime):
            opened_until = value
        else:
            opened_until = datetime.datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        if opened_until.tzinfo is None:
            opened_until = opened_until.replace(tzinfo=datetime.UTC)
    except (TypeError, ValueError):
        return False
    return opened_until > datetime.datetime.now(datetime.UTC)
