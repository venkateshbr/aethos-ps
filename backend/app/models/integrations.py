"""Pydantic schemas for integration catalog endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IntegrationStatus = Literal["available", "planned", "research"]
IntegrationRisk = Literal["low", "medium", "high"]


class IntegrationCatalogItem(BaseModel):
    """One supported or planned integration surface."""

    key: str
    category: str
    display_name: str
    provider: str
    status: IntegrationStatus
    risk: IntegrationRisk
    auth_model: str
    supported_markets: list[str] = Field(description="Product market codes")
    data_classes: list[str]
    capabilities: list[str]
    notes: str | None = None


class IntegrationCatalogResponse(BaseModel):
    """Response wrapper for GET /integrations/catalog."""

    integrations: list[IntegrationCatalogItem]
    total: int
