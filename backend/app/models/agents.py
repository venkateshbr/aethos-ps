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


class SetFinanceOpsScheduleRequest(BaseModel):
    """Admin-controlled scheduled Finance Ops Manager cadence."""

    is_enabled: bool = Field(default=True)
    cadence: str = Field(default="daily", description="daily or weekly")
    run_hour_utc: int = Field(default=7, ge=0, le=23)
    run_weekday_utc: int = Field(
        default=0,
        ge=0,
        le=6,
        description="Monday=0 through Sunday=6; used for weekly cadence.",
    )
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    period_mode: str = Field(default="current_month", description="current_month or previous_month")
    lookback_limit: int = Field(default=10, ge=1, le=25)
    stale_after_hours: int = Field(default=24, ge=1, le=720)
    high_risk_stale_after_hours: int = Field(default=4, ge=1, le=720)
    escalation_enabled: bool = Field(default=True)


class FinanceOpsScheduleResponse(SetFinanceOpsScheduleRequest):
    """Current scheduled Finance Ops Manager cadence."""

    tenant_id: str
    is_seeded_default: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class FinanceOpsControlRoomWorkflow(BaseModel):
    """Safe workflow summary for the Finance Ops Manager control room."""

    id: str
    workflow_name: str
    status: str
    owner_agent_name: str | None = None
    current_step: str | None = None
    period: str | None = None
    started_at: str
    completed_at: str | None = None
    updated_at: str
    has_error: bool = False
    business_summary: str


class FinanceOpsControlRoomTask(BaseModel):
    """Safe Inbox task summary for pending Finance Ops Manager work."""

    id: str
    kind: str
    priority: str
    title: str
    status: str
    period: str | None = None
    action_count: int | None = None
    source_schedule_key: str | None = None
    risk_class: str | None = None
    required_approval_role: str | None = None
    created_at: str
    updated_at: str | None = None


class FinanceOpsControlRoomResponse(BaseModel):
    """Consolidated read-only Finance Ops Manager command center."""

    tenant_id: str
    generated_at: str
    schedule: FinanceOpsScheduleResponse
    next_run_at: str | None = None
    latest_scheduled_run: FinanceOpsControlRoomWorkflow | None = None
    recent_scheduled_runs: list[FinanceOpsControlRoomWorkflow]
    recent_workflow_status_counts: dict[str, int]
    waiting_on_human_workflows: list[FinanceOpsControlRoomWorkflow]
    failed_or_skipped_workflows: list[FinanceOpsControlRoomWorkflow]
    open_action_plans: list[FinanceOpsControlRoomTask]
    open_plan_items: list[FinanceOpsControlRoomTask]
    open_escalations: list[FinanceOpsControlRoomTask]
    operational_health: dict


class ApprovalControlsPersonaSummary(BaseModel):
    """User-safe finance persona mapping for the current tenant role model."""

    id: str
    label: str
    description: str
    matched_current_role: bool
    read_only: bool
    mapped_roles: list[str]
    areas: list[str]
    allowed_actions: list[str]
    restricted_actions: list[str]


class ApprovalControlsPolicyRule(BaseModel):
    """Business-readable approval policy rule for Nous and Settings."""

    id: str
    label: str
    required_role: str
    current_user_can_approve: bool
    threshold: str | None = None
    explanation: str


class ApprovalControlsInboxItem(BaseModel):
    """Safe Inbox item summary for approval-control readbacks."""

    id: str
    kind: str
    priority: str
    title: str
    status: str
    created_at: str
    risk_category: str
    required_approval_role: str
    current_user_can_approve: bool
    business_reason: str
    amount: str | None = None
    threshold: str | None = None


class ApprovalControlsReadPackResponse(BaseModel):
    """Role-aware read pack for approval policy, personas, and Inbox risk."""

    tenant_id: str
    generated_at: str
    current_user_role: str
    policy_source: str
    matched_persona_ids: list[str]
    personas: list[ApprovalControlsPersonaSummary]
    policy_rules: list[ApprovalControlsPolicyRule]
    visible_open_inbox_item_count: int
    pending_high_risk_inbox: list[ApprovalControlsInboxItem]
    pending_items_requiring_higher_role: list[ApprovalControlsInboxItem]
    denied_action_explanations: list[str]


class O2CCollectionsReminderSummary(BaseModel):
    """Safe reminder-history summary for an invoice."""

    count: int = 0
    last_sent_at: str | None = None
    last_tone: str | None = None
    last_status: str | None = None


class O2CCollectionsInvoiceSummary(BaseModel):
    """Invoice-level O2C collections and payment state for Nous."""

    id: str
    invoice_number: str
    client_id: str
    client_name: str | None = None
    status: str
    invoice_state: str
    payment_status: str
    currency: str
    total: str
    paid_amount: str
    balance_due: str
    issue_date: str | None = None
    due_date: str | None = None
    sent_at: str | None = None
    paid_at: str | None = None
    days_overdue: int
    aging_bucket: str
    public_invoice_available: bool
    payment_link_state: str
    reminder_history: O2CCollectionsReminderSummary
    collections_policy_stage: str | None = None
    recommended_next_action: str
    reminder_blockers: list[str]


class O2CCustomerCollectionsSummary(BaseModel):
    """Customer-level O2C collections rollup."""

    client_id: str
    client_name: str | None = None
    invoice_count: int
    open_invoice_count: int
    overdue_invoice_count: int
    balances_by_currency: dict[str, str]
    overdue_balance_by_currency: dict[str, str]
    recommended_next_action: str
    invoices: list[O2CCollectionsInvoiceSummary]


