"""Best-effort helpers for durable agent workflow state."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


def start_workflow_run(
    db: Any,
    *,
    tenant_id: str,
    workflow_name: str,
    owner_agent_name: str | None = None,
    user_id: str | None = None,
    current_step: str | None = None,
    goal_snapshot: dict[str, Any] | None = None,
    state_snapshot: dict[str, Any] | None = None,
    trace_id: str | None = None,
    replay_pointer: str | None = None,
) -> str | None:
    """Create an agent_workflow_runs row without blocking business work."""
    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "workflow_name": workflow_name,
        "status": "running",
        "current_step": current_step,
        "goal_snapshot": goal_snapshot or {},
        "state_snapshot": state_snapshot or {},
    }
    if owner_agent_name:
        payload["owner_agent_name"] = owner_agent_name
    if user_id:
        payload["user_id"] = user_id
    if trace_id:
        payload["trace_id"] = trace_id
    if replay_pointer:
        payload["replay_pointer"] = replay_pointer

    try:
        row = db.table("agent_workflow_runs").insert(payload).execute().data[0]
        return str(row["id"])
    except Exception:
        logger.warning(
            "workflow_runs: could not create workflow run",
            extra={"tenant_id": tenant_id, "workflow_name": workflow_name},
            exc_info=True,
        )
        return None


def finish_workflow_run(
    db: Any,
    workflow_id: str | None,
    *,
    status: str,
    current_step: str,
    state_snapshot: dict[str, Any] | None = None,
    error_message: str | None = None,
    replay_pointer: str | None = None,
) -> None:
    """Update an agent_workflow_runs row without blocking business work."""
    if not workflow_id:
        return

    patch: dict[str, Any] = {
        "status": status,
        "current_step": current_step,
        "state_snapshot": state_snapshot or {},
    }
    if status in _TERMINAL_STATUSES:
        patch["completed_at"] = datetime.now(UTC).isoformat()
    if error_message:
        patch["error_message"] = error_message
    if replay_pointer:
        patch["replay_pointer"] = replay_pointer

    try:
        db.table("agent_workflow_runs").update(patch).eq("id", workflow_id).execute()
    except Exception:
        logger.warning(
            "workflow_runs: could not update workflow run",
            extra={"workflow_id": workflow_id},
            exc_info=True,
        )
