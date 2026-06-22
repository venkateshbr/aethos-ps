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

    def select(self, _columns: str = "*", **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
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

    def execute(self) -> _Result:
        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
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
        return all(row.get(key) == value for key, value in self._eq_filters)


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
        role="manager",
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
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    periods_response = client.get("/api/v1/accounting/periods")
    journals_response = client.get(
        "/api/v1/accounting/journal-entries?reference_type=manual&limit=10&offset=0"
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
