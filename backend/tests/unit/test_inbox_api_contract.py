"""Inbox API contract tests for RLS-backed reads and service-role actions."""

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

TENANT_ID = "tenant-123"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _FakeDb, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._update_payload: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def order(self, key: str, *, desc: bool = False) -> _Query:
        self._order_key = key
        self._order_desc = desc
        return self

    def limit(self, limit: int) -> _Query:
        self._limit = limit
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        rows = self._filtered_rows()
        if self._update_payload is not None:
            for row in rows:
                row.update(self._update_payload)
            return _Result(deepcopy(rows))

        rows = [self._with_embeds(row) for row in rows]
        if self._order_key is not None:
            rows.sort(
                key=lambda row: str(row.get(self._order_key) or ""),
                reverse=self._order_desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(deepcopy(rows))

    def _filtered_rows(self) -> list[dict[str, Any]]:
        rows = list(self.db.tables[self.table])
        for key, value in self._eq_filters:
            rows = [row for row in rows if row.get(key) == value]
        return rows

    def _with_embeds(self, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        if self.table == "hitl_tasks":
            suggestion_id = result.get("agent_suggestion_id")
            result["agent_suggestions"] = self.db.suggestion_by_id.get(str(suggestion_id))
        return result


class _FakeDb:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "agent_suggestions": [
                {
                    "id": "suggestion-1",
                    "tenant_id": TENANT_ID,
                    "agent_name": "vendor_invoice_agent",
                    "confidence": "0.88",
                    "output_snapshot": {"vendor_name": "Acme Supplies"},
                    "action_type": "create_bill",
                    "status": "pending",
                }
            ],
            "hitl_tasks": [
                {
                    "id": "task-1",
                    "tenant_id": TENANT_ID,
                    "kind": "create_bill",
                    "priority": "normal",
                    "title": "Review vendor bill",
                    "description": "Verify extracted bill fields",
                    "payload": {"source": "document-1"},
                    "status": "open",
                    "created_at": "2026-06-22T00:00:00+00:00",
                    "updated_at": "2026-06-22T00:00:00+00:00",
                    "agent_suggestion_id": "suggestion-1",
                }
            ],
            "tenant_users": [
                {"tenant_id": TENANT_ID, "user_id": "owner-1", "role": "owner"}
            ],
        }
        self.suggestion_by_id = {
            str(row["id"]): row for row in self.tables["agent_suggestions"]
        }

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


def test_inbox_read_routes_use_rls_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    list_response = client.get("/api/v1/inbox/tasks?status=open&kind=create_bill")
    detail_response = client.get("/api/v1/inbox/tasks/task-1")

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["tenant_id"] == TENANT_ID
    assert list_response.json()["items"][0]["agent_name"] == "vendor_invoice_agent"
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["tenant_id"] == TENANT_ID
    assert detail_response.json()["payload"] == {"source": "document-1"}


def test_inbox_escalation_uses_service_role_client(
    client: TestClient,
    fake_db: _FakeDb,
) -> None:
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: fake_db

    response = client.post("/api/v1/inbox/tasks/task-1/escalate")

    assert response.status_code == 200, response.text
    assert response.json()["escalated"] is True
    assert fake_db.tables["hitl_tasks"][0]["priority"] == "critical"
    assert fake_db.tables["hitl_tasks"][0]["assigned_to"] == "owner-1"
