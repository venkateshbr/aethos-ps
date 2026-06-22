"""Bills (AP) router.

Endpoints:
  GET    /bills              → list bills with optional status/client_id filters
  POST   /bills              → create a draft bill (manager+)
  GET    /bills/aging        → AP aging buckets
  GET    /bills/{bill_id}    → get bill detail with lines
  PATCH  /bills/{bill_id}/approve → approve bill + post GL journal (admin+)

RBAC:
  read:    any authenticated user (viewer and above)
  create:  manager and above
  approve: admin and above
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.bills import (
    ApAgingResponse,
    BillApproveResponse,
    BillCreate,
    BillListResponse,
    BillResponse,
)
from app.services.bills_service import BillsService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


def _service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> BillsService:
    return BillsService(db, tenant_id)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get("", response_model=BillListResponse)
async def list_bills(
    status: str | None = Query(None, description="Filter by bill status"),
    client_id: str | None = Query(None, description="Filter by client/vendor UUID"),
    limit: int = Query(50, ge=1, le=100),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: BillsService = Depends(_service),  # noqa: B008
) -> BillListResponse:
    return await svc.list_bills(status_filter=status, client_id=client_id, limit=limit)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post("", response_model=BillResponse, status_code=201)
async def create_bill(
    payload: BillCreate,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: BillsService = Depends(_service),  # noqa: B008
) -> BillResponse:
    return await svc.create_bill(payload)


# ---------------------------------------------------------------------------
# AP Aging — must come before /{bill_id} to avoid shadowing
# ---------------------------------------------------------------------------


@router.get("/aging", response_model=ApAgingResponse)
async def ap_aging(
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: BillsService = Depends(_service),  # noqa: B008
) -> ApAgingResponse:
    return await svc.ap_aging()


# ---------------------------------------------------------------------------
# Get detail
# ---------------------------------------------------------------------------


@router.get("/{bill_id}", response_model=BillResponse)
async def get_bill(
    bill_id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: BillsService = Depends(_service),  # noqa: B008
) -> BillResponse:
    bill = await svc.get_bill(bill_id)
    if bill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bill {bill_id!r} not found",
        )
    return bill


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------


@router.patch("/{bill_id}/approve", response_model=BillApproveResponse)
async def approve_bill(
    bill_id: str,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: BillsService = Depends(_service),  # noqa: B008
) -> BillApproveResponse:
    return await svc.approve_bill(bill_id, current_user.user_id)


@router.post("/{bill_id}/void", response_model=BillResponse)
async def void_bill(
    bill_id: str,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: BillsService = Depends(_service),  # noqa: B008
) -> BillResponse:
    """Void a bill.

    Draft bills are status-updated. Approved bills first post a reversing GL
    journal through the accounting guardian, then move to ``voided``.
    """
    return await svc.void_bill(bill_id, current_user.user_id)
