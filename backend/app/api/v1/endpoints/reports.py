"""Reporting endpoints — financial and operational snapshots.

All endpoints are read-only (GET). Minimum role: authenticated user (viewer+).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.reports import TrialBalanceReport
from app.services.reports_service import ReportsService
from supabase import Client

router = APIRouter()


def _service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> ReportsService:
    return ReportsService(db, tenant_id)


@router.get("/ar-aging")
def ar_aging(
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> dict:
    """AR aging buckets — outstanding invoices by days overdue."""
    return svc.ar_aging()


@router.get("/ap-aging")
def ap_aging(
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> dict:
    """AP aging buckets — outstanding bills by days overdue."""
    return svc.ap_aging()


@router.get("/project-pnl")
def project_pnl(
    project_id: str | None = Query(None, description="Filter to a single project"),
    period_start: str | None = Query(None, description="Invoice issue date from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Invoice issue date to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Project P&L — revenue vs direct cost with gross margin per project."""
    return svc.project_pnl(
        project_id=project_id,
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/utilization")
def utilization(
    employee_id: str | None = Query(None, description="Filter to a single employee"),
    period_start: str | None = Query(None, description="Time entry date from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Time entry date to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Billable-hour utilisation percentage per employee."""
    return svc.utilization(
        employee_id=employee_id,
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/wip")
def wip(
    engagement_id: str | None = Query(None, description="Filter by engagement"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Work In Progress — unbilled hours x rate per project."""
    return svc.wip(engagement_id=engagement_id)


@router.get("/revenue-by-engagement")
def revenue_by_engagement(
    period_start: str | None = Query(None, description="Invoice issue date from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Invoice issue date to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Total invoiced per engagement within an optional date window."""
    return svc.revenue_by_engagement(
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/revenue-by-service-line")
def revenue_by_service_line(
    period: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Accounting month (YYYY-MM). Omit for all-time.",
    ),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Revenue grouped by service line, optionally filtered to a single month."""
    return svc.revenue_by_service_line(period=period)


@router.get("/cost-by-service-line")
def cost_by_service_line(
    period: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Accounting month (YYYY-MM). Omit for all-time.",
    ),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Labour cost grouped by service line, optionally filtered to a single month."""
    return svc.cost_by_service_line(period=period)


@router.get("/margin-by-service-line")
def margin_by_service_line(
    period: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Accounting month (YYYY-MM). Omit for all-time.",
    ),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Gross margin by service line (revenue - labour cost), optionally filtered to a month."""
    return svc.margin_by_service_line(period=period)


@router.get("/trial-balance", response_model=TrialBalanceReport)
def get_trial_balance(
    as_of_period: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Cumulative through this accounting period (YYYY-MM). Omit for all-time.",
    ),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> TrialBalanceReport:
    """Cumulative trial balance through the specified period (or all-time if omitted).

    Returns one row per account that has at least one posted journal line,
    sorted by account code ascending. ``is_balanced`` is True when the
    absolute difference between grand DR and grand CR totals is within ±0.01
    (the accounting_guardian guarantees this for any validly-posted tenant).

    RBAC: viewer+ (same as other read-only reports).
    """
    return svc.trial_balance(as_of_period=as_of_period)
