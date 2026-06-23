"""Clients router — CRUD endpoints for the clients resource.

All business logic lives in ClientService; this router is thin.

RBAC:
  GET  → any authenticated user (viewer and above)
  POST / PATCH → require_role(manager)
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.clients import ClientCreate, ClientListResponse, ClientResponse, ClientUpdate
from app.services.clients_service import ClientService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

KindQuery = Annotated[str | None, Query(description="Filter by client kind")]
SearchQuery = Annotated[str | None, Query(description="Search by name (contains)")]


def _read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ClientService:
    return ClientService(db, tenant_id)


def _write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> ClientService:
    return ClientService(db, tenant_id)


@router.get("", response_model=ClientListResponse)
async def list_clients(
    kind: KindQuery = None,
    q: SearchQuery = None,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ClientService = Depends(_read_service),  # noqa: B008
) -> ClientListResponse:
    return await svc.list_clients(kind=kind, q=q)


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ClientService = Depends(_write_service),  # noqa: B008
) -> ClientResponse:
    return await svc.create_client(payload)


@router.get("/{id}", response_model=ClientResponse)
async def get_client(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: ClientService = Depends(_read_service),  # noqa: B008
) -> ClientResponse:
    client = await svc.get_client(id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.patch("/{id}", response_model=ClientResponse)
async def update_client(
    id: str,
    payload: ClientUpdate,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: ClientService = Depends(_write_service),  # noqa: B008
) -> ClientResponse:
    client = await svc.update_client(id, payload)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.post("/{id}/vendor-onboarding/approve", response_model=ClientResponse)
async def approve_vendor_onboarding(
    id: str,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: ClientService = Depends(_write_service),  # noqa: B008
) -> ClientResponse:
    client = await svc.approve_vendor_onboarding(id, current_user.user_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client
