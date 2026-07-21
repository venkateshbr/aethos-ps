"""HTTP authorization contracts for invoice and bill money actions."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.bills import _write_service as bills_write_service
from app.api.v1.endpoints.invoices import _write_service as invoices_write_service
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.main import app

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-2222-2222-222222222222"
INVOICE_ID = "33333333-3333-4333-8333-333333333333"
BILL_ID = "44444444-4444-4444-8444-444444444444"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _PermissionQuery:
    def __init__(self, db: _PermissionDb, table: str) -> None:
        self._db = db
        self._table = table
        self._filters: list[tuple[str, Any]] = []

    def select(self, _columns: str) -> _PermissionQuery:
        return self

    def eq(self, key: str, value: Any) -> _PermissionQuery:
        self._filters.append((key, value))
        return self

    def is_(self, _key: str, _value: str) -> _PermissionQuery:
        return self

    def limit(self, _value: int) -> _PermissionQuery:
        return self

    def execute(self) -> _Result:
        rows = self._db.rows[self._table]
        for key, value in self._filters:
            rows = [row for row in rows if row.get(key) == value]
        return _Result(rows)


class _PermissionDb:
    def __init__(self, privilege_codes: set[str], legacy_role: str) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {
            "tenant_users": [
                {
                    "id": "membership-1",
                    "tenant_id": TENANT_ID,
                    "user_id": USER_ID,
                    "role": legacy_role,
                    "must_change_password": False,
                }
            ],
            "tenant_user_effective_privileges": [
                {
                    "tenant_id": TENANT_ID,
                    "user_id": USER_ID,
                    "role_code": "test_role",
                    "role_label": "Test role",
                    "legacy_role": legacy_role,
                    "privilege_code": code,
                }
                for code in sorted(privilege_codes)
            ],
        }

    def table(self, name: str) -> _PermissionQuery:
        return _PermissionQuery(self, name)


def _invoice_row(status: str) -> dict[str, Any]:
    return {
        "id": INVOICE_ID,
        "tenant_id": TENANT_ID,
        "engagement_id": "55555555-5555-4555-8555-555555555555",
        "client_id": "66666666-6666-4666-8666-666666666666",
        "invoice_number": "INV-0001",
        "currency": "USD",
        "subtotal": "100.00",
        "tax_total": "0.00",
        "total": "100.00",
        "status": status,
        "issue_date": "2026-05-31",
        "due_date": "2026-06-30",
        "paid_at": "2026-06-20T09:00:00+00:00" if status == "paid" else None,
        "stripe_payment_link_id": None,
        "stripe_payment_link_url": None,
        "public_token": "public-token",
        "sent_at": None,
        "notes": None,
        "created_at": "2026-05-31T00:00:00+00:00",
        "updated_at": "2026-05-31T00:00:00+00:00",
        "lines": [],
    }


class _InvoicesStub:
    async def create_invoice(
        self,
        _payload: Any,
        *,
        created_by: str,
    ) -> dict[str, Any]:
        assert created_by == USER_ID
        return _invoice_row("draft")

    async def approve_invoice(
        self,
        _invoice_id: str,
        *,
        approved_by: str,
    ) -> dict[str, Any]:
        assert approved_by == USER_ID
        return _invoice_row("approved")

    async def send_invoice(
        self,
        _invoice_id: str,
        *,
        sent_by: str,
    ) -> dict[str, Any]:
        assert sent_by == USER_ID
        return _invoice_row("sent")

    async def record_manual_payment(self, **_kwargs: Any) -> dict[str, Any]:
        return _invoice_row("paid")


class _BillsStub:
    async def create_bill(self, _payload: Any) -> dict[str, Any]:
        return {
            "id": BILL_ID,
            "tenant_id": TENANT_ID,
            "client_id": "88888888-8888-4888-8888-888888888888",
            "bill_number": "BILL-0001",
            "currency": "USD",
            "subtotal": "100.00",
            "tax_total": "0.00",
            "total": "100.00",
            "status": "draft",
            "issue_date": "2026-05-31",
            "due_date": "2026-06-30",
            "vendor_invoice_number": "VENDOR-1",
            "notes": None,
            "created_at": "2026-05-31T00:00:00+00:00",
            "lines": [],
        }

    async def approve_bill(self, _bill_id: str, approved_by: str) -> dict[str, Any]:
        assert approved_by == USER_ID
        return {
            "id": BILL_ID,
            "status": "approved",
            "journal_entry_id": "77777777-7777-4777-8777-777777777777",
            "message": "Bill approved",
        }


@contextmanager
def _client(
    *,
    privileges: set[str],
    legacy_role: str,
) -> Iterator[TestClient]:
    db = _PermissionDb(privileges, legacy_role)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=USER_ID,
        email="finance@example.com",
        role=legacy_role,
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: db
    app.dependency_overrides[invoices_write_service] = lambda: _InvoicesStub()
    app.dependency_overrides[bills_write_service] = lambda: _BillsStub()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_ar_manager_can_record_invoice_receipt_with_mark_paid_privilege() -> None:
    with _client(privileges={"invoices.mark_paid"}, legacy_role="manager") as client:
        response = client.post(
            f"/api/v1/invoices/{INVOICE_ID}/payments",
            json={"amount": "100.00", "paid_at": "2026-06-20T09:00:00+00:00"},
        )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paid"


def test_billing_specialist_can_post_invoice_with_invoice_post_privilege() -> None:
    with _client(privileges={"invoices.post"}, legacy_role="manager") as client:
        response = client.patch(f"/api/v1/invoices/{INVOICE_ID}/approve")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"


def test_billing_specialist_can_send_invoice_with_invoice_send_privilege() -> None:
    with _client(privileges={"invoices.send"}, legacy_role="manager") as client:
        response = client.post(f"/api/v1/invoices/{INVOICE_ID}/send")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "sent"


def test_custom_operator_can_create_invoice_with_invoice_draft_privilege() -> None:
    with _client(privileges={"invoices.draft"}, legacy_role="member") as client:
        response = client.post(
            "/api/v1/invoices",
            json={
                "engagement_id": "55555555-5555-4555-8555-555555555555",
                "client_id": "66666666-6666-4666-8666-666666666666",
                "currency": "USD",
                "lines": [
                    {
                        "description": "Advisory services",
                        "quantity": "1",
                        "unit_price": "100.00",
                    }
                ],
            },
        )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "draft"


def test_invoice_draft_preview_denies_user_without_invoice_draft_privilege() -> None:
    with _client(privileges=set(), legacy_role="admin") as client:
        response = client.post(
            "/api/v1/invoices/draft",
            json={"engagement_id": "55555555-5555-4555-8555-555555555555"},
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: invoices.draft"


def test_finance_approver_cannot_post_invoice_without_invoice_post_privilege() -> None:
    with _client(
        privileges={"inbox.read", "inbox.approve_manager"},
        legacy_role="approver",
    ) as client:
        response = client.patch(f"/api/v1/invoices/{INVOICE_ID}/approve")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: invoices.post"


def test_public_token_rotation_requires_invoice_send_privilege() -> None:
    with _client(privileges=set(), legacy_role="admin") as client:
        response = client.post(f"/api/v1/invoices/{INVOICE_ID}/public-token/rotate")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: invoices.send"


def test_ap_manager_can_approve_bill_with_bills_approve_privilege() -> None:
    with _client(privileges={"bills.approve"}, legacy_role="manager") as client:
        response = client.patch(f"/api/v1/bills/{BILL_ID}/approve")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"


def test_custom_operator_can_create_bill_with_bills_manage_privilege() -> None:
    with _client(privileges={"bills.manage"}, legacy_role="member") as client:
        response = client.post(
            "/api/v1/bills",
            json={
                "client_id": "88888888-8888-4888-8888-888888888888",
                "currency": "USD",
                "lines": [
                    {
                        "description": "Cloud hosting",
                        "quantity": "1",
                        "unit_price": "100.00",
                        "amount": "100.00",
                    }
                ],
            },
        )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "draft"


def test_void_bill_requires_bills_manage_privilege() -> None:
    with _client(privileges=set(), legacy_role="admin") as client:
        response = client.post(f"/api/v1/bills/{BILL_ID}/void")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: bills.manage"
