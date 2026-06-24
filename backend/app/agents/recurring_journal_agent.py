"""Recurring journal agent helpers for month-end close.

The agent materializes active recurring journal templates into HITL draft
journal suggestions. Posting still runs through Inbox and ManualJournalService.
"""

from __future__ import annotations

import calendar
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel

from app.agents.base import AgentDeps
from app.agents.suggestion_writer import write_agent_suggestion
from app.domain.money import TWO_PLACES, serialise_money

_PERIOD_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
_PROPOSAL_TYPE = "recurring_journal"
_ACTIVE_SUGGESTION_STATUSES = [
    "pending",
    "approved",
    "approved_with_edits",
    "auto_applied",
]


class RecurringJournalProposalError(ValueError):
    """Raised when recurring journal proposals cannot be built safely."""


class RecurringJournalProposal(BaseModel):
    """HITL-ready recurring journal proposal."""

    proposal_type: str = _PROPOSAL_TYPE
    period: str
    template_id: str
    template_name: str
    currency: str
    schedule_day: int
    entry_date: str
    total_amount: str
    line_count: int
    confidence: float
    journal_entry: dict


def build_recurring_journal_proposals(
    deps: AgentDeps,
    period: str,
) -> list[RecurringJournalProposal]:
    """Build draft journals for active recurring templates in a period."""
    _, period_end = _period_bounds(period)
    templates = [
        row for row in _recurring_templates(deps) if _template_is_active_for_period(row, period)
    ]
    if not templates:
        return []

    template_ids = [str(row["id"]) for row in templates]
    lines_by_template = _recurring_template_lines(deps, template_ids)

    proposals: list[RecurringJournalProposal] = []
    for template in sorted(templates, key=lambda row: str(row.get("name") or "")):
        template_id = str(template["id"])
        lines = lines_by_template.get(template_id, [])
        if len(lines) < 2:
            continue
        schedule_day = int(template.get("schedule_day") or 31)
        entry_date = period_end.replace(day=min(schedule_day, period_end.day))
        currency = str(template.get("currency") or "USD")
        journal_lines = _journal_lines(lines, currency)
        if not _lines_balance(journal_lines):
            continue
        total_amount = sum(
            _decimal_or_zero(line["amount"]) for line in journal_lines if line["direction"] == "DR"
        ).quantize(TWO_PLACES)
        if total_amount <= Decimal("0.00"):
            continue
        template_name = str(template.get("name") or "Recurring journal")
        description = f"Recurring journal: {template_name} ({period})"
        proposals.append(
            RecurringJournalProposal(
                period=period,
                template_id=template_id,
                template_name=template_name,
                currency=currency,
                schedule_day=schedule_day,
                entry_date=entry_date.isoformat(),
                total_amount=serialise_money(total_amount) or "0.00",
                line_count=len(journal_lines),
                confidence=0.9,
                journal_entry={
                    "description": description,
                    "entry_date": entry_date.isoformat(),
                    "reference": f"recurring-journal:{period}:{template_id}",
                    "lines": [
                        {
                            **line,
                            "description": line.get("description") or description,
                        }
                        for line in journal_lines
                    ],
                },
            )
        )
    return proposals


async def write_recurring_journal_suggestions(
    deps: AgentDeps,
    period: str,
) -> dict:
    """Persist recurring journal proposals as L2 HITL journal suggestions."""
    proposals = build_recurring_journal_proposals(deps, period)
    created: list[dict] = []
    skipped_duplicates = 0
    for proposal in proposals:
        if _has_existing_recurring_journal_suggestion(deps, proposal):
            skipped_duplicates += 1
            continue
        suggestion = await write_agent_suggestion(
            deps,
            agent_name="recurring_journal_agent",
            action_type="draft_journal",
            document_id=None,
            output=proposal.model_dump(mode="json"),
            confidence=proposal.confidence,
            autonomy_level=2,
            related_entity_type="recurring_journal_template",
            related_entity_id=proposal.template_id,
        )
        created.append(suggestion)
    return {
        "period": period,
        "proposal_count": len(proposals),
        "created_count": len(created),
        "skipped_duplicates": skipped_duplicates,
        "suggestion_ids": [str(row["id"]) for row in created],
        "proposals": [proposal.model_dump(mode="json") for proposal in proposals],
    }


def _period_bounds(period: str) -> tuple[date, date]:
    if not _PERIOD_PATTERN.match(period):
        raise RecurringJournalProposalError("Invalid period format; expected YYYY-MM")
    year = int(period[:4])
    month = int(period[5:])
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def _recurring_templates(deps: AgentDeps) -> list[dict]:
    rows = (
        deps.db.table("recurring_journal_templates")
        .select("*")
        .eq("tenant_id", deps.tenant_id)
        .eq("is_active", True)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return rows


def _recurring_template_lines(
    deps: AgentDeps,
    template_ids: list[str],
) -> dict[str, list[dict]]:
    if not template_ids:
        return {}
    rows = (
        deps.db.table("recurring_journal_template_lines")
        .select("*")
        .eq("tenant_id", deps.tenant_id)
        .in_("template_id", template_ids)
        .execute()
        .data
        or []
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["template_id"])].append(row)
    return {
        template_id: sorted(lines, key=lambda row: int(row.get("order_index") or 0))
        for template_id, lines in grouped.items()
    }


def _template_is_active_for_period(template: dict, period: str) -> bool:
    start_period = str(template.get("start_period") or "")
    end_period = template.get("end_period")
    if start_period > period:
        return False
    return not (end_period and str(end_period) < period)


def _journal_lines(lines: list[dict], currency: str) -> list[dict]:
    journal_lines: list[dict] = []
    for line in lines:
        amount = _decimal_or_zero(line.get("amount"))
        if amount <= Decimal("0.00"):
            continue
        journal_lines.append(
            {
                "direction": str(line.get("direction") or ""),
                "account_id": str(line.get("account_id") or ""),
                "amount": serialise_money(amount) or "0.00",
                "currency": currency,
                "description": line.get("description"),
            }
        )
    return journal_lines


def _lines_balance(lines: list[dict]) -> bool:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for line in lines:
        direction = str(line.get("direction") or "")
        if direction not in {"DR", "CR"}:
            return False
        if not line.get("account_id"):
            return False
        totals[direction] += _decimal_or_zero(line.get("amount"))
    return totals["DR"] == totals["CR"] and totals["DR"] > Decimal("0.00")


def _has_existing_recurring_journal_suggestion(
    deps: AgentDeps,
    proposal: RecurringJournalProposal,
) -> bool:
    for output in _active_recurring_suggestion_outputs(deps):
        if (
            output.get("proposal_type") == _PROPOSAL_TYPE
            and output.get("period") == proposal.period
            and output.get("template_id") == proposal.template_id
        ):
            return True
    return False


def _active_recurring_suggestion_outputs(deps: AgentDeps) -> list[dict]:
    rows = (
        deps.db.table("agent_suggestions")
        .select("id, output_snapshot")
        .eq("tenant_id", deps.tenant_id)
        .eq("agent_name", "recurring_journal_agent")
        .eq("action_type", "draft_journal")
        .in_("status", _ACTIVE_SUGGESTION_STATUSES)
        .execute()
        .data
        or []
    )
    outputs: list[dict] = []
    for row in rows:
        output = row.get("output_snapshot") or {}
        if isinstance(output, dict):
            outputs.append(output)
    return outputs


def _decimal_or_zero(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(TWO_PLACES)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")
