"""Static checks on the employee ERP-firewall RLS migration (#466 / ADR 0005 D4).

The RLS *behaviour* needs a live DB (covered by the live-stack verification), but
these assertions pin the migration's shape so it can't silently regress: the
helper excludes the employee role, and every batch-1 ERP table gets a RESTRICTIVE
policy while the employee self-service tables are NOT firewalled.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "0115_employee_erp_firewall_rls.sql"
)

_ERP_TABLES = [
    "journal_entries",
    "journal_lines",
    "invoices",
    "bills",
    "payments",
    "clients",
    "engagements",
    "projects",
    "bill_payment_batches",
    "bill_payment_items",
]
# Employees keep self-service access to these — they must NOT be firewalled here.
_EXCLUDED = ["time_entries", "employees"]


@pytest.fixture(scope="module")
def sql() -> str:
    return _MIGRATION.read_text()


def test_helper_excludes_employee_role(sql: str) -> None:
    assert "CREATE OR REPLACE FUNCTION public.is_tenant_erp_member" in sql
    assert "<> 'employee'" in sql
    assert "SECURITY DEFINER" in sql


def test_restrictive_policy_is_additive(sql: str) -> None:
    # RESTRICTIVE (not permissive) so it AND-s with existing policies without
    # touching them; scoped to the authenticated role (service_role bypasses RLS).
    assert "AS RESTRICTIVE" in sql
    assert "TO authenticated" in sql
    assert "is_tenant_erp_member(auth.uid(), tenant_id)" in sql


def test_all_batch1_erp_tables_listed(sql: str) -> None:
    for table in _ERP_TABLES:
        assert f"'{table}'" in sql, f"{table} missing from the firewall batch"


def test_self_service_tables_not_firewalled(sql: str) -> None:
    # These must stay reachable by the timesheet employee — never add them to the
    # ERP-only firewall list.
    for table in _EXCLUDED:
        assert f"'{table}'" not in sql, f"{table} must not be ERP-firewalled"
