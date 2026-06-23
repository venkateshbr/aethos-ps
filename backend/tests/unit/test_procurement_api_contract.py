"""Procurement API contract tests for RLS reads and service-role writes."""

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
CLIENT_ID = "33333333-3333-4333-8333-333333333333"
DOCUMENT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CREATED_DOCUMENT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
CREATED_LINE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


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
        self._limit: int | None = None
        self._insert_payload: dict[str, Any] | None = None
        self._update_payload: dict[str, Any] | None = None

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
        for key in self._null_filters:
            if row.get(key) is not None:
                return False
        return True

    def _insert_row(self) -> dict[str, Any]:
        if self.table == "procurement_documents":
            return {
                "id": CREATED_DOCUMENT_ID,
                "tenant_id": TENANT_ID,
                "document_number": "PO-CREATED",
                "status": "draft",
                "subtotal": "0.00",
                "tax_total": "0.00",
                "total": "0.00",
                "matched_bill_total": "0.00",
                "approved_by": None,
                "approved_at": None,
                "created_at": "2026-06-22T00:00:00+00:00",
                "updated_at": "2026-06-22T00:00:00+00:00",
                "deleted_at": None,
                **self._insert_payload,
            }
        if self.table == "procurement_document_lines":
            return {
                "id": CREATED_LINE_ID,
                "account_id": None,
                "service_start_date": None,
                "service_end_date": None,
                "created_at": "2026-06-22T00:00:00+00:00",
                **self._insert_payload,
            }
        raise AssertionError(f"unexpected insert into {self.table}")


class _FakeDb:
    def __init__(self) -> None:
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
            "procurement_documents": [
                {
                    "id": DOCUMENT_ID,
                    "tenant_id": TENANT_ID,
                    "document_type": "purchase_order",
                    "document_number": "PO-0001",
                    "client_id": CLIENT_ID,
                    "status": "approved",
                    "currency": "USD",
                    "issue_date": "2026-06-20",
                    "expected_delivery_date": "2026-07-01",
                    "service_start_date": None,
                    "service_end_date": None,
                    "subtotal": "100.00",
                    "tax_total": "10.00",
                    "total": "110.00",
                    "matched_bill_total": "0.00",
                    "requested_by": "manager-1",
                    "approved_by": "admin-1",
                    "approved_at": "2026-06-20T00:00:00+00:00",
                    "notes": None,
                    "created_at": "2026-06-20T00:00:00+00:00",
                    "updated_at": "2026-06-20T00:00:00+00:00",
                    "deleted_at": None,
                }
            ],
            "procurement_document_lines": [
                {
                    "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                    "tenant_id": TENANT_ID,
                    "procurement_document_id": DOCUMENT_ID,
                    "description": "Implementation tooling",
                    "quantity": "1",
                    "unit_price": "100.00",
                    "amount": "100.00",
                    "tax_amount": "10.00",
                    "account_id": None,
                    "service_start_date": None,
                    "service_end_date": None,
                    "created_at": "2026-06-20T00:00:00+00:00",
                }
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
        email="owner@example.com",
        role="owner",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_procurement_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get(
        "/api/v1/procurement/documents?document_type=purchase_order&status=approved"
    )
    detail_response = client.get(f"/api/v1/procurement/documents/{DOCUMENT_ID}")

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["document_number"] == "PO-0001"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["lines"][0]["description"] == "Implementation tooling"


def test_procurement_writes_use_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    create_response = client.post(
        "/api/v1/procurement/documents",
        json={
            "document_type": "service_order",
            "client_id": CLIENT_ID,
            "currency": "USD",
            "service_start_date": "2026-07-01",
            "service_end_date": "2026-07-31",
            "lines": [
                {
                    "description": "July implementation retainer",
                    "quantity": "1",
                    "unit_price": "500.00",
                    "amount": "500.00",
                    "tax_amount": "50.00",
                    "service_start_date": "2026-07-01",
                    "service_end_date": "2026-07-31",
                }
            ],
        },
    )
    approve_response = client.post(
        f"/api/v1/procurement/documents/{CREATED_DOCUMENT_ID}/approve"
    )

    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["id"] == CREATED_DOCUMENT_ID
    assert create_response.json()["document_type"] == "service_order"
    assert create_response.json()["total"] == "550.00"
    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["status"] == "approved"
    assert approve_response.json()["approved_by"] == "user-1"
