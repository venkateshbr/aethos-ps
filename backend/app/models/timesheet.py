"""Pydantic models for the employee Timesheet Portal (issue #134, P4/P5).

Self-service surface: the employee logs hours against projects they are
assigned to, then submits a week for approval. ``employee_id`` is always the
authenticated caller — never client-supplied.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class MyProject(BaseModel):
    """A project the current employee is assigned to (with codes for display)."""

    project_id: str
    project_code: str | None = None
    project_name: str
    engagement_id: str
    engagement_code: str | None = None
    engagement_name: str | None = None
    role: str | None = None


class MyProjectListResponse(BaseModel):
    items: list[MyProject]
    total: int


class TimesheetEntryCreate(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=36)
    date: date
    hours: Decimal = Field(..., gt=0, le=24)
    description: str = Field(default="", max_length=1000)
    billable: bool = True
    phase_id: str | None = Field(default=None, max_length=36)


class TimesheetEntryUpdate(BaseModel):
    hours: Decimal | None = Field(default=None, gt=0, le=24)
    description: str | None = Field(default=None, max_length=1000)
    billable: bool | None = None


class TimesheetEntryResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    employee_id: str
    date: str
    hours: str
    description: str
    billable: bool
    status: str  # draft | submitted | approved | rejected
    billing_status: str
    rejected_reason: str | None = None
    created_at: str

    @field_validator("hours", mode="before")
    @classmethod
    def hours_to_str(cls, v: object) -> str:
        return "0" if v is None else str(v)

    @field_validator("date", mode="before")
    @classmethod
    def date_to_str(cls, v: object) -> str:
        return v.isoformat() if isinstance(v, date) else str(v)


class TimesheetEntryListResponse(BaseModel):
    items: list[TimesheetEntryResponse]
    total: int


class SubmitWeekRequest(BaseModel):
    week_start: date = Field(..., description="Monday of the week to submit (YYYY-MM-DD)")


class SubmitWeekResponse(BaseModel):
    submitted: int
    week_start: str
    week_end: str


# --- Approvals (manager side, P5) -------------------------------------------


class ApprovalEntry(BaseModel):
    id: str
    employee_id: str
    employee_name: str | None = None
    project_id: str
    project_code: str | None = None
    date: str
    hours: str
    description: str
    billable: bool

    @field_validator("hours", mode="before")
    @classmethod
    def hours_to_str(cls, v: object) -> str:
        return "0" if v is None else str(v)


class ApprovalListResponse(BaseModel):
    items: list[ApprovalEntry]
    total: int


class ApproveRequest(BaseModel):
    entry_ids: list[str] = Field(..., min_length=1)


class RejectRequest(BaseModel):
    entry_ids: list[str] = Field(..., min_length=1)
    reason: str = Field(default="", max_length=500)


class ApprovalActionResponse(BaseModel):
    updated: int
