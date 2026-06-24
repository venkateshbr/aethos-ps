"""Webhook event API contract tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app
from tests.unit.test_webhook_events_service import TENANT_ID, _Db, _Query

pytestmark = pytest.mark.unit


class _ForbiddenDb:
    def table(self, _name: str) -> _Query:
        raise AssertionError("wrong dependency attempted to query webhook_events")


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
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_admin_can_list_webhook_events(admin_client: TestClient) -> None:
    response = admin_client.get(
        "/api/v1/webhook-events?provider_event_id=evt_newer"
        "&event_type=checkout.session.completed"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["provider"] == "stripe"
    assert body["items"][0]["provider_event_id"] == "evt_newer"


def test_viewer_cannot_list_webhook_events() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()
    app.dependency_overrides[get_user_rls_client] = lambda: _ForbiddenDb()
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/webhook-events")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    detail: dict[str, Any] | str = response.json()["detail"]
    assert "admin" in str(detail)
