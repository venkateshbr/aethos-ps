"""Recurring journal template persistence for month-end close."""

from __future__ import annotations

import asyncio
from typing import Any

from app.models.accounting import (
    RecurringJournalTemplateCreate,
    RecurringJournalTemplateLineResponse,
    RecurringJournalTemplateResponse,
)
from supabase import Client


class RecurringJournalTemplateService:
    """Create and list recurring journal templates for a tenant."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def list_templates(self) -> list[RecurringJournalTemplateResponse]:
        rows = await asyncio.to_thread(self._fetch_template_rows)
        template_ids = [str(row["id"]) for row in rows if row.get("id")]
        line_rows = await asyncio.to_thread(lambda: self._fetch_line_rows(template_ids))
        lines_by_template: dict[str, list[dict[str, Any]]] = {}
        for line in line_rows:
            lines_by_template.setdefault(str(line["template_id"]), []).append(line)
        return [_template_response(row, lines_by_template.get(str(row["id"]), [])) for row in rows]

    async def create_template(
        self,
        payload: RecurringJournalTemplateCreate,
        *,
        created_by: str,
    ) -> RecurringJournalTemplateResponse:
        template_row = await asyncio.to_thread(
            lambda: (
                self.db.table("recurring_journal_templates")
                .insert(
                    {
                        "tenant_id": self.tenant_id,
                        "name": payload.name,
                        "description": payload.description,
                        "schedule_day": payload.schedule_day,
                        "start_period": payload.start_period,
                        "end_period": payload.end_period,
                        "currency": payload.currency,
                        "is_active": payload.is_active,
                        "created_by": created_by,
                    }
                )
                .execute()
                .data[0]
            )
        )
        template_id = str(template_row["id"])
        line_payloads = [
            {
                "tenant_id": self.tenant_id,
                "template_id": template_id,
                "account_id": str(line.account_id),
                "direction": line.direction,
                "amount": str(line.amount),
                "description": line.description,
                "order_index": idx,
            }
            for idx, line in enumerate(payload.lines)
        ]
        line_rows = await asyncio.to_thread(
            lambda: (
                self.db.table("recurring_journal_template_lines")
                .insert(line_payloads)
                .execute()
                .data
                or []
            )
        )
        return _template_response(template_row, line_rows)

    def _fetch_template_rows(self) -> list[dict[str, Any]]:
        result = (
            self.db.table("recurring_journal_templates")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .order("name")
            .execute()
        )
        return result.data or []

    def _fetch_line_rows(self, template_ids: list[str]) -> list[dict[str, Any]]:
        if not template_ids:
            return []
        result = (
            self.db.table("recurring_journal_template_lines")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .in_("template_id", template_ids)
            .order("order_index")
            .execute()
        )
        return result.data or []


def _template_response(
    template: dict[str, Any],
    lines: list[dict[str, Any]],
) -> RecurringJournalTemplateResponse:
    ordered_lines = sorted(lines, key=lambda row: int(row.get("order_index") or 0))
    return RecurringJournalTemplateResponse(
        id=str(template["id"]),
        name=str(template["name"]),
        description=template.get("description"),
        schedule_day=int(template.get("schedule_day") or 31),
        start_period=str(template["start_period"]),
        end_period=template.get("end_period"),
        currency=str(template.get("currency") or "USD"),
        is_active=bool(template.get("is_active", True)),
        created_by=str(template["created_by"]) if template.get("created_by") else None,
        created_at=str(template["created_at"]) if template.get("created_at") else None,
        updated_at=str(template["updated_at"]) if template.get("updated_at") else None,
        lines=[
            RecurringJournalTemplateLineResponse(
                id=str(line["id"]),
                account_id=str(line["account_id"]),
                direction=line["direction"],
                amount=str(line["amount"]),
                description=line.get("description"),
                order_index=int(line.get("order_index") or 0),
            )
            for line in ordered_lines
        ],
    )
