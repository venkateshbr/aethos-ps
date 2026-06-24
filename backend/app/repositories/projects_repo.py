"""Repository: tenant-scoped CRUD for projects."""

from __future__ import annotations

import asyncio
import logging

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "projects"


class ProjectRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _base_query(self):  # type: ignore[no-untyped-def]
        return (
            self.db.table(_TABLE)
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list(
        self,
        engagement_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """List projects in this tenant.

        ``engagement_id`` is optional — bug #91, the original API required it
        and broke any UI that wanted a tenant-wide list. When omitted, every
        non-deleted project in the tenant is returned (RLS + tenant_id filter
        ensure cross-tenant isolation).
        """
        def _query() -> object:
            q = self._base_query()
            if engagement_id is not None:
                q = q.eq("engagement_id", engagement_id)
            # Stable ordering keeps pagination deterministic.
            q = q.order("created_at", desc=True).range(offset, offset + limit - 1)
            return q.execute()

        result = await asyncio.to_thread(_query)
        return result.data or []

    async def get(self, id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._base_query().eq("id", id).execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: dict) -> dict:
        payload = {**data, "tenant_id": self.tenant_id}
        result = await asyncio.to_thread(
            lambda: self.db.table(_TABLE).insert(payload).execute()
        )
        return result.data[0]

    # ------------------------------------------------------------------
    # Project phases / milestones
    # ------------------------------------------------------------------

    async def list_phases(self, project_id: str) -> list[dict]:
        def _query() -> object:
            return (
                self.db.table("project_phases")
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .eq("project_id", project_id)
                .is_("deleted_at", "null")
                .order("order_index")
                .order("end_date")
                .execute()
            )

        result = await asyncio.to_thread(_query)
        return result.data or []

    async def create_phase(self, project_id: str, data: dict) -> dict:
        payload = {**data, "tenant_id": self.tenant_id, "project_id": project_id}
        result = await asyncio.to_thread(
            lambda: self.db.table("project_phases").insert(payload).execute()
        )
        return result.data[0]

    async def update_phase(
        self,
        project_id: str,
        phase_id: str,
        data: dict,
    ) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self.db.table("project_phases")
            .update(data)
            .eq("id", phase_id)
            .eq("project_id", project_id)
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return result.data[0] if result.data else None
