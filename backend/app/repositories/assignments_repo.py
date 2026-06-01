"""Repository for project_assignments. Tenant-scoped.

Note: project_assignments has no deleted_at column (migration 0007); removal is
a hard delete. The row is also CASCADE-deleted if its project is removed.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from supabase import Client

logger = logging.getLogger(__name__)


class AssignmentsRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    async def list_for_project(self, project_id: str) -> list[dict]:
        result = (
            self._db.table("project_assignments")
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .eq("project_id", project_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []

    async def list_for_employee(self, employee_id: str) -> list[dict]:
        result = (
            self._db.table("project_assignments")
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .eq("employee_id", employee_id)
            .execute()
        )
        return result.data or []

    async def get(self, assignment_id: str) -> dict | None:
        result = (
            self._db.table("project_assignments")
            .select("*")
            .eq("id", assignment_id)
            .eq("tenant_id", self._tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def exists(self, project_id: str, employee_id: str) -> bool:
        result = (
            self._db.table("project_assignments")
            .select("id")
            .eq("tenant_id", self._tenant_id)
            .eq("project_id", project_id)
            .eq("employee_id", employee_id)
            .execute()
        )
        return bool(result.data)

    async def create(self, data: dict) -> dict:
        payload = {**data, "tenant_id": self._tenant_id}
        result = self._db.table("project_assignments").insert(payload).execute()
        return result.data[0]

    async def update(self, assignment_id: str, data: dict) -> dict | None:
        data = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._db.table("project_assignments")
            .update(data)
            .eq("id", assignment_id)
            .eq("tenant_id", self._tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def delete(self, assignment_id: str) -> bool:
        result = (
            self._db.table("project_assignments")
            .delete()
            .eq("id", assignment_id)
            .eq("tenant_id", self._tenant_id)
            .execute()
        )
        return bool(result.data)

    async def employees_by_ids(self, ids: list[str]) -> dict[str, dict]:
        """Fetch employees for display denormalisation; returns {id: row}."""
        if not ids:
            return {}
        rows = (
            self._db.table("employees")
            .select("id, first_name, last_name, email")
            .eq("tenant_id", self._tenant_id)
            .in_("id", ids)
            .execute()
            .data
            or []
        )
        return {str(r["id"]): r for r in rows}
