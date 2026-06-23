"""Repository: tenant-scoped CRUD for engagements and engagement_billing_terms."""

from __future__ import annotations

import asyncio
import logging

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "engagements"
_TERMS_TABLE = "engagement_billing_terms"


class EngagementRepository:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _base_query(self):  # type: ignore[no-untyped-def]
        return (
            self.db.table(_TABLE)
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list(
        self,
        status: str | None = None,
        client_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        def _query() -> object:
            query = self._base_query()
            if status:
                query = query.eq("status", status)
            if client_id:
                query = query.eq("client_id", client_id)
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            return query.execute()

        result = await asyncio.to_thread(_query)
        return result.data or []

    async def get(self, id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self._base_query().eq("id", id).execute()
        )
        return result.data[0] if result.data else None

    async def get_billing_terms(self, engagement_id: str) -> dict | None:
        result = await asyncio.to_thread(
            lambda: self.db.table(_TERMS_TABLE)
            .select("*")
            .eq("engagement_id", engagement_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: dict) -> dict:
        payload = {**data, "tenant_id": self.tenant_id}
        result = await asyncio.to_thread(
            lambda: self.db.table(_TABLE).insert(payload).execute()
        )
        return result.data[0]

    async def create_billing_terms(self, engagement_id: str, terms: dict) -> dict:
        payload = {
            **terms,
            "engagement_id": engagement_id,
            "tenant_id": self.tenant_id,
        }
        result = await asyncio.to_thread(
            lambda: self.db.table(_TERMS_TABLE).insert(payload).execute()
        )
        return result.data[0]

    async def update_status(self, id: str, status: str) -> dict | None:
        existing = await self.get(id)
        if existing is None:
            return None
        result = await asyncio.to_thread(
            lambda: self.db.table(_TABLE)
            .update({"status": status})
            .eq("id", id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Summary support queries
    # ------------------------------------------------------------------

    async def get_invoice_summary(self, engagement_id: str) -> dict:
        """Return billed_to_date, invoice_count, last_invoice_date for an engagement.

        Only posted/sent/paid, non-deleted invoices are included in the billing
        total. Drafts are still work-in-progress and voids are reversals.
        """
        result = await asyncio.to_thread(
            lambda: self.db.table("invoices")
            .select("total, issue_date, status")
            .eq("tenant_id", self.tenant_id)
            .eq("engagement_id", engagement_id)
            .is_("deleted_at", "null")
            .neq("status", "voided")
            .neq("status", "draft")
            .execute()
        )
        rows = result.data or []
        from decimal import Decimal as _D

        billed = sum(_D(str(r["total"])) for r in rows)
        last_date: str | None = None
        for r in rows:
            if r.get("issue_date"):
                d = str(r["issue_date"])
                if last_date is None or d > last_date:
                    last_date = d
        return {
            "billed_to_date": billed,
            "invoice_count": len(rows),
            "last_invoice_date": last_date,
        }

    async def get_wip_summary(self, engagement_id: str) -> dict:
        """Return wip_hours and wip_value for unbilled billable time on this engagement.

        Approach:
          1. Find all non-deleted projects for this engagement.
          2. For each project, fetch unbilled + billable time entries.
          3. Accumulate hours; for WIP value use the assignment override_rate if
             present, then the employee default_bill_rate as a fallback.
             If no rate is resolvable, the hours are counted but valued at 0.
        """
        # Step 1 — projects under this engagement
        projects_result = await asyncio.to_thread(
            lambda: self.db.table("projects")
            .select("id")
            .eq("tenant_id", self.tenant_id)
            .eq("engagement_id", engagement_id)
            .is_("deleted_at", "null")
            .execute()
        )
        project_rows = projects_result.data or []
        if not project_rows:
            return {"wip_hours": 0.0, "wip_value": "0.00"}

        project_ids = [r["id"] for r in project_rows]

        # Step 2 — unbilled billable time entries across those projects
        te_result = await asyncio.to_thread(
            lambda: self.db.table("time_entries")
            .select("hours, employee_id, project_id")
            .eq("tenant_id", self.tenant_id)
            .in_("project_id", project_ids)
            .eq("billing_status", "unbilled")
            .eq("billable", True)
            .is_("deleted_at", "null")
            .execute()
        )
        te_rows = te_result.data or []
        if not te_rows:
            return {"wip_hours": 0.0, "wip_value": "0.00"}

        # Step 3 — resolve bill rates
        # Fetch project_assignments for override_rate
        pa_result = await asyncio.to_thread(
            lambda: self.db.table("project_assignments")
            .select("project_id, employee_id, override_rate")
            .eq("tenant_id", self.tenant_id)
            .in_("project_id", project_ids)
            .execute()
        )
        pa_map: dict[tuple, str | None] = {
            (r["project_id"], r["employee_id"]): r.get("override_rate")
            for r in (pa_result.data or [])
        }

        # Fetch employee default_bill_rate for fallback
        employee_ids = list({r["employee_id"] for r in te_rows})
        emp_result = await asyncio.to_thread(
            lambda: self.db.table("employees")
            .select("id, default_bill_rate")
            .eq("tenant_id", self.tenant_id)
            .in_("id", employee_ids)
            .execute()
        )
        emp_map: dict[str, str | None] = {
            r["id"]: r.get("default_bill_rate") for r in (emp_result.data or [])
        }

        from decimal import Decimal as _D

        total_hours = _D("0")
        total_value = _D("0")

        for te in te_rows:
            hours = _D(str(te["hours"]))
            total_hours += hours

            override = pa_map.get((te["project_id"], te["employee_id"]))
            default_rate = emp_map.get(te["employee_id"])
            rate_raw = override if override is not None else default_rate
            rate = _D(str(rate_raw)) if rate_raw is not None else _D("0")
            total_value += hours * rate

        from app.domain.money import TWO_PLACES

        return {
            "wip_hours": float(total_hours),
            "wip_value": str(total_value.quantize(TWO_PLACES)),
        }
