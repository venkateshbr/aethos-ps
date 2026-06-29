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

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status

from app.core.rbac import ROLE_HIERARCHY, UserRole
from app.domain.money import serialise_money
from app.models.inbox import (
    ApproveResponse,
    EscalateResponse,
    HitlDecisionEvent,
    HitlTaskDetail,
    HitlTaskListResponse,
    HitlTaskSummary,
    RejectResponse,
)
from app.repositories.inbox_repo import InboxRepository
from app.services.agent_run_ledger import stable_payload_hash
from app.services.approval_policy import (
    ApprovalPolicyDecision,
    ApprovalPolicyMatrix,
    ApprovalPolicySettings,
)
from app.services.approval_policy_settings_service import ApprovalPolicySettingsService
from supabase import Client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApprovalCheck:
    decision: ApprovalPolicyDecision
    user_role: UserRole
    payload: dict


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
        histories = await self._repo.list_decision_events_for_tasks(
            [str(row["id"]) for row in rows],
            limit_per_task=3,
        )
        policy = await self._approval_policy_settings()
        items = [
            _row_to_summary(
                r,
                decision_history=histories.get(str(r["id"]), []),
                policy=policy,
            )
            for r in rows
        ]
        return HitlTaskListResponse(items=items, total=len(items))

    async def get_task(self, task_id: str) -> HitlTaskDetail | None:
        row = await self._repo.get_task(task_id)
        if row is None:
            return None
        history = await self._repo.list_decision_events_for_task(task_id)
        policy = await self._approval_policy_settings()
        return _row_to_detail(row, decision_history=history, policy=policy)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def approve(self, task_id: str, user_id: str) -> ApproveResponse:
        task = await self._get_open_task_or_raise(task_id)
        check = await self._enforce_approval_policy(task, user_id, action="approve")
        suggestion_id = task.get("agent_suggestion_id") or task.get("suggestion_id")
        payload = check.payload
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
        await self._record_decision_event(
            task,
            event_type="hitl_task.approved",
            action="approved",
            actor_user_id=user_id,
            actor_role=check.user_role,
            decision=check.decision,
            before_payload=payload,
            after_payload=payload,
            materialisation=entity,
            idempotency_key=f"hitl_task.approved:{task_id}",
        )

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

        check = await self._enforce_approval_policy(
            task,
            user_id,
            payload_override=corrected_payload,
            action="approve_with_edits",
        )

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
        await self._record_decision_event(
            task,
            event_type="hitl_task.approved_with_edits",
            action="approved_with_edits",
            actor_user_id=user_id,
            actor_role=check.user_role,
            decision=check.decision,
            before_payload=original,
            after_payload=corrected_payload,
            materialisation=entity,
            idempotency_key=f"hitl_task.approved_with_edits:{task_id}",
        )

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
        user_role = await self._fetch_user_role(user_id)
        payload = self._task_materialisation_payload(task)
        decision = ApprovalPolicyMatrix.decision_for_task(
            kind,
            payload,
            settings=await self._approval_policy_settings(),
        )

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
        await self._record_decision_event(
            task,
            event_type="hitl_task.rejected",
            action="rejected",
            actor_user_id=user_id,
            actor_role=user_role,
            decision=decision,
            before_payload=payload,
            after_payload={"reason": _truncate(reason, 500)},
            materialisation=None,
            idempotency_key=f"hitl_task.rejected:{task_id}",
        )
        await self._record_manual_journal_rejected_event(
            task,
            payload=payload,
            reason=reason,
            actor_user_id=user_id,
            actor_role=user_role,
            decision=decision,
        )

        return RejectResponse(rejected=True, task_id=task_id)

    async def escalate(self, task_id: str, user_id: str) -> EscalateResponse:
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

    async def _enforce_approval_policy(
        self,
        task: dict,
        user_id: str,
        *,
        payload_override: dict | None = None,
        action: str,
    ) -> ApprovalCheck:
        kind = str(task.get("kind") or "")
        payload = payload_override or self._task_materialisation_payload(task)
        policy = await self._approval_policy_settings()
        decision = ApprovalPolicyMatrix.decision_for_task(
            kind,
            payload,
            settings=policy,
        )
        user_role = await self._fetch_user_role(user_id)
        if ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[decision.required_role]:
            if _is_manual_journal_self_approval_attempt(payload, user_id):
                denial_payload = {
                    "decision_result": "denied",
                    "denial_reason": "manual_journal_self_approval_denied",
                    "current_user_id": user_id,
                    "current_role": user_role.value,
                    "submitted_by": _manual_journal_submitted_by(payload),
                    "required_role": decision.required_role.value,
                }
                await self._record_decision_event(
                    task,
                    event_type="hitl_task.approval_denied",
                    action=f"{action}_denied",
                    actor_user_id=user_id,
                    actor_role=user_role,
                    decision=decision,
                    before_payload=payload,
                    after_payload=denial_payload,
                    materialisation=None,
                    idempotency_key=None,
                )
                await self._record_manual_journal_approval_denied_event(
                    task,
                    payload=payload,
                    reason="manual_journal_self_approval_denied",
                    actor_user_id=user_id,
                    actor_role=user_role,
                    decision=decision,
                    action=action,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Manual journal approval requires a different user "
                        "than the submitter"
                    ),
                )
            return ApprovalCheck(decision=decision, user_role=user_role, payload=payload)

        await self._record_decision_event(
            task,
            event_type="hitl_task.approval_denied",
            action=f"{action}_denied",
            actor_user_id=user_id,
            actor_role=user_role,
            decision=decision,
            before_payload=payload,
            after_payload={
                "decision_result": "denied",
                "current_role": user_role.value,
                "required_role": decision.required_role.value,
            },
            materialisation=None,
            idempotency_key=None,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Approval requires {decision.required_role.value} or higher "
                f"for {decision.reason}; current role is {user_role.value}"
            ),
        )

    async def _approval_policy_settings(self) -> ApprovalPolicySettings:
        return await ApprovalPolicySettingsService(
            self._db,
            self._tenant_id,
        ).get_runtime_settings()

    async def _record_decision_event(
        self,
        task: dict,
        *,
        event_type: str,
        action: str,
        actor_user_id: str,
        actor_role: UserRole,
        decision: ApprovalPolicyDecision,
        before_payload: dict,
        after_payload: dict,
        materialisation: dict | None,
        idempotency_key: str | None,
    ) -> None:
        task_id = str(task.get("id") or "")
        suggestion_id = task.get("agent_suggestion_id") or task.get("suggestion_id")
        before_state = {
            "task": _task_audit_summary(task),
            "payload": _safe_payload_summary(before_payload),
            "payload_hash": stable_payload_hash(before_payload),
        }
        after_state = {
            "task": {
                **_task_audit_summary(task),
                "status": (
                    "open"
                    if action.endswith("_denied")
                    else "done"
                ),
            },
            "payload": _safe_payload_summary(after_payload),
            "payload_hash": stable_payload_hash(after_payload),
            "materialisation": _materialisation_audit_summary(materialisation),
        }
        metadata = {
            "kind": str(task.get("kind") or ""),
            "agent_name": str(task.get("agent_name") or "unknown"),
            "confidence": str(task.get("confidence") or ""),
            "policy": decision.to_metadata(),
            "decision_result": _decision_result(action),
            "required_role": decision.required_role.value,
            "actor_role": actor_role.value,
            "agent_suggestion_id": str(suggestion_id) if suggestion_id else None,
        }
        await self._repo.append_financial_event(
            event_type=event_type,
            entity_type="hitl_task",
            entity_id=task_id,
            source_type="agent_suggestion" if suggestion_id else "hitl_task",
            source_id=str(suggestion_id or task_id),
            actor_user_id=actor_user_id,
            actor_role=actor_role.value,
            action=action,
            before_state=before_state,
            after_state=after_state,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        for target_type, target_id in _business_record_projection_targets(
            materialisation,
            before_payload,
            after_payload,
        ):
            await self._repo.append_financial_event(
                event_type=event_type,
                entity_type=target_type,
                entity_id=target_id,
                source_type="hitl_task",
                source_id=task_id,
                actor_user_id=actor_user_id,
                actor_role=actor_role.value,
                action=action,
                before_state=before_state,
                after_state=after_state,
                metadata={
                    **metadata,
                    "business_record_projection": True,
                    "source_hitl_task_id": task_id,
                },
                idempotency_key=_projected_decision_idempotency_key(
                    idempotency_key,
                    event_type=event_type,
                    task_id=task_id,
                    entity_type=target_type,
                    entity_id=target_id,
                ),
            )

    async def _record_manual_journal_rejected_event(
        self,
        task: dict,
        *,
        payload: dict,
        reason: str,
        actor_user_id: str,
        actor_role: UserRole,
        decision: ApprovalPolicyDecision,
    ) -> None:
        if not _is_manual_journal_threshold_payload(payload):
            return

        task_id = str(task.get("id") or "")
        if not task_id:
            return
        suggestion_id = task.get("agent_suggestion_id") or task.get("suggestion_id")
        payload_summary = _manual_journal_payload_summary(payload)
        rejection_reason = _truncate(reason, 500)
        before_state = {
            "task": _task_audit_summary(task),
            "payload": payload_summary,
            "payload_hash": stable_payload_hash(payload),
        }
        after_state = {
            "task": {
                **_task_audit_summary(task),
                "status": "done",
            },
            "payload": {"reason": rejection_reason},
            "payload_hash": stable_payload_hash({"reason": rejection_reason}),
        }
        metadata = {
            **payload_summary,
            "agent_suggestion_id": str(suggestion_id) if suggestion_id else None,
            "task_id": task_id,
            "policy": decision.to_metadata(),
            "decision_result": "rejected",
            "actor_role": actor_role.value,
            "required_role": decision.required_role.value,
            "rejection_reason": rejection_reason,
        }
        await self._repo.append_financial_event(
            event_type="manual_journal.rejected",
            entity_type="hitl_task",
            entity_id=task_id,
            source_type="agent_suggestion" if suggestion_id else "hitl_task",
            source_id=str(suggestion_id or task_id),
            actor_user_id=actor_user_id,
            actor_role=actor_role.value,
            action="rejected",
            before_state=before_state,
            after_state=after_state,
            metadata=metadata,
            idempotency_key=f"manual_journal.rejected:{task_id}",
        )

    async def _record_manual_journal_approval_denied_event(
        self,
        task: dict,
        *,
        payload: dict,
        reason: str,
        actor_user_id: str,
        actor_role: UserRole,
        decision: ApprovalPolicyDecision,
        action: str,
    ) -> None:
        if not _is_manual_journal_threshold_payload(payload):
            return

        task_id = str(task.get("id") or "")
        if not task_id:
            return
        suggestion_id = task.get("agent_suggestion_id") or task.get("suggestion_id")
        payload_summary = _manual_journal_payload_summary(payload)
        before_state = {
            "task": _task_audit_summary(task),
            "payload": payload_summary,
            "payload_hash": stable_payload_hash(payload),
        }
        after_state = {
            "task": {
                **_task_audit_summary(task),
                "status": "open",
            },
            "payload": {
                "decision_result": "denied",
                "denial_reason": reason,
                "current_user_id": actor_user_id,
            },
            "payload_hash": stable_payload_hash(
                {
                    "decision_result": "denied",
                    "denial_reason": reason,
                    "current_user_id": actor_user_id,
                }
            ),
        }
        metadata = {
            **payload_summary,
            "agent_suggestion_id": str(suggestion_id) if suggestion_id else None,
            "task_id": task_id,
            "policy": decision.to_metadata(),
            "decision_result": "denied",
            "denial_reason": reason,
            "actor_role": actor_role.value,
            "required_role": decision.required_role.value,
            "approval_action": action,
        }
        await self._repo.append_financial_event(
            event_type="manual_journal.approval_denied",
            entity_type="hitl_task",
            entity_id=task_id,
            source_type="agent_suggestion" if suggestion_id else "hitl_task",
            source_id=str(suggestion_id or task_id),
            actor_user_id=actor_user_id,
            actor_role=actor_role.value,
            action=f"{action}_denied",
            before_state=before_state,
            after_state=after_state,
            metadata=metadata,
            idempotency_key=None,
        )

    async def _fetch_user_role(self, user_id: str) -> UserRole:
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table("tenant_users")
                .select("role")
                .eq("tenant_id", self._tenant_id)
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            rows = getattr(result, "data", None) or []
            if rows:
                return UserRole(rows[0].get("role", UserRole.viewer.value))
        except Exception:
            return UserRole.viewer
        return UserRole.viewer

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
            return await self._materialise_bill(payload, user_id=user_id)
        elif kind in (
            "copilot_log_time_entry",
            "copilot_update_rate_card",
            "copilot_draft_invoice",
            "copilot_prepare_month_end_close",
            "copilot_prepare_year_end_close",
            "copilot_create_finance_ops_action_plan",
            "finance_ops_action_item",
        ):
            return await self._materialise_copilot_tool(payload, user_id=user_id)
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

    async def _materialise_copilot_tool(
        self,
        payload: dict,
        *,
        user_id: str | None = None,
    ) -> dict:
        tool_name = payload.get("tool_name")
        if payload.get("finance_ops_action_item") is True:
            return await self._materialise_finance_ops_action_item(
                payload,
                user_id=user_id,
            )

        if tool_name not in (
            "log_time_entry",
            "update_rate_card",
            "draft_invoice",
            "prepare_month_end_close",
            "prepare_year_end_close",
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

        if tool_name == "create_finance_ops_action_plan":
            return await self._materialise_finance_ops_action_plan(payload)

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
        if tool_name == "prepare_year_end_close":
            return {
                "entity_type": "year_end_close",
                "entity_id": result.get("journal_entry_id") or result.get("period"),
            }
        return {"entity_type": "rate_card", "entity_id": result.get("rate_card_line_id")}

    async def _materialise_finance_ops_action_plan(self, payload: dict) -> dict:
        child_tasks_created = await self._create_finance_ops_action_item_tasks(payload)
        return {
            "entity_type": "finance_ops_action_plan",
            "entity_id": str(payload.get("plan_id") or ""),
            "action_count": payload.get("action_count", 0),
            "child_tasks_created": child_tasks_created,
            "approval_effect": (
                "Approval queued child Inbox work items only; downstream invoices, "
                "payments, journals, statements, and external sends still require "
                "their own specialist approvals."
            ),
        }

    async def _materialise_finance_ops_action_item(
        self,
        payload: dict,
        *,
        user_id: str | None = None,
    ) -> dict:
        dispatch = self._finance_ops_action_item_dispatch(payload)
        if dispatch.get("error"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=dispatch["error"],
            )

        from app.agents.copilot.graph import CopilotAgent, CopilotDeps

        agent = CopilotAgent(
            CopilotDeps(
                tenant_id=self._tenant_id,
                user_id=str(
                    user_id
                    or payload.get("requested_by_user_id")
                    or payload.get("approved_by_user_id")
                    or ""
                ),
                db_client=self._db,
            )
        )
        dispatch_tool = str(dispatch["tool_name"])
        dispatch_input = dispatch["tool_input"]
        result = await agent._execute_tool_with_policy(dispatch_tool, dispatch_input)
        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plan Item dispatch failed: {result['error']}",
            )

        child_review_tasks_created = self._finance_ops_child_review_task_count(result)
        return {
            "entity_type": "finance_ops_action_item",
            "entity_id": str(payload.get("action_item_id") or ""),
            "parent_plan_id": payload.get("parent_plan_id"),
            "dispatched_tool": dispatch_tool,
            "dispatch_input": dispatch_input,
            "dispatch_result": result,
            "child_review_tasks_created": child_review_tasks_created,
            "approval_effect": (
                "Approval dispatched the specialist workflow through its existing "
                "review gates; downstream business records still require the "
                "specialist Inbox approval."
            ),
        }

    @staticmethod
    def _finance_ops_action_item_dispatch(payload: dict) -> dict:
        suggested_tool = str(payload.get("suggested_tool") or "").strip()
        domain = str(payload.get("domain") or "").strip().lower()
        period = str(payload.get("period") or "").strip()
        explicit_tool = payload.get("dispatch_tool")
        explicit_input = payload.get("dispatch_input")
        if isinstance(explicit_tool, str) and explicit_tool.strip():
            tool_name = explicit_tool.strip()
            tool_input = dict(explicit_input) if isinstance(explicit_input, dict) else {}
            if tool_name == "draft_collection_reminders" and not tool_input:
                tool_input = {"minimum_days_overdue": 1, "limit": 10, "tone": "auto"}
            elif tool_name == "propose_bill_payment_batch" and not tool_input:
                tool_input = {"due_within_days": 7}
            elif tool_name == "prepare_month_end_close":
                if not tool_input.get("period") and period:
                    tool_input["period"] = period
                if not tool_input.get("period"):
                    return {
                        "error": "Close Plan Item dispatch requires a period.",
                    }
            elif tool_name == "prepare_year_end_close":
                if not tool_input.get("year"):
                    year = str(payload.get("year") or period[:4]).strip()
                    if year:
                        tool_input["year"] = year
                if not tool_input.get("year"):
                    return {
                        "error": "Year-end close Plan Item dispatch requires a year.",
                    }
            elif tool_name == "draft_invoice":
                invoice_input = InboxService._finance_ops_invoice_dispatch_input(
                    payload,
                    tool_input=tool_input,
                )
                if invoice_input.get("error"):
                    return invoice_input
                tool_input = invoice_input["tool_input"]
            else:
                return {
                    "error": (
                        "Unsupported finance ops Plan Item dispatch target: "
                        f"{tool_name}"
                    )
                }
            return {"tool_name": tool_name, "tool_input": tool_input}

        if suggested_tool in {"send_email", "draft_collection_reminders"} or domain == "ar":
            return {
                "tool_name": "draft_collection_reminders",
                "tool_input": {
                    "minimum_days_overdue": 1,
                    "limit": 10,
                    "tone": "auto",
                },
            }
        if suggested_tool == "propose_bill_payment_batch" or domain == "ap":
            return {
                "tool_name": "propose_bill_payment_batch",
                "tool_input": {"due_within_days": 7},
            }
        if suggested_tool == "prepare_year_end_close":
            year = str(payload.get("year") or period[:4]).strip()
            if not year:
                return {
                    "error": "Year-end close Plan Item dispatch requires a year.",
                }
            return {
                "tool_name": "prepare_year_end_close",
                "tool_input": {"year": year},
            }
        if suggested_tool == "prepare_month_end_close" or domain == "close":
            if not period:
                return {
                    "error": "Close Plan Item dispatch requires a period.",
                }
            return {
                "tool_name": "prepare_month_end_close",
                "tool_input": {"period": period},
            }
        if suggested_tool == "draft_invoice" or domain == "wip":
            return InboxService._finance_ops_invoice_dispatch_input(payload)

        return {
            "error": (
                "Unsupported finance ops Plan Item dispatch target: "
                f"{suggested_tool or domain or 'unknown'}"
            )
        }

    @staticmethod
    def _finance_ops_invoice_dispatch_input(
        payload: dict,
        *,
        tool_input: dict | None = None,
    ) -> dict:
        tool_input = dict(tool_input or {})
        source = payload.get("source_plan_action")
        source = source if isinstance(source, dict) else {}
        engagement_id = (
            tool_input.get("engagement_id")
            or payload.get("engagement_id")
            or source.get("engagement_id")
        )
        engagement_name = (
            tool_input.get("engagement_name")
            or payload.get("engagement_name")
            or source.get("engagement_name")
        )
        if not engagement_id and not engagement_name:
            return {
                "error": (
                    "Invoice Plan Item dispatch requires an engagement_id or "
                    "engagement_name."
                ),
            }
        if engagement_id:
            tool_input["engagement_id"] = str(engagement_id)
        if engagement_name:
            tool_input["engagement_name"] = str(engagement_name)
        return {"tool_name": "draft_invoice", "tool_input": tool_input}

    @staticmethod
    def _finance_ops_child_review_task_count(result: dict) -> int:
        count = result.get("created_review_tasks")
        if isinstance(count, int):
            return count
        if isinstance(count, str) and count.isdigit():
            return int(count)
        if result.get("requires_review") and result.get("suggestion_id"):
            return 1
        return 0

    async def _create_finance_ops_action_item_tasks(self, payload: dict) -> int:
        action_items = payload.get("action_items")
        if not isinstance(action_items, list):
            return 0

        plan_id = str(payload.get("plan_id") or "")
        period = str(payload.get("period") or "")
        created = 0
        for index, item in enumerate(action_items, start=1):
            if not isinstance(item, dict):
                continue
            if item.get("requires_inbox_approval") is False:
                continue

            child_payload = self._finance_ops_child_task_payload(
                item,
                plan_id=plan_id,
                period=period,
                index=index,
            )
            suggestion = await asyncio.to_thread(
                lambda child_payload=child_payload: self._db.table("agent_suggestions")
                .insert(
                    {
                        "tenant_id": self._tenant_id,
                        "agent_name": str(
                            child_payload.get("suggested_agent") or "finance_ops_manager"
                        ),
                        "action_type": "finance_ops_action_item",
                        "input_snapshot": {
                            "parent_plan_id": plan_id,
                            "period": period,
                            "source_tool": "create_finance_ops_action_plan",
                        },
                        "output_snapshot": child_payload,
                        "confidence": "0.00",
                        "status": "pending",
                        "hitl_required": True,
                    }
                )
                .execute()
            )
            rows = getattr(suggestion, "data", None) or []
            suggestion_id = rows[0].get("id") if rows else None
            await asyncio.to_thread(
                lambda child_payload=child_payload, suggestion_id=suggestion_id: self._db.table(
                    "hitl_tasks"
                )
                .insert(
                    {
                        "tenant_id": self._tenant_id,
                        "agent_suggestion_id": suggestion_id,
                        "kind": "finance_ops_action_item",
                        "priority": self._finance_ops_action_item_priority(child_payload),
                        "title": self._finance_ops_action_item_title(child_payload),
                        "description": (
                            "Plan-derived finance ops work item. Review this follow-up "
                            "before requesting the specialist action."
                        ),
                        "payload": child_payload,
                        "status": "open",
                    }
                )
                .execute()
            )
            created += 1
        return created

    @staticmethod
    def _finance_ops_child_task_payload(
        item: dict,
        *,
        plan_id: str,
        period: str,
        index: int,
    ) -> dict:
        action_item_id = str(
            item.get("action_id")
            or item.get("id")
            or f"{plan_id or 'finance-ops-plan'}-{index}"
        )
        return {
            "finance_ops_action_item": True,
            "parent_plan_id": plan_id,
            "period": period,
            "action_item_id": action_item_id,
            "domain": item.get("domain"),
            "recommendation": item.get("recommendation"),
            "suggested_agent": item.get("suggested_agent"),
            "suggested_tool": item.get("suggested_tool"),
            "risk_class": item.get("risk_class"),
            "requires_inbox_approval": True,
            "rationale": item.get("rationale"),
            "review_path": item.get("review_path"),
            "dispatch_tool": InboxService._finance_ops_dispatch_tool(item),
            "dispatch_input": InboxService._finance_ops_dispatch_input(
                item,
                period=period,
            ),
            "source_plan_action": item,
            "approval_effect": (
                "Approving this item dispatches the mapped specialist workflow. "
                "It does not create invoices, payments, journals, statements, or "
                "external sends directly."
            ),
        }

    @staticmethod
    def _finance_ops_dispatch_tool(item: dict) -> str | None:
        suggested_tool = str(item.get("suggested_tool") or "").strip()
        domain = str(item.get("domain") or "").strip().lower()
        if suggested_tool in {"send_email", "draft_collection_reminders"} or domain == "ar":
            return "draft_collection_reminders"
        if suggested_tool == "propose_bill_payment_batch" or domain == "ap":
            return "propose_bill_payment_batch"
        if suggested_tool == "prepare_year_end_close":
            return "prepare_year_end_close"
        if suggested_tool == "prepare_month_end_close" or domain == "close":
            return "prepare_month_end_close"
        if suggested_tool == "draft_invoice" or domain == "wip":
            return "draft_invoice"
        return None

    @staticmethod
    def _finance_ops_dispatch_input(item: dict, *, period: str) -> dict:
        dispatch_tool = InboxService._finance_ops_dispatch_tool(item)
        if dispatch_tool == "draft_collection_reminders":
            return {"minimum_days_overdue": 1, "limit": 10, "tone": "auto"}
        if dispatch_tool == "propose_bill_payment_batch":
            return {"due_within_days": 7}
        if dispatch_tool == "prepare_year_end_close":
            year = str(item.get("year") or period[:4]).strip()
            return {"year": year} if year else {}
        if dispatch_tool == "prepare_month_end_close":
            return {"period": period}
        if dispatch_tool == "draft_invoice":
            result: dict = {}
            if item.get("engagement_id"):
                result["engagement_id"] = str(item["engagement_id"])
            if item.get("engagement_name"):
                result["engagement_name"] = str(item["engagement_name"])
            return result
        return {}

    @staticmethod
    def _finance_ops_action_item_priority(payload: dict) -> str:
        risk_class = str(payload.get("risk_class") or "")
        if risk_class in {"write_money_out", "write_money_in", "accounting"}:
            return "high"
        return "med"

    @staticmethod
    def _finance_ops_action_item_title(payload: dict) -> str:
        domain = _non_empty(payload.get("domain")) or "Finance"
        recommendation = _non_empty(payload.get("recommendation")) or "Review action"
        return f"Review finance ops action: {domain} - {recommendation[:80]}"

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
        journal_payload = dict(journal_payload)
        journal_payload["reason"] = self._journal_reason_from_proposal(
            journal_payload,
            proposal_payload=payload,
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

    @staticmethod
    def _journal_reason_from_proposal(
        journal_payload: dict,
        *,
        proposal_payload: dict,
    ) -> str:
        """Derive the audit reason for older AI draft-journal proposals."""
        candidates = [
            journal_payload.get("reason"),
            journal_payload.get("rationale"),
            journal_payload.get("business_reason"),
            proposal_payload.get("reason"),
            proposal_payload.get("rationale"),
            proposal_payload.get("business_reason"),
            journal_payload.get("description"),
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and len(candidate.strip()) >= 10:
                return candidate.strip()
        description = str(journal_payload.get("description") or "AI-approved journal proposal")
        return f"Approved journal proposal: {description}".strip()

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
            serialise_money(Decimal(str(payload["total_value"])))
            if payload.get("total_value")
            else None
        )
        rate_card_id, rate_card_line_count = await self._create_rate_card_from_hints(
            payload,
            engagement_name=engagement_name,
            currency=engagement_currency,
        )
        eng_row = await asyncio.to_thread(
            lambda: self._db.table("engagements")
            .insert(
                _without_none(
                    {
                        "tenant_id": self._tenant_id,
                        "client_id": client_id,
                        "name": engagement_name,
                        "billing_arrangement": payload.get(
                            "billing_arrangement",
                            "time_and_materials",
                        ),
                        "currency": engagement_currency,
                        "total_value": total_value,
                        "description": _non_empty(payload.get("scope_summary")),
                        "start_date": _non_empty(payload.get("start_date")),
                        "end_date": _non_empty(payload.get("end_date")),
                        "status": "draft",
                        "rate_card_id": rate_card_id,
                        "service_line": _non_empty(payload.get("service_line")),
                        "source_document_id": self._source_document_id(payload),  # #127
                    }
                )
            )
            .execute()
        )
        engagement_id = str(eng_row.data[0]["id"])
        billing_terms_created = await self._create_engagement_billing_terms(
            engagement_id,
            payload,
        )

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
            "client_name": client_name,
            "engagement_name": engagement_name,
            "billing_arrangement": payload.get("billing_arrangement", "time_and_materials"),
            "currency": engagement_currency,
            "total_value": total_value,
            "project_id": project_id,
            "project_name": project_name,
            "rate_card_id": rate_card_id,
            "rate_card_line_count": rate_card_line_count,
            "billing_terms_created": billing_terms_created,
        }

    async def _create_engagement_billing_terms(
        self,
        engagement_id: str,
        payload: dict,
    ) -> bool:
        import asyncio

        terms = _engagement_billing_terms_from_payload(payload)
        if not terms:
            return False
        await asyncio.to_thread(
            lambda: self._db.table("engagement_billing_terms")
            .insert(
                {
                    "tenant_id": self._tenant_id,
                    "engagement_id": engagement_id,
                    **terms,
                }
            )
            .execute()
        )
        return True

    async def _create_rate_card_from_hints(
        self,
        payload: dict,
        *,
        engagement_name: str,
        currency: str,
    ) -> tuple[str | None, int]:
        lines = _normalise_rate_card_hint_lines(payload.get("rate_card_hints"))
        if not lines:
            return None, 0

        effective_date = (
            _non_empty(payload.get("start_date"))
            or date.today().isoformat()
        )
        try:
            card_row = await asyncio.to_thread(
                lambda: self._db.table("rate_cards")
                .insert(
                    {
                        "tenant_id": self._tenant_id,
                        "name": f"{engagement_name} Rate Card",
                        "currency": currency,
                        "effective_date": effective_date,
                    }
                )
                .execute()
            )
            if not card_row.data:
                return None, 0
            rate_card_id = str(card_row.data[0]["id"])
            await asyncio.to_thread(
                lambda: self._db.table("rate_card_lines")
                .insert(
                    [
                        {
                            **line,
                            "tenant_id": self._tenant_id,
                            "rate_card_id": rate_card_id,
                        }
                        for line in lines
                    ]
                )
                .execute()
            )
            return rate_card_id, len(lines)
        except Exception as exc:
            logger.warning(
                "Auto-create rate card failed for engagement %s: %s",
                engagement_name,
                exc,
            )
            return None, 0

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

    async def _materialise_bill(
        self,
        payload: dict,
        *,
        user_id: str | None = None,
    ) -> dict:
        import asyncio

        self._raise_if_duplicate_bill_review_required(payload)
        vendor_name = payload.get("vendor_name") or payload.get("vendor", "Unknown Vendor")

        matched_client_id = self._vendor_invoice_matched_client_id(payload)
        if matched_client_id:
            client_id = matched_client_id
        else:
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

        from app.models.bills import BillCreate
        from app.services.bills_service import BillsService

        bill = await BillsService(self._db, self._tenant_id).create_bill(
            BillCreate(
                client_id=str(client_id),
                purchase_order_id=_non_empty(payload.get("purchase_order_id")),
                currency=str(payload.get("currency") or "USD"),
                issue_date=payload.get("issue_date"),
                due_date=payload.get("due_date"),
                vendor_invoice_number=payload.get("vendor_invoice_number"),
                notes=_non_empty(payload.get("notes")),
                lines=self._vendor_invoice_bill_lines(payload, subtotal=subtotal),
            ),
            source_document_id=self._source_document_id(payload),
            vendor_invoice_review=self._vendor_invoice_review_evidence(
                payload,
                user_id=user_id,
            ),
        )
        if total != Decimal(str(bill.total)):
            logger.info(
                "Vendor invoice reviewed total differs from line-derived bill total",
                extra={
                    "tenant_id": self._tenant_id,
                    "review_total": str(total),
                    "bill_total": bill.total,
                },
            )
        return {"entity_type": "bill", "entity_id": bill.id}

    @staticmethod
    def _raise_if_duplicate_bill_review_required(payload: dict) -> None:
        if not payload.get("possible_duplicate"):
            return
        duplicate_review = payload.get("duplicate_review")
        if not isinstance(duplicate_review, dict):
            duplicate_review = {}
        reason = _non_empty(duplicate_review.get("reason"))
        if duplicate_review.get("approved_duplicate") is True and reason:
            return
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_vendor_invoice_review_required",
                "message": (
                    "Possible duplicate vendor invoice requires approve-with-edits "
                    "with duplicate_review.approved_duplicate=true and a reason."
                ),
            },
        )

    @staticmethod
    def _vendor_invoice_matched_client_id(payload: dict) -> str | None:
        if payload.get("client_id"):
            return str(payload["client_id"])
        vendor_match = payload.get("vendor_match")
        if not isinstance(vendor_match, dict):
            return None
        matched_client_id = _non_empty(vendor_match.get("matched_client_id"))
        if matched_client_id and float(vendor_match.get("confidence") or 0) >= 0.70:
            return matched_client_id
        return None

    @staticmethod
    def _vendor_invoice_bill_lines(
        payload: dict,
        *,
        subtotal: Decimal,
    ) -> list[dict]:
        raw_lines = payload.get("lines") if isinstance(payload.get("lines"), list) else []
        if not raw_lines:
            return [
                {
                    "description": "Vendor invoice",
                    "quantity": Decimal("1"),
                    "unit_price": subtotal,
                    "amount": subtotal,
                    "tax_amount": Decimal(str(payload.get("tax_total") or "0")),
                }
            ]

        gl_suggestions = (
            payload.get("gl_suggestions")
            if isinstance(payload.get("gl_suggestions"), list)
            else []
        )
        lines: list[dict] = []
        for index, raw_line in enumerate(raw_lines):
            if not isinstance(raw_line, dict):
                continue
            amount = Decimal(str(raw_line.get("amount") or raw_line.get("unit_price") or "0"))
            quantity = Decimal(str(raw_line.get("quantity") or "1"))
            unit_price = Decimal(str(raw_line.get("unit_price") or amount))
            account_id = _non_empty(raw_line.get("account_id"))
            if account_id is None and index < len(gl_suggestions):
                suggestion = gl_suggestions[index]
                if (
                    isinstance(suggestion, dict)
                    and float(suggestion.get("confidence") or 0) >= 0.75
                ):
                    account_id = _non_empty(suggestion.get("account_id"))
            line = {
                "description": str(raw_line.get("description") or "Vendor invoice line"),
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": amount,
                "tax_amount": Decimal(str(raw_line.get("tax_amount") or "0")),
            }
            if account_id:
                line["account_id"] = account_id
            lines.append(line)
        if lines:
            return lines
        return [
            {
                "description": "Vendor invoice",
                "quantity": Decimal("1"),
                "unit_price": subtotal,
                "amount": subtotal,
                "tax_amount": Decimal(str(payload.get("tax_total") or "0")),
            }
        ]

    def _vendor_invoice_review_evidence(
        self,
        payload: dict,
        *,
        user_id: str | None,
    ) -> dict[str, object]:
        return {
            "source": "inbox_vendor_invoice_review",
            "source_document_id": self._source_document_id(payload),
            "reviewed_by_user_id": user_id,
            "vendor_name": payload.get("vendor_name") or payload.get("vendor"),
            "vendor_invoice_number": payload.get("vendor_invoice_number"),
            "match_status": payload.get("match_status"),
            "coding_status": payload.get("coding_status"),
            "vendor_match": payload.get("vendor_match") or {},
            "gl_suggestions": payload.get("gl_suggestions") or [],
            "project_hints": payload.get("project_hints") or payload.get("project_matches") or [],
            "customer_hints": payload.get("customer_hints") or payload.get("client_hints") or [],
            "review_exceptions": payload.get("review_exceptions") or [],
            "duplicate_review": payload.get("duplicate_review") or {},
        }


