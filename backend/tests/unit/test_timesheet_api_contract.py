"""Timesheet API contract tests for RLS-backed reads and service-role writes."""

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

TENANT_ID = "11111111-1111-1111-1111-111111111111"
EMPLOYEE_ID = "22222222-2222-4222-8222-222222222222"
PROJECT_ID = "33333333-3333-4333-8333-333333333333"
ENGAGEMENT_ID = "44444444-4444-4444-8444-444444444444"
ENTRY_ID = "55555555-5555-4555-8555-555555555555"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _DbBase, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._null_filters: list[str] = []
        self._gte_filters: list[tuple[str, Any]] = []
        self._lte_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._insert_payload: dict[str, Any] | None = None

    def select(self, _columns: str = "*", **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def in_(self, key: str, values: list[Any]) -> _Query:
        self._in_filters.append((key, values))
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

    def order(self, key: str, desc: bool = False) -> _Query:
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
                "id": ENTRY_ID,
                "created_at": "2026-06-22T00:00:00+00:00",
                "deleted_at": None,
                **self._insert_payload,
            }
            self.db.tables[self.table].append(row)
            return _Result([deepcopy(row)])

        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
        if self._order_key is not None:
            rows.sort(
                key=lambda row: str(row.get(self._order_key) or ""),
                reverse=self._order_desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))

    def _matches(self, row: dict[str, Any]) -> bool:
        for key, value in self._eq_filters:
            if row.get(key) != value:
                return False
        for key, values in self._in_filters:
            if row.get(key) not in values:
                return False
        for key in self._null_filters:
            if row.get(key) is not None:
                return False
        for key, value in self._gte_filters:
            if row.get(key) < value:
                return False
        for key, value in self._lte_filters:
            if row.get(key) > value:
                return False
        return True


class _DbBase:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)


def _employee_row() -> dict[str, Any]:
    return {
        "id": EMPLOYEE_ID,
        "tenant_id": TENANT_ID,
        "user_id": "user-1",
        "first_name": "Taylor",
        "last_name": "Consultant",
        "deleted_at": None,
    }


class _ReadDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "employees": [_employee_row()],
                "project_assignments": [
                    {
                        "id": "assignment-1",
                        "tenant_id": TENANT_ID,
                        "employee_id": EMPLOYEE_ID,
                        "project_id": PROJECT_ID,
                        "role": "Consultant",
                    }
                ],
                "projects": [
                    {
                        "id": PROJECT_ID,
                        "tenant_id": TENANT_ID,
                        "code": "PRJ-001",
                        "name": "ERP rollout",
                        "engagement_id": ENGAGEMENT_ID,
                        "deleted_at": None,
                    }
                ],
                "engagements": [
                    {
                        "id": ENGAGEMENT_ID,
                        "tenant_id": TENANT_ID,
                        "code": "ENG-001",
                        "name": "Aethos deployment",
                    }
                ],
                "time_entries": [
                    {
                        "id": ENTRY_ID,
                        "tenant_id": TENANT_ID,
                        "project_id": PROJECT_ID,
                        "employee_id": EMPLOYEE_ID,
                        "date": "2026-06-22",
                        "hours": "4.00",
                        "description": "Configuration",
                        "billable": True,
                        "status": "draft",
                        "billing_status": "unbilled",
                        "rejected_reason": None,
                        "created_at": "2026-06-22T00:00:00+00:00",
                        "deleted_at": None,
                    }
                ],
            }
        )


class _EmployeeOnlyDb(_DbBase):
    def __init__(self) -> None:
        super().__init__({"employees": [_employee_row()]})


class _WriteDb(_DbBase):
    def __init__(self) -> None:
        super().__init__(
            {
                "project_assignments": [
                    {
                        "id": "assignment-1",
                        "tenant_id": TENANT_ID,
                        "employee_id": EMPLOYEE_ID,
                        "project_id": PROJECT_ID,
                    }
                ],
                "time_entries": [],
            }
        )


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


def _install_common_overrides() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="employee@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID


def test_timesheet_read_routes_use_rls_client() -> None:
    read_db = _ReadDb()
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: read_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            projects_response = client.get("/api/v1/timesheet/my-projects")
            entries_response = client.get(
                "/api/v1/timesheet/entries?date_from=2026-06-01&date_to=2026-06-30"
            )
    finally:
        app.dependency_overrides.clear()

    assert projects_response.status_code == 200, projects_response.text
    assert projects_response.json()["items"][0]["project_code"] == "PRJ-001"
    assert entries_response.status_code == 200, entries_response.text
    assert entries_response.json()["items"][0]["id"] == ENTRY_ID


def test_timesheet_create_uses_service_role_after_rls_employee_lookup() -> None:
    write_db = _WriteDb()
    _install_common_overrides()
    app.dependency_overrides[get_user_rls_client] = lambda: _EmployeeOnlyDb()
    app.dependency_overrides[get_service_role_client] = lambda: write_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/timesheet/entries",
                json={
                    "project_id": PROJECT_ID,
                    "date": "2026-06-22",
                    "hours": "3.50",
                    "description": "Client workshop",
                    "billable": True,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    assert response.json()["employee_id"] == EMPLOYEE_ID
    assert write_db.tables["time_entries"][0]["tenant_id"] == TENANT_ID
