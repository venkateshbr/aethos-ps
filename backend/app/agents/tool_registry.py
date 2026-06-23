"""Agent tool registry.

Keeps tool risk classification in one place so authorization, HITL routing,
and audit logging use the same vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ToolRiskClass = Literal[
    "read_only",
    "draft",
    "write_low_risk",
    "write_money_in",
    "write_money_out",
    "accounting",
]


@dataclass(frozen=True)
class AgentToolDefinition:
    agent_name: str
    tool_name: str
    risk_class: ToolRiskClass
    action_type: str | None = None


def _persisted_action(
    agent_name: str,
    action_type: str,
    risk_class: ToolRiskClass,
) -> AgentToolDefinition:
    return AgentToolDefinition(
        agent_name=agent_name,
        tool_name=action_type,
        risk_class=risk_class,
        action_type=action_type,
    )


_TOOL_DEFINITIONS: tuple[AgentToolDefinition, ...] = (
    AgentToolDefinition("copilot_agent", "query_engagements", "read_only"),
    AgentToolDefinition("copilot_agent", "query_time_entries", "read_only"),
    AgentToolDefinition("copilot_agent", "get_ar_aging", "read_only"),
    AgentToolDefinition("copilot_agent", "get_ap_aging", "read_only"),
    AgentToolDefinition("copilot_agent", "get_wip", "read_only"),
    AgentToolDefinition("copilot_agent", "log_time_entry", "write_low_risk"),
    AgentToolDefinition("copilot_agent", "update_rate_card", "write_money_in"),
    _persisted_action("reporting_agent", "get_ar_aging", "read_only"),
    _persisted_action("reporting_agent", "get_ap_aging", "read_only"),
    _persisted_action("reporting_agent", "get_wip", "read_only"),
    _persisted_action("reporting_agent", "get_project_pnl", "read_only"),
    _persisted_action("reporting_agent", "get_utilization", "read_only"),
    _persisted_action("reporting_agent", "get_revenue", "read_only"),
    _persisted_action("reporting_agent", "get_trial_balance", "read_only"),
    _persisted_action(
        "engagement_letter_agent",
        "create_engagement_draft",
        "draft",
    ),
    _persisted_action("expense_extractor_agent", "create_expense_draft", "draft"),
    _persisted_action("vendor_invoice_agent", "create_bill_draft", "draft"),
    _persisted_action("invoice_drafter_agent", "draft_invoice", "write_money_in"),
    _persisted_action("billing_run_agent", "approve_billing_run", "write_money_in"),
    _persisted_action("collections_agent", "send_email", "write_money_in"),
    _persisted_action(
        "time_entry_agent",
        "send_time_entry_reminder",
        "write_low_risk",
    ),
    _persisted_action(
        "bill_pay_agent",
        "create_bill_payment_batch",
        "write_money_out",
    ),
    _persisted_action("accrual_agent", "draft_journal", "accounting"),
    _persisted_action("revenue_recognition_agent", "draft_journal", "accounting"),
    _persisted_action("accounting_guardian", "create_journal", "accounting"),
    _persisted_action("accounting_guardian", "create_manual_journal", "accounting"),
    _persisted_action("project_health_agent", "BUDGET_BURN_WARNING", "draft"),
    _persisted_action("project_health_agent", "CAPPED_TM_APPROACHING", "draft"),
    _persisted_action("project_health_agent", "RETAINER_FLOOR_WARNING", "draft"),
    _persisted_action("project_health_agent", "SCOPE_CREEP_RISK", "draft"),
    _persisted_action("intelligence_agent", "UNBILLED_ENGAGEMENT", "draft"),
    _persisted_action("intelligence_agent", "EXPENSE_SPIKE", "draft"),
    _persisted_action("intelligence_agent", "MARGIN_COMPRESSION", "draft"),
    _persisted_action("intelligence_agent", "FX_EXPOSURE", "draft"),
    _persisted_action("intelligence_agent", "RETAINER_UNDER_UTILIZATION", "draft"),
    _persisted_action("intelligence_agent", "OVERDUE_ESCALATION", "draft"),
)

_RISK_ORDER: dict[ToolRiskClass, int] = {
    "read_only": 0,
    "draft": 1,
    "write_low_risk": 2,
    "write_money_in": 3,
    "write_money_out": 4,
    "accounting": 5,
}

TOOL_DEFINITIONS: dict[tuple[str, str], AgentToolDefinition] = {
    (definition.agent_name, definition.tool_name): definition
    for definition in _TOOL_DEFINITIONS
}


def risk_class_for_tool(agent_name: str, tool_name: str) -> ToolRiskClass:
    """Return the configured risk class for a tool.

    Unknown tools default to ``draft`` so they are never silently treated as
    read-only by downstream authorization/HITL policy.
    """
    definition = TOOL_DEFINITIONS.get((agent_name, tool_name))
    if definition is None:
        return "draft"
    return definition.risk_class


def action_type_for_tool(agent_name: str, tool_name: str) -> str:
    """Return the autonomy/control action key for a tool call."""
    definition = TOOL_DEFINITIONS.get((agent_name, tool_name))
    if definition is not None and definition.action_type is not None:
        return definition.action_type
    if agent_name == "copilot_agent":
        return f"copilot_{tool_name}"
    return f"{agent_name}_{tool_name}"


def risk_class_for_action(agent_name: str, action_type: str) -> ToolRiskClass:
    """Return a risk class for a persisted autonomy action key."""
    if action_type == "default":
        return _highest_agent_risk_class(agent_name)
    for definition in _TOOL_DEFINITIONS:
        if definition.agent_name != agent_name:
            continue
        if _action_type_for_definition(definition) == action_type:
            return definition.risk_class
    return "draft"


def risk_class_allows(max_allowed: str | None, actual: ToolRiskClass) -> bool:
    """True when an admin-granted max risk permits the actual action risk."""
    allowed_rank = _RISK_ORDER.get(max_allowed, _RISK_ORDER["draft"])
    return _RISK_ORDER[actual] <= allowed_rank


def _action_type_for_definition(definition: AgentToolDefinition) -> str:
    if definition.action_type is not None:
        return definition.action_type
    if definition.agent_name == "copilot_agent":
        return f"copilot_{definition.tool_name}"
    return f"{definition.agent_name}_{definition.tool_name}"


def _highest_agent_risk_class(agent_name: str) -> ToolRiskClass:
    risks = [
        definition.risk_class
        for definition in _TOOL_DEFINITIONS
        if definition.agent_name == agent_name
    ]
    if not risks:
        return "draft"
    return max(risks, key=lambda risk: _RISK_ORDER[risk])
