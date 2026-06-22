"""Pydantic request/response schemas for the Service Catalogue API.

Money (default_rate) is serialised as a string in JSON — never float.
service_line and billing_unit values are constrained to match the DB CHECK
constraints so validation fires at the API boundary.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ServiceLine = Literal["accounting", "tax", "cosec", "payroll", "advisory", "other"]
BillingUnit = Literal[
    "hour", "fixed", "retainer", "per_employee", "per_entity", "per_event", "milestone"
]


class ServiceCatalogueItem(BaseModel):
    """Full representation returned from GET endpoints."""

    id: str
    code: str
    name: str
    description: str | None = None
    service_line: ServiceLine
    billing_unit: BillingUnit
    default_rate: str | None = None          # NUMERIC serialised as string
    default_currency: str = "GBP"
    revenue_account_id: str | None = None
    revenue_account_code: str | None = None  # joined from accounts
    revenue_account_name: str | None = None  # joined from accounts
    is_active: bool
    is_system: bool


class ServiceCatalogueListResponse(BaseModel):
    items: list[ServiceCatalogueItem]
    total: int


class ServiceCatalogueCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    service_line: ServiceLine
    billing_unit: BillingUnit
    default_rate: str | None = None          # caller sends string; we store as NUMERIC
    default_currency: str = Field(default="GBP", min_length=3, max_length=3)
    revenue_account_id: str | None = None


class ServiceCatalogueUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_rate: str | None = None
    default_currency: str | None = None
    revenue_account_id: str | None = None
    is_active: bool | None = None
