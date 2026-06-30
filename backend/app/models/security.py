"""Schemas for enterprise security roles, duties, and privileges."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SecurityPrivilegeResponse(BaseModel):
    code: str
    label: str
    category: str
    description: str = ""


class SecurityDutyResponse(BaseModel):
    code: str
    label: str
    description: str = ""
    privileges: list[SecurityPrivilegeResponse] = Field(default_factory=list)


class SecurityRoleResponse(BaseModel):
    id: str
    code: str
    label: str
    description: str = ""
    legacy_role: str
    is_system: bool
    is_assignable: bool
    rank: int
    duties: list[SecurityDutyResponse] = Field(default_factory=list)
    privilege_codes: list[str] = Field(default_factory=list)


class SecurityRoleListResponse(BaseModel):
    items: list[SecurityRoleResponse]
    total: int


class SecurityPrivilegeListResponse(BaseModel):
    items: list[SecurityPrivilegeResponse]
    total: int


class SecurityRoleCreateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=80)
    label: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    duty_codes: list[str] = Field(default_factory=list)
    legacy_role: str = Field(default="member")


class CurrentUserPermissionsResponse(BaseModel):
    tenant_id: str
    user_id: str
    legacy_role: str
    role_codes: list[str]
    role_labels: list[str]
    privilege_codes: list[str]
    must_change_password: bool = False
