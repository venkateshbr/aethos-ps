"""Business logic for the employee Timesheet Portal (issue #134, P4).

All operations are scoped to a single ``employee_id`` (the authenticated caller,
resolved by ``get_current_employee``). The service NEVER trusts a client-supplied
employee id — callers pass only ``employee_id`` that this layer received from the
dependency.

Editing rules:
- Only ``draft`` and ``rejected`` entries may be edited or deleted.
- ``submit`` flips a week's ``draft`` entries to ``submitted``.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status

from app.models.timesheet import (
    MyProject,
    MyProjectListResponse,
    SubmitWeekResponse,
    TimesheetEntryCreate,
    TimesheetEntryListResponse,
    TimesheetEntryResponse,
    TimesheetEntryUpdate,
)
from supabase import Client

logger = logging.getLogger(__name__)

_EDITABLE = ("draft", "rejected")


class TimesheetService:
    def __init__(self, db: Client, tenant_id: str, employee_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._employee_id = employee_id

    # ------------------------------------------------------------------
    # My projects — the codes the employee is mapped to
    # ------------------------------------------------------------------

    async def my_projects(self) -> MyProjectListResponse:
        assignments = (
            self._db.table("project_assignments")
            .select("project_id, role")
            .eq("tenant_id", self._tenant_id)
            .eq("employee_id", self._employee_id)
            .execute()
            .data
            or []
        )
        if not assignments:
            return MyProjectListResponse(items=[], total=0)

        role_by_project = {str(a["project_id"]): a.get("role") for a in assignments}
        project_ids = list(role_by_project.keys())

        projects = (
            self._db.table("projects")
            .select("id, code, name, engagement_id")
            .eq("tenant_id", self._tenant_id)
            .in_("id", project_ids)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        eng_ids = list({str(p["engagement_id"]) for p in projects})
        eng_map: dict[str, dict] = {}
        if eng_ids:
            eng_rows = (
                self._db.table("engagements")
                .select("id, code, name")
                .eq("tenant_id", self._tenant_id)
                .in_("id", eng_ids)
                .execute()
                .data
                or []
            )
            eng_map = {str(e["id"]): e for e in eng_rows}

        items = []
        for p in projects:
            eng = eng_map.get(str(p["engagement_id"]), {})
            items.append(
                MyProject(
                    project_id=str(p["id"]),
                    project_code=p.get("code"),
                    project_name=p["name"],
                    engagement_id=str(p["engagement_id"]),
                    engagement_code=eng.get("code"),
                    engagement_name=eng.get("name"),
                    role=role_by_project.get(str(p["id"])),
                )
            )
        items.sort(key=lambda m: (m.project_code or "", m.project_name))
        return MyProjectListResponse(items=items, total=len(items))

    # ------------------------------------------------------------------
    # Entries (self-only)
    # ------------------------------------------------------------------

    async def list_entries(
        self, date_from: date | None = None, date_to: date | None = None
    ) -> TimesheetEntryListResponse:
        q = (
            self._db.table("time_entries")
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .eq("employee_id", self._employee_id)
            .is_("deleted_at", "null")
            .order("date", desc=True)
        )
        if date_from:
            q = q.gte("date", date_from.isoformat())
        if date_to:
            q = q.lte("date", date_to.isoformat())
        rows = q.execute().data or []
        items = [_row_to_response(r) for r in rows]
        return TimesheetEntryListResponse(items=items, total=len(items))

    async def create_entry(self, data: TimesheetEntryCreate) -> TimesheetEntryResponse:
        # The project must belong to the tenant AND the employee must be assigned.
        if not await self._is_assigned(data.project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to that project.",
            )
        payload: dict = {
            "tenant_id": self._tenant_id,
            "project_id": data.project_id,
            "employee_id": self._employee_id,
            "date": data.date.isoformat(),
            "hours": str(data.hours),
            "description": data.description,
            "billable": data.billable,
            "billing_status": "unbilled" if data.billable else "non_billable",
            "status": "draft",
        }
        if data.phase_id is not None:
            payload["phase_id"] = data.phase_id
        row = self._db.table("time_entries").insert(payload).execute().data[0]
        return _row_to_response(row)

    async def update_entry(
        self, entry_id: str, data: TimesheetEntryUpdate
    ) -> TimesheetEntryResponse:
        existing = await self._get_own(entry_id)
        if existing.get("status") not in _EDITABLE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot edit a {existing.get('status')} entry.",
            )
        patch: dict = {}
        if data.hours is not None:
            patch["hours"] = str(data.hours)
        if data.description is not None:
            patch["description"] = data.description
        if data.billable is not None:
            patch["billable"] = data.billable
            patch["billing_status"] = "unbilled" if data.billable else "non_billable"
        # Editing a rejected entry returns it to draft.
        if existing.get("status") == "rejected":
            patch["status"] = "draft"
            patch["rejected_reason"] = None
        if not patch:
            return _row_to_response(existing)
        row = (
            self._db.table("time_entries")
            .update(patch)
            .eq("id", entry_id)
            .eq("tenant_id", self._tenant_id)
            .eq("employee_id", self._employee_id)
            .execute()
            .data[0]
        )
        return _row_to_response(row)

    async def delete_entry(self, entry_id: str) -> None:
        existing = await self._get_own(entry_id)
        if existing.get("status") not in _EDITABLE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete a {existing.get('status')} entry.",
            )
        self._db.table("time_entries").update(
            {"deleted_at": datetime.now(UTC).isoformat()}
        ).eq("id", entry_id).eq("tenant_id", self._tenant_id).eq(
            "employee_id", self._employee_id
        ).execute()

    async def submit_week(self, week_start: date) -> SubmitWeekResponse:
        week_end = week_start + timedelta(days=6)
        rows = (
            self._db.table("time_entries")
            .update(
                {"status": "submitted", "submitted_at": datetime.now(UTC).isoformat()}
            )
            .eq("tenant_id", self._tenant_id)
            .eq("employee_id", self._employee_id)
            .eq("status", "draft")
            .gte("date", week_start.isoformat())
            .lte("date", week_end.isoformat())
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        return SubmitWeekResponse(
            submitted=len(rows),
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
        )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    async def _get_own(self, entry_id: str) -> dict:
        result = (
            self._db.table("time_entries")
            .select("*")
            .eq("id", entry_id)
            .eq("tenant_id", self._tenant_id)
            .eq("employee_id", self._employee_id)
            .is_("deleted_at", "null")
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time entry not found",
            )
        return result.data[0]

    async def _is_assigned(self, project_id: str) -> bool:
        result = (
            self._db.table("project_assignments")
            .select("id")
            .eq("tenant_id", self._tenant_id)
            .eq("employee_id", self._employee_id)
            .eq("project_id", project_id)
            .execute()
        )
        return bool(result.data)


def _row_to_response(row: dict) -> TimesheetEntryResponse:
    return TimesheetEntryResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        project_id=str(row["project_id"]),
        employee_id=str(row["employee_id"]),
        date=str(row["date"]),
        hours=row["hours"],
        description=row.get("description") or "",
        billable=bool(row.get("billable", True)),
        status=row.get("status", "draft"),
        billing_status=row.get("billing_status", "unbilled"),
        rejected_reason=row.get("rejected_reason"),
        created_at=str(row["created_at"]),
    )
