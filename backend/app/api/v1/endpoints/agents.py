"""Agents router — autonomy status and level management.

Routes:
  GET  /agents/autonomy-status                — viewer+; returns known agents
  POST /agents/{agent_name}/set-level         — manager+; update autonomy level
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.agents.tool_registry import action_type_for_tool
from app.core.auth import CurrentUser
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.agents import (
    AgentAutonomyStatus,
    AgentAutonomyStatusResponse,
    AgentControlResponse,
    AgentEvalCandidateListResponse,
    AgentEvalCandidateResponse,
    AgentL3PolicyResponse,
    AgentRunDetailResponse,
    AgentRunListResponse,
    AgentRunReplayResponse,
    AgentRunReplayValidationResponse,
    AgentRunSummary,
    AgentWorkflowRunListResponse,
    AgentWorkflowRunSummary,
    ApprovalControlsReadPackResponse,
    FinanceOpsControlRoomResponse,
    FinanceOpsScheduleResponse,
    O2CCollectionsReadPackResponse,
    P2PPaymentRiskReadPackResponse,
    R2RManagementPackReadPackResponse,
    SetAgentControlRequest,
    SetAgentL3PolicyRequest,
    SetAgentLevelRequest,
    SetAgentLevelResponse,
    SetFinanceOpsScheduleRequest,
)
from app.services.agents_service import AgentAutonomyError, AgentsService
from app.services.o2c_read_service import O2CReadService
from app.services.p2p_read_service import P2PReadService
from app.services.r2r_read_service import R2RReadService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Service dependency
# ---------------------------------------------------------------------------


def _read_service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_user_rls_client),  # noqa: B008
) -> AgentsService:
    return AgentsService(db, tenant_id)


def _write_service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> AgentsService:
    return AgentsService(db, tenant_id)


def _ops_service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> AgentsService:
    return AgentsService(db, tenant_id)


def _o2c_read_service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> O2CReadService:
    return O2CReadService(db, tenant_id)


def _p2p_read_service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> P2PReadService:
    return P2PReadService(db, tenant_id)


def _r2r_read_service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> R2RReadService:
    return R2RReadService(db, tenant_id)


# ---------------------------------------------------------------------------
# GET /agents/finance-ops/schedule
# ---------------------------------------------------------------------------


@router.get(
    "/finance-ops/schedule",
    response_model=FinanceOpsScheduleResponse,
    summary="Scheduled AI Finance Ops Manager cadence",
)
def get_finance_ops_schedule(
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> FinanceOpsScheduleResponse:
    """Return the configured cadence or seeded default for this tenant."""
    return FinanceOpsScheduleResponse(**svc.get_finance_ops_schedule())


# ---------------------------------------------------------------------------
# GET /agents/finance-ops/control-room
# ---------------------------------------------------------------------------


@router.get(
    "/finance-ops/control-room",
    response_model=FinanceOpsControlRoomResponse,
    summary="AI Finance Ops Manager control-room status",
)
def get_finance_ops_control_room(
    workflow_limit: int = Query(default=10, ge=1, le=25),
    task_limit: int = Query(default=10, ge=1, le=25),
    svc: AgentsService = Depends(_ops_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> FinanceOpsControlRoomResponse:
    """Return scheduled run, pending work, workflow, and health signals."""
    return FinanceOpsControlRoomResponse(
        **svc.get_finance_ops_control_room(
            workflow_limit=workflow_limit,
            task_limit=task_limit,
        )
    )


# ---------------------------------------------------------------------------
# GET /agents/approval-controls/read-pack
# ---------------------------------------------------------------------------


@router.get(
    "/approval-controls/read-pack",
    response_model=ApprovalControlsReadPackResponse,
    summary="Role-aware approval controls, persona, and Inbox risk read pack",
)
def get_approval_controls_read_pack(
    inbox_limit: int = Query(default=10, ge=1, le=50),
    svc: AgentsService = Depends(_ops_service),  # noqa: B008
    current_user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> ApprovalControlsReadPackResponse:
    """Return user-safe approval policy, persona, and pending-risk state."""
    try:
        result = svc.get_approval_controls_read_pack(
            user_id=current_user.user_id,
            fallback_role=current_user.role,
            inbox_limit=inbox_limit,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return ApprovalControlsReadPackResponse(**result)


# ---------------------------------------------------------------------------
# GET /agents/o2c/collections/read-pack
# ---------------------------------------------------------------------------


@router.get(
    "/o2c/collections/read-pack",
    response_model=O2CCollectionsReadPackResponse,
    summary="Read-only O2C collections and invoice drilldown pack",
)
def get_o2c_collections_read_pack(
    invoice_id: str | None = None,
    invoice_number: str | None = None,
    client_id: str | None = None,
    client_name: str | None = None,
    invoice_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=25, ge=1, le=100),
    svc: O2CReadService = Depends(_o2c_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> O2CCollectionsReadPackResponse:
    """Return customer and invoice collections state for Nous drilldowns."""
    return O2CCollectionsReadPackResponse(
        **svc.collections_read_pack(
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            client_id=client_id,
            client_name=client_name,
            status=invoice_status,
            limit=limit,
        )
    )


# ---------------------------------------------------------------------------
# GET /agents/p2p/payment-risk/read-pack
# ---------------------------------------------------------------------------


@router.get(
    "/p2p/payment-risk/read-pack",
    response_model=P2PPaymentRiskReadPackResponse,
    summary="Read-only P2P vendor bill and payment-risk drilldown pack",
)
def get_p2p_payment_risk_read_pack(
    bill_id: str | None = None,
    bill_number: str | None = None,
    vendor_id: str | None = None,
    vendor_name: str | None = None,
    bill_status: str | None = Query(default=None, alias="status"),
    due_within_days: int = Query(default=10, ge=0, le=365),
    limit: int = Query(default=25, ge=1, le=100),
    svc: P2PReadService = Depends(_p2p_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> P2PPaymentRiskReadPackResponse:
    """Return vendor bill evidence, blockers, and payment-readiness state."""
    return P2PPaymentRiskReadPackResponse(
        **svc.payment_risk_read_pack(
            bill_id=bill_id,
            bill_number=bill_number,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            status=bill_status,
            due_within_days=due_within_days,
            limit=limit,
        )
    )


# ---------------------------------------------------------------------------
# GET /agents/r2r/management-pack/read-pack
# ---------------------------------------------------------------------------


@router.get(
    "/r2r/management-pack/read-pack",
    response_model=R2RManagementPackReadPackResponse,
    summary="Read-only R2R management reporting and close drilldown pack",
)
def get_r2r_management_pack_read_pack(
    period: str = Query(..., min_length=1),
    comparison_period: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=10, ge=1, le=25),
    svc: R2RReadService = Depends(_r2r_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> R2RManagementPackReadPackResponse:
    """Return management pack, variances, source drilldowns, and blockers."""
    try:
        result = svc.management_pack_read_pack(
            period=period,
            comparison_period=comparison_period,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return R2RManagementPackReadPackResponse(**result)


# ---------------------------------------------------------------------------
# PUT /agents/finance-ops/schedule
# ---------------------------------------------------------------------------


@router.put(
    "/finance-ops/schedule",
    response_model=FinanceOpsScheduleResponse,
    summary="Configure scheduled AI Finance Ops Manager cadence",
)
def set_finance_ops_schedule(
    body: SetFinanceOpsScheduleRequest,
    svc: AgentsService = Depends(_write_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> FinanceOpsScheduleResponse:
    """Upsert admin-controlled scheduled Finance Ops Manager cadence."""
    try:
        result = svc.set_finance_ops_schedule(
            is_enabled=body.is_enabled,
            cadence=body.cadence,
            run_hour_utc=body.run_hour_utc,
            run_weekday_utc=body.run_weekday_utc,
            timezone=body.timezone,
            period_mode=body.period_mode,
            lookback_limit=body.lookback_limit,
            stale_after_hours=body.stale_after_hours,
            high_risk_stale_after_hours=body.high_risk_stale_after_hours,
            escalation_enabled=body.escalation_enabled,
        )
    except AgentAutonomyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return FinanceOpsScheduleResponse(**result)


# ---------------------------------------------------------------------------
# GET /agents/autonomy-status
# ---------------------------------------------------------------------------


@router.get(
    "/autonomy-status",
    response_model=AgentAutonomyStatusResponse,
    summary="Per-agent autonomy status with 30-day approval metrics",
)
def get_autonomy_status(
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> AgentAutonomyStatusResponse:
    """Return autonomy status for all known agents.

    Always returns one entry per known agent.  Agents with no
    suggestion history in the last 30 days show ``sample_count_30d=0``
    and ``approval_rate_30d=None``.
    """
    raw = svc.get_autonomy_status()
    agents = [AgentAutonomyStatus(**item) for item in raw]
    return AgentAutonomyStatusResponse(agents=agents)


# ---------------------------------------------------------------------------
# GET /agents/runs
# ---------------------------------------------------------------------------


@router.get(
    "/runs",
    response_model=AgentRunListResponse,
    summary="Recent agent run ledger entries",
)
def list_agent_runs(
    agent_name: str | None = None,
    run_status: str | None = Query(default=None, alias="status"),
    limit: int = 50,
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentRunListResponse:
    """Return recent agent runs for the current tenant.

    The dashboard is manager-gated because it exposes operational trace data.
    """
    raw = svc.list_agent_runs(
        agent_name=agent_name,
        status=run_status,
        limit=limit,
    )
    runs = [AgentRunSummary(**item) for item in raw["runs"]]
    return AgentRunListResponse(runs=runs, total=raw["total"])


# ---------------------------------------------------------------------------
# GET /agents/workflow-runs
# ---------------------------------------------------------------------------


@router.get(
    "/workflow-runs",
    response_model=AgentWorkflowRunListResponse,
    summary="Recent durable agent workflow runs",
)
def list_agent_workflow_runs(
    workflow_name: str | None = None,
    run_status: str | None = Query(default=None, alias="status"),
    limit: int = 50,
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentWorkflowRunListResponse:
    """Return recent long-running workflow containers for the current tenant."""
    raw = svc.list_agent_workflow_runs(
        workflow_name=workflow_name,
        status=run_status,
        limit=limit,
    )
    workflow_runs = [
        AgentWorkflowRunSummary(**item) for item in raw["workflow_runs"]
    ]
    return AgentWorkflowRunListResponse(
        workflow_runs=workflow_runs,
        total=raw["total"],
    )


# ---------------------------------------------------------------------------
# GET /agents/workflow-runs/{workflow_run_id}
# ---------------------------------------------------------------------------


@router.get(
    "/workflow-runs/{workflow_run_id}",
    response_model=AgentWorkflowRunSummary,
    summary="Agent workflow run detail",
)
def get_agent_workflow_run(
    workflow_run_id: str,
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentWorkflowRunSummary:
    """Return one long-running workflow container."""
    row = svc.get_agent_workflow_run(workflow_run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent workflow run not found",
        )
    return AgentWorkflowRunSummary(**row)


# ---------------------------------------------------------------------------
# GET /agents/runs/{run_id}
# ---------------------------------------------------------------------------


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunDetailResponse,
    summary="Agent run detail with tool invocations",
)
def get_agent_run(
    run_id: str,
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentRunDetailResponse:
    """Return a single agent run and its tool invocations."""
    row = svc.get_agent_run(run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found",
        )
    return AgentRunDetailResponse(**row)


# ---------------------------------------------------------------------------
# POST /agents/runs/{run_id}/replay
# ---------------------------------------------------------------------------


@router.post(
    "/runs/{run_id}/replay",
    response_model=AgentRunReplayResponse,
    summary="Build a deterministic recorded replay package for an agent run",
)
def replay_agent_run(
    run_id: str,
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentRunReplayResponse:
    """Return the stored, ordered tool-call transcript for replay analysis.

    Replay is non-mutating: it does not execute tools or call an LLM.
    """
    row = svc.build_agent_run_replay(run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found",
        )
    return AgentRunReplayResponse(**row)


# ---------------------------------------------------------------------------
# POST /agents/runs/{run_id}/replay/validate
# ---------------------------------------------------------------------------


@router.post(
    "/runs/{run_id}/replay/validate",
    response_model=AgentRunReplayValidationResponse,
    summary="Validate read-only replay steps against current code",
)
def validate_agent_run_replay(
    run_id: str,
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentRunReplayValidationResponse:
    """Execute supported read-only steps and compare current hashes.

    Mutating, money movement, and accounting tools are explicitly blocked by
    risk class in this validation mode.
    """
    row = svc.build_agent_run_replay_validation(run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found",
        )
    return AgentRunReplayValidationResponse(**row)


# ---------------------------------------------------------------------------
# GET /agents/eval-candidates
# ---------------------------------------------------------------------------


@router.get(
    "/eval-candidates",
    response_model=AgentEvalCandidateListResponse,
    summary="Correction-backed eval candidates",
)
def list_eval_candidates(
    agent_name: str | None = None,
    candidate_status: str | None = Query(default="candidate", alias="status"),
    limit: int = 50,
    svc: AgentsService = Depends(_read_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentEvalCandidateListResponse:
    """Return human-correction candidates for eval-pack review/export."""
    raw = svc.list_eval_candidates(
        agent_name=agent_name,
        status=candidate_status,
        limit=limit,
    )
    candidates = [AgentEvalCandidateResponse(**item) for item in raw["candidates"]]
    return AgentEvalCandidateListResponse(
        candidates=candidates,
        total=raw["total"],
    )


# ---------------------------------------------------------------------------
# POST /agents/{agent_name}/l3-policy
# ---------------------------------------------------------------------------


@router.post(
    "/{agent_name}/l3-policy",
    response_model=AgentL3PolicyResponse,
    summary="Set admin L3 promotion policy for an agent",
)
def set_agent_l3_policy(
    agent_name: str,
    body: SetAgentL3PolicyRequest,
    svc: AgentsService = Depends(_write_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> AgentL3PolicyResponse:
    """Set explicit opt-in and max auto-risk for future L3 promotion."""
    try:
        result = svc.set_l3_policy(
            agent_name,
            l3_opt_in=body.l3_opt_in,
            max_auto_risk=body.max_auto_risk,
        )
    except AgentAutonomyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return AgentL3PolicyResponse(**result)


# ---------------------------------------------------------------------------
# POST /agents/{agent_name}/tools/{tool_name}/l3-policy
# ---------------------------------------------------------------------------


@router.post(
    "/{agent_name}/tools/{tool_name}/l3-policy",
    response_model=AgentL3PolicyResponse,
    summary="Set admin L3 promotion policy for an agent tool",
)
def set_agent_tool_l3_policy(
    agent_name: str,
    tool_name: str,
    body: SetAgentL3PolicyRequest,
    svc: AgentsService = Depends(_write_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
) -> AgentL3PolicyResponse:
    """Set explicit opt-in and max auto-risk for a specific tool/action."""
    try:
        result = svc.set_l3_policy(
            agent_name,
            action_type=action_type_for_tool(agent_name, tool_name),
            l3_opt_in=body.l3_opt_in,
            max_auto_risk=body.max_auto_risk,
        )
    except AgentAutonomyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return AgentL3PolicyResponse(**result)


# ---------------------------------------------------------------------------
# POST /agents/{agent_name}/control
# ---------------------------------------------------------------------------


@router.post(
    "/{agent_name}/control",
    response_model=AgentControlResponse,
    summary="Update an agent kill switch or circuit breaker",
)
def set_agent_control(
    agent_name: str,
    body: SetAgentControlRequest,
    svc: AgentsService = Depends(_write_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentControlResponse:
    """Pause/resume an agent or tune/reset its default circuit breaker."""
    try:
        result = svc.set_agent_control(
            agent_name,
            is_enabled=body.is_enabled,
            failure_threshold=body.failure_threshold,
            reset_circuit=body.reset_circuit,
        )
    except AgentAutonomyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return AgentControlResponse(**result)


# ---------------------------------------------------------------------------
# POST /agents/{agent_name}/tools/{tool_name}/control
# ---------------------------------------------------------------------------


@router.post(
    "/{agent_name}/tools/{tool_name}/control",
    response_model=AgentControlResponse,
    summary="Update an agent tool kill switch or circuit breaker",
)
def set_agent_tool_control(
    agent_name: str,
    tool_name: str,
    body: SetAgentControlRequest,
    svc: AgentsService = Depends(_write_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> AgentControlResponse:
    """Pause/resume a specific tool/action or reset its circuit breaker."""
    try:
        result = svc.set_agent_control(
            agent_name,
            action_type=action_type_for_tool(agent_name, tool_name),
            is_enabled=body.is_enabled,
            failure_threshold=body.failure_threshold,
            reset_circuit=body.reset_circuit,
        )
    except AgentAutonomyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return AgentControlResponse(**result)


# ---------------------------------------------------------------------------
# POST /agents/{agent_name}/set-level
# ---------------------------------------------------------------------------


@router.post(
    "/{agent_name}/set-level",
    response_model=SetAgentLevelResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually set an agent's autonomy level (manager+)",
)
def set_agent_level(
    agent_name: str,
    body: SetAgentLevelRequest,
    svc: AgentsService = Depends(_write_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
) -> SetAgentLevelResponse:
    """Set the autonomy level for a named agent (1=notify, 2=suggest, 3=auto).

    - Locked agents (``accounting_guardian``) always return 422.
    - Unknown agent names return 404.
    - Level must be 1, 2, or 3.
    """
    try:
        result = svc.set_autonomy_level(agent_name, body.level)
    except AgentAutonomyError as exc:
        msg = str(exc)
        if "Unknown agent" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=msg,
        ) from exc

    return SetAgentLevelResponse(**result)
