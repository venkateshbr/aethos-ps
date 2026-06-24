"""Billing-run API contract tests for RLS-backed reads and service-role writes."""

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
OTHER_TENANT_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "33333333-3333-4333-8333-333333333333"
CREATED_RUN_ID = "44444444-4444-4444-8444-444444444444"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._null_filters: list[str] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._insert_payload: dict[str, Any] | None = None

    def select(self, _columns: str = "*", **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = {
                "id": CREATED_RUN_ID,
                "created_by_agent": None,
                "summary": None,
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
        return _Result(deepcopy(rows))

    def _matches(self, row: dict[str, Any]) -> bool:
        for key, value in self._eq_filters:
            if row.get(key) != value:
                return False
        for key in self._null_filters:
            if row.get(key) is not None:
                return False
        return True


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "billing_runs": [
                {
                    "id": RUN_ID,
                    "tenant_id": TENANT_ID,
                    "name": "Retainer billing June 2026",
                    "period_start": "2026-06-01",
                    "period_end": "2026-06-30",
                    "status": "draft",
                    "engagement_filter": {"engagement_ids": ["eng-1", "eng-2"]},
                    "created_by_agent": "billing_run_agent",
                    "summary": {"retainer_engagement_count": 2},
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": "55555555-5555-4555-8555-555555555555",
                    "tenant_id": OTHER_TENANT_ID,
                    "name": "Foreign billing",
                    "period_start": "2026-06-01",
                    "period_end": "2026-06-30",
                    "status": "draft",
                    "engagement_filter": None,
                    "created_by_agent": None,
                    "summary": None,
                    "created_at": "2026-06-23T00:00:00+00:00",
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


def test_billing_run_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/billing-runs")
    detail_response = client.get(f"/api/v1/billing-runs/{RUN_ID}")

    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == RUN_ID
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["summary"] == {"retainer_engagement_count": 2}


def test_billing_run_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/billing-runs",
        json={
            "name": "Retainer billing July 2026",
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
            "engagement_filter": {"engagement_ids": ["eng-3"]},
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == CREATED_RUN_ID
    assert response.json()["tenant_id"] == TENANT_ID
    assert response.json()["status"] == "draft"
    assert fake_db.tables["billing_runs"][-1]["engagement_filter"] == {
        "engagement_ids": ["eng-3"]
    }
