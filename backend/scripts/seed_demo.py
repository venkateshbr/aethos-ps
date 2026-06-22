"""Demo seed script — populates a clean tenant with realistic demo data.

Usage::

    uv run python -m scripts.seed_demo --tenant-id <uuid>
    uv run python -m scripts.seed_demo --tenant-id <uuid> --reset

The script is safe to re-run when ``--reset`` is supplied: it deletes all
``INV-TEST-*`` / ``BILL-TEST-*`` prefixed documents, the two demo employees,
and the four demo contacts before re-seeding.

All monetary values use ``decimal.Decimal`` — never ``float``.
Money is serialised to strings when writing to Supabase (NUMERIC(15,2) via
the PostgREST JSON bridge).

FK dependency order (must be created in this sequence)
-------------------------------------------------------
1. tenants row must already exist (provided by --tenant-id)
2. Clients (contacts) — no upstream FK
3. Employees           — no upstream FK
4. Engagements         — FK → clients
5. engagement_billing_terms — FK → engagements
6. Projects            — FK → engagements
7. Time entries        — FK → projects + employees
8. Invoices            — FK → engagements + clients
9. Invoice lines       — FK → invoices
10. Invoice lifecycle  — approve → send → pay (manual payment)
11. Bills              — FK → clients
12. Bill lines         — FK → bills
13. Bill approval      — post GL journal

Journal posting is skipped when ``app.current_tenant_id`` cannot be set via
service-role client (e.g. a freshly provisioned tenant without COA accounts).
In that case the script prints a warning and continues — demo data is still
useful without GL entries.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

# ---------------------------------------------------------------------------
# Bootstrap: ensure SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are set before
# importing supabase so the client is built with real credentials.
# ---------------------------------------------------------------------------

# Bug #96 workaround: drop shell-mangled list-typed env vars before importing
# app.core.config so pydantic-settings reads from .env directly.
for _k in ("AGENT_MODELS", "CORS_ORIGINS"):
    os.environ.pop(_k, None)

from supabase import Client, create_client  # noqa: E402 — must follow env pop

# ---------------------------------------------------------------------------
# Money helpers (inline to avoid importing the full app domain)
# ---------------------------------------------------------------------------

TWO_PLACES = Decimal("0.01")


def _d(value: str | int | float) -> Decimal:
    """Convert to Decimal quantised to 2dp. Never use float arithmetic directly."""
    return Decimal(str(value)).quantize(TWO_PLACES)


def _m(value: Decimal) -> str:
    """Serialise money to 2dp string for Supabase JSON (NUMERIC(15,2))."""
    return str(value.quantize(TWO_PLACES))


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------


def _make_client() -> Client:
    url = os.environ.get("SUPABASE_URL") or ""
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        _fail(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.\n"
            "Copy backend/.env and source it, or export these vars before running."
        )
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"  {msg}")


def _section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def _set_tenant(db: Client, tenant_id: str) -> None:
    """Set app.current_tenant_id so RLS policies pass for the service-role client."""
    # service-role already bypasses RLS; no need to set auth token
    try:
        db.rpc("set_config", {"setting": "app.current_tenant_id", "value": tenant_id}).execute()
    except Exception:
        # Older Supabase versions may not expose set_config as an RPC.
        # Fall back: the service-role client bypasses RLS anyway.
        pass


def _today() -> str:
    return date.today().isoformat()


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


# ---------------------------------------------------------------------------
# Reset — deletes demo-prefixed data for this tenant
# ---------------------------------------------------------------------------


def reset_demo_data(db: Client, tenant_id: str) -> None:
    _section("Resetting existing demo data")

    # Delete in reverse FK order to avoid constraint violations.

    # 0. HITL tasks + agent_suggestions linked to demo bills
    bill_rows_pre = (
        db.table("bills")
        .select("id")
        .eq("tenant_id", tenant_id)
        .like("bill_number", "BILL-TEST-%")
        .execute()
    ).data or []
    bill_ids_pre = [r["id"] for r in bill_rows_pre]
    if bill_ids_pre:
        # hitl_tasks that reference these bills via payload or agent_suggestion
        sug_rows = (
            db.table("agent_suggestions")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("related_entity_type", "bill")
            .in_("related_entity_id", bill_ids_pre)
            .execute()
        ).data or []
        sug_ids = [r["id"] for r in sug_rows]
        if sug_ids:
            db.table("hitl_tasks").delete().in_("agent_suggestion_id", sug_ids).execute()
            db.table("agent_suggestions").delete().in_("id", sug_ids).execute()
            _ok(f"Deleted {len(sug_ids)} agent_suggestion(s) and hitl_task(s) for demo bills")

    # 1. Payments linked to demo invoices
    invoice_rows = (
        db.table("invoices")
        .select("id")
        .eq("tenant_id", tenant_id)
        .like("invoice_number", "INV-TEST-%")
        .execute()
    ).data or []
    inv_ids = [r["id"] for r in invoice_rows]
    if inv_ids:
        db.table("payments").delete().in_("invoice_id", inv_ids).execute()
        _ok(f"Deleted payments for {len(inv_ids)} demo invoice(s)")

    # 2. Invoice lines → invoices
    if inv_ids:
        db.table("invoice_lines").delete().in_("invoice_id", inv_ids).execute()
        db.table("invoices").delete().in_("id", inv_ids).execute()
        _ok(f"Deleted {len(inv_ids)} demo invoice(s) and their lines")

    # 3. Bill lines → bills
    bill_rows = (
        db.table("bills")
        .select("id")
        .eq("tenant_id", tenant_id)
        .like("bill_number", "BILL-TEST-%")
        .execute()
    ).data or []
    bill_ids = [r["id"] for r in bill_rows]
    if bill_ids:
        db.table("bill_lines").delete().in_("bill_id", bill_ids).execute()
        db.table("bills").delete().in_("id", bill_ids).execute()
        _ok(f"Deleted {len(bill_ids)} demo bill(s) and their lines")

    # 4. Time entries + project expenses under demo projects
    project_rows = (
        db.table("projects")
        .select("id")
        .eq("tenant_id", tenant_id)
        .in_("name", ["Phase 1 — Discovery [DEMO]", "Advisory Services [DEMO]"])
        .execute()
    ).data or []
    proj_ids = [r["id"] for r in project_rows]
    if proj_ids:
        db.table("time_entries").delete().in_("project_id", proj_ids).eq("tenant_id", tenant_id).execute()
        db.table("project_expenses").delete().in_("project_id", proj_ids).eq("tenant_id", tenant_id).execute()
        _ok(f"Deleted time entries and project expenses under {len(proj_ids)} demo project(s)")

    # 5. Projects under demo engagements
    eng_rows = (
        db.table("engagements")
        .select("id")
        .eq("tenant_id", tenant_id)
        .in_("name", ["Digital Transformation [DEMO]", "Annual Advisory Retainer [DEMO]"])
        .execute()
    ).data or []
    eng_ids = [r["id"] for r in eng_rows]
    if eng_ids:
        db.table("projects").delete().in_("engagement_id", eng_ids).execute()
        db.table("engagement_billing_terms").delete().in_("engagement_id", eng_ids).execute()
        db.table("engagements").delete().in_("id", eng_ids).execute()
        _ok(f"Deleted {len(eng_ids)} demo engagement(s) and their projects")

    # 6. Demo employees (matched by email suffix)
    emp_rows = (
        db.table("employees")
        .select("id")
        .eq("tenant_id", tenant_id)
        .in_("email", ["alice.chen@demo.aethos.app", "bob.martinez@demo.aethos.app"])
        .execute()
    ).data or []
    if emp_rows:
        emp_ids = [r["id"] for r in emp_rows]
        db.table("employees").delete().in_("id", emp_ids).execute()
        _ok(f"Deleted {len(emp_ids)} demo employee(s)")

    # 7. Demo clients/contacts (matched by name)
    demo_client_names = [
        "Acme Corp [DEMO]",
        "Blackwood Consulting [DEMO]",
        "CloudPeak Systems [DEMO]",
        "Apex Staffing Ltd [DEMO]",
    ]
    db.table("clients").delete().in_("name", demo_client_names).eq("tenant_id", tenant_id).execute()
    _ok("Deleted demo contacts")

    # 8. Previous-month period lock (if seeded by this script)
    today = date.today()
    first_of_this_month = today.replace(day=1)
    last_month = first_of_this_month - timedelta(days=1)
    prev_period = last_month.strftime("%Y-%m")
    db.table("period_locks").delete().eq("tenant_id", tenant_id).eq("period", prev_period).execute()
    _ok(f"Removed period lock for {prev_period} (if present)")


# ---------------------------------------------------------------------------
# Seed helpers — each returns the created row's id
# ---------------------------------------------------------------------------


def _ensure_client(
    db: Client,
    *,
    tenant_id: str,
    name: str,
    kind: str,
    currency: str,
    billing_email: str,
) -> str:
    """Insert a client, skipping if it already exists (idempotent without --reset)."""
    existing = (
        db.table("clients")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("name", name)
        .limit(1)
        .execute()
    ).data
    if existing:
        return existing[0]["id"]

    res = (
        db.table("clients")
        .insert(
            {
                "tenant_id": tenant_id,
                "name": name,
                "kind": kind,
                "currency": currency,
                "billing_email": billing_email,
                "payment_terms_days": 30,
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _ensure_employee(
    db: Client,
    *,
    tenant_id: str,
    first_name: str,
    last_name: str,
    email: str,
    title: str,
    bill_rate: Decimal,
    cost_rate: Decimal,
    currency: str = "USD",
) -> str:
    existing = (
        db.table("employees")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("email", email)
        .limit(1)
        .execute()
    ).data
    if existing:
        return existing[0]["id"]

    res = (
        db.table("employees")
        .insert(
            {
                "tenant_id": tenant_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "title": title,
                "employment_type": "full_time",
                "default_bill_rate": _m(bill_rate),
                "default_bill_rate_currency": currency,
                "cost_rate": _m(cost_rate),
                "available_hours_per_week": "40.00",
                "status": "active",
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _ensure_engagement(
    db: Client,
    *,
    tenant_id: str,
    client_id: str,
    name: str,
    billing_arrangement: str,
    currency: str,
    monthly_amount: Decimal | None = None,
) -> str:
    existing = (
        db.table("engagements")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("name", name)
        .limit(1)
        .execute()
    ).data
    if existing:
        return existing[0]["id"]

    res = (
        db.table("engagements")
        .insert(
            {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "name": name,
                "billing_arrangement": billing_arrangement,
                "status": "active",
                "start_date": _days_ago(60),
                "currency": currency,
            }
        )
        .execute()
    )
    eng_id = res.data[0]["id"]

    # 1:1 billing_terms row
    billing_terms: dict = {
        "engagement_id": eng_id,
        "tenant_id": tenant_id,
    }
    if billing_arrangement == "retainer" and monthly_amount is not None:
        billing_terms["retainer_monthly_amount"] = _m(monthly_amount)

    try:
        db.table("engagement_billing_terms").insert(billing_terms).execute()
    except Exception as exc:
        # May already exist via DB trigger; ignore duplicate key errors.
        if "duplicate" not in str(exc).lower() and "conflict" not in str(exc).lower():
            raise

    return eng_id


def _ensure_project(
    db: Client,
    *,
    tenant_id: str,
    engagement_id: str,
    name: str,
    currency: str,
) -> str:
    existing = (
        db.table("projects")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("name", name)
        .limit(1)
        .execute()
    ).data
    if existing:
        return existing[0]["id"]

    res = (
        db.table("projects")
        .insert(
            {
                "tenant_id": tenant_id,
                "engagement_id": engagement_id,
                "name": name,
                "status": "active",
                "currency": currency,
                "budget_hours": "400.00",
                "budget": "80000.00",
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _seed_time_entry(
    db: Client,
    *,
    tenant_id: str,
    project_id: str,
    employee_id: str,
    entry_date: str,
    hours: Decimal,
    description: str,
    billable: bool,
    bill_rate: Decimal,  # kept for caller convenience; not stored on the row
) -> str:
    res = (
        db.table("time_entries")
        .insert(
            {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "employee_id": employee_id,
                "date": entry_date,
                "hours": _m(hours),
                "description": description,
                "billable": billable,
                "billing_status": "unbilled" if billable else "non_billable",
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _seed_project_expense(
    db: Client,
    *,
    tenant_id: str,
    project_id: str,
    employee_id: str,
    description: str,
    amount: Decimal,
    currency: str,
    expense_date: str,
    category: str,
    billable: bool = True,
) -> str:
    """Insert a project expense; returns the created row's id."""
    res = (
        db.table("project_expenses")
        .insert(
            {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "employee_id": employee_id,
                "description": description,
                "amount": _m(amount),
                "currency": currency,
                "base_amount": _m(amount),  # USD-only demo; base = foreign
                "expense_date": expense_date,
                "category": category,
                "billable": billable,
                "billing_status": "unbilled" if billable else "non_billable",
                "reimbursable": True,
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def _seed_period_lock(db: Client, tenant_id: str) -> None:
    """Lock the previous calendar month so the Reports → Period Locks demo works."""
    today = date.today()
    # First day of previous month
    first_of_this_month = today.replace(day=1)
    last_month = first_of_this_month - timedelta(days=1)
    period = last_month.strftime("%Y-%m")  # e.g. "2026-05"

    existing = (
        db.table("period_locks")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("period", period)
        .execute()
    ).data
    if existing:
        _ok(f"Period lock for {period} already exists — skipping")
        return

    db.table("period_locks").insert(
        {
            "tenant_id": tenant_id,
            "period": period,
            "locked_by": "00000000-0000-0000-0000-000000000000",
            "locked_at": datetime.now(UTC).isoformat(),
        }
    ).execute()
    _ok(f"Period locked: {period} (previous month)")


def _seed_bill_hitl(
    db: Client,
    *,
    tenant_id: str,
    bill_id: str,
    bill_number: str,
    client_name: str,
    total_amount: str,
    currency: str,
) -> None:
    """Create an agent_suggestion + hitl_task for the CloudPeak draft bill.

    This simulates the Inbox extraction flow so Scenario B can be demonstrated
    without needing to re-upload a PDF.
    """
    # 1. agent_suggestion (immutable AI output)
    suggestion = (
        db.table("agent_suggestions")
        .insert(
            {
                "tenant_id": tenant_id,
                "agent_name": "bill_extractor_agent",
                "action_type": "extract_bill",
                "input_snapshot": {
                    "document_type": "vendor_invoice",
                    "filename": "cloudpeak-invoice-CP-INV-2024-0892.pdf",
                },
                "output_snapshot": {
                    "vendor_name": client_name,
                    "vendor_invoice_number": "CP-INV-2024-0892",
                    "currency": currency,
                    "total": total_amount,
                    "line_items": [
                        {
                            "description": "Cloud compute — monthly usage",
                            "amount": "1800.00",
                        },
                        {
                            "description": "Blob storage — monthly usage",
                            "amount": "540.00",
                        },
                    ],
                    "due_date": (date.today() + timedelta(days=27)).isoformat(),
                    "notes": "No duplicate found for invoice CP-INV-2024-0892",
                },
                "confidence": "0.94",
                "status": "pending",
                "hitl_required": True,
                "related_entity_type": "bill",
                "related_entity_id": bill_id,
            }
        )
        .execute()
    ).data[0]
    suggestion_id = suggestion["id"]

    # 2. hitl_task — shows in Inbox as an open item
    db.table("hitl_tasks").insert(
        {
            "tenant_id": tenant_id,
            "agent_suggestion_id": suggestion_id,
            "kind": "bill_extract_review",
            "priority": "med",
            "title": f"Review extracted bill: {client_name} — {currency} {total_amount}",
            "description": (
                f"The bill extractor agent extracted vendor invoice CP-INV-2024-0892 "
                f"from CloudPeak Systems ({currency} {total_amount}). "
                f"Confidence: 94%. Review the line items and approve to post to AP."
            ),
            "payload": {
                "bill_id": bill_id,
                "bill_number": bill_number,
                "vendor_name": client_name,
                "total": total_amount,
                "currency": currency,
                "suggestion_id": suggestion_id,
            },
            "status": "open",
            "due_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        }
    ).execute()
    _ok(
        f"HITL task + agent_suggestion created for {bill_number} "
        f"(kind=bill_extract_review, confidence=94%, status=open)"
    )


def _create_invoice(
    db: Client,
    *,
    tenant_id: str,
    engagement_id: str,
    client_id: str,
    invoice_number: str,
    currency: str,
    issue_date: str,
    due_date: str,
    lines: list[dict],
) -> str:
    """Insert an invoice with explicit invoice_number (trigger skips auto-assign when provided)."""
    subtotal = sum(_d(ln["amount"]) for ln in lines)
    total = subtotal  # no tax for demo

    res = (
        db.table("invoices")
        .insert(
            {
                "tenant_id": tenant_id,
                "engagement_id": engagement_id,
                "client_id": client_id,
                "invoice_number": invoice_number,
                "currency": currency,
                "subtotal": _m(subtotal),
                "tax_total": "0.00",
                "total": _m(total),
                "status": "draft",
                "issue_date": issue_date,
                "due_date": due_date,
            }
        )
        .execute()
    )
    invoice_id = res.data[0]["id"]

    # Insert lines
    for ln in lines:
        db.table("invoice_lines").insert(
            {
                "tenant_id": tenant_id,
                "invoice_id": invoice_id,
                "description": ln["description"],
                "quantity": str(ln.get("quantity", "1")),
                "unit_price": _m(_d(ln["unit_price"])),
                "amount": _m(_d(ln["amount"])),
                "tax_amount": "0.00",
            }
        ).execute()

    return invoice_id


def _approve_invoice(db: Client, tenant_id: str, invoice_id: str) -> None:
    """Move invoice to approved and post AR journal (DR 1200 / CR 4000)."""
    row = db.table("invoices").select("*").eq("id", invoice_id).execute().data[0]
    total = _d(row["total"])
    currency = row["currency"]
    invoice_number = row["invoice_number"]
    entry_date = row.get("issue_date") or _today()

    # Resolve account IDs
    acct_rows = (
        db.table("accounts")
        .select("id, code")
        .eq("tenant_id", tenant_id)
        .in_("code", ["1200", "4000"])
        .execute()
    ).data or []
    acct_map = {r["code"]: r["id"] for r in acct_rows}

    if acct_map.get("1200") and acct_map.get("4000"):
        je_number = f"JE-INV-{invoice_number}"
        period = entry_date[:7]
        je = (
            db.table("journal_entries")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "entry_number": je_number,
                    "entry_type": "auto",
                    "description": f"AR for invoice {invoice_number}",
                    "entry_date": str(entry_date),
                    "period": period,
                    "reference_type": "invoice",
                    "reference_id": invoice_id,
                    "posted_at": datetime.now(UTC).isoformat(),
                    "created_by": "00000000-0000-0000-0000-000000000000",
                }
            )
            .execute()
        ).data[0]
        je_id = je["id"]

        db.table("journal_lines").insert(
            [
                {
                    "tenant_id": tenant_id,
                    "journal_entry_id": je_id,
                    "direction": "DR",
                    "account_id": acct_map["1200"],
                    "amount": _m(total),
                    "currency": currency,
                    "base_amount": _m(total),
                    "description": f"AR for invoice {invoice_number}",
                },
                {
                    "tenant_id": tenant_id,
                    "journal_entry_id": je_id,
                    "direction": "CR",
                    "account_id": acct_map["4000"],
                    "amount": _m(total),
                    "currency": currency,
                    "base_amount": _m(total),
                    "description": f"Revenue for invoice {invoice_number}",
                },
            ]
        ).execute()

    db.table("invoices").update({"status": "approved"}).eq("id", invoice_id).execute()


def _send_invoice(db: Client, invoice_id: str) -> None:
    db.table("invoices").update(
        {"status": "sent", "sent_at": datetime.now(UTC).isoformat()}
    ).eq("id", invoice_id).execute()


def _pay_invoice(
    db: Client, tenant_id: str, invoice_id: str, amount: Decimal, currency: str
) -> None:
    """Record a manual payment and post Bank / AR journal."""
    paid_at = datetime.now(UTC).isoformat()

    db.table("payments").insert(
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "amount": _m(amount),
            "currency": currency,
            "base_amount": _m(amount),
            "paid_at": paid_at,
            "notes": "Demo payment — seeded by seed_demo.py",
        }
    ).execute()

    db.table("invoices").update(
        {"status": "paid", "paid_at": paid_at}
    ).eq("id", invoice_id).execute()

    # Post Bank / AR journal
    acct_rows = (
        db.table("accounts")
        .select("id, code")
        .eq("tenant_id", tenant_id)
        .in_("code", ["1100", "1200"])
        .execute()
    ).data or []
    acct_map = {r["code"]: r["id"] for r in acct_rows}

    if acct_map.get("1100") and acct_map.get("1200"):
        period = date.today().isoformat()[:7]
        inv_row = db.table("invoices").select("invoice_number").eq("id", invoice_id).execute().data[0]
        inv_num = inv_row["invoice_number"]
        je = (
            db.table("journal_entries")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "entry_number": f"JE-PMT-{inv_num}",
                    "entry_type": "auto",
                    "description": f"Payment received for invoice {inv_num}",
                    "entry_date": _today(),
                    "period": period,
                    "reference_type": "payment",
                    "reference_id": invoice_id,
                    "posted_at": datetime.now(UTC).isoformat(),
                    "created_by": "00000000-0000-0000-0000-000000000000",
                }
            )
            .execute()
        ).data[0]
        db.table("journal_lines").insert(
            [
                {
                    "tenant_id": tenant_id,
                    "journal_entry_id": je["id"],
                    "direction": "DR",
                    "account_id": acct_map["1100"],
                    "amount": _m(amount),
                    "currency": currency,
                    "base_amount": _m(amount),
                    "description": f"Payment received for invoice {inv_num}",
                },
                {
                    "tenant_id": tenant_id,
                    "journal_entry_id": je["id"],
                    "direction": "CR",
                    "account_id": acct_map["1200"],
                    "amount": _m(amount),
                    "currency": currency,
                    "base_amount": _m(amount),
                    "description": f"Payment received for invoice {inv_num}",
                },
            ]
        ).execute()


