"""Rate Cards router — CRUD endpoints.

RBAC:
  GET  → any authenticated user (viewer and above)
  POST → require_role(admin)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.rate_cards import RateCardCreate, RateCardResponse
from app.services.rate_cards_service import RateCardService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> RateCardService:
    return RateCardService(db, tenant_id)


@router.get("", response_model=list[RateCardResponse])
async def list_rate_cards(
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: RateCardService = Depends(_service),  # noqa: B008
) -> list[RateCardResponse]:
    return await svc.list_rate_cards()


@router.post("", response_model=RateCardResponse, status_code=status.HTTP_201_CREATED)
async def create_rate_card(
    payload: RateCardCreate,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: RateCardService = Depends(_service),  # noqa: B008
) -> RateCardResponse:
    return await svc.create_rate_card(payload)


@router.get("/{id}", response_model=RateCardResponse)
async def get_rate_card(
    id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: RateCardService = Depends(_service),  # noqa: B008
) -> RateCardResponse:
    card = await svc.get_rate_card(id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate card not found")
    return card
