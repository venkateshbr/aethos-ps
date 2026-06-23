"""Repository: tenant-scoped data access for hitl_tasks and agent_suggestions."""

from __future__ import annotations

import asyncio
import logging

from app.services.agent_run_ledger import stable_payload_hash
from supabase import Client

logger = logging.getLogger(__name__)

_TASKS_TABLE = "hitl_tasks"
_SUGGESTIONS_TABLE = "agent_suggestions"
_CORRECTIONS_TABLE = "agent_corrections"
_EVAL_CANDIDATES_TABLE = "agent_eval_candidates"


class InboxRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_tasks(
        self,
        status: str | None = "open",
        kind: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Fetch hitl_tasks joined with agent_suggestions for confidence + payload.

        Returns a flat list of dicts with task fields plus agent-suggestion data
        merged in under keys ``agent_name``, ``confidence``, ``suggestion_payload``.
        """
        query = (
            self.db.table(_TASKS_TABLE)
            .select(
                "id,tenant_id,kind,priority,title,description,payload,status,created_at,updated_at,"
                "agent_suggestion_id,"
                "agent_suggestions(agent_name,confidence,output_snapshot,action_type)"
            )
            .eq("tenant_id", self.tenant_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status:
            query = query.eq("status", status)
        if kind:
            query = query.eq("kind", kind)

        result = await asyncio.to_thread(lambda: query.execute())
        rows = result.data or []
        return [self._flatten_task(r) for r in rows]

    async def get_task(self, task_id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self.db.table(_TASKS_TABLE)
            .select(
                "id,tenant_id,kind,priority,title,description,payload,status,created_at,updated_at,"
                "agent_suggestion_id,"
                "agent_suggestions(id,agent_name,confidence,output_snapshot,action_type,status)"
            )
            .eq("id", task_id)
            .eq("tenant_id", self.tenant_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return self._flatten_task(result.data[0])

    async def get_suggestion(self, suggestion_id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self.db.table(_SUGGESTIONS_TABLE)
            .select("*")
            .eq("id", suggestion_id)
            .eq("tenant_id", self.tenant_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Write — tasks
    # ------------------------------------------------------------------

    async def mark_done(self, task_id: str, decided_by: str) -> None:
        await asyncio.to_thread(
            lambda: self.db.table(_TASKS_TABLE)
            .update({"status": "done"})
            .eq("id", task_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )

    async def update_task(self, task_id: str, patch: dict) -> None:
        await asyncio.to_thread(
            lambda: self.db.table(_TASKS_TABLE)
            .update(patch)
            .eq("id", task_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )

    # ------------------------------------------------------------------
    # Write — suggestions
    # ------------------------------------------------------------------

    async def update_suggestion_status(
        self,
        suggestion_id: str,
        new_status: str,
        decided_by: str,
    ) -> None:
        from datetime import UTC, datetime

        await asyncio.to_thread(
            lambda: self.db.table(_SUGGESTIONS_TABLE)
            .update(
                {
                    "status": new_status,
                    "decided_by": decided_by,
                    "decided_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", suggestion_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )

    # ------------------------------------------------------------------
    # Write — corrections (append-only training signal)
    # ------------------------------------------------------------------

    async def record_correction(
        self,
        suggestion_id: str,
        agent_name: str,
        action_type: str,
        original_output: dict,
        corrected_output: dict | None,
        correction_type: str,
        corrected_by: str,
    ) -> None:
        """Insert an agent_corrections row.  Corrections are immutable once recorded."""
        payload = {
            "tenant_id": self.tenant_id,
            "agent_suggestion_id": suggestion_id,
            "agent_name": agent_name,
            "action_type": action_type,
            "original_output": original_output,
            "corrected_output": corrected_output or {},
            "correction_type": correction_type,
            "corrected_by": corrected_by,
        }
        result = await asyncio.to_thread(
            lambda: self.db.table(_CORRECTIONS_TABLE).insert(payload).execute()
        )
        rows = getattr(result, "data", None) or []
        correction_id = rows[0].get("id") if rows else None
        if correction_id:
            await self._record_eval_candidate(
                correction_id=str(correction_id),
                suggestion_id=suggestion_id,
                agent_name=agent_name,
                action_type=action_type,
                original_output=original_output,
                corrected_output=corrected_output or {},
                correction_type=correction_type,
            )

    async def _record_eval_candidate(
        self,
        *,
        correction_id: str,
        suggestion_id: str,
        agent_name: str,
        action_type: str,
        original_output: dict,
        corrected_output: dict,
        correction_type: str,
    ) -> None:
        """Best-effort eval-candidate index for human corrections."""
        try:
            suggestion = await self.get_suggestion(suggestion_id)
            input_snapshot = (
                suggestion.get("input_snapshot") if isinstance(suggestion, dict) else None
            )
            payload = {
                "tenant_id": self.tenant_id,
                "agent_correction_id": correction_id,
                "agent_suggestion_id": suggestion_id,
                "agent_name": agent_name,
                "action_type": action_type,
                "eval_case_key": f"{agent_name}:{action_type}:correction:{correction_id}",
                "input_hash": (
                    stable_payload_hash(input_snapshot)
                    if input_snapshot is not None
                    else None
                ),
                "original_output_hash": stable_payload_hash(original_output),
                "corrected_output_hash": stable_payload_hash(corrected_output),
                "reason": f"human_{correction_type}",
            }
            await asyncio.to_thread(
                lambda: self.db.table(_EVAL_CANDIDATES_TABLE)
                .upsert(payload, on_conflict="tenant_id,agent_correction_id")
                .execute()
            )
        except Exception:
            logger.warning(
                "agent_eval_candidate_record_failed",
                exc_info=True,
                extra={
                    "tenant_id": self.tenant_id,
                    "agent_name": agent_name,
                    "action_type": action_type,
                    "agent_correction_id": correction_id,
                },
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _flatten_task(row: dict) -> dict:
        """Merge the nested agent_suggestions object into the task dict."""
        suggestion = row.pop("agent_suggestions", None) or {}
        row["agent_name"] = suggestion.get("agent_name", "unknown")
        row["confidence"] = str(suggestion.get("confidence", "0"))
        row["suggestion_payload"] = suggestion.get("output_snapshot", {})
        row["action_type"] = suggestion.get("action_type", "")
        row["suggestion_id"] = suggestion.get("id", row.get("agent_suggestion_id"))
        row["suggestion_status"] = suggestion.get("status", "pending")
        return row
