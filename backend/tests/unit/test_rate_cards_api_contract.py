"""Rate-card API contract tests for RLS-backed reads and service-role writes."""

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
        self._insert_payload: dict[str, Any] | list[dict[str, Any]] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> _Query:
        self._insert_payload = payload
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            payloads = (
                self._insert_payload
                if isinstance(self._insert_payload, list)
                else [self._insert_payload]
            )
            rows: list[dict[str, Any]] = []
            for index, payload in enumerate(payloads, start=1):
                row = {
                    "id": f"{self.table}-{index}",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                    **payload,
                }
                if self.table == "rate_cards":
                    row["id"] = "rate-card-created"
                self.db.tables[self.table].append(row)
                rows.append(row)
            return _Result(rows)

        return _Result(self._filtered_rows())

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
            "rate_cards": [
                {
                    "id": "rate-card-standard",
                    "tenant_id": TENANT_ID,
                    "name": "Standard 2026",
                    "currency": "USD",
                    "effective_date": "2026-01-01",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                }
            ],
            "rate_card_lines": [
                {
                    "id": "line-1",
                    "tenant_id": TENANT_ID,
                    "rate_card_id": "rate-card-standard",
                    "role": "Senior Consultant",
                    "rate": "275.00",
                }
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


def test_rate_card_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/rate-cards")
    detail_response = client.get("/api/v1/rate-cards/rate-card-standard")

    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["lines"][0]["rate"] == "275.00"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["id"] == "rate-card-standard"


def test_rate_card_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/rate-cards",
        json={
            "name": "Created 2026",
            "currency": "USD",
            "effective_date": "2026-07-01",
            "lines": [{"role": "Manager", "rate": "325.00"}],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == "rate-card-created"
    assert response.json()["lines"][0]["role"] == "Manager"
