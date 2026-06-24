"""Tax-rate settings endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.tax_rates import TaxRateCreate, TaxRateResponse, TaxRateUpdate
from app.services.tax_rates_service import TaxRatesService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[TaxRateResponse])
async def list_tax_rates(
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_user_rls_client),  # noqa: B008
) -> list[TaxRateResponse]:
    """List system tax rates plus tenant custom rates using RLS."""
    svc = TaxRatesService(db=db, tenant_id=tenant_id)
    try:
        return await svc.list_tax_rates()
    except Exception as exc:
        logger.exception("Failed to list tax rates for tenant %s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc


@router.post("", response_model=TaxRateResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_rate(
    payload: TaxRateCreate,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> TaxRateResponse:
    """Create a tenant-owned custom tax rate."""
    svc = TaxRatesService(db=db, tenant_id=tenant_id)
    try:
        return await svc.create_tax_rate(payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create tax rate for tenant %s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc


@router.patch("/{tax_rate_id}", response_model=TaxRateResponse)
async def update_tax_rate(
    tax_rate_id: str,
    payload: TaxRateUpdate,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> TaxRateResponse:
    """Patch a tenant-owned custom tax rate."""
    svc = TaxRatesService(db=db, tenant_id=tenant_id)
    try:
        return await svc.update_tax_rate(tax_rate_id, payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update tax rate %s for tenant %s", tax_rate_id, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc
