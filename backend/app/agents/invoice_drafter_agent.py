"""invoice_drafter_agent — calculates invoice lines from engagement data.

Not a prompt-based agent for core arithmetic — numbers come from the DB.
All five billing arrangements are supported:
  - time_and_materials: sum unbilled time entries x rate, pass through expenses
  - fixed_fee: single line from billing_terms.fixed_fee_amount
  - milestone: one line per milestone in billing_terms
  - retainer: monthly_amount from billing_terms
  - retainer_draw: T&M with retainer offset
  - capped_tm: T&M capped at billing_terms.cap_amount

Tax is applied per-line using the tenant's default tax rate.

Quality gates:
- All monetary arithmetic uses Decimal — never float.
- Agent output is a typed Pydantic model (InvoiceDraft).
- DB access is tenant-scoped; every query includes tenant_id.
- If engagement not found, ValueError is raised (caller wraps as HTTP 404).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.agents.base import AgentDeps

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class InvoiceLineItem(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal
    amount: Decimal
    tax_rate_id: str | None = None
    tax_amount: Decimal = Decimal("0")
    time_entry_id: str | None = None
    expense_id: str | None = None


class InvoiceDraft(BaseModel):
    engagement_id: str
    client_id: str
    currency: str
    lines: list[InvoiceLineItem]
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    period_start: str | None = None
    period_end: str | None = None
    billing_arrangement: str
    summary: str = ""
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def draft_invoice(
    engagement_id: str,
    deps: AgentDeps,
    period_start: date | None = None,
    period_end: date | None = None,
) -> InvoiceDraft:
    """Build an InvoiceDraft for an engagement.

    Args:
        engagement_id: UUID of the engagement to draft an invoice for.
        deps: AgentDeps with tenant_id, user_id, and db client.
        period_start: Optional start of billing period (inclusive).
        period_end: Optional end of billing period (inclusive).

    Returns:
        InvoiceDraft with all lines, totals, and tax applied.

    Raises:
        ValueError: If the engagement is not found or is not accessible.
    """
    db = deps.db

    # Fetch engagement + billing terms + client in one query.
    # We deliberately use .limit(1) instead of .single() because .single()
    # raises postgrest.APIError (PGRST116) on 0 rows, which would bubble up
    # as a 500. We want a clean ValueError that the router can translate to
    # a 404. The .eq("tenant_id", ...) clause also makes cross-tenant lookups
    # return 0 rows → 404, never a 5xx — see bug #101.
    eng_result = (
        db.table("engagements")
        .select("*, engagement_billing_terms(*), clients(id, name)")
        .eq("id", engagement_id)
        .eq("tenant_id", deps.tenant_id)
        .limit(1)
        .execute()
    )
    rows = eng_result.data or []
    eng = rows[0] if rows else None

    if not eng:
        raise ValueError(f"Engagement {engagement_id!r} not found for tenant {deps.tenant_id!r}")

    # engagement_billing_terms may be a list or a single dict depending on the join
    billing_raw = eng.get("engagement_billing_terms") or {}
    if isinstance(billing_raw, list):
        billing: dict = billing_raw[0] if billing_raw else {}
    else:
        billing = billing_raw

    arrangement: str = eng.get("billing_arrangement", "time_and_materials")
    currency: str = eng.get("currency", "USD")
    client_id: str = eng["client_id"]

    # Build lines per arrangement
    lines: list[InvoiceLineItem] = []

    if arrangement == "time_and_materials":
        lines = _draft_tm_lines(eng, deps, period_start, period_end)

    elif arrangement == "fixed_fee":
        amount = Decimal(str(billing.get("fixed_fee_amount") or "0"))
        lines = [
            InvoiceLineItem(
                description=f"Fixed Fee: {eng['name']}",
                unit_price=amount,
                amount=amount,
            )
        ]

    elif arrangement == "retainer":
        amount = Decimal(str(billing.get("retainer_monthly_amount") or "0"))
        period_label = period_start.strftime("%B %Y") if period_start else "Current Period"
        lines = [
            InvoiceLineItem(
                description=f"Monthly Retainer — {period_label}",
                unit_price=amount,
                amount=amount,
            )
        ]

    elif arrangement == "retainer_draw":
        lines = _draft_tm_lines(eng, deps, period_start, period_end)
        retainer_balance = Decimal(str(billing.get("retainer_monthly_amount") or "0"))
        if retainer_balance > Decimal("0"):
            lines.append(
                InvoiceLineItem(
                    description="Retainer applied",
                    unit_price=-retainer_balance,
                    amount=-retainer_balance,
                )
            )

    elif arrangement == "capped_tm":
        lines = _draft_tm_lines(eng, deps, period_start, period_end)
        cap = Decimal(str(billing.get("cap_amount") or "0"))
        subtotal = sum(line.amount for line in lines)
        if cap > Decimal("0") and subtotal > cap:
            overflow = subtotal - cap
            lines.append(
                InvoiceLineItem(
                    description=f"Cap adjustment (non-billable overflow: {overflow})",
                    unit_price=-overflow,
                    amount=-overflow,
                )
            )

    elif arrangement == "milestone":
        lines = _draft_milestone_lines(billing)

    else:
        logger.warning(
            "invoice_drafter: unknown billing arrangement %r for engagement %s",
            arrangement,
            engagement_id,
        )
        lines = []

    # Apply tax to each positive line
    lines = _apply_tax(lines, deps, currency)

    subtotal = sum(line.amount for line in lines)
    tax_total = sum(line.tax_amount for line in lines)
    total = subtotal + tax_total

    return InvoiceDraft(
        engagement_id=engagement_id,
        client_id=client_id,
        currency=currency,
        lines=lines,
        subtotal=subtotal,
        tax_total=tax_total,
        total=total,
        period_start=period_start.isoformat() if period_start else None,
        period_end=period_end.isoformat() if period_end else None,
        billing_arrangement=arrangement,
        summary=f"{arrangement.replace('_', ' ').title()} invoice for {eng['name']}",
        confidence=0.95,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _draft_tm_lines(
    eng: dict,
    deps: AgentDeps,
    period_start: date | None,
    period_end: date | None,
) -> list[InvoiceLineItem]:
    """Build lines from unbilled time entries and unbilled expenses."""
    db = deps.db
    tenant_id = deps.tenant_id
    engagement_id = eng["id"]

    # All projects under this engagement
    projects_result = (
        db.table("projects")
        .select("id")
        .eq("engagement_id", engagement_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    project_ids = [p["id"] for p in (projects_result.data or [])]

    if not project_ids:
        return []

    # Fetch unbilled, billable, APPROVED time entries.
    # The approval gate (issue #134) means only manager-approved hours can be
    # billed — draft/submitted/rejected time is excluded from invoicing.
    q = (
        db.table("time_entries")
        .select("id, project_id, employee_id, hours, date, description, billing_status, status")
        .eq("tenant_id", tenant_id)
        .in_("project_id", project_ids)
        .eq("billing_status", "unbilled")
        .eq("billable", True)
        .eq("status", "approved")
        .is_("deleted_at", "null")
    )
    if period_start:
        q = q.gte("date", period_start.isoformat())
    if period_end:
        q = q.lte("date", period_end.isoformat())

    entries = q.execute().data or []

    # Resolve rate card for the engagement
    rate_card_id = eng.get("rate_card_id")
    rates: dict[str, Decimal] = {}
    if rate_card_id:
        rc_lines = (
            db.table("rate_card_lines")
            .select("role, rate")
            .eq("rate_card_id", rate_card_id)
            .execute()
            .data or []
        )
        rates = {r["role"]: Decimal(str(r["rate"])) for r in rc_lines}

    # Aggregate by role (from project_assignments or a default role field on entry)
    # time_entries don't store role directly; resolve via project_assignments
    if entries:
        employee_ids = list({e["employee_id"] for e in entries})
        assignments = (
            db.table("project_assignments")
            .select("employee_id, project_id, role")
            .eq("tenant_id", tenant_id)
            .in_("project_id", project_ids)
            .in_("employee_id", employee_ids)
            .execute()
            .data or []
        )
        # Build (project_id, employee_id) → role map
        role_map: dict[tuple[str, str], str] = {
            (a["project_id"], a["employee_id"]): (a["role"] or "Consultant")
            for a in assignments
        }
    else:
        role_map = {}

    by_role: dict[str, dict] = defaultdict(lambda: {"hours": Decimal("0"), "ids": []})
    for entry in entries:
        role = role_map.get((entry["project_id"], entry["employee_id"]), "Consultant")
        by_role[role]["hours"] += Decimal(str(entry["hours"]))
        by_role[role]["ids"].append(entry["id"])

    lines: list[InvoiceLineItem] = []
    for role, data in by_role.items():
        rate = rates.get(role, Decimal("0"))
        hours = data["hours"]
        amount = (hours * rate).quantize(Decimal("0.01"))
        if amount > Decimal("0"):
            lines.append(
                InvoiceLineItem(
                    description=f"{role} — {hours}h @ {rate}",
                    quantity=hours,
                    unit_price=rate,
                    amount=amount,
                )
            )

    # Unbilled, billable project expenses
    exp_q = (
        db.table("project_expenses")
        .select("id, description, amount, currency, billing_status")
        .eq("tenant_id", tenant_id)
        .in_("project_id", project_ids)
        .eq("billing_status", "unbilled")
        .eq("billable", True)
    )
    expenses = exp_q.execute().data or []

    for exp in expenses:
        amount = Decimal(str(exp.get("amount", "0")))
        lines.append(
            InvoiceLineItem(
                description=exp.get("description", "Expense"),
                unit_price=amount,
                amount=amount,
                expense_id=exp["id"],
            )
        )

    return lines


def _draft_milestone_lines(billing: dict) -> list[InvoiceLineItem]:
    """Build one line per milestone that has an amount."""
    milestones = billing.get("milestones", []) or []
    lines = []
    for m in milestones:
        if m.get("amount"):
            amount = Decimal(str(m["amount"]))
            lines.append(
                InvoiceLineItem(
                    description=f"Milestone: {m.get('name', 'Milestone')}",
                    unit_price=amount,
                    amount=amount,
                )
            )
    return lines


def _apply_tax(
    lines: list[InvoiceLineItem],
    deps: AgentDeps,
    currency: str,
) -> list[InvoiceLineItem]:
    """Look up the default tax rate for the tenant and apply it to each positive line.

    Falls back to a country-level default if no tenant-specific default is found.
    Returns lines unchanged if no tax rate is configured.
    """
    db = deps.db
    tenant_id = deps.tenant_id

    # Try tenant-specific default first
    tax_result = (
        db.table("tax_rates")
        .select("id, rate")
        .eq("tenant_id", tenant_id)
        .eq("is_default", True)
        .limit(1)
        .execute()
    )
    tax_data = tax_result.data

    if not tax_data:
        # Fall back to system default for tenant's country
        try:
            tenant_result = (
                db.table("tenants")
                .select("country")
                .eq("id", tenant_id)
                .single()
                .execute()
            )
            country = tenant_result.data["country"] if tenant_result.data else "US"
        except Exception:
            country = "US"

        tax_result = (
            db.table("tax_rates")
            .select("id, rate")
            .is_("tenant_id", "null")
            .eq("country", country)
            .eq("is_default", True)
            .limit(1)
            .execute()
        )
        tax_data = tax_result.data

    if not tax_data:
        return lines

    tax_rate_id: str = str(tax_data[0]["id"])
    tax_rate: Decimal = Decimal(str(tax_data[0]["rate"]))

    result = []
    for line in lines:
        if line.amount > Decimal("0"):
            tax_amount = (line.amount * tax_rate).quantize(Decimal("0.01"))
            result.append(
                line.model_copy(
                    update={"tax_rate_id": tax_rate_id, "tax_amount": tax_amount}
                )
            )
        else:
            # Negative lines (cap adjustments, retainer offsets) don't get taxed
            result.append(line)
    return result
