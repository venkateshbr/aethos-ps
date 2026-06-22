"""Engagements API contract tests for RLS-backed reads and service-role writes."""

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
        self._update_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
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
                    "client_id": "client-1",
                    "code": "ENG-0001",
                    "name": "Monthly Advisory",
                    "billing_arrangement": "retainer",
                    "currency": "USD",
                    "total_value": "120000.00",
                    "status": "active",
                    "description": "Recurring advisory services",
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                    "service_line": "advisory",
                    "rate_card_id": None,
                    "service_catalogue_id": None,
                },
                {
                    "id": "eng-2",
                    "tenant_id": TENANT_ID,
                    "client_id": "client-2",
                    "code": "ENG-0002",
                    "name": "Tax Filing",
                    "billing_arrangement": "fixed_fee",
                    "currency": "USD",
                    "total_value": "15000.00",
                    "status": "draft",
                    "description": None,
                    "start_date": None,
                    "end_date": None,
                    "created_at": "2026-06-21T00:00:00+00:00",
                    "deleted_at": None,
                    "service_line": "tax",
                    "rate_card_id": None,
                    "service_catalogue_id": None,
                },
            ],
            "engagement_billing_terms": [
                {
                    "id": "terms-1",
                    "tenant_id": TENANT_ID,
                    "engagement_id": "eng-1",
                    "fixed_fee_amount": None,
                    "milestone_total": None,
                    "retainer_monthly_amount": "10000.00",
                    "retainer_floor": "8000.00",
                    "retainer_rollover": True,
                    "cap_amount": None,
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


def test_engagement_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/engagements?status=active&client_id=client-1")
    detail_response = client.get("/api/v1/engagements/eng-1")

    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == "eng-1"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["billing_terms"]["retainer_monthly_amount"] == "10000.00"


def test_engagement_status_update_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.patch("/api/v1/engagements/eng-2/status", json={"status": "active"})

    assert response.status_code == 200, response.text
    assert response.json()["id"] == "eng-2"
    assert response.json()["status"] == "active"
