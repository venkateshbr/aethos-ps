"""Reports API contract tests for RLS-backed read dependency wiring."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "22222222-2222-2222-2222-222222222222"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._null_filters: list[str] = []

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

    def execute(self) -> _Result:
        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
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
        return True


class _FakeDb:
    def __init__(self) -> None:
        due_date = (date.today() - timedelta(days=10)).isoformat()
        self.tables: dict[str, list[dict[str, Any]]] = {
            "invoices": [
                {
                    "id": "invoice-1",
                    "tenant_id": TENANT_ID,
                    "total": "250.00",
                    "currency": "USD",
                    "due_date": due_date,
                    "status": "approved",
                    "deleted_at": None,
                },
                {
                    "id": "invoice-foreign",
                    "tenant_id": OTHER_TENANT_ID,
                    "total": "999.00",
                    "currency": "USD",
                    "due_date": due_date,
                    "status": "approved",
                    "deleted_at": None,
                },
            ]
        }

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


def test_reports_router_uses_rls_client() -> None:
    fake_db = _FakeDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/reports/ar-aging")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["total"] == "250.00"
