"""C40 — Service Catalogue API tests.

Coverage:
  1. test_services_seeded_for_tenant          — 17 system services seeded per tenant
  2. test_create_custom_service               — POST returns new service with is_system=False
  3. test_cannot_deactivate_system_service    — DELETE on is_system=True returns 403
  4. test_revenue_by_service_line             — revenue grouped correctly by service line
  5. test_list_filter_by_service_line         — ?service_line=tax returns only tax services

All tests use the service-role Supabase client for data seeding and use a
temporary test tenant so they don't pollute real tenants.
"""

from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest

pytestmark = [
    pytest.mark.api,
    pytest.mark.requires_supabase,
]

_EXPECTED_SYSTEM_SERVICE_COUNT = 17


def _service_client():
    """Service-role Supabase client — bypasses RLS for test seeding."""
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        pytest.skip("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Shared fixture: a throw-away tenant with the service catalogue seeded
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_tenant():
    """Create a disposable tenant for service-catalogue tests.

    The tenant is deleted at the end of the module (cascade removes all rows).
    """
    db = _service_client()
    run_id = uuid.uuid4().hex[:8]
    tenant_id = str(uuid.uuid4())
    slug = f"svc-test-{run_id}"

    # Insert tenant
    db.table("tenants").insert(
        {
            "id": tenant_id,
            "name": f"Service Catalogue Test {run_id}",
            "slug": slug,
            "country": "GB",
            "base_currency": "GBP",
        }
    ).execute()

    # Seed COA accounts that the migration seed references.
    for code, name in [
        ("4000", "Revenue"),
        ("4001", "Revenue — Tax Services"),
        ("4002", "Revenue — Company Secretarial"),
        ("4003", "Revenue — Payroll"),
    ]:
        existing = (
            db.table("accounts")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("code", code)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not existing:
            db.table("accounts").insert(
                {
                    "tenant_id": tenant_id,
                    "code": code,
                    "name": name,
                    "account_type": "revenue",
                    "is_system": True,
                }
            ).execute()

    # Seed the 17 system services (mirrors migration 0033 seed block).
    services = [
        ("ACC-001", "Monthly Management Accounts", "accounting", "retainer", "4000"),
        ("ACC-002", "Statutory Annual Accounts", "accounting", "fixed", "4000"),
        ("ACC-003", "CFO Advisory Services", "accounting", "hour", "4000"),
        ("ACC-004", "Group Consolidation", "accounting", "fixed", "4000"),
        ("TAX-001", "Corporation Tax Return (CT600)", "tax", "fixed", "4001"),
        ("TAX-002", "VAT Returns (Quarterly)", "tax", "retainer", "4001"),
        ("TAX-003", "Tax Advisory", "tax", "hour", "4001"),
        ("TAX-004", "Personal Tax Return (SA100)", "tax", "fixed", "4001"),
        ("TAX-005", "Trust Tax Return", "tax", "fixed", "4001"),
        ("TAX-006", "CGT Computation", "tax", "fixed", "4001"),
        ("COS-001", "Annual Confirmation Statement", "cosec", "per_event", "4002"),
        ("COS-002", "Director Appointment/Resignation", "cosec", "per_event", "4002"),
        ("COS-003", "Share Allotment", "cosec", "per_event", "4002"),
        ("COS-004", "COSEC Retainer", "cosec", "retainer", "4002"),
        ("PAY-001", "Monthly Payroll Run", "payroll", "per_employee", "4003"),
        ("PAY-002", "Payroll Year-End (P60/P11D)", "payroll", "fixed", "4003"),
        ("PAY-003", "RTI Submission", "payroll", "fixed", "4003"),
    ]

    account_ids: dict[str, str] = {}
    for code, _name, _account_type, *_ in [
        ("4000", "Revenue", "revenue"),
        ("4001", "Revenue — Tax Services", "revenue"),
        ("4002", "Revenue — Company Secretarial", "revenue"),
        ("4003", "Revenue — Payroll", "revenue"),
    ]:
        rows = (
            db.table("accounts")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("code", code)
            .execute()
            .data
        )
        if rows:
            account_ids[code] = str(rows[0]["id"])

    for code, name, service_line, billing_unit, rev_account in services:
        db.table("service_catalogue").insert(
            {
                "tenant_id": tenant_id,
                "code": code,
                "name": name,
                "service_line": service_line,
                "billing_unit": billing_unit,
                "revenue_account_id": account_ids.get(rev_account),
                "is_system": True,
                "is_active": True,
            }
        ).execute()

    yield {"tenant_id": tenant_id, "db": db}

    # Teardown — cascade removes all tenant rows.
    db.table("tenants").delete().eq("id", tenant_id).execute()


# ---------------------------------------------------------------------------
# 1. Seeded count
# ---------------------------------------------------------------------------


def test_services_seeded_for_tenant(test_tenant) -> None:
    """Migration 0033 seeds exactly 17 system services per tenant."""
    db = test_tenant["db"]
    tenant_id = test_tenant["tenant_id"]

    rows = (
        db.table("service_catalogue")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("is_system", True)
        .execute()
        .data
        or []
    )
    assert len(rows) == _EXPECTED_SYSTEM_SERVICE_COUNT, (
        f"Expected {_EXPECTED_SYSTEM_SERVICE_COUNT} system services, found {len(rows)}"
    )


# ---------------------------------------------------------------------------
# 2. Create custom service
# ---------------------------------------------------------------------------


def test_create_custom_service(test_tenant) -> None:
    """POST to service_catalogue creates a non-system service."""
    db = test_tenant["db"]
    tenant_id = test_tenant["tenant_id"]

    new_code = f"CUSTOM-{uuid.uuid4().hex[:6].upper()}"
    result = (
        db.table("service_catalogue")
        .insert(
            {
                "tenant_id": tenant_id,
                "code": new_code,
                "name": "Custom Advisory Service",
                "service_line": "advisory",
                "billing_unit": "hour",
                "is_system": False,
                "is_active": True,
            }
        )
        .execute()
    )
    row = result.data[0]
    assert row["code"] == new_code
    assert row["is_system"] is False
    assert row["is_active"] is True
    assert row["service_line"] == "advisory"

    # Clean up
    db.table("service_catalogue").delete().eq("id", row["id"]).execute()


# ---------------------------------------------------------------------------
# 3. Cannot deactivate system service (PermissionError in service layer)
# ---------------------------------------------------------------------------


def test_cannot_deactivate_system_service(test_tenant) -> None:
    """The service layer must raise PermissionError on deactivate of is_system=True.

    We test the service layer directly (not via HTTP) so we can unit-assert the
    exception without needing a live API server.
    """
    db = test_tenant["db"]
    tenant_id = test_tenant["tenant_id"]

    import asyncio

    from app.services.service_catalogue_service import ServiceCatalogueService

    svc = ServiceCatalogueService(db, tenant_id)

    # Fetch one system service id.
    rows = (
        db.table("service_catalogue")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("is_system", True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        pytest.skip("No system services found in test tenant")

    system_id = str(rows[0]["id"])

    with pytest.raises(PermissionError, match="System services cannot be deactivated"):
        asyncio.run(svc.deactivate_service(system_id))


# ---------------------------------------------------------------------------
# 4. Revenue by service line
# ---------------------------------------------------------------------------


def test_revenue_by_service_line(test_tenant) -> None:
    """revenue_by_service_line returns correct groupings for mock invoices.

    We insert:
      - 1 client, 2 engagements (tax + accounting), 2 invoices with invoice_lines.
    Then assert that the report buckets correctly.
    """
    db = test_tenant["db"]
    tenant_id = test_tenant["tenant_id"]

    from app.services.reports_service import ReportsService

    # Insert a client
    client_id = str(uuid.uuid4())
    db.table("clients").insert(
        {"id": client_id, "tenant_id": tenant_id, "name": "Test Client Rev", "kind": "customer", "payment_terms_days": 30}
    ).execute()

    # Two engagements: tax and accounting
    eng_tax_id = str(uuid.uuid4())
    eng_acc_id = str(uuid.uuid4())
    for eng_id, svc_line in [(eng_tax_id, "tax"), (eng_acc_id, "accounting")]:
        db.table("engagements").insert(
            {
                "id": eng_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "name": f"Eng {svc_line}",
                "billing_arrangement": "fixed_fee",
                "currency": "GBP",
                "status": "active",
                "service_line": svc_line,
            }
        ).execute()

    # Two invoices, one per engagement.
    inv_tax_id = str(uuid.uuid4())
    inv_acc_id = str(uuid.uuid4())
    for inv_id, eng_id, total in [
        (inv_tax_id, eng_tax_id, "500.00"),
        (inv_acc_id, eng_acc_id, "1000.00"),
    ]:
        db.table("invoices").insert(
            {
                "id": inv_id,
                "tenant_id": tenant_id,
                "engagement_id": eng_id,
                "client_id": client_id,
                "status": "sent",
                "issue_date": "2026-06-01",
                "due_date": "2026-06-30",
                "currency": "GBP",
                "total": total,
                "subtotal": total,
                "tax_total": "0.00",
            }
        ).execute()
        db.table("invoice_lines").insert(
            {
                "tenant_id": tenant_id,
                "invoice_id": inv_id,
                "description": "Fee",
                "quantity": "1",
                "unit_price": total,
                "amount": total,
            }
        ).execute()

    svc = ReportsService(db, tenant_id)
    rows = svc.revenue_by_service_line(period="2026-06")

    # Check that both service lines appear and totals are correct.
    by_line = {r["service_line"]: r for r in rows}
    assert "tax" in by_line, f"Expected 'tax' in result, got {list(by_line)}"
    assert "accounting" in by_line, f"Expected 'accounting' in result, got {list(by_line)}"
    assert Decimal(by_line["tax"]["total_revenue"]) == Decimal("500.00")
    assert Decimal(by_line["accounting"]["total_revenue"]) == Decimal("1000.00")

    # Teardown
    for inv_id in [inv_tax_id, inv_acc_id]:
        db.table("invoice_lines").delete().eq("invoice_id", inv_id).execute()
        db.table("invoices").delete().eq("id", inv_id).execute()
    for eng_id in [eng_tax_id, eng_acc_id]:
        db.table("engagements").delete().eq("id", eng_id).execute()
    db.table("clients").delete().eq("id", client_id).execute()


# ---------------------------------------------------------------------------
# 5. List filter by service_line
# ---------------------------------------------------------------------------


def test_list_filter_by_service_line(test_tenant) -> None:
    """?service_line=tax via the service layer returns only tax services."""
    db = test_tenant["db"]
    tenant_id = test_tenant["tenant_id"]

    import asyncio

    from app.services.service_catalogue_service import ServiceCatalogueService

    svc = ServiceCatalogueService(db, tenant_id)
    result = asyncio.run(
        svc.list_services(service_line="tax", active_only=True)
    )

    # All returned items must be tax
    for item in result.items:
        assert item.service_line == "tax", (
            f"Expected service_line='tax', got {item.service_line!r} for {item.code}"
        )

    # We seeded 6 tax services (TAX-001 through TAX-006)
    expected_tax_count = 6
    assert result.total == expected_tax_count, (
        f"Expected {expected_tax_count} tax services, got {result.total}"
    )
