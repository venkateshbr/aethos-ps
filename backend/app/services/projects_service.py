"""Business logic for the Projects resource."""

from __future__ import annotations

import logging

from app.domain.money import serialise_money
from app.models.projects import ProjectCreate, ProjectResponse
from app.repositories.projects_repo import ProjectRepository
from app.services._validation import assert_belongs_to_tenant
from supabase import Client

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._repo = ProjectRepository(db, tenant_id)

    async def list_projects(
        self,
        engagement_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProjectResponse]:
        # Bug #91: engagement_id is optional. When None, list all projects in
        # the tenant — RLS / tenant_id filter handle isolation.
        rows = await self._repo.list(
            engagement_id=engagement_id, limit=limit, offset=offset
        )
        return [ProjectResponse.from_db(r) for r in rows]

    async def get_project(self, id: str) -> ProjectResponse | None:
        row = await self._repo.get(id)
        return ProjectResponse.from_db(row) if row else None

    async def create_project(self, data: ProjectCreate) -> ProjectResponse:
        # Bug #92: tenant A must not attach tenant B's engagement_id.
        await assert_belongs_to_tenant(
            self._db,
            "engagements",
            data.engagement_id,
            self._tenant_id,
            not_found_detail="Engagement not found",
        )

        # #160 — inherit currency from the parent engagement when the caller
        # didn't ship one. Previously the model defaulted to "USD", which
        # silently mis-stamped projects on SGD/GBP/etc. engagements.
        currency = data.currency
        if not currency:
            import asyncio
            eng_row = await asyncio.to_thread(
                lambda: self._db.table("engagements")
                .select("currency")
                .eq("id", data.engagement_id)
                .eq("tenant_id", self._tenant_id)
                .single()
                .execute()
            )
            currency = (eng_row.data or {}).get("currency") or "USD"

        payload: dict = {
            "engagement_id": data.engagement_id,
            "name": data.name,
            "currency": currency,
            "status": "planning",
        }
        if data.budget is not None:
            payload["budget"] = serialise_money(data.budget)
        row = await self._repo.create(payload)
        return ProjectResponse.from_db(row)