def _create_bill(
    db: Client,
    *,
    tenant_id: str,
    client_id: str,
    bill_number: str,
    currency: str,
    issue_date: str,
    due_date: str,
    vendor_invoice_number: str,
    lines: list[dict],
) -> str:
    subtotal = sum(_d(ln["amount"]) for ln in lines)
    total = subtotal  # no tax for demo

    res = (
        db.table("bills")
        .insert(
            {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "bill_number": bill_number,
                "currency": currency,
                "subtotal": _m(subtotal),
                "tax_total": "0.00",
                "total": _m(total),
                "status": "draft",
                "issue_date": issue_date,
                "due_date": due_date,
                "vendor_invoice_number": vendor_invoice_number,
                "notes": "Demo bill — seeded by seed_demo.py",
            }
        )
        .execute()
    )
    bill_id = res.data[0]["id"]

    for ln in lines:
        db.table("bill_lines").insert(
            {
                "tenant_id": tenant_id,
                "bill_id": bill_id,
                "description": ln["description"],
                "quantity": str(ln.get("quantity", "1")),
                "unit_price": _m(_d(ln["unit_price"])),
                "amount": _m(_d(ln["amount"])),
                "tax_amount": "0.00",
            }
        ).execute()

    return bill_id


def _approve_bill(
    db: Client, tenant_id: str, bill_id: str
) -> None:
    """Post DR Expenses (5000) / CR AP (2000) journal and mark bill approved."""
    row = db.table("bills").select("*").eq("id", bill_id).execute().data[0]
    total = _d(row["total"])
    currency = row["currency"]
    bill_number = row["bill_number"]
    entry_date = row.get("issue_date") or _today()

    acct_rows = (
        db.table("accounts")
        .select("id, code")
        .eq("tenant_id", tenant_id)
        .in_("code", ["5000", "2000"])
        .execute()
    ).data or []
    acct_map = {r["code"]: r["id"] for r in acct_rows}

    if acct_map.get("5000") and acct_map.get("2000"):
        period = str(entry_date)[:7]
        je = (
            db.table("journal_entries")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "entry_number": f"JE-BILL-{bill_number}",
                    "entry_type": "auto",
                    "description": f"AP for bill {bill_number}",
                    "entry_date": str(entry_date),
                    "period": period,
                    "reference_type": "bill",
                    "reference_id": bill_id,
                    "posted_at": datetime.now(UTC).isoformat(),
                    "created_by": "00000000-0000-0000-0000-000000000000",
                }
            )
            .execute()
        ).data[0]
        db.table("journal_lines").insert(
            [
                {
                    "tenant_id": tenant_id,
                    "journal_entry_id": je["id"],
                    "direction": "DR",
                    "account_id": acct_map["5000"],
                    "amount": _m(total),
                    "currency": currency,
                    "base_amount": _m(total),
                    "description": f"Expense for bill {bill_number}",
                },
                {
                    "tenant_id": tenant_id,
                    "journal_entry_id": je["id"],
                    "direction": "CR",
                    "account_id": acct_map["2000"],
                    "amount": _m(total),
                    "currency": currency,
                    "base_amount": _m(total),
                    "description": f"AP liability for bill {bill_number}",
                },
            ]
        ).execute()

    db.table("bills").update({"status": "approved"}).eq("id", bill_id).execute()


