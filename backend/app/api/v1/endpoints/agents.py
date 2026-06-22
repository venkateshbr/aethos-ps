"""Agents router — autonomy status and level management.

Routes:
  GET  /agents/autonomy-status                — viewer+; returns all 8 agents
  POST /agents/{agent_name}/set-level         — manager+; update autonomy level
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.agents import (
    AgentAutonomyStatus,
    AgentAutonomyStatusResponse,
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


def _service(
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
    svc: AgentsService = Depends(_service),  # noqa: B008
    _current_user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> AgentAutonomyStatusResponse:
    """Return autonomy status for all known agents.

    Always returns 8 entries (one per known agent).  Agents with no
    suggestion history in the last 30 days show ``sample_count_30d=0``
    and ``approval_rate_30d=None``.
    """
    raw = svc.get_autonomy_status()
    agents = [AgentAutonomyStatus(**item) for item in raw]
    return AgentAutonomyStatusResponse(agents=agents)


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
    svc: AgentsService = Depends(_service),  # noqa: B008
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
