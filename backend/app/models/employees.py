"""Pydantic request/response models for the employees resource.

The ``employees`` table (migration 0001) is the resource master for everyone who
does billable work — staff, contractors, consultants. It is decoupled from auth:
an employee may or may not have a login (``user_id`` / ``tenant_user_id`` set via
the invite flow). See issue #134.

Money rules:
- Rates use Decimal (never float) and serialise as strings in JSON responses.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class EmploymentType(StrEnum):
    full_time = "full_time"
    part_time = "part_time"
    contractor = "contractor"
    consultant = "consultant"


class PracticeArea(StrEnum):
    accounting = "accounting"
    tax = "tax"
    cosec = "cosec"
    payroll = "payroll"
    advisory = "advisory"
    other = "other"


class Seniority(StrEnum):
    partner = "partner"
    director = "director"
    manager = "manager"
    senior = "senior"
    associate = "associate"
    analyst = "analyst"


class EmployeeCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    title: str | None = Field(default=None, max_length=160)
    department: str | None = Field(default=None, max_length=160)
    employment_type: EmploymentType = EmploymentType.full_time
    default_bill_rate: Decimal | None = Field(default=None, ge=0)
    default_bill_rate_currency: str | None = Field(default=None, min_length=3, max_length=3)
    cost_rate: Decimal | None = Field(default=None, ge=0)
    available_hours_per_week: Decimal | None = Field(default=None, ge=0, le=168)
    target_billable_utilization_pct: Decimal | None = Field(default=None, ge=0, le=100)
    manager_id: str | None = Field(default=None, max_length=36)
    skills: list[str] = Field(default_factory=list)
    practice_area: PracticeArea | None = None
    seniority: Seniority | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    title: str | None = Field(default=None, max_length=160)
    department: str | None = Field(default=None, max_length=160)
    employment_type: EmploymentType | None = None
    default_bill_rate: Decimal | None = Field(default=None, ge=0)
    default_bill_rate_currency: str | None = Field(default=None, min_length=3, max_length=3)
    cost_rate: Decimal | None = Field(default=None, ge=0)
    available_hours_per_week: Decimal | None = Field(default=None, ge=0, le=168)
    target_billable_utilization_pct: Decimal | None = Field(default=None, ge=0, le=100)
    manager_id: str | None = Field(default=None, max_length=36)
    skills: list[str] | None = None
    status: str | None = Field(default=None, max_length=40)
    practice_area: PracticeArea | None = None
    seniority: Seniority | None = None


class EmployeeResponse(BaseModel):
    id: str
    tenant_id: str
    first_name: str
    last_name: str
    email: str
    title: str | None = None
    department: str | None = None
    employment_type: str
    default_bill_rate: str | None = None
    default_bill_rate_currency: str | None = None
    cost_rate: str | None = None
    available_hours_per_week: str | None = None
    target_billable_utilization_pct: str | None = None
    manager_id: str | None = None
    skills: list[str] = Field(default_factory=list)
    # Login linkage — null until the employee is invited to the portal (#134 P3).
    user_id: str | None = None
    tenant_user_id: str | None = None
    has_login: bool = False
    status: str
    created_at: str
    updated_at: str | None = None
    practice_area: str | None = None
    seniority: str | None = None

    @field_validator(
        "default_bill_rate",
        "cost_rate",
        "available_hours_per_week",
        "target_billable_utilization_pct",
        mode="before",
    )
    @classmethod
    def decimal_to_str(cls, v: object) -> str | None:
        """Coerce Decimal / float / int from the DB row to a string (None stays None)."""
        if v is None:
            return None
        return str(v)

    @model_validator(mode="after")
    def _derive_has_login(self) -> EmployeeResponse:
        """has_login always reflects whether a Supabase auth user is linked."""
        object.__setattr__(self, "has_login", bool(self.user_id))
        return self


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int


class EmployeeInviteRequest(BaseModel):
    # Optional admin-set initial password. When omitted, a strong temporary
    # password is generated and returned once (pilot: no email is sent).
    password: str | None = Field(default=None, min_length=8, max_length=128)


class EmployeeInviteResponse(BaseModel):
    employee_id: str
    user_id: str
    tenant_user_id: str
    email: str
    role: str = "employee"
    # One-time set-password (recovery) link the admin shares with the employee.
    # Null if Supabase could not mint one (the temp_password is then the fallback).
    set_password_url: str | None = None
    # Temporary password shown ONCE (pilot only — Resend email not yet wired).
    temp_password: str | None = None
