"""Pydantic models for the agents/autonomy endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentAutonomyStatus(BaseModel):
    """Per-agent autonomy status snapshot."""

    agent_name: str = Field(description="Internal agent identifier, e.g. 'expense_extractor_agent'")
    display_name: str = Field(description="Human-readable name, e.g. 'Expense Extractor'")
    current_level: int = Field(description="Autonomy level: 1=notify, 2=suggest (HITL), 3=auto-apply")
    is_locked: bool = Field(description="True for agents whose level cannot be changed (accounting_guardian)")
    approval_rate_30d: float | None = Field(
        default=None,
        description="Fraction of decided suggestions approved in last 30 days (0.0-1.0). None if < 10 decided samples.",
    )
    sample_count_30d: int = Field(
        description="Count of decided (non-pending) suggestions in last 30 days"
    )
    avg_confidence_30d: float | None = Field(
        default=None,
        description="Average agent confidence score in last 30 days. None if no decided samples.",
    )
    is_eligible_for_promotion: bool = Field(
        description="True when all L2→L3 thresholds are met and current_level is 2"
    )
    description: str = Field(description="What this agent does")


class AgentAutonomyStatusResponse(BaseModel):
    """Response wrapper for GET /agents/autonomy-status."""

    agents: list[AgentAutonomyStatus]


class SetAgentLevelRequest(BaseModel):
    """Body for POST /agents/{agent_name}/set-level."""

    level: int = Field(ge=1, le=3, description="Target autonomy level (1-3)")


class SetAgentLevelResponse(BaseModel):
    """Confirmation that an agent's level was updated."""

    agent_name: str
    level: int


class AgentRunSummary(BaseModel):
    """Single agent run row for the operator dashboard."""

    id: str
    agent_name: str
    trigger_type: str
    status: str
    user_id: str | None = None
    prompt_version: str | None = None
    model_version: str | None = None
    trace_id: str | None = None
    replay_pointer: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    source_document_hash: str | None = None
    usage_input_tokens: int | None = None
    usage_output_tokens: int | None = None
    cost_usd: str | None = None
    error_message: str | None = None
    started_at: str
    completed_at: str | None = None
    created_at: str
    tool_count: int = 0
    failed_tool_count: int = 0


class AgentRunListResponse(BaseModel):
    """Response wrapper for GET /agents/runs."""

    runs: list[AgentRunSummary]
    total: int


class AgentToolInvocationResponse(BaseModel):
    """Tool invocation row attached to an agent run detail."""

    id: str
    tool_name: str
    risk_class: str
    status: str
    external_tool_call_id: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    input_snapshot: dict
    output_snapshot: dict
    duration_ms: int | None = None
    error_message: str | None = None
    created_at: str


class AgentRunDetailResponse(AgentRunSummary):
    """Agent run detail with ordered tool invocations."""

    tool_invocations: list[AgentToolInvocationResponse]
