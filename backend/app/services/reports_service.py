"""Reports service — financial and operational reporting.

All monetary values use Decimal internally; serialised as strings in the
returned dicts so JSON consumers receive exact values without float drift.

Report methods:
  1. ar_aging              — AR aging buckets (0-30 / 31-60 / 61-90 / 90+)
  2. ap_aging              — AP aging buckets
  3. project_pnl           — revenue vs cost per project
  4. utilization           — billable-hour utilisation per employee
  5. wip                   — unbilled hours x rate (Work In Progress)
  6. revenue_by_engagement — total invoiced per engagement in a period
  7. trial_balance         — DR/CR totals per account, optionally cumulative to period
  8. revenue_by_service_line
  9. cost_by_service_line
  10. margin_by_service_line
  11. client_profitability
  12. client_group_profitability
  13. segment_profitability
  14. practice_dashboard
  15. project_health_scores
  16. capacity_planning
  17. pricing_staffing_recommendations
  18. scope_change_advisor
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.domain.money import serialise_money
from app.models.reports import TrialBalanceLine, TrialBalanceReport
from supabase import Client

logger = logging.getLogger(__name__)

_FINAL_INVOICE_STATUSES = ["approved", "sent", "paid", "overdue"]
_RETAINER_BILLING_MODELS = {"retainer", "retainer_draw"}
_DEFAULT_WEEKLY_CAPACITY_HOURS = Decimal("40")
_TARGET_GROSS_MARGIN_PCT = Decimal("40")
_SCOPE_CHANGE_DRIVER_CODES = {"budget_hours_burn", "cap_drawdown", "scope_creep"}
_SERVICE_LINE_LABELS = {
    "accounting": "Accounting",
    "tax": "Tax",
    "cosec": "Company Secretarial",
    "payroll": "Payroll",
    "advisory": "Advisory",
    "other": "Other",
    "unclassified": "Unclassified",
}


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
        project_ids = [str(project["id"]) for project in projects]
        engagement_ids = {
            str(project["engagement_id"])
            for project in projects
            if project.get("engagement_id")
        }

        revenue_by_engagement: dict[str, Decimal] = {}
        if engagement_ids:
            inv_q = (
                self.db.table("invoices")
                .select("engagement_id, total, currency, issue_date")
                .eq("tenant_id", self.tenant_id)
                .in_("engagement_id", list(engagement_ids))
                .in_("status", ["approved", "sent", "paid"])
                .is_("deleted_at", "null")
            )
            if period_start:
                inv_q = inv_q.gte("issue_date", period_start)
            if period_end:
                inv_q = inv_q.lte("issue_date", period_end)
            for invoice in inv_q.execute().data or []:
                engagement_id = str(invoice.get("engagement_id") or "")
                revenue_by_engagement[engagement_id] = revenue_by_engagement.get(
                    engagement_id, Decimal("0")
                ) + (Decimal(str(invoice.get("total", "0"))))

        costs_by_project: dict[str, Decimal] = {}
        if project_ids:
            exp_q = (
                self.db.table("project_expenses")
                .select("project_id, amount, base_amount")
                .eq("tenant_id", self.tenant_id)
                .in_("project_id", project_ids)
                .is_("deleted_at", "null")
            )
            if period_start:
                exp_q = exp_q.gte("expense_date", period_start)
            if period_end:
                exp_q = exp_q.lte("expense_date", period_end)
            for expense in exp_q.execute().data or []:
                project_id_value = str(expense.get("project_id") or "")
                amount = (
                    _decimal(expense.get("base_amount"))
                    or _decimal(expense.get("amount"))
                    or Decimal("0")
                )
                costs_by_project[project_id_value] = (
                    costs_by_project.get(project_id_value, Decimal("0")) + amount
                )

        result: list[dict] = []
        for proj in projects:
            pid = proj["id"]
            eng_id = proj.get("engagement_id") or ""
            revenue = revenue_by_engagement.get(str(eng_id), Decimal("0"))
            costs = costs_by_project.get(str(pid), Decimal("0"))

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
        """Unbilled effort x average rate per project.

        Rate card lives on the engagement (``engagements.rate_card_id``), not
        on the project — there is no per-project rate-card override in the
        current schema. We join through the engagement to find the applicable
        rate card. See bug #99.
        """
        # Embed the parent engagement so we can pick up its rate_card_id in
        # the same round-trip. PostgREST returns embedded foreign tables as a
        # nested dict when the FK is many-to-one.
        q = (
            self.db.table("projects")
            .select("id, name, engagement_id, engagements(rate_card_id)")
            .eq("tenant_id", self.tenant_id)
        )
        if engagement_id:
            q = q.eq("engagement_id", engagement_id)
        projects = q.execute().data or []
        project_ids = [str(project["id"]) for project in projects]

        hours_by_project: dict[str, Decimal] = {}
        if project_ids:
            entries = (
                self.db.table("time_entries")
                .select("project_id, hours")
                .eq("tenant_id", self.tenant_id)
                .in_("project_id", project_ids)
                .eq("billing_status", "unbilled")
                .eq("billable", True)
                .is_("deleted_at", "null")
                .execute()
                .data
                or []
            )
            for entry in entries:
                project_id_value = str(entry.get("project_id") or "")
                hours_by_project[project_id_value] = hours_by_project.get(
                    project_id_value, Decimal("0")
                ) + Decimal(str(entry.get("hours", "0")))

        rate_card_ids = {
            str(_embedded_one(project.get("engagements")).get("rate_card_id"))
            for project in projects
            if _embedded_one(project.get("engagements")).get("rate_card_id")
        }
        rate_cache: dict[str, Decimal] = {}
        if rate_card_ids:
            rate_rows = (
                self.db.table("rate_card_lines")
                .select("rate_card_id, rate")
                .eq("tenant_id", self.tenant_id)
                .in_("rate_card_id", list(rate_card_ids))
                .execute()
                .data
                or []
            )
            for row in rate_rows:
                rate_card_id = str(row.get("rate_card_id") or "")
                if rate_card_id not in rate_cache:
                    rate_cache[rate_card_id] = Decimal(str(row.get("rate") or "0"))

        result: list[dict] = []
        for proj in projects:
            # engagements may come back as a dict or a list depending on the
            # PostgREST cardinality inference; normalise.
            eng_embed = _embedded_one(proj.get("engagements"))
            rate_card_id = (eng_embed or {}).get("rate_card_id")

            hours = hours_by_project.get(str(proj["id"]), Decimal("0"))
            rate = rate_cache.get(str(rate_card_id), Decimal("0"))

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

        if not by_eng:
            return []

        eng_rows = (
            self.db.table("engagements")
            .select("id, name")
            .eq("tenant_id", self.tenant_id)
            .in_("id", list(by_eng.keys()))
            .execute()
            .data
            or []
        )
        name_map = {e["id"]: e["name"] for e in eng_rows}

        return [
            {
                "engagement_id": k,
                "engagement_name": name_map.get(k, k),
                "total_invoiced": str(v),
            }
            for k, v in by_eng.items()
        ]

    # ------------------------------------------------------------------
    # 7. Trial Balance
    # ------------------------------------------------------------------

    def trial_balance(self, as_of_period: str | None = None) -> TrialBalanceReport:
        """Aggregate posted journal_lines by account, returning DR/CR totals.

        Uses ``base_amount`` (tenant base currency) so multi-currency entries
        are always comparable on a single scale.

        If ``as_of_period`` is supplied (format ``YYYY-MM``) only journal
        entries whose ``period`` is <= that value are included — giving a
        cumulative-to-date view. If omitted, all posted entries are included.

        Accounts are sorted by ``code`` ascending.  Only accounts that have
        at least one journal line are returned (zero-balance accounts are
        omitted — they would add noise without information).

        Raises no exceptions on an empty tenant: returns an empty ``lines``
        list with ``is_balanced=True`` and zero grand totals.
        """
        # ------------------------------------------------------------------
        # Step 1 — fetch all journal_lines for this tenant joined with
        # journal_entries (for period filtering) and accounts (for metadata).
        # Supabase-py uses PostgREST foreign-key embedding.
        #
        # PostgREST embed: journal_lines has a FK to journal_entries
        # (journal_entry_id) and to accounts (account_id).  We embed both.
        # ------------------------------------------------------------------
        lines_q = (
            self.db.table("journal_lines")
            .select(
                "direction, base_amount, "
                "journal_entries!journal_entry_id(period, posted_at), "
                "accounts!account_id(code, name, account_type)"
            )
            .eq("tenant_id", self.tenant_id)
        )
        raw_lines: list[dict] = lines_q.execute().data or []

        # ------------------------------------------------------------------
        # Step 2 — Python-side aggregation (avoids complex GROUP BY via RPC
        # and keeps the service layer testable with MagicMock).
        # Filter to posted entries only (posted_at IS NOT NULL).
        # Optionally filter to period <= as_of_period.
        # ------------------------------------------------------------------
        # Per account accumulate DR and CR base amounts.
        # key: (code, name, account_type)  value: {"DR": Decimal, "CR": Decimal}
        agg: dict[tuple[str, str, str], dict[str, Decimal]] = {}

        for row in raw_lines:
            je = row.get("journal_entries") or {}
            # Skip unposted / draft entries
            if not je.get("posted_at"):
                continue

            period = je.get("period", "")
            if as_of_period and period > as_of_period:
                continue

            account = row.get("accounts") or {}
            code: str = account.get("code", "")
            name: str = account.get("name", "")
            acct_type: str = account.get("account_type", "")
            direction: str = row.get("direction", "DR")
            base_amt = Decimal(str(row.get("base_amount", "0")))

            key = (code, name, acct_type)
            if key not in agg:
                agg[key] = {"DR": Decimal("0"), "CR": Decimal("0")}
            agg[key][direction] += base_amt

        # ------------------------------------------------------------------
        # Step 3 — build sorted line list and compute grand totals.
        # ------------------------------------------------------------------
        tb_lines: list[TrialBalanceLine] = []
        grand_dr = Decimal("0")
        grand_cr = Decimal("0")

        for (code, name, acct_type), totals in sorted(agg.items(), key=lambda x: x[0][0]):
            total_dr = totals["DR"]
            total_cr = totals["CR"]
            net = total_dr - total_cr
            grand_dr += total_dr
            grand_cr += total_cr
            tb_lines.append(
                TrialBalanceLine(
                    account_code=code,
                    account_name=name,
                    account_type=acct_type,
                    total_dr=serialise_money(total_dr),  # type: ignore[arg-type]
                    total_cr=serialise_money(total_cr),  # type: ignore[arg-type]
                    net=serialise_money(net),  # type: ignore[arg-type]
                )
            )

        is_balanced = abs(grand_dr - grand_cr) <= Decimal("0.01")

        return TrialBalanceReport(
            as_of_period=as_of_period,
            lines=tb_lines,
            grand_total_dr=serialise_money(grand_dr),  # type: ignore[arg-type]
            grand_total_cr=serialise_money(grand_cr),  # type: ignore[arg-type]
            is_balanced=is_balanced,
            generated_at=datetime.now(tz=UTC),
        )

    # ------------------------------------------------------------------
    # 8. Revenue by Service Line
    # ------------------------------------------------------------------

    def revenue_by_service_line(self, period: str | None = None) -> list[dict]:
        """Revenue grouped by service line.

        Sources: invoice_lines joined to service_catalogue for the primary
        service_line.  Falls back to engagements.service_line for lines that
        have no catalogue entry attached.  Lines with no service_line on
        either path are bucketed as ``unclassified``.

        ``period`` is ``YYYY-MM``; when supplied only invoices whose
        ``issue_date`` falls in that month are included.

        Returns: [{service_line, label, total_revenue, pct}]
        All monetary amounts serialised as strings.
        """
        _SERVICE_LINE_LABELS = {
            "accounting": "Accounting",
            "tax": "Tax",
            "cosec": "Company Secretarial",
            "payroll": "Payroll",
            "advisory": "Advisory",
            "other": "Other",
            "unclassified": "Unclassified",
        }

        # Build date range from YYYY-MM
        date_start: str | None = None
        date_end: str | None = None
        if period:
            try:
                year, month = int(period[:4]), int(period[5:7])
                import calendar as _calendar
                last_day = _calendar.monthrange(year, month)[1]
                date_start = f"{year:04d}-{month:02d}-01"
                date_end = f"{year:04d}-{month:02d}-{last_day:02d}"
            except (ValueError, IndexError):
                pass  # ignore malformed period — treat as all-time

        # Fetch invoice_lines joined to invoices (for status + date) and
        # optionally to service_catalogue and engagements.
        # We fetch the raw rows and do grouping in Python (same pattern as
        # trial_balance, avoids complex PostgREST GROUP BY).
        inv_q = (
            self.db.table("invoice_lines")
            .select(
                "amount, "
                "service_catalogue_id, "
                "invoices!invoice_id(status, issue_date, engagement_id, deleted_at)"
            )
            .eq("tenant_id", self.tenant_id)
        )
        raw_lines: list[dict] = inv_q.execute().data or []

        # Gather all engagement_ids we need to resolve service_line from.
        engagement_ids_needed: set[str] = set()
        for line in raw_lines:
            inv = line.get("invoices") or {}
            if isinstance(inv, list):
                inv = inv[0] if inv else {}
            if not inv.get("engagement_id"):
                continue
            engagement_ids_needed.add(str(inv["engagement_id"]))

        # Fetch engagement service_lines in one round-trip.
        eng_service_line: dict[str, str] = {}
        if engagement_ids_needed:
            eng_rows = (
                self.db.table("engagements")
                .select("id, service_line")
                .eq("tenant_id", self.tenant_id)
                .in_("id", list(engagement_ids_needed))
                .execute()
                .data
                or []
            )
            eng_service_line = {
                str(e["id"]): str(e["service_line"])
                for e in eng_rows
                if e.get("service_line")
            }

        # Fetch service_catalogue service_lines in one round-trip.
        svc_ids_needed: set[str] = {
            str(ln["service_catalogue_id"])
            for ln in raw_lines
            if ln.get("service_catalogue_id")
        }
        svc_service_line: dict[str, str] = {}
        if svc_ids_needed:
            svc_rows = (
                self.db.table("service_catalogue")
                .select("id, service_line")
                .eq("tenant_id", self.tenant_id)
                .in_("id", list(svc_ids_needed))
                .execute()
                .data
                or []
            )
            svc_service_line = {str(s["id"]): str(s["service_line"]) for s in svc_rows}

        # Aggregate revenue by service_line.
        by_line: dict[str, Decimal] = {}
        for line in raw_lines:
            inv = line.get("invoices") or {}
            if isinstance(inv, list):
                inv = inv[0] if inv else {}

            # Skip voided / draft invoices and deleted invoices.
            if inv.get("deleted_at") or inv.get("status") in ("voided", "draft"):
                continue

            # Apply period filter.
            issue_date = str(inv.get("issue_date", "") or "")
            if date_start and issue_date < date_start:
                continue
            if date_end and issue_date > date_end:
                continue

            # Resolve service_line: catalogue > engagement > unclassified.
            svc_cat_id = str(line["service_catalogue_id"]) if line.get("service_catalogue_id") else None
            eng_id = str(inv.get("engagement_id")) if inv.get("engagement_id") else None
            svc_line = (
                svc_service_line.get(svc_cat_id)
                if svc_cat_id
                else None
            ) or (
                eng_service_line.get(eng_id)
                if eng_id
                else None
            ) or "unclassified"

            amount = Decimal(str(line.get("amount", "0")))
            by_line[svc_line] = by_line.get(svc_line, Decimal("0")) + amount

        grand_total = sum(by_line.values(), Decimal("0"))

        return [
            {
                "service_line": sl,
                "label": _SERVICE_LINE_LABELS.get(sl, sl.title()),
                "total_revenue": str(total.quantize(Decimal("0.01"))),
                "pct": round(float(total / grand_total * 100), 1) if grand_total else 0.0,
            }
            for sl, total in sorted(by_line.items())
        ]

    # ------------------------------------------------------------------
    # 9. Cost by Service Line
    # ------------------------------------------------------------------

    def cost_by_service_line(self, period: str | None = None) -> list[dict]:
        """Labour cost (hours x cost_rate) grouped by service_line.

        Service_line is resolved from engagements via projects → time_entries.
        cost_rate is taken from employees.cost_rate (the internal cost of the
        employee's time, not their bill rate).

        Returns: [{service_line, label, total_cost, total_hours}]
        """
        _SERVICE_LINE_LABELS = {
            "accounting": "Accounting",
            "tax": "Tax",
            "cosec": "Company Secretarial",
            "payroll": "Payroll",
            "advisory": "Advisory",
            "other": "Other",
            "unclassified": "Unclassified",
        }

        date_start: str | None = None
        date_end: str | None = None
        if period:
            try:
                year, month = int(period[:4]), int(period[5:7])
                import calendar as _calendar
                last_day = _calendar.monthrange(year, month)[1]
                date_start = f"{year:04d}-{month:02d}-01"
                date_end = f"{year:04d}-{month:02d}-{last_day:02d}"
            except (ValueError, IndexError):
                pass

        te_q = (
            self.db.table("time_entries")
            .select("hours, employee_id, project_id")
            .eq("tenant_id", self.tenant_id)
            .eq("billable", True)
            .is_("deleted_at", "null")
        )
        if date_start:
            te_q = te_q.gte("date", date_start)
        if date_end:
            te_q = te_q.lte("date", date_end)
        entries: list[dict] = te_q.execute().data or []

        if not entries:
            return []

        # Project → engagement → service_line map.
        project_ids = {str(e["project_id"]) for e in entries if e.get("project_id")}
        proj_to_line: dict[str, str] = {}
        if project_ids:
            proj_rows = (
                self.db.table("projects")
                .select("id, engagements!engagement_id(service_line)")
                .eq("tenant_id", self.tenant_id)
                .in_("id", list(project_ids))
                .execute()
                .data
                or []
            )
            for pr in proj_rows:
                eng_embed = pr.get("engagements")
                if isinstance(eng_embed, list):
                    eng_embed = eng_embed[0] if eng_embed else None
                sl = (eng_embed or {}).get("service_line") or "unclassified"
                proj_to_line[str(pr["id"])] = str(sl)

        # Employee → cost_rate map.
        emp_ids = {str(e["employee_id"]) for e in entries if e.get("employee_id")}
        emp_cost_rate: dict[str, Decimal] = {}
        if emp_ids:
            emp_rows = (
                self.db.table("employees")
                .select("id, cost_rate")
                .eq("tenant_id", self.tenant_id)
                .in_("id", list(emp_ids))
                .execute()
                .data
                or []
            )
            for em in emp_rows:
                if em.get("cost_rate") is not None:
                    emp_cost_rate[str(em["id"])] = Decimal(str(em["cost_rate"]))

        # Aggregate hours and cost by service_line.
        by_line_hours: dict[str, Decimal] = {}
        by_line_cost: dict[str, Decimal] = {}

        for e in entries:
            pid = str(e.get("project_id") or "")
            eid = str(e.get("employee_id") or "")
            sl = proj_to_line.get(pid, "unclassified")
            hours = Decimal(str(e.get("hours", "0")))
            rate = emp_cost_rate.get(eid, Decimal("0"))
            cost = (hours * rate).quantize(Decimal("0.01"))

            by_line_hours[sl] = by_line_hours.get(sl, Decimal("0")) + hours
            by_line_cost[sl] = by_line_cost.get(sl, Decimal("0")) + cost

        return [
            {
                "service_line": sl,
                "label": _SERVICE_LINE_LABELS.get(sl, sl.title()),
                "total_cost": str(by_line_cost.get(sl, Decimal("0")).quantize(Decimal("0.01"))),
                "total_hours": str(by_line_hours.get(sl, Decimal("0")).quantize(Decimal("0.01"))),
            }
            for sl in sorted(by_line_hours)
        ]

    # ------------------------------------------------------------------
    # 10. Margin by Service Line
    # ------------------------------------------------------------------

    def margin_by_service_line(self, period: str | None = None) -> list[dict]:
        """Gross margin by service line = revenue - labour cost.

        Combines revenue_by_service_line and cost_by_service_line.
        Returns: [{service_line, label, revenue, cost, gross_margin, margin_pct}]
        """
        rev_rows = {r["service_line"]: r for r in self.revenue_by_service_line(period)}
        cost_rows = {c["service_line"]: c for c in self.cost_by_service_line(period)}

        all_lines = sorted(set(rev_rows) | set(cost_rows))

        result: list[dict] = []
        for sl in all_lines:
            revenue = Decimal(rev_rows[sl]["total_revenue"]) if sl in rev_rows else Decimal("0")
            cost = Decimal(cost_rows[sl]["total_cost"]) if sl in cost_rows else Decimal("0")
            gross_margin = revenue - cost
            margin_pct = (
                round(float(gross_margin / revenue * 100), 1)
                if revenue > Decimal("0")
                else 0.0
            )
            label = rev_rows.get(sl, cost_rows.get(sl, {})).get("label", sl.title())
            result.append(
                {
                    "service_line": sl,
                    "label": label,
                    "revenue": str(revenue.quantize(Decimal("0.01"))),
                    "cost": str(cost.quantize(Decimal("0.01"))),
                    "gross_margin": str(gross_margin.quantize(Decimal("0.01"))),
                    "margin_pct": margin_pct,
                }
            )

        return result

    # ------------------------------------------------------------------
    # 11. Client Profitability
    # ------------------------------------------------------------------

    def client_profitability(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
        client_id: str | None = None,
        client_group_id: str | None = None,
    ) -> list[dict]:
        """Profitability by client using current transactional schema.

        Revenue comes from finalized invoices. Costs include labour cost
        (time-entry hours x employee cost_rate) and direct project expenses.
        Vendor AP is not allocated to clients in the current schema, so this
        report intentionally excludes generic bills until bill-line project or
        service-line coding exists.
        """
        client_ids_filter = (
            self._client_ids_for_client_group(client_group_id)
            if client_group_id
            else None
        )
        facts = self._profitability_facts(
            period_start=period_start,
            period_end=period_end,
            client_id=client_id,
            client_ids_filter=client_ids_filter,
        )
        return self._client_profitability_from_facts(facts)

    def _client_profitability_from_facts(self, facts: dict[str, object]) -> list[dict]:
        rows: list[dict] = []
        for client in facts["clients"].values():
            cid = str(client["id"])
            stats = facts["by_client"].get(cid, _profitability_stats())
            if _is_empty_profitability(stats):
                continue
            rows.append(
                _profitability_row(
                    {
                        "client_id": cid,
                        "client_name": client.get("name") or cid,
                        "client_kind": client.get("kind") or "customer",
                        "currency": _currency_label(stats),
                        "service_lines": sorted(stats["service_lines"]),
                    },
                    stats,
                )
            )
        return sorted(
            rows,
            key=lambda row: (
                Decimal(str(row["gross_margin"])),
                str(row["client_name"]),
            ),
        )

    # ------------------------------------------------------------------
    # 12. Client Group Profitability
    # ------------------------------------------------------------------

    def client_group_profitability(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
        client_group_id: str | None = None,
    ) -> list[dict]:
        """Profitability rollups for configured client groups."""
        groups_q = (
            self.db.table("client_groups")
            .select("id, name, group_type, primary_client_id, billing_client_id, currency, status")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
        )
        if client_group_id:
            groups_q = groups_q.eq("id", client_group_id)
        groups = groups_q.execute().data or []
        if not groups:
            return []

        group_ids = [str(group["id"]) for group in groups]
        members_by_group = self._client_group_members_by_group(group_ids)
        all_client_ids = {
            str(member["client_id"])
            for members in members_by_group.values()
            for member in members
            if member.get("client_id")
        }
        facts = self._profitability_facts(
            period_start=period_start,
            period_end=period_end,
            client_ids_filter=all_client_ids,
        )

        rows: list[dict] = []
        by_client = facts["by_client"]  # type: ignore[index]
        for group in groups:
            group_id = str(group["id"])
            members = members_by_group.get(group_id, [])
            stats = _profitability_stats()
            for member in members:
                member_stats = by_client.get(str(member["client_id"]))
                if member_stats:
                    _merge_profitability_stats(stats, member_stats)
            if _is_empty_profitability(stats):
                continue
            rows.append(
                _profitability_row(
                    {
                        "client_group_id": group_id,
                        "client_group_name": group.get("name") or group_id,
                        "group_type": group.get("group_type") or "other",
                        "primary_client_id": group.get("primary_client_id"),
                        "billing_client_id": group.get("billing_client_id"),
                        "group_status": group.get("status") or "active",
                        "currency": _currency_label(stats) or group.get("currency"),
                        "service_lines": sorted(stats["service_lines"]),
                        "member_count": len(members),
                        "members": [_client_group_member_summary(member) for member in members],
                    },
                    stats,
                )
            )

        return sorted(
            rows,
            key=lambda row: (
                Decimal(str(row["gross_margin"])),
                str(row["client_group_name"]),
            ),
        )

    # ------------------------------------------------------------------
    # 13. Segment Profitability
    # ------------------------------------------------------------------

    def segment_profitability(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
        group_by: str = "service_line",
    ) -> list[dict]:
        """Profitability grouped by service line or client kind.

        There is no client-segment or client-group table in the current schema.
        This method therefore exposes the two segment dimensions that are
        already data-backed: engagement service line and client kind.
        """
        facts = self._profitability_facts(
            period_start=period_start,
            period_end=period_end,
        )
        return self._segment_profitability_from_facts(facts, group_by=group_by)

    def _segment_profitability_from_facts(
        self,
        facts: dict[str, object],
        *,
        group_by: str = "service_line",
    ) -> list[dict]:
        segment_type = (
            "client_kind" if group_by == "client_kind" else "service_line"
        )
        by_segment: dict[str, dict] = {}

        for segment_key, stats in facts[f"by_{segment_type}"].items():
            if _is_empty_profitability(stats):
                continue
            label = (
                _SERVICE_LINE_LABELS.get(segment_key, segment_key.title())
                if segment_type == "service_line"
                else segment_key.replace("_", " ").title()
            )
            by_segment[segment_key] = _profitability_row(
                {
                    "segment_type": segment_type,
                    "segment_key": segment_key,
                    "segment_label": label,
                    "currency": _currency_label(stats),
                },
                stats,
            )

        return sorted(
            by_segment.values(),
            key=lambda row: (
                -Decimal(str(row["gross_margin"])),
                str(row["segment_label"]),
            ),
        )

    # ------------------------------------------------------------------
    # 13. Practice Dashboard
    # ------------------------------------------------------------------

    def practice_dashboard(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        """Partner/practice dashboard by current service-line dimensions.

        There is no partner ownership model yet, so this report uses the
        schema-backed practice dimension: ``engagements.service_line`` for
        financial/project views and ``employees.practice_area`` for capacity.
        """
        return self._practice_dashboard_from_components(
            profitability_rows=self.segment_profitability(
                period_start=period_start,
                period_end=period_end,
                group_by="service_line",
            ),
            project_rows=self.project_health_scores(
                period_start=period_start,
                period_end=period_end,
            ),
            capacity_rows=self.capacity_planning(
                period_start=period_start,
                period_end=period_end,
            ),
            period_start=period_start,
            period_end=period_end,
        )

    def _practice_dashboard_from_components(
        self,
        *,
        profitability_rows: list[dict],
        project_rows: list[dict],
        capacity_rows: list[dict],
        period_start: str | None,
        period_end: str | None,
    ) -> list[dict]:
        practices: dict[str, dict] = {}

        for profitability in profitability_rows:
            practice = _practice_stats(str(profitability["segment_key"]))
            practice.update(
                {
                    "revenue": profitability["revenue"],
                    "labor_cost": profitability["labor_cost"],
                    "expense_cost": profitability["expense_cost"],
                    "total_cost": profitability["total_cost"],
                    "gross_margin": profitability["gross_margin"],
                    "gross_margin_pct": profitability["gross_margin_pct"],
                    "profitability_status": profitability["profitability_status"],
                    "financial_recommended_action": profitability["recommended_action"],
                    "client_count": profitability["client_count"],
                    "engagement_count": profitability["engagement_count"],
                    "project_count": profitability["project_count"],
                    "invoice_count": profitability["invoice_count"],
                }
            )
            practices[practice["practice_key"]] = practice

        for project in project_rows:
            key = str(project.get("service_line") or "unclassified")
            practice = practices.setdefault(key, _practice_stats(key))
            practice["active_project_count"] += 1
            practice["project_health_score_total"] += Decimal(
                str(project.get("health_score") or "0")
            )
            risk_level = str(project.get("risk_level") or "healthy")
            practice["project_risk_counts"][risk_level] = (
                practice["project_risk_counts"].get(risk_level, 0) + 1
            )
            if risk_level in {"at_risk", "critical"}:
                practice["at_risk_project_count"] += 1
            if risk_level == "critical":
                practice["critical_project_count"] += 1
            for action in project.get("recommended_actions") or []:
                _append_unique(practice["recommended_actions"], str(action))

        for capacity in capacity_rows:
            key = str(capacity.get("practice_area") or "unclassified")
            practice = practices.setdefault(key, _practice_stats(key))
            practice["employee_count"] += 1
            practice["capacity_hours"] += _decimal(capacity.get("capacity_hours")) or Decimal("0")
            practice["logged_hours"] += _decimal(capacity.get("logged_hours")) or Decimal("0")
            practice["billable_hours"] += _decimal(capacity.get("billable_hours")) or Decimal("0")
            capacity_status = str(capacity.get("capacity_status") or "balanced")
            practice["capacity_status_counts"][capacity_status] = (
                practice["capacity_status_counts"].get(capacity_status, 0) + 1
            )
            if capacity_status in {"overallocated", "underutilized"}:
                _append_unique(
                    practice["recommended_actions"],
                    str(capacity.get("recommended_action") or ""),
                )

        return sorted(
            (
                _practice_dashboard_row(
                    practice,
                    period_start=period_start,
                    period_end=period_end,
                )
                for practice in practices.values()
            ),
            key=lambda row: (
                -int(row["critical_project_count"]),
                -int(row["at_risk_project_count"]),
                str(row["practice_label"]),
            ),
        )

    # ------------------------------------------------------------------
    # 14. Pricing & Staffing Recommendations
    # ------------------------------------------------------------------

    def pricing_staffing_recommendations(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        """Deterministic pricing and staffing recommendations.

        This composes existing profitability, project health, capacity, and
        practice dashboard reports. It intentionally returns evidence-backed
        recommendations only; no ML prediction or speculative backlog model is
        implied until allocation forecast tables exist.
        """
        recommendations: list[dict] = []
        profitability_facts = self._profitability_facts(
            period_start=period_start,
            period_end=period_end,
        )
        client_rows = self._client_profitability_from_facts(profitability_facts)
        profitability_rows = self._segment_profitability_from_facts(
            profitability_facts,
            group_by="service_line",
        )
        project_rows = self.project_health_scores(
            period_start=period_start,
            period_end=period_end,
        )
        capacity_rows = self.capacity_planning(
            period_start=period_start,
            period_end=period_end,
        )
        practice_rows = self._practice_dashboard_from_components(
            profitability_rows=profitability_rows,
            project_rows=project_rows,
            capacity_rows=capacity_rows,
            period_start=period_start,
            period_end=period_end,
        )
        recommendations.extend(
            self._client_pricing_recommendations(
                client_rows,
                period_start=period_start,
                period_end=period_end,
            )
        )
        recommendations.extend(
            self._project_pricing_recommendations(
                project_rows,
                period_start=period_start,
                period_end=period_end,
            )
        )
        recommendations.extend(
            self._staffing_recommendations(
                capacity_rows,
                period_start=period_start,
                period_end=period_end,
            )
        )
        recommendations.extend(
            self._practice_recommendations(
                practice_rows,
                period_start=period_start,
                period_end=period_end,
            )
        )

        return sorted(
            recommendations,
            key=lambda row: (
                _recommendation_priority_rank(str(row["priority"])),
                str(row["recommendation_type"]),
                str(row["entity_name"]),
            ),
        )

    def _client_pricing_recommendations(
        self,
        client_rows: list[dict],
        *,
        period_start: str | None,
        period_end: str | None,
    ) -> list[dict]:
        rows: list[dict] = []
        for client in client_rows:
            margin_pct = Decimal(str(client.get("gross_margin_pct") or "0"))
            if margin_pct >= Decimal("30"):
                continue
            revenue = _decimal(client.get("revenue")) or Decimal("0")
            total_cost = _decimal(client.get("total_cost")) or Decimal("0")
            labor_hours = _decimal(client.get("labor_hours")) or Decimal("0")
            pricing_gap = _target_margin_gap(revenue, total_cost)
            current_rate = _rate_per_hour(revenue, labor_hours)
            target_rate = _rate_per_hour(
                _target_revenue_for_margin(total_cost),
                labor_hours,
            )

            rows.append(
                _recommendation(
                    recommendation_id=f"pricing:client:{client['client_id']}",
                    recommendation_type="pricing",
                    priority="critical" if margin_pct < Decimal("20") else "high",
                    entity_type="client",
                    entity_id=str(client["client_id"]),
                    entity_name=str(client.get("client_name") or client["client_id"]),
                    service_line=", ".join(client.get("service_lines") or []) or None,
                    period_start=period_start,
                    period_end=period_end,
                    evidence=[
                        f"Gross margin is {margin_pct}% against a 30% watch threshold.",
                        (
                            f"Revenue {serialise_money(revenue) or '0.00'} vs total "
                            f"cost {serialise_money(total_cost) or '0.00'}."
                        ),
                    ],
                    metrics={
                        "revenue": serialise_money(revenue) or "0.00",
                        "total_cost": serialise_money(total_cost) or "0.00",
                        "gross_margin_pct": float(margin_pct),
                        "target_gross_margin_pct": float(_TARGET_GROSS_MARGIN_PCT),
                        "pricing_gap_to_target": serialise_money(pricing_gap) or "0.00",
                        "labor_hours": str(labor_hours.quantize(Decimal("0.01"))),
                        "current_effective_rate": (
                            serialise_money(current_rate) if current_rate is not None else None
                        ),
                        "target_effective_rate": (
                            serialise_money(target_rate) if target_rate is not None else None
                        ),
                        "required_rate_uplift_pct": _rate_uplift_pct(current_rate, target_rate),
                    },
                    recommended_action=(
                        "Reprice the client, narrow scope, or change staffing mix "
                        "before approving additional work."
                    ),
                )
            )
        return rows

    def _project_pricing_recommendations(
        self,
        project_rows: list[dict],
        *,
        period_start: str | None,
        period_end: str | None,
    ) -> list[dict]:
        rows: list[dict] = []
        pricing_driver_codes = {"low_margin", "cap_drawdown", "budget_hours_burn"}
        for project in project_rows:
            drivers = [
                driver
                for driver in project.get("drivers") or []
                if driver.get("code") in pricing_driver_codes
            ]
            if not drivers:
                continue
            priority = (
                "critical"
                if project.get("risk_level") == "critical"
                or any(driver.get("severity") == "critical" for driver in drivers)
                else "high"
            )
            rows.append(
                _recommendation(
                    recommendation_id=f"pricing:project:{project['project_id']}",
                    recommendation_type="pricing",
                    priority=priority,
                    entity_type="project",
                    entity_id=str(project["project_id"]),
                    entity_name=str(project.get("project_name") or project["project_id"]),
                    service_line=str(project.get("service_line") or "unclassified"),
                    period_start=period_start,
                    period_end=period_end,
                    evidence=[
                        str(driver.get("summary") or driver.get("label") or "")
                        for driver in drivers
                        if driver.get("summary") or driver.get("label")
                    ],
                    metrics={
                        "health_score": project.get("health_score"),
                        "risk_level": project.get("risk_level"),
                        "driver_codes": [driver.get("code") for driver in drivers],
                    },
                    recommended_action=(
                        "Review the project quote, cap, and staffing mix before "
                        "the next billing approval."
                    ),
                )
            )
        return rows

    def _staffing_recommendations(
        self,
        capacity_rows: list[dict],
        *,
        period_start: str | None,
        period_end: str | None,
    ) -> list[dict]:
        underutilized = [
            row for row in capacity_rows if row.get("capacity_status") == "underutilized"
        ]
        under_by_practice: dict[str, list[dict]] = {}
        for employee in underutilized:
            practice = str(employee.get("practice_area") or "unclassified")
            under_by_practice.setdefault(practice, []).append(employee)
        for employees in under_by_practice.values():
            employees.sort(
                key=lambda row: (
                    float(row.get("billable_utilization_pct") or 0),
                    str(row.get("employee_name") or ""),
                )
            )

        rows: list[dict] = []
        for employee in capacity_rows:
            status = str(employee.get("capacity_status") or "")
            if status == "overallocated":
                practice = str(employee.get("practice_area") or "unclassified")
                logged_hours = _decimal(employee.get("logged_hours")) or Decimal("0")
                capacity_hours = _decimal(employee.get("capacity_hours")) or Decimal("0")
                overload_hours = max(Decimal("0"), logged_hours - capacity_hours)
                candidates = [
                    candidate
                    for candidate in under_by_practice.get(practice, [])
                    if candidate.get("employee_id") != employee.get("employee_id")
                ][:3]
                rows.append(
                    _recommendation(
                        recommendation_id=f"staffing:employee:{employee['employee_id']}",
                        recommendation_type="staffing",
                        priority=(
                            "critical"
                            if float(employee.get("utilization_pct") or 0) >= 125
                            else "high"
                        ),
                        entity_type="employee",
                        entity_id=str(employee["employee_id"]),
                        entity_name=str(employee.get("employee_name") or employee["employee_id"]),
                        service_line=practice,
                        period_start=employee.get("period_start") or period_start,
                        period_end=employee.get("period_end") or period_end,
                        evidence=[
                            (
                                f"Utilization is {employee.get('utilization_pct')}% "
                                "against a 110% overallocated threshold."
                            ),
                            _candidate_evidence(candidates),
                        ],
                        metrics={
                            "capacity_hours": employee.get("capacity_hours"),
                            "logged_hours": employee.get("logged_hours"),
                            "billable_hours": employee.get("billable_hours"),
                            "overload_hours": str(overload_hours.quantize(Decimal("0.01"))),
                            "candidate_count": len(candidates),
                            "candidate_employee_ids": [
                                candidate.get("employee_id") for candidate in candidates
                            ],
                            "candidate_names": [
                                candidate.get("employee_name") for candidate in candidates
                            ],
                        },
                        recommended_action=(
                            "Reassign delivery work to same-practice available staff "
                            "or defer lower-priority work."
                        ),
                    )
                )
            elif status == "underutilized":
                utilization_pct = float(employee.get("utilization_pct") or 0)
                if utilization_pct > 50:
                    continue
                rows.append(
                    _recommendation(
                        recommendation_id=f"staffing:bench:{employee['employee_id']}",
                        recommendation_type="staffing",
                        priority="medium",
                        entity_type="employee",
                        entity_id=str(employee["employee_id"]),
                        entity_name=str(employee.get("employee_name") or employee["employee_id"]),
                        service_line=str(employee.get("practice_area") or "unclassified"),
                        period_start=employee.get("period_start") or period_start,
                        period_end=employee.get("period_end") or period_end,
                        evidence=[
                            (
                                f"Utilization is {employee.get('utilization_pct')}% "
                                "with available capacity this period."
                            )
                        ],
                        metrics={
                            "capacity_hours": employee.get("capacity_hours"),
                            "logged_hours": employee.get("logged_hours"),
                            "billable_hours": employee.get("billable_hours"),
                            "available_hours": _available_hours(employee),
                        },
                        recommended_action=(
                            "Review open work and assign additional billable tasks "
                            "where skills and client constraints fit."
                        ),
                    )
                )
        return rows

    def _practice_recommendations(
        self,
        practice_rows: list[dict],
        *,
        period_start: str | None,
        period_end: str | None,
    ) -> list[dict]:
        rows: list[dict] = []
        for practice in practice_rows:
            margin_pct = Decimal(str(practice.get("gross_margin_pct") or "0"))
            overallocated_count = int(
                (practice.get("capacity_status_counts") or {}).get("overallocated", 0)
            )
            critical_project_count = int(practice.get("critical_project_count") or 0)
            if margin_pct >= Decimal("30") and not (
                overallocated_count and critical_project_count
            ):
                continue
            rows.append(
                _recommendation(
                    recommendation_id=f"practice:{practice['practice_key']}",
                    recommendation_type="practice",
                    priority="critical" if critical_project_count else "high",
                    entity_type="practice",
                    entity_id=str(practice["practice_key"]),
                    entity_name=str(practice.get("practice_label") or practice["practice_key"]),
                    service_line=str(practice["practice_key"]),
                    period_start=period_start,
                    period_end=period_end,
                    evidence=[
                        f"Practice gross margin is {margin_pct}%.",
                        f"Critical projects: {critical_project_count}.",
                        f"Overallocated staff: {overallocated_count}.",
                    ],
                    metrics={
                        "gross_margin_pct": float(margin_pct),
                        "critical_project_count": critical_project_count,
                        "overallocated_employee_count": overallocated_count,
                        "avg_project_health_score": practice.get("avg_project_health_score"),
                        "billable_utilization_pct": practice.get("billable_utilization_pct"),
                    },
                    recommended_action=(
                        "Run a partner review covering pricing, delivery risk, "
                        "and staffing balance for this practice."
                    ),
                )
            )
        return rows

    # ------------------------------------------------------------------
    # 15. Scope-Change Advisor
    # ------------------------------------------------------------------

    def scope_change_advisor(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        """Scope-change recommendations using completed-project comparables."""
        health_rows = self.project_health_scores(
            period_start=period_start,
            period_end=period_end,
        )
        risky_projects = [
            row
            for row in health_rows
            if _scope_change_drivers(row.get("drivers") or [])
        ]
        if not risky_projects:
            return []

        project_ids = [str(row["project_id"]) for row in risky_projects]
        contexts = self._scope_project_contexts(project_ids)
        comparables = self._scope_comparable_project_facts()

        rows: list[dict] = []
        for project in risky_projects:
            project_id = str(project["project_id"])
            context = contexts.get(project_id, {})
            engagement = _embedded_one(context.get("engagements"))
            drivers = _scope_change_drivers(project.get("drivers") or [])
            comparable_projects = _select_scope_comparables(
                context=context,
                project=project,
                comparables=comparables,
            )
            fee, basis = _scope_fee_adjustment(project, comparable_projects)
            rows.append(
                {
                    "advisor_id": f"scope:{project_id}",
                    "project_id": project_id,
                    "project_name": project.get("project_name") or project_id,
                    "service_line": project.get("service_line") or "unclassified",
                    "billing_arrangement": engagement.get("billing_arrangement"),
                    "risk_level": project.get("risk_level"),
                    "health_score": project.get("health_score"),
                    "scope_signals": [driver.get("code") for driver in drivers],
                    "drivers": drivers,
                    "current_metrics": _scope_current_metrics(project),
                    "comparable_projects": comparable_projects,
                    "suggested_fee_adjustment": serialise_money(fee) or "0.00",
                    "suggested_fee_basis": basis,
                    "confidence": _scope_confidence(comparable_projects),
                    "recommended_action": _scope_recommended_action(drivers, fee),
                }
            )

        return sorted(
            rows,
            key=lambda row: (
                _recommendation_priority_rank(_scope_priority(str(row["risk_level"]))),
                -Decimal(str(row["suggested_fee_adjustment"])),
                str(row["project_name"]),
            ),
        )

    def _scope_project_contexts(self, project_ids: list[str]) -> dict[str, dict]:
        if not project_ids:
            return {}
        rows = (
            self.db.table("projects")
            .select(
                "id, name, budget_hours, currency, status, "
                "engagements!engagement_id("
                "id, name, billing_arrangement, total_value, service_line)"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("id", project_ids)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        project_id_set = set(project_ids)
        return {
            str(row["id"]): row
            for row in rows
            if str(row.get("id")) in project_id_set
        }

    def _scope_comparable_project_facts(self) -> list[dict]:
        projects = (
            self.db.table("projects")
            .select(
                "id, name, budget_hours, currency, status, "
                "engagements!engagement_id("
                "id, name, billing_arrangement, total_value, service_line)"
            )
            .eq("tenant_id", self.tenant_id)
            .eq("status", "completed")
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        completed = [
            project
            for project in projects
            if str(project.get("status") or "") == "completed"
        ]
        if not completed:
            return []

        project_ids = [str(project["id"]) for project in completed]
        time_by_project = self._time_entries_by_project(project_ids)
        pnl_by_project = {str(row["project_id"]): row for row in self.project_pnl()}

        facts: list[dict] = []
        for project in completed:
            project_id = str(project["id"])
            entries = time_by_project.get(project_id, [])
            logged_hours = sum(
                (_decimal(entry.get("hours")) or Decimal("0")) for entry in entries
            )
            billable_hours = sum(
                (_decimal(entry.get("hours")) or Decimal("0"))
                for entry in entries
                if entry.get("billable", True)
                and entry.get("billing_status") != "non_billable"
            )
            if logged_hours <= 0:
                continue
            pnl = pnl_by_project.get(project_id, {})
            revenue = _decimal(pnl.get("revenue")) or Decimal("0")
            if revenue <= 0:
                continue
            direct_cost = _decimal(pnl.get("direct_cost")) or Decimal("0")
            engagement = _embedded_one(project.get("engagements"))
            budget_hours = _decimal(project.get("budget_hours"))
            facts.append(
                {
                    "project_id": project_id,
                    "project_name": project.get("name") or project_id,
                    "service_line": engagement.get("service_line") or "unclassified",
                    "billing_arrangement": engagement.get("billing_arrangement"),
                    "currency": project.get("currency") or "USD",
                    "revenue": serialise_money(revenue) or "0.00",
                    "direct_cost": serialise_money(direct_cost) or "0.00",
                    "gross_margin_pct": pnl.get("gross_margin_pct") or 0.0,
                    "logged_hours": str(logged_hours.quantize(Decimal("0.01"))),
                    "billable_hours": str(billable_hours.quantize(Decimal("0.01"))),
                    "budget_hours": (
                        str(budget_hours.quantize(Decimal("0.01")))
                        if budget_hours is not None
                        else None
                    ),
                    "budget_overrun_pct": _scope_budget_overrun_pct(
                        logged_hours,
                        budget_hours,
                    ),
                    "effective_rate": (
                        serialise_money(_rate_per_hour(revenue, billable_hours))
                        if billable_hours > 0
                        else None
                    ),
                }
            )
        return facts

    def _profitability_facts(
        self,
        *,
        period_start: str | None = None,
        period_end: str | None = None,
        client_id: str | None = None,
        client_ids_filter: set[str] | None = None,
    ) -> dict[str, object]:
        if client_ids_filter is not None and not client_ids_filter:
            return _empty_profitability_facts()

        clients_q = (
            self.db.table("clients")
            .select("id, name, kind, currency")
            .eq("tenant_id", self.tenant_id)
            .in_("kind", ["customer", "both"])
            .is_("deleted_at", "null")
        )
        if client_id:
            clients_q = clients_q.eq("id", client_id)
        if client_ids_filter is not None:
            clients_q = clients_q.in_("id", sorted(client_ids_filter))
        clients = clients_q.execute().data or []
        clients_by_id = {str(client["id"]): client for client in clients}
        client_ids = set(clients_by_id)
        if not client_ids:
            return _empty_profitability_facts()

        engagements = (
            self.db.table("engagements")
            .select("id, client_id, service_line, currency")
            .eq("tenant_id", self.tenant_id)
            .in_("client_id", list(client_ids))
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        engagement_by_id = {
            str(engagement["id"]): engagement for engagement in engagements
        }
        engagement_ids = set(engagement_by_id)

        projects = []
        project_by_id: dict[str, dict] = {}
        if engagement_ids:
            projects = (
                self.db.table("projects")
                .select("id, engagement_id, currency")
                .eq("tenant_id", self.tenant_id)
                .in_("engagement_id", list(engagement_ids))
                .is_("deleted_at", "null")
                .execute()
                .data
                or []
            )
            project_by_id = {str(project["id"]): project for project in projects}

        facts: dict[str, object] = {
            "clients": clients_by_id,
            "by_client": {},
            "by_service_line": {},
            "by_client_kind": {},
        }

        for engagement in engagements:
            self._ensure_profitability_dimensions(
                facts=facts,
                client=clients_by_id.get(str(engagement["client_id"]), {}),
                engagement=engagement,
            )

        self._add_profitability_revenue(
            facts=facts,
            clients_by_id=clients_by_id,
            engagement_by_id=engagement_by_id,
            client_ids=client_ids,
            period_start=period_start,
            period_end=period_end,
        )
        self._add_profitability_labor(
            facts=facts,
            clients_by_id=clients_by_id,
            engagement_by_id=engagement_by_id,
            project_by_id=project_by_id,
            period_start=period_start,
            period_end=period_end,
        )
        self._add_profitability_expenses(
            facts=facts,
            clients_by_id=clients_by_id,
            engagement_by_id=engagement_by_id,
            project_by_id=project_by_id,
            period_start=period_start,
            period_end=period_end,
        )
        return facts

    def _client_ids_for_client_group(self, client_group_id: str) -> set[str]:
        rows = (
            self.db.table("client_group_members")
            .select("client_id")
            .eq("tenant_id", self.tenant_id)
            .eq("group_id", client_group_id)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        return {str(row["client_id"]) for row in rows if row.get("client_id")}

    def _client_group_members_by_group(self, group_ids: list[str]) -> dict[str, list[dict]]:
        if not group_ids:
            return {}
        rows = (
            self.db.table("client_group_members")
            .select("id, group_id, client_id, relationship_role, is_primary, clients!client_id(id, name, kind)")
            .eq("tenant_id", self.tenant_id)
            .in_("group_id", group_ids)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(str(row["group_id"]), []).append(row)
        for members in grouped.values():
            members.sort(
                key=lambda member: (
                    not bool(member.get("is_primary")),
                    _embedded_one(member.get("clients")).get("name") or "",
                )
            )
        return grouped

    def _ensure_profitability_dimensions(
        self,
        *,
        facts: dict[str, object],
        client: dict,
        engagement: dict,
    ) -> tuple[dict, dict, dict]:
        by_client = facts["by_client"]  # type: ignore[index]
        by_service_line = facts["by_service_line"]  # type: ignore[index]
        by_client_kind = facts["by_client_kind"]  # type: ignore[index]

        cid = str(client.get("id") or engagement.get("client_id") or "")
        service_line = str(engagement.get("service_line") or "unclassified")
        client_kind = str(client.get("kind") or "customer")

        client_stats = by_client.setdefault(cid, _profitability_stats())
        service_stats = by_service_line.setdefault(service_line, _profitability_stats())
        kind_stats = by_client_kind.setdefault(client_kind, _profitability_stats())

        for stats in (client_stats, service_stats, kind_stats):
            stats["client_ids"].add(cid)
            stats["engagement_ids"].add(str(engagement["id"]))
            stats["service_lines"].add(service_line)
            if engagement.get("currency"):
                stats["currencies"].add(str(engagement["currency"]))

        return client_stats, service_stats, kind_stats

    def _profitability_dimensions_for_engagement(
        self,
        *,
        facts: dict[str, object],
        clients_by_id: dict[str, dict],
        engagement: dict,
    ) -> tuple[dict, dict, dict]:
        client = clients_by_id.get(str(engagement.get("client_id")), {})
        return self._ensure_profitability_dimensions(
            facts=facts,
            client=client,
            engagement=engagement,
        )

    def _add_profitability_revenue(
        self,
        *,
        facts: dict[str, object],
        clients_by_id: dict[str, dict],
        engagement_by_id: dict[str, dict],
        client_ids: set[str],
        period_start: str | None,
        period_end: str | None,
    ) -> None:
        invoice_q = (
            self.db.table("invoices")
            .select("id, client_id, engagement_id, total, currency, issue_date")
            .eq("tenant_id", self.tenant_id)
            .in_("client_id", list(client_ids))
            .in_("status", _FINAL_INVOICE_STATUSES)
            .is_("deleted_at", "null")
        )
        if period_start:
            invoice_q = invoice_q.gte("issue_date", period_start)
        if period_end:
            invoice_q = invoice_q.lte("issue_date", period_end)
        invoices = invoice_q.execute().data or []

        for invoice in invoices:
            engagement = engagement_by_id.get(str(invoice.get("engagement_id")))
            if not engagement:
                continue
            amount = _decimal(invoice.get("total")) or Decimal("0")
            for stats in self._profitability_dimensions_for_engagement(
                facts=facts,
                clients_by_id=clients_by_id,
                engagement=engagement,
            ):
                stats["revenue"] += amount
                stats["invoice_ids"].add(str(invoice["id"]))
                if invoice.get("currency"):
                    stats["currencies"].add(str(invoice["currency"]))

    def _add_profitability_labor(
        self,
        *,
        facts: dict[str, object],
        clients_by_id: dict[str, dict],
        engagement_by_id: dict[str, dict],
        project_by_id: dict[str, dict],
        period_start: str | None,
        period_end: str | None,
    ) -> None:
        if not project_by_id:
            return
        entries_q = (
            self.db.table("time_entries")
            .select("project_id, employee_id, hours, date")
            .eq("tenant_id", self.tenant_id)
            .in_("project_id", list(project_by_id))
            .is_("deleted_at", "null")
        )
        if period_start:
            entries_q = entries_q.gte("date", period_start)
        if period_end:
            entries_q = entries_q.lte("date", period_end)
        entries = entries_q.execute().data or []
        if not entries:
            return

        employee_ids = {
            str(entry["employee_id"]) for entry in entries if entry.get("employee_id")
        }
        cost_rates: dict[str, Decimal] = {}
        if employee_ids:
            employees = (
                self.db.table("employees")
                .select("id, cost_rate")
                .eq("tenant_id", self.tenant_id)
                .in_("id", list(employee_ids))
                .execute()
                .data
                or []
            )
            cost_rates = {
                str(employee["id"]): _decimal(employee.get("cost_rate")) or Decimal("0")
                for employee in employees
            }

        for entry in entries:
            project = project_by_id.get(str(entry.get("project_id")))
            if not project:
                continue
            engagement = engagement_by_id.get(str(project.get("engagement_id")))
            if not engagement:
                continue
            hours = _decimal(entry.get("hours")) or Decimal("0")
            rate = cost_rates.get(str(entry.get("employee_id")), Decimal("0"))
            cost = (hours * rate).quantize(Decimal("0.01"))
            for stats in self._profitability_dimensions_for_engagement(
                facts=facts,
                clients_by_id=clients_by_id,
                engagement=engagement,
            ):
                stats["labor_cost"] += cost
                stats["labor_hours"] += hours
                stats["project_ids"].add(str(project["id"]))

    def _add_profitability_expenses(
        self,
        *,
        facts: dict[str, object],
        clients_by_id: dict[str, dict],
        engagement_by_id: dict[str, dict],
        project_by_id: dict[str, dict],
        period_start: str | None,
        period_end: str | None,
    ) -> None:
        if not project_by_id:
            return
        expenses_q = (
            self.db.table("project_expenses")
            .select("id, project_id, amount, base_amount, currency, expense_date")
            .eq("tenant_id", self.tenant_id)
            .in_("project_id", list(project_by_id))
            .is_("deleted_at", "null")
        )
        if period_start:
            expenses_q = expenses_q.gte("expense_date", period_start)
        if period_end:
            expenses_q = expenses_q.lte("expense_date", period_end)
        expenses = expenses_q.execute().data or []

        for expense in expenses:
            project = project_by_id.get(str(expense.get("project_id")))
            if not project:
                continue
            engagement = engagement_by_id.get(str(project.get("engagement_id")))
            if not engagement:
                continue
            amount = (
                _decimal(expense.get("base_amount"))
                or _decimal(expense.get("amount"))
                or Decimal("0")
            )
            for stats in self._profitability_dimensions_for_engagement(
                facts=facts,
                clients_by_id=clients_by_id,
                engagement=engagement,
            ):
                stats["expense_cost"] += amount
                stats["expense_ids"].add(str(expense["id"]))
                stats["project_ids"].add(str(project["id"]))
                if expense.get("currency"):
                    stats["currencies"].add(str(expense["currency"]))

    # ------------------------------------------------------------------
    # 14. Project Health Scores
    # ------------------------------------------------------------------

    def project_health_scores(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        """Rank active projects by deterministic operating risk.

        Reuses the existing P&L and WIP reports, then layers in project budget,
        time-entry mix, capped T&M drawdown, and retainer under-utilisation.
        Every risk driver is returned with the score so users can audit why a
        project is ranked as healthy, watch, at-risk, or critical.
        """
        projects = (
            self.db.table("projects")
            .select(
                "id, name, engagement_id, currency, budget, budget_hours, status, "
                "engagements!engagement_id("
                "id, name, billing_arrangement, total_value, service_line)"
            )
            .eq("tenant_id", self.tenant_id)
            .eq("status", "active")
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        if not projects:
            return []

        project_ids = [str(project["id"]) for project in projects]
        engagement_ids = {
            str(project["engagement_id"])
            for project in projects
            if project.get("engagement_id")
        }

        terms_by_engagement = self._billing_terms_by_engagement(engagement_ids)
        time_entries_by_project = self._time_entries_by_project(project_ids)
        invoices_by_engagement = self._invoices_by_engagement(engagement_ids)
        pnl_by_project = {
            str(row["project_id"]): row
            for row in self.project_pnl(
                period_start=period_start,
                period_end=period_end,
            )
        }
        wip_by_project = {str(row["project_id"]): row for row in self.wip()}

        rows: list[dict] = []
        for project in projects:
            project_id = str(project["id"])
            engagement_id = str(project.get("engagement_id") or "")
            engagement = _embedded_one(project.get("engagements"))
            terms = terms_by_engagement.get(engagement_id, {})
            entries = time_entries_by_project.get(project_id, [])
            invoices = invoices_by_engagement.get(engagement_id, [])
            pnl = pnl_by_project.get(project_id, {})
            wip = wip_by_project.get(project_id, {})

            drivers: list[dict] = []
            metrics = self._project_health_metrics(
                project=project,
                engagement=engagement,
                terms=terms,
                entries=entries,
                invoices=invoices,
                pnl=pnl,
                wip=wip,
                drivers=drivers,
            )

            score = max(0, 100 - sum(int(driver["impact"]) for driver in drivers))
            rows.append(
                {
                    "project_id": project_id,
                    "project_name": str(project.get("name") or project_id),
                    "engagement_id": engagement_id or None,
                    "engagement_name": engagement.get("name"),
                    "service_line": engagement.get("service_line") or "unclassified",
                    "currency": project.get("currency") or "USD",
                    "health_score": score,
                    "risk_level": _risk_level(score),
                    "drivers": drivers,
                    "metrics": metrics,
                    "recommended_actions": _unique_actions(drivers),
                }
            )

        return sorted(rows, key=lambda row: (row["health_score"], row["project_name"]))

    def _billing_terms_by_engagement(
        self, engagement_ids: set[str]
    ) -> dict[str, dict]:
        if not engagement_ids:
            return {}
        rows = (
            self.db.table("engagement_billing_terms")
            .select(
                "engagement_id, cap_amount, retainer_floor, "
                "retainer_monthly_amount, milestone_total"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("engagement_id", list(engagement_ids))
            .execute()
            .data
            or []
        )
        return {str(row["engagement_id"]): row for row in rows}

    def _time_entries_by_project(self, project_ids: list[str]) -> dict[str, list[dict]]:
        if not project_ids:
            return {}
        rows = (
            self.db.table("time_entries")
            .select("project_id, hours, billable, billing_status, date")
            .eq("tenant_id", self.tenant_id)
            .in_("project_id", project_ids)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(str(row.get("project_id")), []).append(row)
        return grouped

    def _invoices_by_engagement(
        self, engagement_ids: set[str]
    ) -> dict[str, list[dict]]:
        if not engagement_ids:
            return {}
        rows = (
            self.db.table("invoices")
            .select("engagement_id, total, status, issue_date")
            .eq("tenant_id", self.tenant_id)
            .in_("engagement_id", list(engagement_ids))
            .in_("status", _FINAL_INVOICE_STATUSES)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(str(row.get("engagement_id")), []).append(row)
        return grouped

    def _project_health_metrics(
        self,
        *,
        project: dict,
        engagement: dict,
        terms: dict,
        entries: list[dict],
        invoices: list[dict],
        pnl: dict,
        wip: dict,
        drivers: list[dict],
    ) -> dict[str, object]:
        logged_hours = sum(
            (_decimal(row.get("hours")) or Decimal("0")) for row in entries
        )
        billable_hours = sum(
            (_decimal(row.get("hours")) or Decimal("0"))
            for row in entries
            if row.get("billable", True)
        )
        budget_hours = _decimal(project.get("budget_hours"))
        revenue = _decimal(pnl.get("revenue")) or Decimal("0")
        direct_cost = _decimal(pnl.get("direct_cost")) or Decimal("0")
        gross_margin_pct = Decimal(str(pnl.get("gross_margin_pct") or "0"))
        wip_value = _decimal(wip.get("wip_value")) or Decimal("0")
        unbilled_hours = _decimal(wip.get("unbilled_hours")) or Decimal("0")

        metrics: dict[str, object] = {
            "logged_hours": str(logged_hours),
            "billable_hours": str(billable_hours),
            "budget_hours": str(budget_hours) if budget_hours is not None else None,
            "revenue": serialise_money(revenue),
            "direct_cost": serialise_money(direct_cost),
            "gross_margin_pct": float(gross_margin_pct),
            "wip_value": serialise_money(wip_value),
            "unbilled_hours": str(unbilled_hours),
        }

        self._budget_driver(project, logged_hours, budget_hours, drivers, metrics)
        self._margin_driver(revenue, gross_margin_pct, drivers)
        self._wip_driver(revenue, wip_value, drivers, metrics)
        self._cap_driver(engagement, terms, invoices, revenue, drivers, metrics)
        self._retainer_driver(engagement, terms, invoices, drivers, metrics)
        self._scope_creep_driver(entries, drivers, metrics)
        return metrics

    @staticmethod
    def _budget_driver(
        project: dict,
        logged_hours: Decimal,
        budget_hours: Decimal | None,
        drivers: list[dict],
        metrics: dict[str, object],
    ) -> None:
        if budget_hours is None or budget_hours <= 0:
            return
        burn_pct = logged_hours / budget_hours
        metrics["budget_burn_pct"] = round(float(burn_pct * 100), 1)
        if burn_pct >= Decimal("1.00"):
            drivers.append(
                _driver(
                    "budget_hours_burn",
                    "Budget hours exceeded",
                    "critical",
                    25,
                    f"{round(float(burn_pct * 100), 1)}%",
                    "100%",
                    "Logged hours exceed the approved project hour budget.",
                    "Review remaining scope and request a budget or timeline change.",
                )
            )
        elif burn_pct >= Decimal("0.80"):
            drivers.append(
                _driver(
                    "budget_hours_burn",
                    "Budget hours nearing limit",
                    "watch",
                    15,
                    f"{round(float(burn_pct * 100), 1)}%",
                    "80%",
                    (
                        f"{project.get('name', 'Project')} has used most of "
                        "its approved hour budget."
                    ),
                    "Review remaining scope before approving more work.",
                )
            )

    @staticmethod
    def _margin_driver(
        revenue: Decimal,
        gross_margin_pct: Decimal,
        drivers: list[dict],
    ) -> None:
        if revenue <= 0:
            return
        if gross_margin_pct < Decimal("20"):
            drivers.append(
                _driver(
                    "low_margin",
                    "Low gross margin",
                    "critical",
                    25,
                    f"{gross_margin_pct}%",
                    "20%",
                    "Project gross margin is below the finance guardrail.",
                    "Investigate labour and vendor costs before the next billing run.",
                )
            )
        elif gross_margin_pct < Decimal("30"):
            drivers.append(
                _driver(
                    "low_margin",
                    "Gross margin watch",
                    "watch",
                    10,
                    f"{gross_margin_pct}%",
                    "30%",
                    "Project margin is below target but not yet critical.",
                    "Review staffing mix and unbilled recoverability.",
                )
            )

    @staticmethod
    def _wip_driver(
        revenue: Decimal,
        wip_value: Decimal,
        drivers: list[dict],
        metrics: dict[str, object],
    ) -> None:
        if wip_value <= 0:
            return
        if revenue > 0:
            wip_pct = wip_value / revenue
            metrics["wip_to_revenue_pct"] = round(float(wip_pct * 100), 1)
            if wip_pct >= Decimal("0.25"):
                drivers.append(
                    _driver(
                        "unbilled_wip",
                        "High unbilled WIP",
                        "watch",
                        12,
                        f"{round(float(wip_pct * 100), 1)}%",
                        "25% of revenue",
                        "Unbilled WIP is high relative to recognized revenue.",
                        "Prepare billing or accrual review for this project.",
                    )
                )
        elif wip_value >= Decimal("1000"):
            drivers.append(
                _driver(
                    "unbilled_wip",
                    "Unbilled WIP with no revenue",
                    "watch",
                    12,
                    serialise_money(wip_value) or "0.00",
                    "1000.00",
                    "The project has material WIP but no finalized revenue.",
                    "Review whether the next billing run should include this work.",
                )
            )

    @staticmethod
    def _cap_driver(
        engagement: dict,
        terms: dict,
        invoices: list[dict],
        revenue: Decimal,
        drivers: list[dict],
        metrics: dict[str, object],
    ) -> None:
        if engagement.get("billing_arrangement") != "capped_tm":
            return
        cap_amount = _decimal(terms.get("cap_amount"))
        if cap_amount is None or cap_amount <= 0:
            return
        billed = _sum_money(invoices, "total") or revenue
        cap_pct = billed / cap_amount
        metrics["cap_amount"] = serialise_money(cap_amount)
        metrics["cap_used_pct"] = round(float(cap_pct * 100), 1)
        if cap_pct >= Decimal("0.90"):
            drivers.append(
                _driver(
                    "cap_drawdown",
                    "Capped T&M near cap",
                    "critical",
                    20,
                    f"{round(float(cap_pct * 100), 1)}%",
                    "90%",
                    "Finalized billings are close to the capped T&M limit.",
                    "Confirm scope, cap increase, or stop-work posture with the client.",
                )
            )
        elif cap_pct >= Decimal("0.80"):
            drivers.append(
                _driver(
                    "cap_drawdown",
                    "Capped T&M cap watch",
                    "watch",
                    10,
                    f"{round(float(cap_pct * 100), 1)}%",
                    "80%",
                    "Finalized billings are approaching the capped T&M limit.",
                    "Warn the project lead before approving additional work.",
                )
            )

    @staticmethod
    def _retainer_driver(
        engagement: dict,
        terms: dict,
        invoices: list[dict],
        drivers: list[dict],
        metrics: dict[str, object],
    ) -> None:
        if engagement.get("billing_arrangement") not in _RETAINER_BILLING_MODELS:
            return
        retainer_floor = _decimal(terms.get("retainer_floor"))
        if retainer_floor is None or retainer_floor <= 0:
            return
        current_month_billed = _sum_current_month_money(invoices, "total")
        metrics["retainer_floor"] = serialise_money(retainer_floor)
        metrics["current_month_billed"] = serialise_money(current_month_billed)
        if current_month_billed < retainer_floor:
            drivers.append(
                _driver(
                    "retainer_underutilized",
                    "Retainer below floor",
                    "watch",
                    10,
                    serialise_money(current_month_billed) or "0.00",
                    serialise_money(retainer_floor) or "0.00",
                    "Current-month billing is below the retainer floor.",
                    "Schedule work or review retainer communication before month end.",
                )
            )

    @staticmethod
    def _scope_creep_driver(
        entries: list[dict],
        drivers: list[dict],
        metrics: dict[str, object],
    ) -> None:
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        recent = [entry for entry in entries if str(entry.get("date") or "") >= cutoff]
        if len(recent) < 5:
            return
        non_billable = [
            entry
            for entry in recent
            if not entry.get("billable", True)
            or entry.get("billing_status") == "non_billable"
        ]
        scope_pct = Decimal(len(non_billable)) / Decimal(len(recent))
        metrics["recent_non_billable_pct"] = round(float(scope_pct * 100), 1)
        if scope_pct > Decimal("0.20"):
            drivers.append(
                _driver(
                    "scope_creep",
                    "Scope creep risk",
                    "watch",
                    10,
                    f"{round(float(scope_pct * 100), 1)}%",
                    "20%",
                    "Recent non-billable time is above the scope-risk threshold.",
                    "Review whether non-billable work should be re-scoped or absorbed.",
                )
            )

    # ------------------------------------------------------------------
    # 12. Capacity Planning
    # ------------------------------------------------------------------

    def capacity_planning(
        self,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> list[dict]:
        """Employee capacity and utilization for a date window.

        This is an operational planning report built only from current schema:
        employee weekly availability, logged time, billable mix, and active
        project assignments.  It does not invent forecast hours until the data
        model supports allocation percentages or scheduled assignment hours.
        """
        start, end = _capacity_window(period_start, period_end)
        capacity_factor = Decimal((end - start).days + 1) / Decimal("7")
        employees = (
            self.db.table("employees")
            .select(
                "id, first_name, last_name, email, department, practice_area, "
                "seniority, available_hours_per_week, status"
            )
            .eq("tenant_id", self.tenant_id)
            .eq("status", "active")
            .execute()
            .data
            or []
        )
        if not employees:
            return []

        employee_ids = [str(employee["id"]) for employee in employees]
        time_by_employee = self._time_entries_by_employee(employee_ids, start, end)
        assignments_by_employee = self._assignments_by_employee(
            employee_ids, start, end
        )

        rows: list[dict] = []
        for employee in employees:
            employee_id = str(employee["id"])
            entries = time_by_employee.get(employee_id, [])
            assignments = assignments_by_employee.get(employee_id, [])
            weekly_capacity = (
                _decimal(employee.get("available_hours_per_week"))
                or _DEFAULT_WEEKLY_CAPACITY_HOURS
            )
            capacity_hours = (weekly_capacity * capacity_factor).quantize(
                Decimal("0.01")
            )
            logged_hours = sum(
                (_decimal(entry.get("hours")) or Decimal("0")) for entry in entries
            )
            billable_hours = sum(
                (_decimal(entry.get("hours")) or Decimal("0"))
                for entry in entries
                if entry.get("billable", True)
            )
            utilization_pct = _pct(logged_hours, capacity_hours)
            billable_utilization_pct = _pct(billable_hours, capacity_hours)
            capacity_status = _capacity_status(utilization_pct)

            rows.append(
                {
                    "employee_id": employee_id,
                    "employee_name": _employee_name(employee),
                    "email": employee.get("email"),
                    "department": employee.get("department"),
                    "practice_area": employee.get("practice_area"),
                    "seniority": employee.get("seniority"),
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "capacity_hours": str(capacity_hours),
                    "logged_hours": str(logged_hours),
                    "billable_hours": str(billable_hours),
                    "utilization_pct": utilization_pct,
                    "billable_utilization_pct": billable_utilization_pct,
                    "active_assignment_count": len(assignments),
                    "active_assignments": assignments,
                    "capacity_status": capacity_status,
                    "recommended_action": _capacity_action(capacity_status),
                }
            )

        return sorted(
            rows,
            key=lambda row: (
                _capacity_sort_rank(str(row["capacity_status"])),
                -float(row["utilization_pct"]),
                str(row["employee_name"]),
            ),
        )

    def _time_entries_by_employee(
        self,
        employee_ids: list[str],
        start: date,
        end: date,
    ) -> dict[str, list[dict]]:
        rows = (
            self.db.table("time_entries")
            .select("employee_id, hours, billable, date")
            .eq("tenant_id", self.tenant_id)
            .in_("employee_id", employee_ids)
            .gte("date", start.isoformat())
            .lte("date", end.isoformat())
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(str(row.get("employee_id")), []).append(row)
        return grouped

    def _assignments_by_employee(
        self,
        employee_ids: list[str],
        start: date,
        end: date,
    ) -> dict[str, list[dict]]:
        rows = (
            self.db.table("project_assignments")
            .select(
                "employee_id, project_id, role, start_date, end_date, "
                "projects!project_id(id, name, status)"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("employee_id", employee_ids)
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            if not _assignment_overlaps(row, start, end):
                continue
            project = _embedded_one(row.get("projects"))
            if project.get("status") in {"completed", "cancelled"}:
                continue
            employee_id = str(row.get("employee_id"))
            grouped.setdefault(employee_id, []).append(
                {
                    "project_id": str(row.get("project_id")),
                    "project_name": project.get("name"),
                    "role": row.get("role"),
                    "start_date": row.get("start_date"),
                    "end_date": row.get("end_date"),
                }
            )
        return grouped


def _decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _profitability_stats() -> dict[str, object]:
    return {
        "revenue": Decimal("0"),
        "labor_cost": Decimal("0"),
        "expense_cost": Decimal("0"),
        "labor_hours": Decimal("0"),
        "client_ids": set(),
        "engagement_ids": set(),
        "project_ids": set(),
        "invoice_ids": set(),
        "expense_ids": set(),
        "service_lines": set(),
        "currencies": set(),
    }


def _empty_profitability_facts() -> dict[str, object]:
    return {
        "clients": {},
        "by_client": {},
        "by_service_line": {},
        "by_client_kind": {},
    }


def _merge_profitability_stats(target: dict, source: dict) -> None:
    for key in ("revenue", "labor_cost", "expense_cost", "labor_hours"):
        target[key] += source[key]
    for key in (
        "client_ids",
        "engagement_ids",
        "project_ids",
        "invoice_ids",
        "expense_ids",
        "service_lines",
        "currencies",
    ):
        target[key].update(source[key])


def _is_empty_profitability(stats: dict) -> bool:
    return (
        stats["revenue"] == Decimal("0")
        and stats["labor_cost"] == Decimal("0")
        and stats["expense_cost"] == Decimal("0")
    )


def _profitability_row(identity: dict[str, object], stats: dict) -> dict[str, object]:
    revenue = stats["revenue"]
    labor_cost = stats["labor_cost"]
    expense_cost = stats["expense_cost"]
    total_cost = labor_cost + expense_cost
    gross_margin = revenue - total_cost
    gross_margin_pct = (
        round(float(gross_margin / revenue * 100), 1)
        if revenue > Decimal("0")
        else 0.0
    )

    return {
        **identity,
        "revenue": serialise_money(revenue) or "0.00",
        "labor_cost": serialise_money(labor_cost) or "0.00",
        "expense_cost": serialise_money(expense_cost) or "0.00",
        "total_cost": serialise_money(total_cost) or "0.00",
        "gross_margin": serialise_money(gross_margin) or "0.00",
        "gross_margin_pct": gross_margin_pct,
        "labor_hours": str(stats["labor_hours"].quantize(Decimal("0.01"))),
        "client_count": len(stats["client_ids"]),
        "engagement_count": len(stats["engagement_ids"]),
        "project_count": len(stats["project_ids"]),
        "invoice_count": len(stats["invoice_ids"]),
        "expense_count": len(stats["expense_ids"]),
        "profitability_status": _profitability_status(gross_margin_pct),
        "recommended_action": _profitability_action(gross_margin_pct),
    }


def _client_group_member_summary(member: dict) -> dict[str, object]:
    client = _embedded_one(member.get("clients"))
    return {
        "member_id": str(member["id"]),
        "client_id": str(member["client_id"]),
        "client_name": client.get("name"),
        "client_kind": client.get("kind"),
        "relationship_role": member.get("relationship_role") or "other",
        "is_primary": bool(member.get("is_primary")),
    }


def _currency_label(stats: dict) -> str | None:
    currencies = {str(currency) for currency in stats["currencies"] if currency}
    if not currencies:
        return None
    if len(currencies) == 1:
        return next(iter(currencies))
    return "mixed"


def _profitability_status(gross_margin_pct: float) -> str:
    if gross_margin_pct < 20:
        return "critical"
    if gross_margin_pct < 30:
        return "watch"
    if gross_margin_pct >= 50:
        return "strong"
    return "healthy"


def _profitability_action(gross_margin_pct: float) -> str:
    if gross_margin_pct < 20:
        return "Review pricing, scope, staffing mix, and direct costs before more work is approved."
    if gross_margin_pct < 30:
        return "Ask the partner to review margin leakage and unbilled recovery."
    if gross_margin_pct >= 50:
        return "Protect this relationship and look for repeatable delivery patterns."
    return "Continue monitoring margin and delivery mix."


def _practice_stats(practice_key: str) -> dict[str, object]:
    return {
        "practice_key": practice_key,
        "practice_label": _SERVICE_LINE_LABELS.get(
            practice_key, practice_key.replace("_", " ").title()
        ),
        "revenue": "0.00",
        "labor_cost": "0.00",
        "expense_cost": "0.00",
        "total_cost": "0.00",
        "gross_margin": "0.00",
        "gross_margin_pct": 0.0,
        "profitability_status": "healthy",
        "financial_recommended_action": None,
        "client_count": 0,
        "engagement_count": 0,
        "project_count": 0,
        "invoice_count": 0,
        "active_project_count": 0,
        "at_risk_project_count": 0,
        "critical_project_count": 0,
        "project_health_score_total": Decimal("0"),
        "project_risk_counts": {
            "healthy": 0,
            "watch": 0,
            "at_risk": 0,
            "critical": 0,
        },
        "employee_count": 0,
        "capacity_hours": Decimal("0"),
        "logged_hours": Decimal("0"),
        "billable_hours": Decimal("0"),
        "capacity_status_counts": {
            "overallocated": 0,
            "full": 0,
            "underutilized": 0,
            "balanced": 0,
        },
        "recommended_actions": [],
    }


def _practice_dashboard_row(
    practice: dict,
    *,
    period_start: str | None,
    period_end: str | None,
) -> dict[str, object]:
    active_project_count = int(practice["active_project_count"])
    avg_health_score = (
        round(
            float(practice["project_health_score_total"] / active_project_count),
            1,
        )
        if active_project_count
        else None
    )
    capacity_hours = practice["capacity_hours"]
    logged_hours = practice["logged_hours"]
    billable_hours = practice["billable_hours"]
    avg_utilization_pct = _pct(logged_hours, capacity_hours)
    billable_utilization_pct = _pct(billable_hours, capacity_hours)

    actions = list(practice["recommended_actions"])
    financial_action = practice.get("financial_recommended_action")
    if practice.get("profitability_status") in {"critical", "watch"}:
        _append_unique(actions, str(financial_action or "Review practice margin."))
    if int(practice["critical_project_count"]):
        _append_unique(actions, "Escalate critical project risks in the next partner review.")
    if practice["capacity_status_counts"].get("overallocated", 0):
        _append_unique(actions, "Rebalance overallocated staff before accepting new work.")

    return {
        "practice_key": practice["practice_key"],
        "practice_label": practice["practice_label"],
        "period_start": period_start,
        "period_end": period_end,
        "revenue": practice["revenue"],
        "labor_cost": practice["labor_cost"],
        "expense_cost": practice["expense_cost"],
        "total_cost": practice["total_cost"],
        "gross_margin": practice["gross_margin"],
        "gross_margin_pct": practice["gross_margin_pct"],
        "profitability_status": practice["profitability_status"],
        "client_count": practice["client_count"],
        "engagement_count": practice["engagement_count"],
        "project_count": practice["project_count"],
        "invoice_count": practice["invoice_count"],
        "active_project_count": active_project_count,
        "at_risk_project_count": practice["at_risk_project_count"],
        "critical_project_count": practice["critical_project_count"],
        "avg_project_health_score": avg_health_score,
        "project_risk_counts": practice["project_risk_counts"],
        "employee_count": practice["employee_count"],
        "capacity_hours": serialise_money(capacity_hours) or "0.00",
        "logged_hours": serialise_money(logged_hours) or "0.00",
        "billable_hours": serialise_money(billable_hours) or "0.00",
        "avg_utilization_pct": avg_utilization_pct,
        "billable_utilization_pct": billable_utilization_pct,
        "capacity_status_counts": practice["capacity_status_counts"],
        "recommended_actions": actions,
    }


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _embedded_one(value: object) -> dict:
    if isinstance(value, list):
        return value[0] if value else {}
    return value if isinstance(value, dict) else {}


def _sum_money(rows: list[dict], key: str) -> Decimal:
    total = Decimal("0")
    for row in rows:
        amount = _decimal(row.get(key))
        if amount is not None:
            total += amount
    return total


def _sum_current_month_money(rows: list[dict], key: str) -> Decimal:
    month_prefix = date.today().strftime("%Y-%m")
    total = Decimal("0")
    for row in rows:
        issue_date = str(row.get("issue_date") or "")
        if issue_date[:7] != month_prefix:
            continue
        amount = _decimal(row.get(key))
        if amount is not None:
            total += amount
    return total


def _driver(
    code: str,
    label: str,
    severity: str,
    impact: int,
    metric: str,
    threshold: str,
    summary: str,
    recommended_action: str,
) -> dict[str, object]:
    return {
        "code": code,
        "label": label,
        "severity": severity,
        "impact": impact,
        "metric": metric,
        "threshold": threshold,
        "summary": summary,
        "recommended_action": recommended_action,
    }


def _risk_level(score: int) -> str:
    if score >= 85:
        return "healthy"
    if score >= 70:
        return "watch"
    if score >= 50:
        return "at_risk"
    return "critical"


def _unique_actions(drivers: list[dict]) -> list[str]:
    actions: list[str] = []
    for driver in drivers:
        action = str(driver.get("recommended_action") or "")
        if action and action not in actions:
            actions.append(action)
    return actions


def _capacity_window(
    period_start: str | None,
    period_end: str | None,
) -> tuple[date, date]:
    today = date.today()
    default_start = today - timedelta(days=today.weekday())
    start = _parse_date(period_start) or default_start
    end = _parse_date(period_end) or (start + timedelta(days=6))
    if end < start:
        return end, start
    return start, end


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _pct(numerator: Decimal, denominator: Decimal) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator / denominator * 100), 1)


def _employee_name(employee: dict) -> str:
    name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    return name or str(employee.get("email") or employee.get("id") or "Unknown")


def _capacity_status(utilization_pct: float) -> str:
    if utilization_pct >= 110:
        return "overallocated"
    if utilization_pct >= 90:
        return "full"
    if utilization_pct <= 60:
        return "underutilized"
    return "balanced"


def _capacity_action(status: str) -> str:
    if status == "overallocated":
        return "Rebalance assignments or defer non-critical work this period."
    if status == "full":
        return "Avoid adding new work without partner approval."
    if status == "underutilized":
        return "Review backlog and assign additional billable work where possible."
    return "Capacity is within the target operating range."


def _capacity_sort_rank(status: str) -> int:
    return {
        "overallocated": 0,
        "underutilized": 1,
        "full": 2,
        "balanced": 3,
    }.get(status, 4)


def _assignment_overlaps(row: dict, start: date, end: date) -> bool:
    assignment_start = _parse_date(row.get("start_date")) or start
    assignment_end = _parse_date(row.get("end_date")) or end
    return assignment_start <= end and assignment_end >= start


def _target_revenue_for_margin(total_cost: Decimal) -> Decimal:
    if total_cost <= 0:
        return Decimal("0")
    margin_factor = Decimal("1") - (_TARGET_GROSS_MARGIN_PCT / Decimal("100"))
    return (total_cost / margin_factor).quantize(Decimal("0.01"))


def _target_margin_gap(revenue: Decimal, total_cost: Decimal) -> Decimal:
    return max(Decimal("0"), _target_revenue_for_margin(total_cost) - revenue)


def _rate_per_hour(amount: Decimal, hours: Decimal) -> Decimal | None:
    if hours <= 0:
        return None
    return (amount / hours).quantize(Decimal("0.01"))


def _rate_uplift_pct(
    current_rate: Decimal | None,
    target_rate: Decimal | None,
) -> float | None:
    if current_rate is None or target_rate is None or current_rate <= 0:
        return None
    if target_rate <= current_rate:
        return 0.0
    return round(float((target_rate / current_rate - Decimal("1")) * 100), 1)


def _candidate_evidence(candidates: list[dict]) -> str:
    if not candidates:
        return "No same-practice underutilized candidate is visible in this period."
    names = ", ".join(str(candidate.get("employee_name") or "Unknown") for candidate in candidates)
    return f"Same-practice underutilized candidates: {names}."


def _available_hours(employee: dict) -> str:
    capacity_hours = _decimal(employee.get("capacity_hours")) or Decimal("0")
    logged_hours = _decimal(employee.get("logged_hours")) or Decimal("0")
    return str(max(Decimal("0"), capacity_hours - logged_hours).quantize(Decimal("0.01")))


def _recommendation(
    *,
    recommendation_id: str,
    recommendation_type: str,
    priority: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    service_line: str | None,
    period_start: str | None,
    period_end: str | None,
    evidence: list[str],
    metrics: dict[str, object],
    recommended_action: str,
) -> dict[str, object]:
    return {
        "recommendation_id": recommendation_id,
        "recommendation_type": recommendation_type,
        "priority": priority,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "service_line": service_line,
        "period_start": period_start,
        "period_end": period_end,
        "evidence": [item for item in evidence if item],
        "metrics": metrics,
        "recommended_action": recommended_action,
    }


def _recommendation_priority_rank(priority: str) -> int:
    return {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }.get(priority, 4)


def _scope_change_drivers(drivers: list[dict]) -> list[dict]:
    return [
        driver
        for driver in drivers
        if driver.get("code") in _SCOPE_CHANGE_DRIVER_CODES
    ]


def _select_scope_comparables(
    *,
    context: dict,
    project: dict,
    comparables: list[dict],
) -> list[dict]:
    engagement = _embedded_one(context.get("engagements"))
    service_line = str(project.get("service_line") or "unclassified")
    billing_arrangement = engagement.get("billing_arrangement")
    current_budget_hours = _decimal(context.get("budget_hours")) or _decimal(
        (project.get("metrics") or {}).get("budget_hours")
    )

    same_billing_model = [
        comparable
        for comparable in comparables
        if comparable.get("service_line") == service_line
        and comparable.get("billing_arrangement") == billing_arrangement
    ]
    same_service_line = [
        comparable
        for comparable in comparables
        if comparable.get("service_line") == service_line
        and comparable not in same_billing_model
    ]
    ranked = [*same_billing_model, *same_service_line]
    ranked.sort(
        key=lambda comparable: (
            _budget_distance(current_budget_hours, comparable),
            -(_decimal(comparable.get("revenue")) or Decimal("0")),
            str(comparable.get("project_name") or ""),
        )
    )
    return ranked[:3]


def _budget_distance(current_budget_hours: Decimal | None, comparable: dict) -> Decimal:
    comparable_budget_hours = _decimal(comparable.get("budget_hours"))
    if current_budget_hours is None or comparable_budget_hours is None:
        return Decimal("999999")
    return abs(current_budget_hours - comparable_budget_hours)


def _scope_fee_adjustment(
    project: dict,
    comparables: list[dict],
) -> tuple[Decimal, str]:
    metrics = project.get("metrics") or {}
    logged_hours = _decimal(metrics.get("logged_hours")) or Decimal("0")
    budget_hours = _decimal(metrics.get("budget_hours"))
    overrun_hours = (
        max(Decimal("0"), logged_hours - budget_hours)
        if budget_hours is not None
        else Decimal("0")
    )
    comparable_rates = [
        rate
        for rate in (_decimal(row.get("effective_rate")) for row in comparables)
        if rate is not None and rate > 0
    ]
    if overrun_hours > 0 and comparable_rates:
        return (
            (overrun_hours * _median_decimal(comparable_rates)).quantize(Decimal("0.01")),
            "historical_effective_rate",
        )

    wip_value = _decimal(metrics.get("wip_value")) or Decimal("0")
    if wip_value > 0:
        return wip_value.quantize(Decimal("0.01")), "unbilled_wip"
    return Decimal("0"), "insufficient_scope_value_data"


def _median_decimal(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return ((ordered[middle - 1] + ordered[middle]) / Decimal("2")).quantize(
        Decimal("0.01")
    )


def _scope_current_metrics(project: dict) -> dict[str, object]:
    metrics = project.get("metrics") or {}
    logged_hours = _decimal(metrics.get("logged_hours")) or Decimal("0")
    budget_hours = _decimal(metrics.get("budget_hours"))
    overrun_hours = (
        max(Decimal("0"), logged_hours - budget_hours)
        if budget_hours is not None
        else Decimal("0")
    )
    return {
        "logged_hours": str(logged_hours.quantize(Decimal("0.01"))),
        "budget_hours": (
            str(budget_hours.quantize(Decimal("0.01")))
            if budget_hours is not None
            else None
        ),
        "overrun_hours": str(overrun_hours.quantize(Decimal("0.01"))),
        "budget_burn_pct": metrics.get("budget_burn_pct"),
        "cap_used_pct": metrics.get("cap_used_pct"),
        "recent_non_billable_pct": metrics.get("recent_non_billable_pct"),
        "wip_value": metrics.get("wip_value"),
        "unbilled_hours": metrics.get("unbilled_hours"),
    }


def _scope_budget_overrun_pct(
    logged_hours: Decimal,
    budget_hours: Decimal | None,
) -> float | None:
    if budget_hours is None or budget_hours <= 0:
        return None
    return round(float((logged_hours - budget_hours) / budget_hours * 100), 1)


def _scope_confidence(comparables: list[dict]) -> str:
    if len(comparables) >= 3:
        return "high"
    if comparables:
        return "medium"
    return "low"


def _scope_priority(risk_level: str) -> str:
    if risk_level == "critical":
        return "critical"
    if risk_level == "at_risk":
        return "high"
    return "medium"


def _scope_recommended_action(drivers: list[dict], fee: Decimal) -> str:
    codes = {str(driver.get("code")) for driver in drivers}
    fee_text = serialise_money(fee) or "0.00"
    if "cap_drawdown" in codes:
        return (
            f"Prepare a cap increase or change order for at least {fee_text}, "
            "then pause additional out-of-scope work until approved."
        )
    if "budget_hours_burn" in codes:
        return (
            f"Raise a scope-change request for at least {fee_text} and reset "
            "the remaining hour budget with the client."
        )
    return (
        f"Separate recurring non-billable work into a change request worth at "
        f"least {fee_text}, or document why the firm will absorb it."
    )
