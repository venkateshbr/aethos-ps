"""Invoice API contract tests for RLS-backed reads and service-role writes."""

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
CLIENT_ID = "22222222-2222-2222-2222-222222222222"
ENGAGEMENT_ID = "33333333-3333-3333-3333-333333333333"
INVOICE_ID = "44444444-4444-4444-8444-444444444444"
CREATED_INVOICE_ID = "55555555-5555-4555-8555-555555555555"
TAX_RATE_ID = "88888888-8888-4888-8888-888888888888"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._select = ""
        self._eq_filters: list[tuple[str, Any]] = []
        self._null_filters: list[str] = []
        self._order_key: str | None = None
        self._limit: int | None = None
        self._insert_payload: dict[str, Any] | None = None

    def select(self, columns: str = "*", **_kwargs: Any) -> _Query:
        self._select = columns
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def order(self, key: str, **_kwargs: Any) -> _Query:
        self._order_key = key
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._insert_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            row = self._insert_row()
            self.db.tables[self.table].append(row)
            return _Result([deepcopy(row)])

        rows = [self._with_embeds(row) for row in self._filtered_rows()]
        if self._order_key is not None:
            rows.sort(key=lambda row: str(row.get(self._order_key) or ""))
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))

    def _insert_row(self) -> dict[str, Any]:
        if self.table == "invoices":
            return {
                "id": CREATED_INVOICE_ID,
                "invoice_number": "INV-CREATED",
                "public_token": "public-created",
                "stripe_payment_link_id": None,
                "stripe_payment_link_url": None,
                "sent_at": None,
                "paid_at": None,
                "created_at": "2026-06-22T00:00:00+00:00",
                "updated_at": "2026-06-22T00:00:00+00:00",
                "deleted_at": None,
                **self._insert_payload,
            }
        return {
            "id": "66666666-6666-4666-8666-666666666666",
            "created_at": "2026-06-22T00:00:00+00:00",
            **self._insert_payload,
        }

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        for key in self._null_filters:
            rows = [row for row in rows if row.get(key) is None]
        return rows

    def _with_embeds(self, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        if self.table == "invoices" and "clients" in self._select:
            result["clients"] = self.db.client_by_id.get(str(result["client_id"]))
        return result


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "clients": [
                {
                    "id": CLIENT_ID,
                    "tenant_id": TENANT_ID,
                    "name": "Acme Corp",
                    "deleted_at": None,
                }
            ],
            "engagements": [
                {
                    "id": ENGAGEMENT_ID,
                    "tenant_id": TENANT_ID,
                    "deleted_at": None,
                }
            ],
            "invoice_lines": [
                {
                    "id": "77777777-7777-4777-8777-777777777777",
                    "tenant_id": TENANT_ID,
                    "invoice_id": INVOICE_ID,
                    "description": "Advisory services",
                    "quantity": "1",
                    "unit_price": "1200.00",
                    "amount": "1200.00",
                    "tax_rate_id": None,
                    "tax_amount": "0.00",
                    "time_entry_id": None,
                    "expense_id": None,
                    "created_at": "2026-06-22T00:00:00+00:00",
                }
            ],
            "tax_rates": [
                {
                    "id": TAX_RATE_ID,
                    "tenant_id": None,
                    "rate": "0.1000",
                    "is_active": True,
                    "deleted_at": None,
                }
            ],
            "invoices": [
                {
                    "id": INVOICE_ID,
                    "tenant_id": TENANT_ID,
                    "engagement_id": ENGAGEMENT_ID,
                    "client_id": CLIENT_ID,
                    "invoice_number": "INV-0001",
                    "currency": "USD",
                    "subtotal": "1200.00",
                    "tax_total": "0.00",
                    "total": "1200.00",
                    "status": "draft",
                    "issue_date": "2026-06-22",
                    "due_date": "2026-07-22",
                    "paid_at": None,
                    "stripe_payment_link_id": None,
                    "stripe_payment_link_url": None,
                    "public_token": "public-token",
                    "sent_at": None,
                    "notes": None,
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": "2026-06-22T00:00:00+00:00",
                    "deleted_at": None,
                }
            ],
        }
        self.client_by_id = {str(row["id"]): row for row in self.tables["clients"]}

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
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_invoice_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get(
        f"/api/v1/invoices?engagement_id={ENGAGEMENT_ID}&status=draft"
    )
    detail_response = client.get(f"/api/v1/invoices/{INVOICE_ID}")

    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["client_name"] == "Acme Corp"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["lines"][0]["amount"] == "1200.00"


def test_invoice_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/invoices",
        json={
            "engagement_id": ENGAGEMENT_ID,
            "client_id": CLIENT_ID,
            "currency": "USD",
            "issue_date": "2026-06-22",
            "due_date": "2026-07-22",
            "lines": [
                {
                    "description": "Implementation support",
                    "quantity": "2",
                    "unit_price": "100.00",
                }
            ],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == CREATED_INVOICE_ID
    assert response.json()["lines"][0]["amount"] == "200.00"


def test_invoice_create_applies_line_tax_from_visible_tax_rate(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post(
        "/api/v1/invoices",
        json={
            "engagement_id": ENGAGEMENT_ID,
            "client_id": CLIENT_ID,
            "currency": "USD",
            "lines": [
                {
                    "description": "Taxable advisory",
                    "quantity": "2",
                    "unit_price": "100.00",
                    "tax_rate_id": TAX_RATE_ID,
                },
                {
                    "description": "Untaxed advisory",
                    "quantity": "1",
                    "unit_price": "50.00",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["subtotal"] == "250.00"
    assert body["tax_total"] == "20.00"
    assert body["total"] == "270.00"
    assert body["lines"][0]["tax_rate_id"] == TAX_RATE_ID
    assert body["lines"][0]["tax_amount"] == "20.00"
    assert body["lines"][1]["tax_amount"] == "0.00"
