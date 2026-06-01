"""Pydantic models for project_assignments (issue #134, Phase 2).

An assignment maps an employee onto a project with a role and optional billing
overrides. The invoice drafter reads these to resolve each time entry's role →
rate. Money fields are Decimal and serialise as strings.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class AssignmentCreate(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=36)
    role: str | None = Field(default=None, max_length=120)
    override_rate: Decimal | None = Field(default=None, ge=0)
    start_date: str | None = None
    end_date: str | None = None


class AssignmentResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    employee_id: str
    role: str | None = None
    override_rate: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    created_at: str
    # Denormalised for display (joined from employees).
    employee_name: str | None = None
    employee_email: str | None = None

    @field_validator("override_rate", mode="before")
    @classmethod
    def decimal_to_str(cls, v: object) -> str | None:
        return None if v is None else str(v)


class AssignmentListResponse(BaseModel):
    items: list[AssignmentResponse]
    total: int
