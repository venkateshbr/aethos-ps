"""Unit tests for financial statement reports."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.services.reports_service import ReportsService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-financial-statements-001"


def _journal_line(
    direction: str,
    amount: str,
    code: str,
    name: str,
    account_type: str,
    period: str,
    *,
    entry_id: str,
    description: str = "Posted activity",
    reference_type: str | None = None,
    posted: bool = True,
) -> dict:
    return {
        "tenant_id": TENANT_ID,
        "journal_entry_id": entry_id,
        "direction": direction,
        "base_amount": amount,
        "journal_entries": {
            "period": period,
            "posted_at": "2026-06-30T00:00:00+00:00" if posted else None,
            "description": description,
            "reference_type": reference_type,
        },
        "accounts": {
            "code": code,
            "name": name,
            "account_type": account_type,
        },
    }


def _chain(data: list[dict]) -> MagicMock:
    result = MagicMock()
    result.data = data

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = result
    return chain


class _ReportQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []

    def select(self, _columns: str) -> _ReportQuery:
        return self

    def eq(self, field: str, value: Any) -> _ReportQuery:
        self._filters.append(("eq", field, value))
        return self

    def in_(self, field: str, values: list[Any]) -> _ReportQuery:
        self._filters.append(("in", field, values))
        return self

    def gte(self, field: str, value: Any) -> _ReportQuery:
        self._filters.append(("gte", field, value))
        return self

    def lte(self, field: str, value: Any) -> _ReportQuery:
        self._filters.append(("lte", field, value))
        return self

    def is_(self, field: str, value: Any) -> _ReportQuery:
        self._filters.append(("is", field, value))
        return self

    def execute(self) -> object:
        result = MagicMock()
        result.data = [row for row in self._rows if self._matches(row)]
        return result

    def _matches(self, row: dict) -> bool:
        for op, field, value in self._filters:
            current = row.get(field)
            if op == "eq" and current != value:
                return False
            if op == "in" and current not in value and str(current) not in {str(v) for v in value}:
                return False
            if op == "gte" and str(current or "") < str(value):
                return False
            if op == "lte" and str(current or "") > str(value):
                return False
            if op == "is" and value == "null" and current is not None:
                return False
        return True


class _ReportDb:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _ReportQuery:
        return _ReportQuery(self.tables.get(name, []))


def _service(rows: list[dict]) -> ReportsService:
    db = MagicMock()
    db.table.return_value = _chain(rows)
    return ReportsService(db, TENANT_ID)


def test_balance_sheet_rolls_current_net_income_into_equity() -> None:
    svc = _service(
        [
            _journal_line("DR", "2500.00", "1100", "Bank", "asset", "2026-06", entry_id="je-1"),
            _journal_line(
                "DR",
                "1000.00",
                "1200",
                "Accounts Receivable",
                "asset",
                "2026-06",
                entry_id="je-2",
            ),
            _journal_line(
                "CR",
                "700.00",
                "2000",
                "Accounts Payable",
                "liability",
                "2026-06",
                entry_id="je-3",
            ),
            _journal_line(
                "CR",
                "300.00",
                "3000",
                "Retained Earnings",
                "equity",
                "2026-06",
                entry_id="je-4",
            ),
            _journal_line(
                "CR",
                "3000.00",
                "4000",
                "Revenue",
                "revenue",
                "2026-06",
                entry_id="je-5",
            ),
            _journal_line(
                "DR",
                "500.00",
                "5000",
                "Expenses",
                "expense",
                "2026-06",
                entry_id="je-6",
            ),
        ]
    )

    report = svc.balance_sheet(as_of_period="2026-06")

    assert report.total_assets == "3500.00"
    assert report.total_liabilities == "700.00"
    assert report.total_equity == "2800.00"
    assert report.liabilities_and_equity == "3500.00"
    assert report.is_balanced is True
    assert report.equity_lines[-1].account_code == "current-earnings"
    assert report.equity_lines[-1].amount == "2500.00"


def test_income_statement_filters_period_range() -> None:
    svc = _service(
        [
            _journal_line(
                "CR", "2000.00", "4000", "Revenue", "revenue", "2026-06", entry_id="je-1"
            ),
            _journal_line(
                "DR", "600.00", "5000", "Expenses", "expense", "2026-06", entry_id="je-2"
            ),
            _journal_line("CR", "999.00", "4000", "Revenue", "revenue", "2026-05", entry_id="je-3"),
            _journal_line(
                "DR", "111.00", "5000", "Expenses", "expense", "2026-07", entry_id="je-4"
            ),
        ]
    )

    report = svc.income_statement(period_start="2026-06", period_end="2026-06")

    assert report.total_revenue == "2000.00"
    assert report.total_expenses == "600.00"
    assert report.net_income == "1400.00"
    assert [line.account_code for line in report.revenue_lines] == ["4000"]
    assert [line.account_code for line in report.expense_lines] == ["5000"]


def test_retained_earnings_roll_forward_for_selected_period() -> None:
    svc = _service(
        [
            _journal_line(
                "CR",
                "1000.00",
                "3000",
                "Retained Earnings",
                "equity",
                "2026-05",
                entry_id="je-re-begin",
            ),
            _journal_line(
                "DR",
                "100.00",
                "3000",
                "Retained Earnings",
                "equity",
                "2026-06",
                entry_id="je-re-distribution",
            ),
            _journal_line(
                "CR",
                "900.00",
                "4000",
                "Revenue",
                "revenue",
                "2026-06",
                entry_id="je-revenue",
            ),
            _journal_line(
                "DR",
                "300.00",
                "5000",
                "Expenses",
                "expense",
                "2026-06",
                entry_id="je-expense",
            ),
        ]
    )

    report = svc.retained_earnings_roll_forward(period="2026-06")

    assert report.previous_period == "2026-05"
    assert report.beginning_retained_earnings == "1000.00"
    assert report.current_period_net_income == "600.00"
    assert report.retained_earnings_activity == "-100.00"
    assert report.ending_retained_earnings == "1500.00"


def test_cash_flow_groups_cash_movements_by_statement_section() -> None:
    svc = _service(
        [
            _journal_line(
                "DR",
                "1000.00",
                "1100",
                "Bank",
                "asset",
                "2026-06",
                entry_id="je-operating-in",
                description="Customer receipt",
                reference_type="payment",
            ),
            _journal_line(
                "CR",
                "1000.00",
                "1200",
                "Accounts Receivable",
                "asset",
                "2026-06",
                entry_id="je-operating-in",
                description="Customer receipt",
                reference_type="payment",
            ),
            _journal_line(
                "DR",
                "400.00",
                "2000",
                "Accounts Payable",
                "liability",
                "2026-06",
                entry_id="je-operating-out",
                description="Vendor payment",
                reference_type="bill_payment",
            ),
            _journal_line(
                "CR",
                "400.00",
                "1100",
                "Bank",
                "asset",
                "2026-06",
                entry_id="je-operating-out",
                description="Vendor payment",
                reference_type="bill_payment",
            ),
            _journal_line(
                "DR",
                "200.00",
                "1600",
                "Equipment",
                "asset",
                "2026-06",
                entry_id="je-investing",
                description="Equipment purchase",
            ),
            _journal_line(
                "CR",
                "200.00",
                "1100",
                "Bank",
                "asset",
                "2026-06",
                entry_id="je-investing",
                description="Equipment purchase",
            ),
        ]
    )

    report = svc.cash_flow(period_start="2026-06", period_end="2026-06")

    assert report.net_cash_from_operating == "600.00"
    assert report.net_cash_from_investing == "-200.00"
    assert report.net_cash_from_financing == "0.00"
    assert report.net_change_in_cash == "400.00"
    assert report.beginning_cash == "0.00"
    assert report.ending_cash == "400.00"
    assert [line.description for line in report.operating_lines] == [
        "Customer receipt",
        "Vendor payment",
    ]


def test_statutory_reporting_pack_composes_statements_and_tax_controls() -> None:
    svc = ReportsService(
        _ReportDb(
            {
                "journal_lines": [
                    _journal_line(
                        "DR",
                        "1000.00",
                        "1100",
                        "Bank",
                        "asset",
                        "2026-06",
                        entry_id="je-tax-sale",
                        description="Taxed sale",
                        reference_type="invoice",
                    ),
                    _journal_line(
                        "CR",
                        "800.00",
                        "4000",
                        "Revenue",
                        "revenue",
                        "2026-06",
                        entry_id="je-tax-sale",
                        description="Taxed sale",
                        reference_type="invoice",
                    ),
                    _journal_line(
                        "CR",
                        "200.00",
                        "2300",
                        "Sales Tax Payable",
                        "liability",
                        "2026-06",
                        entry_id="je-tax-sale",
                        description="Taxed sale",
                        reference_type="invoice",
                    ),
                    _journal_line(
                        "DR",
                        "300.00",
                        "5000",
                        "Expenses",
                        "expense",
                        "2026-06",
                        entry_id="je-tax-bill",
                        description="Taxed bill",
                        reference_type="bill",
                    ),
                    _journal_line(
                        "DR",
                        "60.00",
                        "1300",
                        "Input Tax Recoverable",
                        "asset",
                        "2026-06",
                        entry_id="je-tax-bill",
                        description="Taxed bill",
                        reference_type="bill",
                    ),
                    _journal_line(
                        "CR",
                        "360.00",
                        "2000",
                        "Accounts Payable",
                        "liability",
                        "2026-06",
                        entry_id="je-tax-bill",
                        description="Taxed bill",
                        reference_type="bill",
                    ),
                ],
                "invoices": [
                    {
                        "tenant_id": TENANT_ID,
                        "currency": "GBP",
                        "tax_total": "200.00",
                        "status": "approved",
                        "issue_date": "2026-06-15",
                        "deleted_at": None,
                    },
                    {
                        "tenant_id": TENANT_ID,
                        "currency": "GBP",
                        "tax_total": "999.00",
                        "status": "draft",
                        "issue_date": "2026-06-16",
                        "deleted_at": None,
                    },
                ],
                "bills": [
                    {
                        "tenant_id": TENANT_ID,
                        "currency": "GBP",
                        "tax_total": "60.00",
                        "status": "approved",
                        "issue_date": "2026-06-20",
                        "deleted_at": None,
                    }
                ],
            }
        ),  # type: ignore[arg-type]
        TENANT_ID,
    )

    pack = svc.statutory_reporting_pack(
        period_start="2026-06",
        tenant_metadata={
            "country": "GB",
            "base_currency": "GBP",
            "timezone": "Europe/London",
            "locale": "en-GB",
        },
    )

    assert pack.country == "GB"
    assert pack.market == "UK"
    assert pack.base_currency == "GBP"
    assert pack.tax_label == "VAT"
    assert pack.balance_sheet.is_balanced is True
    assert pack.income_statement.net_income == "500.00"
    assert pack.retained_earnings_roll_forward.ending_retained_earnings == "500.00"
    assert pack.tax_summary.ledger_output_tax_payable_balance == "200.00"
    assert pack.tax_summary.ledger_input_tax_recoverable_balance == "60.00"
    assert pack.tax_summary.ledger_net_tax_payable == "140.00"
    assert len(pack.tax_summary.transaction_currency_buckets) == 1
    bucket = pack.tax_summary.transaction_currency_buckets[0]
    assert bucket.currency == "GBP"
    assert bucket.output_tax_collected == "200.00"
    assert bucket.input_tax_recoverable == "60.00"
    assert bucket.net_tax_payable == "140.00"
