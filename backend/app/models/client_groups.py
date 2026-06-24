"""Pydantic request/response schemas for client groups."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ClientGroupType = Literal[
    "family_office",
    "portfolio",
    "corporate_group",
    "billing_group",
    "client_relationship",
    "other",
]
ClientGroupStatus = Literal["active", "inactive", "archived"]
ClientGroupMemberRole = Literal[
    "parent",
    "subsidiary",
    "trust",
    "spv",
    "individual",
    "portfolio_company",
    "billing_entity",
    "other",
]


class ClientGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    group_type: ClientGroupType = "other"
    primary_client_id: str | None = None
    billing_client_id: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: ClientGroupStatus = "active"


class ClientGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    group_type: ClientGroupType | None = None
    primary_client_id: str | None = None
    billing_client_id: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: ClientGroupStatus | None = None


class ClientGroupMemberCreate(BaseModel):
    client_id: str
    relationship_role: ClientGroupMemberRole = "other"
    is_primary: bool = False
    start_date: str | None = None
    end_date: str | None = None


class ClientGroupMemberResponse(BaseModel):
    id: str
    tenant_id: str
    group_id: str
    client_id: str
    client_name: str | None = None
    client_kind: str | None = None
    relationship_role: str
    is_primary: bool
    start_date: str | None = None
    end_date: str | None = None
    created_at: str


class ClientGroupResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    group_type: str
    primary_client_id: str | None = None
    billing_client_id: str | None = None
    currency: str | None = None
    status: str
    member_count: int
    members: list[ClientGroupMemberResponse] = []
    created_at: str
    updated_at: str


class ClientGroupListResponse(BaseModel):
    items: list[ClientGroupResponse]
    total: int
