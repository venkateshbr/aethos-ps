"""Business logic for the HITL Inbox.

Flow:
  list_tasks     → paginated open tasks with suggestion metadata merged in
  get_task       → full task detail for review UI
  approve        → materialise suggestion as-is, record correction(type=none), mark done
  approve_with_edits → materialise corrected payload, record correction(type=edit), mark done
  reject         → record correction(type=reject), mark done — nothing materialised
  escalate       → raise priority to critical, assign to tenant owner

All mutation methods guard against double-processing (status==done → 409).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import HTTPException, status

from app.models.inbox import (
    ApproveResponse,
    EscalateResponse,
    HitlTaskDetail,
    HitlTaskListResponse,
    HitlTaskSummary,
    RejectResponse,
)
from app.repositories.inbox_repo import InboxRepository
from supabase import Client

logger = logging.getLogger(__name__)


class InboxService:
    """Orchestrates HITL task resolution: fetch, decide, materialise, audit."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self._repo = InboxRepository(db, tenant_id)
        self._db = db
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_tasks(
        self,
        status_filter: str | None = "open",
        kind: str | None = None,
        limit: int = 50,
    ) -> HitlTaskListResponse:
        rows = await self._repo.list_tasks(status=status_filter, kind=kind, limit=limit)
        items = [_row_to_summary(r) for r in rows]
        return HitlTaskListResponse(items=items, total=len(items))

    async def get_task(self, task_id: str) -> HitlTaskDetail | None:
        row = await self._repo.get_task(task_id)
        if row is None:
            return None
        return _row_to_detail(row)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def approve(self, task_id: str, user_id: str) -> ApproveResponse:
        task = await self._get_open_task_or_raise(task_id)
        suggestion_id = task.get("agent_suggestion_id") or task.get("suggestion_id")
        payload = task.get("suggestion_payload", {})
        kind = task.get("kind", "")
        agent_name = task.get("agent_name", "unknown")

        entity = await self._materialise(kind, payload)

        if suggestion_id:
            await self._repo.update_suggestion_status(suggestion_id, "approved", user_id)
            # Note: do NOT write an agent_corrections row on plain approve.
            # The `agent_corrections` table records EDITS and REJECTIONS only
            # (enum agent_correction_type = 'edit' | 'reject'). Plain approvals
            # are already captured by `agent_suggestions.status='approved'`.
            # Writing a "none" correction was a copy-paste from approve_with_edits
            # that crashed because "none" is not a valid enum value (#124).
            # Approval rate for autonomy promotion is computed from
            # agent_suggestions.status, not from this table.

        await self._repo.mark_done(task_id, decided_by=user_id)

        return ApproveResponse(
            materialised=True,
            entity_id=entity.get("entity_id"),
            entity_type=entity.get("entity_type"),
            message=f"Task {task_id} approved and materialised as {entity.get('entity_type', kind)}",
        )

    async def approve_with_edits(
        self, task_id: str, corrected_payload: dict, user_id: str
    ) -> ApproveResponse:
        task = await self._get_open_task_or_raise(task_id)
        suggestion_id = task.get("agent_suggestion_id") or task.get("suggestion_id")
        original = task.get("suggestion_payload", {})
        kind = task.get("kind", "")
        agent_name = task.get("agent_name", "unknown")

        entity = await self._materialise(kind, corrected_payload)

        if suggestion_id:
            await self._repo.update_suggestion_status(suggestion_id, "approved", user_id)
            await self._repo.record_correction(
                suggestion_id=suggestion_id,
                agent_name=agent_name,
                action_type=kind,
                original_output=original,
                corrected_output=corrected_payload,
                correction_type="edit",
                corrected_by=user_id,
            )

        await self._repo.mark_done(task_id, decided_by=user_id)

        return ApproveResponse(
            materialised=True,
            entity_id=entity.get("entity_id"),
            entity_type=entity.get("entity_type"),
            message=f"Task {task_id} approved with edits and materialised as {entity.get('entity_type', kind)}",
        )

    async def reject(self, task_id: str, reason: str, user_id: str) -> RejectResponse:
        task = await self._get_open_task_or_raise(task_id)
        suggestion_id = task.get("agent_suggestion_id") or task.get("suggestion_id")
        agent_name = task.get("agent_name", "unknown")
        kind = task.get("kind", "")

        if suggestion_id:
            await self._repo.update_suggestion_status(suggestion_id, "rejected", user_id)
            await self._repo.record_correction(
                suggestion_id=suggestion_id,
                agent_name=agent_name,
                action_type=kind,
                original_output=task.get("suggestion_payload", {}),
                corrected_output={"reason": reason},
                correction_type="reject",
                corrected_by=user_id,
            )

        await self._repo.mark_done(task_id, decided_by=user_id)

        return RejectResponse(rejected=True, task_id=task_id)

    async def escalate(self, task_id: str, user_id: str) -> EscalateResponse:
        import asyncio

        row = await self._repo.get_task(task_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id!r} not found",
            )

        # Find the tenant owner
        owner_result = await asyncio.to_thread(
            lambda: self._db.table("tenant_users")
            .select("user_id")
            .eq("tenant_id", self._tenant_id)
            .eq("role", "owner")
            .limit(1)
            .execute()
        )
        owner_id = (
            owner_result.data[0]["user_id"] if owner_result.data else user_id
        )

        await self._repo.update_task(
            task_id,
            {"priority": "critical", "assigned_to": owner_id},
        )

        return EscalateResponse(
            escalated=True,
            task_id=task_id,
            message=f"Task {task_id} escalated to critical priority and assigned to tenant owner",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_open_task_or_raise(self, task_id: str) -> dict:
        task = await self._repo.get_task(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id!r} not found",
            )
        if task.get("status") == "done":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task {task_id!r} has already been resolved",
            )
        return task

    async def _materialise(self, kind: str, payload: dict) -> dict:
        """Route materialisation by kind.  Returns entity_type + entity_id."""
        if kind == "create_engagement":
            return await self._materialise_engagement(payload)
        elif kind == "create_expense":
            return await self._materialise_expense(payload)
        elif kind in ("create_bill", "vendor_invoice"):
            return await self._materialise_bill(payload)
        else:
            logger.warning("Unknown materialisation kind %r — skipping", kind)
            return {"entity_type": kind, "entity_id": None}

    @staticmethod
    def _source_document_id(payload: dict) -> str | None:
        """Source-document FK plumbing (#127).

        `suggestion_writer` mirrors `original_document_id` into the suggestion
        payload, so every approve/approve_with_edits path can carry the link
        back into the materialised row without an extra DB lookup.
        """
        return payload.get("original_document_id")

    async def _materialise_engagement(self, payload: dict) -> dict:
        import asyncio

        client_name = payload.get("client_name", "Unknown Client")

        # Find or create client
        existing = await asyncio.to_thread(
            lambda: self._db.table("clients")
            .select("id")
            .eq("tenant_id", self._tenant_id)
            .ilike("name", client_name)
            .limit(1)
            .execute()
        )
        if existing.data:
            client_id = existing.data[0]["id"]
        else:
            client_row = await asyncio.to_thread(
                lambda: self._db.table("clients")
                .insert(
                    {
                        "tenant_id": self._tenant_id,
                        "name": client_name,
                        "kind": "customer",
                    }
                )
                .execute()
            )
            client_id = client_row.data[0]["id"]

        eng_row = await asyncio.to_thread(
            lambda: self._db.table("engagements")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "client_id": client_id,
                    "name": payload.get("engagement_name") or f"{client_name} Engagement",
                    "billing_arrangement": payload.get("billing_arrangement", "time_and_materials"),
                    "currency": payload.get("currency", "USD"),
                    "total_value": (
                        str(Decimal(str(payload["total_value"])))
                        if payload.get("total_value")
                        else None
                    ),
                    "status": "draft",
                    "source_document_id": self._source_document_id(payload),  # #127
                }
            )
            .execute()
        )
        return {"entity_type": "engagement", "entity_id": str(eng_row.data[0]["id"])}

    async def _materialise_expense(self, payload: dict) -> dict:
        import asyncio

        project_id = payload.get("project_id")
        if not project_id:
            logger.warning("Cannot materialise expense — project_id missing from payload")
            return {
                "entity_type": "expense",
                "entity_id": None,
                "note": "project_id required",
            }

        amount = Decimal(str(payload.get("amount", "0")))
        exp_row = await asyncio.to_thread(
            lambda: self._db.table("project_expenses")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "project_id": project_id,
                    "description": payload.get("vendor") or payload.get("description") or "Expense",
                    "amount": str(amount),
                    "currency": payload.get("currency", "USD"),
                    "base_amount": str(amount),
                    "expense_date": payload.get("expense_date"),
                    "category": payload.get("category", "other"),
                    "billable": payload.get("billable", True),
                    "document_id": self._source_document_id(payload),  # #127 — column existed from 0007, never populated
                }
            )
            .execute()
        )
        return {"entity_type": "expense", "entity_id": str(exp_row.data[0]["id"])}

    async def _materialise_bill(self, payload: dict) -> dict:
        import asyncio

        vendor_name = payload.get("vendor_name") or payload.get("vendor", "Unknown Vendor")

        # Find or create vendor client
        existing = await asyncio.to_thread(
            lambda: self._db.table("clients")
            .select("id")
            .eq("tenant_id", self._tenant_id)
            .eq("kind", "vendor")
            .ilike("name", vendor_name)
            .limit(1)
            .execute()
        )
        if existing.data:
            client_id = existing.data[0]["id"]
        else:
            client_row = await asyncio.to_thread(
                lambda: self._db.table("clients")
                .insert(
                    {
                        "tenant_id": self._tenant_id,
                        "name": vendor_name,
                        "kind": "vendor",
                    }
                )
                .execute()
            )
            client_id = client_row.data[0]["id"]

        subtotal = Decimal(str(payload.get("subtotal") or payload.get("amount", "0")))
        tax_total = Decimal(str(payload.get("tax_total", "0")))
        total = Decimal(str(payload.get("total", "0"))) or (subtotal + tax_total)

        bill_row = await asyncio.to_thread(
            lambda: self._db.table("bills")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "client_id": client_id,
                    "currency": payload.get("currency", "USD"),
                    "subtotal": str(subtotal),
                    "tax_total": str(tax_total),
                    "total": str(total),
                    "vendor_invoice_number": payload.get("vendor_invoice_number"),
                    "issue_date": payload.get("issue_date"),
                    "due_date": payload.get("due_date"),
                    "source_document_id": self._source_document_id(payload),  # #127
                }
            )
            .execute()
        )
        return {"entity_type": "bill", "entity_id": str(bill_row.data[0]["id"])}


# ------------------------------------------------------------------
# Mapping helpers
# ------------------------------------------------------------------


def _row_to_summary(row: dict) -> HitlTaskSummary:
    return HitlTaskSummary(
        id=str(row["id"]),
        kind=row.get("kind", ""),
        priority=row.get("priority", "normal"),
        title=row.get("title", ""),
        agent_name=row.get("agent_name", "unknown"),
        confidence=row.get("confidence", "0"),
        status=row.get("status", "open"),
        created_at=str(row.get("created_at", "")),
        suggestion_payload=row.get("suggestion_payload", {}),
    )


def _row_to_detail(row: dict) -> HitlTaskDetail:
    return HitlTaskDetail(
        id=str(row["id"]),
        kind=row.get("kind", ""),
        priority=row.get("priority", "normal"),
        title=row.get("title", ""),
        agent_name=row.get("agent_name", "unknown"),
        confidence=row.get("confidence", "0"),
        status=row.get("status", "open"),
        created_at=str(row.get("created_at", "")),
        suggestion_payload=row.get("suggestion_payload", {}),
        description=row.get("description"),
        payload=row.get("payload", {}),
    )
