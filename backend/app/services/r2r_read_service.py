"""Read-only R2R management reporting and close drilldown service."""

from __future__ import annotations

import datetime
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.money import serialise_money
from app.services.close_package_service import (
    ClosePackageService,
    period_bounds,
    previous_period_for,
)
from app.services.reports_service import ReportsService
from supabase import Client

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NO_ACTIVITY_STATUSES = {"no_activity", "limited_activity"}


class R2RReadService:
    """Tenant-scoped read model for management reporting and close review."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def management_pack_read_pack(
        self,
        *,
        period: str,
        comparison_period: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        current_period = normalise_period(period)
        comparison = (
            normalise_period(comparison_period)
            if comparison_period
            else previous_period_for(current_period)
        )
        capped_limit = max(1, min(limit, 25))
        bounds = period_bounds(current_period)

        reports = ReportsService(self.db, self.tenant_id)
        close_package_service = ClosePackageService(
            self.db,
            self.tenant_id,
            reports_service=reports,
        )
        current_package = close_package_service.build_package(current_period)
        comparison_package = close_package_service.build_package(comparison)

        current_statements = self._financial_statement_summary(
            reports,
            period=current_period,
            limit=capped_limit,
        )
        comparison_statements = self._financial_statement_summary(
            reports,
            period=comparison,
            limit=capped_limit,
        )
        journal_summary = self._journal_summary(current_period, limit=capped_limit)
        close_status = _safe_close_status(current_package.get("close_status"))
        close_tasks = self._close_tasks(current_period)
        close_task_state = _close_task_state(close_tasks, close_status)
        close_blockers = _close_blockers(
            close_status=close_status,
            close_task_state=close_task_state,
            draft_journals=journal_summary["draft_journals"],
        )
        project_margin = self._project_margin_highlights(
            reports,
            period_start=bounds.start,
            period_end=bounds.end,
            limit=capped_limit,
        )
        utilization = self._utilization_highlights(
            reports,
            period_start=bounds.start,
            period_end=bounds.end,
            limit=capped_limit,
        )
        data_availability = _data_availability(
            current_package=current_package,
            current_statements=current_statements,
            journal_summary=journal_summary,
            project_margin=project_margin,
            utilization=utilization,
        )

        return {
            "tenant_id": self.tenant_id,
            "generated_at": datetime.datetime.now().astimezone().isoformat(),
            "period": current_period,
            "period_start": bounds.start,
            "period_end": bounds.end,
            "comparison_period": comparison,
            "query": {
                "period": current_period,
                "comparison_period": comparison,
                "limit": capped_limit,
            },
            "data_availability": data_availability,
            "close_status": close_status,
            "close_task_checklist_state": close_task_state,
            "close_blockers": close_blockers,
            "financial_statements": {
                "current": current_statements,
                "comparison": comparison_statements,
            },
            "statement_variances": _statement_variances(
                current=current_statements,
                comparison=comparison_statements,
                current_period=current_period,
                comparison_period=comparison,
            ),
            "working_capital_movement": self._working_capital_movement(
                current_package=current_package,
                comparison_package=comparison_package,
                current_period=current_period,
                comparison_period=comparison,
            ),
            "project_margin_highlights": project_margin,
            "utilization_highlights": utilization,
            "journal_summary": journal_summary,
            "management_commentary": _safe_commentary(current_package.get("variance_commentary")),
            "recommended_next_actions": _recommended_next_actions(
                data_availability=data_availability,
                close_status=close_status,
                close_task_state=close_task_state,
                journal_summary=journal_summary,
                project_margin=project_margin,
                utilization=utilization,
            ),
            "response_contract": [
                "Management-pack answers must include revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers.",
                "Close drilldowns must mention task owner/owner role, status, blocker, and next action.",
                "Do not post journals or lock the period from a read-only management-pack answer.",
            ],
        }

    def _financial_statement_summary(
        self,
        reports: ReportsService,
        *,
        period: str,
        limit: int,
    ) -> dict[str, Any]:
        trial_balance = reports.trial_balance(as_of_period=period)
        income_statement = reports.income_statement(period_start=period, period_end=period)
        balance_sheet = reports.balance_sheet(as_of_period=period)
        cash_flow = reports.cash_flow(period_start=period, period_end=period)

        return {
            "period": period,
            "trial_balance": {
                "is_balanced": trial_balance.is_balanced,
                "grand_total_dr": trial_balance.grand_total_dr,
                "grand_total_cr": trial_balance.grand_total_cr,
                "line_count": len(trial_balance.lines),
                "top_lines": _top_statement_lines(
                    [
                        {
                            "account_code": line.account_code,
                            "account_name": line.account_name,
                            "account_type": line.account_type,
                            "amount": line.net,
                        }
                        for line in trial_balance.lines
                    ],
                    limit=limit,
                ),
            },
            "income_statement": {
                "total_revenue": income_statement.total_revenue,
                "total_expenses": income_statement.total_expenses,
                "net_income": income_statement.net_income,
                "revenue_line_count": len(income_statement.revenue_lines),
                "expense_line_count": len(income_statement.expense_lines),
                "top_revenue_lines": _top_statement_lines(
                    [line.model_dump(mode="json") for line in income_statement.revenue_lines],
                    limit=limit,
                ),
                "top_expense_lines": _top_statement_lines(
                    [line.model_dump(mode="json") for line in income_statement.expense_lines],
                    limit=limit,
                ),
            },
            "balance_sheet": {
                "total_assets": balance_sheet.total_assets,
                "total_liabilities": balance_sheet.total_liabilities,
                "total_equity": balance_sheet.total_equity,
                "liabilities_and_equity": balance_sheet.liabilities_and_equity,
                "is_balanced": balance_sheet.is_balanced,
            },
            "cash_flow": {
                "net_cash_from_operating": cash_flow.net_cash_from_operating,
                "net_cash_from_investing": cash_flow.net_cash_from_investing,
                "net_cash_from_financing": cash_flow.net_cash_from_financing,
                "net_change_in_cash": cash_flow.net_change_in_cash,
                "beginning_cash": cash_flow.beginning_cash,
                "ending_cash": cash_flow.ending_cash,
            },
        }

    def _journal_summary(self, period: str, *, limit: int) -> dict[str, Any]:
        rows = (
            self.db.table("journal_entries")
            .select(
                "id,entry_number,description,entry_date,period,reference_type,"
                "reference_id,posted_at,created_at"
            )
            .eq("tenant_id", self.tenant_id)
            .eq("period", period)
            .order("entry_date", desc=True)
            .limit(max(limit, 25))
            .execute()
            .data
            or []
        )
        journals = [_safe_journal(row) for row in rows]
        draft_journals = [row for row in journals if not row["posted"]]
        return {
            "period": period,
            "total_count": len(journals),
            "posted_count": sum(1 for row in journals if row["posted"]),
            "draft_count": len(draft_journals),
            "recent_journals": journals[:limit],
            "draft_journals": draft_journals[:limit],
            "response_summary": (
                f"{len(draft_journals)} draft journal(s) and "
                f"{sum(1 for row in journals if row['posted'])} posted journal(s) for {period}."
            ),
        }

    def _close_tasks(self, period: str) -> list[dict[str, Any]]:
        return (
            self.db.table("accounting_close_tasks")
            .select("id,code,title,status,owner_role,due_date,order_index")
            .eq("tenant_id", self.tenant_id)
            .eq("period", period)
            .is_("deleted_at", "null")
            .order("order_index")
            .execute()
            .data
            or []
        )

    def _working_capital_movement(
        self,
        *,
        current_package: dict[str, Any],
        comparison_package: dict[str, Any],
        current_period: str,
        comparison_period: str,
    ) -> dict[str, object]:
        current = current_package.get("working_capital")
        comparison = comparison_package.get("working_capital")
        current_wc = current if isinstance(current, dict) else {}
        comparison_wc = comparison if isinstance(comparison, dict) else {}
        current_ar_activity = self._period_document_total(
            "invoices",
            period=current_period,
            statuses=["approved", "sent", "paid", "overdue"],
        )
        comparison_ar_activity = self._period_document_total(
            "invoices",
            period=comparison_period,
            statuses=["approved", "sent", "paid", "overdue"],
        )
        current_ap_activity = self._period_document_total(
            "bills",
            period=current_period,
            statuses=["approved", "partially_paid", "paid"],
        )
        comparison_ap_activity = self._period_document_total(
            "bills",
            period=comparison_period,
            statuses=["approved", "partially_paid", "paid"],
        )
        return {
            "current_period": current_period,
            "comparison_period": comparison_period,
            "period_ar_activity": _movement(
                current_ar_activity,
                comparison_ar_activity,
            ),
            "period_ap_activity": _movement(
                current_ap_activity,
                comparison_ap_activity,
            ),
            "ar_open_total": _movement(
                current_wc.get("ar_open_total"),
                comparison_wc.get("ar_open_total"),
            ),
            "ap_open_total": _movement(
                current_wc.get("ap_open_total"),
                comparison_wc.get("ap_open_total"),
            ),
            "wip_total": _movement(current_wc.get("wip_total"), comparison_wc.get("wip_total")),
            "ar_aging": current_package.get("ar_aging") or {},
            "ap_aging": current_package.get("ap_aging") or {},
            "top_wip_projects": _top_wip_projects(current_package.get("wip")),
        }

    def _period_document_total(
        self,
        table_name: str,
        *,
        period: str,
        statuses: list[str],
    ) -> Decimal:
        bounds = period_bounds(period)
        rows = (
            self.db.table(table_name)
            .select("total,status,issue_date")
            .eq("tenant_id", self.tenant_id)
            .in_("status", statuses)
            .gte("issue_date", bounds.start)
            .lte("issue_date", bounds.end)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        return sum((_decimal(row.get("total")) for row in rows), Decimal("0"))

    def _project_margin_highlights(
        self,
        reports: ReportsService,
        *,
        period_start: str,
        period_end: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        rows = reports.project_pnl(period_start=period_start, period_end=period_end)
        safe_rows = [
            {
                "project_id": str(row.get("project_id") or ""),
                "project_name": str(row.get("project_name") or "Unnamed project"),
                "currency": str(row.get("currency") or "USD"),
                "revenue": _money(row.get("revenue")),
                "direct_cost": _money(row.get("direct_cost")),
                "gross_margin": _money(row.get("gross_margin")),
                "gross_margin_pct": float(row.get("gross_margin_pct") or 0.0),
                "risk_level": _margin_risk(row),
            }
            for row in rows
        ]
        return sorted(
            safe_rows,
            key=lambda row: (
                _margin_risk_rank(str(row["risk_level"])),
                float(row["gross_margin_pct"]),
                str(row["project_name"]),
            ),
        )[:limit]

    def _utilization_highlights(
        self,
        reports: ReportsService,
        *,
        period_start: str,
        period_end: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        rows = reports.utilization(period_start=period_start, period_end=period_end)
        employee_names = self._employee_names_by_id(
            [str(row.get("employee_id") or "") for row in rows if row.get("employee_id")]
        )
        safe_rows = [
            {
                "employee_id": str(row.get("employee_id") or ""),
                "employee_name": employee_names.get(str(row.get("employee_id") or "")),
                "total_hours": _money(row.get("total_hours")),
                "billable_hours": _money(row.get("billable_hours")),
                "utilization_pct": float(row.get("utilization_pct") or 0.0),
                "risk_level": _utilization_risk(row),
            }
            for row in rows
        ]
        return sorted(
            safe_rows,
            key=lambda row: (
                _utilization_risk_rank(str(row["risk_level"])),
                float(row["utilization_pct"]),
                str(row["employee_id"]),
            ),
        )[:limit]

    def _employee_names_by_id(self, employee_ids: list[str]) -> dict[str, str]:
        ids = [value for value in employee_ids if value]
        if not ids:
            return {}
        rows = (
            self.db.table("employees")
            .select("id,first_name,last_name")
            .eq("tenant_id", self.tenant_id)
            .in_("id", ids)
            .execute()
            .data
            or []
        )
        return {
            str(row["id"]): " ".join(
                part
                for part in [str(row.get("first_name") or ""), str(row.get("last_name") or "")]
                if part
            )
            or str(row["id"])
            for row in rows
        }


def normalise_period(value: str | None) -> str:
    """Normalize YYYY-MM, YYYY-MM-DD, Month YYYY, and Mon YYYY to YYYY-MM."""
    if value is None:
        raise ValueError("period is required")
    text = str(value).strip()
    if _PERIOD_RE.match(text):
        return text
    if _DATE_RE.match(text):
        return text[:7]
    for fmt in ("%B %Y", "%b %Y"):
        try:
            return datetime.datetime.strptime(text, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    raise ValueError("period must be formatted YYYY-MM, YYYY-MM-DD, or Month YYYY")


def _safe_close_status(value: object) -> dict[str, Any]:
    close_status = value if isinstance(value, dict) else {}
    checklist = (
        close_status.get("checklist") if isinstance(close_status.get("checklist"), list) else []
    )
    return {
        "period": close_status.get("period"),
        "status": close_status.get("status", "unknown"),
        "locked": bool(close_status.get("locked")),
        "locked_at": close_status.get("locked_at"),
        "ready_to_lock": bool(close_status.get("ready_to_lock")),
        "lock_blockers": [
            str(item) for item in close_status.get("lock_blockers", []) if item is not None
        ]
        if isinstance(close_status.get("lock_blockers"), list)
        else [],
        "checklist": [_safe_checklist_item(item) for item in checklist],
        "pending_reviews": _safe_pending_reviews(close_status.get("pending_reviews")),
        "incomplete_tasks": _safe_incomplete_tasks(close_status.get("incomplete_tasks")),
        "unposted_journals": _safe_unposted_journals(close_status.get("unposted_journals")),
        "subledger_findings": _safe_findings(close_status.get("findings")),
        "override_count": len(close_status.get("overrides", []))
        if isinstance(close_status.get("overrides"), list)
        else 0,
    }


def _safe_checklist_item(item: object) -> dict[str, object]:
    row = item if isinstance(item, dict) else {}
    return {
        "code": str(row.get("code") or "unknown"),
        "label": str(row.get("label") or row.get("code") or "Unknown"),
        "status": str(row.get("status") or "unknown"),
        "blocking": bool(row.get("blocking")),
        "summary": str(row.get("summary") or ""),
        "count": int(row.get("count") or 0),
        "overridden": bool(row.get("overridden")),
    }


def _safe_pending_reviews(value: object) -> list[dict[str, object]]:
    rows = value if isinstance(value, list) else []
    return [
        {
            "id": str(row.get("id") or ""),
            "agent_name": str(row.get("agent_name") or "unknown"),
            "action_type": str(row.get("action_type") or "unknown"),
            "status": str(row.get("status") or "pending"),
            "summary": str(row.get("summary") or ""),
        }
        for row in rows
        if isinstance(row, dict)
    ][:10]


def _safe_incomplete_tasks(value: object) -> list[dict[str, object]]:
    rows = value if isinstance(value, list) else []
    return [
        {
            "id": str(row.get("id") or ""),
            "code": str(row.get("code") or ""),
            "title": str(row.get("title") or row.get("code") or ""),
            "status": str(row.get("status") or "open"),
        }
        for row in rows
        if isinstance(row, dict)
    ][:10]


def _safe_unposted_journals(value: object) -> list[dict[str, object]]:
    rows = value if isinstance(value, list) else []
    return [
        {
            "id": str(row.get("id") or ""),
            "entry_number": str(row.get("entry_number") or row.get("id") or ""),
            "description": str(row.get("description") or ""),
            "entry_date": str(row.get("entry_date") or ""),
            "reference_type": str(row.get("reference_type") or "manual"),
        }
        for row in rows
        if isinstance(row, dict)
    ][:10]


def _safe_findings(value: object) -> list[dict[str, object]]:
    rows = value if isinstance(value, list) else []
    return [
        {
            "code": str(row.get("code") or ""),
            "source_table": str(row.get("source_table") or ""),
            "source_id": str(row.get("source_id") or ""),
            "source_number": row.get("source_number"),
            "reason": str(row.get("reason") or ""),
            "expected_reference_type": str(row.get("expected_reference_type") or ""),
        }
        for row in rows
        if isinstance(row, dict)
    ][:25]


def _close_task_state(
    close_tasks: list[dict[str, Any]],
    close_status: dict[str, Any],
) -> dict[str, object]:
    if not close_tasks:
        return {
            "status": "not_bootstrapped",
            "task_count": 0,
            "incomplete_task_count": len(close_status.get("incomplete_tasks", [])),
            "message": "No close task checklist has been bootstrapped for this period.",
        }
    incomplete = [
        row for row in close_tasks if str(row.get("status") or "open") not in {"done", "waived"}
    ]
    return {
        "status": "incomplete" if incomplete else "complete",
        "task_count": len(close_tasks),
        "incomplete_task_count": len(incomplete),
        "owner_roles": sorted(
            {
                str(row.get("owner_role") or "finance_manager")
                for row in close_tasks
                if str(row.get("status") or "open") not in {"done", "waived"}
            }
        ),
        "owner_summary": "Each close task includes an owner_role; incomplete tasks must be resolved by the named owner role.",
        "tasks": [
            {
                "id": str(row.get("id") or ""),
                "code": str(row.get("code") or ""),
                "title": str(row.get("title") or row.get("code") or ""),
                "status": str(row.get("status") or "open"),
                "owner_role": str(row.get("owner_role") or "finance_manager"),
                "due_date": row.get("due_date"),
            }
            for row in close_tasks[:10]
        ],
    }


def _close_blockers(
    *,
    close_status: dict[str, Any],
    close_task_state: dict[str, object],
    draft_journals: list[dict[str, object]],
) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    for item in close_status.get("checklist", []):
        if not isinstance(item, dict):
            continue
        if item.get("status") in {"complete"} and not item.get("blocking"):
            continue
        blockers.append(
            {
                "code": item.get("code"),
                "label": item.get("label"),
                "status": item.get("status"),
                "blocking": item.get("blocking"),
                "summary": item.get("summary"),
                "count": item.get("count"),
                "source": "close_status.checklist",
            }
        )
    if close_task_state.get("status") == "not_bootstrapped":
        blockers.append(
            {
                "code": "close_tasks_not_bootstrapped",
                "label": "Close tasks",
                "status": "missing",
                "blocking": True,
                "summary": close_task_state.get("message"),
                "count": 0,
                "source": "accounting_close_tasks",
            }
        )
    if draft_journals and not any(item.get("code") == "unposted_journals" for item in blockers):
        blockers.append(
            {
                "code": "unposted_journals",
                "label": "Unposted journals",
                "status": "blocked",
                "blocking": True,
                "summary": f"{len(draft_journals)} draft journal(s) remain unposted.",
                "count": len(draft_journals),
                "source": "journal_entries",
            }
        )
    return blockers


def _statement_variances(
    *,
    current: dict[str, Any],
    comparison: dict[str, Any],
    current_period: str,
    comparison_period: str,
) -> list[dict[str, object]]:
    current_is = current.get("income_statement", {})
    comparison_is = comparison.get("income_statement", {})
    current_cf = current.get("cash_flow", {})
    comparison_cf = comparison.get("cash_flow", {})
    current_bs = current.get("balance_sheet", {})
    comparison_bs = comparison.get("balance_sheet", {})
    metrics = [
        ("revenue", "Revenue", current_is.get("total_revenue"), comparison_is.get("total_revenue")),
        (
            "expenses",
            "Expenses",
            current_is.get("total_expenses"),
            comparison_is.get("total_expenses"),
        ),
        ("net_income", "Net income", current_is.get("net_income"), comparison_is.get("net_income")),
        (
            "net_cash_change",
            "Net cash change",
            current_cf.get("net_change_in_cash"),
            comparison_cf.get("net_change_in_cash"),
        ),
        (
            "total_assets",
            "Total assets",
            current_bs.get("total_assets"),
            comparison_bs.get("total_assets"),
        ),
    ]
    return [
        _variance_row(
            code=code,
            label=label,
            current=current_value,
            comparison=comparison_value,
            current_period=current_period,
            comparison_period=comparison_period,
        )
        for code, label, current_value, comparison_value in metrics
    ]


def _variance_row(
    *,
    code: str,
    label: str,
    current: object,
    comparison: object,
    current_period: str,
    comparison_period: str,
) -> dict[str, object]:
    current_amount = _decimal(current)
    comparison_amount = _decimal(comparison)
    delta = current_amount - comparison_amount
    delta_pct = None
    if comparison_amount != Decimal("0"):
        delta_pct = round(float(delta / abs(comparison_amount) * 100), 1)
    return {
        "code": code,
        "label": label,
        "current": serialise_money(current_amount) or "0.00",
        "comparison": serialise_money(comparison_amount) or "0.00",
        "delta": serialise_money(delta) or "0.00",
        "delta_pct": delta_pct,
        "severity": "watch" if delta_pct is not None and abs(delta_pct) >= 20 else "info",
        "evidence": {
            "current_period": current_period,
            "comparison_period": comparison_period,
            "source": "financial_statement_summary",
        },
    }


def _movement(current: object, comparison: object) -> dict[str, object]:
    current_amount = _decimal(current)
    comparison_amount = _decimal(comparison)
    delta = current_amount - comparison_amount
    return {
        "current": serialise_money(current_amount) or "0.00",
        "comparison": serialise_money(comparison_amount) or "0.00",
        "delta": serialise_money(delta) or "0.00",
    }


def _top_wip_projects(value: object) -> list[dict[str, object]]:
    rows = value if isinstance(value, list) else []
    safe_rows = [
        {
            "project_id": str(row.get("project_id") or ""),
            "project_name": str(row.get("project_name") or "Unnamed project"),
            "wip_value": _money(row.get("wip_value")),
        }
        for row in rows
        if isinstance(row, dict)
    ]
    return sorted(
        safe_rows,
        key=lambda row: _decimal(row["wip_value"]),
        reverse=True,
    )[:5]


def _data_availability(
    *,
    current_package: dict[str, Any],
    current_statements: dict[str, Any],
    journal_summary: dict[str, Any],
    project_margin: list[dict[str, object]],
    utilization: list[dict[str, object]],
) -> dict[str, object]:
    gl_summary = current_package.get("gl_summary")
    gl = gl_summary if isinstance(gl_summary, dict) else {}
    journal_line_count = int(gl.get("journal_line_count") or 0)
    statement_line_count = int(current_statements.get("trial_balance", {}).get("line_count") or 0)
    activity_count = (
        journal_line_count
        + int(journal_summary.get("total_count") or 0)
        + len(project_margin)
        + len(utilization)
    )
    if activity_count == 0 and statement_line_count == 0:
        status = "no_activity"
    elif journal_line_count == 0 or statement_line_count == 0:
        status = "limited_activity"
    else:
        status = "available"
    return {
        "status": status,
        "message": _data_availability_message(status),
        "journal_line_count": journal_line_count,
        "trial_balance_line_count": statement_line_count,
        "project_margin_row_count": len(project_margin),
        "utilization_row_count": len(utilization),
    }


def _data_availability_message(status: str) -> str:
    if status == "no_activity":
        return "No posted GL, project margin, or utilization activity was found for this period."
    if status == "limited_activity":
        return "Some management-pack sections have limited source activity."
    return "Source data is available for the management pack."


def _safe_commentary(value: object) -> list[dict[str, object]]:
    rows = value if isinstance(value, list) else []
    return [
        {
            "code": str(row.get("code") or ""),
            "severity": str(row.get("severity") or "info"),
            "summary": str(row.get("summary") or ""),
            "metric": row.get("metric"),
            "evidence": row.get("evidence") if isinstance(row.get("evidence"), dict) else {},
        }
        for row in rows
        if isinstance(row, dict)
    ][:20]


def _recommended_next_actions(
    *,
    data_availability: dict[str, object],
    close_status: dict[str, Any],
    close_task_state: dict[str, object],
    journal_summary: dict[str, Any],
    project_margin: list[dict[str, object]],
    utilization: list[dict[str, object]],
) -> list[str]:
    actions: list[str] = []
    if data_availability.get("status") in _NO_ACTIVITY_STATUSES:
        actions.append("Review source activity before relying on the management pack.")
    if close_task_state.get("status") == "not_bootstrapped":
        actions.append("Bootstrap the close task checklist for the period.")
    if close_status.get("locked"):
        actions.append(
            "Period is locked; use the pack for review and create a controlled unlock request for changes."
        )
    elif close_status.get("ready_to_lock"):
        actions.append("Review the management pack and lock the period if approvals are complete.")
    else:
        actions.append("Resolve close blockers before locking the period.")
    if journal_summary.get("draft_count"):
        actions.append("Post, reject, or document draft journals before close.")
    if any(row.get("risk_level") == "high" for row in project_margin):
        actions.append("Review low-margin projects and explain margin drivers.")
    if any(row.get("risk_level") == "low_utilization" for row in utilization):
        actions.append("Review low-utilization staff before finalizing operating commentary.")
    return _dedupe(actions)


def _safe_journal(row: dict[str, Any]) -> dict[str, object]:
    return {
        "id": str(row.get("id") or ""),
        "entry_number": str(row.get("entry_number") or row.get("id") or ""),
        "description": str(row.get("description") or ""),
        "entry_date": str(row.get("entry_date") or ""),
        "period": str(row.get("period") or ""),
        "reference_type": str(row.get("reference_type") or "manual"),
        "reference_id": row.get("reference_id"),
        "posted": bool(row.get("posted_at")),
        "posted_at": row.get("posted_at"),
        "created_at": row.get("created_at"),
    }


def _top_statement_lines(lines: list[dict[str, Any]], *, limit: int) -> list[dict[str, object]]:
    safe_rows = [
        {
            "account_code": str(row.get("account_code") or ""),
            "account_name": str(row.get("account_name") or ""),
            "account_type": str(row.get("account_type") or ""),
            "amount": _money(row.get("amount")),
        }
        for row in lines
    ]
    return sorted(
        safe_rows,
        key=lambda row: abs(_decimal(row["amount"])),
        reverse=True,
    )[:limit]


def _margin_risk(row: dict[str, Any]) -> str:
    revenue = _decimal(row.get("revenue"))
    gross_margin = _decimal(row.get("gross_margin"))
    pct = float(row.get("gross_margin_pct") or 0.0)
    if revenue == Decimal("0"):
        return "no_revenue"
    if gross_margin < Decimal("0") or pct < 20:
        return "high"
    if pct < 40:
        return "watch"
    return "normal"


def _margin_risk_rank(value: str) -> int:
    return {"high": 0, "watch": 1, "no_revenue": 2, "normal": 3}.get(value, 4)


def _utilization_risk(row: dict[str, Any]) -> str:
    pct = float(row.get("utilization_pct") or 0.0)
    total_hours = _decimal(row.get("total_hours"))
    if total_hours == Decimal("0"):
        return "no_hours"
    if pct < 60:
        return "low_utilization"
    if pct > 95:
        return "over_utilized"
    return "normal"


def _utilization_risk_rank(value: str) -> int:
    return {"low_utilization": 0, "over_utilized": 1, "no_hours": 2, "normal": 3}.get(
        value,
        4,
    )


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: object) -> str:
    return serialise_money(_decimal(value)) or "0.00"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
