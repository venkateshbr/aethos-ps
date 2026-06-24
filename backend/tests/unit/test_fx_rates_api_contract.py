"""FX-rate API contract tests for authenticated read dependency wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import fx_rates as fx_rates_endpoint
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"


class _FakeDb:
    pass


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"wrong dependency attempted to access {name}")


def test_fx_rate_endpoint_uses_rls_client(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db = _FakeDb()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="viewer@example.com",
        role="viewer",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_user_rls_client] = lambda: fake_db
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()
    lookup = AsyncMock(
        return_value={
            "from_currency": "USD",
            "to_currency": "GBP",
            "rate": "0.790000",
            "refreshed_at": "2026-06-22T00:00:00+00:00",
            "stale": False,
        }
    )
    monkeypatch.setattr(fx_rates_endpoint, "get_fx_rate_with_staleness", lookup)

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/fx-rates/usd/gbp")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["rate"] == "0.790000"
    _, kwargs = lookup.await_args
    assert kwargs["from_currency"] == "usd"
    assert kwargs["to_currency"] == "gbp"
    assert kwargs["db"] is fake_db
