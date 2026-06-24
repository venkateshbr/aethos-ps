"""Composed period close package and deterministic variance commentary."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.domain.money import serialise_money
from app.services.close_status_service import CloseStatusService
from app.services.reports_service import ReportsService
from supabase import Client


@dataclass(frozen=True)
class PeriodBounds:
    period: str
    start: str
    end: str


@dataclass(frozen=True)
class PeriodGlSummary:
    period: str
    revenue: Decimal
    expenses: Decimal
    net_income: Decimal
    revenue_account_count: int
    expense_account_count: int
    journal_line_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "revenue": serialise_money(self.revenue),
            "expenses": serialise_money(self.expenses),
            "net_income": serialise_money(self.net_income),
            "revenue_account_count": self.revenue_account_count,
            "expense_account_count": self.expense_account_count,
            "journal_line_count": self.journal_line_count,
        }


class ClosePackageService:
    """Build a close-review package from existing reports and close status."""

    def __init__(
        self,
        db: Client,
        tenant_id: str,
        *,
        reports_service: ReportsService | None = None,
        close_status_service: CloseStatusService | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.reports = reports_service or ReportsService(db, tenant_id)
        self.close_status = close_status_service or CloseStatusService(db, tenant_id)

    def build_package(self, period: str) -> dict[str, object]:
        """Return a period close package suitable for review before lock."""
        bounds = period_bounds(period)
        previous_period = previous_period_for(period)
        current_gl = self._period_gl_summary(period)
        previous_gl = self._period_gl_summary(previous_period)
        close_status = self.close_status.get_status(period)
        trial_balance = self.reports.trial_balance(as_of_period=period)
        ar_aging = self.reports.ar_aging()
        ap_aging = self.reports.ap_aging()
        wip = self.reports.wip()
        service_line_margins = self.reports.margin_by_service_line(period)

        ar_total = _money_from_mapping(ar_aging, "total")
        ap_total = _money_from_mapping(ap_aging, "total")
        wip_total = _sum_money(wip, "wip_value")

        return {
            "period": period,
            "period_start": bounds.start,
            "period_end": bounds.end,
            "previous_period": previous_period,
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "close_status": close_status.as_dict(),
            "gl_summary": current_gl.as_dict(),
            "previous_gl_summary": previous_gl.as_dict(),
            "working_capital": {
                "ar_open_total": serialise_money(ar_total),
                "ap_open_total": serialise_money(ap_total),
                "wip_total": serialise_money(wip_total),
            },
            "trial_balance": trial_balance.model_dump(mode="json"),
            "ar_aging": ar_aging,
            "ap_aging": ap_aging,
            "wip": wip,
            "service_line_margins": service_line_margins,
            "variance_commentary": build_variance_commentary(
                period=period,
                previous_period=previous_period,
                current=current_gl,
                previous=previous_gl,
                close_status=close_status.as_dict(),
                ar_total=ar_total,
                ap_total=ap_total,
                wip_total=wip_total,
                service_line_margins=service_line_margins,
            ),
        }

    def _period_gl_summary(self, period: str) -> PeriodGlSummary:
        rows = (
            self.db.table("journal_lines")
            .select(
                "direction, base_amount, "
                "journal_entries!journal_entry_id(period, posted_at), "
                "accounts!account_id(code, account_type)"
            )
            .eq("tenant_id", self.tenant_id)
            .execute()
            .data
            or []
        )

        revenue = Decimal("0")
        expenses = Decimal("0")
        revenue_accounts: set[str] = set()
        expense_accounts: set[str] = set()
        journal_line_count = 0

        for row in rows:
            entry = row.get("journal_entries") or {}
            if isinstance(entry, list):
                entry = entry[0] if entry else {}
            if entry.get("period") != period or not entry.get("posted_at"):
                continue

            account = row.get("accounts") or {}
            if isinstance(account, list):
                account = account[0] if account else {}
            account_type = str(account.get("account_type") or "")
            if account_type not in {"revenue", "expense"}:
                continue

            amount = Decimal(str(row.get("base_amount") or "0"))
            direction = str(row.get("direction") or "DR")
            code = str(account.get("code") or "")
            journal_line_count += 1

            if account_type == "revenue":
                revenue_accounts.add(code)
                revenue += amount if direction == "CR" else -amount
            else:
                expense_accounts.add(code)
                expenses += amount if direction == "DR" else -amount

        return PeriodGlSummary(
            period=period,
            revenue=revenue,
            expenses=expenses,
            net_income=revenue - expenses,
            revenue_account_count=len(revenue_accounts),
            expense_account_count=len(expense_accounts),
            journal_line_count=journal_line_count,
        )


def build_variance_commentary(
    *,
    period: str,
    previous_period: str,
    current: PeriodGlSummary,
    previous: PeriodGlSummary,
    close_status: dict[str, Any],
    ar_total: Decimal,
    ap_total: Decimal,
    wip_total: Decimal,
    service_line_margins: list[dict],
) -> list[dict[str, object]]:
    """Create deterministic commentary from the close package numbers."""
    commentary = [
        _variance_comment(
            code="revenue_variance",
            label="Revenue",
            current=current.revenue,
            previous=previous.revenue,
            period=period,
            previous_period=previous_period,
        ),
        _variance_comment(
            code="expense_variance",
            label="Expenses",
            current=current.expenses,
            previous=previous.expenses,
            period=period,
            previous_period=previous_period,
        ),
        _variance_comment(
            code="net_income_variance",
            label="Net income",
            current=current.net_income,
            previous=previous.net_income,
            period=period,
            previous_period=previous_period,
        ),
        _margin_comment(current, previous, previous_period),
        _working_capital_comment(ar_total, ap_total, wip_total),
    ]

    if close_status.get("lock_blockers"):
        blockers = ", ".join(str(item) for item in close_status["lock_blockers"])
        commentary.insert(
            0,
            {
                "code": "close_blockers",
                "severity": "blocker",
                "summary": f"Close cannot lock until these blockers clear: {blockers}.",
                "metric": blockers,
            },
        )

    service_line_comment = _service_line_comment(service_line_margins)
    if service_line_comment is not None:
        commentary.append(service_line_comment)

    return commentary


def period_bounds(period: str) -> PeriodBounds:
    year, month = _period_parts(period)
    last_day = calendar.monthrange(year, month)[1]
    return PeriodBounds(
        period=period,
        start=f"{year:04d}-{month:02d}-01",
        end=f"{year:04d}-{month:02d}-{last_day:02d}",
    )


def previous_period_for(period: str) -> str:
    year, month = _period_parts(period)
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"


def _period_parts(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[5:7])


def _variance_comment(
    *,
    code: str,
    label: str,
    current: Decimal,
    previous: Decimal,
    period: str,
    previous_period: str,
) -> dict[str, object]:
    delta = current - previous
    delta_pct = _pct_change(delta, previous)
    direction = "increased" if delta >= Decimal("0") else "decreased"
    if previous == Decimal("0"):
        summary = (
            f"{label} is {serialise_money(current)} in {period}; "
            f"{previous_period} has no comparable amount."
        )
    else:
        summary = (
            f"{label} {direction} by {serialise_money(abs(delta))} "
            f"({delta_pct}%) versus {previous_period}."
        )

    return {
        "code": code,
        "severity": _variance_severity(delta_pct),
        "summary": summary,
        "current": serialise_money(current),
        "previous": serialise_money(previous),
        "delta": serialise_money(delta),
        "delta_pct": delta_pct,
    }


def _margin_comment(
    current: PeriodGlSummary,
    previous: PeriodGlSummary,
    previous_period: str,
) -> dict[str, object]:
    current_pct = _margin_pct(current)
    previous_pct = _margin_pct(previous)
    delta = round(current_pct - previous_pct, 1)
    direction = "up" if delta >= 0 else "down"
    return {
        "code": "margin_variance",
        "severity": "watch" if abs(delta) >= 10 else "info",
        "summary": (
            f"Net margin is {current_pct}% ({direction} {abs(delta)} pts "
            f"versus {previous_period})."
        ),
        "current_margin_pct": current_pct,
        "previous_margin_pct": previous_pct,
        "delta_points": delta,
    }


def _working_capital_comment(
    ar_total: Decimal,
    ap_total: Decimal,
    wip_total: Decimal,
) -> dict[str, object]:
    exposure = ar_total + wip_total - ap_total
    return {
        "code": "working_capital",
        "severity": "watch" if ar_total or ap_total or wip_total else "info",
        "summary": (
            f"Open AR is {serialise_money(ar_total)}, AP is "
            f"{serialise_money(ap_total)}, and WIP is {serialise_money(wip_total)}."
        ),
        "ar_open_total": serialise_money(ar_total),
        "ap_open_total": serialise_money(ap_total),
        "wip_total": serialise_money(wip_total),
        "net_exposure": serialise_money(exposure),
    }


def _service_line_comment(rows: list[dict]) -> dict[str, object] | None:
    if not rows:
        return None
    top = max(rows, key=lambda row: Decimal(str(row.get("revenue") or "0")))
    return {
        "code": "service_line_mix",
        "severity": "info",
        "summary": (
            f"{top.get('label', top.get('service_line', 'Service line'))} has the "
            f"highest service-line revenue at {top.get('revenue', '0.00')} "
            f"with {top.get('margin_pct', 0.0)}% margin."
        ),
        "service_line": top.get("service_line"),
        "revenue": top.get("revenue"),
        "margin_pct": top.get("margin_pct"),
    }


def _margin_pct(summary: PeriodGlSummary) -> float:
    if summary.revenue == Decimal("0"):
        return 0.0
    return round(float(summary.net_income / summary.revenue * 100), 1)


def _pct_change(delta: Decimal, previous: Decimal) -> float | None:
    if previous == Decimal("0"):
        return None
    return round(float(delta / abs(previous) * 100), 1)


def _variance_severity(delta_pct: float | None) -> str:
    if delta_pct is None:
        return "info"
    return "watch" if abs(delta_pct) >= 20 else "info"


def _money_from_mapping(values: dict, key: str) -> Decimal:
    return Decimal(str(values.get(key) or "0"))


def _sum_money(rows: list[dict], key: str) -> Decimal:
    return sum((Decimal(str(row.get(key) or "0")) for row in rows), Decimal("0"))
