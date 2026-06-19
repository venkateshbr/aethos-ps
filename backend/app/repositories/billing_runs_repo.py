"""Repository for billing_runs."""
from __future__ import annotations

import asyncio

from supabase import Client


class BillingRunsRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def list_runs(self) -> list[dict]:
        def _list() -> list[dict]:
            return (
                self.db.table("billing_runs")
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .order("created_at", desc=True)
                .execute()
                .data
                or []
            )

        return await asyncio.to_thread(_list)

    async def get_by_id(self, run_id: str) -> dict | None:
        def _get() -> dict | None:
            result = (
                self.db.table("billing_runs")
                .select("*")
                .eq("id", run_id)
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    async def create(self, data: dict) -> dict:
        def _create() -> dict:
            return self.db.table("billing_runs").insert(data).execute().data[0]

        return await asyncio.to_thread(_create)

    async def update(self, run_id: str, data: dict) -> dict | None:
        def _upd() -> dict | None:
            result = (
                self.db.table("billing_runs")
                .update(data)
                .eq("id", run_id)
                .eq("tenant_id", self.tenant_id)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_upd)
