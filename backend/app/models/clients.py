"""Pydantic request/response schemas for the Clients API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    kind: Literal["customer", "vendor", "both"] = "customer"
    billing_address: dict | None = None
    tax_id: str | None = Field(default=None, max_length=100)
    payment_terms_days: int = Field(default=30, ge=0, le=365)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: Literal["customer", "vendor", "both"] | None = None
    billing_address: dict | None = None
    tax_id: str | None = Field(default=None, max_length=100)
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)


class ClientResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    kind: str
    payment_terms_days: int
    created_at: str


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
