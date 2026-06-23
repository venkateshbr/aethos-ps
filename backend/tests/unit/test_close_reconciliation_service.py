"""Unit tests for pre-lock financial close reconciliation."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.services.close_reconciliation_service import CloseReconciliationService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-close-001"


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _NotFilter:
    def __init__(self, query: _Query) -> None:
        self._query = query

    def is_(self, field: str, value: str) -> _Query:
        self._query._filters.append(("not_is", field, value))
        return self._query


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []
        self.not_ = _NotFilter(self)

    def select(self, _columns: str) -> _Query:
        return self

    def eq(self, field: str, value: Any) -> _Query:
        self._filters.append(("eq", field, value))
        return self

    def in_(self, field: str, values: list[Any]) -> _Query:
        self._filters.append(("in", field, values))
        return self

    def gte(self, field: str, value: Any) -> _Query:
        self._filters.append(("gte", field, value))
        return self

    def lte(self, field: str, value: Any) -> _Query:
        self._filters.append(("lte", field, value))
        return self

    def is_(self, field: str, value: str) -> _Query:
        self._filters.append(("is", field, value))
        return self

    def execute(self) -> _Result:
        rows = [row for row in self._rows if self._matches(row)]
        return _Result(rows)

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
            if op == "not_is" and value == "null" and current is None:
                return False
        return True


class _Db:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.get(name, []))


def _journal_line(direction: str, amount: str, code: str, period: str) -> dict:
    account_names = {
        "1200": ("Accounts Receivable", "asset"),
        "1999": ("Suspense", "asset"),
        "2000": ("Accounts Payable", "liability"),
        "4000": ("Revenue", "revenue"),
        "5000": ("Expenses", "expense"),
    }
    name, account_type = account_names[code]
    return {
        "tenant_id": TENANT_ID,
        "direction": direction,
        "base_amount": amount,
        "journal_entries": {
            "period": period,
            "posted_at": "2026-06-30T00:00:00+00:00",
        },
        "accounts": {
            "code": code,
            "name": name,
            "account_type": account_type,
        },
    }


def _balanced_trial_balance_lines(period: str = "2026-06") -> list[dict]:
    return [
        _journal_line("DR", "100.00", "1200", period),
        _journal_line("CR", "100.00", "4000", period),
    ]


def test_blocks_approved_invoice_without_posted_ar_journal() -> None:
    invoice_id = str(uuid.uuid4())
    db = _Db(
        {
            "invoices": [
                {
                    "tenant_id": TENANT_ID,
                    "id": invoice_id,
                    "invoice_number": "INV-1001",
                    "status": "approved",
                    "issue_date": "2026-06-15",
                    "paid_at": None,
                    "deleted_at": None,
                }
            ],
            "journal_entries": [],
            "journal_lines": _balanced_trial_balance_lines(),
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is False
    assert [finding.code for finding in result.findings] == ["missing_invoice_journal"]
    assert result.as_error_detail()["code"] == "close_reconciliation_failed"


def test_period_ready_when_ar_and_ap_documents_have_posted_journals() -> None:
    invoice_id = str(uuid.uuid4())
    bill_id = str(uuid.uuid4())
    db = _Db(
        {
            "invoices": [
                {
                    "tenant_id": TENANT_ID,
                    "id": invoice_id,
                    "invoice_number": "INV-1002",
                    "status": "sent",
                    "issue_date": "2026-06-10",
                    "paid_at": None,
                    "deleted_at": None,
                }
            ],
            "bills": [
                {
                    "tenant_id": TENANT_ID,
                    "id": bill_id,
                    "bill_number": "BILL-1002",
                    "status": "approved",
                    "issue_date": "2026-06-12",
                    "paid_at": None,
                    "deleted_at": None,
                }
            ],
            "journal_entries": [
                {
                    "tenant_id": TENANT_ID,
                    "reference_type": "invoice",
                    "reference_id": invoice_id,
                    "posted_at": "2026-06-10T00:00:00+00:00",
                },
                {
                    "tenant_id": TENANT_ID,
                    "reference_type": "bill",
                    "reference_id": bill_id,
                    "posted_at": "2026-06-12T00:00:00+00:00",
                },
            ],
            "journal_lines": _balanced_trial_balance_lines(),
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is True
    assert result.findings == []
    assert result.trial_balance_balanced is True


def test_blocks_paid_invoice_without_posted_payment_journal() -> None:
    invoice_id = str(uuid.uuid4())
    db = _Db(
        {
            "invoices": [
                {
                    "tenant_id": TENANT_ID,
                    "id": invoice_id,
                    "invoice_number": "INV-1003",
                    "status": "paid",
                    "issue_date": "2026-05-15",
                    "paid_at": "2026-06-20T09:00:00+00:00",
                    "deleted_at": None,
                }
            ],
            "journal_entries": [],
            "journal_lines": _balanced_trial_balance_lines(),
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is False
    assert [finding.code for finding in result.findings] == ["missing_ar_payment_journal"]


def test_paid_bill_requires_bill_payment_journal() -> None:
    bill_id = str(uuid.uuid4())
    db = _Db(
        {
            "invoices": [],
            "bills": [
                {
                    "tenant_id": TENANT_ID,
                    "id": bill_id,
                    "bill_number": "BILL-1003",
                    "status": "paid",
                    "issue_date": "2026-05-15",
                    "paid_at": "2026-06-21T09:00:00+00:00",
                    "deleted_at": None,
                }
            ],
            "journal_entries": [
                {
                    "tenant_id": TENANT_ID,
                    "reference_type": "bill",
                    "reference_id": bill_id,
                    "posted_at": "2026-05-15T00:00:00+00:00",
                }
            ],
            "journal_lines": _balanced_trial_balance_lines(),
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is False
    assert [finding.code for finding in result.findings] == ["missing_ap_payment_journal"]


def test_paid_bill_with_bill_payment_journal_is_ready() -> None:
    bill_id = str(uuid.uuid4())
    db = _Db(
        {
            "invoices": [],
            "bills": [
                {
                    "tenant_id": TENANT_ID,
                    "id": bill_id,
                    "bill_number": "BILL-1004",
                    "status": "paid",
                    "issue_date": "2026-05-15",
                    "paid_at": "2026-06-21T09:00:00+00:00",
                    "deleted_at": None,
                }
            ],
            "journal_entries": [
                {
                    "tenant_id": TENANT_ID,
                    "reference_type": "bill",
                    "reference_id": bill_id,
                    "posted_at": "2026-05-15T00:00:00+00:00",
                },
                {
                    "tenant_id": TENANT_ID,
                    "reference_type": "bill_payment",
                    "reference_id": bill_id,
                    "posted_at": "2026-06-21T00:00:00+00:00",
                },
            ],
            "journal_lines": _balanced_trial_balance_lines(),
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is True
    assert result.findings == []


def test_blocks_unbalanced_trial_balance() -> None:
    db = _Db(
        {
            "invoices": [],
            "bills": [],
            "journal_entries": [],
            "journal_lines": [
                _journal_line("DR", "100.00", "1200", "2026-06"),
                _journal_line("CR", "90.00", "4000", "2026-06"),
            ],
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is False
    assert result.trial_balance_balanced is False
    assert [finding.code for finding in result.findings] == ["trial_balance_unbalanced"]


def test_blocks_unmatched_bank_transaction() -> None:
    db = _Db(
        {
            "invoices": [],
            "bills": [],
            "journal_entries": [],
            "journal_lines": _balanced_trial_balance_lines(),
            "bank_transactions": [
                {
                    "tenant_id": TENANT_ID,
                    "id": "bank-tx-1",
                    "external_transaction_id": "bank-ext-1",
                    "transaction_date": "2026-06-20",
                    "amount": "100.00",
                    "currency": "USD",
                    "description": "Unmatched receipt",
                    "status": "unmatched",
                    "matched_journal_entry_id": None,
                    "deleted_at": None,
                }
            ],
            "bank_reconciliation_matches": [],
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is False
    assert [finding.code for finding in result.findings] == ["unmatched_bank_transaction"]
    assert result.findings[0].expected_reference_type == "bank_reconciliation_match"


def test_matched_bank_transaction_does_not_block_close() -> None:
    db = _Db(
        {
            "invoices": [],
            "bills": [],
            "journal_entries": [],
            "journal_lines": _balanced_trial_balance_lines(),
            "bank_transactions": [
                {
                    "tenant_id": TENANT_ID,
                    "id": "bank-tx-2",
                    "external_transaction_id": "bank-ext-2",
                    "transaction_date": "2026-06-20",
                    "amount": "-75.00",
                    "currency": "USD",
                    "description": "Matched payment",
                    "status": "matched",
                    "matched_journal_entry_id": None,
                    "deleted_at": None,
                }
            ],
            "bank_reconciliation_matches": [
                {
                    "tenant_id": TENANT_ID,
                    "bank_transaction_id": "bank-tx-2",
                    "status": "matched",
                    "deleted_at": None,
                }
            ],
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is True
    assert result.findings == []


def test_blocks_nonzero_suspense_balance() -> None:
    db = _Db(
        {
            "invoices": [],
            "bills": [],
            "journal_entries": [],
            "journal_lines": [
                _journal_line("DR", "25.00", "1999", "2026-06"),
                _journal_line("CR", "25.00", "4000", "2026-06"),
            ],
            "bank_transactions": [],
            "bank_reconciliation_matches": [],
        }
    )

    result = CloseReconciliationService(db, TENANT_ID).check_period("2026-06")  # type: ignore[arg-type]

    assert result.ready is False
    assert result.trial_balance_balanced is True
    assert [finding.code for finding in result.findings] == ["suspense_account_balance"]
    assert result.findings[0].source_number == "1999"
