"""Best-effort persistence for agent run and tool-call provenance."""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import json
import logging
import uuid
from typing import Any, Literal

from app.agents.base import mask_pii
from app.agents.tool_registry import ToolRiskClass
from app.services.agent_circuit_breaker import AgentCircuitBreaker

logger = logging.getLogger(__name__)

AgentRunStatus = Literal["running", "succeeded", "failed", "cancelled"]
ToolInvocationStatus = Literal["running", "succeeded", "failed", "skipped"]


def stable_payload_hash(payload: Any) -> str:
    """Return a deterministic sha256 hash for JSON-like payloads."""
    normalized = _json_dumps(_json_safe(payload))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def safe_snapshot(payload: Any) -> Any:
    """Return a JSON-safe, lightly PII-masked payload snapshot."""
    return _json_safe(_mask_payload(payload))


class AgentRunLedger:
    """Small interface over the agent run ledger tables.

    The ledger is intentionally best-effort: audit-write failures are logged but
    do not block ERP workflows or agent responses.
    """

    def __init__(self, db: object, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def start_run(
        self,
        *,
        agent_name: str,
        trigger_type: str,
        user_id: str | None = None,
        input_payload: Any | None = None,
        prompt_version: str | None = None,
        model_version: str | None = None,
        source_document_id: str | None = None,
        source_document_hash: str | None = None,
        trace_id: str | None = None,
        replay_pointer: str | None = None,
    ) -> str | None:
        row: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "agent_name": agent_name,
            "trigger_type": trigger_type,
            "status": "running",
        }
        if user_uuid := _uuid_or_none(user_id):
            row["user_id"] = user_uuid
        if input_payload is not None:
            row["input_hash"] = stable_payload_hash(input_payload)
        if prompt_version:
            row["prompt_version"] = prompt_version
        if model_version:
            row["model_version"] = model_version
        if source_uuid := _uuid_or_none(source_document_id):
            row["source_document_id"] = source_uuid
        if source_document_hash:
            row["source_document_hash"] = source_document_hash
        if trace_id:
            row["trace_id"] = trace_id
        if replay_pointer:
            row["replay_pointer"] = replay_pointer

        try:
            result = await asyncio.to_thread(
                lambda: self.db.table("agent_runs").insert(row).execute()
            )
            data = getattr(result, "data", None) or []
            return str(data[0]["id"]) if data else None
        except Exception:
            logger.warning(
                "agent_run_ledger_start_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id, "agent_name": agent_name},
            )
            return None

    async def complete_run(
        self,
        run_id: str | None,
        *,
        status: AgentRunStatus,
        output_payload: Any | None = None,
        error_message: str | None = None,
        model_version: str | None = None,
        usage_input_tokens: int | None = None,
        usage_output_tokens: int | None = None,
        cost_usd: str | None = None,
    ) -> None:
        if not run_id:
            return

        patch: dict[str, Any] = {
            "status": status,
            "completed_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        if output_payload is not None:
            patch["output_hash"] = stable_payload_hash(output_payload)
        if error_message:
            patch["error_message"] = error_message[:1000]
        if model_version:
            patch["model_version"] = model_version
        if usage_input_tokens is not None:
            patch["usage_input_tokens"] = usage_input_tokens
        if usage_output_tokens is not None:
            patch["usage_output_tokens"] = usage_output_tokens
        if cost_usd is not None:
            patch["cost_usd"] = cost_usd

        try:
            await asyncio.to_thread(
                lambda: self.db.table("agent_runs").update(patch).eq("id", run_id).execute()
            )
        except Exception:
            logger.warning(
                "agent_run_ledger_complete_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id, "agent_run_id": run_id},
            )

    async def record_tool_invocation(
        self,
        run_id: str | None,
        *,
        agent_name: str | None = None,
        action_type: str | None = None,
        tool_name: str,
        risk_class: ToolRiskClass,
        input_payload: Any | None,
        output_payload: Any | None,
        status: ToolInvocationStatus,
        duration_ms: int | None = None,
        error_message: str | None = None,
        external_tool_call_id: str | None = None,
    ) -> None:
        if not run_id:
            return

        row: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "agent_run_id": run_id,
            "tool_name": tool_name,
            "risk_class": risk_class,
            "status": status,
        }
        if external_tool_call_id:
            row["external_tool_call_id"] = external_tool_call_id
        if input_payload is not None:
            row["input_hash"] = stable_payload_hash(input_payload)
            row["input_snapshot"] = safe_snapshot(input_payload)
        if output_payload is not None:
            row["output_hash"] = stable_payload_hash(output_payload)
            row["output_snapshot"] = safe_snapshot(output_payload)
        if duration_ms is not None:
            row["duration_ms"] = max(0, duration_ms)
        if error_message:
            row["error_message"] = error_message[:1000]

        try:
            await asyncio.to_thread(
                lambda: self.db.table("agent_tool_invocations").insert(row).execute()
            )
        except Exception:
            logger.warning(
                "agent_tool_invocation_record_failed",
                exc_info=True,
                extra={
                    "tenant_id": self.tenant_id,
                    "agent_run_id": run_id,
                    "tool_name": tool_name,
                },
            )
        if agent_name and action_type:
            await AgentCircuitBreaker(self.db, self.tenant_id).record_tool_result(
                agent_name=agent_name,
                action_type=action_type,
                status=status,
                error_message=error_message,
            )


def _uuid_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _json_safe(payload: Any) -> Any:
    return json.loads(_json_dumps(payload))


def _json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _mask_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {str(key): _mask_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_mask_payload(value) for value in payload]
    if isinstance(payload, tuple):
        return [_mask_payload(value) for value in payload]
    if isinstance(payload, str):
        return mask_pii(payload)
    return payload
