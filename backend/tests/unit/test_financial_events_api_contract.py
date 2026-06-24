"""Financial event API contract tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app
from tests.unit.test_financial_events_service import TENANT_ID, _Db, _Query

pytestmark = pytest.mark.unit


class _ForbiddenDb:
    def table(self, _name: str) -> _Query:
        raise AssertionError("wrong dependency attempted to query financial_events")


@pytest.fixture
def fake_db() -> _Db:
    return _Db()


@pytest.fixture
def admin_client(fake_db: _Db) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="admin@example.com",
        role="admin",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_admin_can_list_financial_events(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/financial-events?event_type=period.locked")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["event_type"] == "period.locked"
    assert body["items"][0]["entity_type"] == "period_lock"
    assert body["items"][0]["event_hash"] == "hash-event-newer"


def test_admin_can_export_financial_events_csv(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/financial-events/export?entity_type=journal_entry")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "financial-events.csv" in response.headers["content-disposition"]
    body = response.text
    assert "event_type,entity_type,entity_id" in body
    assert "journal_entry.posted,journal_entry,journal-1" in body
    assert "period.locked" not in body


def test_viewer_can_list_business_record_decisions(fake_db: _Db) -> None:
    fake_db.rows.append(
        {
            "id": "event-bill-projection",
            "tenant_id": TENANT_ID,
            "event_type": "hitl_task.approved",
            "entity_type": "bill",
            "entity_id": "bill-1",
            "source_type": "hitl_task",
            "source_id": "task-1",
            "actor_user_id": "user-1",
            "actor_role": "manager",
            "action": "approved",
            "before_state": {"payload_hash": "hash-before"},
            "after_state": {
                "payload_hash": "hash-after",
                "materialisation": {"entity_type": "bill", "entity_id": "bill-1"},
            },
            "metadata": {"source_hitl_task_id": "task-1"},
            "idempotency_key": "hitl_task.approved:task-1:record:bill:bill-1",
            "previous_event_hash": None,
            "event_hash": "hash-event-bill-projection",
            "created_at": "2026-06-23T10:00:00+00:00",
        }
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()
    try:
        with TestClient(app) as test_client:
            response = test_client.get(
                "/api/v1/financial-events/business-records/bill/bill-1/decisions"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["entity_type"] == "bill"
    assert body["items"][0]["source_type"] == "hitl_task"


def test_viewer_cannot_list_financial_events() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/financial-events")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    detail: dict[str, Any] | str = response.json()["detail"]
    assert "admin" in str(detail)
