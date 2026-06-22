"""Tax-rates API contract tests for the Settings UI."""

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


class _TaxRatesQuery:
    def __init__(self, db: _FakeDb, rows: list[dict[str, Any]]) -> None:
        self.db = db
        self.rows = list(rows)
        self.update_payload: dict[str, Any] | None = None

    def select(self, _columns: str) -> _TaxRatesQuery:
        return self

    def eq(self, key: str, value: Any) -> _TaxRatesQuery:
        self.rows = [row for row in self.rows if row.get(key) == value]
        return self

    def is_(self, key: str, value: Any) -> _TaxRatesQuery:
        if value == "null":
            self.rows = [row for row in self.rows if row.get(key) is None]
        return self

    def order(self, key: str) -> _TaxRatesQuery:
        self.rows = sorted(self.rows, key=lambda row: row.get(key) or "")
        return self

    def limit(self, count: int) -> _TaxRatesQuery:
        self.rows = self.rows[:count]
        return self

    def update(self, payload: dict[str, Any]) -> _TaxRatesQuery:
        self.update_payload = payload
        return self

    def execute(self) -> _Result:
        if self.update_payload is not None:
            for row in self.rows:
                row.update(self.update_payload)
            return _Result(deepcopy(self.rows))
        return _Result(deepcopy(self.rows))


class _TaxRatesTable:
    def __init__(self, db: _FakeDb) -> None:
        self.db = db

    def select(self, columns: str) -> _TaxRatesQuery:
        return _TaxRatesQuery(self.db, self.db.tax_rates).select(columns)

    def insert(self, payload: dict[str, Any]) -> _TaxRatesQuery:
        row = {
            "id": "created-rate",
            "is_seeded": False,
            "deleted_at": None,
            **payload,
        }
        self.db.tax_rates.append(row)
        return _TaxRatesQuery(self.db, [row])

    def update(self, payload: dict[str, Any]) -> _TaxRatesQuery:
        return _TaxRatesQuery(self.db, self.db.tax_rates).update(payload)


class _FakeDb:
    def __init__(self) -> None:
        self.tax_rates = [
            {
                "id": "sys-gb-vat",
                "tenant_id": None,
                "country": "GB",
                "code": "VAT-20",
                "name": "UK VAT Standard Rate (20%)",
                "rate": "0.2000",
                "is_active": True,
                "is_seeded": True,
                "deleted_at": None,
            },
            {
                "id": "tenant-a-custom",
                "tenant_id": TENANT_A,
                "country": "US",
                "code": "CUSTOM-LOCAL",
                "name": "Local services tax",
                "rate": "0.0750",
                "is_active": True,
                "is_seeded": False,
                "deleted_at": None,
            },
            {
                "id": "tenant-b-custom",
                "tenant_id": TENANT_B,
                "country": "US",
                "code": "CUSTOM-FOREIGN",
                "name": "Foreign tenant tax",
                "rate": "0.0500",
                "is_active": True,
                "is_seeded": False,
                "deleted_at": None,
            },
        ]

    def table(self, name: str) -> _TaxRatesTable:
        assert name == "tax_rates"
        return _TaxRatesTable(self)


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
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_A
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_tax_rates_returns_system_and_current_tenant_rates(client: TestClient) -> None:
    response = client.get("/api/v1/tax-rates")

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": "sys-gb-vat",
            "name": "UK VAT Standard Rate (20%)",
            "rate": "20.00",
            "market": "UK",
            "is_system": True,
            "is_active": True,
        },
        {
            "id": "tenant-a-custom",
            "name": "Local services tax",
            "rate": "7.50",
            "market": "US",
            "is_system": False,
            "is_active": True,
        },
    ]


def test_create_tax_rate_accepts_percent_and_stores_fraction(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    response = client.post(
        "/api/v1/tax-rates",
        json={"name": "County tax", "rate": "8.25", "market": "US", "is_active": True},
    )

    assert response.status_code == 201, response.text
    assert response.json()["rate"] == "8.25"
    created = fake_db.tax_rates[-1]
    assert created["tenant_id"] == TENANT_A
    assert created["country"] == "US"
    assert created["rate"] == "0.0825"
    assert created["code"] == "CUSTOM-COUNTY-TAX"


def test_patch_tax_rate_toggles_only_current_tenant_custom_rate(client: TestClient) -> None:
    response = client.patch("/api/v1/tax-rates/tenant-a-custom", json={"is_active": False})

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False

    system_response = client.patch("/api/v1/tax-rates/sys-gb-vat", json={"is_active": False})
    assert system_response.status_code == 404
