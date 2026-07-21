"""Accounting API contract tests for bounded RLS reads and service-role writes."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app
from app.models.accounting import (
    ManualJournalApprovalTaskResponse,
    ManualJournalEntryResponse,
)
from app.services.close_package_service import ClosePackageService
from app.services.close_reconciliation_service import (
    CloseReconciliationResult,
    CloseReconciliationService,
    ReconciliationFinding,
)
from app.services.close_status_service import CloseStatusService
from app.services.manual_journal_service import ManualJournalService
from app.services.year_end_close_service import YearEndCloseService

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "22222222-2222-2222-2222-222222222222"
JOURNAL_ID = "33333333-3333-4333-8333-333333333333"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._offset = 0
        self._null_filters: list[str] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._insert_payload: dict[str, Any] | list[dict[str, Any]] | None = None
        self._update_payload: dict[str, Any] | None = None

    def select(self, _columns: str = "*", **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._in_filters.append((key, values))
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def offset(self, offset: int) -> _Query:
        self._offset = offset
        return self

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> _Query:
        self._insert_payload = deepcopy(payload)
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            payloads = (
                self._insert_payload
                if isinstance(self._insert_payload, list)
                else [self._insert_payload]
            )
            inserted = []
            for idx, payload in enumerate(payloads, start=1):
                if self.table == "accounting_close_tasks":
                    row_id = f"close-task-created-{idx}"
                else:
                    row_id = f"{self.table}-created-{len(self.db.tables[self.table]) + idx}"
                row = {
                    "id": row_id,
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                    **payload,
                }
                self.db.tables[self.table].append(row)
                inserted.append(row)
            return _Result(deepcopy(inserted))

        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
        if self._update_payload is not None:
            for row in rows:
                row.update(self._update_payload)
            return _Result(deepcopy(rows))
        if self._order_key is not None:
            rows.sort(
                key=lambda row: str(row.get(self._order_key) or ""),
                reverse=self._order_desc,
            )
        if self._offset:
            rows = rows[self._offset :]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))

    def _matches(self, row: dict[str, Any]) -> bool:
        return (
            all(row.get(key) == value for key, value in self._eq_filters)
            and all(row.get(key) is None for key in self._null_filters)
            and all(
                row.get(key) in values or str(row.get(key)) in {str(value) for value in values}
                for key, values in self._in_filters
            )
        )


class _FakeDb:
    def __init__(self) -> None:
        locked_period = date.today().strftime("%Y-%m")
        self.table_calls: list[str] = []
        self.tables: dict[str, list[dict[str, Any]]] = {
            "tenants": [{"id": TENANT_ID, "base_currency": "SGD"}],
            "period_locks": [
                {
                    "id": "lock-1",
                    "tenant_id": TENANT_ID,
                    "period": locked_period,
                    "locked_at": "2026-06-22T00:00:00+00:00",
                    "locked_by": "admin-1",
                },
                {
                    "id": "lock-foreign",
                    "tenant_id": OTHER_TENANT_ID,
                    "period": locked_period,
                    "locked_at": "2026-06-22T00:00:00+00:00",
                    "locked_by": "admin-2",
                },
            ],
            "journal_entries": [
                {
                    "id": JOURNAL_ID,
                    "tenant_id": TENANT_ID,
                    "entry_number": "JE-0001",
                    "description": "Month-end accrual",
                    "reason": "Accrue approved June payroll before close.",
                    "entry_date": "2026-06-22",
                    "period": "2026-06",
                    "reference_type": "manual",
                    "reference_id": None,
                    "created_by": "manager-1",
                    "posted_at": "2026-06-22T00:00:00+00:00",
                },
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "tenant_id": OTHER_TENANT_ID,
                    "entry_number": "JE-FOREIGN",
                    "description": "Foreign journal",
                    "reason": "Foreign tenant manual journal reason.",
                    "entry_date": "2026-06-22",
                    "period": "2026-06",
                    "reference_type": "manual",
                    "reference_id": None,
                    "created_by": "manager-2",
                    "posted_at": "2026-06-23T00:00:00+00:00",
                },
            ],
            "journal_lines": [
                {
                    "id": "journal-line-dr",
                    "tenant_id": TENANT_ID,
                    "journal_entry_id": JOURNAL_ID,
                    "direction": "DR",
                    "account_id": "55555555-5555-4555-8555-555555555555",
                    "amount": "100.00",
                    "currency": "GBP",
                    "base_amount": "125.00",
                    "fx_rate_id": "77777777-7777-4777-8777-777777777777",
                    "description": "Foreign-currency bank receipt",
                    "accounts": {"code": "1100", "name": "Bank"},
                },
                {
                    "id": "journal-line-cr",
                    "tenant_id": TENANT_ID,
                    "journal_entry_id": JOURNAL_ID,
                    "direction": "CR",
                    "account_id": "66666666-6666-4666-8666-666666666666",
                    "amount": "100.00",
                    "currency": "GBP",
                    "base_amount": "125.00",
                    "fx_rate_id": "77777777-7777-4777-8777-777777777777",
                    "description": "Foreign-currency revenue",
                    "accounts": {"code": "4000", "name": "Revenue"},
                },
                {
                    "id": "foreign-tenant-journal-line",
                    "tenant_id": OTHER_TENANT_ID,
                    "journal_entry_id": "44444444-4444-4444-8444-444444444444",
                    "direction": "DR",
                    "account_id": "88888888-8888-4888-8888-888888888888",
                    "amount": "9999.00",
                    "currency": "USD",
                    "base_amount": "9999.00",
                    "fx_rate_id": None,
                    "description": "Must never cross tenant boundary",
                    "accounts": {"code": "9999", "name": "Foreign Tenant"},
                },
            ],
            "tenant_users": [
                {
                    "id": "tenant-user-manager",
                    "tenant_id": TENANT_ID,
                    "user_id": "manager-1",
                    "display_name": "Mina Controller",
                    "email": "finance@example.test",
                },
                {
                    "id": "foreign-tenant-user-manager",
                    "tenant_id": OTHER_TENANT_ID,
                    "user_id": "manager-1",
                    "display_name": "Foreign Tenant Controller",
                    "email": "foreign@example.test",
                },
            ],
            "accounting_close_tasks": [
                {
                    "id": "close-task-1",
                    "tenant_id": TENANT_ID,
                    "period": "2026-06",
                    "code": "trial_balance_review",
                    "title": "Review trial balance and close package",
                    "description": "Review close evidence.",
                    "owner_role": "controller",
                    "status": "open",
                    "due_date": "2026-07-05",
                    "completed_at": None,
                    "completed_by": None,
                    "evidence": {},
                    "order_index": 40,
                    "deleted_at": None,
                }
            ],
            "accounting_close_overrides": [],
            "agent_suggestions": [],
            "recurring_journal_templates": [
                {
                    "id": "template-rent",
                    "tenant_id": TENANT_ID,
                    "name": "Monthly rent accrual",
                    "description": None,
                    "schedule_day": 31,
                    "start_period": "2026-06",
                    "end_period": None,
                    "currency": "USD",
                    "is_active": True,
                    "created_by": "manager-1",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                }
            ],
            "recurring_journal_template_lines": [
                {
                    "id": "template-rent-line-1",
                    "tenant_id": TENANT_ID,
                    "template_id": "template-rent",
                    "account_id": "55555555-5555-4555-8555-555555555555",
                    "direction": "DR",
                    "amount": "100.00",
                    "description": None,
                    "order_index": 0,
                },
                {
                    "id": "template-rent-line-2",
                    "tenant_id": TENANT_ID,
                    "template_id": "template-rent",
                    "account_id": "66666666-6666-4666-8666-666666666666",
                    "direction": "CR",
                    "amount": "100.00",
                    "description": None,
                    "order_index": 1,
                },
            ],
        }

    def table(self, name: str) -> _Query:
        assert name in self.tables
        self.table_calls.append(name)
        return _Query(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


@pytest.fixture
def fake_db() -> _FakeDb:
    return _FakeDb()


@pytest.fixture
def client(fake_db: _FakeDb) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="manager-1",
        email="manager@example.com",
        role="admin",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_journal_list_returns_batch_enriched_tenant_scoped_audit_detail(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.table_calls.clear()

    response = client.get(
        "/api/v1/accounting/journal-entries?reference_type=manual&limit=10&offset=0"
    )

    assert response.status_code == 200, response.text
    assert fake_db.table_calls == [
        "journal_entries",
        "journal_lines",
        "tenant_users",
    ]
    assert response.json() == [
        {
            "id": JOURNAL_ID,
            "entry_number": "JE-0001",
            "description": "Month-end accrual",
            "reason": "Accrue approved June payroll before close.",
            "entry_date": "2026-06-22",
            "period": "2026-06",
            "reference_type": "manual",
            "reference": None,
            "created_by": "manager-1",
            "posted_by": "Mina Controller",
            "posted_at": "2026-06-22T00:00:00+00:00",
            "total_dr": "100.00",
            "lines": [
                {
                    "id": "journal-line-cr",
                    "direction": "CR",
                    "account_id": "66666666-6666-4666-8666-666666666666",
                    "account_code": "4000",
                    "account_name": "Revenue",
                    "amount": "100.00",
                    "currency": "GBP",
                    "base_amount": "125.00",
                    "fx_rate_id": "77777777-7777-4777-8777-777777777777",
                    "description": "Foreign-currency revenue",
                },
                {
                    "id": "journal-line-dr",
                    "direction": "DR",
                    "account_id": "55555555-5555-4555-8555-555555555555",
                    "account_code": "1100",
                    "account_name": "Bank",
                    "amount": "100.00",
                    "currency": "GBP",
                    "base_amount": "125.00",
                    "fx_rate_id": "77777777-7777-4777-8777-777777777777",
                    "description": "Foreign-currency bank receipt",
                },
            ],
        }
    ]
    lines = response.json()[0]["lines"]
    total_dr = sum(
        Decimal(line["amount"]) for line in lines if line["direction"] == "DR"
    )
    total_cr = sum(
        Decimal(line["amount"]) for line in lines if line["direction"] == "CR"
    )
    assert total_dr == total_cr == Decimal("100.00")
    assert all(line["account_name"] != "Foreign Tenant" for line in lines)
    assert "email" not in response.json()[0]
    assert "Foreign Tenant Controller" not in response.text


def test_journal_list_falls_back_to_actor_uuid_when_display_name_is_unavailable(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.tables["tenant_users"] = []

    response = client.get("/api/v1/accounting/journal-entries?reference_type=manual")

    assert response.status_code == 200, response.text
    assert response.json()[0]["posted_by"] == "manager-1"


def test_accounting_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_context_db = _FakeDb()
    tenant_context_db.tables = {
        "tenants": tenant_context_db.tables["tenants"],
    }
    class _CloseStatusResult:
        def as_dict(self) -> dict[str, Any]:
            return {
                "period": "2026-06",
                "status": "ready",
                "locked": False,
                "locked_at": None,
                "locked_by": None,
                "ready_to_lock": True,
                "checklist": [],
                "findings": [],
                "pending_reviews": [],
                "unposted_journals": [],
                "incomplete_tasks": [],
                "overrides": [],
                "lock_blockers": [],
            }

    class _CloseReadinessResult:
        def __init__(self) -> None:
            self.period = "2026-06"
            self.ready = True
            self.findings: list[Any] = []
            self.trial_balance_balanced = True

    def _close_status(self: CloseStatusService, period: str) -> _CloseStatusResult:
        assert period == "2026-06"
        assert self.db is fake_db
        return _CloseStatusResult()

    def _close_readiness(self: CloseReconciliationService, period: str) -> _CloseReadinessResult:
        assert period == "2026-06"
        assert self.db is fake_db
        return _CloseReadinessResult()

    def _close_package(self: ClosePackageService, period: str) -> dict[str, Any]:
        assert period == "2026-06"
        assert self.db is fake_db
        assert self._tenant_base_currency() == "SGD"
        return {
            "period": "2026-06",
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "previous_period": "2026-05",
            "generated_at": "2026-06-22T00:00:00+00:00",
            "close_status": {"status": "ready"},
            "gl_summary": {},
            "previous_gl_summary": {},
            "working_capital": {},
            "readiness_evidence": {},
            "close_overrides": [],
            "trial_balance": {},
            "ar_aging": {},
            "ap_aging": {},
            "wip": [],
            "service_line_margins": [],
            "variance_commentary": [],
        }

    monkeypatch.setattr(CloseStatusService, "get_status", _close_status)
    monkeypatch.setattr(CloseReconciliationService, "check_period", _close_readiness)
    monkeypatch.setattr(ClosePackageService, "build_package", _close_package)

    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: tenant_context_db

    periods_response = client.get("/api/v1/accounting/periods")
    journals_response = client.get(
        "/api/v1/accounting/journal-entries?reference_type=manual&limit=10&offset=0"
    )
    close_status_response = client.get("/api/v1/accounting/periods/2026-06/close-status")
    close_readiness_response = client.get("/api/v1/accounting/periods/2026-06/close-readiness")
    close_package_response = client.get("/api/v1/accounting/periods/2026-06/close-package")
    close_tasks_response = client.get("/api/v1/accounting/periods/2026-06/close-tasks")
    recurring_templates_response = client.get("/api/v1/accounting/recurring-journal-templates")

    assert periods_response.status_code == 200, periods_response.text
    current_period = date.today().strftime("%Y-%m")
    current = next(
        item for item in periods_response.json()["periods"] if item["period"] == current_period
    )
    assert current["locked"] is True
    assert current["locked_by"] == "admin-1"
    assert journals_response.status_code == 200, journals_response.text
    journals = journals_response.json()
    assert len(journals) == 1
    assert journals[0]["id"] == JOURNAL_ID
    assert journals[0]["entry_number"] == "JE-0001"
    assert journals[0]["reason"] == "Accrue approved June payroll before close."
    assert journals[0]["posted_by"] == "Mina Controller"
    assert journals[0]["total_dr"] == "100.00"
    assert len(journals[0]["lines"]) == 2
    assert close_status_response.status_code == 200, close_status_response.text
    assert close_status_response.json()["ready_to_lock"] is True
    assert close_readiness_response.status_code == 200, close_readiness_response.text
    assert close_readiness_response.json()["ready"] is True
    assert close_package_response.status_code == 200, close_package_response.text
    assert close_package_response.json()["previous_period"] == "2026-05"
    assert close_tasks_response.status_code == 200, close_tasks_response.text
    assert close_tasks_response.json()["tasks"][0]["code"] == "trial_balance_review"
    assert recurring_templates_response.status_code == 200, recurring_templates_response.text
    assert recurring_templates_response.json()["templates"][0]["id"] == "template-rent"
    assert recurring_templates_response.json()["templates"][0]["lines"][0]["direction"] == "DR"
    assert tenant_context_db.table_calls == ["tenants"]


def test_close_package_uses_service_role_only_for_authorized_tenant_currency(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_db = _FakeDb()
    service_db.tables["tenants"].append(
        {"id": OTHER_TENANT_ID, "base_currency": "USD"}
    )
    fake_db.tables.pop("tenants")
    fake_db.table_calls.clear()
    service_db.table_calls.clear()

    def _close_package(self: ClosePackageService, period: str) -> dict[str, Any]:
        assert period == "2026-06"
        assert self.db is fake_db
        base_currency = self._tenant_base_currency()
        return {
            "period": period,
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "previous_period": "2026-05",
            "generated_at": "2026-07-12T00:00:00+00:00",
            "close_status": {},
            "gl_summary": {},
            "previous_gl_summary": {},
            "working_capital": {"base_currency": base_currency},
            "readiness_evidence": {},
            "close_overrides": [],
            "trial_balance": {},
            "ar_aging": {},
            "ap_aging": {},
            "wip": [],
            "service_line_margins": [],
            "variance_commentary": [],
        }

    monkeypatch.setattr(ClosePackageService, "build_package", _close_package)
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: service_db

    response = client.get("/api/v1/accounting/periods/2026-06/close-package")

    assert response.status_code == 200, response.text
    assert response.json()["working_capital"]["base_currency"] == "SGD"
    assert "tenants" not in fake_db.table_calls
    assert service_db.table_calls == ["tenants"]


def test_manual_journal_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    posted_payloads: list[Any] = []

    async def _submit_manual_journal(
        self: ManualJournalService,
        payload: Any,
    ) -> ManualJournalEntryResponse:
        assert self.db is fake_db
        assert self.actor_role == "admin"
        assert payload.reason == "Record approved finance adjustment for API contract test."
        assert [line.currency for line in payload.lines] == [None, None]
        posted_payloads.append(payload)
        return ManualJournalEntryResponse(
            id=JOURNAL_ID,
            entry_number="JE-0001",
            description="Manual adjustment",
            reason=payload.reason,
            entry_date="2026-06-22",
            period="2026-06",
            reference_type="manual",
            reference=None,
            created_by="manager-1",
            posted_at="2026-06-22T00:00:00+00:00",
            lines=[],
        )

    monkeypatch.setattr(ManualJournalService, "submit_manual_journal", _submit_manual_journal)

    response = client.post(
        "/api/v1/accounting/journal-entries",
        json={
            "description": "Manual adjustment",
            "reason": "Record approved finance adjustment for API contract test.",
            "entry_date": "2026-06-22",
            "lines": [
                {
                    "direction": "DR",
                    "account_id": "55555555-5555-4555-8555-555555555555",
                    "amount": "100.00",
                },
                {
                    "direction": "CR",
                    "account_id": "66666666-6666-4666-8666-666666666666",
                    "amount": "100.00",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == JOURNAL_ID
    assert response.json()["reason"] == "Record approved finance adjustment for API contract test."
    assert len(posted_payloads) == 1


def test_manual_journal_create_can_return_pending_approval(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    async def _submit_manual_journal(
        self: ManualJournalService,
        payload: Any,
    ) -> ManualJournalApprovalTaskResponse:
        assert self.db is fake_db
        assert payload.reason == "Route high value adjustment through approval."
        return ManualJournalApprovalTaskResponse(
            task_id="hitl-task-1",
            suggestion_id="suggestion-1",
            required_approval_role="admin",
            approval_policy_reason="manual_journal_above_approval_threshold",
            total_debits="15000.00",
            threshold="10000.00",
            message="Manual journal routed to Inbox for approval before posting.",
        )

    monkeypatch.setattr(ManualJournalService, "submit_manual_journal", _submit_manual_journal)

    response = client.post(
        "/api/v1/accounting/journal-entries",
        json={
            "description": "Manual adjustment",
            "reason": "Route high value adjustment through approval.",
            "entry_date": "2026-06-22",
            "lines": [
                {
                    "direction": "DR",
                    "account_id": "55555555-5555-4555-8555-555555555555",
                    "amount": "15000.00",
                    "currency": "USD",
                },
                {
                    "direction": "CR",
                    "account_id": "66666666-6666-4666-8666-666666666666",
                    "amount": "15000.00",
                    "currency": "USD",
                },
            ],
        },
    )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "pending_approval"
    assert body["task_id"] == "hitl-task-1"
    assert body["required_approval_role"] == "admin"


def test_manual_journal_reverse_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    async def _reverse_manual_journal(
        self: ManualJournalService,
        journal_entry_id: str,
        payload: Any,
    ) -> ManualJournalEntryResponse:
        assert self.db is fake_db
        assert self.actor_role == "admin"
        assert journal_entry_id == JOURNAL_ID
        assert payload.reason == "Reverse duplicate accrual after review."
        return ManualJournalEntryResponse(
            id="journal-reversal",
            entry_number="JE-R1",
            description="Reversal of JE-0001",
            reason=payload.reason,
            entry_date="2026-06-23",
            period="2026-06",
            reference_type="manual_reversal",
            reference=JOURNAL_ID,
            created_by="manager-1",
            posted_at="2026-06-23T00:00:00+00:00",
            lines=[],
        )

    monkeypatch.setattr(ManualJournalService, "reverse_manual_journal", _reverse_manual_journal)

    response = client.post(
        f"/api/v1/accounting/journal-entries/{JOURNAL_ID}/reverse",
        json={
            "entry_date": "2026-06-23",
            "reason": "Reverse duplicate accrual after review.",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] == "journal-reversal"
    assert body["reference"] == JOURNAL_ID


def _recurring_template_payload(*, currency: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Monthly depreciation",
        "schedule_day": 31,
        "start_period": "2026-06",
        "lines": [
            {
                "direction": "DR",
                "account_id": "55555555-5555-4555-8555-555555555555",
                "amount": "100.00",
            },
            {
                "direction": "CR",
                "account_id": "66666666-6666-4666-8666-666666666666",
                "amount": "100.00",
            },
        ],
    }
    if currency is not None:
        payload["currency"] = currency
    return payload


def test_recurring_journal_template_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/accounting/recurring-journal-templates",
        json=_recurring_template_payload(),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Monthly depreciation"
    assert body["schedule_day"] == 31
    assert body["currency"] == "SGD"
    assert len(body["lines"]) == 2
    assert body["lines"][0]["amount"] == "100.00"
    created = fake_db.tables["recurring_journal_templates"][-1]
    assert created["currency"] == "SGD"


def test_recurring_journal_template_preserves_explicit_foreign_currency(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    response = client.post(
        "/api/v1/accounting/recurring-journal-templates",
        json=_recurring_template_payload(currency="gbp"),
    )

    assert response.status_code == 201, response.text
    assert response.json()["currency"] == "GBP"
    assert fake_db.tables["recurring_journal_templates"][-1]["currency"] == "GBP"


@pytest.mark.parametrize("base_currency", [None, "ÅBC"])
def test_recurring_journal_template_omission_rejects_invalid_tenant_base_currency(
    client: TestClient,
    fake_db: _FakeDb,
    base_currency: str | None,
) -> None:
    fake_db.tables["tenants"][0]["base_currency"] = base_currency

    response = client.post(
        "/api/v1/accounting/recurring-journal-templates",
        json=_recurring_template_payload(),
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == "Tenant base currency is not configured"


def test_close_task_bootstrap_and_update_use_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    fake_db.tables["accounting_close_tasks"] = []

    bootstrap = client.post("/api/v1/accounting/periods/2026-06/close-tasks/bootstrap")
    update = client.patch(
        "/api/v1/accounting/periods/2026-06/close-tasks/close-task-created-1",
        json={"status": "done", "evidence": {"reviewed": True}},
    )

    assert bootstrap.status_code == 200, bootstrap.text
    assert len(bootstrap.json()["tasks"]) == 6
    assert update.status_code == 200, update.text
    body = update.json()
    assert body["status"] == "done"
    assert body["completed_by"] == "manager-1"
    assert body["evidence"] == {"reviewed": True}


def test_close_override_create_uses_service_role_and_records_actor(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/accounting/periods/2026-06/close-overrides",
        json={
            "blocker_code": "unposted_journals",
            "reason": "Controller confirmed the draft journal should be excluded.",
            "blocker_ref": {"journal_entry_id": "journal-draft-001"},
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["blocker_code"] == "unposted_journals"
    assert body["created_by"] == "manager-1"
    assert body["created_by_role"] == "admin"
    assert fake_db.tables["accounting_close_overrides"][0]["reason"].startswith(
        "Controller confirmed"
    )
    assert fake_db.tables["accounting_close_overrides"][0]["created_by_role"] == "admin"


def test_lock_period_requires_matching_override_for_reconciliation_blocker(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    fake_db.tables["period_locks"] = []
    fake_db.tables["accounting_close_tasks"] = []

    def _blocked_reconciliation(
        self: CloseReconciliationService,
        period: str,
    ) -> CloseReconciliationResult:
        assert self.db is fake_db
        return CloseReconciliationResult(
            period=period,
            ready=False,
            trial_balance_balanced=True,
            findings=[
                ReconciliationFinding(
                    code="missing_invoice_journal",
                    source_table="invoices",
                    source_id="invoice-1",
                    source_number="INV-001",
                    reason="Approved invoice has no posted AR journal.",
                    expected_reference_type="invoice",
                )
            ],
        )

    monkeypatch.setattr(CloseReconciliationService, "check_period", _blocked_reconciliation)

    blocked = client.post("/api/v1/accounting/periods/2026-06/lock")
    allowed = client.post(
        "/api/v1/accounting/periods/2026-06/lock",
        json={
            "overrides": [
                {
                    "blocker_code": "subledger_reconciliation",
                    "reason": "Controller reconciled the invoice externally for this close.",
                    "blocker_ref": {"invoice_id": "invoice-1"},
                }
            ]
        },
    )

    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "close_reconciliation_failed"
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["override_count"] == 1
    assert fake_db.tables["accounting_close_overrides"][0]["blocker_code"] == (
        "subledger_reconciliation"
    )
    assert fake_db.tables["period_locks"][0]["period"] == "2026-06"


def test_year_end_close_route_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    def _post_year_end_close(self: YearEndCloseService, year: int) -> dict[str, Any]:
        assert self.db is fake_db
        assert self.tenant_id == TENANT_ID
        assert self.user_id == "manager-1"
        assert year == 2026
        return {
            "year": 2026,
            "period": "2026-12",
            "entry_date": "2026-12-31",
            "journal_entry_id": "journal-year-end-2026",
            "entry_number": "YE-2026",
            "posted_at": "2026-12-31T23:59:00+00:00",
            "net_income": "900.00",
            "retained_earnings_direction": "CR",
            "retained_earnings_amount": "900.00",
            "retained_earnings_account": {
                "id": "acct-3000",
                "code": "3000",
                "name": "Retained Earnings",
            },
            "revenue_closed": "1200.00",
            "expenses_closed": "300.00",
            "line_count": 3,
        }

    monkeypatch.setattr(YearEndCloseService, "post_year_end_close", _post_year_end_close)

    response = client.post("/api/v1/accounting/years/2026/year-end-close")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["entry_number"] == "YE-2026"
    assert body["retained_earnings_direction"] == "CR"
    assert body["net_income"] == "900.00"


def test_expense_accrual_proposal_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    async def _write_suggestions(
        deps: Any,
        period: str,
        *,
        debit_account_code: str,
        credit_account_code: str,
    ) -> dict[str, Any]:
        assert deps.db is fake_db
        assert deps.tenant_id == TENANT_ID
        assert deps.user_id == "manager-1"
        assert period == "2026-06"
        assert debit_account_code == "5100"
        assert credit_account_code == "2100"
        return {
            "period": period,
            "proposal_count": 1,
            "created_count": 1,
            "skipped_duplicates": 0,
            "suggestion_ids": ["suggestion-expense-accrual-001"],
            "proposals": [
                {
                    "proposal_type": "employee_reimbursement_accrual",
                    "expense_ids": ["expense-1"],
                }
            ],
        }

    monkeypatch.setattr(
        "app.agents.accrual_agent.write_employee_reimbursement_accrual_suggestions",
        _write_suggestions,
    )

    response = client.post("/api/v1/accounting/periods/2026-06/propose-expense-accrual")

    assert response.status_code == 200, response.text
    assert response.json()["created_count"] == 1
    assert response.json()["proposals"][0]["expense_ids"] == ["expense-1"]


def test_milestone_recognition_proposal_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    async def _write_suggestions(
        deps: Any,
        period: str,
        *,
        deferred_account_code: str,
        revenue_account_code: str,
    ) -> dict[str, Any]:
        assert deps.db is fake_db
        assert deps.tenant_id == TENANT_ID
        assert deps.user_id == "manager-1"
        assert period == "2026-06"
        assert deferred_account_code == "2200"
        assert revenue_account_code == "4000"
        return {
            "period": period,
            "proposal_count": 1,
            "created_count": 1,
            "skipped_duplicates": 0,
            "suggestion_ids": ["suggestion-milestone-001"],
            "proposals": [
                {
                    "proposal_type": "milestone_revenue_recognition",
                    "phase_id": "phase-discovery",
                }
            ],
        }

    monkeypatch.setattr(
        "app.agents.revenue_recognition_agent.write_milestone_revenue_recognition_suggestions",
        _write_suggestions,
    )

    response = client.post("/api/v1/accounting/periods/2026-06/propose-milestone-recognition")

    assert response.status_code == 200, response.text
    assert response.json()["created_count"] == 1
    assert response.json()["proposals"][0]["phase_id"] == "phase-discovery"


def test_percentage_completion_recognition_proposal_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    async def _write_suggestions(
        deps: Any,
        period: str,
        *,
        asset_account_code: str,
        revenue_account_code: str,
    ) -> dict[str, Any]:
        assert deps.db is fake_db
        assert deps.tenant_id == TENANT_ID
        assert deps.user_id == "manager-1"
        assert period == "2026-06"
        assert asset_account_code == "1200"
        assert revenue_account_code == "4000"
        return {
            "period": period,
            "proposal_count": 1,
            "created_count": 1,
            "skipped_duplicates": 0,
            "suggestion_ids": ["suggestion-poc-001"],
            "proposals": [
                {
                    "proposal_type": "percentage_completion_revenue_recognition",
                    "phase_id": "phase-build",
                }
            ],
        }

    monkeypatch.setattr(
        "app.agents.revenue_recognition_agent."
        "write_percentage_completion_revenue_recognition_suggestions",
        _write_suggestions,
    )

    response = client.post(
        "/api/v1/accounting/periods/2026-06/propose-percentage-completion-recognition"
    )

    assert response.status_code == 200, response.text
    assert response.json()["created_count"] == 1
    assert response.json()["proposals"][0]["phase_id"] == "phase-build"


def test_prepaid_amortization_proposal_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    async def _write_suggestions(
        deps: Any,
        period: str,
        *,
        prepaid_account_code: str,
        expense_account_code: str,
    ) -> dict[str, Any]:
        assert deps.db is fake_db
        assert deps.tenant_id == TENANT_ID
        assert deps.user_id == "manager-1"
        assert period == "2026-06"
        assert prepaid_account_code == "1500"
        assert expense_account_code == "5000"
        return {
            "period": period,
            "proposal_count": 1,
            "created_count": 1,
            "skipped_duplicates": 0,
            "suggestion_ids": ["suggestion-prepaid-001"],
            "proposals": [
                {
                    "proposal_type": "prepaid_expense_amortization",
                    "bill_line_id": "bill-line-prepaid",
                }
            ],
        }

    monkeypatch.setattr(
        "app.agents.prepaid_amortization_agent.write_prepaid_amortization_suggestions",
        _write_suggestions,
    )

    response = client.post("/api/v1/accounting/periods/2026-06/propose-prepaid-amortization")

    assert response.status_code == 200, response.text
    assert response.json()["created_count"] == 1
    assert response.json()["proposals"][0]["bill_line_id"] == "bill-line-prepaid"


def test_recurring_journal_proposal_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    async def _write_suggestions(
        deps: Any,
        period: str,
    ) -> dict[str, Any]:
        assert deps.db is fake_db
        assert deps.tenant_id == TENANT_ID
        assert deps.user_id == "manager-1"
        assert period == "2026-06"
        return {
            "period": period,
            "proposal_count": 1,
            "created_count": 1,
            "skipped_duplicates": 0,
            "suggestion_ids": ["suggestion-recurring-001"],
            "proposals": [
                {
                    "proposal_type": "recurring_journal",
                    "template_id": "template-rent",
                }
            ],
        }

    monkeypatch.setattr(
        "app.agents.recurring_journal_agent.write_recurring_journal_suggestions",
        _write_suggestions,
    )

    response = client.post("/api/v1/accounting/periods/2026-06/propose-recurring-journals")

    assert response.status_code == 200, response.text
    assert response.json()["created_count"] == 1
    assert response.json()["proposals"][0]["template_id"] == "template-rent"
