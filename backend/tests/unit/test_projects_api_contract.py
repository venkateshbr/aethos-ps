"""Projects API contract tests for RLS-backed reads and service-role writes."""

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
    def __init__(self, data: Any) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._null_filters: list[str] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None
        self._single = False
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

    def order(self, key: str, *, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def range(self, start: int, end: int) -> _Query:
        self._range = (start, end)
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def single(self) -> _Query:
        self._single = True
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = {
                "id": "project-created",
                "code": "PRJ-0003",
                "budget": None,
                "status": "planning",
                "created_at": "2026-06-22T00:00:00+00:00",
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
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._single:
            return _Result(rows[0] if rows else None)
        return _Result(rows)

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        for key in self._null_filters:
            rows = [row for row in rows if row.get(key) is None]
        return rows


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "engagements": [
                {
                    "id": "eng-1",
                    "tenant_id": TENANT_ID,
                    "currency": "USD",
                    "deleted_at": None,
                }
            ],
            "projects": [
                {
                    "id": "project-alpha",
                    "tenant_id": TENANT_ID,
                    "engagement_id": "eng-1",
                    "code": "PRJ-0001",
                    "name": "Alpha",
                    "currency": "USD",
                    "budget": "50000.00",
                    "status": "active",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": "project-beta",
                    "tenant_id": TENANT_ID,
                    "engagement_id": "eng-2",
                    "code": "PRJ-0002",
                    "name": "Beta",
                    "currency": "USD",
                    "budget": "30000.00",
                    "status": "planning",
                    "created_at": "2026-06-21T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": "project-other-tenant",
                    "tenant_id": "tenant-other",
                    "engagement_id": "eng-other",
                    "code": "PRJ-9999",
                    "name": "Other Tenant",
                    "currency": "USD",
                    "budget": "1.00",
                    "status": "active",
                    "created_at": "2026-06-22T00:00:00+00:00",
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
        email="owner@example.com",
        role="owner",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_project_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/projects?engagement_id=eng-1&limit=10")
    detail_response = client.get("/api/v1/projects/project-alpha")

    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == "project-alpha"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["name"] == "Alpha"


def test_project_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/projects",
        json={
            "engagement_id": "eng-1",
            "name": "Created Project",
            "currency": "USD",
            "budget": "12000.00",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == "project-created"
    assert response.json()["tenant_id"] == TENANT_ID
    assert response.json()["engagement_id"] == "eng-1"
