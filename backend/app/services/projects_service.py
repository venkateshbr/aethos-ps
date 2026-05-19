"""Business logic for the Projects resource."""

from __future__ import annotations

import logging

from app.models.projects import ProjectCreate, ProjectResponse
from app.repositories.projects_repo import ProjectRepository
from supabase import Client

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._repo = ProjectRepository(db, tenant_id)

    async def list_projects(self, engagement_id: str) -> list[ProjectResponse]:
        rows = await self._repo.list(engagement_id)
        return [ProjectResponse.from_db(r) for r in rows]

    async def get_project(self, id: str) -> ProjectResponse | None:
        row = await self._repo.get(id)
        return ProjectResponse.from_db(row) if row else None

    async def create_project(self, data: ProjectCreate) -> ProjectResponse:
        payload: dict = {
            "engagement_id": data.engagement_id,
            "name": data.name,
            "currency": data.currency,
            "status": "planning",
        }
        if data.budget is not None:
            payload["budget"] = str(data.budget)
        row = await self._repo.create(payload)
        return ProjectResponse.from_db(row)
