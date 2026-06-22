"""Employees API contract tests for RLS-backed reads and service-role writes."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-123"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._neq_filters: list[tuple[str, Any]] = []
        self._null_filters: list[str] = []
        self._ilike_filters: list[tuple[str, str]] = []
        self._or_search: str | None = None
        self._limit: int | None = None
        self._order_key: str | None = None
        self._order_desc = False
        self._insert_payload: dict[str, Any] | None = None
        self._update_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def neq(self, key: str, value: Any) -> _Query:
        self._neq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def ilike(self, key: str, pattern: str) -> _Query:
        self._ilike_filters.append((key, pattern))
        return self

    def or_(self, expression: str) -> _Query:
        first_clause = expression.split(",", 1)[0]
        self._or_search = first_clause.rsplit(".ilike.", 1)[-1].strip("%").lower()
        return self

    def order(self, key: str, *, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = dict(payload)
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = {
                "id": "employee-created",
                "created_at": "2026-06-22T00:00:00+00:00",
                "updated_at": None,
                "deleted_at": None,
                **self._insert_payload,
            }
            self.db.tables[self.table].append(row)
            return _Result([row])

        rows = self._filtered_rows()

        if self._update_payload is not None:
            for row in rows:
                row.update(self._update_payload)
            return _Result(rows)

        if self._order_key is not None:
            rows.sort(
                key=lambda row: str(row.get(self._order_key) or ""),
                reverse=self._order_desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(rows)

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        for key, value in self._neq_filters:
            rows = [row for row in rows if row.get(key) != value]
        for key in self._null_filters:
            rows = [row for row in rows if row.get(key) is None]
        for key, pattern in self._ilike_filters:
            needle = pattern.strip("%").lower()
            rows = [row for row in rows if needle in str(row.get(key, "")).lower()]
        if self._or_search:
            needle = self._or_search
            rows = [
                row
                for row in rows
                if needle in str(row.get("first_name", "")).lower()
                or needle in str(row.get("last_name", "")).lower()
                or needle in str(row.get("email", "")).lower()
            ]
        return rows


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "employees": [
                {
                    "id": "employee-asha",
                    "tenant_id": TENANT_ID,
                    "first_name": "Asha",
                    "last_name": "Rao",
                    "email": "asha@example.com",
                    "title": "Senior Consultant",
                    "department": "Advisory",
                    "employment_type": "full_time",
                    "default_bill_rate": "275.00",
                    "default_bill_rate_currency": "USD",
                    "cost_rate": "110.00",
                    "available_hours_per_week": "40",
                    "manager_id": None,
                    "skills": ["advisory"],
                    "user_id": None,
                    "tenant_user_id": None,
                    "status": "active",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": None,
                    "deleted_at": None,
                    "practice_area": "advisory",
                    "seniority": "senior",
                },
                {
                    "id": "employee-ben",
                    "tenant_id": TENANT_ID,
                    "first_name": "Ben",
                    "last_name": "Low",
                    "email": "ben@example.com",
                    "title": "Analyst",
                    "department": "Tax",
                    "employment_type": "full_time",
                    "default_bill_rate": "150.00",
                    "default_bill_rate_currency": "USD",
                    "cost_rate": "70.00",
                    "available_hours_per_week": "40",
                    "manager_id": None,
                    "skills": ["tax"],
                    "user_id": None,
                    "tenant_user_id": None,
                    "status": "inactive",
                    "created_at": "2026-06-21T00:00:00+00:00",
                    "updated_at": None,
                    "deleted_at": None,
                    "practice_area": "tax",
                    "seniority": "analyst",
                },
            ]
        }

    def table(self, name: str) -> _Query:
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
        user_id="user-1",
        email="owner@example.com",
        role="owner",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_employee_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/employees?status=active&search=asha&limit=10")
    detail_response = client.get("/api/v1/employees/employee-asha")

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["email"] == "asha@example.com"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["id"] == "employee-asha"


def test_employee_mutations_use_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    create_response = client.post(
        "/api/v1/employees",
        json={
            "first_name": "Cara",
            "last_name": "Iyer",
            "email": "cara@example.com",
            "employment_type": "full_time",
            "default_bill_rate": "180.00",
            "default_bill_rate_currency": "USD",
            "cost_rate": "80.00",
            "available_hours_per_week": "40",
            "skills": ["accounting"],
            "practice_area": "accounting",
            "seniority": "associate",
        },
    )
    patch_response = client.patch(
        "/api/v1/employees/employee-created",
        json={"title": "Consultant", "status": "active"},
    )
    delete_response = client.delete("/api/v1/employees/employee-created")

    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["id"] == "employee-created"
    assert create_response.json()["tenant_id"] == TENANT_ID
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["title"] == "Consultant"
    assert delete_response.status_code == 204, delete_response.text
