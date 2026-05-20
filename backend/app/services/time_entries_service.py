"""Business logic for the time_entries resource.

Validation rules:
- project_id must reference a project that belongs to the tenant.
- employee_id must reference an employee that belongs to the tenant.
- hours > 0 and <= 24 (enforced by Pydantic model + DB CHECK).
- Cannot update a billed time entry (billing_status = 'billed').
- Cannot delete a billed time entry.
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import HTTPException, status

from app.models.time_entries import (
    TimeEntryCreate,
    TimeEntryListResponse,
    TimeEntryResponse,
    TimeEntryUpdate,
)
from app.repositories.time_entries_repo import TimeEntriesRepository
from supabase import Client

logger = logging.getLogger(__name__)


class TimeEntriesService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._repo = TimeEntriesRepository(db, tenant_id)
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list_entries(
        self,
        project_id: str | None = None,
        employee_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        billing_status: str | None = None,
        limit: int = 100,
    ) -> TimeEntryListResponse:
        rows = await self._repo.list(
            project_id=project_id,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            billing_status=billing_status,
            limit=limit,
        )
        items = [_row_to_response(r) for r in rows]
        return TimeEntryListResponse(items=items, total=len(items))

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------

    async def get_entry(self, entry_id: str) -> TimeEntryResponse | None:
        row = await self._repo.get(entry_id)
        if row is None:
            return None
        return _row_to_response(row)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_entry(self, data: TimeEntryCreate) -> TimeEntryResponse:
        # Validate project belongs to tenant
        if not await self._repo.project_belongs_to_tenant(data.project_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {data.project_id!r} not found",
            )

        # Validate employee belongs to tenant
        if not await self._repo.employee_belongs_to_tenant(data.employee_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {data.employee_id!r} not found",
            )

        payload: dict = {
            "project_id": data.project_id,
            "employee_id": data.employee_id,
            "date": data.date.isoformat(),
            "hours": str(data.hours),
            "description": data.description,
            "billable": data.billable,
            "billing_status": "unbilled" if data.billable else "non_billable",
        }
        if data.phase_id is not None:
            payload["phase_id"] = data.phase_id

        row = await self._repo.create(payload)
        return _row_to_response(row)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_entry(self, entry_id: str, data: TimeEntryUpdate) -> TimeEntryResponse:
        existing = await self._repo.get(entry_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Time entry {entry_id!r} not found",
            )

        if existing.get("billing_status") == "billed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot update a time entry that has already been billed",
            )

        patch: dict = {}
        if data.hours is not None:
            patch["hours"] = str(data.hours)
        if data.description is not None:
            patch["description"] = data.description
        if data.billable is not None:
            patch["billable"] = data.billable
            # Sync billing_status if changing billability and entry is currently unbilled
            if existing.get("billing_status") == "unbilled" and not data.billable:
                patch["billing_status"] = "non_billable"
            elif existing.get("billing_status") == "non_billable" and data.billable:
                patch["billing_status"] = "unbilled"

        if not patch:
            return _row_to_response(existing)

        row = await self._repo.update(entry_id, patch)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Time entry {entry_id!r} not found",
            )
        return _row_to_response(row)

    # ------------------------------------------------------------------
    # Delete (soft)
    # ------------------------------------------------------------------

    async def delete_entry(self, entry_id: str) -> None:
        existing = await self._repo.get(entry_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Time entry {entry_id!r} not found",
            )

        if existing.get("billing_status") == "billed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a time entry that has already been billed",
            )

        await self._repo.soft_delete(entry_id)


# ---------------------------------------------------------------------------
# Private
# ---------------------------------------------------------------------------


def _row_to_response(row: dict) -> TimeEntryResponse:
    return TimeEntryResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        project_id=str(row["project_id"]),
        employee_id=str(row["employee_id"]),
        date=str(row["date"]),
        hours=row["hours"],
        description=row.get("description") or "",
        billable=bool(row.get("billable", True)),
        billing_status=row.get("billing_status", "unbilled"),
        phase_id=str(row["phase_id"]) if row.get("phase_id") else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )
