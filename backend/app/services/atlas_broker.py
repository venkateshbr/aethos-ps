"""Authorization and metadata-only auditing for the internal ERP broker."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import HTTPException, status

from app.agents.tool_registry import ToolRiskClass, action_type_for_tool
from app.core.rbac import UserRole, role_meets_minimum
from app.services.agent_run_ledger import AgentRunLedger, ToolInvocationStatus
from app.services.agent_tool_policy import AgentToolPolicy
from app.services.atlas_context import AtlasToolContext
from app.services.security_service import SecurityService
from supabase import Client

logger = logging.getLogger(__name__)
_DENIED = "You do not have permission to perform this ERP operation, or it has been disabled."


@dataclass(frozen=True)
class BrokerTool:
    handler: Callable[[Client, AtlasToolContext, dict[str, Any]], Awaitable[Any]]
    risk_class: ToolRiskClass
    privileges: tuple[str, ...]
    policy_tool: str | None = None
    agent_name: str = "copilot_agent"
    minimum_role: UserRole | None = None


def _denied() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_DENIED)


async def dispatch_broker_tool(
    db: Client,
    context: AtlasToolContext,
    tool_name: str,
    tool: BrokerTool | None,
    arguments: dict[str, Any],
    *,
    source: Literal["tool_broker", "semantic_intent"] = "tool_broker",
) -> Any:
    ledger = AgentRunLedger(db, context.tenant_id)
    run_id = await ledger.start_run(
        agent_name="nous_hermes_broker" if source == "tool_broker" else "copilot_agent",
        trigger_type=source,
        user_id=context.user_id,
    )
    outcome: ToolInvocationStatus = "failed"
    reason: str | None = None
    try:
        if tool is None:
            outcome, reason = "skipped", "unavailable_operation"
            raise HTTPException(status_code=404, detail="Nous tool is not available")

        policy_tool = tool.policy_tool or tool_name
        try:
            decision = await AgentToolPolicy(db, context.tenant_id).decide(
                agent_name=tool.agent_name,
                action_type=action_type_for_tool(tool.agent_name, policy_tool),
                tool_name=policy_tool,
                risk_class=tool.risk_class,
                user_id=context.user_id,
                required_privileges=tool.privileges,
            )
            role_allowed = True
            if decision.allowed and tool.minimum_role is not None:
                # Match require_role: the active membership row is authoritative,
                # not a legacy role projected from assigned catalog duties.
                membership = await SecurityService(db, context.tenant_id).tenant_user_membership(
                    context.user_id
                )
                role_allowed = membership is not None and role_meets_minimum(
                    UserRole(membership["role"]), tool.minimum_role
                )
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            outcome, reason = "skipped", "inactive_membership"
            raise _denied() from exc
        except Exception as exc:
            reason = "permission_check_unavailable"
            logger.warning("broker_permission_check_failed", extra={"operation": tool_name})
            raise HTTPException(
                status_code=503,
                detail="ERP permissions could not be verified. Please try again later.",
            ) from exc

        can_dispatch = (
            decision.execute_now if tool.risk_class == "read_only" else decision.route_to_hitl
        )
        if not (decision.allowed and can_dispatch):
            outcome, reason = "skipped", decision.reason
            raise _denied()
        if not role_allowed:
            outcome, reason = "skipped", "insufficient_membership_role"
            raise _denied()

        try:
            result = await tool.handler(db, context, arguments)
        except PermissionError as exc:
            outcome, reason = "skipped", "domain_permission_denied"
            raise _denied() from exc
        if isinstance(result, dict) and result.get("policy_denied"):
            outcome, reason = "skipped", "downstream_policy_denied"
            raise _denied()
        if not (isinstance(result, dict) and result.get("error")):
            outcome = "succeeded"
        else:
            reason = "operation_failed"
        return result
    finally:
        await ledger.record_tool_invocation(
            run_id,
            tool_name=tool_name if tool is not None else "unavailable_operation",
            risk_class=tool.risk_class if tool is not None else "read_only",
            input_payload=None,
            output_payload=None,
            status=outcome,
            error_message=reason,
        )
        await ledger.complete_run(
            run_id, status="succeeded" if outcome == "succeeded" else "failed"
        )
