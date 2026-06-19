"""Business logic for the Projects resource."""

from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

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

    async def delete_project(self, project_id: str) -> None:
        """Soft-delete a project. Blocks if unbilled time entries exist."""
        import datetime

        row = await self._repo.get(project_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # Guard: refuse deletion while unbilled/approved time entries remain
        unbilled_result = await asyncio.to_thread(
            lambda: self._db.table("time_entries")
            .select("id", count="exact")
            .eq("project_id", project_id)
            .eq("tenant_id", self._tenant_id)
            .in_("billing_status", ["unbilled", "approved"])
            .is_("deleted_at", "null")
            .execute()
        )
        if (unbilled_result.count or 0) > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot delete project: {unbilled_result.count} unbilled "
                    "time entries must be invoiced or marked non-billable first."
                ),
            )

        await asyncio.to_thread(
            lambda: self._db.table("projects")
            .update({"deleted_at": datetime.datetime.now(datetime.UTC).isoformat()})
            .eq("id", project_id)
            .eq("tenant_id", self._tenant_id)
            .execute()
        )
