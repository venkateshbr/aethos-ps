"""API contract for the tenant accounting context used by journal composers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def client() -> tuple[TestClient, MagicMock]:
    db = MagicMock()
    result = MagicMock()
    result.data = [{"id": TENANT_ID, "base_currency": "SGD"}]
    query = db.table.return_value.select.return_value.eq.return_value
    query.limit.return_value.execute.return_value = result

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="admin-1",
        email="admin@example.test",
        role="admin",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: db
    yield TestClient(app), db
    app.dependency_overrides.clear()


def test_current_tenant_accounting_context_returns_verified_base_currency(
    client: tuple[TestClient, MagicMock],
) -> None:
    http, db = client

    response = http.get("/api/v1/tenants/accounting-context")

    assert response.status_code == 200, response.text
    assert response.json() == {"tenant_id": TENANT_ID, "base_currency": "SGD"}
    db.table.assert_called_with("tenants")


def test_current_tenant_accounting_context_rejects_unicode_currency_code(
    client: tuple[TestClient, MagicMock],
) -> None:
    http, db = client
    query = db.table.return_value.select.return_value.eq.return_value
    query.limit.return_value.execute.return_value.data = [
        {"id": TENANT_ID, "base_currency": "ÅBC"}
    ]

    response = http.get("/api/v1/tenants/accounting-context")

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == "Tenant base currency is not configured"
