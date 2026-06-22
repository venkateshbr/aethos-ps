"""Project expenses service."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException, status

from app.domain.money import serialise_money
from app.models.expenses import ExpenseCreate, ExpenseResponse
from app.services._validation import assert_belongs_to_tenant
from supabase import Client


class ExpensesService:
    """Tenant-scoped project expense operations."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def list_expenses(
        self,
        *,
        project_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[ExpenseResponse]:
        """List project expenses for this tenant."""

        def _fetch() -> list[dict]:
            query = (
                self.db.table("project_expenses")
                .select(
                    "id, project_id, document_id, description, amount, currency, "
                    "expense_date, category, billable, billing_status"
                )
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .order("expense_date", desc=True)
            )
            if project_id:
                query = query.eq("project_id", project_id)
            if date_from:
                query = query.gte("expense_date", date_from)
            if date_to:
                query = query.lte("expense_date", date_to)
            return query.execute().data or []

        rows = await asyncio.to_thread(_fetch)
        return [ExpenseResponse.from_db(row) for row in rows]

    async def create_expense(
        self,
        project_id: str,
        payload: ExpenseCreate,
    ) -> ExpenseResponse:
        """Create a project-scoped expense."""

        await assert_belongs_to_tenant(
            self.db,
            "projects",
            project_id,
            self.tenant_id,
            not_found_detail="Project not found",
        )

        amount = serialise_money(payload.amount)
        if amount is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Amount is required",
            )
        row = {
            "tenant_id": self.tenant_id,
            "project_id": project_id,
            "description": payload.description,
            "amount": amount,
            "currency": payload.currency,
            "base_amount": amount,
            "expense_date": payload.expense_date.isoformat(),
            "category": payload.category,
            "billable": payload.billable,
            "billing_status": "unbilled" if payload.billable else "non_billable",
        }

        def _insert() -> dict:
            result = self.db.table("project_expenses").insert(row).execute()
            return (result.data or [])[0]

        created = await asyncio.to_thread(_insert)
        return ExpenseResponse.from_db(created)