# ------------------------------------------------------------------
# Mapping helpers
# ------------------------------------------------------------------


def _non_empty(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _without_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


_ENGAGEMENT_BILLING_TERM_MONEY_KEYS = (
    "fixed_fee_amount",
    "milestone_total",
    "retainer_monthly_amount",
    "retainer_floor",
    "cap_amount",
)


def _money_or_none(value: object) -> str | None:
    text = _non_empty(value)
    if text is None:
        return None
    try:
        return serialise_money(Decimal(text.replace(",", "")))
    except Exception:
        return None


def _bool_or_none(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return None


def _engagement_billing_terms_from_payload(payload: dict) -> dict[str, Any]:
    nested = payload.get("billing_terms") if isinstance(payload.get("billing_terms"), dict) else {}
    result: dict[str, Any] = {}
    for key in _ENGAGEMENT_BILLING_TERM_MONEY_KEYS:
        value = payload.get(key)
        if value in (None, "") and isinstance(nested, dict):
            value = nested.get(key)
        money = _money_or_none(value)
        if money is not None:
            result[key] = money

    rollover = payload.get("retainer_rollover")
    if rollover is None and isinstance(nested, dict):
        rollover = nested.get("retainer_rollover")
    rollover_bool = _bool_or_none(rollover)
    if rollover_bool is not None:
        result["retainer_rollover"] = rollover_bool

    return result


def _row_to_summary(
    row: dict,
    *,
    decision_history: list[dict] | None = None,
    policy: ApprovalPolicySettings | None = None,
) -> HitlTaskSummary:
    approval = _approval_policy_metadata(row, policy=policy)
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
        required_approval_role=approval.get("required_role"),
        approval_policy_reason=approval.get("reason"),
        approval_policy=approval,
        decision_history=[
            HitlDecisionEvent.from_db(event)
            for event in (decision_history or [])
        ],
    )


def _row_to_detail(
    row: dict,
    *,
    decision_history: list[dict] | None = None,
    policy: ApprovalPolicySettings | None = None,
) -> HitlTaskDetail:
    approval = _approval_policy_metadata(row, policy=policy)
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
        required_approval_role=approval.get("required_role"),
        approval_policy_reason=approval.get("reason"),
        approval_policy=approval,
        decision_history=[
            HitlDecisionEvent.from_db(event)
            for event in (decision_history or [])
        ],
        description=row.get("description"),
        payload=row.get("payload", {}),
    )


