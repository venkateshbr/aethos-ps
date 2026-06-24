"""Derived financial close status for period-close workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.close_override_service import CloseOverrideService
from app.services.close_reconciliation_service import CloseReconciliationService
from app.services.close_tasks_service import CloseTasksService
from supabase import Client

CloseItemStatus = Literal["complete", "pending", "blocked", "overridden"]
ClosePeriodStatus = Literal["ready", "blocked", "locked"]

_CLOSE_REVIEW_AGENTS = (
    "accrual_agent",
    "close_agent",
    "prepaid_amortization_agent",
    "recurring_journal_agent",
    "reporting_agent",
    "revenue_recognition_agent",
)
_CLOSE_REVIEW_STATUSES = ("pending",)


@dataclass(frozen=True)
class PendingCloseReview:
    """A pending HITL review that should be resolved before period lock."""

    id: str
    agent_name: str
    action_type: str
    status: str
    summary: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "status": self.status,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class CloseChecklistItem:
    """One derived close checklist row."""

    code: str
    label: str
    status: CloseItemStatus
    blocking: bool
    summary: str
    count: int = 0
    overridden: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "label": self.label,
            "status": self.status,
            "blocking": self.blocking,
            "summary": self.summary,
            "count": self.count,
            "overridden": self.overridden,
        }


@dataclass(frozen=True)
class CloseStatusResult:
    """Tenant period close status derived from current accounting state."""

    period: str
    status: ClosePeriodStatus
    locked: bool
    locked_at: str | None
    locked_by: str | None
    ready_to_lock: bool
    checklist: list[CloseChecklistItem]
    findings: list[dict[str, str | None]]
    pending_reviews: list[PendingCloseReview]
    unposted_journals: list[dict[str, str | None]]
    incomplete_tasks: list[dict[str, str | None]]
    overrides: list[dict[str, object]]
    lock_blockers: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "status": self.status,
            "locked": self.locked,
            "locked_at": self.locked_at,
            "locked_by": self.locked_by,
            "ready_to_lock": self.ready_to_lock,
            "checklist": [item.as_dict() for item in self.checklist],
            "findings": self.findings,
            "pending_reviews": [review.as_dict() for review in self.pending_reviews],
            "unposted_journals": self.unposted_journals,
            "incomplete_tasks": self.incomplete_tasks,
            "overrides": self.overrides,
            "lock_blockers": self.lock_blockers,
        }


class CloseStatusService:
    """Build a deterministic close checklist without storing duplicate state."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def get_status(self, period: str) -> CloseStatusResult:
        """Return the close status and blockers for a period."""
        lock = self._lock_row(period)
        reconciliation = CloseReconciliationService(self.db, self.tenant_id).check_period(period)
        pending_reviews = self.pending_close_reviews(period)
        unposted_journals = self._unposted_journals(period)
        incomplete_tasks = self._incomplete_tasks(period)
        overrides = CloseOverrideService(self.db, self.tenant_id).list_overrides(period)
        override_codes = {override.blocker_code for override in overrides}

        subledger_findings = [
            finding
            for finding in reconciliation.findings
            if finding.code != "trial_balance_unbalanced"
        ]
        raw_blockers: list[str] = []
        if subledger_findings:
            raw_blockers.append("subledger_reconciliation")
        if not reconciliation.trial_balance_balanced:
            raw_blockers.append("trial_balance")
        if unposted_journals:
            raw_blockers.append("unposted_journals")
        if pending_reviews:
            raw_blockers.append("close_reviews")
        if incomplete_tasks:
            raw_blockers.append("close_tasks")

        blockers = [code for code in raw_blockers if code not in override_codes]

        locked = lock is not None
        ready_to_lock = not locked and not blockers
        status: ClosePeriodStatus
        if locked:
            status = "locked"
        elif ready_to_lock:
            status = "ready"
        else:
            status = "blocked"

        checklist = [
            self._subledger_item(
                subledger_findings,
                overridden="subledger_reconciliation" in override_codes,
            ),
            self._trial_balance_item(
                reconciliation.trial_balance_balanced,
                overridden="trial_balance" in override_codes,
            ),
            self._unposted_journals_item(
                unposted_journals,
                overridden="unposted_journals" in override_codes,
            ),
            self._close_reviews_item(
                pending_reviews,
                overridden="close_reviews" in override_codes,
            ),
            self._close_tasks_item(
                incomplete_tasks,
                overridden="close_tasks" in override_codes,
            ),
            self._period_lock_item(locked=locked, ready_to_lock=ready_to_lock),
        ]

        return CloseStatusResult(
            period=period,
            status=status,
            locked=locked,
            locked_at=str(lock.get("locked_at")) if lock else None,
            locked_by=str(lock.get("locked_by")) if lock else None,
            ready_to_lock=ready_to_lock,
            checklist=checklist,
            findings=[finding.as_dict() for finding in reconciliation.findings],
            pending_reviews=pending_reviews,
            unposted_journals=unposted_journals,
            incomplete_tasks=incomplete_tasks,
            overrides=[override.as_dict() for override in overrides],
            lock_blockers=blockers,
        )

    def pending_close_reviews(self, period: str) -> list[PendingCloseReview]:
        """Return unresolved close-related suggestions for this period."""
        rows = (
            self.db.table("agent_suggestions")
            .select("id, agent_name, action_type, output_snapshot, status")
            .eq("tenant_id", self.tenant_id)
            .in_("agent_name", list(_CLOSE_REVIEW_AGENTS))
            .in_("status", list(_CLOSE_REVIEW_STATUSES))
            .execute()
            .data
            or []
        )
        reviews: list[PendingCloseReview] = []
        for row in rows:
            output = row.get("output_snapshot") or {}
            if not isinstance(output, dict) or not _output_matches_period(output, period):
                continue
            reviews.append(
                PendingCloseReview(
                    id=str(row["id"]),
                    agent_name=str(row.get("agent_name") or "unknown"),
                    action_type=str(row.get("action_type") or "unknown"),
                    status=str(row.get("status") or "pending"),
                    summary=_review_summary(output),
                )
            )
        return reviews

    def _lock_row(self, period: str) -> dict | None:
        rows = (
            self.db.table("period_locks")
            .select("period, locked_at, locked_by")
            .eq("tenant_id", self.tenant_id)
            .eq("period", period)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    @staticmethod
    def _task_summary(row: dict) -> dict[str, str | None]:
        return {
            "id": str(row["id"]),
            "code": str(row["code"]),
            "title": str(row["title"]),
            "status": str(row.get("status") or "open"),
        }

    def _incomplete_tasks(self, period: str) -> list[dict[str, str | None]]:
        return [
            self._task_summary(row)
            for row in CloseTasksService(
                self.db,
                self.tenant_id,
            ).incomplete_blocking_tasks(period)
        ]

    def _unposted_journals(self, period: str) -> list[dict[str, str | None]]:
        rows = (
            self.db.table("journal_entries")
            .select("id, entry_number, description, entry_date, reference_type, reference")
            .eq("tenant_id", self.tenant_id)
            .eq("period", period)
            .is_("posted_at", "null")
            .execute()
            .data
            or []
        )
        return [
            {
                "id": str(row["id"]),
                "entry_number": str(row.get("entry_number") or row["id"]),
                "description": row.get("description"),
                "entry_date": str(row.get("entry_date") or ""),
                "reference_type": str(row.get("reference_type") or "manual"),
                "reference": str(row["reference"]) if row.get("reference") else None,
            }
            for row in rows
        ]

    @staticmethod
    def _subledger_item(
        findings: list[object],
        *,
        overridden: bool = False,
    ) -> CloseChecklistItem:
        if findings:
            if overridden:
                return CloseChecklistItem(
                    code="subledger_reconciliation",
                    label="Sub-ledger reconciliation",
                    status="overridden",
                    blocking=False,
                    summary=(
                        f"{len(findings)} sub-ledger item(s) remain, but a close "
                        "override is recorded."
                    ),
                    count=len(findings),
                    overridden=True,
                )
            return CloseChecklistItem(
                code="subledger_reconciliation",
                label="Sub-ledger reconciliation",
                status="blocked",
                blocking=True,
                summary=f"{len(findings)} sub-ledger item(s) need posted GL references.",
                count=len(findings),
            )
        return CloseChecklistItem(
            code="subledger_reconciliation",
            label="Sub-ledger reconciliation",
            status="complete",
            blocking=False,
            summary="AR and AP sub-ledgers reconcile to posted GL references.",
        )

    @staticmethod
    def _trial_balance_item(
        balanced: bool,
        *,
        overridden: bool = False,
    ) -> CloseChecklistItem:
        if not balanced:
            if overridden:
                return CloseChecklistItem(
                    code="trial_balance",
                    label="Trial balance",
                    status="overridden",
                    blocking=False,
                    summary="Trial balance is unbalanced, but a close override is recorded.",
                    count=1,
                    overridden=True,
                )
            return CloseChecklistItem(
                code="trial_balance",
                label="Trial balance",
                status="blocked",
                blocking=True,
                summary="Trial balance debits and credits do not match.",
                count=1,
            )
        return CloseChecklistItem(
            code="trial_balance",
            label="Trial balance",
            status="complete",
            blocking=False,
            summary="Trial balance is balanced.",
        )

    @staticmethod
    def _unposted_journals_item(
        journals: list[dict[str, str | None]],
        *,
        overridden: bool = False,
    ) -> CloseChecklistItem:
        if journals:
            if overridden:
                return CloseChecklistItem(
                    code="unposted_journals",
                    label="Unposted journals",
                    status="overridden",
                    blocking=False,
                    summary=(
                        f"{len(journals)} unposted journal(s) remain, but a close "
                        "override is recorded."
                    ),
                    count=len(journals),
                    overridden=True,
                )
            return CloseChecklistItem(
                code="unposted_journals",
                label="Unposted journals",
                status="blocked",
                blocking=True,
                summary=f"{len(journals)} journal(s) in the period are not posted.",
                count=len(journals),
            )
        return CloseChecklistItem(
            code="unposted_journals",
            label="Unposted journals",
            status="complete",
            blocking=False,
            summary="No unposted journals remain for the period.",
        )

    @staticmethod
    def _close_reviews_item(
        reviews: list[PendingCloseReview],
        *,
        overridden: bool = False,
    ) -> CloseChecklistItem:
        if reviews:
            if overridden:
                return CloseChecklistItem(
                    code="close_reviews",
                    label="Close review queue",
                    status="overridden",
                    blocking=False,
                    summary=(
                        f"{len(reviews)} close review(s) remain in HITL, but a "
                        "close override is recorded."
                    ),
                    count=len(reviews),
                    overridden=True,
                )
            return CloseChecklistItem(
                code="close_reviews",
                label="Close review queue",
                status="pending",
                blocking=True,
                summary=f"{len(reviews)} close review(s) are pending in HITL.",
                count=len(reviews),
            )
        return CloseChecklistItem(
            code="close_reviews",
            label="Close review queue",
            status="complete",
            blocking=False,
            summary="No pending close-related HITL reviews.",
        )

    @staticmethod
    def _close_tasks_item(
        tasks: list[dict[str, str | None]],
        *,
        overridden: bool = False,
    ) -> CloseChecklistItem:
        if tasks:
            if overridden:
                return CloseChecklistItem(
                    code="close_tasks",
                    label="Close tasks",
                    status="overridden",
                    blocking=False,
                    summary=(
                        f"{len(tasks)} close task(s) remain incomplete, but a "
                        "close override is recorded."
                    ),
                    count=len(tasks),
                    overridden=True,
                )
            return CloseChecklistItem(
                code="close_tasks",
                label="Close tasks",
                status="pending",
                blocking=True,
                summary=f"{len(tasks)} close task(s) must be completed or waived.",
                count=len(tasks),
            )
        return CloseChecklistItem(
            code="close_tasks",
            label="Close tasks",
            status="complete",
            blocking=False,
            summary="No incomplete blocking close tasks.",
        )

    @staticmethod
    def _period_lock_item(*, locked: bool, ready_to_lock: bool) -> CloseChecklistItem:
        if locked:
            return CloseChecklistItem(
                code="period_lock",
                label="Period lock",
                status="complete",
                blocking=False,
                summary="Period is locked.",
            )
        if ready_to_lock:
            return CloseChecklistItem(
                code="period_lock",
                label="Period lock",
                status="pending",
                blocking=False,
                summary="Period is ready to lock.",
            )
        return CloseChecklistItem(
            code="period_lock",
            label="Period lock",
            status="blocked",
            blocking=False,
            summary="Resolve blocking close items before locking the period.",
        )


def close_review_blocker_detail(
    period: str, pending_reviews: list[PendingCloseReview]
) -> dict[str, object]:
    """Build the 409 detail used when unresolved reviews block period lock."""
    return {
        "code": "close_review_pending",
        "period": period,
        "pending_reviews": [review.as_dict() for review in pending_reviews],
    }


def _output_matches_period(output: dict, period: str) -> bool:
    if output.get("period") == period:
        return True
    journal_entry = output.get("journal_entry")
    if isinstance(journal_entry, dict):
        reference = journal_entry.get("reference")
        return isinstance(reference, str) and f":{period}:" in reference
    return False


def _review_summary(output: dict) -> str:
    currency = output.get("currency")
    wip_value = output.get("wip_value")
    if currency and wip_value:
        return f"Review {currency} WIP accrual proposal for {wip_value}."
    reimbursement_accrual = output.get("reimbursement_accrual_amount")
    if (
        output.get("proposal_type") == "employee_reimbursement_accrual"
        and currency
        and reimbursement_accrual
    ):
        return (
            f"Review {currency} employee reimbursement accrual proposal for "
            f"{reimbursement_accrual}."
        )
    deferred_release = output.get("deferred_release_amount")
    if currency and deferred_release:
        return f"Review {currency} deferred revenue release proposal for {deferred_release}."
    amortization_amount = output.get("amortization_amount")
    if (
        output.get("proposal_type") == "prepaid_expense_amortization"
        and currency
        and amortization_amount
    ):
        description = str(output.get("line_description") or "prepaid expense")
        return (
            f"Review {currency} prepaid amortization proposal for "
            f"{description}: {amortization_amount}."
        )
    if (
        output.get("proposal_type") == "recurring_journal"
        and currency
        and output.get("total_amount")
    ):
        template_name = str(output.get("template_name") or "recurring journal")
        return (
            f"Review {currency} recurring journal proposal for "
            f"{template_name}: {output['total_amount']}."
        )
    recognition_amount = output.get("recognition_amount")
    if (
        output.get("proposal_type") == "percentage_completion_revenue_recognition"
        and currency
        and recognition_amount
    ):
        phase_name = str(output.get("phase_name") or "phase")
        return (
            f"Review {currency} percentage-completion recognition proposal for "
            f"{phase_name}: {recognition_amount}."
        )
    if currency and recognition_amount:
        phase_name = str(output.get("phase_name") or "milestone")
        return (
            f"Review {currency} milestone recognition proposal for "
            f"{phase_name}: {recognition_amount}."
        )
    return "Review pending close-related agent proposal."
