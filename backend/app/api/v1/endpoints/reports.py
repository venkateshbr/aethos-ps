"""Reporting endpoints — financial and operational snapshots.

All endpoints are read-only (GET). Minimum role: authenticated user (viewer+).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_user_rls_client
from app.core.rbac import UserRole, require_role
from app.core.tenant import get_tenant_id
from app.models.reports import (
    BalanceSheetReport,
    CashFlowReport,
    IncomeStatementReport,
    TrialBalanceReport,
)
from app.services.reports_service import ReportsService
from supabase import Client

router = APIRouter()


def _service(
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_user_rls_client),  # noqa: B008
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


@router.get("/project-health")
def project_health(
    period_start: str | None = Query(None, description="Analysis window from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Analysis window to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Project health scores ranked from riskiest to healthiest."""
    return svc.project_health_scores(
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/capacity-planning")
def capacity_planning(
    period_start: str | None = Query(None, description="Capacity window from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Capacity window to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Employee capacity and utilization planning for a date window."""
    return svc.capacity_planning(
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


@router.get("/client-profitability")
def client_profitability(
    client_id: str | None = Query(None, description="Filter to a single client"),
    client_group_id: str | None = Query(None, description="Filter to members of a client group"),
    period_start: str | None = Query(None, description="Invoice/time/expense date from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Invoice/time/expense date to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Client profitability from finalized revenue, labour cost, and expenses."""
    if client_id and client_group_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use either client_id or client_group_id, not both.",
        )
    return svc.client_profitability(
        period_start=period_start,
        period_end=period_end,
        client_id=client_id,
        client_group_id=client_group_id,
    )


@router.get("/client-group-profitability")
def client_group_profitability(
    client_group_id: str | None = Query(None, description="Filter to a single client group"),
    period_start: str | None = Query(None, description="Invoice/time/expense date from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Invoice/time/expense date to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Client group profitability rollups across active member clients."""
    return svc.client_group_profitability(
        period_start=period_start,
        period_end=period_end,
        client_group_id=client_group_id,
    )


@router.get("/segment-profitability")
def segment_profitability(
    group_by: Literal["service_line", "client_kind"] = Query(
        "service_line",
        description="Data-backed segment dimension.",
    ),
    period_start: str | None = Query(None, description="Invoice/time/expense date from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Invoice/time/expense date to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Segment profitability by service line or client kind."""
    return svc.segment_profitability(
        period_start=period_start,
        period_end=period_end,
        group_by=group_by,
    )


@router.get("/practice-dashboard")
def practice_dashboard(
    period_start: str | None = Query(None, description="Practice dashboard window from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Practice dashboard window to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Partner/practice dashboard by service line and employee practice area."""
    return svc.practice_dashboard(
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/pricing-staffing-recommendations")
def pricing_staffing_recommendations(
    period_start: str | None = Query(None, description="Recommendation window from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Recommendation window to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Evidence-backed pricing and staffing recommendations."""
    return svc.pricing_staffing_recommendations(
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/scope-change-advisor")
def scope_change_advisor(
    period_start: str | None = Query(None, description="Scope risk window from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Scope risk window to (YYYY-MM-DD)"),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Scope-change recommendations backed by completed-project comparables."""
    return svc.scope_change_advisor(
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/action-queue")
def action_queue(
    role: Literal["all", "partner", "finance_manager", "project_manager", "ap_clerk"] = Query(
        "all",
        description="Persona queue to return.",
    ),
    period_start: str | None = Query(None, description="Queue evidence window from (YYYY-MM-DD)"),
    period_end: str | None = Query(None, description="Queue evidence window to (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=100),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> list[dict]:
    """Role-specific operating action queue composed from report evidence."""
    return svc.action_queue(
        role=role,
        period_start=period_start,
        period_end=period_end,
        limit=limit,
    )


@router.get("/balance-sheet", response_model=BalanceSheetReport)
def balance_sheet(
    as_of_period: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Cumulative through this accounting period (YYYY-MM). Omit for all-time.",
    ),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> BalanceSheetReport:
    """Balance sheet grouped into assets, liabilities, and equity."""
    return svc.balance_sheet(as_of_period=as_of_period)


@router.get("/income-statement", response_model=IncomeStatementReport)
def income_statement(
    period_start: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Accounting period from (YYYY-MM).",
    ),
    period_end: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Accounting period to (YYYY-MM).",
    ),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> IncomeStatementReport:
    """Income statement for a period range."""
    return svc.income_statement(period_start=period_start, period_end=period_end)


@router.get("/cash-flow", response_model=CashFlowReport)
def cash_flow(
    period_start: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Accounting period from (YYYY-MM).",
    ),
    period_end: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Accounting period to (YYYY-MM).",
    ),
    svc: ReportsService = Depends(_service),  # noqa: B008
    _user: CurrentUser = require_role(UserRole.viewer),  # noqa: B008
) -> CashFlowReport:
    """Direct cash-flow statement from posted cash-account journal lines."""
    return svc.cash_flow(period_start=period_start, period_end=period_end)


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
