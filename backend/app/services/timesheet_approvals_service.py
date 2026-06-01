"""Manager-side timesheet approval logic (issue #134, P5).

Tenant-scoped. Operates on submitted entries; approve/reject are bulk, so a
manager can clear an employee's week in one action. Approve is idempotent.
Rejected entries return to the employee (the portal makes them editable again).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.models.timesheet import (
    ApprovalActionResponse,
    ApprovalEntry,
    ApprovalListResponse,
)
from supabase import Client

logger = logging.getLogger(__name__)


class TimesheetApprovalsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def list_pending(self) -> ApprovalListResponse:
        rows = (
            self._db.table("time_entries")
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .eq("status", "submitted")
            .is_("deleted_at", "null")
            .order("date", desc=False)
            .execute()
            .data
            or []
        )
        if not rows:
            return ApprovalListResponse(items=[], total=0)

        emp_ids = list({str(r["employee_id"]) for r in rows})
        proj_ids = list({str(r["project_id"]) for r in rows})
        emp_map = self._lookup("employees", emp_ids, "first_name, last_name")
        proj_map = self._lookup("projects", proj_ids, "code")

        items = []
        for r in rows:
            emp = emp_map.get(str(r["employee_id"]), {})
            name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or None
            items.append(
                ApprovalEntry(
                    id=str(r["id"]),
                    employee_id=str(r["employee_id"]),
                    employee_name=name,
                    project_id=str(r["project_id"]),
                    project_code=proj_map.get(str(r["project_id"]), {}).get("code"),
                    date=str(r["date"]),
                    hours=r["hours"],
                    description=r.get("description") or "",
                    billable=bool(r.get("billable", True)),
                )
            )
        return ApprovalListResponse(items=items, total=len(items))

    async def approve(self, entry_ids: list[str], approver_user_id: str) -> ApprovalActionResponse:
        rows = (
            self._db.table("time_entries")
            .update(
                {
                    "status": "approved",
                    "approved_at": datetime.now(UTC).isoformat(),
                    "approved_by": approver_user_id,
                    "rejected_reason": None,
                }
            )
            .eq("tenant_id", self._tenant_id)
            .eq("status", "submitted")
            .in_("id", entry_ids)
            .execute()
            .data
            or []
        )
        return ApprovalActionResponse(updated=len(rows))

    async def reject(
        self, entry_ids: list[str], reason: str, approver_user_id: str
    ) -> ApprovalActionResponse:
        rows = (
            self._db.table("time_entries")
            .update(
                {
                    "status": "rejected",
                    "approved_by": approver_user_id,
                    "approved_at": datetime.now(UTC).isoformat(),
                    "rejected_reason": reason or None,
                }
            )
            .eq("tenant_id", self._tenant_id)
            .eq("status", "submitted")
            .in_("id", entry_ids)
            .execute()
            .data
            or []
        )
        return ApprovalActionResponse(updated=len(rows))

    # ------------------------------------------------------------------

    def _lookup(self, table: str, ids: list[str], cols: str) -> dict[str, dict]:
        if not ids:
            return {}
        rows = (
            self._db.table(table)
            .select(f"id, {cols}")
            .eq("tenant_id", self._tenant_id)
            .in_("id", ids)
            .execute()
            .data
            or []
        )
        return {str(r["id"]): r for r in rows}
