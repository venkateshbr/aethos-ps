"""Pydantic schemas for project expenses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.domain.money import quantise_money, serialise_money


class ExpenseResponse(BaseModel):
    """Expense row shape consumed by the Angular expenses table."""

    id: str
    project_id: str
    date: str
    vendor: str
    amount: str
    currency: str
    category: str
    billable: bool
    description: str | None = None
    status: str | None = None
    document_id: str | None = None

    @classmethod
    def from_db(cls, row: dict) -> ExpenseResponse:
        description = row.get("description") or "Expense"
        return cls(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            date=str(row.get("expense_date") or ""),
            vendor=str(row.get("vendor") or description),
            amount=serialise_money(row.get("amount")) or "0.00",
            currency=str(row.get("currency") or "USD"),
            category=str(row.get("category") or "other"),
            billable=bool(row.get("billable")),
            description=description,
            status=row.get("billing_status"),
            document_id=str(row["document_id"]) if row.get("document_id") else None,
        )


class ExpenseCreate(BaseModel):
    """Create a project expense.

    ``project_id`` is optional here so top-level POST /expenses can use the same
    schema, but that route rejects missing project_id because the DB table
    requires project-scoped expenses.
    """

    project_id: str | None = None
    description: str
    amount: Decimal
    currency: str = "USD"
    category: str
    expense_date: date
    billable: bool = True

    @field_validator("description", "category")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field is required")
        return cleaned

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Amount must be positive")
        result = quantise_money(value)
        if result is None:
            raise ValueError("Amount could not be quantised")
        return result
