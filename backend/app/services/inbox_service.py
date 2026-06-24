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
from datetime import date
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
        payload = self._task_materialisation_payload(task)
        kind = task.get("kind", "")
        # `agent_name` was previously read here for the record_correction call
        # that lived under the plain-approve path — removed in #126 because the
        # agent_corrections table only accepts edit/reject correction_type.

        entity = await self._materialise(kind, payload, user_id=user_id)

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
            materialisation=entity,
        )

    async def approve_with_edits(
        self, task_id: str, corrected_payload: dict, user_id: str
    ) -> ApproveResponse:
        task = await self._get_open_task_or_raise(task_id)
        suggestion_id = task.get("agent_suggestion_id") or task.get("suggestion_id")
        original = self._task_materialisation_payload(task)
        corrected_payload = self._payload_with_task_metadata(corrected_payload, task)
        kind = task.get("kind", "")
        agent_name = task.get("agent_name", "unknown")

        entity = await self._materialise(kind, corrected_payload, user_id=user_id)

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
            materialisation=entity,
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

    @staticmethod
    def _task_materialisation_payload(task: dict) -> dict:
        """Use task payload metadata plus immutable suggestion output for approval.

        The repository exposes ``suggestion_payload`` from
        ``agent_suggestions.output_snapshot`` and ``payload`` from the HITL task.
        Source-document metadata lives on the task payload so approval can
        materialise rows with the correct FK even when the immutable suggestion
        snapshot predates that metadata.
        """
        suggestion_payload = task.get("suggestion_payload") or {}
        task_payload = task.get("payload") or {}
        if not isinstance(suggestion_payload, dict):
            suggestion_payload = {}
        if not isinstance(task_payload, dict):
            task_payload = {}
        return {**suggestion_payload, **task_payload}

    @staticmethod
    def _payload_with_task_metadata(payload: dict, task: dict) -> dict:
        """Preserve non-editable task metadata when approving with edits."""
        result = dict(payload)
        task_payload = task.get("payload") or {}
        if isinstance(task_payload, dict) and "original_document_id" not in result:
            original_document_id = task_payload.get("original_document_id")
            if original_document_id:
                result["original_document_id"] = original_document_id
        return result

    async def _materialise(
        self,
        kind: str,
        payload: dict,
        *,
        user_id: str | None = None,
    ) -> dict:
        """Route materialisation by kind.  Returns entity_type + entity_id.

        The extraction worker emits the ``*_draft`` kinds; earlier kinds without
        the suffix are accepted too for backward-compatibility. Before this fix
        the dispatch only matched the suffix-less names, so every approval fell
        through to the no-op branch and silently created nothing (#146 follow-up).
        """
        if kind in ("create_engagement", "create_engagement_draft"):
            return await self._materialise_engagement(payload)
        elif kind in ("create_expense", "create_expense_draft"):
            return await self._materialise_expense(payload)
        elif kind in ("create_bill", "create_bill_draft", "vendor_invoice"):
            return await self._materialise_bill(payload)
        elif kind in (
            "copilot_log_time_entry",
            "copilot_update_rate_card",
            "copilot_draft_invoice",
            "copilot_prepare_month_end_close",
            "copilot_create_finance_ops_action_plan",
        ):
            return await self._materialise_copilot_tool(payload)
        elif kind == "approve_billing_run":
            return await self._materialise_billing_run(payload)
        elif kind == "send_email":
            return await self._materialise_collections_email(payload)
        elif kind == "send_time_entry_reminder":
            return await self._materialise_time_entry_reminder(payload)
        elif kind == "create_bill_payment_batch":
            return await self._materialise_bill_payment_batch(payload, user_id=user_id)
        elif kind in ("draft_journal", "create_journal", "create_manual_journal"):
            return await self._materialise_journal(payload, user_id=user_id)
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

    async def _materialise_copilot_tool(self, payload: dict) -> dict:
        tool_name = payload.get("tool_name")
        if tool_name not in (
            "log_time_entry",
            "update_rate_card",
            "draft_invoice",
            "prepare_month_end_close",
            "create_finance_ops_action_plan",
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported Copilot tool approval: {tool_name!r}",
            )

        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Copilot tool payload must include a tool_input object",
            )

        from app.agents.copilot.graph import CopilotAgent, CopilotDeps

        agent = CopilotAgent(
            CopilotDeps(
                tenant_id=self._tenant_id,
                user_id=str(payload.get("requested_by_user_id") or ""),
                db_client=self._db,
            )
        )
        if tool_name == "draft_invoice" and isinstance(payload.get("invoice_draft"), dict):
            result = await agent._persist_invoice_draft_payload(payload["invoice_draft"])
        elif tool_name == "create_finance_ops_action_plan":
            return {
                "entity_type": "finance_ops_action_plan",
                "entity_id": str(payload.get("plan_id") or ""),
                "action_count": payload.get("action_count", 0),
                "approval_effect": payload.get("approval_effect"),
            }
        else:
            result = await agent._execute_tool(tool_name, tool_input)
        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Approved Copilot tool failed: {result['error']}",
            )

        if tool_name == "log_time_entry":
            return {"entity_type": "time_entry", "entity_id": result.get("entry_id")}
        if tool_name == "draft_invoice":
            return {"entity_type": "invoice", "entity_id": result.get("invoice_id")}
        if tool_name == "prepare_month_end_close":
            return {"entity_type": "month_end_close", "entity_id": result.get("period")}
        return {"entity_type": "rate_card", "entity_id": result.get("rate_card_line_id")}

    async def _materialise_billing_run(self, payload: dict) -> dict:
        billing_run_id = payload.get("billing_run_id")
        if not billing_run_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Billing run approval payload must include billing_run_id",
            )

        from app.agents.base import AgentDeps
        from app.api.v1.endpoints.billing_runs import _draft_invoices_for_run
        from app.repositories.billing_runs_repo import BillingRunsRepository

        repo = BillingRunsRepository(self._db, self._tenant_id)
        row = await repo.get_by_id(str(billing_run_id))
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Billing run not found",
            )
        if row["status"] not in ("draft", "reviewed"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot approve billing run with status={row['status']!r}",
            )

        updated = await repo.update(str(billing_run_id), {"status": "approved"})
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Billing run not found after update",
            )

        deps = AgentDeps(
            tenant_id=self._tenant_id,
            user_id="billing_run_agent",
            db=self._db,
        )
        await _draft_invoices_for_run(updated, deps)
        return {"entity_type": "billing_run", "entity_id": str(billing_run_id)}

    async def _materialise_collections_email(self, payload: dict) -> dict:
        client_email = str(payload.get("client_email") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        body_html = str(payload.get("body_html") or "").strip()
        invoice_id = str(payload.get("invoice_id") or "").strip() or None

        missing = [
            name
            for name, value in (
                ("client_email", client_email),
                ("subject", subject),
                ("body_html", body_html),
            )
            if not value
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Collections email payload missing: {', '.join(missing)}",
            )

        from app.services.resend_service import ResendService

        result = ResendService().send_email(client_email, subject, body_html)
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collections email failed: {result.get('error', 'unknown error')}",
            )

        return {
            "entity_type": "collections_email",
            "entity_id": invoice_id,
            "send_status": result.get("status", "sent"),
        }

    async def _materialise_time_entry_reminder(self, payload: dict) -> dict:
        employee_email = str(payload.get("employee_email") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        body_html = str(payload.get("body_html") or "").strip()
        employee_id = str(payload.get("employee_id") or "").strip() or None

        missing = [
            name
            for name, value in (
                ("employee_email", employee_email),
                ("subject", subject),
                ("body_html", body_html),
            )
            if not value
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Time entry reminder payload missing: {', '.join(missing)}",
            )

        from app.services.resend_service import ResendService

        result = ResendService().send_email(employee_email, subject, body_html)
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Time entry reminder failed: {result.get('error', 'unknown error')}",
            )

        return {
            "entity_type": "time_entry_reminder",
            "entity_id": employee_id,
            "send_status": result.get("status", "sent"),
        }

    async def _materialise_bill_payment_batch(
        self,
        payload: dict,
        *,
        user_id: str | None = None,
    ) -> dict:
        bill_ids = payload.get("proposed_bill_ids") or payload.get("bill_ids") or []
        if not isinstance(bill_ids, list) or not all(isinstance(v, str) for v in bill_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Bill payment proposal must include proposed_bill_ids",
            )

        pay_date = None
        if payload.get("proposed_pay_date"):
            try:
                pay_date = date.fromisoformat(str(payload["proposed_pay_date"]))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Invalid proposed_pay_date",
                ) from exc

        from app.services.bill_payments_service import BillPaymentsService

        created_by = str(user_id or payload.get("requested_by_user_id") or "").strip()
        if not created_by:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Bill payment approval requires a deciding user id",
            )

        batch = BillPaymentsService(self._db, self._tenant_id).create_batch(
            bill_ids,
            pay_date,
            str(payload.get("bank_account_label") or ""),
            created_by=created_by,
        )
        return {"entity_type": "bill_payment_batch", "entity_id": str(batch["id"])}

    async def _materialise_journal(
        self,
        payload: dict,
        *,
        user_id: str | None,
    ) -> dict:
        """Post a HITL-approved journal proposal through the manual journal service."""
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Journal approval requires a deciding user id",
            )

        journal_payload = payload.get("journal_entry") or payload.get("journal") or payload
        if not isinstance(journal_payload, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Journal proposal payload must be an object",
            )

        from pydantic import ValidationError

        from app.models.accounting import ManualJournalEntryIn
        from app.services.manual_journal_service import ManualJournalService

        try:
            journal = ManualJournalEntryIn.model_validate(journal_payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=exc.errors(),
            ) from exc

        posted = await ManualJournalService(
            db=self._db,
            tenant_id=self._tenant_id,
            user_id=user_id,
        ).post_manual_journal(journal)
        return {"entity_type": "journal_entry", "entity_id": posted.id}

    async def _materialise_engagement(self, payload: dict) -> dict:
        import asyncio

        client_name = _non_empty(payload.get("client_name")) or "Unknown Client"

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

        engagement_currency = (_non_empty(payload.get("currency")) or "USD").upper()
        engagement_name = (
            _non_empty(payload.get("engagement_name"))
            or f"{client_name} Engagement"
        )
        total_value = (
            str(Decimal(str(payload["total_value"])))
            if payload.get("total_value")
            else None
        )
        eng_row = await asyncio.to_thread(
            lambda: self._db.table("engagements")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "client_id": client_id,
                    "name": engagement_name,
                    "billing_arrangement": payload.get("billing_arrangement", "time_and_materials"),
                    "currency": engagement_currency,
                    "total_value": total_value,
                    "description": _non_empty(payload.get("scope_summary")),
                    "start_date": _non_empty(payload.get("start_date")),
                    "end_date": _non_empty(payload.get("end_date")),
                    "status": "draft",
                    "source_document_id": self._source_document_id(payload),  # #127
                }
            )
            .execute()
        )
        engagement_id = str(eng_row.data[0]["id"])

        # Auto-create the reviewed first project so the user can log time
        # against the engagement immediately, without a manual project-create
        # step. When older payloads lack first-project fields we keep the
        # historical "General" fallback.
        project_id: str | None = None
        project_name = _non_empty(payload.get("first_project_name")) or "General"
        try:
            project_row = await asyncio.to_thread(
                lambda: self._db.table("projects")
                .insert(
                    {
                        "tenant_id": self._tenant_id,
                        "engagement_id": engagement_id,
                        "name": project_name,
                        "description": (
                            _non_empty(payload.get("first_project_description"))
                            or _non_empty(payload.get("scope_summary"))
                        ),
                        "currency": engagement_currency,
                        "budget": total_value,
                        "start_date": _non_empty(payload.get("start_date")),
                        "end_date": _non_empty(payload.get("end_date")),
                        "status": "planning",
                    }
                )
                .execute()
            )
            if project_row.data:
                project_id = str(project_row.data[0]["id"])
        except Exception as exc:
            logger.warning(
                "Auto-create first project failed for engagement %s: %s",
                engagement_id,
                exc,
            )

        return {
            "entity_type": "engagement",
            "entity_id": engagement_id,
            "client_id": str(client_id),
            "project_id": project_id,
            "project_name": project_name,
        }

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


def _non_empty(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _row_to_summary(row: dict) -> HitlTaskSummary:
    return HitlTaskSummary(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
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
        tenant_id=str(row["tenant_id"]),
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
