"""Accounting endpoints — period management and manual journal entries.

Endpoints:
  GET    /api/v1/accounting/periods                — list all periods with lock status
  GET    /api/v1/accounting/periods/{period}/close-status — close checklist/status
  GET    /api/v1/accounting/periods/{period}/close-package — close review package
  GET    /api/v1/accounting/periods/{period}/close-readiness — pre-lock reconciliation
  POST   /api/v1/accounting/periods/{period}/propose-wip-accrual — HITL accrual proposal
  POST   /api/v1/accounting/periods/{period}/propose-deferred-revenue-release — HITL revenue release
  POST   /api/v1/accounting/periods/{period}/lock  — lock a period (admin+)
  DELETE /api/v1/accounting/periods/{period}/lock  — unlock a period (owner only)
  POST   /api/v1/accounting/journal-entries        — post a manual GL journal entry (manager+)
  GET    /api/v1/accounting/journal-entries        — list journal entries (viewer+)

Period format: "YYYY-MM" (e.g. "2026-05").

Locking a period prevents any new journal entries from being posted with an
entry_date that falls within that period. The accounting_guardian enforces
this at journal-post time. Before the lock row is inserted, finalized AR/AP
sub-ledger rows are reconciled against posted GL references.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.accounting import (
    JournalEntryListItem,
    ManualJournalEntryIn,
    ManualJournalEntryResponse,
)
from app.services.close_package_service import ClosePackageService
from app.services.close_reconciliation_service import CloseReconciliationService
from app.services.close_status_service import (
    CloseStatusService,
    close_review_blocker_detail,
)
from app.services.manual_journal_service import ManualJournalService
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

_PERIOD_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PeriodStatus(BaseModel):
    period: str
    locked: bool
    locked_at: str | None = None
    locked_by: str | None = None


class PeriodListResponse(BaseModel):
    periods: list[PeriodStatus]


class PeriodLockResponse(BaseModel):
    period: str
    action: str  # "locked" | "unlocked"
    message: str


class PeriodCloseFinding(BaseModel):
    code: str
    source_table: str
    source_id: str
    source_number: str | None
    reason: str
    expected_reference_type: str


class PeriodCloseReadinessResponse(BaseModel):
    period: str
    ready: bool
    findings: list[PeriodCloseFinding]
    trial_balance_balanced: bool


class PeriodCloseChecklistItem(BaseModel):
    code: str
    label: str
    status: str
    blocking: bool
    summary: str
    count: int


class PeriodClosePendingReview(BaseModel):
    id: str
    agent_name: str
    action_type: str
    status: str
    summary: str


class PeriodCloseStatusResponse(BaseModel):
    period: str
    status: str
    locked: bool
    locked_at: str | None
    locked_by: str | None
    ready_to_lock: bool
    checklist: list[PeriodCloseChecklistItem]
    findings: list[PeriodCloseFinding]
    pending_reviews: list[PeriodClosePendingReview]
    lock_blockers: list[str]


class PeriodClosePackageResponse(BaseModel):
    period: str
    period_start: str
    period_end: str
    previous_period: str
    generated_at: str
    close_status: dict[str, Any]
    gl_summary: dict[str, Any]
    previous_gl_summary: dict[str, Any]
    working_capital: dict[str, Any]
    trial_balance: dict[str, Any]
    ar_aging: dict[str, str]
    ap_aging: dict[str, str]
    wip: list[dict[str, Any]]
    service_line_margins: list[dict[str, Any]]
    variance_commentary: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_period(period: str) -> None:
    """Raise 422 if the period string is not a valid YYYY-MM."""
    if not _PERIOD_PATTERN.match(period):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid period format {period!r} — expected YYYY-MM (e.g. '2026-05')",
        )


def _generate_periods(months_back: int = 12, months_forward: int = 3) -> list[str]:
    """Generate a list of period strings centred around today."""
    today = date.today()
    # Start from months_back ago
    year = today.year
    month = today.month - months_back
    while month <= 0:
        month += 12
        year -= 1

    periods = []
    y, m = year, month
    total_months = months_back + months_forward + 1
    for _ in range(total_months):
        periods.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return periods


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/periods", response_model=PeriodListResponse)
async def list_periods(
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> PeriodListResponse:
    """Return periods (last 12 months + next 3) with their lock status."""
    try:
        lock_rows = (
            db.table("period_locks")
            .select("period, locked_at, locked_by")
            .eq("tenant_id", tenant_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Failed to fetch period locks for tenant %s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    locked_periods: dict[str, dict] = {
        row["period"]: row for row in (lock_rows.data or [])
    }

    periods = _generate_periods()
    result = []
    for period in periods:
        lock = locked_periods.get(period)
        result.append(
            PeriodStatus(
                period=period,
                locked=lock is not None,
                locked_at=str(lock["locked_at"]) if lock else None,
                locked_by=str(lock["locked_by"]) if lock else None,
            )
        )

    return PeriodListResponse(periods=result)


@router.get("/periods/{period}/close-status", response_model=PeriodCloseStatusResponse)
async def close_status(
    period: str,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> PeriodCloseStatusResponse:
    """Return the derived close checklist and lock blockers for a period."""
    _validate_period(period)
    try:
        result = CloseStatusService(db, tenant_id).get_status(period)
    except Exception as exc:
        logger.exception("Failed to build close status for period %s tenant %s", period, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    return PeriodCloseStatusResponse(**result.as_dict())


@router.get("/periods/{period}/close-package", response_model=PeriodClosePackageResponse)
async def close_package(
    period: str,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> PeriodClosePackageResponse:
    """Return a review-ready close package with deterministic commentary."""
    _validate_period(period)
    try:
        result = ClosePackageService(db, tenant_id).build_package(period)
    except Exception as exc:
        logger.exception(
            "Failed to build close package for tenant %s period %s",
            tenant_id,
            period,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    return PeriodClosePackageResponse(**result)


@router.get("/periods/{period}/close-readiness", response_model=PeriodCloseReadinessResponse)
async def close_readiness(
    period: str,
    _current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> PeriodCloseReadinessResponse:
    """Return reconciliation status for a period before attempting to lock it."""
    _validate_period(period)
    try:
        result = CloseReconciliationService(db, tenant_id).check_period(period)
    except Exception as exc:
        logger.exception("Failed to reconcile period %s for tenant %s", period, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    return PeriodCloseReadinessResponse(
        period=result.period,
        ready=result.ready,
        findings=[PeriodCloseFinding(**finding.as_dict()) for finding in result.findings],
        trial_balance_balanced=result.trial_balance_balanced,
    )


@router.post("/periods/{period}/propose-wip-accrual")
async def propose_wip_accrual(
    period: str,
    debit_account_code: str = Query("1200", min_length=1, max_length=20),
    credit_account_code: str = Query("4000", min_length=1, max_length=20),
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> dict:
    """Create HITL draft-journal suggestions for unbilled WIP accruals."""
    _validate_period(period)

    from app.agents.accrual_agent import (
        AccrualProposalError,
        write_wip_accrual_suggestions,
    )
    from app.agents.base import AgentDeps

    deps = AgentDeps(tenant_id=tenant_id, user_id=current_user.user_id, db=db)
    try:
        return await write_wip_accrual_suggestions(
            deps,
            period,
            debit_account_code=debit_account_code,
            credit_account_code=credit_account_code,
        )
    except AccrualProposalError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/periods/{period}/propose-deferred-revenue-release")
async def propose_deferred_revenue_release(
    period: str,
    deferred_account_code: str = Query("2200", min_length=1, max_length=20),
    revenue_account_code: str = Query("4000", min_length=1, max_length=20),
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> dict:
    """Create HITL draft-journal suggestions for deferred revenue releases."""
    _validate_period(period)

    from app.agents.base import AgentDeps
    from app.agents.revenue_recognition_agent import (
        RevenueRecognitionProposalError,
        write_deferred_revenue_release_suggestions,
    )

    deps = AgentDeps(tenant_id=tenant_id, user_id=current_user.user_id, db=db)
    try:
        return await write_deferred_revenue_release_suggestions(
            deps,
            period,
            deferred_account_code=deferred_account_code,
            revenue_account_code=revenue_account_code,
        )
    except RevenueRecognitionProposalError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/periods/{period}/lock", response_model=PeriodLockResponse)
async def lock_period(
    period: str,
    current_user: CurrentUser = require_role(UserRole.admin),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> PeriodLockResponse:
    """Lock a period, preventing new journal entries.

    Requires admin role or higher.
    """
    _validate_period(period)

    # Check if already locked
    try:
        existing = (
            db.table("period_locks")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("period", period)
            .execute()
        )
    except Exception as exc:
        logger.exception("Failed to check period lock status for tenant %s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Period {period} is already locked",
        )

    try:
        reconciliation = CloseReconciliationService(db, tenant_id).check_period(period)
    except Exception as exc:
        logger.exception("Failed to reconcile period %s for tenant %s", period, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    if not reconciliation.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=reconciliation.as_error_detail(),
        )

    pending_reviews = CloseStatusService(db, tenant_id).pending_close_reviews(period)
    if pending_reviews:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=close_review_blocker_detail(period, pending_reviews),
        )

    # Insert the lock
    try:
        db.table("period_locks").insert(
            {
                "tenant_id": tenant_id,
                "period": period,
                "locked_at": datetime.now(UTC).isoformat(),
                "locked_by": current_user.user_id,
            }
        ).execute()
    except Exception as exc:
        logger.exception("Failed to lock period %s for tenant %s", period, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    logger.info(
        "Period locked: period=%s tenant=%s user=%s",
        period,
        tenant_id,
        current_user.user_id,
    )
    return PeriodLockResponse(
        period=period,
        action="locked",
        message=f"Period {period} is now locked. New journal entries are blocked for this period.",
    )


@router.delete("/periods/{period}/lock", response_model=PeriodLockResponse)
async def unlock_period(
    period: str,
    current_user: CurrentUser = require_role(UserRole.owner),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> PeriodLockResponse:
    """Unlock a period (owner only — this is a high-risk operation).

    Unlocking allows new journal entries to be posted in a previously closed period.
    This operation is auditable and requires owner-level privileges.
    """
    _validate_period(period)

    try:
        result = (
            db.table("period_locks")
            .delete()
            .eq("tenant_id", tenant_id)
            .eq("period", period)
            .execute()
        )
    except Exception as exc:
        logger.exception("Failed to unlock period %s for tenant %s", period, tenant_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Period {period} is not locked",
        )

    logger.info(
        "Period unlocked: period=%s tenant=%s user=%s",
        period,
        tenant_id,
        current_user.user_id,
    )
    return PeriodLockResponse(
        period=period,
        action="unlocked",
        message=f"Period {period} has been unlocked.",
    )


# ---------------------------------------------------------------------------
# Manual Journal Entry routes
# ---------------------------------------------------------------------------


@router.post(
    "/journal-entries",
    response_model=ManualJournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_journal(
    payload: ManualJournalEntryIn,
    current_user: CurrentUser = require_role(UserRole.manager),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> ManualJournalEntryResponse:
    """Post a manual GL journal entry.

    All entries are gated by the accounting_guardian (L3 hard gate):
    balance check, period lock, and account validity. The journal is
    immutable once posted — corrections require reversing entries.

    RBAC: manager or owner only.
    """
    svc = ManualJournalService(db=db, tenant_id=tenant_id, user_id=current_user.user_id)
    return await svc.post_manual_journal(payload)


@router.get("/journal-entries", response_model=list[JournalEntryListItem])
async def list_journal_entries(
    reference_type: str | None = Query(None, description="Filter by reference_type (e.g. 'manual', 'invoice')"),
    limit: int = Query(50, ge=1, le=100, description="Maximum rows to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> list[JournalEntryListItem]:
    """List journal entries for the tenant, newest first.

    Optionally filter by ``reference_type`` (e.g. ``manual``, ``invoice``,
    ``bill``, ``payment``). Paginate with ``limit`` and ``offset``.

    RBAC: viewer+ (all authenticated tenant members).
    """
    svc = ManualJournalService(db=db, tenant_id=tenant_id, user_id=_current_user.user_id)
    return await svc.list_journal_entries(
        reference_type=reference_type,
        limit=limit,
        offset=offset,
    )
