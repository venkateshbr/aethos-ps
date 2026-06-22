"""Payments API contract tests for RLS-backed reads."""

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

TENANT_ID = "tenant-1"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _ReadDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def order(self, key: str, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def execute(self) -> _Result:
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
        return True


class _ReadDb:
    def __init__(self) -> None:
        self.tables = {
            "payments": [
                {
                    "id": "payment-1",
                    "tenant_id": TENANT_ID,
                    "invoice_id": "invoice-1",
                    "amount": "1250.00",
                    "currency": "USD",
                    "base_amount": "1250.00",
                    "paid_at": "2026-06-22T00:00:00+00:00",
                    "notes": "Stripe receipt",
                    "invoices": {
                        "invoice_number": "INV-0001",
                        "status": "paid",
                    },
                }
            ]
        }

    def table(self, name: str) -> _Query:
        assert name in self.tables
        return _Query(self, name)


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


def test_payment_list_uses_rls_client() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: _ReadDb()
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/payments?limit=10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json() == {
        "items": [
            {
                "id": "payment-1",
                "invoice_id": "invoice-1",
                "invoice_number": "INV-0001",
                "amount": "1250.00",
                "currency": "USD",
                "base_amount": "1250.00",
                "paid_at": "2026-06-22T00:00:00+00:00",
                "notes": "Stripe receipt",
            }
        ],
        "total": 1,
    }
