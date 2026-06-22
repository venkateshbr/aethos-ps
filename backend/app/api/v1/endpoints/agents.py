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
    AgentRunSummary,
    SetAgentControlRequest,
    SetAgentL3PolicyRequest,
    SetAgentLevelRequest,
    SetAgentLevelResponse,
)
from app.services.agents_service import AgentAutonomyError, AgentsService
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
