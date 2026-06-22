"""Invoices router — AR invoice lifecycle endpoints.

Routes:
  GET  /invoices                     — list (viewer+)
  POST /invoices                     — create (manager+)
  GET  /invoices/{id}                — get with lines (viewer+)
  PATCH /invoices/{id}/approve       — approve + AR journal (admin+)
  POST  /invoices/{id}/send          — send + Stripe Payment Link (admin+)

Public (no auth):
  GET /public/invoices/{token}       — fetch by public_token for /p/:token page
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.agents.base import AgentDeps
from app.agents.invoice_drafter_agent import draft_invoice
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.invoices import (
    InvoiceCreate,
    InvoiceDraftRequest,
    InvoiceResponse,
    ManualPaymentCreate,
    PublicInvoiceResponse,
)
from app.repositories.invoices_repo import InvoicesRepository
from app.services.invoices_service import InvoicesService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()
public_router = APIRouter()

EngagementIdQuery = Annotated[str | None, Query(description="Filter by engagement")]
StatusQuery = Annotated[
    str | None,
    Query(alias="status", description="Filter by invoice status"),
]


# ---------------------------------------------------------------------------
# Service dependency
# ---------------------------------------------------------------------------


def _read_service(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> InvoicesService:
    return InvoicesService(db, tenant_id)


def _write_service(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> InvoicesService:
    return InvoicesService(db, tenant_id)


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    engagement_id: EngagementIdQuery = None,
    status_filter: StatusQuery = None,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: InvoicesService = Depends(_read_service),  # noqa: B008
) -> list[InvoiceResponse]:
    return await svc.list_invoices(engagement_id=engagement_id, status=status_filter)


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: InvoicesService = Depends(_write_service),  # noqa: B008
) -> InvoiceResponse:
    return await svc.create_invoice(payload, created_by=current_user.user_id)


@router.post("/draft")
async def draft_invoice_for_engagement(
    payload: InvoiceDraftRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> dict:
    """Build a non-persistent invoice draft for an engagement.

    Compatibility route for frontend callers that use ``/invoices/draft``.
    The canonical drafter remains ``draft_invoice``; callers that want a
    persisted invoice should POST the returned lines to ``/invoices``.
    """
    deps = AgentDeps(tenant_id=tenant_id, user_id=current_user.user_id, db=db)
    try:
        invoice_draft = draft_invoice(
            payload.engagement_id,
            deps,
            period_start=payload.period_start,
            period_end=payload.period_end,
        )
    except ValueError as exc:
        logger.warning(
            "draft_invoice raised ValueError for engagement %s: %s",
            payload.engagement_id,
            exc,
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Engagement not found or cannot be invoiced",
        ) from exc
    except Exception as exc:
        logger.exception("draft_invoice failed for engagement %s", payload.engagement_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    return invoice_draft.model_dump(mode="json")


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    svc: InvoicesService = Depends(_read_service),  # noqa: B008
) -> InvoiceResponse:
    return await svc.get_invoice(invoice_id)


@router.patch("/{invoice_id}/approve", response_model=InvoiceResponse)
async def approve_invoice(
    invoice_id: str,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    svc: InvoicesService = Depends(_write_service),  # noqa: B008
) -> InvoiceResponse:
    return await svc.approve_invoice(invoice_id, approved_by=current_user.user_id)


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: str,
    current_user: CurrentUser = require_role(UserRole.owner),  # noqa: B008
    svc: InvoicesService = Depends(_write_service),  # noqa: B008
) -> InvoiceResponse:
    return await svc.send_invoice(invoice_id, sent_by=current_user.user_id)


@router.post("/{invoice_id}/payments", response_model=InvoiceResponse)
async def record_manual_payment(
    invoice_id: str,
    payload: ManualPaymentCreate,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    svc: InvoicesService = Depends(_write_service),  # noqa: B008
) -> InvoiceResponse:
    """Record a payment received outside of Stripe (wire/cheque/cash/etc.).

    Same accounting outcome as the Stripe checkout webhook: inserts a payments
    row, marks the invoice paid, back-links invoiced time entries, and posts
    DR 1100 Bank / CR 1200 AR.
    """
    from decimal import Decimal, InvalidOperation
    try:
        amount = Decimal(payload.amount)
    except InvalidOperation as exc:
        raise HTTPException(status_code=422, detail=f"Invalid amount: {payload.amount!r}") from exc
    return await svc.record_manual_payment(
        invoice_id=invoice_id,
        amount=amount,
        currency=payload.currency,
        paid_at_iso=payload.paid_at,
        notes=payload.notes,
        recorded_by=current_user.user_id,
    )


# ---------------------------------------------------------------------------
# Public endpoint — no auth (for customer-facing payment page)
# ---------------------------------------------------------------------------


@public_router.get("/{token}", response_model=PublicInvoiceResponse)
async def get_public_invoice(
    token: str,
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> PublicInvoiceResponse:
    """Fetch invoice by public_token for the unauthenticated payment page.

    No tenant_id or auth required — the token is the access credential.
    Uses service-role client since there is no user session (bypasses RLS).
    """
    # Public endpoint: we look up without a tenant_id; the public_token is unique
    # across all tenants (UNIQUE constraint in migration 0008).
    repo = InvoicesRepository(db, "")
    row = await repo.get_by_public_token(token)
    if row is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Now fetch lines scoped to the actual tenant
    lines_repo = InvoicesRepository(db, str(row["tenant_id"]))
    lines = await lines_repo.list_lines(str(row["id"]))
    return PublicInvoiceResponse.from_db(row, lines)