# ---------------------------------------------------------------------------
# Main seed routine
# ---------------------------------------------------------------------------


def seed_demo(tenant_id: str, reset: bool = False) -> None:
    """Seed a tenant with demo data.

    Args:
        tenant_id: UUID of the target tenant (must already exist).
        reset: When True, wipes existing demo-prefixed records before seeding.
    """
    db = _make_client()

    # Verify tenant exists
    tenant_row = (
        db.table("tenants")
        .select("id, name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    ).data
    if not tenant_row:
        _fail(f"Tenant {tenant_id!r} not found in the database.")
    tenant_name = tenant_row[0].get("name", tenant_id)
    print(f"\nSeeding demo data into tenant: {tenant_name} ({tenant_id})")

    if reset:
        reset_demo_data(db, tenant_id)

    # Set session var for triggers / RLS
    _set_tenant(db, tenant_id)

    # ------------------------------------------------------------------
    # 1. Contacts (clients table)
    # ------------------------------------------------------------------
    _section("1. Contacts")

    acme_id = _ensure_client(
        db,
        tenant_id=tenant_id,
        name="Acme Corp [DEMO]",
        kind="customer",
        currency="USD",
        billing_email="ap@acmecorp-demo.example.com",
    )
    _ok(f"Contact: Acme Corp [DEMO] ({acme_id})")

    blackwood_id = _ensure_client(
        db,
        tenant_id=tenant_id,
        name="Blackwood Consulting [DEMO]",
        kind="customer",
        currency="GBP",
        billing_email="accounts@blackwood-demo.example.com",
    )
    _ok(f"Contact: Blackwood Consulting [DEMO] ({blackwood_id})")

    cloudpeak_id = _ensure_client(
        db,
        tenant_id=tenant_id,
        name="CloudPeak Systems [DEMO]",
        kind="vendor",
        currency="USD",
        billing_email="billing@cloudpeak-demo.example.com",
    )
    _ok(f"Contact: CloudPeak Systems [DEMO] ({cloudpeak_id})")

    apex_id = _ensure_client(
        db,
        tenant_id=tenant_id,
        name="Apex Staffing Ltd [DEMO]",
        kind="vendor",
        currency="USD",
        billing_email="invoices@apex-demo.example.com",
    )
    _ok(f"Contact: Apex Staffing Ltd [DEMO] ({apex_id})")

    # ------------------------------------------------------------------
    # 2. Employees
    # ------------------------------------------------------------------
    _section("2. Employees")

    alice_id = _ensure_employee(
        db,
        tenant_id=tenant_id,
        first_name="Alice",
        last_name="Chen",
        email="alice.chen@demo.aethos.app",
        title="Senior Consultant",
        bill_rate=_d("200.00"),
        cost_rate=_d("120.00"),
        currency="USD",
    )
    _ok(f"Employee: Alice Chen — Senior Consultant, $200/hr bill, $120/hr cost ({alice_id})")

    bob_id = _ensure_employee(
        db,
        tenant_id=tenant_id,
        first_name="Bob",
        last_name="Martinez",
        email="bob.martinez@demo.aethos.app",
        title="Project Manager",
        bill_rate=_d("180.00"),
        cost_rate=_d("100.00"),
        currency="USD",
    )
    _ok(f"Employee: Bob Martinez — Project Manager, $180/hr bill, $100/hr cost ({bob_id})")

    # ------------------------------------------------------------------
    # 3. Engagements
    # ------------------------------------------------------------------
    _section("3. Engagements")

    acme_eng_id = _ensure_engagement(
        db,
        tenant_id=tenant_id,
        client_id=acme_id,
        name="Digital Transformation [DEMO]",
        billing_arrangement="time_and_materials",
        currency="USD",
    )
    _ok(f"Engagement: Digital Transformation [DEMO] / Acme Corp (T&M, USD) ({acme_eng_id})")

    blackwood_eng_id = _ensure_engagement(
        db,
        tenant_id=tenant_id,
        client_id=blackwood_id,
        name="Annual Advisory Retainer [DEMO]",
        billing_arrangement="retainer",
        currency="GBP",
        monthly_amount=_d("5000.00"),
    )
    _ok(
        f"Engagement: Annual Advisory Retainer [DEMO] / Blackwood Consulting "
        f"(Retainer, £5,000/mo, GBP) ({blackwood_eng_id})"
    )

    # ------------------------------------------------------------------
    # 4. Projects
    # ------------------------------------------------------------------
    _section("4. Projects")

    acme_proj_id = _ensure_project(
        db,
        tenant_id=tenant_id,
        engagement_id=acme_eng_id,
        name="Phase 1 — Discovery [DEMO]",
        currency="USD",
    )
    _ok(f"Project: Phase 1 — Discovery [DEMO] under Digital Transformation ({acme_proj_id})")

    bw_proj_id = _ensure_project(
        db,
        tenant_id=tenant_id,
        engagement_id=blackwood_eng_id,
        name="Advisory Services [DEMO]",
        currency="GBP",
    )
    _ok(f"Project: Advisory Services [DEMO] under Annual Advisory Retainer ({bw_proj_id})")

    # ------------------------------------------------------------------
    # 5. Time entries (5 total, last 30 days, all assigned to Alice Chen)
    # ------------------------------------------------------------------
    _section("5. Time entries")

    time_entries = [
        {
            "date": _days_ago(28),
            "hours": _d("6.0"),
            "description": "Stakeholder interviews — requirements gathering",
            "billable": True,
            "bill_rate": _d("200.00"),
        },
        {
            "date": _days_ago(21),
            "hours": _d("8.0"),
            "description": "AS-IS process mapping and gap analysis",
            "billable": True,
            "bill_rate": _d("200.00"),
        },
        {
            "date": _days_ago(14),
            "hours": _d("4.0"),
            "description": "Internal team meeting — non-billable coordination",
            "billable": False,
            "bill_rate": _d("200.00"),
        },
        {
            "date": _days_ago(10),
            "hours": _d("7.5"),
            "description": "TO-BE architecture design and roadmap",
            "billable": True,
            "bill_rate": _d("200.00"),
        },
        {
            "date": _days_ago(4),
            "hours": _d("3.0"),
            "description": "Client presentation prep — internal review",
            "billable": False,
            "bill_rate": _d("200.00"),
        },
    ]

    for te in time_entries:
        te_id = _seed_time_entry(
            db,
            tenant_id=tenant_id,
            project_id=acme_proj_id,
            employee_id=alice_id,
            entry_date=te["date"],
            hours=te["hours"],
            description=te["description"],
            billable=te["billable"],
            bill_rate=te["bill_rate"],
        )
        billable_tag = "billable" if te["billable"] else "non-billable"
        _ok(
            f"Time entry: {te['hours']}h on {te['date']} — {te['description'][:45]}... "
            f"[{billable_tag}] ({te_id})"
        )

    # ------------------------------------------------------------------
    # 6. Invoices
    # ------------------------------------------------------------------
    _section("6. Invoices")

    # INV-TEST-001: Acme Corp, $8,500, status=paid
    inv001_id = _create_invoice(
        db,
        tenant_id=tenant_id,
        engagement_id=acme_eng_id,
        client_id=acme_id,
        invoice_number="INV-TEST-001",
        currency="USD",
        issue_date=_days_ago(20),
        due_date=_days_ago(10),
        lines=[
            {
                "description": "Consulting services — Digital Transformation Phase 1",
                "quantity": "1",
                "unit_price": "8500.00",
                "amount": "8500.00",
            }
        ],
    )
    _ok(f"Invoice: INV-TEST-001 — Acme Corp, $8,500 USD (draft) ({inv001_id})")

    try:
        _approve_invoice(db, tenant_id, inv001_id)
        _ok("  → Approved (DR AR / CR Revenue journal posted)")
    except Exception as exc:
        print(f"  WARNING: Could not approve INV-TEST-001: {exc}")

    try:
        _send_invoice(db, inv001_id)
        _ok("  → Marked as sent")
    except Exception as exc:
        print(f"  WARNING: Could not send INV-TEST-001: {exc}")

    try:
        _pay_invoice(db, tenant_id, inv001_id, _d("8500.00"), "USD")
        _ok("  → Payment recorded ($8,500 USD — DR Bank / CR AR journal posted)")
    except Exception as exc:
        print(f"  WARNING: Could not record payment for INV-TEST-001: {exc}")

    # INV-TEST-002: Blackwood, £5,000, status=sent
    inv002_id = _create_invoice(
        db,
        tenant_id=tenant_id,
        engagement_id=blackwood_eng_id,
        client_id=blackwood_id,
        invoice_number="INV-TEST-002",
        currency="GBP",
        issue_date=_days_ago(5),
        due_date=(date.today() + timedelta(days=25)).isoformat(),
        lines=[
            {
                "description": "Advisory retainer — monthly fee",
                "quantity": "1",
                "unit_price": "5000.00",
                "amount": "5000.00",
            }
        ],
    )
    _ok(f"Invoice: INV-TEST-002 — Blackwood Consulting, £5,000 GBP (draft) ({inv002_id})")

    try:
        _approve_invoice(db, tenant_id, inv002_id)
        _ok("  → Approved (DR AR / CR Revenue journal posted)")
    except Exception as exc:
        print(f"  WARNING: Could not approve INV-TEST-002: {exc}")

    try:
        _send_invoice(db, inv002_id)
        _ok("  → Marked as sent (awaiting payment)")
    except Exception as exc:
        print(f"  WARNING: Could not send INV-TEST-002: {exc}")

    # ------------------------------------------------------------------
    # 6b. Project expense (at least 1 — so the Expenses page has data)
    # ------------------------------------------------------------------
    _section("6b. Project expenses")

    expense_id = _seed_project_expense(
        db,
        tenant_id=tenant_id,
        project_id=acme_proj_id,
        employee_id=alice_id,
        description="Client dinner — stakeholder alignment meeting",
        amount=_d("185.50"),
        currency="USD",
        expense_date=_days_ago(7),
        category="meals_entertainment",
        billable=True,
    )
    _ok(f"Project expense: $185.50 — client dinner (billable, reimbursable) ({expense_id})")

    # ------------------------------------------------------------------
    # 7. Bills (AP)
    # ------------------------------------------------------------------
    _section("7. Bills (AP)")

    # BILL-TEST-001: CloudPeak, $2,340, status=draft (simulates Inbox extraction)
    bill001_id = _create_bill(
        db,
        tenant_id=tenant_id,
        client_id=cloudpeak_id,
        bill_number="BILL-TEST-001",
        currency="USD",
        issue_date=_days_ago(3),
        due_date=(date.today() + timedelta(days=27)).isoformat(),
        vendor_invoice_number="CP-INV-2024-0892",
        lines=[
            {
                "description": "Cloud compute — monthly usage",
                "quantity": "1",
                "unit_price": "1800.00",
                "amount": "1800.00",
            },
            {
                "description": "Blob storage — monthly usage",
                "quantity": "1",
                "unit_price": "540.00",
                "amount": "540.00",
            },
        ],
    )
    _ok(
        f"Bill: BILL-TEST-001 — CloudPeak Systems, $2,340 USD, status=draft "
        f"(simulates Inbox extraction) ({bill001_id})"
    )

    # BILL-TEST-002: Apex Staffing, $3,600, status=approved (posted to AP)
    bill002_id = _create_bill(
        db,
        tenant_id=tenant_id,
        client_id=apex_id,
        bill_number="BILL-TEST-002",
        currency="USD",
        issue_date=_days_ago(10),
        due_date=(date.today() + timedelta(days=20)).isoformat(),
        vendor_invoice_number="APEX-2024-7741",
        lines=[
            {
                "description": "Contractor hours — software engineering (20h @ $180)",
                "quantity": "20",
                "unit_price": "180.00",
                "amount": "3600.00",
            }
        ],
    )
    _ok(f"Bill: BILL-TEST-002 — Apex Staffing Ltd, $3,600 USD (draft) ({bill002_id})")

    try:
        _approve_bill(db, tenant_id, bill002_id)
        _ok("  → Approved (DR Expenses / CR AP journal posted) — payable in Pay Bills wizard")
    except Exception as exc:
        print(f"  WARNING: Could not approve BILL-TEST-002: {exc}")

    # ------------------------------------------------------------------
    # 8. HITL task + agent_suggestion for BILL-TEST-001 (CloudPeak draft)
    # ------------------------------------------------------------------
    _section("8. HITL task (Inbox — CloudPeak bill)")

    try:
        _seed_bill_hitl(
            db,
            tenant_id=tenant_id,
            bill_id=bill001_id,
            bill_number="BILL-TEST-001",
            client_name="CloudPeak Systems [DEMO]",
            total_amount="2340.00",
            currency="USD",
        )
    except Exception as exc:
        print(f"  WARNING: Could not create HITL task for BILL-TEST-001: {exc}")

    # ------------------------------------------------------------------
    # 9. Period lock — previous month (for Reports → Period Locks demo)
    # ------------------------------------------------------------------
    _section("9. Period lock (previous month)")

    try:
        _seed_period_lock(db, tenant_id)
    except Exception as exc:
        print(f"  WARNING: Could not seed period lock: {exc}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    first_of_this_month = date.today().replace(day=1)
    prev_month_str = (first_of_this_month - timedelta(days=1)).strftime("%Y-%m")

    print("\n" + "=" * 60)
    print("Demo data seeded successfully!")
    print("=" * 60)
    print(
        f"""
Tenant: {tenant_id}

Created:
  - 2 employees (Alice Chen, Bob Martinez)
  - 4 contacts (Acme Corp, Blackwood Consulting, CloudPeak Systems, Apex Staffing)
  - 2 engagements (T&M + Retainer)
  - 2 projects
  - 5 time entries
  - 1 project expense ($185.50 client dinner, billable)
  - 2 invoices (INV-TEST-001 paid, INV-TEST-002 sent)
  - 2 bills (BILL-TEST-001 draft, BILL-TEST-002 approved)
  - 1 HITL task (bill_extract_review for BILL-TEST-001 in Inbox)
  - 1 period lock ({prev_month_str} — previous month)

Next steps:
  1. Start backend:  cd backend && uv run uvicorn app.main:app --reload --port 8011
  2. Start frontend: cd frontend && ng serve --port 4201
  3. Open: http://localhost:4201
  4. Follow: docs/DEMO_GUIDE.md
"""
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scripts.seed_demo",
        description="Populate a tenant with realistic demo data for Aethos PS demos.",
    )
    parser.add_argument(
        "--tenant-id",
        required=True,
        metavar="UUID",
        help="UUID of the target tenant (must already exist in the tenants table).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help=(
            "Delete all demo-prefixed records (INV-TEST-*, BILL-TEST-*, demo employees "
            "and contacts) before seeding. Makes the script idempotent."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    # Validate the tenant-id looks like a UUID before hitting the DB.
    try:
        uuid.UUID(args.tenant_id)
    except ValueError:
        _fail(f"--tenant-id must be a valid UUID, got: {args.tenant_id!r}")

    try:
        seed_demo(tenant_id=args.tenant_id, reset=args.reset)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\nFATAL: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
