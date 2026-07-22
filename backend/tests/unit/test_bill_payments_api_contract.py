"""Bill-payment API contract tests for RLS-backed reads and service-role writes."""

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
BATCH_ID = "33333333-3333-4333-8333-333333333333"
BILL_ID = "44444444-4444-4444-8444-444444444444"
CREATED_BATCH_ID = "55555555-5555-4555-8555-555555555555"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._select = "*"
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._null_filters: list[str] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._insert_payload: dict[str, Any] | list[dict[str, Any]] | None = None

    def select(self, columns: str = "*", **_kwargs: Any) -> _Query:
        self._select = columns
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

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> _Query:
        self._insert_payload = deepcopy(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            rows = self._insert_rows()
            self.db.tables[self.table].extend(rows)
            return _Result(deepcopy(rows))

        rows = [self._with_embeds(row) for row in self.db.tables[self.table] if self._matches(row)]
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

    def _with_embeds(self, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        if self.table == "bill_payment_items" and "bills(" in self._select:
            result["bills"] = self.db.bills_by_id.get(str(result["bill_id"]))
        return result

    def _insert_rows(self) -> list[dict[str, Any]]:
        payloads = (
            self._insert_payload
            if isinstance(self._insert_payload, list)
            else [self._insert_payload]
        )
        rows: list[dict[str, Any]] = []
        for index, payload in enumerate(payloads):
            assert payload is not None
            if self.table == "bill_payment_batches":
                rows.append(
                    {
                        "id": CREATED_BATCH_ID,
                        "status": "draft",
                        "created_at": "2026-06-22T00:00:00+00:00",
                        "updated_at": "2026-06-22T00:00:00+00:00",
                        **payload,
                    }
                )
            elif self.table == "bill_payment_items":
                rows.append(
                    {
                        "id": f"created-item-{index}",
                        "status": "pending",
                        "created_at": "2026-06-22T00:00:00+00:00",
                        **payload,
                    }
                )
            else:
                raise AssertionError(f"unexpected insert into {self.table}")
        return rows


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "tenant_users": [
                {
                    "id": "membership-user-1",
                    "tenant_id": TENANT_ID,
                    "user_id": "user-1",
                    "role": "admin",
                    "must_change_password": False,
                    "deleted_at": None,
                }
            ],
            "tenant_user_effective_privileges": [
                {
                    "tenant_id": TENANT_ID,
                    "user_id": "user-1",
                    "role_code": "ap_manager",
                    "role_label": "AP Manager",
                    "legacy_role": "admin",
                    "privilege_code": privilege,
                }
                for privilege in (
                    "bill_payments.read",
                    "bill_payments.prepare",
                    "bill_payments.approve",
                    "bill_payments.export",
                    "bill_payments.settle",
                )
            ],
            "bills": [
                {
                    "id": BILL_ID,
                    "tenant_id": TENANT_ID,
                    "bill_number": "BILL-0001",
                    "client_id": "vendor-1",
                    "vendor_invoice_number": "AWS-001",
                    "total": "125.00",
                    "currency": "USD",
                    "status": "approved",
                    "deleted_at": None,
                }
            ],
            "bill_payment_batches": [
                {
                    "id": BATCH_ID,
                    "tenant_id": TENANT_ID,
                    "status": "draft",
                    "total": "125.00",
                    "currency": "USD",
                    "bank_account_label": "Operating",
                    "pay_date": "2026-06-30",
                    "created_by": "user-1",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": "2026-06-22T00:00:00+00:00",
                },
                {
                    "id": "66666666-6666-4666-8666-666666666666",
                    "tenant_id": OTHER_TENANT_ID,
                    "status": "draft",
                    "total": "999.00",
                    "currency": "USD",
                    "bank_account_label": "Foreign",
                    "pay_date": "2026-06-30",
                    "created_by": "user-2",
                    "created_at": "2026-06-23T00:00:00+00:00",
                    "updated_at": "2026-06-23T00:00:00+00:00",
                },
            ],
            "bill_payment_items": [
                {
                    "id": "77777777-7777-4777-8777-777777777777",
                    "tenant_id": TENANT_ID,
                    "batch_id": BATCH_ID,
                    "bill_id": BILL_ID,
                    "amount": "125.00",
                    "currency": "USD",
                    "status": "pending",
                    "created_at": "2026-06-22T00:00:00+00:00",
                },
                {
                    "id": "88888888-8888-4888-8888-888888888888",
                    "tenant_id": OTHER_TENANT_ID,
                    "batch_id": BATCH_ID,
                    "bill_id": BILL_ID,
                    "amount": "999.00",
                    "currency": "USD",
                    "status": "pending",
                    "created_at": "2026-06-22T00:00:00+00:00",
                },
            ],
        }
        self.bills_by_id = {str(row["id"]): row for row in self.tables["bills"]}

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


class _SecurityOnlyDb:
    """Allow privilege evaluation while rejecting bill-payment data access."""

    def __init__(self, db: _FakeDb) -> None:
        self._db = db

    def table(self, name: str) -> _Query:
        if name not in {"tenant_users", "tenant_user_effective_privileges"}:
            raise AssertionError(f"service-role read attempted to access {name}")
        return self._db.table(name)


@pytest.fixture
def fake_db() -> _FakeDb:
    return _FakeDb()


@pytest.fixture
def client(fake_db: _FakeDb) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="admin@example.com",
        role="admin",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_bill_payment_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _SecurityOnlyDb(fake_db)

    list_response = client.get("/api/v1/bill-payments/batches?status=draft")
    detail_response = client.get(f"/api/v1/bill-payments/batches/{BATCH_ID}")

    assert list_response.status_code == 200, list_response.text
    assert [row["id"] for row in list_response.json()] == [BATCH_ID]
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["items"] == [
        {
            "id": "77777777-7777-4777-8777-777777777777",
            "tenant_id": TENANT_ID,
            "batch_id": BATCH_ID,
            "bill_id": BILL_ID,
            "amount": "125.00",
            "currency": "USD",
            "status": "pending",
            "created_at": "2026-06-22T00:00:00+00:00",
            "bills": {
                "id": BILL_ID,
                "tenant_id": TENANT_ID,
                "bill_number": "BILL-0001",
                "client_id": "vendor-1",
                "vendor_invoice_number": "AWS-001",
                "total": "125.00",
                "currency": "USD",
                "status": "approved",
                "deleted_at": None,
            },
        }
    ]


def test_bill_payment_create_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    # Fresh-create scenario: the bill is not yet in any payment batch. (The shared
    # fixture seeds an existing item for get/settle tests; the #391 double-settle
    # guard now correctly rejects re-batching a bill that already has an active item.)
    fake_db.tables["bill_payment_items"] = []

    response = client.post(
        "/api/v1/bill-payments/batches",
        json={
            "bill_ids": [BILL_ID],
            "pay_date": "2026-06-30",
            "bank_account_label": "Operating",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == CREATED_BATCH_ID
    assert response.json()["total"] == "125.00"
    assert response.json()["items"] == [
        {
            "tenant_id": TENANT_ID,
            "batch_id": CREATED_BATCH_ID,
            "bill_id": BILL_ID,
            "amount": "125.00",
            "currency": "USD",
        }
    ]
