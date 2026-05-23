"""Agent Suggestion Writer.

Persists agent output as an immutable agent_suggestion row and (when HITL is required)
creates an open hitl_task for human review.

Rules:
- agent_suggestion rows are immutable once written (no updates, no deletes)
- hitl_required = True when autonomy_level < 3 OR confidence < confidence_threshold
- suspected_injection in output ALWAYS forces hitl_required = True
- priority is "high" when confidence < 0.5, else "med"
"""

from __future__ import annotations

import logging

from app.agents.base import AgentDeps

logger = logging.getLogger(__name__)


async def write_agent_suggestion(
    deps: AgentDeps,
    agent_name: str,
    action_type: str,
    document_id: str | None,
    output: dict,
    confidence: float,
    autonomy_level: int = 2,
    confidence_threshold: float = 0.90,
) -> dict:
    """Write agent_suggestion + hitl_task rows.

    Parameters
    ----------
    deps:                 Tenant-scoped agent dependencies (db client + tenant_id).
    agent_name:           Machine name of the agent, e.g. "engagement_letter_agent".
    action_type:          The HITL action kind, e.g. "create_engagement_draft".
    document_id:          UUID of the source document row, or None if the agent
                          has no single source document (e.g. bill_pay_agent
                          sweeps approved bills). When None, the FK column
                          ``original_document_id`` is omitted from the insert
                          payload so it stores SQL NULL — see bug #102.
    output:               The typed draft serialised as a plain dict.
    confidence:           Agent confidence score (0.0 - 1.0).
    autonomy_level:       Agent autonomy level (1=notify, 2=suggest, 3=auto-apply).
    confidence_threshold: Minimum confidence to skip HITL at L3.

    Returns
    -------
    The inserted agent_suggestion row dict.
    """
    # suspected_injection always forces HITL regardless of autonomy level
    suspected_injection = output.get("suspected_injection", False)
    hitl_required = suspected_injection or autonomy_level < 3 or confidence < confidence_threshold

    db = deps.db

    suggestion_payload: dict = {
        "tenant_id": deps.tenant_id,
        "agent_name": agent_name,
        "action_type": action_type,
        "input_snapshot": {"document_id": document_id},
        "output_snapshot": output,
        "confidence": str(confidence),  # NUMERIC column — send as string
        "status": "pending" if hitl_required else "auto_applied",
        "hitl_required": hitl_required,
    }
    # Only include the FK when we actually have a document — otherwise omit so
    # the column stores SQL NULL (matches schema: nullable REFERENCES documents).
    if document_id is not None:
        suggestion_payload["original_document_id"] = document_id

    suggestion = db.table("agent_suggestions").insert(suggestion_payload).execute().data[0]

    logger.info(
        "suggestion_writer: suggestion created",
        extra={
            "suggestion_id": suggestion.get("id"),
            "agent_name": agent_name,
            "tenant_id": deps.tenant_id,
            "hitl_required": hitl_required,
            "autonomy_level": autonomy_level,
            "confidence": confidence,
            "suspected_injection": suspected_injection,
        },
    )

    if hitl_required:
        # Priority escalation for low-confidence or injections
        if suspected_injection:
            priority = "critical"
        elif confidence < 0.5:
            priority = "high"
        else:
            priority = "med"

        title = f"Review: {agent_name.replace('_', ' ').title()}"
        if suspected_injection:
            title = f"[INJECTION DETECTED] {title}"

        db.table("hitl_tasks").insert(
            {
                "tenant_id": deps.tenant_id,
                "agent_suggestion_id": suggestion["id"],
                "kind": action_type,
                "priority": priority,
                "title": title,
                "description": (
                    f"Agent confidence: {confidence:.0%}. Please review before applying."
                    + (" SUSPECTED PROMPT INJECTION — do not auto-apply." if suspected_injection else "")
                ),
                "payload": output,
                "status": "open",
            }
        ).execute()

        logger.info(
            "suggestion_writer: hitl_task created",
            extra={
                "suggestion_id": suggestion.get("id"),
                "priority": priority,
                "suspected_injection": suspected_injection,
                "tenant_id": deps.tenant_id,
            },
        )

    return suggestion
