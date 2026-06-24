"""Expenses API contract tests for the Expenses page."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data
        self.count = len(data)


class _Query:
    def __init__(self, db: _FakeDb, table_name: str, rows: list[dict[str, Any]]) -> None:
        self.db = db
        self.table_name = table_name
        self.rows = list(rows)

    def select(self, _columns: str, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if row.get(key) == value]
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self.rows = [row for row in self.rows if row.get(key) is None]
        return self

    def gte(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if row.get(key) >= value]
        return self

    def lte(self, key: str, value: Any) -> _Query:
        self.rows = [row for row in self.rows if row.get(key) <= value]
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self.rows = sorted(self.rows, key=lambda row: row.get(key) or "", reverse=desc)
        return self

    def limit(self, count: int) -> _Query:
        self.rows = self.rows[:count]
        return self

    def execute(self) -> _Result:
        return _Result(deepcopy(self.rows))


class _Table:
    def __init__(self, db: _FakeDb, table_name: str) -> None:
        self.db = db
        self.table_name = table_name

    def select(self, columns: str, **kwargs: Any) -> _Query:
        return _Query(self.db, self.table_name, self.db.rows[self.table_name]).select(
            columns,
            **kwargs,
        )

    def insert(self, payload: dict[str, Any]) -> _Query:
        row = {
            "id": "created-expense",
            "created_at": "2026-06-22T00:00:00Z",
            "updated_at": "2026-06-22T00:00:00Z",
            "deleted_at": None,
            "document_id": None,
            "billing_status": "unbilled",
            **payload,
        }
        self.db.rows[self.table_name].append(row)
        return _Query(self.db, self.table_name, [row])


class _FakeDb:
    def __init__(self) -> None:
        self.rows = {
            "projects": [
                {"id": "proj-a", "tenant_id": TENANT_A, "deleted_at": None},
                {"id": "proj-b", "tenant_id": TENANT_B, "deleted_at": None},
            ],
            "project_expenses": [
                {
                    "id": "expense-a-new",
                    "tenant_id": TENANT_A,
                    "project_id": "proj-a",
                    "document_id": "doc-1",
                    "description": "Client dinner",
                    "amount": "125.50",
                    "currency": "USD",
                    "expense_date": "2026-06-21",
                    "category": "meals",
                    "billable": True,
                    "billing_status": "unbilled",
                    "deleted_at": None,
                },
                {
                    "id": "expense-a-old",
                    "tenant_id": TENANT_A,
                    "project_id": "proj-a",
                    "document_id": None,
                    "description": "Office supplies",
                    "amount": "20.00",
                    "currency": "USD",
                    "expense_date": "2026-06-01",
                    "category": "office",
                    "billable": False,
                    "billing_status": "non_billable",
                    "deleted_at": None,
                },
                {
                    "id": "expense-b",
                    "tenant_id": TENANT_B,
                    "project_id": "proj-b",
                    "document_id": None,
                    "description": "Foreign expense",
                    "amount": "999.00",
                    "currency": "USD",
                    "expense_date": "2026-06-22",
                    "category": "other",
                    "billable": True,
                    "billing_status": "unbilled",
                    "deleted_at": None,
                },
            ],
        }

    def table(self, name: str) -> _Table:
        assert name in self.rows
        return _Table(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


@pytest.fixture
def fake_db() -> _FakeDb:
    return _FakeDb()


@pytest.fixture
def client(fake_db: _FakeDb) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_A
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_expenses_returns_current_tenant_rows_for_ui(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    response = client.get("/api/v1/expenses")

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": "expense-a-new",
            "project_id": "proj-a",
            "date": "2026-06-21",
            "vendor": "Client dinner",
            "amount": "125.50",
            "currency": "USD",
            "category": "meals",
            "billable": True,
            "description": "Client dinner",
            "status": "unbilled",
            "document_id": "doc-1",
        },
        {
            "id": "expense-a-old",
            "project_id": "proj-a",
            "date": "2026-06-01",
            "vendor": "Office supplies",
            "amount": "20.00",
            "currency": "USD",
            "category": "office",
            "billable": False,
            "description": "Office supplies",
            "status": "non_billable",
            "document_id": None,
        },
    ]


def test_create_project_expense_materializes_project_scoped_row(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/projects/proj-a/expenses",
        json={
            "description": "Taxi to client site",
            "amount": "42.25",
            "currency": "USD",
            "category": "travel",
            "expense_date": "2026-06-22",
            "billable": True,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == "created-expense"
    assert response.json()["project_id"] == "proj-a"
    created = fake_db.rows["project_expenses"][-1]
    assert created["tenant_id"] == TENANT_A
    assert created["project_id"] == "proj-a"
    assert created["base_amount"] == "42.25"
