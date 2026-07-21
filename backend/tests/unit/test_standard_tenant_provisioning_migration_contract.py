"""Contracts for cumulative COA and service provisioning in migration 0103."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MIGRATION = (
    Path(__file__).parents[2]
    / "supabase/migrations/0103_standard_tenant_provisioning.sql"
)

_STANDARD_ACCOUNTS = {
    "1100": ("Bank", "asset", "debit"),
    "1200": ("Accounts Receivable", "asset", "debit"),
    "1300": ("Input Tax Recoverable", "asset", "debit"),
    "1500": ("Prepaid Expenses", "asset", "debit"),
    "1600": ("Equipment", "asset", "debit"),
    "1690": ("Accumulated Depreciation", "asset", "credit"),
    "1999": ("Suspense", "asset", "debit"),
    "2000": ("Accounts Payable", "liability", "credit"),
    "2100": ("Accrued Reimbursement", "liability", "credit"),
    "2150": ("Payroll Accrual", "liability", "credit"),
    "2200": ("Deferred Revenue", "liability", "credit"),
    "2300": ("Sales Tax Payable", "liability", "credit"),
    "3000": ("Retained Earnings", "equity", "credit"),
    "3100": ("Owner Capital", "equity", "credit"),
    "4000": ("Revenue", "revenue", "credit"),
    "4001": ("Revenue — Tax Services", "revenue", "credit"),
    "4002": ("Revenue — Company Secretarial", "revenue", "credit"),
    "4003": ("Revenue — Payroll", "revenue", "credit"),
    "5000": ("Expenses", "expense", "debit"),
    "5100": ("Employee Expenses", "expense", "debit"),
    "5300": ("Payroll Expense", "expense", "debit"),
    "6000": ("Software Expense", "expense", "debit"),
    "6100": ("Depreciation Expense", "expense", "debit"),
    "7900": ("Realized FX Gain/Loss", "expense", "debit"),
}

_STANDARD_SERVICES = {
    "ACC-001": ("Monthly Management Accounts", "accounting", "retainer", "4000"),
    "ACC-002": ("Statutory Annual Accounts", "accounting", "fixed", "4000"),
    "ACC-003": ("CFO Advisory Services", "accounting", "hour", "4000"),
    "ACC-004": ("Group Consolidation", "accounting", "fixed", "4000"),
    "TAX-001": ("Corporation Tax Return (CT600)", "tax", "fixed", "4001"),
    "TAX-002": ("VAT Returns (Quarterly)", "tax", "retainer", "4001"),
    "TAX-003": ("Tax Advisory", "tax", "hour", "4001"),
    "TAX-004": ("Personal Tax Return (SA100)", "tax", "fixed", "4001"),
    "TAX-005": ("Trust Tax Return", "tax", "fixed", "4001"),
    "TAX-006": ("CGT Computation", "tax", "fixed", "4001"),
    "COS-001": ("Annual Confirmation Statement", "cosec", "per_event", "4002"),
    "COS-002": ("Director Appointment/Resignation", "cosec", "per_event", "4002"),
    "COS-003": ("Share Allotment", "cosec", "per_event", "4002"),
    "COS-004": ("COSEC Retainer", "cosec", "retainer", "4002"),
    "PAY-001": ("Monthly Payroll Run", "payroll", "per_employee", "4003"),
    "PAY-002": ("Payroll Year-End (P60/P11D)", "payroll", "fixed", "4003"),
    "PAY-003": ("RTI Submission", "payroll", "fixed", "4003"),
}


def _sql() -> str:
    return _MIGRATION.read_text(encoding="utf-8")


def _normalise(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).lower()


def test_migration_adds_normal_balance_and_durable_collision_audit() -> None:
    sql = _normalise(_sql())

    assert "begin;" in sql and "commit;" in sql
    assert "add column if not exists normal_balance" in sql
    assert "normal_balance in ('debit', 'credit')" in sql
    assert "create table if not exists tenant_provisioning_audit" in sql
    assert "alter table tenant_provisioning_audit enable row level security" in sql
    assert "unique (tenant_id, entity_type, desired_code, issue_type, fingerprint)" in sql


def test_seed_standard_coa_is_cumulative_and_semantically_complete() -> None:
    sql = _normalise(_sql())
    coa = sql.split("create or replace function seed_standard_coa", maxsplit=1)[1]
    coa = coa.split(
        "create or replace function seed_standard_service_catalogue", maxsplit=1
    )[0]

    for code, (name, account_type, normal_balance) in _STANDARD_ACCOUNTS.items():
        expected = (
            f"('{code}', '{name.lower()}', '{account_type}', "
            f"'{normal_balance}')"
        )
        assert expected in coa

    desired_codes = re.findall(
        r"\('(\d{4})', '[^']+', '(?:asset|liability|equity|revenue|expense)', "
        r"'(?:debit|credit)'\)",
        coa,
    )
    assert set(desired_codes) == set(_STANDARD_ACCOUNTS)


def test_account_backfill_guards_conflicts_without_replacing_rows() -> None:
    sql = _normalise(_sql())
    coa = sql.split("create or replace function seed_standard_coa", maxsplit=1)[1]
    coa = coa.split(
        "create or replace function seed_standard_service_catalogue", maxsplit=1
    )[0]

    assert "soft_deleted_code_collision" in coa
    assert "soft_deleted_name_collision" in coa
    assert "code_semantic_conflict" in coa
    assert "name_code_collision" in coa
    assert "duplicate_standard_name" in coa
    assert "lower(btrim(" in coa
    assert "normal_balance is null" in coa
    assert "set normal_balance = desired.normal_balance" in coa
    for forbidden in (
        "set code =",
        "set name =",
        "set account_type =",
        "set is_system =",
        "set deleted_at =",
        "delete from accounts",
    ):
        assert forbidden not in coa


def test_future_tenants_and_backfill_receive_all_established_services() -> None:
    sql = _normalise(_sql())
    services = sql.split(
        "create or replace function seed_standard_service_catalogue", maxsplit=1
    )[1]
    services = services.split(
        "create or replace function trg_seed_coa_on_tenant_insert", maxsplit=1
    )[0]

    for code, (name, service_line, billing_unit, revenue_code) in (
        _STANDARD_SERVICES.items()
    ):
        pattern = re.compile(
            rf"\('{re.escape(code.lower())}', '{re.escape(name.lower())}', "
            rf"'[^']*', '{service_line}', '{billing_unit}', '{revenue_code}'\)"
        )
        assert pattern.search(services)

    assert "service_code_semantic_conflict" in services
    assert "service_name_code_collision" in services
    assert "missing_revenue_account" in services
    assert "update service_catalogue" not in services
    assert "delete from service_catalogue" not in services

    trigger = sql.split(
        "create or replace function trg_seed_coa_on_tenant_insert", maxsplit=1
    )[1]
    assert "perform seed_standard_coa(new.id)" in trigger
    assert "perform seed_standard_service_catalogue(new.id)" in trigger
    assert "perform seed_standard_coa(tenant_row.id)" in sql
    assert "perform seed_standard_service_catalogue(tenant_row.id)" in sql
    assert "from tenants where status::text = 'active'" in sql


def test_seeded_services_use_each_tenants_base_currency() -> None:
    sql = _normalise(_sql())
    services = sql.split(
        "create or replace function seed_standard_service_catalogue", maxsplit=1
    )[1]
    services = services.split(
        "create or replace function trg_seed_coa_on_tenant_insert", maxsplit=1
    )[0]

    assert "select upper(base_currency)" in services
    assert "where id = p_tenant_id" in services
    assert "upper(code_match.default_currency) = desired_currency" in services
    assert "desired_currency" in services
    assert "'gbp'," not in services


def test_provisioning_preserves_ids_and_never_overwrites_conflicting_semantics() -> None:
    sql = _normalise(_sql())

    assert "insert into accounts" in sql
    assert "insert into service_catalogue" in sql
    assert "insert into accounts (id" not in sql
    assert "insert into service_catalogue (id" not in sql
    assert "drop table" not in sql
    assert "delete from accounts" not in sql
    assert "delete from service_catalogue" not in sql
