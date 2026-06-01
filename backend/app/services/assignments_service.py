"""Business logic for project_assignments (issue #134, Phase 2).

Rules:
- The project must belong to the tenant.
- The employee must belong to the tenant.
- (project_id, employee_id) is unique — re-assigning the same person 409s.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.models.assignments import (
    AssignmentCreate,
    AssignmentListResponse,
    AssignmentResponse,
)
from app.repositories.assignments_repo import AssignmentsRepository
from app.repositories.employees_repo import EmployeesRepository
from app.services._validation import assert_belongs_to_tenant
from supabase import Client

logger = logging.getLogger(__name__)


class AssignmentsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._repo = AssignmentsRepository(db, tenant_id)
        self._employees = EmployeesRepository(db, tenant_id)

    async def list_for_project(self, project_id: str) -> AssignmentListResponse:
        await assert_belongs_to_tenant(
            self._db, "projects", project_id, self._tenant_id,
            not_found_detail="Project not found",
        )
        rows = await self._repo.list_for_project(project_id)
        emp_map = await self._repo.employees_by_ids(
            [str(r["employee_id"]) for r in rows]
        )
        items = [_row_to_response(r, emp_map.get(str(r["employee_id"]))) for r in rows]
        return AssignmentListResponse(items=items, total=len(items))

    async def create(self, project_id: str, data: AssignmentCreate) -> AssignmentResponse:
        await assert_belongs_to_tenant(
            self._db, "projects", project_id, self._tenant_id,
            not_found_detail="Project not found",
        )
        if not await self._employees.belongs_to_tenant(data.employee_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee {data.employee_id!r} not found",
            )
        if await self._repo.exists(project_id, data.employee_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That employee is already assigned to this project",
            )
        payload: dict = {
            "project_id": project_id,
            "employee_id": data.employee_id,
            "role": data.role,
            "override_rate": str(data.override_rate) if data.override_rate is not None else None,
            "start_date": data.start_date,
            "end_date": data.end_date,
        }
        row = await self._repo.create(payload)
        emp = (await self._repo.employees_by_ids([data.employee_id])).get(data.employee_id)
        return _row_to_response(row, emp)

    async def delete(self, project_id: str, assignment_id: str) -> None:
        existing = await self._repo.get(assignment_id)
        if existing is None or str(existing["project_id"]) != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found",
            )
        await self._repo.delete(assignment_id)


def _row_to_response(row: dict, emp: dict | None) -> AssignmentResponse:
    name = None
    email = None
    if emp:
        name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        email = emp.get("email")
    return AssignmentResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        project_id=str(row["project_id"]),
        employee_id=str(row["employee_id"]),
        role=row.get("role"),
        override_rate=row.get("override_rate"),
        start_date=str(row["start_date"]) if row.get("start_date") else None,
        end_date=str(row["end_date"]) if row.get("end_date") else None,
        created_at=str(row["created_at"]),
        employee_name=name,
        employee_email=email,
    )
