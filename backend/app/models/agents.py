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
    is_enabled: bool = Field(
        default=True,
        description="False when the admin kill switch blocks this agent's default action.",
    )
    failure_count: int = Field(
        default=0,
        description="Consecutive failures recorded for this agent's default action.",
    )
    failure_threshold: int = Field(
        default=3,
        description="Failures required before this agent's default circuit opens.",
    )
    circuit_open_until: str | None = Field(
        default=None,
        description="Future timestamp while the agent circuit is open.",
    )
    circuit_open_reason: str | None = Field(
        default=None,
        description="Last error that opened the agent circuit.",
    )
    is_circuit_open: bool = Field(
        default=False,
        description="True when circuit_open_until is still in the future.",
    )
    l3_opt_in: bool = Field(
        default=False,
        description="Explicit admin opt-in for L3 promotion.",
    )
    eval_passed_at: str | None = Field(
        default=None,
        description="Timestamp of latest passing eval gate for this agent default action.",
    )
    eval_score: str | None = Field(
        default=None,
        description="Score from latest passing eval gate.",
    )
    max_auto_risk: str = Field(
        default="draft",
        description="Highest risk class permitted for automatic L3 execution.",
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


class SetAgentControlRequest(BaseModel):
    """Body for updating an agent/action kill switch or circuit threshold."""

    is_enabled: bool | None = Field(
        default=None,
        description="Set false to pause this agent/action, true to resume it.",
    )
    failure_threshold: int | None = Field(
        default=None,
        ge=1,
        le=25,
        description="Consecutive failures before opening the circuit.",
    )
    reset_circuit: bool = Field(
        default=False,
        description="Reset failure counters and close any currently open circuit.",
    )


class AgentControlResponse(BaseModel):
    """Current control state for an agent/action row."""

    agent_name: str
    action_type: str
    is_enabled: bool
    failure_count: int
    failure_threshold: int
    circuit_open_until: str | None = None
    circuit_open_reason: str | None = None
    is_circuit_open: bool


class SetAgentL3PolicyRequest(BaseModel):
    """Admin policy gate for allowing future L3 promotion."""

    l3_opt_in: bool = Field(description="Explicit admin opt-in for L3 promotion.")
    max_auto_risk: str = Field(
        default="draft",
        description="Highest risk class permitted for automatic L3 execution.",
    )


class AgentL3PolicyResponse(BaseModel):
    """Current L3 promotion policy for an agent/action row."""

    agent_name: str
    action_type: str
    l3_opt_in: bool
    max_auto_risk: str
    eval_passed_at: str | None = None
    eval_score: str | None = None


class AgentEvalCandidateResponse(BaseModel):
    """Human correction selected as a candidate eval case."""

    id: str
    agent_correction_id: str
    agent_suggestion_id: str
    agent_name: str
    action_type: str
    eval_case_key: str
    status: str
    input_hash: str | None = None
    original_output_hash: str | None = None
    corrected_output_hash: str | None = None
    reason: str | None = None
    created_at: str
    updated_at: str


class AgentEvalCandidateListResponse(BaseModel):
    """Response wrapper for GET /agents/eval-candidates."""

    candidates: list[AgentEvalCandidateResponse]
    total: int


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
