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


_TOOL_DEFINITIONS: tuple[AgentToolDefinition, ...] = (
    AgentToolDefinition("copilot_agent", "query_engagements", "read_only"),
    AgentToolDefinition("copilot_agent", "query_time_entries", "read_only"),
    AgentToolDefinition("copilot_agent", "get_ar_aging", "read_only"),
    AgentToolDefinition("copilot_agent", "get_ap_aging", "read_only"),
    AgentToolDefinition("copilot_agent", "get_wip", "read_only"),
    AgentToolDefinition("copilot_agent", "log_time_entry", "write_low_risk"),
    AgentToolDefinition("copilot_agent", "update_rate_card", "write_money_in"),
    AgentToolDefinition("reporting_agent", "get_ar_aging", "read_only"),
    AgentToolDefinition("reporting_agent", "get_ap_aging", "read_only"),
    AgentToolDefinition("reporting_agent", "get_wip", "read_only"),
    AgentToolDefinition("reporting_agent", "get_project_pnl", "read_only"),
    AgentToolDefinition("reporting_agent", "get_utilization", "read_only"),
    AgentToolDefinition("reporting_agent", "get_revenue", "read_only"),
    AgentToolDefinition("reporting_agent", "get_trial_balance", "read_only"),
)

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
    if agent_name == "copilot_agent":
        return f"copilot_{tool_name}"
    return f"{agent_name}_{tool_name}"
