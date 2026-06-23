"""Pydantic schemas for procurement documents used by AP matching."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

ProcurementDocumentType = Literal["purchase_request", "purchase_order", "service_order"]
ProcurementOrderType = Literal["purchase_order", "service_order"]
ProcurementDocumentStatus = Literal["draft", "submitted", "approved", "closed", "cancelled"]


class ProcurementLineCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    unit_price: Decimal = Field(..., ge=Decimal("0"))
    amount: Decimal = Field(..., ge=Decimal("0"))
    tax_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    account_id: str | None = None
    service_start_date: date | None = None
    service_end_date: date | None = None


class ProcurementDocumentCreate(BaseModel):
    document_type: ProcurementDocumentType = "purchase_order"
    client_id: str = Field(..., description="Vendor contact id")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    issue_date: date | None = None
    expected_delivery_date: date | None = None
    service_start_date: date | None = None
    service_end_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[ProcurementLineCreate] = Field(default_factory=list)


class ProcurementLineResponse(BaseModel):
    id: str
    procurement_document_id: str
    description: str
    quantity: str
    unit_price: str
    amount: str
    tax_amount: str
    account_id: str | None
    service_start_date: str | None = None
    service_end_date: str | None = None
    created_at: str


class ProcurementDocumentResponse(BaseModel):
    id: str
    tenant_id: str
    document_type: ProcurementDocumentType
    document_number: str
    client_id: str
    source_request_id: str | None = None
    status: ProcurementDocumentStatus
    currency: str
    issue_date: str | None
    expected_delivery_date: str | None
    service_start_date: str | None
    service_end_date: str | None
    subtotal: str
    tax_total: str
    total: str
    matched_bill_total: str
    remaining_total: str
    requested_by: str | None
    approved_by: str | None
    approved_at: str | None
    notes: str | None
    created_at: str
    lines: list[ProcurementLineResponse] = Field(default_factory=list)


class ProcurementDocumentListResponse(BaseModel):
    items: list[ProcurementDocumentResponse]
    total: int


class ProcurementConvertRequest(BaseModel):
    document_type: ProcurementOrderType | None = None