class O2CCollectionsReadPackResponse(BaseModel):
    """Read-only O2C collections and invoice drilldown pack."""

    tenant_id: str
    generated_at: str
    query: dict
    totals: dict[str, object]
    customers: list[O2CCustomerCollectionsSummary]
    invoices: list[O2CCollectionsInvoiceSummary]


class P2PPaymentBatchSummary(BaseModel):
    """Safe payment-batch state for one bill."""

    batch_id: str
    batch_status: str
    item_status: str
    amount: str
    currency: str
    pay_date: str | None = None
    file_format: str | None = None
    exported_at: str | None = None
    export_file_hash_present: bool = False
    sent_at: str | None = None
    settled_at: str | None = None
    risk_review_required: bool = False


class P2PBillSummary(BaseModel):
    """Bill-level P2P payment-risk and evidence state for Nous."""

    id: str
    bill_number: str
    vendor_id: str
    vendor_name: str | None = None
    vendor_invoice_number: str | None = None
    status: str
    bill_state: str
    currency: str
    total: str
    issue_date: str | None = None
    due_date: str | None = None
    paid_at: str | None = None
    days_until_due: int | None = None
    days_overdue: int
    aging_bucket: str
    source_document_id: str | None = None
    source_document_available: bool
    po_match_status: str
    coding_summary: dict[str, object]
    duplicate_risk: bool
    duplicate_review_required: bool
    approval_state: str
    payment_readiness: str
    payment_blockers: list[str]
    payment_batches: list[P2PPaymentBatchSummary]
    recommended_next_action: str


class P2PVendorSummary(BaseModel):
    """Vendor-level P2P payment-risk rollup."""

    vendor_id: str
    vendor_name: str | None = None
    bill_count: int
    open_bill_count: int
    due_soon_bill_count: int
    blocked_bill_count: int
    balances_by_currency: dict[str, str]
    due_soon_by_currency: dict[str, str]
    recommended_next_action: str
    bills: list[P2PBillSummary]


class P2PPaymentRiskReadPackResponse(BaseModel):
    """Read-only P2P vendor bill and payment-risk drilldown pack."""

    tenant_id: str
    generated_at: str
    query: dict
    totals: dict[str, object]
    vendors: list[P2PVendorSummary]
    bills: list[P2PBillSummary]


class R2RJournalSummary(BaseModel):
    """Safe journal state summary for an R2R management pack."""

    period: str
    total_count: int
    posted_count: int
    draft_count: int
    recent_journals: list[dict[str, object]]
    draft_journals: list[dict[str, object]]


class R2RManagementPackReadPackResponse(BaseModel):
    """Read-only R2R management reporting and close drilldown pack."""

    tenant_id: str
    generated_at: str
    period: str
    period_start: str
    period_end: str
    comparison_period: str
    query: dict
    data_availability: dict[str, object]
    close_status: dict[str, object]
    close_task_checklist_state: dict[str, object]
    close_blockers: list[dict[str, object]]
    financial_statements: dict[str, object]
    statement_variances: list[dict[str, object]]
    working_capital_movement: dict[str, object]
    project_margin_highlights: list[dict[str, object]]
    utilization_highlights: list[dict[str, object]]
    journal_summary: R2RJournalSummary
    management_commentary: list[dict[str, object]]
    recommended_next_actions: list[str]


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


class AgentWorkflowRunSummary(BaseModel):
    """Durable long-running agent workflow container."""

    id: str
    tenant_id: str
    workflow_name: str
    status: str
    owner_agent_name: str | None = None
    user_id: str | None = None
    current_step: str | None = None
    goal_snapshot: dict
    state_snapshot: dict
    trace_id: str | None = None
    replay_pointer: str | None = None
    error_message: str | None = None
    started_at: str
    completed_at: str | None = None
    created_at: str
    updated_at: str


class AgentWorkflowRunListResponse(BaseModel):
    """Response wrapper for GET /agents/workflow-runs."""

    workflow_runs: list[AgentWorkflowRunSummary]
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


class AgentReplayStepResponse(BaseModel):
    """One recorded tool-call step in a replay preview."""

    index: int
    tool_invocation_id: str
    tool_name: str
    risk_class: str
    status: str
    input_hash: str | None = None
    output_hash: str | None = None
    input_snapshot: dict
    output_snapshot: dict
    error_message: str | None = None
    created_at: str


class AgentRunReplayResponse(BaseModel):
    """Deterministic, non-mutating replay package for an agent run."""

    run_id: str
    agent_name: str
    status: str
    replay_mode: str
    can_reexecute: bool
    trace_id: str | None = None
    replay_pointer: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    prompt_version: str | None = None
    model_version: str | None = None
    manifest_hash: str
    steps: list[AgentReplayStepResponse]


class AgentReplayValidationStepResponse(BaseModel):
    """Current-code dry-run validation for one recorded tool-call step."""

    index: int
    tool_invocation_id: str
    tool_name: str
    recorded_risk_class: str
    current_risk_class: str
    recorded_status: str
    replay_status: str
    reason: str
    input_hash: str | None = None
    recorded_output_hash: str | None = None
    current_output_hash: str | None = None
    input_hash_matches: bool | None = None
    output_hash_matches: bool | None = None
    duration_ms: int | None = None
    current_output_snapshot: dict | None = None
    reexecution_plan: dict | None = None
    error_message: str | None = None


class AgentRunReplayValidationResponse(BaseModel):
    """Read-only current-code replay validation for an agent run."""

    run_id: str
    agent_name: str
    validation_mode: str
    overall_status: str
    can_reexecute: bool
    can_request_human_reexecution: bool = False
    manifest_hash: str
    reexecuted_step_count: int
    planned_step_count: int = 0
    blocked_step_count: int
    drift_step_count: int
    failed_step_count: int
    steps: list[AgentReplayValidationStepResponse]
