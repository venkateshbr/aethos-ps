"""Persisted financial close tasks for guided month-end close workflows."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from app.services.postgrest_errors import is_missing_table_error
from supabase import Client

_DONE_STATUSES = {"done", "waived"}
_TABLE = "accounting_close_tasks"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CloseTaskTemplate:
    code: str
    title: str
    description: str
    owner_role: str
    order_index: int


_DEFAULT_TASKS = [
    CloseTaskTemplate(
        code="subledger_reconciliation",
        title="Reconcile AR/AP subledgers",
        description="Confirm finalized invoices, bills, and settlements agree to posted GL.",
        owner_role="finance_manager",
        order_index=10,
    ),
    CloseTaskTemplate(
        code="wip_accrual_review",
        title="Review accruals",
        description=(
            "Generate and approve unbilled WIP and employee reimbursement "
            "accrual proposals for the period."
        ),
        owner_role="finance_manager",
        order_index=20,
    ),
    CloseTaskTemplate(
        code="deferred_revenue_review",
        title="Review deferred revenue release",
        description="Generate and approve deferred revenue release proposals for earned revenue.",
        owner_role="finance_manager",
        order_index=30,
    ),
    CloseTaskTemplate(
        code="recurring_journal_review",
        title="Review recurring journals",
        description="Generate and approve recurring journal proposals for active templates.",
        owner_role="finance_manager",
        order_index=35,
    ),
    CloseTaskTemplate(
        code="trial_balance_review",
        title="Review trial balance and close package",
        description="Review trial balance, variance commentary, and close package evidence.",
        owner_role="controller",
        order_index=40,
    ),
    CloseTaskTemplate(
        code="period_lock",
        title="Lock accounting period",
        description="Lock the period after all blocking close items are complete.",
        owner_role="admin",
        order_index=50,
    ),
]


class CloseTasksService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def list_tasks(self, period: str) -> list[dict[str, Any]]:
        try:
            result = (
                self.db.table(_TABLE)
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .eq("period", period)
                .is_("deleted_at", "null")
                .order("order_index")
                .execute()
            )
        except Exception as exc:
            if is_missing_table_error(exc, _TABLE):
                logger.warning(
                    "accounting_close_tasks table missing; treating period as having no close tasks",
                    extra={"tenant_id": self.tenant_id, "period": period},
                )
                return []
            raise
        return result.data or []

    async def bootstrap_tasks(self, period: str, created_by: str) -> list[dict[str, Any]]:
        existing = await asyncio.to_thread(lambda: self.list_tasks(period))
        existing_codes = {str(row["code"]) for row in existing}
        payloads: list[dict[str, Any]] = []
        due_date = _period_due_date(period)
        for template in _DEFAULT_TASKS:
            if template.code in existing_codes:
                continue
            payloads.append(
                {
                    "tenant_id": self.tenant_id,
                    "period": period,
                    "code": template.code,
                    "title": template.title,
                    "description": template.description,
                    "owner_role": template.owner_role,
                    "status": "open",
                    "due_date": due_date.isoformat(),
                    "order_index": template.order_index,
                    "evidence": {"created_by": created_by},
                }
            )
        if payloads:
            try:
                await asyncio.to_thread(lambda: self.db.table(_TABLE).insert(payloads).execute())
            except Exception as exc:
                if is_missing_table_error(exc, _TABLE):
                    logger.warning(
                        "accounting_close_tasks table missing; skipping close task bootstrap",
                        extra={"tenant_id": self.tenant_id, "period": period},
                    )
                    return []
                raise
        return await asyncio.to_thread(lambda: self.list_tasks(period))

    async def update_task(
        self,
        *,
        period: str,
        task_id: str,
        patch: dict[str, Any],
        actor_id: str,
    ) -> dict[str, Any] | None:
        status = patch.get("status")
        payload = dict(patch)
        if status in _DONE_STATUSES:
            payload["completed_at"] = datetime.now(UTC).isoformat()
            payload["completed_by"] = actor_id
        elif status:
            payload["completed_at"] = None
            payload["completed_by"] = None

        try:
            result = await asyncio.to_thread(
                lambda: (
                    self.db.table(_TABLE)
                    .update(payload)
                    .eq("id", task_id)
                    .eq("tenant_id", self.tenant_id)
                    .eq("period", period)
                    .is_("deleted_at", "null")
                    .execute()
                )
            )
        except Exception as exc:
            if is_missing_table_error(exc, _TABLE):
                logger.warning(
                    "accounting_close_tasks table missing; close task update cannot be applied",
                    extra={
                        "tenant_id": self.tenant_id,
                        "period": period,
                        "task_id": task_id,
                    },
                )
                return None
            raise
        return result.data[0] if result.data else None

    def incomplete_blocking_tasks(self, period: str) -> list[dict[str, Any]]:
        """Return review tasks that must finish before the lock action.

        ``period_lock`` represents the action being attempted, so treating its
        initial open state as a precondition creates a circular close workflow.
        The endpoint marks that item done only after the lock row is persisted.
        """
        return [
            row
            for row in self.list_tasks(period)
            if str(row.get("code") or "") != "period_lock"
            and str(row.get("status") or "open") not in _DONE_STATUSES
        ]

    async def mark_period_lock_task(
        self,
        *,
        period: str,
        actor_id: str,
        locked: bool,
    ) -> dict[str, Any] | None:
        """Synchronise the checklist action with an authoritative lock change."""
        tasks = await asyncio.to_thread(lambda: self.list_tasks(period))
        task = next(
            (row for row in tasks if str(row.get("code") or "") == "period_lock"),
            None,
        )
        if task is None:
            return None
        return await self.update_task(
            period=period,
            task_id=str(task["id"]),
            patch={"status": "done" if locked else "open"},
            actor_id=actor_id,
        )


def _period_due_date(period: str) -> date:
    year, month = (int(part) for part in period.split("-", 1))
    if month == 12:
        return date(year + 1, 1, 5)
    return date(year, month + 1, 5)
