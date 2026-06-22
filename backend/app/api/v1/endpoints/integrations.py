"""Integration catalog endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.integrations import IntegrationCatalogResponse, IntegrationStatus
from app.services.integrations_service import list_integrations

router = APIRouter()


@router.get("/catalog", response_model=IntegrationCatalogResponse)
async def get_integration_catalog(
    category: str | None = None,
    status: IntegrationStatus | None = None,
) -> IntegrationCatalogResponse:
    """Return public integration catalog and roadmap metadata."""
    items = list_integrations(category=category, status=status)
    return IntegrationCatalogResponse(integrations=items, total=len(items))
