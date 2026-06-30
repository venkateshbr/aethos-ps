"""Models for tenant user administration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

TenantUserRole = Literal[
    "owner",
    "admin",
    "manager",
    "approver",
    "member",
    "auditor",
    "viewer",
]


class TenantUserInviteRequest(BaseModel):
    email: EmailStr
    role: TenantUserRole = "member"
    role_codes: list[str] | None = None
    display_name: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, min_length=8)


class TenantUserUpdateRequest(BaseModel):
    role: TenantUserRole | None = None
    role_codes: list[str] | None = None
    display_name: str | None = Field(default=None, max_length=120)


class TenantUserResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    email: str | None = None
    display_name: str | None = None
    role: str
    role_codes: list[str] = Field(default_factory=list)
    role_labels: list[str] = Field(default_factory=list)
    status: str
    must_change_password: bool = False
    invited_at: str | None = None
    joined_at: str | None = None
    created_at: str
    updated_at: str
    deactivated_at: str | None = None


class TenantUserListResponse(BaseModel):
    items: list[TenantUserResponse]
    total: int


class TenantUserInviteResponse(TenantUserResponse):
    set_password_url: str | None = None
    temp_password: str | None = None


class TenantUserAuditEventResponse(BaseModel):
    id: str
    tenant_id: str
    tenant_user_id: str | None = None
    actor_user_id: str | None = None
    action: str
    previous_role: str | None = None
    new_role: str | None = None
    metadata: dict
    created_at: str


class TenantUserAuditEventListResponse(BaseModel):
    items: list[TenantUserAuditEventResponse]
    total: int
