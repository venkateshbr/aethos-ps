"""Accounting API contract tests for bounded RLS reads and service-role writes."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app
from app.models.accounting import ManualJournalEntryResponse
from app.services.close_package_service import ClosePackageService
from app.services.close_reconciliation_service import CloseReconciliationService
from app.services.close_status_service import CloseStatusService
from app.services.manual_journal_service import ManualJournalService

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
                row = {
                    "id": f"close-task-created-{idx}",
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
        return all(row.get(key) == value for key, value in self._eq_filters) and all(
            row.get(key) is None for key in self._null_filters
        )


class _FakeDb:
    def __init__(self) -> None:
        locked_period = date.today().strftime("%Y-%m")
        self.tables: dict[str, list[dict[str, Any]]] = {
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
                    "entry_date": "2026-06-22",
                    "period": "2026-06",
                    "reference_type": "manual",
                    "reference_id": None,
                    "created_by": "manager-2",
                    "posted_at": "2026-06-23T00:00:00+00:00",
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
        }

    def table(self, name: str) -> _Query:
        assert name in self.tables
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


def test_accounting_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    def _close_readiness(
        self: CloseReconciliationService, period: str
    ) -> _CloseReadinessResult:
        assert period == "2026-06"
        assert self.db is fake_db
        return _CloseReadinessResult()

    def _close_package(self: ClosePackageService, period: str) -> dict[str, Any]:
        assert period == "2026-06"
        assert self.db is fake_db
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
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    periods_response = client.get("/api/v1/accounting/periods")
    journals_response = client.get(
        "/api/v1/accounting/journal-entries?reference_type=manual&limit=10&offset=0"
    )
    close_status_response = client.get(
        "/api/v1/accounting/periods/2026-06/close-status"
    )
    close_readiness_response = client.get(
        "/api/v1/accounting/periods/2026-06/close-readiness"
    )
    close_package_response = client.get(
        "/api/v1/accounting/periods/2026-06/close-package"
    )
    close_tasks_response = client.get(
        "/api/v1/accounting/periods/2026-06/close-tasks"
    )

    assert periods_response.status_code == 200, periods_response.text
    current_period = date.today().strftime("%Y-%m")
    current = next(
        item
        for item in periods_response.json()["periods"]
        if item["period"] == current_period
    )
    assert current["locked"] is True
    assert current["locked_by"] == "admin-1"
    assert journals_response.status_code == 200, journals_response.text
    assert journals_response.json() == [
        {
            "id": JOURNAL_ID,
            "entry_number": "JE-0001",
            "description": "Month-end accrual",
            "entry_date": "2026-06-22",
            "period": "2026-06",
            "reference_type": "manual",
            "reference": None,
            "created_by": "manager-1",
            "posted_at": "2026-06-22T00:00:00+00:00",
        }
    ]
    assert close_status_response.status_code == 200, close_status_response.text
    assert close_status_response.json()["ready_to_lock"] is True
    assert close_readiness_response.status_code == 200, close_readiness_response.text
    assert close_readiness_response.json()["ready"] is True
    assert close_package_response.status_code == 200, close_package_response.text
    assert close_package_response.json()["previous_period"] == "2026-05"
    assert close_tasks_response.status_code == 200, close_tasks_response.text
    assert close_tasks_response.json()["tasks"][0]["code"] == "trial_balance_review"


def test_manual_journal_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    post_mock = AsyncMock(
        return_value=ManualJournalEntryResponse(
            id=JOURNAL_ID,
            entry_number="JE-0001",
            description="Manual adjustment",
            entry_date="2026-06-22",
            period="2026-06",
            reference_type="manual",
            reference=None,
            created_by="manager-1",
            posted_at="2026-06-22T00:00:00+00:00",
            lines=[],
        )
    )
    monkeypatch.setattr(ManualJournalService, "post_manual_journal", post_mock)

    response = client.post(
        "/api/v1/accounting/journal-entries",
        json={
            "description": "Manual adjustment",
            "entry_date": "2026-06-22",
            "lines": [
                {
                    "direction": "DR",
                    "account_id": "55555555-5555-4555-8555-555555555555",
                    "amount": "100.00",
                    "currency": "USD",
                },
                {
                    "direction": "CR",
                    "account_id": "66666666-6666-4666-8666-666666666666",
                    "amount": "100.00",
                    "currency": "USD",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == JOURNAL_ID
    post_mock.assert_awaited_once()


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
    assert len(bootstrap.json()["tasks"]) == 5
    assert update.status_code == 200, update.text
    body = update.json()
    assert body["status"] == "done"
    assert body["completed_by"] == "manager-1"
    assert body["evidence"] == {"reviewed": True}
