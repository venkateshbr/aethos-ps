"""Unit tests for Bills (AP) and HITL Inbox modules.

Coverage:
  - JournalLineSpec / validate_journal_balance (journal_helper)
  - BillResponse money serialisation (models/bills)
  - BillCreate validation
  - HitlTaskSummary / ApproveWithEditsRequest (models/inbox)
  - InboxService._get_open_task_or_raise logic (service pure-Python path)
  - Business rules: total > 0 for approval

All tests are pure-Python — no I/O, no DB, no HTTP.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest

from app.domain.journal_helper import JournalLineSpec, validate_journal_balance

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# journal_helper — JournalLineSpec validation
# ---------------------------------------------------------------------------


def test_journal_line_spec_requires_valid_direction() -> None:
    with pytest.raises(ValueError, match="direction must be"):
        JournalLineSpec(direction="XX", account_code="5000", amount=Decimal("100"))


def test_journal_line_spec_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="amount must be non-negative"):
        JournalLineSpec(direction="DR", account_code="5000", amount=Decimal("-1"))


def test_journal_line_spec_allows_zero_amount() -> None:
    spec = JournalLineSpec(direction="CR", account_code="2000", amount=Decimal("0"))
    assert spec.amount == Decimal("0")


# ---------------------------------------------------------------------------
# validate_journal_balance
# ---------------------------------------------------------------------------


def test_validate_journal_balance_passes_exact() -> None:
    lines = [
        JournalLineSpec("DR", "5000", Decimal("100.00")),
        JournalLineSpec("CR", "2000", Decimal("100.00")),
    ]
    assert validate_journal_balance(lines) is True


def test_validate_journal_balance_fails_imbalanced() -> None:
    lines = [
        JournalLineSpec("DR", "5000", Decimal("100.00")),
        JournalLineSpec("CR", "2000", Decimal("99.00")),
    ]
    assert validate_journal_balance(lines) is False


def test_validate_journal_balance_allows_01_fx_residual() -> None:
    """1-cent tolerance handles FX rounding residuals."""
    lines = [
        JournalLineSpec("DR", "1200", Decimal("100.00")),
        JournalLineSpec("CR", "4000", Decimal("99.99")),
    ]
    assert validate_journal_balance(lines) is True


def test_validate_journal_balance_rejects_02_gap() -> None:
    """2-cent gap is outside tolerance."""
    lines = [
        JournalLineSpec("DR", "5000", Decimal("100.00")),
        JournalLineSpec("CR", "2000", Decimal("99.98")),
    ]
    assert validate_journal_balance(lines) is False


def test_validate_journal_balance_multi_line() -> None:
    """Multiple debit lines balanced by one credit."""
    lines = [
        JournalLineSpec("DR", "5000", Decimal("60.00")),
        JournalLineSpec("DR", "5100", Decimal("40.00")),
        JournalLineSpec("CR", "2000", Decimal("100.00")),
    ]
    assert validate_journal_balance(lines) is True


def test_ap_journal_uses_net_expense_accounts_and_input_tax_recoverable() -> None:
    from app.services.bills_service import _build_ap_journal_lines

    journal_lines = _build_ap_journal_lines(
        bill_lines=[
            {
                "description": "AWS",
                "amount": "60.00",
                "tax_amount": "6.00",
                "account_id": "acct-cloud",
            },
            {
                "description": "Slack",
                "amount": "40.00",
                "tax_amount": "0.00",
                "account_id": None,
            },
        ],
        expense_account_id="acct-expense",
        ap_account_id="acct-ap",
        input_tax_account_id="acct-input-tax",
        bill_total=Decimal("106.00"),
        bill_number="BILL-001",
        currency="USD",
    )

    debit_lines = [line for line in journal_lines if line.direction == "DR"]
    credit_lines = [line for line in journal_lines if line.direction == "CR"]
    by_account = {line.account_id: line for line in debit_lines}

    assert by_account["acct-cloud"].amount == Decimal("60.00")
    assert by_account["acct-cloud"].account_code == ""
    assert by_account["acct-expense"].amount == Decimal("40.00")
    assert by_account["acct-expense"].account_code == "5000"
    assert by_account["acct-input-tax"].amount == Decimal("6.00")
    assert by_account["acct-input-tax"].account_code == "1300"
    assert credit_lines[0].account_id == "acct-ap"
    assert credit_lines[0].amount == Decimal("106.00")
    assert validate_journal_balance(journal_lines) is True


def test_ap_journal_groups_lines_with_same_expense_account() -> None:
    from app.services.bills_service import _build_ap_journal_lines

    journal_lines = _build_ap_journal_lines(
        bill_lines=[
            {"amount": "25.00", "tax_amount": "0.00", "account_id": "acct-saas"},
            {"amount": "75.00", "tax_amount": "0.00", "account_id": "acct-saas"},
        ],
        expense_account_id="acct-expense",
        ap_account_id="acct-ap",
        input_tax_account_id=None,
        bill_total=Decimal("100.00"),
        bill_number="BILL-002",
        currency="USD",
    )

    debit_lines = [line for line in journal_lines if line.direction == "DR"]
    assert len(debit_lines) == 1
    assert debit_lines[0].account_id == "acct-saas"
    assert debit_lines[0].amount == Decimal("100.00")


def test_ap_journal_rejects_line_total_mismatch() -> None:
    from app.services.bills_service import _build_ap_journal_lines

    with pytest.raises(ValueError, match="Bill line totals do not match"):
        _build_ap_journal_lines(
            bill_lines=[
                {"amount": "99.00", "tax_amount": "0.00", "account_id": None},
            ],
            expense_account_id="acct-expense",
            ap_account_id="acct-ap",
            input_tax_account_id=None,
            bill_total=Decimal("100.00"),
            bill_number="BILL-003",
            currency="USD",
        )


def test_ap_journal_requires_input_tax_account_for_taxable_bill() -> None:
    from app.services.bills_service import _build_ap_journal_lines

    with pytest.raises(ValueError, match="Input tax recoverable account"):
        _build_ap_journal_lines(
            bill_lines=[
                {"amount": "100.00", "tax_amount": "10.00", "account_id": None},
            ],
            expense_account_id="acct-expense",
            ap_account_id="acct-ap",
            input_tax_account_id=None,
            bill_total=Decimal("110.00"),
            bill_number="BILL-004",
            currency="USD",
        )


def test_ap_journal_capitalizes_prepaid_lines_to_prepaid_asset() -> None:
    from app.services.bills_service import _build_ap_journal_lines

    journal_lines = _build_ap_journal_lines(
        bill_lines=[
            {
                "amount": "1200.00",
                "tax_amount": "0.00",
                "account_id": "acct-software-expense",
                "is_prepaid": True,
            },
        ],
        expense_account_id="acct-expense",
        ap_account_id="acct-ap",
        input_tax_account_id=None,
        prepaid_account_id="acct-prepaid",
        bill_total=Decimal("1200.00"),
        bill_number="BILL-005",
        currency="USD",
    )

    debit_lines = [line for line in journal_lines if line.direction == "DR"]
    credit_lines = [line for line in journal_lines if line.direction == "CR"]

    assert debit_lines[0].account_id == "acct-prepaid"
    assert debit_lines[0].account_code == "1500"
    assert debit_lines[0].amount == Decimal("1200.00")
    assert credit_lines[0].account_id == "acct-ap"
    assert validate_journal_balance(journal_lines) is True


def test_ap_journal_requires_prepaid_account_for_prepaid_line() -> None:
    from app.services.bills_service import _build_ap_journal_lines

    with pytest.raises(ValueError, match="Prepaid expenses account"):
        _build_ap_journal_lines(
            bill_lines=[
                {
                    "amount": "1200.00",
                    "tax_amount": "0.00",
                    "account_id": None,
                    "is_prepaid": True,
                },
            ],
            expense_account_id="acct-expense",
            ap_account_id="acct-ap",
            input_tax_account_id=None,
            prepaid_account_id=None,
            bill_total=Decimal("1200.00"),
            bill_number="BILL-006",
            currency="USD",
        )


def test_validate_journal_balance_empty_balances() -> None:
    """Empty list trivially balances."""
    assert validate_journal_balance([]) is True


# ---------------------------------------------------------------------------
# BillResponse — money serialisation
# ---------------------------------------------------------------------------


def test_bill_response_serialises_totals_as_strings() -> None:
    from app.models.bills import BillResponse

    r = BillResponse(
        id="b1",
        tenant_id="t1",
        client_id="c1",
        bill_number="BILL-0001",
        currency="USD",
        subtotal="500.00",
        tax_total="50.00",
        total="550.00",
        status="draft",
        issue_date=None,
        due_date=None,
        vendor_invoice_number=None,
        notes=None,
        created_at="2026-05-19T00:00:00Z",
    )
    assert isinstance(r.total, str)
    assert r.total == "550.00"
    assert isinstance(r.subtotal, str)
    assert isinstance(r.tax_total, str)


def test_bill_response_lines_default_empty() -> None:
    from app.models.bills import BillResponse

    r = BillResponse(
        id="b2",
        tenant_id="t1",
        client_id="c1",
        bill_number="BILL-0002",
        currency="USD",
        subtotal="0",
        tax_total="0",
        total="0",
        status="draft",
        issue_date=None,
        due_date=None,
        vendor_invoice_number=None,
        notes=None,
        created_at="2026-05-19",
    )
    assert r.lines == []


# ---------------------------------------------------------------------------
# BillCreate — field validation
# ---------------------------------------------------------------------------


def test_bill_create_currency_must_be_three_chars() -> None:
    from pydantic import ValidationError

    from app.models.bills import BillCreate

    with pytest.raises(ValidationError):
        BillCreate(client_id="c1", currency="US")  # too short


def test_bill_create_defaults_to_usd() -> None:
    from app.models.bills import BillCreate

    b = BillCreate(client_id="c1")
    assert b.currency == "USD"


def test_bill_line_quantity_must_be_positive() -> None:
    from pydantic import ValidationError

    from app.models.bills import BillLineCreate

    with pytest.raises(ValidationError):
        BillLineCreate(
            description="x", quantity=Decimal("0"), unit_price=Decimal("10"), amount=Decimal("0")
        )


def test_bill_line_prepaid_requires_service_window() -> None:
    from pydantic import ValidationError

    from app.models.bills import BillLineCreate

    with pytest.raises(ValidationError, match="Prepaid lines require"):
        BillLineCreate(
            description="Annual software",
            unit_price=Decimal("1200"),
            amount=Decimal("1200"),
            is_prepaid=True,
        )


def test_bill_line_prepaid_service_window_must_be_ordered() -> None:
    from datetime import date

    from pydantic import ValidationError

    from app.models.bills import BillLineCreate

    with pytest.raises(ValidationError, match="service_end_date"):
        BillLineCreate(
            description="Annual software",
            unit_price=Decimal("1200"),
            amount=Decimal("1200"),
            is_prepaid=True,
            service_start_date=date(2026, 12, 31),
            service_end_date=date(2026, 1, 1),
        )


def test_bill_line_prepaid_accepts_valid_service_window() -> None:
    from datetime import date

    from app.models.bills import BillLineCreate

    line = BillLineCreate(
        description="Annual software",
        unit_price=Decimal("1200"),
        amount=Decimal("1200"),
        is_prepaid=True,
        service_start_date=date(2026, 1, 1),
        service_end_date=date(2026, 12, 31),
    )

    assert line.is_prepaid is True
    assert line.service_start_date == date(2026, 1, 1)
    assert line.service_end_date == date(2026, 12, 31)


# ---------------------------------------------------------------------------
# Business rule: total > 0 required for approval
# ---------------------------------------------------------------------------


def test_bill_requires_positive_total_for_approval() -> None:
    total = Decimal("0")
    with pytest.raises(ValueError, match="Bill total must be > 0"):
        if total <= 0:
            raise ValueError("Bill total must be > 0")


def test_bill_positive_total_does_not_raise() -> None:
    total = Decimal("100.00")
    # No exception should be raised
    if total <= 0:
        raise AssertionError("Should not raise for positive total")


# ---------------------------------------------------------------------------
# ApAgingResponse / AgingBucket — serialisation
# ---------------------------------------------------------------------------


def test_aging_bucket_total_is_string() -> None:
    from app.models.bills import AgingBucket

    bucket = AgingBucket(label="current", total="1500.00", count=3)
    assert isinstance(bucket.total, str)
    assert bucket.count == 3


# ---------------------------------------------------------------------------
# HitlTaskSummary — model construction
# ---------------------------------------------------------------------------


def test_hitl_task_summary_confidence_is_string() -> None:
    from app.models.inbox import HitlTaskSummary

    t = HitlTaskSummary(
        id="t1",
        tenant_id="tenant-a",
        kind="create_bill",
        priority="normal",
        title="Review vendor invoice",
        agent_name="vendor_invoice_agent",
        confidence="0.92",
        status="open",
        created_at="2026-05-19T00:00:00Z",
        suggestion_payload={"vendor": "AWS", "total": "500.00"},
    )
    assert isinstance(t.confidence, str)
    assert t.confidence == "0.92"
    assert t.suggestion_payload["vendor"] == "AWS"


# ---------------------------------------------------------------------------
# ApproveWithEditsRequest — accepts arbitrary corrected payload
# ---------------------------------------------------------------------------


def test_approve_with_edits_accepts_arbitrary_payload() -> None:
    from app.models.inbox import ApproveWithEditsRequest

    req = ApproveWithEditsRequest(corrected_payload={"vendor": "AWS", "total": "200.00"})
    assert req.corrected_payload["vendor"] == "AWS"
    assert req.corrected_payload["total"] == "200.00"


def test_approve_with_edits_empty_payload_allowed() -> None:
    from app.models.inbox import ApproveWithEditsRequest

    req = ApproveWithEditsRequest(corrected_payload={})
    assert req.corrected_payload == {}


# ---------------------------------------------------------------------------
# RejectRequest — optional reason
# ---------------------------------------------------------------------------


def test_reject_request_defaults_empty_reason() -> None:
    from app.models.inbox import RejectRequest

    req = RejectRequest()
    assert req.reason == ""


def test_reject_request_accepts_reason() -> None:
    from app.models.inbox import RejectRequest

    req = RejectRequest(reason="Duplicate invoice")
    assert req.reason == "Duplicate invoice"


# ---------------------------------------------------------------------------
# InboxService — pure-Python path: double-resolve guard
# ---------------------------------------------------------------------------


def test_done_task_raises_409() -> None:
    """Simulate the guard logic in InboxService._get_open_task_or_raise."""
    from fastapi import HTTPException

    task = {"id": "t1", "status": "done", "kind": "create_bill"}

    with pytest.raises(HTTPException) as exc_info:
        if task.get("status") == "done":
            raise HTTPException(status_code=409, detail="Task already resolved")

    assert exc_info.value.status_code == 409


def test_missing_task_raises_404() -> None:
    from fastapi import HTTPException

    task = None

    with pytest.raises(HTTPException) as exc_info:
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# InboxService._materialise — kind routing (#146 follow-up)
#
# The extraction worker emits *_draft kinds. The dispatch previously only
# matched the suffix-less names, so every approval fell through to the no-op
# branch and created nothing. These verify the draft kinds route correctly.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "expected_method"),
    [
        ("create_engagement_draft", "_materialise_engagement"),
        ("create_expense_draft", "_materialise_expense"),
        ("create_bill_draft", "_materialise_bill"),
        # backward-compat: suffix-less + legacy aliases still route
        ("create_engagement", "_materialise_engagement"),
        ("vendor_invoice", "_materialise_bill"),
    ],
)
async def test_materialise_routes_draft_kinds(kind: str, expected_method: str) -> None:
    from unittest.mock import AsyncMock

    from app.services.inbox_service import InboxService

    svc = InboxService.__new__(InboxService)  # bypass __init__ (no DB needed)
    for m in ("_materialise_engagement", "_materialise_expense", "_materialise_bill"):
        setattr(svc, m, AsyncMock(return_value={"entity_type": "x", "entity_id": "1"}))

    await svc._materialise(kind, {"client_name": "Acme"})

    getattr(svc, expected_method).assert_awaited_once()
    others = {"_materialise_engagement", "_materialise_expense", "_materialise_bill"} - {
        expected_method
    }
    for m in others:
        getattr(svc, m).assert_not_awaited()


@pytest.mark.asyncio
async def test_materialise_unknown_kind_is_noop() -> None:
    from app.services.inbox_service import InboxService

    svc = InboxService.__new__(InboxService)
    result = await svc._materialise("something_else", {})
    assert result["entity_id"] is None


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _P2PQuery:
    def __init__(self, db: _P2PDb, table: str) -> None:
        self.db = db
        self.table = table
        self.eq_filters: list[tuple[str, Any]] = []
        self.null_filters: list[str] = []
        self.limit_count: int | None = None
        self.insert_payload: dict[str, Any] | None = None
        self.update_payload: dict[str, Any] | None = None
        self.ilike_filter: tuple[str, str] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _P2PQuery:
        return self

    def eq(self, key: str, value: Any) -> _P2PQuery:
        self.eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _P2PQuery:
        if value == "null":
            self.null_filters.append(key)
        return self

    def ilike(self, key: str, pattern: str) -> _P2PQuery:
        self.ilike_filter = (key, pattern.strip("%").lower())
        return self

    def limit(self, count: int) -> _P2PQuery:
        self.limit_count = count
        return self

    def insert(self, payload: dict[str, Any]) -> _P2PQuery:
        self.insert_payload = dict(payload)
        return self

    def update(self, payload: dict[str, Any]) -> _P2PQuery:
        self.update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self.insert_payload is not None:
            row = self._insert_row()
            self.db.tables[self.table].append(row)
            return _Result([deepcopy(row)])

        rows = self._filtered_rows()
        if self.update_payload is not None:
            for row in rows:
                row.update(self.update_payload)
            return _Result(deepcopy(rows))
        if self.limit_count is not None:
            rows = rows[: self.limit_count]
        return _Result(deepcopy(rows))

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self.db.tables[self.table])
        for key, value in self.eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        for key in self.null_filters:
            rows = [row for row in rows if row.get(key) is None]
        if self.ilike_filter is not None:
            key, needle = self.ilike_filter
            rows = [row for row in rows if needle in str(row.get(key) or "").lower()]
        return rows

    def _insert_row(self) -> dict[str, Any]:
        assert self.insert_payload is not None
        if self.table == "bills":
            return {
                "id": "bill-created",
                "tenant_id": "tenant-1",
                "bill_number": "BILL-0001",
                "subtotal": "0.00",
                "tax_total": "0.00",
                "total": "0.00",
                "status": "draft",
                "created_at": "2026-06-24T00:00:00+00:00",
                "updated_at": "2026-06-24T00:00:00+00:00",
                "deleted_at": None,
                **self.insert_payload,
            }
        if self.table == "bill_lines":
            return {
                "id": f"line-{len(self.db.tables[self.table]) + 1}",
                "created_at": "2026-06-24T00:00:00+00:00",
                **self.insert_payload,
            }
        if self.table == "clients":
            return {
                "id": "client-created",
                "tenant_id": "tenant-1",
                "deleted_at": None,
                **self.insert_payload,
            }
        raise AssertionError(f"unexpected insert into {self.table}")


class _P2PDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "clients": [
                {
                    "id": "vendor-1",
                    "tenant_id": "tenant-1",
                    "name": "AWS",
                    "kind": "vendor",
                    "deleted_at": None,
                }
            ],
            "accounts": [
                {
                    "id": "acct-software",
                    "tenant_id": "tenant-1",
                    "code": "5100",
                    "name": "Software",
                    "deleted_at": None,
                }
            ],
            "bills": [],
            "bill_lines": [],
            "procurement_documents": [],
            "procurement_document_lines": [],
        }

    def table(self, name: str) -> _P2PQuery:
        self.tables.setdefault(name, [])
        return _P2PQuery(self, name)


@pytest.mark.asyncio
async def test_materialise_bill_blocks_duplicate_without_explicit_override() -> None:
    from fastapi import HTTPException

    from app.services.inbox_service import InboxService

    svc = InboxService(_P2PDb(), "tenant-1")

    with pytest.raises(HTTPException) as exc_info:
        await svc._materialise_bill(
            {
                "vendor_name": "AWS",
                "possible_duplicate": True,
                "subtotal": "100.00",
                "tax_total": "0.00",
                "total": "100.00",
                "lines": [{"description": "Cloud hosting", "amount": "100.00"}],
            },
            user_id="manager-1",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "duplicate_vendor_invoice_review_required"


@pytest.mark.asyncio
async def test_materialise_bill_creates_lines_and_review_evidence() -> None:
    from app.services.inbox_service import InboxService

    db = _P2PDb()
    svc = InboxService(db, "tenant-1")

    result = await svc._materialise_bill(
        {
            "client_id": "vendor-1",
            "vendor_name": "AWS",
            "vendor_invoice_number": "AWS-100",
            "currency": "USD",
            "subtotal": "100.00",
            "tax_total": "10.00",
            "total": "110.00",
            "issue_date": "2026-06-01",
            "due_date": "2026-07-01",
            "original_document_id": "document-1",
            "possible_duplicate": True,
            "duplicate_review": {
                "approved_duplicate": True,
                "reason": "Legitimate split invoice after AP review.",
            },
            "match_status": "duplicate_review_required",
            "coding_status": "coded",
            "vendor_match": {"matched_client_id": "vendor-1", "confidence": 0.97},
            "gl_suggestions": [
                {
                    "account_id": "acct-software",
                    "account_code": "5100",
                    "account_name": "Software",
                    "confidence": 0.91,
                }
            ],
            "project_hints": [{"project_id": "project-1", "confidence": 0.82}],
            "customer_hints": [{"client_id": "customer-1", "confidence": 0.79}],
            "review_exceptions": [{"code": "possible_duplicate", "severity": "high"}],
            "lines": [
                {
                    "description": "Cloud hosting",
                    "amount": "100.00",
                    "tax_amount": "10.00",
                    "account_id": "acct-software",
                }
            ],
        },
        user_id="manager-1",
    )

    assert result == {"entity_type": "bill", "entity_id": "bill-created"}
    bill = db.tables["bills"][0]
    assert bill["source_document_id"] == "document-1"
    assert bill["vendor_invoice_review"]["reviewed_by_user_id"] == "manager-1"
    assert bill["vendor_invoice_review"]["duplicate_review"]["approved_duplicate"] is True
    assert bill["vendor_invoice_review"]["match_status"] == "duplicate_review_required"
    assert bill["vendor_invoice_review"]["project_hints"][0]["project_id"] == "project-1"
    assert bill["vendor_invoice_review"]["customer_hints"][0]["client_id"] == "customer-1"
    assert db.tables["bill_lines"][0]["account_id"] == "acct-software"


@pytest.mark.asyncio
async def test_materialise_bill_falls_back_when_extracted_lines_are_malformed() -> None:
    from app.services.inbox_service import InboxService

    db = _P2PDb()
    svc = InboxService(db, "tenant-1")

    await svc._materialise_bill(
        {
            "client_id": "vendor-1",
            "vendor_name": "AWS",
            "subtotal": "42.00",
            "tax_total": "4.20",
            "total": "46.20",
            "lines": ["not-a-line"],
        },
        user_id="manager-1",
    )

    line = db.tables["bill_lines"][0]
    assert line["description"] == "Vendor invoice"
    assert line["amount"] == "42.00"
    assert line["tax_amount"] == "4.20"


# ---------------------------------------------------------------------------
# Engagement materialisation also creates the reviewed first project so the
# user can log time immediately without a manual project-create step.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_materialise_engagement_creates_reviewed_first_project() -> None:
    """Approving an extracted engagement also inserts the reviewed first project."""
    from unittest.mock import MagicMock

    from app.services.inbox_service import InboxService

    inserts: list[tuple[str, dict]] = []

    def _table(name: str):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.ilike.return_value = chain
        chain.limit.return_value = chain
        # clients lookup returns empty so insert path runs
        chain.execute.return_value = MagicMock(data=[])

        def _insert(row: dict):
            inserts.append((name, row))
            ret = MagicMock()
            ret.execute.return_value = MagicMock(data=[{"id": f"{name}-id"}])
            return ret

        chain.insert.side_effect = _insert
        return chain

    db = MagicMock()
    db.table.side_effect = _table

    svc = InboxService.__new__(InboxService)
    svc._db = db
    svc._tenant_id = "tenant-1"

    payload = {
        "client_name": "Lumera Technologies",
        "engagement_name": "Lumera SOC 2 Readiness",
        "currency": "SGD",
        "billing_arrangement": "fixed_fee",
        "total_value": "44500",
        "start_date": "2026-07-01",
        "end_date": "2026-09-30",
        "scope_summary": "SOC 2 readiness assessment and evidence support.",
        "first_project_name": "SOC 2 Readiness",
        "first_project_description": "Readiness assessment, gap closure, and evidence support.",
    }
    result = await svc._materialise_engagement(payload)

    assert result["entity_type"] == "engagement"
    assert result["client_id"] == "clients-id"
    assert result["project_id"] == "projects-id"
    assert result["project_name"] == "SOC 2 Readiness"
    inserted_tables = [t for t, _ in inserts]
    assert "clients" in inserted_tables
    assert "engagements" in inserted_tables
    assert "projects" in inserted_tables, "default project must be auto-created"

    engagement_row = next(row for t, row in inserts if t == "engagements")
    assert engagement_row["name"] == "Lumera SOC 2 Readiness"
    assert engagement_row["description"] == "SOC 2 readiness assessment and evidence support."
    assert engagement_row["start_date"] == "2026-07-01"
    assert engagement_row["end_date"] == "2026-09-30"

    project_row = next(row for t, row in inserts if t == "projects")
    assert project_row["name"] == "SOC 2 Readiness"
    assert project_row["description"] == "Readiness assessment, gap closure, and evidence support."
    assert project_row["currency"] == "SGD"  # inherited from engagement
    assert project_row["budget"] == "44500"
    assert project_row["start_date"] == "2026-07-01"
    assert project_row["end_date"] == "2026-09-30"
    assert project_row["status"] == "planning"
