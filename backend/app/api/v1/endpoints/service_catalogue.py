"""Service Catalogue router — CRUD for the service/product catalogue.

RBAC:
  GET  → any authenticated user (viewer and above)
  POST / PATCH → require_role(manager)
  DELETE       → require_role(owner); system services return 403
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.service_catalogue import (
    ServiceCatalogueCreate,
    ServiceCatalogueItem,
    ServiceCatalogueListResponse,
    ServiceCatalogueUpdate,
)
from app.services.service_catalogue_service import ServiceCatalogueService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ServiceCatalogueService:
    return ServiceCatalogueService(db, tenant_id)


@router.get("", response_model=ServiceCatalogueListResponse)
async def list_services(
    service_line: str | None = Query(
        default=None,
        description="Filter by service line (accounting|tax|cosec|payroll|advisory|other)",
    ),
    active_only: bool = Query(
        default=True,
        description="Return only active services (default true)",
    ),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ServiceCatalogueService = Depends(_service),  # noqa: B008
) -> ServiceCatalogueListResponse:
    """List all services in the catalogue.

    Returns system and custom services for the current tenant, ordered by
    service_line then code.  Pass ``active_only=false`` to include inactive.
    """
    return await svc.list_services(service_line=service_line, active_only=active_only)


@router.post("", response_model=ServiceCatalogueItem, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCatalogueCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ServiceCatalogueService = Depends(_service),  # noqa: B008
) -> ServiceCatalogueItem:
    """Create a custom service in the catalogue.

    RBAC: manager or above.
    ``code`` must be unique within the tenant (DB UNIQUE constraint).
    """
    try:
        return await svc.create_service(payload)
    except Exception as exc:
        # Surface DB unique-constraint violation as a 409
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A service with code '{payload.code}' already exists",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create service",
        ) from exc


@router.get("/{id}", response_model=ServiceCatalogueItem)
async def get_service(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ServiceCatalogueService = Depends(_service),  # noqa: B008
) -> ServiceCatalogueItem:
    """Retrieve a single service by ID."""
    item = await svc.get_service(id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
        )
    return item


@router.patch("/{id}", response_model=ServiceCatalogueItem)
async def update_service(
    id: str,
    payload: ServiceCatalogueUpdate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ServiceCatalogueService = Depends(_service),  # noqa: B008
) -> ServiceCatalogueItem:
    """Partially update a service.

    RBAC: manager or above.
    System services can have name/rate overridden but cannot be deactivated via
    PATCH — use DELETE for that distinction.
    """
    item = await svc.update_service(id, payload)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
        )
    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_service(
    id: str,
    _current_user: CurrentUser = require_role(UserRole.owner),  # noqa: B008
    svc: ServiceCatalogueService = Depends(_service),  # noqa: B008
) -> None:
    """Deactivate a service (soft-delete via is_active=False).

    RBAC: owner only.
    System services (is_system=True) cannot be deactivated — returns 403.
    """
    try:
        await svc.deactivate_service(id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
