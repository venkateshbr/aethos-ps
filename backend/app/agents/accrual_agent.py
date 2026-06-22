"""Accrual agent helpers for month-end close proposals.

The agent only proposes draft journals. Posting still goes through the HITL
Inbox and ``ManualJournalService`` so accounting guardian and period-lock
checks remain authoritative.
"""

from __future__ import annotations

import calendar
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.agents.base import AgentDeps
from app.agents.suggestion_writer import write_agent_suggestion
from app.domain.money import serialise_money

_PERIOD_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")


class AccrualProposalError(ValueError):
    """Raised when an accrual proposal cannot be built safely."""


class WipAccrualProposal(BaseModel):
    """HITL-ready unbilled WIP accrual proposal."""

    period: str
    currency: str
    unbilled_hours: str
    wip_value: str
    project_count: int
    time_entry_count: int
    skipped_time_entry_count: int
    debit_account_code: str
    credit_account_code: str
    confidence: float
    journal_entry: dict


@dataclass
class _CurrencyBucket:
    amount: Decimal = Decimal("0")
    hours: Decimal = Decimal("0")
    time_entry_count: int = 0
    project_ids: set[str] | None = None

    def add(self, *, project_id: str, hours: Decimal, amount: Decimal) -> None:
        if self.project_ids is None:
            self.project_ids = set()
        self.project_ids.add(project_id)
        self.hours += hours
        self.amount += amount
        self.time_entry_count += 1


def build_wip_accrual_proposals(
    deps: AgentDeps,
    period: str,
    *,
    debit_account_code: str = "1200",
    credit_account_code: str = "4000",
) -> list[WipAccrualProposal]:
    """Build draft journal proposals for approved unbilled WIP in a period."""
    start, end = _period_bounds(period)
    account_ids = _get_account_ids_by_codes(
        deps,
        [debit_account_code, credit_account_code],
    )
    missing_accounts = [
        code
        for code in (debit_account_code, credit_account_code)
        if code not in account_ids
    ]
    if missing_accounts:
        raise AccrualProposalError(
            f"Missing accrual account codes: {', '.join(missing_accounts)}"
        )

    entries = (
        deps.db.table("time_entries")
        .select("id, project_id, employee_id, hours")
        .eq("tenant_id", deps.tenant_id)
        .eq("billing_status", "unbilled")
        .eq("billable", True)
        .eq("status", "approved")
        .gte("date", start.isoformat())
        .lte("date", end.isoformat())
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    if not entries:
        return []

    employee_ids = sorted({str(row["employee_id"]) for row in entries if row.get("employee_id")})
    employees = _get_employee_rates(deps, employee_ids)

    buckets: defaultdict[str, _CurrencyBucket] = defaultdict(_CurrencyBucket)
    skipped = 0
    for entry in entries:
        employee = employees.get(str(entry.get("employee_id")))
        if not employee:
            skipped += 1
            continue
        rate = Decimal(str(employee.get("default_bill_rate") or "0"))
        if rate <= 0:
            skipped += 1
            continue
        currency = str(employee.get("default_bill_rate_currency") or "USD")
        hours = Decimal(str(entry.get("hours") or "0"))
        amount = (hours * rate).quantize(Decimal("0.01"))
        if amount <= 0:
            skipped += 1
            continue
        buckets[currency].add(
            project_id=str(entry.get("project_id")),
            hours=hours,
            amount=amount,
        )

    proposals: list[WipAccrualProposal] = []
    entry_date = end.isoformat()
    for currency, bucket in sorted(buckets.items()):
        amount_str = serialise_money(bucket.amount)
        hours_str = str(bucket.hours.quantize(Decimal("0.01")))
        description = f"Month-end unbilled WIP accrual for {period} ({currency})"
        proposals.append(
            WipAccrualProposal(
                period=period,
                currency=currency,
                unbilled_hours=hours_str,
                wip_value=amount_str or "0.00",
                project_count=len(bucket.project_ids or set()),
                time_entry_count=bucket.time_entry_count,
                skipped_time_entry_count=skipped,
                debit_account_code=debit_account_code,
                credit_account_code=credit_account_code,
                confidence=0.78 if skipped == 0 else 0.68,
                journal_entry={
                    "description": description,
                    "entry_date": entry_date,
                    "reference": f"wip-accrual:{period}:{currency}",
                    "lines": [
                        {
                            "direction": "DR",
                            "account_id": account_ids[debit_account_code],
                            "amount": amount_str,
                            "currency": currency,
                            "description": description,
                        },
                        {
                            "direction": "CR",
                            "account_id": account_ids[credit_account_code],
                            "amount": amount_str,
                            "currency": currency,
                            "description": description,
                        },
                    ],
                },
            )
        )
    return proposals


async def write_wip_accrual_suggestions(
    deps: AgentDeps,
    period: str,
    *,
    debit_account_code: str = "1200",
    credit_account_code: str = "4000",
) -> dict:
    """Persist WIP accrual proposals as L2 HITL journal suggestions."""
    proposals = build_wip_accrual_proposals(
        deps,
        period,
        debit_account_code=debit_account_code,
        credit_account_code=credit_account_code,
    )
    created: list[dict] = []
    skipped_duplicates = 0
    for proposal in proposals:
        if _has_existing_wip_accrual_suggestion(deps, proposal):
            skipped_duplicates += 1
            continue
        suggestion = await write_agent_suggestion(
            deps,
            agent_name="accrual_agent",
            action_type="draft_journal",
            document_id=None,
            output=proposal.model_dump(mode="json"),
            confidence=proposal.confidence,
            autonomy_level=2,
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
        raise AccrualProposalError("Invalid period format; expected YYYY-MM")
    year = int(period[:4])
    month = int(period[5:])
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def _get_account_ids_by_codes(deps: AgentDeps, codes: list[str]) -> dict[str, str]:
    rows = (
        deps.db.table("accounts")
        .select("id, code")
        .eq("tenant_id", deps.tenant_id)
        .in_("code", codes)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return {str(row["code"]): str(row["id"]) for row in rows}


def _get_employee_rates(deps: AgentDeps, employee_ids: list[str]) -> dict[str, dict]:
    if not employee_ids:
        return {}
    rows = (
        deps.db.table("employees")
        .select("id, default_bill_rate, default_bill_rate_currency")
        .eq("tenant_id", deps.tenant_id)
        .in_("id", employee_ids)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return {str(row["id"]): row for row in rows}


def _has_existing_wip_accrual_suggestion(
    deps: AgentDeps,
    proposal: WipAccrualProposal,
) -> bool:
    rows = (
        deps.db.table("agent_suggestions")
        .select("id, output_snapshot")
        .eq("tenant_id", deps.tenant_id)
        .eq("agent_name", "accrual_agent")
        .eq("action_type", "draft_journal")
        .in_("status", ["pending", "approved", "auto_applied"])
        .execute()
        .data
        or []
    )
    for row in rows:
        output = row.get("output_snapshot") or {}
        if output.get("period") == proposal.period and output.get("currency") == proposal.currency:
            return True
    return False
