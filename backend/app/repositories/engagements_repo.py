"""Repository: tenant-scoped CRUD for engagements and engagement_billing_terms."""

from __future__ import annotations

import asyncio
import logging

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "engagements"
_TERMS_TABLE = "engagement_billing_terms"


class EngagementRepository:
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
        status: str | None = None,
        client_id: str | None = None,
    ) -> list[dict]:
        query = self._base_query()
        if status:
            query = query.eq("status", status)
        if client_id:
            query = query.eq("client_id", client_id)
        result = await asyncio.to_thread(lambda: query.execute())
        return result.data or []

    async def get(self, id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._base_query().eq("id", id).execute()
        )
        return result.data[0] if result.data else None

    async def get_billing_terms(self, engagement_id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self.db.table(_TERMS_TABLE)
            .select("*")
            .eq("engagement_id", engagement_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
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

    async def create_billing_terms(self, engagement_id: str, terms: dict) -> dict:
        payload = {
            **terms,
            "engagement_id": engagement_id,
            "tenant_id": self.tenant_id,
        }
        result = await asyncio.to_thread(
            lambda: self.db.table(_TERMS_TABLE).insert(payload).execute()
        )
        return result.data[0]

    async def update_status(self, id: str, status: str) -> dict | None:
        existing = await self.get(id)
        if existing is None:
            return None
        result = await asyncio.to_thread(
            lambda: self.db.table(_TABLE)
            .update({"status": status})
            .eq("id", id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None