def _approval_policy_metadata(
    row: dict,
    *,
    policy: ApprovalPolicySettings | None = None,
) -> dict[str, str]:
    suggestion_payload = row.get("suggestion_payload") or {}
    task_payload = row.get("payload") or {}
    if not isinstance(suggestion_payload, dict):
        suggestion_payload = {}
    if not isinstance(task_payload, dict):
        task_payload = {}
    payload = {**suggestion_payload, **task_payload}
    return ApprovalPolicyMatrix.decision_for_task(
        str(row.get("kind") or ""),
        payload,
        settings=policy,
    ).to_metadata()


def _task_audit_summary(task: dict) -> dict[str, Any]:
    return {
        "id": str(task.get("id") or ""),
        "kind": str(task.get("kind") or ""),
        "status": str(task.get("status") or ""),
        "priority": str(task.get("priority") or ""),
        "title": _truncate(str(task.get("title") or ""), 200),
    }


def _materialisation_audit_summary(materialisation: dict | None) -> dict[str, Any]:
    if not materialisation:
        return {}
    result: dict[str, Any] = {}
    for key in (
        "entity_type",
        "entity_id",
        "client_id",
        "project_id",
        "parent_plan_id",
        "dispatched_tool",
        "child_review_tasks_created",
        "child_tasks_created",
        "action_count",
        "send_status",
    ):
        value = materialisation.get(key)
        if value is not None:
            result[key] = value
    if not result:
        result["keys"] = sorted(str(key) for key in materialisation.keys())[:20]
    return result


