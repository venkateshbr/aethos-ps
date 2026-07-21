"""Business logic for procurement documents and PO/service-order approval."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status

from app.core.rbac import UserRole, role_allows_approval
from app.domain.money import serialise_money
from app.models.procurement import (
    ProcurementConvertRequest,
    ProcurementDocumentCreate,
    ProcurementDocumentListResponse,
    ProcurementDocumentResponse,
    ProcurementLineResponse,
)
from app.repositories.clients_repo import ClientRepository
from app.repositories.procurement_repo import ProcurementRepository
from app.services._validation import assert_belongs_to_tenant
from supabase import Client

_VENDOR_KINDS = {"vendor", "both"}
_MANAGER_APPROVAL_LIMIT = Decimal("5000.00")
_OWNER_APPROVAL_THRESHOLD = Decimal("50000.00")


def _approval_policy_for(
    *,
    total: Decimal,
    currency: str,
    document_type: str,
    cost_center_code: str | None,
) -> dict[str, Any]:
    """Build the deterministic launch approval route for procurement spend."""
    if total >= _OWNER_APPROVAL_THRESHOLD:
        required_role = UserRole.owner
        reason = "amount_at_or_above_owner_threshold"
    elif total > _MANAGER_APPROVAL_LIMIT:
        required_role = UserRole.admin
        reason = "amount_above_manager_limit"
    else:
        required_role = UserRole.manager
        reason = "amount_within_manager_limit"

    route: list[dict[str, Any]] = []
    if cost_center_code:
        route.append(
            {
                "step": "cost_center_review",
                "role": UserRole.manager.value,
                "cost_center_code": cost_center_code,
                "reason": "cost_center_coded_request",
            }
        )
    route.append(
        {
            "step": "final_approval",
            "role": required_role.value,
            "reason": reason,
        }
    )

    return {
        "required_role": required_role.value,
        "route": route,
        "snapshot": {
            "policy_version": "procurement_approval_v1",
            "document_type": document_type,
            "currency": currency,
            "total": serialise_money(total) or "0.00",
            "cost_center_code": cost_center_code,
            "manager_limit": serialise_money(_MANAGER_APPROVAL_LIMIT),
            "owner_threshold": serialise_money(_OWNER_APPROVAL_THRESHOLD),
            "reason": reason,
        },
    }


def _approval_patch(
    *,
    total: Decimal,
    currency: str,
    document_type: str,
    cost_center_code: str | None,
) -> dict[str, Any]:
    policy = _approval_policy_for(
        total=total,
        currency=currency,
        document_type=document_type,
        cost_center_code=cost_center_code,
    )
    return {
        "approval_required_role": policy["required_role"],
        "approval_route": policy["route"],
        "approval_policy_snapshot": policy["snapshot"],
    }


def _role_allows(user_role: str | None, required_role: str) -> bool:
    try:
        resolved_user_role = UserRole(str(user_role))
    except ValueError:
        resolved_user_role = UserRole.viewer
    try:
        resolved_required_role = UserRole(required_role)
    except ValueError:
        resolved_required_role = UserRole.owner
    return role_allows_approval(resolved_user_role, resolved_required_role)


def _line_to_response(row: dict) -> ProcurementLineResponse:
    return ProcurementLineResponse(
        id=str(row["id"]),
        procurement_document_id=str(row["procurement_document_id"]),
        description=row["description"],
        quantity=str(row["quantity"]),
        unit_price=serialise_money(row["unit_price"]) or "0.00",
        amount=serialise_money(row["amount"]) or "0.00",
        tax_amount=serialise_money(row.get("tax_amount") or "0") or "0.00",
        account_id=str(row["account_id"]) if row.get("account_id") else None,
        service_start_date=(
            str(row["service_start_date"]) if row.get("service_start_date") else None
        ),
        service_end_date=(str(row["service_end_date"]) if row.get("service_end_date") else None),
        created_at=str(row["created_at"]),
    )


def _document_to_response(
    row: dict,
    lines: list[dict] | None = None,
) -> ProcurementDocumentResponse:
    total = Decimal(str(row.get("total") or "0"))
    matched = Decimal(str(row.get("matched_bill_total") or "0"))
    remaining = max(total - matched, Decimal("0"))
    return ProcurementDocumentResponse(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        document_type=row["document_type"],
        document_number=row["document_number"],
        client_id=str(row["client_id"]),
        source_request_id=str(row["source_request_id"]) if row.get("source_request_id") else None,
        status=row["status"],
        currency=row["currency"],
        cost_center_code=row.get("cost_center_code"),
        approval_required_role=row.get("approval_required_role") or "manager",
        approval_policy_snapshot=row.get("approval_policy_snapshot") or {},
        approval_route=row.get("approval_route") or [],
        issue_date=str(row["issue_date"]) if row.get("issue_date") else None,
        expected_delivery_date=(
            str(row["expected_delivery_date"]) if row.get("expected_delivery_date") else None
        ),
        service_start_date=(
            str(row["service_start_date"]) if row.get("service_start_date") else None
        ),
        service_end_date=(str(row["service_end_date"]) if row.get("service_end_date") else None),
        subtotal=serialise_money(row.get("subtotal") or "0") or "0.00",
        tax_total=serialise_money(row.get("tax_total") or "0") or "0.00",
        total=serialise_money(total) or "0.00",
        matched_bill_total=serialise_money(matched) or "0.00",
        remaining_total=serialise_money(remaining) or "0.00",
        requested_by=row.get("requested_by"),
        approved_by=row.get("approved_by"),
        approved_at=str(row["approved_at"]) if row.get("approved_at") else None,
        notes=row.get("notes"),
        created_at=str(row["created_at"]),
        lines=[_line_to_response(line) for line in (lines or [])],
    )


class ProcurementService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id
        self._repo = ProcurementRepository(db, tenant_id)
        self._clients_repo = ClientRepository(db, tenant_id)

    async def list_documents(
        self,
        *,
        document_type: str | None = None,
        status_filter: str | None = None,
        client_id: str | None = None,
        limit: int = 50,
    ) -> ProcurementDocumentListResponse:
        rows = await self._repo.list(
            document_type=document_type,
            status=status_filter,
            client_id=client_id,
            limit=limit,
        )
        items = [_document_to_response(row) for row in rows]
        return ProcurementDocumentListResponse(items=items, total=len(items))

    async def get_document(self, document_id: str) -> ProcurementDocumentResponse | None:
        row = await self._repo.get(document_id)
        if row is None:
            return None
        lines = await self._repo.get_lines(document_id)
        return _document_to_response(row, lines)

    async def create_document(
        self,
        data: ProcurementDocumentCreate,
        *,
        requested_by: str,
    ) -> ProcurementDocumentResponse:
        client = await self._clients_repo.get(data.client_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {data.client_id!r} not found",
            )
        if client.get("kind") not in _VENDOR_KINDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Procurement documents require a vendor-capable contact",
            )

        payload: dict = {
            "document_type": data.document_type,
            "client_id": data.client_id,
            "currency": data.currency,
            "status": "draft",
            "requested_by": requested_by,
        }
        if data.cost_center_code:
            payload["cost_center_code"] = data.cost_center_code
        for field in (
            "issue_date",
            "expected_delivery_date",
            "service_start_date",
            "service_end_date",
        ):
            value = getattr(data, field)
            if value is not None:
                payload[field] = value.isoformat()
        if data.notes is not None:
            payload["notes"] = data.notes

        doc_row = await self._repo.create(payload)
        document_id = str(doc_row["id"])

        subtotal = Decimal("0")
        tax_total = Decimal("0")
        line_rows: list[dict] = []
        for line in data.lines:
            line_payload = {
                "description": line.description,
                "quantity": str(line.quantity),
                "unit_price": serialise_money(line.unit_price),
                "amount": serialise_money(line.amount),
                "tax_amount": serialise_money(line.tax_amount),
            }
            if line.account_id is not None:
                await assert_belongs_to_tenant(
                    self._db,
                    "accounts",
                    line.account_id,
                    self._tenant_id,
                    not_found_detail="Account not found",
                )
                line_payload["account_id"] = line.account_id
            if line.service_start_date is not None:
                line_payload["service_start_date"] = line.service_start_date.isoformat()
            if line.service_end_date is not None:
                line_payload["service_end_date"] = line.service_end_date.isoformat()
            line_row = await self._repo.create_line(document_id, line_payload)
            line_rows.append(line_row)
            subtotal += line.amount
            tax_total += line.tax_amount

        total = subtotal + tax_total
        update_payload = {
            "subtotal": serialise_money(subtotal),
            "tax_total": serialise_money(tax_total),
            "total": serialise_money(total),
            **_approval_patch(
                total=total,
                currency=data.currency,
                document_type=data.document_type,
                cost_center_code=data.cost_center_code,
            ),
        }
        updated = await self._repo.update(document_id, update_payload)
        doc_row = updated or {**doc_row, **update_payload}

        return _document_to_response(doc_row, line_rows)

    async def approve_document(
        self,
        document_id: str,
        *,
        approved_by: str,
        approver_role: str,
    ) -> ProcurementDocumentResponse | None:
        row = await self._repo.get(document_id)
        if row is None:
            return None
        if row.get("status") not in {"draft", "submitted"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Procurement document is already {row.get('status')!r}",
            )
        if str(row.get("requested_by") or "") == approved_by:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "procurement_requester_cannot_approve",
                    "message": (
                        "The requester cannot approve their own procurement document"
                    ),
                },
            )
        lines = await self._repo.get_lines(document_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Procurement document has no lines",
            )
        total = Decimal(str(row.get("total") or "0"))
        if total <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Procurement document total must be greater than zero",
            )
        required_role = str(row.get("approval_required_role") or "manager")
        if not _role_allows(approver_role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "procurement_approval_role_required",
                    "required_role": required_role,
                    "approver_role": approver_role,
                    "approval_route": row.get("approval_route") or [],
                },
            )

        updated = await self._repo.update(
            document_id,
            {
                "status": "approved",
                "approved_by": approved_by,
                "approved_at": datetime.now(UTC).isoformat(),
            },
        )
        return _document_to_response(updated, lines) if updated else None

    async def convert_request_to_order(
        self,
        document_id: str,
        *,
        payload: ProcurementConvertRequest,
        converted_by: str,
    ) -> ProcurementDocumentResponse | None:
        request = await self._repo.get(document_id)
        if request is None:
            return None
        if request.get("document_type") != "purchase_request":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Only purchase requests can be converted to procurement orders",
            )
        if request.get("status") != "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Purchase request must be approved before conversion",
            )

        target_type = payload.document_type
        if target_type is None:
            target_type = (
                "service_order"
                if request.get("service_start_date") or request.get("service_end_date")
                else "purchase_order"
            )

        order_payload = {
            "document_type": target_type,
            "client_id": request["client_id"],
            "currency": request.get("currency") or "USD",
            "status": "draft",
            "requested_by": converted_by,
            "source_request_id": document_id,
            "cost_center_code": request.get("cost_center_code"),
            "notes": request.get("notes"),
        }
        for field in (
            "issue_date",
            "expected_delivery_date",
            "service_start_date",
            "service_end_date",
        ):
            if request.get(field):
                order_payload[field] = str(request[field])

        order = await self._repo.create(order_payload)
        order_id = str(order["id"])

        subtotal = Decimal("0")
        tax_total = Decimal("0")
        order_lines: list[dict] = []
        for line in await self._repo.get_lines(document_id):
            line_payload = {
                "description": line["description"],
                "quantity": str(line.get("quantity") or "1"),
                "unit_price": serialise_money(line.get("unit_price") or "0"),
                "amount": serialise_money(line.get("amount") or "0"),
                "tax_amount": serialise_money(line.get("tax_amount") or "0"),
            }
            if line.get("account_id"):
                line_payload["account_id"] = line["account_id"]
            if line.get("service_start_date"):
                line_payload["service_start_date"] = str(line["service_start_date"])
            if line.get("service_end_date"):
                line_payload["service_end_date"] = str(line["service_end_date"])
            created_line = await self._repo.create_line(order_id, line_payload)
            order_lines.append(created_line)
            subtotal += Decimal(str(line.get("amount") or "0"))
            tax_total += Decimal(str(line.get("tax_amount") or "0"))

        total = subtotal + tax_total
        update_payload = {
            "subtotal": serialise_money(subtotal),
            "tax_total": serialise_money(tax_total),
            "total": serialise_money(total),
            **_approval_patch(
                total=total,
                currency=order_payload["currency"],
                document_type=target_type,
                cost_center_code=order_payload.get("cost_center_code"),
            ),
        }
        updated = await self._repo.update(
            order_id,
            update_payload,
        )
        order = updated or {**order, **update_payload}
        return _document_to_response(order, order_lines)
