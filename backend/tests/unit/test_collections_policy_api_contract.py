"""Collections policy API contract tests for Settings and the worker."""

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


class _CollectionsPolicyQuery:
    def __init__(self, db: _FakeDb, rows: list[dict[str, Any]]) -> None:
        self.db = db
        self.rows = list(rows)
        self.update_payload: dict[str, Any] | None = None

    def select(self, _columns: str) -> _CollectionsPolicyQuery:
        return self

    def eq(self, key: str, value: Any) -> _CollectionsPolicyQuery:
        self.rows = [row for row in self.rows if row.get(key) == value]
        return self

    def is_(self, key: str, value: Any) -> _CollectionsPolicyQuery:
        if value == "null":
            self.rows = [row for row in self.rows if row.get(key) is None]
        return self

    def order(self, key: str) -> _CollectionsPolicyQuery:
        self.rows = sorted(self.rows, key=lambda row: row.get(key) or "")
        return self

    def limit(self, count: int) -> _CollectionsPolicyQuery:
        self.rows = self.rows[:count]
        return self

    def update(self, payload: dict[str, Any]) -> _CollectionsPolicyQuery:
        self.update_payload = payload
        return self

    def execute(self) -> _Result:
        if self.update_payload is not None:
            for row in self.rows:
                row.update(self.update_payload)
            return _Result(deepcopy(self.rows))
        return _Result(deepcopy(self.rows))


class _CollectionsPolicyTable:
    def __init__(self, db: _FakeDb) -> None:
        self.db = db

    def select(self, columns: str) -> _CollectionsPolicyQuery:
        return _CollectionsPolicyQuery(self.db, self.db.collections_policies).select(
            columns
        )

    def insert(self, payload: dict[str, Any]) -> _CollectionsPolicyQuery:
        row = {
            "id": f"policy-{len(self.db.collections_policies) + 1}",
            "deleted_at": None,
            **payload,
        }
        self.db.collections_policies.append(row)
        return _CollectionsPolicyQuery(self.db, [row])

    def update(self, payload: dict[str, Any]) -> _CollectionsPolicyQuery:
        return _CollectionsPolicyQuery(self.db, self.db.collections_policies).update(
            payload
        )


class _FakeDb:
    def __init__(self) -> None:
        self.collections_policies = [
            {
                "id": "tenant-policy",
                "tenant_id": TENANT_A,
                "client_id": None,
                "is_enabled": True,
                "gentle_after_days": 2,
                "firm_after_days": 10,
                "final_after_days": 35,
                "cooldown_days": 9,
                "max_reminders_per_invoice": 4,
                "max_auto_send_tone": "firm",
                "deleted_at": None,
            },
            {
                "id": "client-policy",
                "tenant_id": TENANT_A,
                "client_id": "client-a",
                "is_enabled": True,
                "gentle_after_days": 5,
                "firm_after_days": 20,
                "final_after_days": 45,
                "cooldown_days": 14,
                "max_reminders_per_invoice": 2,
                "max_auto_send_tone": "gentle",
                "deleted_at": None,
            },
            {
                "id": "foreign-policy",
                "tenant_id": TENANT_B,
                "client_id": None,
                "is_enabled": False,
                "gentle_after_days": 30,
                "firm_after_days": 60,
                "final_after_days": 90,
                "cooldown_days": 30,
                "max_reminders_per_invoice": 1,
                "max_auto_send_tone": "none",
                "deleted_at": None,
            },
        ]

    def table(self, name: str) -> _CollectionsPolicyTable:
        assert name == "collections_policies"
        return _CollectionsPolicyTable(self)


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


def test_get_effective_policy_returns_client_override(client: TestClient) -> None:
    response = client.get("/api/v1/collections/policies/effective?client_id=client-a")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == "client-policy"
    assert body["policy_source"] == "client_override"
    assert body["gentle_after_days"] == 5
    assert body["max_auto_send_tone"] == "gentle"


def test_get_effective_policy_falls_back_to_tenant_default(client: TestClient) -> None:
    response = client.get("/api/v1/collections/policies/effective?client_id=missing")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == "tenant-policy"
    assert body["policy_source"] == "tenant_default"
    assert body["cooldown_days"] == 9


def test_get_effective_policy_returns_system_default_when_no_rows(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    fake_db.collections_policies = [
        row for row in fake_db.collections_policies if row["tenant_id"] != TENANT_A
    ]

    response = client.get("/api/v1/collections/policies/effective")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] is None
    assert body["policy_source"] == "system_default"
    assert body["gentle_after_days"] == 1


def test_list_policies_uses_rls_client(client: TestClient) -> None:
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    response = client.get("/api/v1/collections/policies")

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    assert {item["id"] for item in response.json()["items"]} == {
        "client-policy",
        "tenant-policy",
    }


def test_put_default_policy_uses_service_role(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    response = client.put(
        "/api/v1/collections/policies/default",
        json={
            "is_enabled": True,
            "gentle_after_days": 3,
            "firm_after_days": 12,
            "final_after_days": 40,
            "cooldown_days": 11,
            "max_reminders_per_invoice": 5,
            "max_auto_send_tone": "gentle",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == "tenant-policy"
    tenant_policy = next(row for row in fake_db.collections_policies if row["id"] == "tenant-policy")
    assert tenant_policy["firm_after_days"] == 12
    assert tenant_policy["max_auto_send_tone"] == "gentle"


def test_invalid_policy_stage_order_returns_422(client: TestClient) -> None:
    response = client.put(
        "/api/v1/collections/policies/default",
        json={
            "gentle_after_days": 10,
            "firm_after_days": 3,
            "final_after_days": 40,
        },
    )

    assert response.status_code == 422
