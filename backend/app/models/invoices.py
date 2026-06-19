"""Pydantic request/response models for the Invoices resource.

Money fields use Decimal internally; serialised as strings in JSON per the
Aethos money gate.
"""
# Prahari review required — see docs/team/SECURITY_REVIEW.md

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.money import serialise_money

# ---------------------------------------------------------------------------
# Invoice line models
# ---------------------------------------------------------------------------


class InvoiceLineCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=1000)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate_id: str | None = None
    time_entry_id: str | None = None
    expense_id: str | None = None


class InvoiceLineResponse(BaseModel):
    id: str
    invoice_id: str
    description: str
    quantity: str
    unit_price: str
    amount: str
    tax_rate_id: str | None
    tax_amount: str
    time_entry_id: str | None
    expense_id: str | None
    created_at: datetime

    @classmethod
    def from_db(cls, row: dict) -> InvoiceLineResponse:
        # Money fields always quantised to 2dp (bug #93). Quantity is a count
        # (Decimal hours / units) and renders as-is — not money.
        return cls(
            id=str(row["id"]),
            invoice_id=str(row["invoice_id"]),
            description=row["description"],
            quantity=str(row.get("quantity", "1")),
            unit_price=serialise_money(row.get("unit_price") or "0") or "0.00",
            amount=serialise_money(row.get("amount") or "0") or "0.00",
            tax_rate_id=str(row["tax_rate_id"]) if row.get("tax_rate_id") else None,
            tax_amount=serialise_money(row.get("tax_amount") or "0") or "0.00",
            time_entry_id=str(row["time_entry_id"]) if row.get("time_entry_id") else None,
            expense_id=str(row["expense_id"]) if row.get("expense_id") else None,
            created_at=row["created_at"],
        )


# ---------------------------------------------------------------------------
# Invoice create / update models
# ---------------------------------------------------------------------------


class InvoiceCreate(BaseModel):
    engagement_id: str = Field(..., description="UUID of the parent engagement")
    client_id: str = Field(..., description="UUID of the client being invoiced")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    issue_date: date | None = None
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)
    lines: list[InvoiceLineCreate] = Field(default_factory=list, min_length=1)


class ManualPaymentCreate(BaseModel):
    """Body for POST /invoices/{id}/payments — a payment received outside Stripe."""

    amount: str = Field(..., description="Decimal string, e.g. '700.00'")
    currency: str | None = Field(
        default=None,
        description="3-letter ISO; defaults to the invoice currency",
        min_length=3, max_length=3,
    )
    paid_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp; defaults to now",
    )
    notes: str | None = Field(default=None, max_length=1000)


class InvoiceResponse(BaseModel):
    id: str
    tenant_id: str
    engagement_id: str
    client_id: str
    invoice_number: str
    currency: str
    subtotal: str
    tax_total: str
    total: str
    status: str
    issue_date: date | None
    due_date: date | None
    paid_at: datetime | None
    stripe_payment_link_id: str | None
    stripe_payment_link_url: str | None
    public_token: str | None
    sent_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    lines: list[InvoiceLineResponse] = Field(default_factory=list)
    # Populated when sending — not persisted, returned in-response
    payment_link_url: str | None = None
    # List-view conveniences — populated by InvoicesService.list_invoices via
    # an embedded join. The frontend list table renders these directly so it
    # does not have to fetch each client by id (previously the Invoices page
    # showed blank Client + "—" Total).
    client_name: str | None = None
    total_amount: str | None = None

    @classmethod
    def from_db(
        cls,
        row: dict,
        lines: list[dict] | None = None,
    ) -> InvoiceResponse:
        # Joined-row convention: clients is either {"name": "..."} or a list
        # with one dict (PostgREST returns a list when the FK is reverse).
        client_join = row.get("clients")
        client_name: str | None = None
        if isinstance(client_join, dict):
            client_name = client_join.get("name")
        elif isinstance(client_join, list) and client_join:
            client_name = (client_join[0] or {}).get("name")
        total_str = serialise_money(row.get("total") or "0") or "0.00"

        return cls(
            id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            engagement_id=str(row["engagement_id"]),
            client_id=str(row["client_id"]),
            invoice_number=row.get("invoice_number", ""),
            currency=row.get("currency", "USD"),
            subtotal=serialise_money(row.get("subtotal") or "0") or "0.00",
            tax_total=serialise_money(row.get("tax_total") or "0") or "0.00",
            total=total_str,
            status=row.get("status", "draft"),
            issue_date=row.get("issue_date"),
            due_date=row.get("due_date"),
            paid_at=row.get("paid_at"),
            stripe_payment_link_id=row.get("stripe_payment_link_id"),
            stripe_payment_link_url=row.get("stripe_payment_link_url"),
            public_token=row.get("public_token"),
            sent_at=row.get("sent_at"),
            notes=row.get("notes"),
            created_at=row["created_at"],
            client_name=client_name,
            total_amount=total_str,
            updated_at=row["updated_at"],
            lines=[InvoiceLineResponse.from_db(ln) for ln in (lines or [])],
            payment_link_url=row.get("payment_link_url"),
        )


# ---------------------------------------------------------------------------
# Public invoice model (no auth — redacted fields)
# ---------------------------------------------------------------------------


class PublicInvoiceResponse(BaseModel):
    """Safe subset of invoice fields for the unauthenticated payment page."""

    id: str
    invoice_number: str
    currency: str
    subtotal: str
    tax_total: str
    total: str
    status: str
    issue_date: date | None
    due_date: date | None
    notes: str | None
    stripe_payment_link_url: str | None
    lines: list[InvoiceLineResponse] = Field(default_factory=list)

    @classmethod
    def from_db(cls, row: dict, lines: list[dict] | None = None) -> PublicInvoiceResponse:
        return cls(
            id=str(row["id"]),
            invoice_number=row.get("invoice_number", ""),
            currency=row.get("currency", "USD"),
            subtotal=serialise_money(row.get("subtotal") or "0") or "0.00",
            tax_total=serialise_money(row.get("tax_total") or "0") or "0.00",
            total=serialise_money(row.get("total") or "0") or "0.00",
            status=row.get("status", "draft"),
            issue_date=row.get("issue_date"),
            due_date=row.get("due_date"),
            notes=row.get("notes"),
            stripe_payment_link_url=row.get("stripe_payment_link_url"),
            lines=[InvoiceLineResponse.from_db(ln) for ln in (lines or [])],
        )


# ---------------------------------------------------------------------------
# Stripe Connect models (issue #51)
# ---------------------------------------------------------------------------


class ConnectOAuthUrlResponse(BaseModel):
    url: str


class ConnectStatusResponse(BaseModel):
    status: Literal[
        "not_connected", "pending", "active", "restricted", "deauthorized"
    ]
    charges_enabled: bool
    payouts_enabled: bool
    stripe_connect_account_id: str | None
