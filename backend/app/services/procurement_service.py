"""Business logic for procurement documents and PO/service-order approval."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status

from app.domain.money import serialise_money
from app.models.procurement import (
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
        status=row["status"],
        currency=row["currency"],
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
        if data.lines:
            await self._repo.update_totals(
                document_id,
                subtotal=subtotal,
                tax_total=tax_total,
                total=total,
            )
            doc_row = await self._repo.get(document_id) or doc_row
            doc_row["subtotal"] = serialise_money(subtotal)
            doc_row["tax_total"] = serialise_money(tax_total)
            doc_row["total"] = serialise_money(total)

        return _document_to_response(doc_row, line_rows)

    async def approve_document(
        self,
        document_id: str,
        *,
        approved_by: str,
    ) -> ProcurementDocumentResponse | None:
        row = await self._repo.get(document_id)
        if row is None:
            return None
        if row.get("status") not in {"draft", "submitted"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Procurement document is already {row.get('status')!r}",
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

        updated = await self._repo.update(
            document_id,
            {
                "status": "approved",
                "approved_by": approved_by,
                "approved_at": datetime.now(UTC).isoformat(),
            },
        )
        return _document_to_response(updated, lines) if updated else None
