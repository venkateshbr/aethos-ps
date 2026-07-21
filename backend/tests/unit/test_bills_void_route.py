"""Bill void route contract tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import bills as bills_endpoint
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.main import app
from app.models.bills import BillResponse
from app.models.security import CurrentUserPermissionsResponse

pytestmark = pytest.mark.unit


@pytest.fixture
def bill_response() -> BillResponse:
    return BillResponse(
        id="bill-1",
        tenant_id="tenant-1",
        client_id="vendor-1",
        bill_number="BILL-0001",
        currency="USD",
        subtotal="100.00",
        tax_total="0.00",
        total="100.00",
        status="voided",
        issue_date="2026-06-01",
        due_date="2026-06-30",
        vendor_invoice_number="V-100",
        notes=None,
        created_at="2026-06-01T00:00:00Z",
    )


def test_void_bill_route_calls_service(bill_response: BillResponse) -> None:
    svc = AsyncMock()
    svc.void_bill.return_value = bill_response
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="owner-1",
        email="owner@example.com",
        role="owner",
    )
    app.dependency_overrides[get_tenant_id] = lambda: "tenant-1"
    app.dependency_overrides[get_service_role_client] = lambda: MagicMock()
    app.dependency_overrides[bills_endpoint._write_service] = lambda: svc
    try:
        with (
            patch(
                "app.services.security_service.SecurityService.effective_permissions",
                new=AsyncMock(
                    return_value=CurrentUserPermissionsResponse(
                        tenant_id="tenant-1",
                        user_id="owner-1",
                        legacy_role="owner",
                        role_codes=["tenant_owner"],
                        role_labels=["Tenant Owner"],
                        privilege_codes=["bills.manage"],
                        must_change_password=False,
                    )
                ),
            ),
            TestClient(app) as client,
        ):
            response = client.post("/api/v1/bills/bill-1/void")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "voided"
    svc.void_bill.assert_awaited_once_with("bill-1", "owner-1")
