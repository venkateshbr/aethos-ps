"""Repository layer for the time_entries table.

All queries are tenant-scoped. Soft deletes use deleted_at — we never hard-delete
financial records.
"""

from __future__ import annotations

import logging
from datetime import UTC, date

from supabase import Client

logger = logging.getLogger(__name__)


class TimeEntriesRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list(
        self,
        project_id: str | None = None,
        employee_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        billing_status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List time entries with optional filters. Excludes soft-deleted rows."""
        q = (
            self._db.table("time_entries")
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .order("date", desc=True)
            .limit(limit)
        )
        if project_id:
            q = q.eq("project_id", project_id)
        if employee_id:
            q = q.eq("employee_id", employee_id)
        if date_from:
            q = q.gte("date", date_from.isoformat())
        if date_to:
            q = q.lte("date", date_to.isoformat())
        if billing_status:
            q = q.eq("billing_status", billing_status)

        result = q.execute()
        return result.data or []

    async def get(self, entry_id: str) -> dict | None:
        """Fetch a single time entry by id; returns None if not found or deleted."""
        result = (
            self._db.table("time_entries")
            .select("*")
            .eq("id", entry_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: dict) -> dict:
        """Insert a new time entry; returns the created row."""
        payload = {**data, "tenant_id": self._tenant_id}
        result = self._db.table("time_entries").insert(payload).execute()
        return result.data[0]

    async def update(self, entry_id: str, data: dict) -> dict | None:
        """Partial update on a time entry; returns the updated row or None."""
        result = (
            self._db.table("time_entries")
            .update(data)
            .eq("id", entry_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data[0] if result.data else None

    async def soft_delete(self, entry_id: str) -> bool:
        """Soft-delete by setting deleted_at; returns True if a row was updated."""
        from datetime import datetime

        result = (
            self._db.table("time_entries")
            .update({"deleted_at": datetime.now(UTC).isoformat()})
            .eq("id", entry_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return bool(result.data)

    # ------------------------------------------------------------------
    # Helpers for FK validation
    # ------------------------------------------------------------------

    async def project_belongs_to_tenant(self, project_id: str) -> bool:
        result = (
            self._db.table("projects")
            .select("id")
            .eq("id", project_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return bool(result.data)

    async def employee_belongs_to_tenant(self, employee_id: str) -> bool:
        result = (
            self._db.table("employees")
            .select("id")
            .eq("id", employee_id)
            .eq("tenant_id", self._tenant_id)
            .execute()
        )
        return bool(result.data)
