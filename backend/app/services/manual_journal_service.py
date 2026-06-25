"""Manual journal entry service.

Handles posting of manual GL adjustments (accruals, corrections, period-end
entries). Every manual entry is gated by:

  1. Period lock check (via period_lock_service.assert_period_open).
  2. accounting_guardian L3 validation (balance, period lock, account validity).
  3. post_journal() insertion (journal_entries + journal_lines rows).
  4. manual_journal.posted evidence in financial_events.

The accounting_guardian always runs at L3 and cannot be bypassed.
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status

from app.domain.journal_helper import JournalLineSpec, post_journal
from app.domain.money import serialise_money
from app.models.accounting import (
    JournalEntryListItem,
    ManualJournalApprovalTaskResponse,
    ManualJournalEntryIn,
    ManualJournalEntryResponse,
    ManualJournalReversalIn,
)
from app.services.agent_run_ledger import stable_payload_hash
from app.services.approval_policy import ApprovalPolicyMatrix
from app.services.approval_policy_settings_service import ApprovalPolicySettingsService
from app.services.period_lock_service import assert_period_open
from supabase import Client

logger = logging.getLogger(__name__)


class ManualJournalService:
    """Service for posting and listing manual GL journal entries."""

    def __init__(
        self,
        db: Client,
        tenant_id: str,
        user_id: str,
        *,
        actor_role: str | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.actor_role = actor_role

    async def submit_manual_journal(
        self, payload: ManualJournalEntryIn
    ) -> ManualJournalEntryResponse | ManualJournalApprovalTaskResponse:
        """Post immediately or route a high-value manual journal to Inbox."""
        total_debits = self._payload_total_debits(payload)
        policy = await ApprovalPolicySettingsService(
            self.db,
            self.tenant_id,
        ).get_runtime_settings()
        if total_debits >= policy.manual_journal_approval_threshold:
            return await self._create_manual_journal_approval_task(
                payload=payload,
                total_debits=total_debits,
                threshold=policy.manual_journal_approval_threshold,
            )
        return await self.post_manual_journal(payload)

    async def reverse_manual_journal(
        self,
        journal_entry_id: str,
        payload: ManualJournalReversalIn,
    ) -> ManualJournalEntryResponse:
        """Create a reversing journal for a posted manual journal entry."""
        await assert_period_open(self.db, self.tenant_id, payload.entry_date)
        original = await self._fetch_journal_entry(journal_entry_id)
        if original is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manual journal entry not found",
            )
        if str(original.get("reference_type") or "") != "manual":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Only original manual journal entries can be reversed here",
            )
        existing_reversal = await self._find_existing_reversal(journal_entry_id)
        if existing_reversal is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Manual journal entry has already been reversed",
            )

        original_lines = await self._fetch_journal_lines(journal_entry_id)
        if not original_lines:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Manual journal entry has no lines to reverse",
            )

        entry_number = str(original.get("entry_number") or journal_entry_id)
        reversal_lines = [
            JournalLineSpec(
                direction="CR" if line.get("direction") == "DR" else "DR",
                account_code="",
                account_id=str(line["account_id"]),
                amount=Decimal(str(line.get("amount") or "0")),
                currency=str(line.get("currency") or "USD"),
                description=f"Reversal of {entry_number}: {line.get('description') or ''}".strip(),
                base_amount=Decimal(str(line.get("base_amount") or line.get("amount") or "0")),
            )
            for line in original_lines
        ]

        def _post() -> dict:
            return post_journal(
                db=self.db,
                tenant_id=self.tenant_id,
                created_by=self.user_id,
                description=f"Reversal of {entry_number}",
                entry_date=payload.entry_date.isoformat(),
                reference_type="manual_reversal",
                reference_id=journal_entry_id,
                lines=reversal_lines,
                extra_entry_fields={"reason": payload.reason},
            )

        try:
            reversal = await asyncio.to_thread(_post)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

        reversal_db_lines = await self._fetch_journal_lines(str(reversal["id"]))
        await self._append_manual_journal_reversal_event(
            original=original,
            reversal=reversal,
            lines=reversal_db_lines,
            payload=payload,
        )
        return ManualJournalEntryResponse.from_db(reversal, reversal_db_lines)

    async def post_manual_journal(
        self, payload: ManualJournalEntryIn
    ) -> ManualJournalEntryResponse:
        """Validate and post a manual journal entry.

        Steps:
          1. Assert the entry_date is in an open period.
          2. Build JournalLineSpec list from the request lines.
          3. Call post_journal() — which runs accounting_guardian internally.
          4. Fetch journal_lines, append audit evidence, and return response.

        Raises:
            HTTPException 422 if the period is locked.
            ValueError (re-raised as HTTPException 422) if the guardian rejects
            the journal (imbalanced, unknown accounts).
        """
        # 1. Period lock check — raises 422 with code=period_locked if locked
        await assert_period_open(self.db, self.tenant_id, payload.entry_date)

        # 2. Build JournalLineSpec list
        # account_id is a UUID from Pydantic; convert to str for the guardian
        lines = [
            JournalLineSpec(
                direction=line.direction,
                account_code="",  # not required for manual entries (guardian uses account_id)
                account_id=str(line.account_id),
                amount=line.amount,
                currency=line.currency,
                description=line.description or "",
                base_amount=line.amount,  # TODO: FX convert if currency != tenant base currency
            )
            for line in payload.lines
        ]

        # 3. Call post_journal (runs accounting_guardian → DB insert)
        # post_journal is synchronous (supabase-py is sync); run in thread
        def _post() -> dict:
            return post_journal(
                db=self.db,
                tenant_id=self.tenant_id,
                created_by=self.user_id,
                description=payload.description,
                entry_date=payload.entry_date.isoformat(),
                reference_type="manual",
                reference_id=None,  # no sub-ledger reference for manual entries
                lines=lines,
                extra_entry_fields={"reason": payload.reason},
            )

        try:
            je = await asyncio.to_thread(_post)
        except ValueError as exc:
            # accounting_guardian rejected — bubble up as 422
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        # 4. Fetch journal_lines for the response
        def _fetch_lines() -> list[dict]:
            result = (
                self.db.table("journal_lines")
                .select("*")
                .eq("journal_entry_id", je["id"])
                .execute()
            )
            return result.data or []

        je_lines = await asyncio.to_thread(_fetch_lines)
        await self._append_manual_journal_event(
            journal=je,
            lines=je_lines,
            payload=payload,
        )

        logger.info(
            "Manual journal posted",
            extra={
                "journal_entry_id": je["id"],
                "tenant_id": self.tenant_id,
                "user_id": self.user_id,
                "lines": len(je_lines),
            },
        )

        return ManualJournalEntryResponse.from_db(je, je_lines)

    async def list_journal_entries(
        self,
        *,
        reference_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JournalEntryListItem]:
        """List journal entries for this tenant, optionally filtered by reference_type.

        Args:
            reference_type: Filter to a specific type (e.g. "manual", "invoice", "bill").
            limit: Maximum rows to return (capped at 100).
            offset: Pagination offset.

        Returns:
            List of JournalEntryListItem in descending posted_at order.
        """

        def _fetch() -> list[dict]:
            query = (
                self.db.table("journal_entries")
                .select(
                    "id, entry_number, description, reason, entry_date, period, "
                    "reference_type, reference_id, created_by, posted_at"
                )
                .eq("tenant_id", self.tenant_id)
                .order("posted_at", desc=True)
                .limit(min(limit, 100))
                .offset(offset)
            )
            if reference_type is not None:
                query = query.eq("reference_type", reference_type)
            return query.execute().data or []

        rows = await asyncio.to_thread(_fetch)

        return [
            JournalEntryListItem(
                id=str(r["id"]),
                entry_number=str(r["entry_number"]),
                description=str(r["description"]),
                reason=str(r["reason"]) if r.get("reason") is not None else None,
                entry_date=str(r["entry_date"]),
                period=str(r["period"]),
                reference_type=str(r["reference_type"]),
                reference=r.get("reference_id"),
                created_by=str(r["created_by"]),
                posted_at=str(r["posted_at"]),
            )
            for r in rows
        ]

    async def _fetch_journal_entry(self, journal_entry_id: str) -> dict[str, Any] | None:
        def _fetch() -> list[dict[str, Any]]:
            return (
                self.db.table("journal_entries")
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .eq("id", journal_entry_id)
                .limit(1)
                .execute()
                .data
                or []
            )

        rows = await asyncio.to_thread(_fetch)
        return rows[0] if rows else None

    async def _find_existing_reversal(self, journal_entry_id: str) -> dict[str, Any] | None:
        def _fetch() -> list[dict[str, Any]]:
            return (
                self.db.table("journal_entries")
                .select("id")
                .eq("tenant_id", self.tenant_id)
                .eq("reference_type", "manual_reversal")
                .eq("reference_id", journal_entry_id)
                .limit(1)
                .execute()
                .data
                or []
            )

        rows = await asyncio.to_thread(_fetch)
        return rows[0] if rows else None

    async def _fetch_journal_lines(self, journal_entry_id: str) -> list[dict[str, Any]]:
        def _fetch() -> list[dict[str, Any]]:
            return (
                self.db.table("journal_lines")
                .select("*")
                .eq("journal_entry_id", journal_entry_id)
                .execute()
                .data
                or []
            )

        return await asyncio.to_thread(_fetch)

    async def _create_manual_journal_approval_task(
        self,
        *,
        payload: ManualJournalEntryIn,
        total_debits: Decimal,
        threshold: Decimal,
    ) -> ManualJournalApprovalTaskResponse:
        """Create the review task for an over-threshold manual journal."""
        journal_payload = payload.model_dump(mode="json")
        journal_payload["total_debits"] = serialise_money(total_debits)
        journal_payload["manual_journal_approval"] = {
            "source": "manual_journal_threshold",
            "submitted_by": self.user_id,
            "submitted_by_role": self.actor_role,
            "threshold": serialise_money(threshold),
        }
        decision = ApprovalPolicyMatrix.decision_for_task(
            "draft_journal",
            journal_payload,
            settings=await ApprovalPolicySettingsService(
                self.db,
                self.tenant_id,
            ).get_runtime_settings(),
        )

        def _insert_task() -> tuple[str | None, str | None]:
            suggestion_rows = (
                self.db.table("agent_suggestions")
                .insert(
                    {
                        "tenant_id": self.tenant_id,
                        "agent_name": "manual_journal_service",
                        "action_type": "draft_journal",
                        "input_snapshot": {
                            "source": "manual_journal_threshold",
                            "submitted_by": self.user_id,
                        },
                        "output_snapshot": journal_payload,
                        "confidence": "1.00",
                        "status": "pending",
                        "hitl_required": True,
                    }
                )
                .execute()
                .data
                or []
            )
            suggestion_id = suggestion_rows[0].get("id") if suggestion_rows else None
            task_rows = (
                self.db.table("hitl_tasks")
                .insert(
                    {
                        "tenant_id": self.tenant_id,
                        "agent_suggestion_id": suggestion_id,
                        "kind": "draft_journal",
                        "priority": "high",
                        "title": f"Review high-value manual journal: {payload.description}",
                        "description": (
                            f"Manual journal debit total {serialise_money(total_debits)} "
                            f"meets or exceeds threshold {serialise_money(threshold)}. "
                            "Review before posting to the general ledger."
                        ),
                        "payload": journal_payload,
                        "status": "open",
                    }
                )
                .execute()
                .data
                or []
            )
            task_id = task_rows[0].get("id") if task_rows else None
            return (
                str(suggestion_id) if suggestion_id is not None else None,
                str(task_id) if task_id is not None else None,
            )

        suggestion_id, task_id = await asyncio.to_thread(_insert_task)
        if task_id:
            await self._append_manual_journal_submitted_for_approval_event(
                journal_payload=journal_payload,
                suggestion_id=suggestion_id,
                task_id=task_id,
                total_debits=total_debits,
                threshold=threshold,
                required_role=decision.required_role.value,
                policy_reason=decision.reason,
            )
        return ManualJournalApprovalTaskResponse(
            task_id=task_id,
            suggestion_id=suggestion_id,
            required_approval_role=decision.required_role.value,
            approval_policy_reason=decision.reason,
            total_debits=serialise_money(total_debits) or "0.00",
            threshold=serialise_money(threshold) or "0.00",
            message=(
                "Manual journal routed to Inbox for approval before posting."
            ),
        )

    async def _append_manual_journal_submitted_for_approval_event(
        self,
        *,
        journal_payload: dict[str, Any],
        suggestion_id: str | None,
        task_id: str,
        total_debits: Decimal,
        threshold: Decimal,
        required_role: str,
        policy_reason: str,
    ) -> None:
        """Append proposal lifecycle evidence for threshold-routed journals."""
        approval_payload = journal_payload.get("manual_journal_approval") or {}
        metadata = {
            "task_id": task_id,
            "agent_suggestion_id": suggestion_id,
            "submitted_by": self.user_id,
            "submitted_by_role": self.actor_role,
            "required_role": required_role,
            "policy_reason": policy_reason,
            "reason": str(journal_payload.get("reason") or ""),
            "entry_date": str(journal_payload.get("entry_date") or ""),
            "line_count": len(journal_payload.get("lines") or []),
            "total_debits": serialise_money(total_debits),
            "threshold": serialise_money(threshold),
            "payload_hash": stable_payload_hash(journal_payload),
            "source": approval_payload.get("source", "manual_journal_threshold"),
        }
        after_state = {
            "task": {
                "id": task_id,
                "kind": "draft_journal",
                "status": "open",
            },
            "payload": {
                "description": str(journal_payload.get("description") or ""),
                "reason": str(journal_payload.get("reason") or ""),
                "entry_date": str(journal_payload.get("entry_date") or ""),
                "reference": journal_payload.get("reference"),
                "line_count": len(journal_payload.get("lines") or []),
                "total_debits": serialise_money(total_debits),
                "threshold": serialise_money(threshold),
            },
            "payload_hash": stable_payload_hash(journal_payload),
        }

        await asyncio.to_thread(
            lambda: self.db.rpc(
                "append_financial_event",
                {
                    "p_tenant_id": self.tenant_id,
                    "p_event_type": "manual_journal.submitted_for_approval",
                    "p_entity_type": "hitl_task",
                    "p_entity_id": task_id,
                    "p_source_type": "agent_suggestion" if suggestion_id else "hitl_task",
                    "p_source_id": suggestion_id or task_id,
                    "p_actor_user_id": self.user_id,
                    "p_actor_role": self.actor_role,
                    "p_action": "submitted_for_approval",
                    "p_before_state": {},
                    "p_after_state": after_state,
                    "p_metadata": metadata,
                    "p_idempotency_key": (
                        f"manual_journal.submitted_for_approval:{task_id}"
                    ),
                },
            ).execute()
        )

    async def _append_manual_journal_event(
        self,
        *,
        journal: dict[str, Any],
        lines: list[dict[str, Any]],
        payload: ManualJournalEntryIn,
    ) -> None:
        """Append manual-journal-specific evidence to the immutable event log."""
        total_debits = sum(
            Decimal(str(line.get("base_amount") or line.get("amount") or "0"))
            for line in lines
            if line.get("direction") == "DR"
        )
        metadata = {
            "entry_number": str(journal.get("entry_number") or ""),
            "period": str(journal.get("period") or ""),
            "entry_date": str(journal.get("entry_date") or payload.entry_date.isoformat()),
            "reason": payload.reason,
            "line_count": len(lines),
            "total_debits": serialise_money(total_debits),
            "reference": payload.reference,
            "source": "manual_journal_service",
        }
        after_state = {
            "journal_entry_id": str(journal.get("id") or ""),
            "entry_number": str(journal.get("entry_number") or ""),
            "description": str(journal.get("description") or payload.description),
            "reason": payload.reason,
            "posted_at": str(journal.get("posted_at") or ""),
            "line_count": len(lines),
            "total_debits": serialise_money(total_debits),
        }

        await asyncio.to_thread(
            lambda: self.db.rpc(
                "append_financial_event",
                {
                    "p_tenant_id": self.tenant_id,
                    "p_event_type": "manual_journal.posted",
                    "p_entity_type": "journal_entry",
                    "p_entity_id": str(journal["id"]),
                    "p_source_type": "manual_journal",
                    "p_source_id": str(journal["id"]),
                    "p_actor_user_id": self.user_id,
                    "p_actor_role": self.actor_role,
                    "p_action": "posted",
                    "p_before_state": {},
                    "p_after_state": after_state,
                    "p_metadata": metadata,
                    "p_idempotency_key": f"manual_journal.posted:{journal['id']}",
                },
            ).execute()
        )

    async def _append_manual_journal_reversal_event(
        self,
        *,
        original: dict[str, Any],
        reversal: dict[str, Any],
        lines: list[dict[str, Any]],
        payload: ManualJournalReversalIn,
    ) -> None:
        """Append reversal-specific evidence to the immutable event log."""
        total_debits = sum(
            Decimal(str(line.get("base_amount") or line.get("amount") or "0"))
            for line in lines
            if line.get("direction") == "DR"
        )
        metadata = {
            "original_journal_entry_id": str(original.get("id") or ""),
            "original_entry_number": str(original.get("entry_number") or ""),
            "reversal_entry_number": str(reversal.get("entry_number") or ""),
            "reason": payload.reason,
            "line_count": len(lines),
            "total_debits": serialise_money(total_debits),
            "source": "manual_journal_service",
        }
        after_state = {
            "original_journal_entry_id": str(original.get("id") or ""),
            "reversal_journal_entry_id": str(reversal.get("id") or ""),
            "reversal_entry_number": str(reversal.get("entry_number") or ""),
            "reason": payload.reason,
            "posted_at": str(reversal.get("posted_at") or ""),
            "line_count": len(lines),
            "total_debits": serialise_money(total_debits),
        }

        await asyncio.to_thread(
            lambda: self.db.rpc(
                "append_financial_event",
                {
                    "p_tenant_id": self.tenant_id,
                    "p_event_type": "manual_journal.reversed",
                    "p_entity_type": "journal_entry",
                    "p_entity_id": str(original["id"]),
                    "p_source_type": "manual_journal_reversal",
                    "p_source_id": str(reversal["id"]),
                    "p_actor_user_id": self.user_id,
                    "p_actor_role": self.actor_role,
                    "p_action": "reversed",
                    "p_before_state": {
                        "original_journal_entry_id": str(original.get("id") or ""),
                        "entry_number": str(original.get("entry_number") or ""),
                    },
                    "p_after_state": after_state,
                    "p_metadata": metadata,
                    "p_idempotency_key": f"manual_journal.reversed:{original['id']}",
                },
            ).execute()
        )

    @staticmethod
    def _payload_total_debits(payload: ManualJournalEntryIn) -> Decimal:
        return sum(line.amount for line in payload.lines if line.direction == "DR")
