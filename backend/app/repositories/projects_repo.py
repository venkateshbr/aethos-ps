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

    async def list(self, engagement_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: self._base_query().eq("engagement_id", engagement_id).execute()
        )
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
