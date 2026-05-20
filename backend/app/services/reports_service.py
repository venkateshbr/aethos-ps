"""Reports service — financial and operational reporting.

All monetary values use Decimal internally; serialised as strings in the
returned dicts so JSON consumers receive exact values without float drift.

Six report methods:
  1. ar_aging              — AR aging buckets (0-30 / 31-60 / 61-90 / 90+)
  2. ap_aging              — AP aging buckets
  3. project_pnl           — revenue vs cost per project
  4. utilization           — billable-hour utilisation per employee
  5. wip                   — unbilled hours x rate (Work In Progress)
  6. revenue_by_engagement — total invoiced per engagement in a period
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from supabase import Client

logger = logging.getLogger(__name__)


class ReportsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # 1. AR Aging
    # ------------------------------------------------------------------

    def ar_aging(self) -> dict:
        """Bucket outstanding invoices by days past due date."""
        today = date.today()
        invoices = (
            self.db.table("invoices")
            .select("id, total, currency, due_date, status")
            .eq("tenant_id", self.tenant_id)
            .in_("status", ["approved", "sent", "overdue"])
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )

        buckets: dict[str, Decimal] = {
            "0_30": Decimal("0"),
            "31_60": Decimal("0"),
            "61_90": Decimal("0"),
            "over_90": Decimal("0"),
            "total": Decimal("0"),
        }

        for inv in invoices:
            if not inv.get("due_date"):
                continue
            days = (today - date.fromisoformat(str(inv["due_date"]))).days
            amount = Decimal(str(inv.get("total", "0")))
            buckets["total"] += amount
            if days <= 30:
                buckets["0_30"] += amount
            elif days <= 60:
                buckets["31_60"] += amount
            elif days <= 90:
                buckets["61_90"] += amount
            else:
                buckets["over_90"] += amount

        return {k: str(v) for k, v in buckets.items()}

    # ------------------------------------------------------------------
    # 2. AP Aging
    # ------------------------------------------------------------------

    def ap_aging(self) -> dict:
        """Bucket outstanding bills by days past due date."""
        today = date.today()
        bills = (
            self.db.table("bills")
            .select("id, total, currency, due_date, status")
            .eq("tenant_id", self.tenant_id)
            .in_("status", ["approved", "partially_paid"])
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )

        buckets: dict[str, Decimal] = {
            "0_30": Decimal("0"),
            "31_60": Decimal("0"),
            "61_90": Decimal("0"),
            "over_90": Decimal("0"),
            "total": Decimal("0"),
        }

        for bill in bills:
            if not bill.get("due_date"):
                continue
            days = (today - date.fromisoformat(str(bill["due_date"]))).days
            amount = Decimal(str(bill.get("total", "0")))
            buckets["total"] += amount
            if days <= 30:
                buckets["0_30"] += amount
            elif days <= 60:
                buckets["31_60"] += amount
            elif days <= 90:
                buckets["61_90"] += amount
            else:
                buckets["over_90"] += amount

        return {k: str(v) for k, v in buckets.items()}

    # ------------------------------------------------------------------
    # 3. Project P&L
    # ------------------------------------------------------------------

    def project_pnl(
        self,
        project_id: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        """Revenue vs direct cost per project with gross margin."""
        q = (
            self.db.table("projects")
            .select("id, name, engagement_id, currency, budget")
            .eq("tenant_id", self.tenant_id)
        )
        if project_id:
            q = q.eq("id", project_id)
        projects = q.execute().data or []

        result: list[dict] = []
        for proj in projects:
            pid = proj["id"]
            eng_id = proj.get("engagement_id") or ""

            # Revenue: invoiced amounts for this project's engagement
            inv_q = (
                self.db.table("invoices")
                .select("total, currency")
                .eq("tenant_id", self.tenant_id)
                .eq("engagement_id", eng_id)
                .in_("status", ["approved", "sent", "paid"])
                .is_("deleted_at", "null")
            )
            if period_start:
                inv_q = inv_q.gte("issue_date", period_start)
            if period_end:
                inv_q = inv_q.lte("issue_date", period_end)
            revenue = sum(
                Decimal(str(i["total"])) for i in (inv_q.execute().data or [])
            )

            # Direct costs: project expenses
            exp_q = (
                self.db.table("project_expenses")
                .select("amount")
                .eq("tenant_id", self.tenant_id)
                .eq("project_id", pid)
                .is_("deleted_at", "null")
            )
            costs = sum(Decimal(str(e["amount"])) for e in (exp_q.execute().data or []))

            margin = revenue - costs
            margin_pct = float(margin / revenue * 100) if revenue > Decimal("0") else 0.0

            result.append(
                {
                    "project_id": pid,
                    "project_name": proj["name"],
                    "currency": proj.get("currency", "USD"),
                    "revenue": str(revenue),
                    "direct_cost": str(costs),
                    "gross_margin": str(margin),
                    "gross_margin_pct": round(margin_pct, 1),
                }
            )

        return result

    # ------------------------------------------------------------------
    # 4. Utilisation
    # ------------------------------------------------------------------

    def utilization(
        self,
        employee_id: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        """Billable-hour utilisation percentage per employee."""
        q = (
            self.db.table("time_entries")
            .select("employee_id, hours, billable")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
        )
        if employee_id:
            q = q.eq("employee_id", employee_id)
        if period_start:
            q = q.gte("date", period_start)
        if period_end:
            q = q.lte("date", period_end)
        entries = q.execute().data or []

        by_emp: dict[str, dict[str, Decimal]] = {}
        for e in entries:
            eid = e["employee_id"]
            if eid not in by_emp:
                by_emp[eid] = {"total": Decimal("0"), "billable": Decimal("0")}
            h = Decimal(str(e.get("hours", "0")))
            by_emp[eid]["total"] += h
            if e.get("billable"):
                by_emp[eid]["billable"] += h

        result: list[dict] = []
        for eid, data in by_emp.items():
            pct = (
                float(data["billable"] / data["total"] * 100)
                if data["total"] > Decimal("0")
                else 0.0
            )
            result.append(
                {
                    "employee_id": eid,
                    "total_hours": str(data["total"]),
                    "billable_hours": str(data["billable"]),
                    "utilization_pct": round(pct, 1),
                }
            )
        return result

    # ------------------------------------------------------------------
    # 5. Work In Progress (WIP)
    # ------------------------------------------------------------------

    def wip(self, engagement_id: str | None = None) -> list[dict]:
        """Unbilled effort x average rate per project."""
        q = (
            self.db.table("projects")
            .select("id, name, engagement_id, rate_card_id")
            .eq("tenant_id", self.tenant_id)
        )
        if engagement_id:
            q = q.eq("engagement_id", engagement_id)
        projects = q.execute().data or []

        result: list[dict] = []
        for proj in projects:
            entries = (
                self.db.table("time_entries")
                .select("hours")
                .eq("tenant_id", self.tenant_id)
                .eq("project_id", proj["id"])
                .eq("billing_status", "unbilled")
                .eq("billable", True)
                .is_("deleted_at", "null")
                .execute()
                .data
                or []
            )
            hours = sum(Decimal(str(e["hours"])) for e in entries)

            rate = Decimal("0")
            if proj.get("rate_card_id"):
                rc = (
                    self.db.table("rate_card_lines")
                    .select("rate")
                    .eq("rate_card_id", proj["rate_card_id"])
                    .limit(1)
                    .execute()
                    .data
                )
                if rc:
                    rate = Decimal(str(rc[0]["rate"]))

            value = (hours * rate).quantize(Decimal("0.01"))
            result.append(
                {
                    "project_id": proj["id"],
                    "project_name": proj["name"],
                    "unbilled_hours": str(hours),
                    "avg_rate": str(rate),
                    "wip_value": str(value),
                }
            )
        return result

    # ------------------------------------------------------------------
    # 6. Revenue by Engagement
    # ------------------------------------------------------------------

    def revenue_by_engagement(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        """Total invoiced amount per engagement in an optional date window."""
        q = (
            self.db.table("invoices")
            .select("engagement_id, total, currency, status, issue_date")
            .eq("tenant_id", self.tenant_id)
            .in_("status", ["approved", "sent", "paid"])
            .is_("deleted_at", "null")
        )
        if period_start:
            q = q.gte("issue_date", period_start)
        if period_end:
            q = q.lte("issue_date", period_end)
        invoices = q.execute().data or []

        by_eng: dict[str, Decimal] = {}
        for inv in invoices:
            eid = inv["engagement_id"]
            by_eng[eid] = by_eng.get(eid, Decimal("0")) + Decimal(str(inv.get("total", "0")))

        return [{"engagement_id": k, "total_invoiced": str(v)} for k, v in by_eng.items()]
