"""Time-entry API contract tests for RLS-backed reads and service-role writes."""

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
        self._null_filters: list[str] = []
        self._gte_filters: list[tuple[str, Any]] = []
        self._lte_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._insert_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def gte(self, key: str, value: Any) -> _Query:
        self._gte_filters.append((key, value))
        return self

    def lte(self, key: str, value: Any) -> _Query:
        self._lte_filters.append((key, value))
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

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = {
                "id": "time-entry-created",
                "created_at": "2026-06-22T00:00:00+00:00",
                "updated_at": None,
                "deleted_at": None,
                **self._insert_payload,
            }
            self.db.tables[self.table].append(row)
            return _Result([row])

        rows = self._filtered_rows()
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
        for key in self._null_filters:
            rows = [row for row in rows if row.get(key) is None]
        for key, value in self._gte_filters:
            rows = [row for row in rows if row.get(key) >= value]
        for key, value in self._lte_filters:
            rows = [row for row in rows if row.get(key) <= value]
        return rows


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "employees": [
                {"id": "employee-1", "tenant_id": TENANT_ID, "deleted_at": None}
            ],
            "period_locks": [],
            "projects": [
                {"id": "project-1", "tenant_id": TENANT_ID, "deleted_at": None}
            ],
            "time_entries": [
                {
                    "id": "time-entry-1",
                    "tenant_id": TENANT_ID,
                    "project_id": "project-1",
                    "employee_id": "employee-1",
                    "date": "2026-06-21",
                    "hours": "6.50",
                    "description": "Client advisory work",
                    "billable": True,
                    "billing_status": "unbilled",
                    "status": "approved",
                    "approved_by": "manager-1",
                    "approved_at": "2026-06-21T12:00:00+00:00",
                    "phase_id": None,
                    "timezone": "UTC",
                    "created_at": "2026-06-21T00:00:00+00:00",
                    "updated_at": None,
                    "deleted_at": None,
                },
                {
                    "id": "time-entry-2",
                    "tenant_id": TENANT_ID,
                    "project_id": "project-1",
                    "employee_id": "employee-1",
                    "date": "2026-05-31",
                    "hours": "2.00",
                    "description": "Older work",
                    "billable": True,
                    "billing_status": "billed",
                    "status": "approved",
                    "approved_by": "manager-1",
                    "approved_at": "2026-05-31T12:00:00+00:00",
                    "phase_id": None,
                    "timezone": "UTC",
                    "created_at": "2026-05-31T00:00:00+00:00",
                    "updated_at": None,
                    "deleted_at": None,
                },
            ],
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
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_time_entry_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get(
        "/api/v1/time-entries?"
        "project_id=project-1&employee_id=employee-1&date_from=2026-06-01"
        "&date_to=2026-06-30&billing_status=unbilled&limit=10"
    )
    detail_response = client.get("/api/v1/time-entries/time-entry-1")

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["id"] == "time-entry-1"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["hours"] == "6.50"


def test_time_entry_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/time-entries",
        json={
            "project_id": "project-1",
            "employee_id": "employee-1",
            "date": "2026-06-22",
            "hours": "4.25",
            "description": "Follow-up advisory work",
            "billable": True,
            "timezone": "UTC",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == "time-entry-created"
    assert response.json()["tenant_id"] == TENANT_ID
    assert response.json()["approved_by"] == "user-1"
