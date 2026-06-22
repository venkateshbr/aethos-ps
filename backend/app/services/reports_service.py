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
  11. project_health_scores
  12. capacity_planning
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

        # Cache of rate_card_id → rate to avoid repeating the same lookup across
        # multiple projects that share an engagement / rate card.
        rate_cache: dict[str, Decimal] = {}

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

            # engagements may come back as a dict or a list depending on the
            # PostgREST cardinality inference; normalise.
            eng_embed = proj.get("engagements")
            if isinstance(eng_embed, list):
                eng_embed = eng_embed[0] if eng_embed else None
            rate_card_id = (eng_embed or {}).get("rate_card_id")

            rate = Decimal("0")
            if rate_card_id:
                if rate_card_id in rate_cache:
                    rate = rate_cache[rate_card_id]
                else:
                    rc = (
                        self.db.table("rate_card_lines")
                        .select("rate")
                        .eq("rate_card_id", rate_card_id)
                        .limit(1)
                        .execute()
                        .data
                    )
                    if rc:
                        rate = Decimal(str(rc[0]["rate"]))
                    rate_cache[rate_card_id] = rate

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
    # 11. Project Health Scores
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
