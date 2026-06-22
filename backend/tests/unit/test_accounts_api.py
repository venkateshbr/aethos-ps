"""Accounts API contract tests.

The manual journal UI calls GET /api/v1/accounts to populate its account
picker. These tests exercise the public HTTP route with dependency overrides,
not the service internals, so a missing router registration fails as a 404.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit


TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _AccountsQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = list(rows)

    def select(self, _columns: str) -> _AccountsQuery:
        return self

    def eq(self, key: str, value: Any) -> _AccountsQuery:
        self.rows = [row for row in self.rows if row.get(key) == value]
        return self

    def is_(self, key: str, value: Any) -> _AccountsQuery:
        if value == "null":
            self.rows = [row for row in self.rows if row.get(key) is None]
        return self

    def order(self, key: str) -> _AccountsQuery:
        self.rows = sorted(self.rows, key=lambda row: row.get(key) or "")
        return self

    def execute(self) -> _Result:
        return _Result(self.rows)


class _FakeDb:
    def __init__(self) -> None:
        self.accounts = [
            {
                "id": "a-rev",
                "tenant_id": TENANT_A,
                "code": "4000",
                "name": "Revenue",
                "account_type": "revenue",
                "is_system": True,
                "parent_id": None,
                "deleted_at": None,
            },
            {
                "id": "a-bank",
                "tenant_id": TENANT_A,
                "code": "1100",
                "name": "Bank",
                "account_type": "asset",
                "is_system": True,
                "parent_id": None,
                "deleted_at": None,
            },
            {
                "id": "a-advisory-rev",
                "tenant_id": TENANT_A,
                "code": "4100",
                "name": "Advisory Revenue",
                "account_type": "revenue",
                "is_system": False,
                "parent_id": None,
                "deleted_at": None,
            },
            {
                "id": "a-old",
                "tenant_id": TENANT_A,
                "code": "9999",
                "name": "Deleted account",
                "account_type": "expense",
                "is_system": False,
                "parent_id": None,
                "deleted_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "b-bank",
                "tenant_id": TENANT_B,
                "code": "1100",
                "name": "Tenant B Bank",
                "account_type": "asset",
                "is_system": True,
                "parent_id": None,
                "deleted_at": None,
            },
        ]

    def table(self, name: str) -> _AccountsQuery:
        assert name == "accounts"
        return _AccountsQuery(self.accounts)


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="owner@example.com",
        role="owner",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_A
    app.dependency_overrides[get_user_rls_client] = lambda: _FakeDb()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_accounts_returns_active_tenant_accounts_sorted_for_picker(client: TestClient) -> None:
    response = client.get("/api/v1/accounts")

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": "a-bank",
            "code": "1100",
            "name": "Bank",
            "account_type": "asset",
            "is_system": True,
            "parent_id": None,
        },
        {
            "id": "a-rev",
            "code": "4000",
            "name": "Revenue",
            "account_type": "revenue",
            "is_system": True,
            "parent_id": None,
        },
        {
            "id": "a-advisory-rev",
            "code": "4100",
            "name": "Advisory Revenue",
            "account_type": "revenue",
            "is_system": False,
            "parent_id": None,
        },
    ]


def test_list_accounts_can_filter_by_account_type(client: TestClient) -> None:
    response = client.get("/api/v1/accounts?account_type=revenue")

    assert response.status_code == 200, response.text
    assert [row["code"] for row in response.json()] == ["4000", "4100"]


def test_list_accounts_supports_picker_search_and_limit(client: TestClient) -> None:
    response = client.get("/api/v1/accounts?search=revenue&limit=1")

    assert response.status_code == 200, response.text
    assert [row["code"] for row in response.json()] == ["4000"]
