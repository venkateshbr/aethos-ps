"""Pydantic request/response schemas for the Bills (AP) API.

Money rules:
- Input: Decimal fields (Python precision, no float leakage)
- Output: serialised as str in JSON (JSON number precision is not guaranteed)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class BillLineCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    unit_price: Decimal = Field(..., ge=Decimal("0"))
    amount: Decimal = Field(..., ge=Decimal("0"))
    tax_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    # Optional: override expense account; defaults to COA 5000 on approval
    account_id: str | None = None
    is_prepaid: bool = False
    service_start_date: date | None = None
    service_end_date: date | None = None

    @model_validator(mode="after")
    def validate_prepaid_schedule(self) -> BillLineCreate:
        if not self.is_prepaid:
            return self
        if self.service_start_date is None or self.service_end_date is None:
            raise ValueError("Prepaid lines require service_start_date and service_end_date")
        if self.service_end_date < self.service_start_date:
            raise ValueError("service_end_date must be on or after service_start_date")
        return self


class BillCreate(BaseModel):
    client_id: str = Field(..., description="Must reference a client with kind='vendor' or 'both'")
    purchase_order_id: str | None = Field(default=None, description="Approved PO/service order")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    issue_date: date | None = None
    due_date: date | None = None
    vendor_invoice_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[BillLineCreate] = Field(default_factory=list)


class BillLineResponse(BaseModel):
    id: str
    bill_id: str
    description: str
    quantity: str  # Decimal as string
    unit_price: str  # Decimal as string
    amount: str  # Decimal as string
    tax_amount: str  # Decimal as string
    account_id: str | None
    is_prepaid: bool = False
    service_start_date: str | None = None
    service_end_date: str | None = None
    created_at: str


class BillResponse(BaseModel):
    id: str
    tenant_id: str
    client_id: str
    purchase_order_id: str | None = None
    bill_number: str
    currency: str
    subtotal: str  # Decimal as string
    tax_total: str  # Decimal as string
    total: str  # Decimal as string
    base_currency: str | None = None
    base_subtotal: str | None = None
    base_tax_total: str | None = None
    base_total: str | None = None
    approval_fx_rate_id: str | None = None
    status: str
    issue_date: str | None
    due_date: str | None
    vendor_invoice_number: str | None
    po_match_status: str = "not_linked"
    po_match_summary: dict[str, object] = Field(default_factory=dict)
    vendor_invoice_review: dict[str, object] = Field(default_factory=dict)
    source_document_id: str | None = None
    notes: str | None
    created_at: str
    lines: list[BillLineResponse] = Field(default_factory=list)


class BillListResponse(BaseModel):
    items: list[BillResponse]
    total: int


class BillApproveResponse(BaseModel):
    id: str
    status: str
    # Will be None until accounting_guardian agent is wired; service posts synchronously for v1
    journal_entry_id: str | None
    message: str


class AgingBucket(BaseModel):
    label: str  # e.g. "current", "1-30", "31-60", "61-90", "90+"
    total: str  # Decimal as string
    count: int


class ApAgingResponse(BaseModel):
    buckets: list[AgingBucket]
    grand_total: str  # Decimal as string
