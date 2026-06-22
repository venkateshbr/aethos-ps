"""Agent kill-switch and circuit-breaker state updates."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Literal

logger = logging.getLogger(__name__)

_DEFAULT_ACTION_TYPE = "default"
_DEFAULT_FAILURE_THRESHOLD = 3
_CIRCUIT_OPEN_MINUTES = 15

ToolResultStatus = Literal["succeeded", "failed", "skipped", "running"]


class AgentCircuitBreaker:
    """Maintains operational circuit state for agent/tool control rows."""

    def __init__(self, db: object, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def record_tool_result(
        self,
        *,
        agent_name: str,
        action_type: str,
        status: ToolResultStatus,
        error_message: str | None = None,
    ) -> None:
        """Update agent-wide and tool/action circuit state for a tool outcome."""
        if status not in {"succeeded", "failed"}:
            return

        try:
            if status == "failed":
                await asyncio.to_thread(
                    lambda: self._record_failure(
                        agent_name=agent_name,
                        action_types=[_DEFAULT_ACTION_TYPE, action_type],
                        error_message=error_message,
                    )
                )
            else:
                await asyncio.to_thread(
                    lambda: self._record_success(
                        agent_name=agent_name,
                        action_types=[_DEFAULT_ACTION_TYPE, action_type],
                    )
                )
        except Exception:
            logger.warning(
                "agent_circuit_breaker_update_failed",
                exc_info=True,
                extra={
                    "tenant_id": self.tenant_id,
                    "agent_name": agent_name,
                    "action_type": action_type,
                    "status": status,
                },
            )

    def _record_failure(
        self,
        *,
        agent_name: str,
        action_types: list[str],
        error_message: str | None,
    ) -> None:
        now = datetime.datetime.now(datetime.UTC)
        for action_type in dict.fromkeys(action_types):
            row = self._fetch_row(agent_name, action_type)
            threshold = _positive_int(
                row.get("failure_threshold") if row else None,
                default=_DEFAULT_FAILURE_THRESHOLD,
            )
            failure_count = _positive_int(row.get("failure_count") if row else None) + 1
            patch: dict[str, object] = {
                "tenant_id": self.tenant_id,
                "agent_name": agent_name,
                "action_type": action_type,
                "failure_count": failure_count,
                "last_failure_at": now.isoformat(),
            }
            if failure_count >= threshold:
                patch.update(
                    {
                        "circuit_opened_at": now.isoformat(),
                        "circuit_open_until": (
                            now + datetime.timedelta(minutes=_CIRCUIT_OPEN_MINUTES)
                        ).isoformat(),
                        "circuit_open_reason": (error_message or "tool_failed")[:500],
                    }
                )

            self.db.table("agent_autonomy_settings").upsert(
                patch,
                on_conflict="tenant_id,agent_name,action_type",
            ).execute()

    def _record_success(self, *, agent_name: str, action_types: list[str]) -> None:
        patch = {
            "failure_count": 0,
            "last_failure_at": None,
            "circuit_opened_at": None,
            "circuit_open_until": None,
            "circuit_open_reason": None,
        }
        for action_type in dict.fromkeys(action_types):
            self.db.table("agent_autonomy_settings").update(patch).eq(
                "tenant_id", self.tenant_id
            ).eq("agent_name", agent_name).eq("action_type", action_type).execute()

    def _fetch_row(self, agent_name: str, action_type: str) -> dict | None:
        result = (
            self.db.table("agent_autonomy_settings")
            .select("failure_count,failure_threshold")
            .eq("tenant_id", self.tenant_id)
            .eq("agent_name", agent_name)
            .eq("action_type", action_type)
            .limit(1)
            .execute()
        )
        rows = getattr(result, "data", None) or []
        return rows[0] if rows else None


def _positive_int(value: object, *, default: int = 0) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(0, parsed)
