"""Collections policy router.

Managers configure reminder cadence and auto-send limits here; the nightly
collections worker consumes the same policy rows.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.collections_policy import (
    CollectionsPolicyListResponse,
    CollectionsPolicyResponse,
    CollectionsPolicyUpsert,
)
from app.services.collections_policy_service import CollectionsPolicyService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

ClientIdQuery = Annotated[
    str | None,
    Query(description="Optional client ID for resolving a client-specific override"),
]


def _read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> CollectionsPolicyService:
    return CollectionsPolicyService(db, tenant_id)


def _write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> CollectionsPolicyService:
    return CollectionsPolicyService(db, tenant_id)


@router.get("/policies", response_model=CollectionsPolicyListResponse)
async def list_collections_policies(
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: CollectionsPolicyService = Depends(_read_service),  # noqa: B008
) -> CollectionsPolicyListResponse:
    """List saved tenant/client collections policies for the current tenant."""
    return await svc.list_policies()


@router.get("/policies/effective", response_model=CollectionsPolicyResponse)
async def get_effective_collections_policy(
    client_id: ClientIdQuery = None,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: CollectionsPolicyService = Depends(_read_service),  # noqa: B008
) -> CollectionsPolicyResponse:
    """Resolve the effective policy, falling back to the system default."""
    return await svc.get_effective_policy(client_id=client_id)


@router.put("/policies/default", response_model=CollectionsPolicyResponse)
async def upsert_default_collections_policy(
    payload: CollectionsPolicyUpsert,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: CollectionsPolicyService = Depends(_write_service),  # noqa: B008
) -> CollectionsPolicyResponse:
    """Create or replace the tenant-wide default collections policy."""
    try:
        return await svc.upsert_default_policy(payload)
    except Exception as exc:
        logger.exception("Failed to upsert collections policy")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save collections policy",
        ) from exc


@router.put("/policies/clients/{client_id}", response_model=CollectionsPolicyResponse)
async def upsert_client_collections_policy(
    client_id: str,
    payload: CollectionsPolicyUpsert,
    _current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: CollectionsPolicyService = Depends(_write_service),  # noqa: B008
) -> CollectionsPolicyResponse:
    """Create or replace a client-specific collections policy override."""
    try:
        return await svc.upsert_client_policy(client_id, payload)
    except Exception as exc:
        logger.exception("Failed to upsert client collections policy")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save collections policy",
        ) from exc
