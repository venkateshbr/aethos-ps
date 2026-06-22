"""Clients API contract tests for RLS-backed reads and service-role writes."""

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
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._null_filters: list[str] = []
        self._ilike_filters: list[tuple[str, str]] = []
        self._insert_payload: dict[str, Any] | None = None
        self._update_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
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

    def ilike(self, key: str, pattern: str) -> _Query:
        self._ilike_filters.append((key, pattern))
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
                "id": "client-created",
                "created_at": "2026-06-22T00:00:00+00:00",
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

        return _Result(rows)

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self._in_filters:
            rows = [row for row in rows if row.get(key) in values]
        for key in self._null_filters:
            rows = [row for row in rows if row.get(key) is None]
        for key, pattern in self._ilike_filters:
            needle = pattern.strip("%").lower()
            rows = [row for row in rows if needle in str(row.get(key, "")).lower()]
        return rows


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "clients": [
                {
                    "id": "client-acme",
                    "tenant_id": TENANT_ID,
                    "name": "Acme Corp",
                    "kind": "customer",
                    "payment_terms_days": 30,
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": "client-bravo",
                    "tenant_id": TENANT_ID,
                    "name": "Bravo Holdings",
                    "kind": "both",
                    "payment_terms_days": 45,
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": "client-other-tenant",
                    "tenant_id": "tenant-other",
                    "name": "Other Tenant",
                    "kind": "customer",
                    "payment_terms_days": 30,
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
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


def test_client_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/clients?kind=customer&q=acme")
    detail_response = client.get("/api/v1/clients/client-acme")

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["name"] == "Acme Corp"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["id"] == "client-acme"


def test_client_writes_use_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    create_response = client.post(
        "/api/v1/clients",
        json={
            "name": "Created Client",
            "kind": "vendor",
            "payment_terms_days": 15,
        },
    )
    update_response = client.patch(
        "/api/v1/clients/client-created",
        json={"payment_terms_days": 20},
    )

    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["id"] == "client-created"
    assert create_response.json()["tenant_id"] == TENANT_ID
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["payment_terms_days"] == 20
