"""Billing Runs router — batch pre-bill containers for retainer engagements.

Routes:
  GET  /billing-runs              — list (viewer+)
  POST /billing-runs              — create draft (manager+)
  GET  /billing-runs/{id}         — get single run (viewer+)
  PATCH /billing-runs/{id}/approve — approve run (owner+)
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.base import AgentDeps
from app.agents.invoice_drafter_agent import draft_invoice
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.billing_runs import BillingRunCreate, BillingRunResponse
from app.models.invoices import InvoiceCreate, InvoiceLineCreate
from app.repositories.billing_runs_repo import BillingRunsRepository
from app.services.invoices_service import InvoicesService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Internal helper — invoice drafting for approved billing runs (#198)
# ---------------------------------------------------------------------------


async def _draft_invoices_for_run(
    run: dict,
    deps: AgentDeps,
    mock_invoice_svc: InvoicesService | None = None,
) -> None:
    """Draft and persist invoices for each retainer engagement in an approved run.

    Called after a billing run is marked approved.  Each engagement in
    ``run['engagement_filter']['engagement_ids']`` gets an InvoiceDraft computed
    by the invoice_drafter_agent, which is then persisted via InvoicesService.

    Errors on individual engagements are logged and skipped so that one bad
    engagement does not abort the entire billing run.
    """
    engagement_ids: list[str] = (
        (run.get("engagement_filter") or {}).get("engagement_ids") or []
    )
    if not engagement_ids:
        logger.info(
            "billing_runs: no engagements in run %s — skipping invoice drafting",
            run.get("id"),
        )
        return

    period_start: date | None = None
    period_end: date | None = None
    try:
        if run.get("period_start"):
            period_start = date.fromisoformat(str(run["period_start"]))
        if run.get("period_end"):
            period_end = date.fromisoformat(str(run["period_end"]))
    except (ValueError, TypeError):
        logger.warning(
            "billing_runs: could not parse period dates for run %s", run.get("id")
        )

    invoice_svc = mock_invoice_svc or InvoicesService(deps.db, deps.tenant_id)

    for engagement_id in engagement_ids:
        try:
            invoice_draft = draft_invoice(
                engagement_id,
                deps,
                period_start=period_start,
                period_end=period_end,
            )

            # Convert InvoiceDraft → InvoiceCreate and persist
            invoice_lines = [
                InvoiceLineCreate(
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    tax_rate_id=line.tax_rate_id,
                    time_entry_id=line.time_entry_id,
                    expense_id=line.expense_id,
                    service_catalogue_id=line.service_catalogue_id,
                )
                for line in invoice_draft.lines
            ]
            invoice_create = InvoiceCreate(
                engagement_id=engagement_id,
                client_id=invoice_draft.client_id,
                currency=invoice_draft.currency,
                issue_date=period_end,
                notes=invoice_draft.summary,
                lines=invoice_lines,
            )
            created_by = deps.user_id or "billing_run_agent"
            await invoice_svc.create_invoice(invoice_create, created_by)
            logger.info(
                "billing_runs: drafted invoice for engagement %s (run %s)",
                engagement_id,
                run.get("id"),
            )
        except Exception as exc:
            logger.error(
                "billing_runs: failed to draft invoice for engagement %s (run %s): %s",
                engagement_id,
                run.get("id"),
                exc,
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# Repository dependency
# ---------------------------------------------------------------------------


def _read_repo(
    db: Client = Depends(get_user_rls_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> BillingRunsRepository:
    return BillingRunsRepository(db, tenant_id)


def _write_repo(
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> BillingRunsRepository:
    return BillingRunsRepository(db, tenant_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[BillingRunResponse])
async def list_billing_runs(
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    repo: BillingRunsRepository = Depends(_read_repo),  # noqa: B008
) -> list[BillingRunResponse]:
    rows = await repo.list_runs()
    return [BillingRunResponse.from_db(r) for r in rows]


@router.post("", response_model=BillingRunResponse, status_code=status.HTTP_201_CREATED)
async def create_billing_run(
    payload: BillingRunCreate,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    repo: BillingRunsRepository = Depends(_write_repo),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> BillingRunResponse:
    data: dict = {
        "tenant_id": tenant_id,
        "name": payload.name,
        "period_start": payload.period_start.isoformat(),
        "period_end": payload.period_end.isoformat(),
        "status": "draft",
    }
    if payload.engagement_filter:
        data["engagement_filter"] = payload.engagement_filter
    row = await repo.create(data)
    return BillingRunResponse.from_db(row)


@router.get("/{run_id}", response_model=BillingRunResponse)
async def get_billing_run(
    run_id: str,
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    repo: BillingRunsRepository = Depends(_read_repo),  # noqa: B008
) -> BillingRunResponse:
    row = await repo.get_by_id(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Billing run not found")
    return BillingRunResponse.from_db(row)


@router.patch("/{run_id}/approve", response_model=BillingRunResponse)
async def approve_billing_run(
    run_id: str,
    current_user: CurrentUser = require_role(UserRole.owner),  # noqa: B008
    repo: BillingRunsRepository = Depends(_write_repo),  # noqa: B008
    db: Client = Depends(get_service_role_client),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> BillingRunResponse:
    row = await repo.get_by_id(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Billing run not found")
    if row["status"] not in ("draft", "reviewed"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve billing run with status={row['status']!r}",
        )
    updated = await repo.update(run_id, {"status": "approved"})
    if updated is None:
        raise HTTPException(status_code=404, detail="Billing run not found after update")

    # Wire: draft and persist invoices for each retainer engagement in this run (#198)
    deps = AgentDeps(
        tenant_id=tenant_id,
        user_id=current_user.id if hasattr(current_user, "id") else str(current_user),
        db=db,
    )
    await _draft_invoices_for_run(updated, deps)

    return BillingRunResponse.from_db(updated)
