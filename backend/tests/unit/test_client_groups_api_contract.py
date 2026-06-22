"""Client-groups API contract tests for related entities UI."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.main import app
from tests.unit.test_client_groups_service import TENANT_ID, _FakeDb

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_db() -> _FakeDb:
    return _FakeDb()


@pytest.fixture
def client(fake_db: _FakeDb) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="owner@example.com",
        role="owner",
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: fake_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_client_group_routes_create_list_and_add_member(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/client-groups",
        json={
            "name": "Acme Family Office",
            "group_type": "family_office",
            "primary_client_id": "client-acme",
            "billing_client_id": "client-acme",
            "currency": "USD",
        },
    )

    assert create_response.status_code == 201, create_response.text
    group = create_response.json()
    assert group["name"] == "Acme Family Office"
    assert group["member_count"] == 1

    list_response = client.get("/api/v1/client-groups?client_id=client-acme")
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 1

    add_response = client.post(
        f"/api/v1/client-groups/{group['id']}/members",
        json={
            "client_id": "client-bravo",
            "relationship_role": "portfolio_company",
            "is_primary": False,
        },
    )
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["client_name"] == "Bravo Holdings"

    detail_response = client.get(f"/api/v1/client-groups/{group['id']}")
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["member_count"] == 2