def _business_record_projection_targets(
    materialisation: dict | None,
    before_payload: dict | None,
    payload: dict | None,
) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    if materialisation:
        entity_type = _non_empty(materialisation.get("entity_type"))
        entity_id = _non_empty(materialisation.get("entity_id"))
        if entity_type and entity_id and entity_type != "hitl_task":
            targets.append((entity_type, entity_id))
    source_document_id = (
        _source_document_id_from_payload(payload)
        or _source_document_id_from_payload(before_payload)
    )
    if source_document_id:
        targets.append(("document", source_document_id))

    deduped: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for target in targets:
        if target in seen:
            continue
        seen.add(target)
        deduped.append(target)
    return deduped


def _source_document_id_from_payload(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("source_document_id", "original_document_id", "document_id"):
        value = _non_empty(payload.get(key))
        if value:
            return value
    return None


def _projected_decision_idempotency_key(
    idempotency_key: str | None,
    *,
    event_type: str,
    task_id: str,
    entity_type: str,
    entity_id: str,
) -> str:
    base = idempotency_key or f"{event_type}:{task_id}"
    return f"{base}:record:{entity_type}:{entity_id}"


def _safe_payload_summary(payload: dict | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    summary, redacted = _summarise_mapping(payload)
    if redacted:
        summary["redacted_fields"] = sorted(redacted)
    return summary


def _normalise_rate_card_hint_lines(hints: Any) -> list[dict[str, str | None]]:
    if not isinstance(hints, list):
        return []
    lines: list[dict[str, str | None]] = []
    seen_roles: set[str] = set()
    for hint in hints:
        if not isinstance(hint, dict):
            continue
        role = _non_empty(hint.get("role"))
        if role is None:
            continue
        role_key = role.casefold()
        if role_key in seen_roles:
            continue
        try:
            rate = Decimal(str(hint.get("rate") or ""))
        except Exception:
            continue
        if rate < 0:
            continue
        seen_roles.add(role_key)
        lines.append(
            {
                "role": role,
                "rate": f"{rate:.2f}",
                "service_line": _normalise_rate_card_service_line(
                    hint.get("service_line")
                ),
            }
        )
    return lines


def _normalise_rate_card_service_line(value: Any) -> str | None:
    service_line = _non_empty(value)
    if service_line is None:
        return None
    service_line = service_line.lower().replace(" ", "_").replace("-", "_")
    if service_line in {"accounting", "tax", "cosec", "payroll", "advisory", "other"}:
        return service_line
    return None


def _is_manual_journal_threshold_payload(payload: dict | None) -> bool:
    if not isinstance(payload, dict):
        return False
    approval = payload.get("manual_journal_approval")
    if not isinstance(approval, dict):
        return False
    return approval.get("source") == "manual_journal_threshold"


def _is_manual_journal_self_approval_attempt(
    payload: dict | None,
    user_id: str,
) -> bool:
    submitted_by = _manual_journal_submitted_by(payload)
    return submitted_by is not None and submitted_by == user_id


def _manual_journal_submitted_by(payload: dict | None) -> str | None:
    if not _is_manual_journal_threshold_payload(payload):
        return None
    approval = payload.get("manual_journal_approval") if isinstance(payload, dict) else {}
    if not isinstance(approval, dict):
        return None
    return _non_empty(approval.get("submitted_by"))


def _manual_journal_payload_summary(payload: dict) -> dict[str, Any]:
    approval = payload.get("manual_journal_approval") or {}
    if not isinstance(approval, dict):
        approval = {}
    lines = payload.get("lines") or []
    line_count = len(lines) if isinstance(lines, list) else 0
    total_debits = _non_empty(payload.get("total_debits"))
    if total_debits is None:
        total_debits = _manual_journal_total_debits(lines)
    return {
        "description": _truncate(str(payload.get("description") or ""), 200),
        "reason": _truncate(str(payload.get("reason") or ""), 500),
        "entry_date": str(payload.get("entry_date") or ""),
        "reference": _non_empty(payload.get("reference")),
        "line_count": line_count,
        "total_debits": total_debits,
        "threshold": _non_empty(approval.get("threshold")),
        "source": approval.get("source", "manual_journal_threshold"),
        "submitted_by": _non_empty(approval.get("submitted_by")),
        "submitted_by_role": _non_empty(approval.get("submitted_by_role")),
    }


def _manual_journal_total_debits(lines: Any) -> str | None:
    if not isinstance(lines, list):
        return None
    total = Decimal("0")
    found = False
    for line in lines:
        if not isinstance(line, dict):
            continue
        if str(line.get("direction") or "").upper() != "DR":
            continue
        try:
            total += Decimal(str(line.get("amount") or "0"))
            found = True
        except Exception:
            continue
    if not found:
        return None
    return f"{total:.2f}"


def _summarise_mapping(
    payload: dict[str, Any],
    *,
    depth: int = 0,
) -> tuple[dict[str, Any], set[str]]:
    result: dict[str, Any] = {}
    redacted: set[str] = set()
    for key, value in payload.items():
        key_text = str(key)
        normalised_key = key_text.lower()
        if _is_sensitive_key(normalised_key):
            redacted.add(key_text)
            continue

        if isinstance(value, dict):
            if depth >= 1 or key_text not in _NESTED_SUMMARY_KEYS:
                result[f"{key_text}_keys"] = sorted(str(k) for k in value.keys())[:20]
                continue
            child, child_redacted = _summarise_mapping(value, depth=depth + 1)
            result[key_text] = child
            redacted.update(f"{key_text}.{name}" for name in child_redacted)
            continue

        if isinstance(value, list):
            result[f"{key_text}_count"] = len(value)
            continue

        if key_text in _SUMMARY_KEYS and value is not None:
            result[key_text] = _truncate(str(value), 200)

    return result, redacted


def _is_sensitive_key(key: str) -> bool:
    return any(marker in key for marker in _SENSITIVE_KEY_MARKERS)


def _decision_result(action: str) -> str:
    if action.endswith("_denied"):
        return "denied"
    if action == "rejected":
        return "rejected"
    return "approved"


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."


_SENSITIVE_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "api_key",
    "body_html",
    "email_body",
    "raw",
    "content",
    "ocr",
    "document_text",
    "base64",
)

_NESTED_SUMMARY_KEYS = {
    "preview",
    "invoice_draft",
    "journal",
    "journal_entry",
    "source_plan_action",
    "tool_input",
    "dispatch_input",
}

_SUMMARY_KEYS = {
    "action_count",
    "action_item_id",
    "amount",
    "bank_account_label",
    "bill_count",
    "billing_arrangement",
    "category",
    "client_name",
    "currency",
    "dispatch_tool",
    "domain",
    "due_date",
    "engagement_id",
    "engagement_name",
    "expense_date",
    "flagged_for_review_count",
    "invoice_number",
    "issue_date",
    "line_count",
    "net_income",
    "parent_plan_id",
    "period",
    "priority",
    "project_id",
    "proposed_pay_date",
    "recommendation",
    "reason",
    "review_path",
    "risk_class",
    "status",
    "subtotal",
    "suggested_agent",
    "suggested_tool",
    "tax_total",
    "title",
    "tone",
    "tool_name",
    "total",
    "total_amount",
    "vendor",
    "vendor_invoice_number",
    "vendor_name",
    "workflow",
}
