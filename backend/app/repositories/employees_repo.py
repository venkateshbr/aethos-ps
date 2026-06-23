"""Repository layer for the employees table.

All queries are tenant-scoped. Soft deletes use deleted_at — we never hard-delete
people records (time entries, assignments and invoices reference them).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.services.postgrest_errors import is_missing_column_error
from supabase import Client

logger = logging.getLogger(__name__)

_OPTIONAL_EMPLOYEE_PROFILE_FIELDS = frozenset(
    {
        "target_billable_utilization_pct",
        "practice_area",
        "seniority",
    }
)


class EmployeesRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list(
        self,
        status: str | None = None,
        search: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """List employees, newest first. Excludes soft-deleted rows."""
        q = (
            self._db.table("employees")
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status:
            q = q.eq("status", status)
        if search:
            # PostgREST OR filter across name + email.
            term = f"%{search}%"
            q = q.or_(
                f"first_name.ilike.{term},last_name.ilike.{term},email.ilike.{term}"
            )
        result = q.execute()
        return result.data or []

    async def get(self, employee_id: str) -> dict | None:
        result = (
            self._db.table("employees")
            .select("*")
            .eq("id", employee_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_by_user_id(self, user_id: str) -> dict | None:
        """Resolve the employee record for an authenticated portal user."""
        result = (
            self._db.table("employees")
            .select("*")
            .eq("user_id", user_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data[0] if result.data else None

    async def email_exists(self, email: str, exclude_id: str | None = None) -> bool:
        q = (
            self._db.table("employees")
            .select("id")
            .eq("tenant_id", self._tenant_id)
            .ilike("email", email)
            .is_("deleted_at", "null")
        )
        if exclude_id:
            q = q.neq("id", exclude_id)
        return bool(q.execute().data)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: dict) -> dict:
        payload = {**data, "tenant_id": self._tenant_id}
        try:
            result = self._db.table("employees").insert(payload).execute()
        except Exception as exc:
            if not is_missing_column_error(exc, _OPTIONAL_EMPLOYEE_PROFILE_FIELDS):
                raise
            fallback_payload = _without_optional_employee_profile_fields(payload)
            if fallback_payload == payload:
                raise
            logger.warning(
                "employees table is missing optional profile columns; "
                "retrying insert without those fields"
            )
            result = self._db.table("employees").insert(fallback_payload).execute()
        return result.data[0]

    async def update(self, employee_id: str, data: dict) -> dict | None:
        data = {**data, "updated_at": datetime.now(UTC).isoformat()}
        try:
            result = (
                self._db.table("employees")
                .update(data)
                .eq("id", employee_id)
                .eq("tenant_id", self._tenant_id)
                .is_("deleted_at", "null")
                .execute()
            )
        except Exception as exc:
            if not is_missing_column_error(exc, _OPTIONAL_EMPLOYEE_PROFILE_FIELDS):
                raise
            fallback_data = _without_optional_employee_profile_fields(data)
            if fallback_data == data:
                raise
            logger.warning(
                "employees table is missing optional profile columns; "
                "retrying update without those fields"
            )
            result = (
                self._db.table("employees")
                .update(fallback_data)
                .eq("id", employee_id)
                .eq("tenant_id", self._tenant_id)
                .is_("deleted_at", "null")
                .execute()
            )
        return result.data[0] if result.data else None

    async def soft_delete(self, employee_id: str) -> bool:
        result = (
            self._db.table("employees")
            .update({"deleted_at": datetime.now(UTC).isoformat()})
            .eq("id", employee_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return bool(result.data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def belongs_to_tenant(self, employee_id: str) -> bool:
        result = (
            self._db.table("employees")
            .select("id")
            .eq("id", employee_id)
            .eq("tenant_id", self._tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return bool(result.data)


def _without_optional_employee_profile_fields(payload: dict) -> dict:
    return {
        key: value
        for key, value in payload.items()
        if key not in _OPTIONAL_EMPLOYEE_PROFILE_FIELDS
    }
