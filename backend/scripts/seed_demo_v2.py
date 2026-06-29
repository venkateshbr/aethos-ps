"""Seed the Demo Guide v2 Meridian fixture into an existing tenant.

Usage:
    uv run python -m scripts.seed_demo_v2 --tenant-id <uuid> --reset

This is intentionally tenant-scoped. It preserves tenant membership, chart of
accounts, tax rates, FX rates, and platform configuration, while replacing the
operational demo records used by docs/DEMO_GUIDE_v2.md.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from scripts.seed_demo import (
    _approve_bill,
    _approve_invoice,
    _create_bill,
    _create_invoice,
    _d,
    _ensure_client,
    _ensure_employee,
    _ensure_engagement,
    _ensure_project,
    _fail,
    _m,
    _make_client,
    _ok,
    _pay_invoice,
    _section,
    _send_invoice,
    _set_tenant,
)
from supabase import Client

SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"
JUNE = "2026-06"


def _best_effort_delete(db: Client, table: str, tenant_id: str) -> None:
    try:
        db.table(table).delete().eq("tenant_id", tenant_id).execute()
    except Exception as exc:
        _ok(f"Skipped {table}: {str(exc).splitlines()[0][:120]}")


def reset_demo_v2_data(db: Client, tenant_id: str) -> None:
    _section("Resetting tenant operational demo data")
    for table in [
        "bill_payment_items",
        "bill_payment_batches",
        "payments",
        "invoice_lines",
        "bill_lines",
        "project_expenses",
        "time_entries",
        "project_assignments",
        "journal_lines",
        "journal_entries",
        "accounting_close_tasks",
        "period_locks",
        "hitl_tasks",
        "agent_suggestions",
        "documents",
        "bills",
        "invoices",
        "projects",
        "engagement_billing_terms",
        "engagements",
        "rate_card_lines",
        "rate_cards",
        "employees",
        "clients",
    ]:
        _best_effort_delete(db, table, tenant_id)
    _ok("Tenant operational records cleared")


def _owner_id(db: Client, tenant_id: str) -> str:
    rows = (
        db.table("tenant_users")
        .select("user_id")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    ).data or []
    return str(rows[0]["user_id"]) if rows else SYSTEM_USER_ID


def _account_map(db: Client, tenant_id: str) -> dict[str, str]:
    rows = db.table("accounts").select("id, code").eq("tenant_id", tenant_id).execute().data or []
    return {str(row["code"]): str(row["id"]) for row in rows}


def _ensure_rate_card(
    db: Client,
    *,
    tenant_id: str,
    name: str,
    currency: str,
    rates: dict[str, Decimal],
) -> str:
    existing = (
        db.table("rate_cards")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("name", name)
        .limit(1)
        .execute()
    ).data
    if existing:
        rate_card_id = existing[0]["id"]
    else:
        rate_card_id = (
            db.table("rate_cards")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "name": name,
                    "currency": currency,
                    "effective_date": "2026-01-01",
                }
            )
            .execute()
        ).data[0]["id"]

    db.table("rate_card_lines").delete().eq("tenant_id", tenant_id).eq("rate_card_id", rate_card_id).execute()
    db.table("rate_card_lines").insert(
        [
            {
                "tenant_id": tenant_id,
                "rate_card_id": rate_card_id,
                "role": role,
                "rate": _m(rate),
            }
            for role, rate in rates.items()
        ]
    ).execute()
    return rate_card_id


def _update_employee(
    db: Client,
    employee_id: str,
    *,
    practice_area: str,
    seniority: str,
    target: Decimal,
) -> None:
    db.table("employees").update(
        {
            "practice_area": practice_area,
            "seniority": seniority,
            "target_billable_utilization_pct": _m(target),
        }
    ).eq("id", employee_id).execute()


def _update_engagement(
    db: Client,
    engagement_id: str,
    *,
    total_value: Decimal | None = None,
    service_line: str,
    rate_card_id: str | None = None,
    description: str,
) -> None:
    patch: dict[str, object] = {
        "service_line": service_line,
        "description": description,
        "status": "active",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    if total_value is not None:
        patch["total_value"] = _m(total_value)
    if rate_card_id:
        patch["rate_card_id"] = rate_card_id
    db.table("engagements").update(patch).eq("id", engagement_id).execute()


def _update_terms(db: Client, engagement_id: str, **fields: object) -> None:
    payload = {k: (_m(v) if isinstance(v, Decimal) else v) for k, v in fields.items() if v is not None}
    if not payload:
        return
    db.table("engagement_billing_terms").update(payload).eq("engagement_id", engagement_id).execute()


def _assign(
    db: Client,
    *,
    tenant_id: str,
    project_id: str,
    employee_id: str,
    role: str,
    override_rate: Decimal | None = None,
) -> None:
    existing = (
        db.table("project_assignments")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("project_id", project_id)
        .eq("employee_id", employee_id)
        .limit(1)
        .execute()
    ).data
    payload = {
        "tenant_id": tenant_id,
        "project_id": project_id,
        "employee_id": employee_id,
        "role": role,
        "start_date": "2026-01-01",
        "override_rate": _m(override_rate) if override_rate is not None else None,
    }
    if existing:
        db.table("project_assignments").update(payload).eq("id", existing[0]["id"]).execute()
    else:
        db.table("project_assignments").insert(payload).execute()


def _seed_time(
    db: Client,
    *,
    tenant_id: str,
    project_id: str,
    employee_id: str,
    day: str,
    hours: str,
    description: str,
    billable: bool = True,
) -> None:
    db.table("time_entries").insert(
        {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "employee_id": employee_id,
            "date": day,
            "hours": hours,
            "description": description,
            "billable": billable,
            "billing_status": "unbilled" if billable else "non_billable",
            "timezone": "Europe/London",
        }
    ).execute()


def _create_hitl_task(
    db: Client,
    *,
    tenant_id: str,
    title: str,
    kind: str,
    priority: str,
    description: str,
    output: dict,
    payload: dict,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
) -> None:
    suggestion = (
        db.table("agent_suggestions")
        .insert(
            {
                "tenant_id": tenant_id,
                "agent_name": "atlas_demo_v2_seed",
                "action_type": kind,
                "input_snapshot": {"source": "Demo Guide v2 production seed"},
                "output_snapshot": output,
                "confidence": "0.91",
                "status": "pending",
                "hitl_required": True,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
            }
        )
        .execute()
    ).data[0]
    db.table("hitl_tasks").insert(
        {
            "tenant_id": tenant_id,
            "agent_suggestion_id": suggestion["id"],
            "kind": kind,
            "priority": priority,
            "title": title,
            "description": description,
            "payload": payload,
            "status": "open",
            "due_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        }
    ).execute()


def _create_document(
    db: Client,
    *,
    tenant_id: str,
    owner_id: str,
    filename: str,
    document_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> None:
    db.table("documents").insert(
        {
            "tenant_id": tenant_id,
            "uploader_id": owner_id,
            "document_type": document_type,
            "original_filename": filename,
            "storage_path": f"demo-v2/{tenant_id}/{filename}",
            "mime_type": "application/pdf",
            "file_size_bytes": 128000,
            "sha256": f"demo-v2-{filename}",
            "page_count": 4,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": "extracted",
        }
    ).execute()


def _post_manual_journal(
    db: Client,
    *,
    tenant_id: str,
    owner_id: str,
    entry_number: str,
    description: str,
    period: str,
    entry_date: str,
    lines: list[tuple[str, str, Decimal, str]],
    posted: bool,
) -> str:
    accounts = _account_map(db, tenant_id)
    je = (
        db.table("journal_entries")
        .insert(
            {
                "tenant_id": tenant_id,
                "entry_number": entry_number,
                "entry_type": "standard",
                "description": description,
                "entry_date": entry_date,
                "period": period,
                "reference_type": "manual",
                "created_by": owner_id,
                "posted_at": datetime.now(UTC).isoformat() if posted else None,
            }
        )
        .execute()
    ).data[0]
    rows = []
    for direction, account_code, amount, line_description in lines:
        account_id = accounts.get(account_code)
        if account_id:
            rows.append(
                {
                    "tenant_id": tenant_id,
                    "journal_entry_id": je["id"],
                    "direction": direction,
                    "account_id": account_id,
                    "amount": _m(amount),
                    "currency": "GBP",
                    "base_amount": _m(amount),
                    "description": line_description,
                }
            )
    if rows:
        db.table("journal_lines").insert(rows).execute()
    return str(je["id"])


def _seed_close_tasks(db: Client, *, tenant_id: str) -> None:
    tasks = [
        ("subledger_reconciliation", "Reconcile AR/AP subledgers", "done", "finance_manager", 10),
        ("wip_accrual_review", "Review accruals", "blocked", "finance_manager", 20),
        ("deferred_revenue_review", "Review deferred revenue release", "open", "finance_manager", 30),
        ("recurring_journal_review", "Review recurring journals", "open", "finance_manager", 35),
        ("trial_balance_review", "Review trial balance and close package", "open", "controller", 40),
        ("period_lock", "Lock accounting period", "blocked", "admin", 50),
    ]
    db.table("accounting_close_tasks").insert(
        [
            {
                "tenant_id": tenant_id,
                "period": JUNE,
                "code": code,
                "title": title,
                "description": f"Demo Guide v2 June close task: {title}.",
                "owner_role": owner,
                "status": status,
                "due_date": "2026-07-05",
                "evidence": {"demo": "Demo Guide v2", "period": JUNE},
                "order_index": order_index,
            }
            for code, title, status, owner, order_index in tasks
        ]
    ).execute()


def seed_demo_v2(tenant_id: str, reset: bool = False) -> None:
    db = _make_client()
    tenant_row = (
        db.table("tenants")
        .select("id, name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    ).data
    if not tenant_row:
        _fail(f"Tenant {tenant_id!r} not found.")
    print(f"\nSeeding Demo Guide v2 data into tenant: {tenant_row[0].get('name')} ({tenant_id})")

    _set_tenant(db, tenant_id)
    if reset:
        reset_demo_v2_data(db, tenant_id)
    owner_id = _owner_id(db, tenant_id)

    _section("1. Contacts")
    nexus = _ensure_client(db, tenant_id=tenant_id, name="Nexus Capital Partners LP", kind="customer", currency="GBP", billing_email="finance@nexus-capital.example")
    brightwater = _ensure_client(db, tenant_id=tenant_id, name="Brightwater Manufacturing Ltd", kind="customer", currency="GBP", billing_email="accounts@brightwater.example")
    forster = _ensure_client(db, tenant_id=tenant_id, name="Forster & Reid Ltd", kind="vendor", currency="GBP", billing_email="accounts@forsterreid.example")
    alderton = _ensure_client(db, tenant_id=tenant_id, name="Alderton Family Office", kind="both", currency="GBP", billing_email="office@alderton.example")
    thornton = _ensure_client(db, tenant_id=tenant_id, name="Thornton Tech Solutions Ltd", kind="customer", currency="USD", billing_email="finance@thorntontech.example")
    bt = _ensure_client(db, tenant_id=tenant_id, name="BT Broadband", kind="vendor", currency="GBP", billing_email="billing@bt.example")
    for label, item in [("Nexus", nexus), ("Brightwater", brightwater), ("Forster & Reid", forster), ("Alderton", alderton), ("Thornton", thornton), ("BT Broadband", bt)]:
        _ok(f"{label}: {item}")

    _section("2. People")
    marcus = _ensure_employee(db, tenant_id=tenant_id, first_name="Marcus", last_name="Chen", email="marcus.chen@meridianadvisory.example", title="Managing Partner", bill_rate=_d("350.00"), cost_rate=_d("180.00"), currency="GBP")
    sarah = _ensure_employee(db, tenant_id=tenant_id, first_name="Sarah", last_name="Williams", email="sarah.williams@meridianadvisory.example", title="Tax Director", bill_rate=_d("280.00"), cost_rate=_d("145.00"), currency="GBP")
    priya = _ensure_employee(db, tenant_id=tenant_id, first_name="Priya", last_name="Sharma", email="priya.sharma@meridianadvisory.example", title="Head of COSEC", bill_rate=_d("220.00"), cost_rate=_d("115.00"), currency="GBP")
    james = _ensure_employee(db, tenant_id=tenant_id, first_name="James", last_name="O'Brien", email="james.obrien@meridianadvisory.example", title="Payroll Manager", bill_rate=_d("180.00"), cost_rate=_d("95.00"), currency="GBP")
    alice = _ensure_employee(db, tenant_id=tenant_id, first_name="Alice", last_name="Chen", email="alice.chen@meridianadvisory.example", title="Senior Consultant", bill_rate=_d("250.00"), cost_rate=_d("120.00"), currency="GBP")
    _update_employee(db, marcus, practice_area="advisory", seniority="partner", target=_d("65.00"))
    _update_employee(db, sarah, practice_area="tax", seniority="director", target=_d("75.00"))
    _update_employee(db, priya, practice_area="cosec", seniority="manager", target=_d("70.00"))
    _update_employee(db, james, practice_area="payroll", seniority="manager", target=_d("70.00"))
    _update_employee(db, alice, practice_area="accounting", seniority="senior", target=_d("72.00"))
    _ok("Seeded Marcus, Sarah, Priya, James, and Alice")

    _section("3. Rate cards and engagements")
    gbp_rates = _ensure_rate_card(
        db,
        tenant_id=tenant_id,
        name="Meridian 2026 GBP Rate Card",
        currency="GBP",
        rates={
            "Managing Partner": _d("350.00"),
            "Tax Director": _d("280.00"),
            "COSEC Manager": _d("220.00"),
            "Payroll Manager": _d("180.00"),
            "Senior Consultant": _d("250.00"),
        },
    )
    usd_rates = _ensure_rate_card(
        db,
        tenant_id=tenant_id,
        name="Meridian 2026 USD Rate Card",
        currency="USD",
        rates={"Partner": _d("475.00"), "Senior Consultant": _d("325.00"), "COSEC Manager": _d("285.00")},
    )

    nexus_group = _ensure_engagement(db, tenant_id=tenant_id, client_id=nexus, name="Nexus Capital Partners - Group Accounting & Advisory", billing_arrangement="mixed", currency="GBP")
    _update_engagement(db, nexus_group, total_value=_d("156000.00"), service_line="accounting", rate_card_id=gbp_rates, description="Mixed fixed-fee consolidation, monthly management accounts retainer, and CFO advisory T&M.")
    _update_terms(db, nexus_group, fixed_fee_amount=_d("48000.00"), retainer_monthly_amount=_d("9000.00"), billing_unit="hour", unit_label="advisory hour", unit_price=_d("350.00"))

    nexus_tax = _ensure_engagement(db, tenant_id=tenant_id, client_id=nexus, name="Nexus Corporation Tax Return FY2025", billing_arrangement="capped_tm", currency="GBP")
    _update_engagement(db, nexus_tax, total_value=_d("22000.00"), service_line="tax", rate_card_id=gbp_rates, description="Fixed-fee corporation tax return with advisory overrun capped.")
    _update_terms(db, nexus_tax, fixed_fee_amount=_d("18500.00"), cap_amount=_d("22000.00"), billing_unit="hour", unit_label="tax advisory hour", unit_price=_d("280.00"))

    bright_retainer = _ensure_engagement(db, tenant_id=tenant_id, client_id=brightwater, name="Brightwater - Monthly Management Accounts", billing_arrangement="retainer", currency="GBP", monthly_amount=_d("4500.00"))
    _update_engagement(db, bright_retainer, total_value=_d("54000.00"), service_line="accounting", rate_card_id=gbp_rates, description="Monthly management accounts retainer for Brightwater.")
    bright_annual = _ensure_engagement(db, tenant_id=tenant_id, client_id=brightwater, name="Brightwater - Annual Statutory Accounts + CT600 FY2025", billing_arrangement="milestone", currency="GBP")
    _update_engagement(db, bright_annual, total_value=_d("28000.00"), service_line="tax", rate_card_id=gbp_rates, description="Annual accounts and CT600 milestone engagement.")
    _update_terms(db, bright_annual, milestone_total=_d("28000.00"), billing_unit="milestone", unit_label="statutory accounts milestone", unit_price=_d("7000.00"), unit_quantity=_d("4.00"))
    bright_payroll = _ensure_engagement(db, tenant_id=tenant_id, client_id=brightwater, name="Brightwater - Payroll Bureau", billing_arrangement="fixed_fee", currency="GBP")
    _update_engagement(db, bright_payroll, total_value=_d("18360.00"), service_line="payroll", rate_card_id=gbp_rates, description="Payroll billing at GBP 8.50 per active employee per month.")
    _update_terms(db, bright_payroll, fixed_fee_amount=_d("1530.00"), billing_unit="per_employee", unit_label="active employee", unit_quantity=_d("180.00"), unit_price=_d("8.50"))

    alderton_advisory = _ensure_engagement(db, tenant_id=tenant_id, client_id=alderton, name="Alderton Family Office - Advisory Retainer", billing_arrangement="retainer", currency="GBP", monthly_amount=_d("12500.00"))
    _update_engagement(db, alderton_advisory, total_value=_d("150000.00"), service_line="advisory", rate_card_id=gbp_rates, description="Private wealth advisory retainer across family entities.")
    alderton_trust = _ensure_engagement(db, tenant_id=tenant_id, client_id=alderton, name="Alderton Trust (1985) - Trust Accounts & Tax", billing_arrangement="fixed_fee", currency="GBP")
    _update_engagement(db, alderton_trust, total_value=_d("12500.00"), service_line="tax", rate_card_id=gbp_rates, description="Trust accounts and tax work, including SGD dividend income review.")
    _update_terms(db, alderton_trust, fixed_fee_amount=_d("12500.00"))
    alderton_cosec = _ensure_engagement(db, tenant_id=tenant_id, client_id=alderton, name="Alderton COSEC Retainer - All Entities", billing_arrangement="retainer", currency="GBP", monthly_amount=_d("3200.00"))
    _update_engagement(db, alderton_cosec, total_value=_d("38400.00"), service_line="cosec", rate_card_id=gbp_rates, description="COSEC retainer covering 12 Alderton entities.")

    thornton_accounting = _ensure_engagement(db, tenant_id=tenant_id, client_id=thornton, name="Thornton Tech - Accounting & Advisory FY2026", billing_arrangement="retainer", currency="USD", monthly_amount=_d("4500.00"))
    _update_engagement(db, thornton_accounting, total_value=_d("54000.00"), service_line="accounting", rate_card_id=usd_rates, description="USD-billed accounting and advisory retainer.")
    thornton_series_a = _ensure_engagement(db, tenant_id=tenant_id, client_id=thornton, name="Thornton Tech - Series A Tax Structuring", billing_arrangement="milestone", currency="USD")
    _update_engagement(db, thornton_series_a, total_value=_d("106500.00"), service_line="tax", rate_card_id=usd_rates, description="Series A success-fee milestone at 0.75 percent of funds raised.")
    _update_terms(db, thornton_series_a, milestone_total=_d("106500.00"), billing_unit="milestone", unit_label="success fee", unit_price=_d("106500.00"), unit_quantity=_d("1.00"))
    thornton_cosec = _ensure_engagement(db, tenant_id=tenant_id, client_id=thornton, name="Thornton Tech - COSEC Filings", billing_arrangement="time_and_materials", currency="GBP")
    _update_engagement(db, thornton_cosec, total_value=_d("3500.00"), service_line="cosec", rate_card_id=gbp_rates, description="Event-based UK company secretarial filings.")
    _ok("Seeded Meridian engagements")

    _section("4. Projects and delivery data")
    nexus_cfo = _ensure_project(db, tenant_id=tenant_id, engagement_id=nexus_group, name="Nexus CFO Advisory", currency="GBP")
    _ensure_project(db, tenant_id=tenant_id, engagement_id=nexus_group, name="Nexus Group Consolidation FY2025", currency="GBP")
    _ensure_project(db, tenant_id=tenant_id, engagement_id=nexus_group, name="Nexus Monthly Management Accounts", currency="GBP")
    bright_mgmt = _ensure_project(db, tenant_id=tenant_id, engagement_id=bright_retainer, name="Brightwater Monthly Management Accounts", currency="GBP")
    bright_accounts = _ensure_project(db, tenant_id=tenant_id, engagement_id=bright_annual, name="Brightwater Annual Accounts FY2025", currency="GBP")
    alderton_tax = _ensure_project(db, tenant_id=tenant_id, engagement_id=alderton_trust, name="Alderton Trust 1985 Accounts & Tax", currency="GBP")
    alderton_cosec_project = _ensure_project(db, tenant_id=tenant_id, engagement_id=alderton_cosec, name="Alderton COSEC Filings", currency="GBP")
    thornton_usd = _ensure_project(db, tenant_id=tenant_id, engagement_id=thornton_accounting, name="Thornton USD Advisory", currency="USD")
    thornton_cosec_project = _ensure_project(db, tenant_id=tenant_id, engagement_id=thornton_cosec, name="Thornton COSEC Filings", currency="GBP")
    for project_id, employee_id, role, rate in [
        (nexus_cfo, marcus, "Managing Partner", _d("350.00")),
        (nexus_cfo, alice, "Senior Consultant", _d("250.00")),
        (bright_mgmt, alice, "Senior Consultant", _d("250.00")),
        (bright_accounts, sarah, "Tax Director", _d("280.00")),
        (alderton_tax, sarah, "Tax Director", _d("280.00")),
        (alderton_cosec_project, priya, "COSEC Manager", _d("220.00")),
        (thornton_usd, marcus, "Partner", _d("475.00")),
        (thornton_cosec_project, priya, "COSEC Manager", _d("220.00")),
    ]:
        _assign(db, tenant_id=tenant_id, project_id=project_id, employee_id=employee_id, role=role, override_rate=rate)

    for payload in [
        (nexus_cfo, alice, "2026-06-04", "4.50", "Board pack review and cash flow modelling"),
        (nexus_cfo, alice, "2026-06-12", "4.50", "Investor KPI bridge and cash runway update"),
        (nexus_cfo, alice, "2026-06-18", "2.00", "Internal planning and scope notes", False),
        (bright_mgmt, alice, "2026-06-07", "8.00", "Monthly management accounts preparation"),
        (alderton_tax, alice, "2026-06-09", "5.00", "Trust accounts schedules and dividend evidence"),
        (bright_accounts, sarah, "2026-06-11", "16.00", "CT600 review and statutory accounts evidence"),
        (alderton_cosec_project, priya, "2026-06-17", "10.00", "Confirmation statement and register review"),
    ]:
        if len(payload) == 5:
            project_id, employee_id, day, hours, description = payload
            billable = True
        else:
            project_id, employee_id, day, hours, description, billable = payload
        _seed_time(db, tenant_id=tenant_id, project_id=project_id, employee_id=employee_id, day=day, hours=hours, description=description, billable=billable)

    db.table("project_expenses").insert(
        {
            "tenant_id": tenant_id,
            "project_id": nexus_cfo,
            "employee_id": alice,
            "description": "Client travel receipt - Nexus CFO Advisory",
            "amount": "185.50",
            "currency": "GBP",
            "base_amount": "185.50",
            "expense_date": "2026-06-14",
            "category": "travel",
            "billable": True,
            "billing_status": "unbilled",
            "reimbursable": True,
        }
    ).execute()
    _ok("Seeded projects, time entries, and billable expense")

    _section("5. AR invoices and payments")
    inv1001 = _create_invoice(db, tenant_id=tenant_id, engagement_id=nexus_group, client_id=nexus, invoice_number="INV-1001", currency="GBP", issue_date="2026-05-20", due_date="2026-06-19", lines=[{"description": "Nexus monthly management accounts retainer - May 2026", "quantity": "1", "unit_price": "9000.00", "amount": "9000.00"}])
    _approve_invoice(db, tenant_id, inv1001)
    _send_invoice(db, inv1001)
    inv1002 = _create_invoice(db, tenant_id=tenant_id, engagement_id=bright_retainer, client_id=brightwater, invoice_number="INV-1002", currency="GBP", issue_date="2026-06-25", due_date="2026-07-25", lines=[{"description": "Brightwater June 2026 monthly management accounts retainer", "quantity": "1", "unit_price": "4500.00", "amount": "4500.00"}])
    _approve_invoice(db, tenant_id, inv1002)
    _send_invoice(db, inv1002)
    inv1003 = _create_invoice(db, tenant_id=tenant_id, engagement_id=thornton_accounting, client_id=thornton, invoice_number="INV-1003", currency="USD", issue_date="2026-06-10", due_date="2026-07-10", lines=[{"description": "Thornton June USD advisory retainer", "quantity": "1", "unit_price": "4500.00", "amount": "4500.00"}])
    _approve_invoice(db, tenant_id, inv1003)
    _send_invoice(db, inv1003)
    _pay_invoice(db, tenant_id, inv1003, _d("4500.00"), "USD")
    _ok("Seeded INV-1001, INV-1002, INV-1003")

    _section("6. AP bills and payment controls")
    bill1001 = _create_bill(db, tenant_id=tenant_id, client_id=forster, bill_number="BILL-1001", currency="GBP", issue_date="2026-06-15", due_date="2026-07-05", vendor_invoice_number="FR-2026-0615", lines=[{"description": "Senior technical accounting support - Brightwater Annual Accounts FY2025", "quantity": "16", "unit_price": "200.00", "amount": "3200.00"}])
    _approve_bill(db, tenant_id, bill1001)
    bill1002 = _create_bill(db, tenant_id=tenant_id, client_id=bt, bill_number="BILL-1002", currency="GBP", issue_date="2026-06-20", due_date="2026-07-01", vendor_invoice_number="BT-2026-0620", lines=[{"description": "Broadband service for June 2026", "quantity": "1", "unit_price": "189.00", "amount": "189.00"}])
    _approve_bill(db, tenant_id, bill1002)
    _create_hitl_task(
        db,
        tenant_id=tenant_id,
        title="Review payment batch: Forster & Reid and BT Broadband",
        kind="create_bill_payment_batch",
        priority="high",
        description="Demo Guide v2 payment batch containing approved bills due in the next 10 days.",
        output={"bill_numbers": ["BILL-1001", "BILL-1002"], "total": "3389.00", "currency": "GBP", "cash_impact": "Pay from operating account after controller approval."},
        payload={"bill_ids": [bill1001, bill1002], "bill_numbers": ["BILL-1001", "BILL-1002"], "total": "3389.00", "currency": "GBP"},
        related_entity_type="bill",
        related_entity_id=bill1001,
    )
    _ok("Seeded BILL-1001, BILL-1002, and payment approval Inbox item")

    _section("7. Documents, HITL, close, and journals")
    _create_document(db, tenant_id=tenant_id, owner_id=owner_id, filename="nexus_engagement_letter.pdf", document_type="engagement_letter", entity_type="engagement", entity_id=nexus_group)
    _create_document(db, tenant_id=tenant_id, owner_id=owner_id, filename="brightwater_subcontractor_invoice.pdf", document_type="vendor_invoice", entity_type="bill", entity_id=bill1001)
    _create_document(db, tenant_id=tenant_id, owner_id=owner_id, filename="alderton_sgd_dividend_notice.pdf", document_type="dividend_notice", entity_type="journal", entity_id=None)
    _create_document(db, tenant_id=tenant_id, owner_id=owner_id, filename="thornton_cosec_instruction.pdf", document_type="cosec_instruction", entity_type="project", entity_id=thornton_cosec_project)
    _create_hitl_task(
        db,
        tenant_id=tenant_id,
        title="Review Nexus engagement letter extraction",
        kind="engagement_onboarding_review",
        priority="high",
        description="Nexus engagement letter extracted as mixed billing: fixed fee, retainer, and T&M advisory.",
        output={"client_name": "Nexus Capital Partners LP", "billing_arrangement": "mixed", "fixed_fee_amount": "48000.00", "retainer_monthly_amount": "9000.00", "rate_card": "Meridian 2026 GBP Rate Card"},
        payload={"client_id": nexus, "engagement_id": nexus_group, "billing_arrangement": "mixed"},
        related_entity_type="engagement",
        related_entity_id=nexus_group,
    )
    _create_hitl_task(
        db,
        tenant_id=tenant_id,
        title="Review June 2026 month-end close package",
        kind="copilot_prepare_month_end_close",
        priority="high",
        description="June close has WIP accrual review and period-lock blockers requiring Controller review.",
        output={"period": JUNE, "blockers": ["wip_accrual_review", "period_lock"], "trial_balance_status": "balanced"},
        payload={"period": JUNE, "required_role": "controller"},
    )
    _seed_close_tasks(db, tenant_id=tenant_id)
    _post_manual_journal(
        db,
        tenant_id=tenant_id,
        owner_id=owner_id,
        entry_number="DEMO-JE-ALDERTON-SGD",
        description="Alderton Trust SGD dividend income accrual, GBP base currency",
        period=JUNE,
        entry_date="2026-06-21",
        lines=[("DR", "1100", _d("10440.00"), "Dividend cash receivable"), ("CR", "4000", _d("10440.00"), "Dividend income")],
        posted=False,
    )
    posted_manual = _post_manual_journal(
        db,
        tenant_id=tenant_id,
        owner_id=owner_id,
        entry_number="DEMO-JE-MANUAL-001",
        description="Manual accrual posted for reversal demonstration",
        period=JUNE,
        entry_date="2026-06-24",
        lines=[("DR", "5000", _d("750.00"), "Accrued professional expense"), ("CR", "2000", _d("750.00"), "Accrued AP")],
        posted=True,
    )
    _create_hitl_task(
        db,
        tenant_id=tenant_id,
        title="Review manual journal reversal packet",
        kind="manual_journal_reversal_review",
        priority="med",
        description="Reversal packet for DEMO-JE-MANUAL-001 awaits Controller approval.",
        output={"original_entry_number": "DEMO-JE-MANUAL-001", "reversal_date": "2026-07-01", "creates_new_journal": True},
        payload={"journal_entry_id": posted_manual, "period": JUNE},
        related_entity_type="journal",
        related_entity_id=posted_manual,
    )
    try:
        db.table("period_locks").insert(
            {
                "tenant_id": tenant_id,
                "period": "2026-05",
                "locked_by": owner_id,
                "locked_at": datetime.now(UTC).isoformat(),
            }
        ).execute()
    except Exception:
        pass
    _ok("Seeded source documents, Inbox items, close tasks, and manual journals")

    print("\n" + "=" * 64)
    print("Demo Guide v2 data seeded successfully")
    print("=" * 64)
    print(
        f"""
Tenant: {tenant_id}
Created:
  - 6 contacts and 5 Meridian employees
  - 10 engagements across O2C, P2P support, R2R, COSEC, payroll, and tax
  - 9 projects with assignments, WIP, and one billable expense
  - 3 invoices including INV-1001 and a paid USD Thornton invoice
  - 2 approved vendor bills including BILL-1001
  - 4 source document records, 4 Inbox review tasks, June close tasks, and manual journals

Next:
  Run the Demo Guide v2 browser validation against production.
"""
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Demo Guide v2 Meridian data.")
    parser.add_argument("--tenant-id", required=True, metavar="UUID")
    parser.add_argument("--reset", action="store_true", default=False)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        uuid.UUID(args.tenant_id)
    except ValueError:
        _fail(f"--tenant-id must be a valid UUID, got: {args.tenant_id!r}")
    try:
        seed_demo_v2(args.tenant_id, reset=args.reset)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\nFATAL: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
