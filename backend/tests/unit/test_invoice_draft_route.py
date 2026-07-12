"""Invoice draft compatibility route tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.main import app
from app.models.security import CurrentUserPermissionsResponse

pytestmark = pytest.mark.unit


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="user-1",
        email="manager@example.com",
        role="manager",
    )
    app.dependency_overrides[get_tenant_id] = lambda: "11111111-1111-1111-1111-111111111111"
    app.dependency_overrides[get_service_role_client] = lambda: MagicMock()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_invoice_draft_route_delegates_to_existing_drafter(client: TestClient) -> None:
    draft = MagicMock()
    draft.model_dump.return_value = {
        "engagement_id": "eng-1",
        "client_id": "client-1",
        "currency": "USD",
        "lines": [],
        "subtotal": "0",
        "tax_total": "0",
        "total": "0",
        "billing_arrangement": "time_and_materials",
        "confidence": 0.95,
    }

    with (
        patch(
            "app.services.security_service.SecurityService.effective_permissions",
            new=AsyncMock(
                return_value=CurrentUserPermissionsResponse(
                    tenant_id="11111111-1111-1111-1111-111111111111",
                    user_id="user-1",
                    legacy_role="manager",
                    role_codes=["billing_specialist"],
                    role_labels=["Billing Specialist"],
                    privilege_codes=["invoices.draft"],
                    must_change_password=False,
                )
            ),
        ),
        patch(
            "app.api.v1.endpoints.invoices.draft_invoice",
            return_value=draft,
            create=True,
        ) as drafter,
    ):
        response = client.post(
            "/api/v1/invoices/draft",
            json={"engagement_id": "eng-1"},
        )

    assert response.status_code == 200, response.text
    assert response.json()["engagement_id"] == "eng-1"
    drafter.assert_called_once()
