"""Bills API contract tests for RLS-backed reads and service-role writes."""

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
CLIENT_ID = "33333333-3333-4333-8333-333333333333"
BILL_ID = "44444444-4444-4444-8444-444444444444"
OVERDUE_BILL_ID = "55555555-5555-4555-8555-555555555555"
CREATED_BILL_ID = "66666666-6666-4666-8666-666666666666"
CREATED_LINE_ID = "77777777-7777-4777-8777-777777777777"


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
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._insert_payload: dict[str, Any] | None = None
        self._update_payload: dict[str, Any] | None = None

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

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = self._insert_row()
            self.db.tables[self.table].append(row)
            return _Result([deepcopy(row)])

        if self._update_payload is not None:
            updated: list[dict[str, Any]] = []
            for row in self.db.tables[self.table]:
                if self._matches(row):
                    row.update(self._update_payload)
                    updated.append(row)
            return _Result(deepcopy(updated))

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
        return True

    def _insert_row(self) -> dict[str, Any]:
        if self.table == "bills":
            return {
                "id": CREATED_BILL_ID,
                "tenant_id": TENANT_ID,
                "bill_number": "BILL-CREATED",
                "subtotal": "0.00",
                "tax_total": "0.00",
                "total": "0.00",
                "created_at": "2026-06-22T00:00:00+00:00",
                "updated_at": "2026-06-22T00:00:00+00:00",
                "deleted_at": None,
                **self._insert_payload,
            }
        if self.table == "bill_lines":
            return {
                "id": CREATED_LINE_ID,
                "account_id": None,
                "created_at": "2026-06-22T00:00:00+00:00",
                **self._insert_payload,
            }
        raise AssertionError(f"unexpected insert into {self.table}")


class _FakeDb:
    def __init__(self) -> None:
        today = date.today()
        self.tables: dict[str, list[dict[str, Any]]] = {
            "clients": [
                {
                    "id": CLIENT_ID,
                    "tenant_id": TENANT_ID,
                    "name": "Acme Supplies",
                    "kind": "vendor",
                    "deleted_at": None,
                }
            ],
            "bill_lines": [
                {
                    "id": "88888888-8888-4888-8888-888888888888",
                    "tenant_id": TENANT_ID,
                    "bill_id": BILL_ID,
                    "description": "Cloud hosting",
                    "quantity": "1",
                    "unit_price": "100.00",
                    "amount": "100.00",
                    "tax_amount": "0.00",
                    "account_id": None,
                    "created_at": "2026-06-20T00:00:00+00:00",
                }
            ],
            "bills": [
                {
                    "id": BILL_ID,
                    "tenant_id": TENANT_ID,
                    "client_id": CLIENT_ID,
                    "bill_number": "BILL-0001",
                    "currency": "USD",
                    "subtotal": "100.00",
                    "tax_total": "0.00",
                    "total": "100.00",
                    "status": "approved",
                    "issue_date": today.isoformat(),
                    "due_date": today.isoformat(),
                    "vendor_invoice_number": "AWS-100",
                    "notes": None,
                    "created_at": "2026-06-20T00:00:00+00:00",
                    "updated_at": "2026-06-20T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": OVERDUE_BILL_ID,
                    "tenant_id": TENANT_ID,
                    "client_id": CLIENT_ID,
                    "bill_number": "BILL-0002",
                    "currency": "USD",
                    "subtotal": "50.00",
                    "tax_total": "0.00",
                    "total": "50.00",
                    "status": "partially_paid",
                    "issue_date": (today - timedelta(days=20)).isoformat(),
                    "due_date": (today - timedelta(days=10)).isoformat(),
                    "vendor_invoice_number": "OFFICE-50",
                    "notes": None,
                    "created_at": "2026-06-19T00:00:00+00:00",
                    "updated_at": "2026-06-19T00:00:00+00:00",
                    "deleted_at": None,
                },
                {
                    "id": "99999999-9999-4999-8999-999999999999",
                    "tenant_id": OTHER_TENANT_ID,
                    "client_id": CLIENT_ID,
                    "bill_number": "BILL-FOREIGN",
                    "currency": "USD",
                    "subtotal": "999.00",
                    "tax_total": "0.00",
                    "total": "999.00",
                    "status": "approved",
                    "issue_date": today.isoformat(),
                    "due_date": today.isoformat(),
                    "vendor_invoice_number": "FOREIGN",
                    "notes": None,
                    "created_at": "2026-06-21T00:00:00+00:00",
                    "updated_at": "2026-06-21T00:00:00+00:00",
                    "deleted_at": None,
                },
            ],
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


def test_bill_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get(
        f"/api/v1/bills?status=approved&client_id={CLIENT_ID}&limit=10"
    )
    detail_response = client.get(f"/api/v1/bills/{BILL_ID}")
    aging_response = client.get("/api/v1/bills/aging")

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["id"] == BILL_ID
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["lines"][0]["description"] == "Cloud hosting"
    assert aging_response.status_code == 200, aging_response.text
    buckets = {bucket["label"]: bucket for bucket in aging_response.json()["buckets"]}
    assert buckets["current"] == {"label": "current", "total": "100.00", "count": 1}
    assert buckets["1-30"] == {"label": "1-30", "total": "50.00", "count": 1}
    assert aging_response.json()["grand_total"] == "150.00"


def test_bill_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/bills",
        json={
            "client_id": CLIENT_ID,
            "currency": "USD",
            "issue_date": "2026-06-22",
            "due_date": "2026-07-22",
            "vendor_invoice_number": "VENDOR-001",
            "lines": [
                {
                    "description": "Implementation tooling",
                    "quantity": "2",
                    "unit_price": "75.00",
                    "amount": "150.00",
                    "tax_amount": "15.00",
                }
            ],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == CREATED_BILL_ID
    assert response.json()["subtotal"] == "150.00"
    assert response.json()["tax_total"] == "15.00"
    assert response.json()["total"] == "165.00"
    assert response.json()["lines"][0]["id"] == CREATED_LINE_ID
