"""Privilege authorization contracts for procurement and bill-payment actions."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.bill_payments import _read_service as bill_payments_read_service
from app.api.v1.endpoints.bill_payments import _write_service as bill_payments_write_service
from app.api.v1.endpoints.procurement import _read_service as procurement_read_service
from app.api.v1.endpoints.procurement import _write_service as procurement_write_service
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.main import app
from app.models.procurement import ProcurementDocumentListResponse, ProcurementDocumentResponse

pytestmark = pytest.mark.unit

TENANT_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-4222-8222-222222222222"
DOCUMENT_ID = "33333333-3333-4333-8333-333333333333"
BATCH_ID = "44444444-4444-4444-8444-444444444444"
BILL_ID = "55555555-5555-4555-8555-555555555555"


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

    def lte(self, _key: str, _value: Any) -> _PermissionQuery:
        return self

    def execute(self) -> _Result:
        rows = self._db.rows.get(self._table, [])
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
            "bills": [],
        }

    def table(self, name: str) -> _PermissionQuery:
        return _PermissionQuery(self, name)


class _BillPaymentsStub:
    def list_batches(self, status: str | None = None) -> list[dict[str, Any]]:
        return [{"id": BATCH_ID, "status": status or "draft"}]

    def get_batch(self, batch_id: str) -> dict[str, Any]:
        assert batch_id == BATCH_ID
        return {"id": BATCH_ID, "status": "draft", "items": []}

    def create_batch(
        self,
        bill_ids: list[str],
        _pay_date: Any,
        _bank_account_label: str,
        created_by: str,
    ) -> dict[str, Any]:
        assert bill_ids == [BILL_ID]
        assert created_by == USER_ID
        return {"id": BATCH_ID, "status": "draft", "items": []}

    def approve_batch(self, batch_id: str, approved_by: str) -> dict[str, Any]:
        assert batch_id == BATCH_ID
        assert approved_by == USER_ID
        return {"id": BATCH_ID, "status": "approved"}

    def export_csv(self, batch_id: str, exported_by: str) -> bytes:
        assert batch_id == BATCH_ID
        assert exported_by == USER_ID
        return b"Vendor,Amount\nAcme,100.00\n"

    def mark_sent(self, batch_id: str, sent_by: str) -> dict[str, Any]:
        assert batch_id == BATCH_ID
        assert sent_by == USER_ID
        return {"id": BATCH_ID, "status": "sent_to_bank"}

    def settle_batch(self, batch_id: str, settled_by: str) -> dict[str, Any]:
        assert batch_id == BATCH_ID
        assert settled_by == USER_ID
        return {
            "batch_id": BATCH_ID,
            "status": "settled",
            "settled_count": 1,
            "journal_entry_ids": [],
        }


class _ProcurementStub:
    async def list_documents(self, **_kwargs: Any) -> ProcurementDocumentListResponse:
        return ProcurementDocumentListResponse(
            items=[_procurement_document()],
            total=1,
        )

    async def get_document(
        self,
        document_id: str,
    ) -> ProcurementDocumentResponse:
        assert document_id == DOCUMENT_ID
        return _procurement_document()

    async def create_document(
        self,
        _payload: Any,
        *,
        requested_by: str,
    ) -> ProcurementDocumentResponse:
        assert requested_by == USER_ID
        return _procurement_document()

    async def convert_request_to_order(
        self,
        document_id: str,
        *,
        payload: Any,
        converted_by: str,
    ) -> ProcurementDocumentResponse:
        assert document_id == DOCUMENT_ID
        assert payload.document_type == "service_order"
        assert converted_by == USER_ID
        return _procurement_document(
            document_type="service_order",
            document_number="SO-0001",
            source_request_id=DOCUMENT_ID,
        )

    async def approve_document(
        self,
        document_id: str,
        *,
        approved_by: str,
        approver_role: str,
    ) -> ProcurementDocumentResponse:
        assert document_id == DOCUMENT_ID
        assert approved_by == USER_ID
        return _procurement_document(
            status="approved",
            approved_by=USER_ID,
            approval_required_role="manager",
            approval_policy_snapshot={"observed_approver_role": approver_role},
        )


@contextmanager
def _client(
    *,
    privileges: set[str],
    legacy_role: str,
    token_role: str | None = None,
) -> Iterator[TestClient]:
    db = _PermissionDb(privileges, legacy_role)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=USER_ID,
        email="finance@example.com",
        role=token_role or legacy_role,
    )
    app.dependency_overrides[get_tenant_id] = lambda: TENANT_ID
    app.dependency_overrides[get_service_role_client] = lambda: db
    bill_payments = _BillPaymentsStub()
    procurement = _ProcurementStub()
    app.dependency_overrides[bill_payments_read_service] = lambda: bill_payments
    app.dependency_overrides[bill_payments_write_service] = lambda: bill_payments
    app.dependency_overrides[procurement_read_service] = lambda: procurement
    app.dependency_overrides[procurement_write_service] = lambda: procurement
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _procurement_document(**changes: Any) -> ProcurementDocumentResponse:
    values: dict[str, Any] = {
        "id": DOCUMENT_ID,
        "tenant_id": TENANT_ID,
        "document_type": "purchase_order",
        "document_number": "PO-0001",
        "client_id": "66666666-6666-4666-8666-666666666666",
        "status": "draft",
        "currency": "USD",
        "issue_date": None,
        "expected_delivery_date": None,
        "service_start_date": None,
        "service_end_date": None,
        "subtotal": "100.00",
        "tax_total": "0.00",
        "total": "100.00",
        "matched_bill_total": "0.00",
        "remaining_total": "100.00",
        "requested_by": USER_ID,
        "approved_by": None,
        "approved_at": None,
        "notes": None,
        "created_at": "2026-07-12T00:00:00+00:00",
        "lines": [],
    }
    values.update(changes)
    return ProcurementDocumentResponse(**values)


def test_ap_manager_can_prepare_a_bill_payment_batch_without_admin_fallback() -> None:
    with _client(
        privileges={"bill_payments.prepare"},
        legacy_role="manager",
    ) as client:
        response = client.post(
            "/api/v1/bill-payments/batches",
            json={"bill_ids": [BILL_ID], "bank_account_label": "Operating"},
        )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == BATCH_ID


def test_ap_manager_can_approve_a_bill_payment_batch_with_explicit_privilege() -> None:
    with _client(
        privileges={"bill_payments.approve"},
        legacy_role="manager",
    ) as client:
        response = client.post(f"/api/v1/bill-payments/batches/{BATCH_ID}/approve")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"


def test_finance_approver_cannot_approve_bill_payments_without_exact_privilege() -> None:
    with _client(
        privileges={"procurement.approve"},
        legacy_role="approver",
    ) as client:
        response = client.post(f"/api/v1/bill-payments/batches/{BATCH_ID}/approve")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: bill_payments.approve"


def test_ap_manager_can_export_a_payment_file_with_export_privilege() -> None:
    with _client(
        privileges={"bill_payments.export"},
        legacy_role="manager",
    ) as client:
        response = client.get(
            f"/api/v1/bill-payments/batches/{BATCH_ID}/export?format=csv"
        )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert response.content.startswith(b"Vendor,Amount")


def test_mark_sent_requires_settlement_privilege_not_export_privilege() -> None:
    with _client(
        privileges={"bill_payments.settle"},
        legacy_role="manager",
    ) as client:
        response = client.patch(
            f"/api/v1/bill-payments/batches/{BATCH_ID}/mark-sent"
        )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "sent_to_bank"


def test_ap_manager_can_confirm_settlement_with_settlement_privilege() -> None:
    with _client(
        privileges={"bill_payments.settle"},
        legacy_role="manager",
    ) as client:
        response = client.post(
            f"/api/v1/bill-payments/batches/{BATCH_ID}/settle"
        )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "settled"


def test_ap_manager_can_request_a_payment_proposal_with_prepare_privilege() -> None:
    with _client(
        privileges={"bill_payments.prepare"},
        legacy_role="manager",
    ) as client:
        response = client.post("/api/v1/bill-payments/propose?due_within_days=7")

    assert response.status_code == 200, response.text
    assert response.json()["proposed_bill_ids"] == []
    assert response.json()["skipped_reason"] == "no_approved_bills"


@pytest.mark.parametrize(
    ("method", "path", "granted_privilege", "required_privilege"),
    [
        (
            "post",
            "/api/v1/bill-payments/batches",
            "bill_payments.approve",
            "bill_payments.prepare",
        ),
        (
            "post",
            f"/api/v1/bill-payments/batches/{BATCH_ID}/approve",
            "bill_payments.prepare",
            "bill_payments.approve",
        ),
        (
            "get",
            f"/api/v1/bill-payments/batches/{BATCH_ID}/export?format=csv",
            "bill_payments.settle",
            "bill_payments.export",
        ),
        (
            "patch",
            f"/api/v1/bill-payments/batches/{BATCH_ID}/mark-sent",
            "bill_payments.export",
            "bill_payments.settle",
        ),
        (
            "post",
            f"/api/v1/bill-payments/batches/{BATCH_ID}/settle",
            "bill_payments.export",
            "bill_payments.settle",
        ),
        (
            "post",
            "/api/v1/bill-payments/propose?due_within_days=7",
            "bill_payments.approve",
            "bill_payments.prepare",
        ),
    ],
)
def test_bill_payment_mutations_reject_an_adjacent_privilege(
    method: str,
    path: str,
    granted_privilege: str,
    required_privilege: str,
) -> None:
    request_kwargs: dict[str, Any] = {}
    if path == "/api/v1/bill-payments/batches":
        request_kwargs["json"] = {
            "bill_ids": [BILL_ID],
            "bank_account_label": "Operating",
        }
    with _client(
        privileges={granted_privilege},
        legacy_role="admin",
    ) as client:
        response = client.request(method, path, **request_kwargs)

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == f"Permission required: {required_privilege}"


def test_procurement_manage_privilege_can_create_without_manager_role_fallback() -> None:
    with _client(
        privileges={"procurement.manage"},
        legacy_role="member",
    ) as client:
        response = client.post(
            "/api/v1/procurement/documents",
            json={
                "document_type": "purchase_order",
                "client_id": "66666666-6666-4666-8666-666666666666",
                "currency": "USD",
                "lines": [
                    {
                        "description": "Cloud services",
                        "quantity": "1",
                        "unit_price": "100.00",
                        "amount": "100.00",
                    }
                ],
            },
        )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == DOCUMENT_ID


def test_procurement_manage_privilege_can_convert_an_approved_request() -> None:
    with _client(
        privileges={"procurement.manage"},
        legacy_role="member",
    ) as client:
        response = client.post(
            f"/api/v1/procurement/documents/{DOCUMENT_ID}/convert-to-order",
            json={"document_type": "service_order"},
        )

    assert response.status_code == 201, response.text
    assert response.json()["document_type"] == "service_order"


def test_procurement_approver_cannot_create_without_manage_privilege() -> None:
    with _client(
        privileges={"procurement.approve"},
        legacy_role="approver",
    ) as client:
        response = client.post(
            "/api/v1/procurement/documents",
            json={
                "document_type": "purchase_order",
                "client_id": "66666666-6666-4666-8666-666666666666",
                "currency": "USD",
                "lines": [
                    {
                        "description": "Cloud services",
                        "quantity": "1",
                        "unit_price": "100.00",
                        "amount": "100.00",
                    }
                ],
            },
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: procurement.manage"


def test_procurement_manager_cannot_approve_with_manage_privilege_alone() -> None:
    with _client(
        privileges={"procurement.manage"},
        legacy_role="manager",
    ) as client:
        response = client.post(
            f"/api/v1/procurement/documents/{DOCUMENT_ID}/approve"
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: procurement.approve"


def test_manager_without_procurement_approve_privilege_cannot_approve() -> None:
    with _client(privileges=set(), legacy_role="manager") as client:
        response = client.post(
            f"/api/v1/procurement/documents/{DOCUMENT_ID}/approve"
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: procurement.approve"


def test_procurement_manager_approval_retains_verified_threshold_role() -> None:
    with _client(
        privileges={"procurement.approve"},
        legacy_role="manager",
        token_role="authenticated",
    ) as client:
        response = client.post(
            f"/api/v1/procurement/documents/{DOCUMENT_ID}/approve"
        )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"
    assert response.json()["approval_policy_snapshot"]["observed_approver_role"] == (
        "manager"
    )


def test_procurement_read_denies_a_role_without_read_privilege() -> None:
    with _client(privileges=set(), legacy_role="viewer") as client:
        response = client.get("/api/v1/procurement/documents")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: procurement.read"


def test_bill_payment_read_denies_a_role_without_read_privilege() -> None:
    with _client(privileges=set(), legacy_role="viewer") as client:
        response = client.get("/api/v1/bill-payments/batches")

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Permission required: bill_payments.read"
