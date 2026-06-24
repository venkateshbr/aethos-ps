"""Pydantic request/response schemas for the HITL Inbox API.

The Inbox surface lets humans review, approve, edit, reject, or escalate
AI-generated suggestions that have been queued as hitl_tasks.

confidence is stored as NUMERIC(3,2) in the DB (0.00 - 1.00) and exposed
as a string so JSON consumers can format it as "0.78" without float drift.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HitlDecisionEvent(BaseModel):
    """Financial event projected onto an Inbox task decision timeline."""

    id: str
    event_type: str
    action: str
    actor_user_id: str | None = None
    actor_role: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    metadata: dict[str, Any]
    event_hash: str
    created_at: str

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> HitlDecisionEvent:
        return cls(
            id=str(row["id"]),
            event_type=str(row["event_type"]),
            action=str(row["action"]),
            actor_user_id=row.get("actor_user_id"),
            actor_role=row.get("actor_role"),
            source_type=row.get("source_type"),
            source_id=row.get("source_id"),
            before_state=dict(row.get("before_state") or {}),
            after_state=dict(row.get("after_state") or {}),
            metadata=dict(row.get("metadata") or {}),
            event_hash=str(row["event_hash"]),
            created_at=str(row["created_at"]),
        )


class HitlTaskSummary(BaseModel):
    """Lightweight list-item view of a HITL task."""

    id: str
    tenant_id: str
    kind: str
    priority: str
    title: str
    agent_name: str
    confidence: str         # e.g. "0.78" — string to avoid float precision issues
    status: str
    created_at: str
    suggestion_payload: dict  # agent_suggestions.output_snapshot
    required_approval_role: str | None = None
    approval_policy_reason: str | None = None
    approval_policy: dict = Field(default_factory=dict)
    decision_history: list[HitlDecisionEvent] = Field(default_factory=list)


class HitlTaskDetail(HitlTaskSummary):
    """Full detail view — includes the task description and payload."""

    description: str | None
    payload: dict           # hitl_tasks.payload (task-specific extra data)


class HitlTaskListResponse(BaseModel):
    items: list[HitlTaskSummary]
    total: int


# ---------------------------------------------------------------------------
# Action request bodies
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    """Approve a suggestion as-is.  No body fields required."""

    pass


class ApproveWithEditsRequest(BaseModel):
    """Approve with human corrections.

    ``corrected_payload`` must be a valid replacement for the original
    ``output_snapshot``.  The service validates it matches the expected
    action_type schema before materialising.
    """

    corrected_payload: dict = Field(..., description="Corrected version of the agent's output_snapshot")


class RejectRequest(BaseModel):
    """Reject a suggestion with an optional reason."""

    reason: str = Field(default="", max_length=1000)


# ---------------------------------------------------------------------------
# Action response bodies
# ---------------------------------------------------------------------------


class ApproveResponse(BaseModel):
    materialised: bool
    entity_id: str | None
    entity_type: str | None
    message: str
    materialisation: dict = Field(default_factory=dict)


class RejectResponse(BaseModel):
    rejected: bool
    task_id: str


class EscalateResponse(BaseModel):
    escalated: bool
    task_id: str
    message: str
