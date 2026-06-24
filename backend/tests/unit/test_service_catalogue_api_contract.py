"""Service catalogue API contract tests for Settings UI."""

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


class _ServiceCatalogueQuery:
    def __init__(self, db: _FakeDb, rows: list[dict[str, Any]]) -> None:
        self.db = db
        self.rows = list(rows)
        self.update_payload: dict[str, Any] | None = None

    def select(self, _columns: str) -> _ServiceCatalogueQuery:
        return self

    def eq(self, key: str, value: Any) -> _ServiceCatalogueQuery:
        self.rows = [row for row in self.rows if row.get(key) == value]
        return self

    def order(self, key: str) -> _ServiceCatalogueQuery:
        self.rows = sorted(self.rows, key=lambda row: row.get(key) or "")
        return self

    def update(self, payload: dict[str, Any]) -> _ServiceCatalogueQuery:
        self.update_payload = payload
        return self

    def execute(self) -> _Result:
        if self.update_payload is not None:
            for row in self.rows:
                row.update(self.update_payload)
            return _Result(deepcopy(self.rows))
        return _Result(deepcopy(self.rows))


class _ServiceCatalogueTable:
    def __init__(self, db: _FakeDb) -> None:
        self.db = db

    def select(self, columns: str) -> _ServiceCatalogueQuery:
        return _ServiceCatalogueQuery(self.db, self.db.services).select(columns)

    def insert(self, payload: dict[str, Any]) -> _ServiceCatalogueQuery:
        row = {
            "id": "created-service",
            "description": None,
            "default_rate": None,
            "revenue_account_id": None,
            "revenue_account": None,
            "is_active": True,
            **payload,
        }
        self.db.services.append(row)
        return _ServiceCatalogueQuery(self.db, [row])

    def update(self, payload: dict[str, Any]) -> _ServiceCatalogueQuery:
        return _ServiceCatalogueQuery(self.db, self.db.services).update(payload)


class _FakeDb:
    def __init__(self) -> None:
        self.services = [
            {
                "id": "svc-tax",
                "tenant_id": TENANT_A,
                "code": "TAX-001",
                "name": "Corporation Tax Return",
                "description": "Annual corporate tax return",
                "service_line": "tax",
                "billing_unit": "fixed",
                "default_rate": "1200.00",
                "default_currency": "GBP",
                "revenue_account_id": "acct-tax",
                "revenue_account": {"code": "4001", "name": "Revenue - Tax Services"},
                "is_active": True,
                "is_system": True,
            },
            {
                "id": "svc-inactive",
                "tenant_id": TENANT_A,
                "code": "ADV-OLD",
                "name": "Inactive Advisory",
                "description": None,
                "service_line": "advisory",
                "billing_unit": "hour",
                "default_rate": "250.00",
                "default_currency": "GBP",
                "revenue_account_id": None,
                "revenue_account": None,
                "is_active": False,
                "is_system": False,
            },
            {
                "id": "svc-foreign",
                "tenant_id": TENANT_B,
                "code": "TAX-FOREIGN",
                "name": "Foreign Tenant Tax",
                "description": None,
                "service_line": "tax",
                "billing_unit": "fixed",
                "default_rate": "999.00",
                "default_currency": "USD",
                "revenue_account_id": None,
                "revenue_account": None,
                "is_active": True,
                "is_system": False,
            },
        ]

    def table(self, name: str) -> _ServiceCatalogueTable:
        assert name == "service_catalogue"
        return _ServiceCatalogueTable(self)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"service-role client should not read {name}")


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
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_services_uses_rls_client_and_returns_current_tenant(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    response = client.get("/api/v1/services")

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert response.json()["items"][0] == {
        "id": "svc-tax",
        "code": "TAX-001",
        "name": "Corporation Tax Return",
        "description": "Annual corporate tax return",
        "service_line": "tax",
        "billing_unit": "fixed",
        "default_rate": "1200.00",
        "default_currency": "GBP",
        "revenue_account_id": "acct-tax",
        "revenue_account_code": "4001",
        "revenue_account_name": "Revenue - Tax Services",
        "is_active": True,
        "is_system": True,
    }
    assert {row["tenant_id"] for row in fake_db.services} == {TENANT_A, TENANT_B}


def test_list_services_supports_filters(client: TestClient) -> None:
    response = client.get("/api/v1/services?active_only=false&service_line=advisory")

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == "svc-inactive"


def test_get_service_uses_read_dependency(client: TestClient) -> None:
    response = client.get("/api/v1/services/svc-tax")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == "svc-tax"


def test_create_service_keeps_write_path_on_service_role(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    response = client.post(
        "/api/v1/services",
        json={
            "code": "ADV-001",
            "name": "Board Advisory",
            "service_line": "advisory",
            "billing_unit": "hour",
            "default_currency": "GBP",
        },
    )

    assert response.status_code == 201, response.text
    created = fake_db.services[-1]
    assert created["tenant_id"] == TENANT_A
    assert created["is_system"] is False
    assert response.json()["id"] == "created-service"
