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

    proposal_type: str = "wip_accrual"
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


class EmployeeReimbursementAccrualProposal(BaseModel):
    """HITL-ready employee reimbursement expense accrual proposal."""

    proposal_type: str = "employee_reimbursement_accrual"
    period: str
    currency: str
    expense_ids: list[str]
    expense_count: int
    project_count: int
    reimbursement_accrual_amount: str
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


@dataclass
class _ExpenseBucket:
    amount: Decimal = Decimal("0.00")
    expense_ids: list[str] | None = None
    project_ids: set[str] | None = None

    def add(self, *, expense_id: str, project_id: str, amount: Decimal) -> None:
        if self.expense_ids is None:
            self.expense_ids = []
        if self.project_ids is None:
            self.project_ids = set()
        self.expense_ids.append(expense_id)
        if project_id:
            self.project_ids.add(project_id)
        self.amount += amount


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
        code for code in (debit_account_code, credit_account_code) if code not in account_ids
    ]
    if missing_accounts:
        raise AccrualProposalError(f"Missing accrual account codes: {', '.join(missing_accounts)}")

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


def build_employee_reimbursement_accrual_proposals(
    deps: AgentDeps,
    period: str,
    *,
    debit_account_code: str = "5100",
    credit_account_code: str = "2100",
) -> list[EmployeeReimbursementAccrualProposal]:
    """Build draft journals for unreimbursed employee-paid project expenses."""
    start, end = _period_bounds(period)
    account_ids = _get_account_ids_by_codes(
        deps,
        [debit_account_code, credit_account_code],
    )
    missing_accounts = [
        code for code in (debit_account_code, credit_account_code) if code not in account_ids
    ]
    if missing_accounts:
        raise AccrualProposalError(
            f"Missing employee reimbursement accrual account codes: {', '.join(missing_accounts)}"
        )

    already_accrued = _already_accrued_reimbursable_expense_ids(deps)
    rows = (
        deps.db.table("project_expenses")
        .select("id, project_id, amount, currency, expense_date, reimbursable, reimbursed_at")
        .eq("tenant_id", deps.tenant_id)
        .eq("reimbursable", True)
        .is_("reimbursed_at", "null")
        .is_("deleted_at", "null")
        .gte("expense_date", start.isoformat())
        .lte("expense_date", end.isoformat())
        .execute()
        .data
        or []
    )
    buckets: defaultdict[str, _ExpenseBucket] = defaultdict(_ExpenseBucket)
    for row in rows:
        expense_id = str(row.get("id") or "")
        if not expense_id or expense_id in already_accrued:
            continue
        amount = _decimal_or_zero(row.get("amount"))
        if amount <= Decimal("0.00"):
            continue
        currency = str(row.get("currency") or "USD")
        buckets[currency].add(
            expense_id=expense_id,
            project_id=str(row.get("project_id") or ""),
            amount=amount,
        )

    proposals: list[EmployeeReimbursementAccrualProposal] = []
    entry_date = end.isoformat()
    for currency, bucket in sorted(buckets.items()):
        amount = bucket.amount.quantize(Decimal("0.01"))
        if amount <= Decimal("0.00"):
            continue
        expense_ids = bucket.expense_ids or []
        project_ids = bucket.project_ids or set()
        amount_str = serialise_money(amount) or "0.00"
        description = f"Month-end employee reimbursement accrual for {period} ({currency})"
        proposals.append(
            EmployeeReimbursementAccrualProposal(
                period=period,
                currency=currency,
                expense_ids=expense_ids,
                expense_count=len(expense_ids),
                project_count=len(project_ids),
                reimbursement_accrual_amount=amount_str,
                debit_account_code=debit_account_code,
                credit_account_code=credit_account_code,
                confidence=0.84,
                journal_entry={
                    "description": description,
                    "entry_date": entry_date,
                    "reference": f"expense-accrual:{period}:{currency}",
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


async def write_employee_reimbursement_accrual_suggestions(
    deps: AgentDeps,
    period: str,
    *,
    debit_account_code: str = "5100",
    credit_account_code: str = "2100",
) -> dict:
    """Persist employee reimbursement accruals as L2 HITL journal suggestions."""
    proposals = build_employee_reimbursement_accrual_proposals(
        deps,
        period,
        debit_account_code=debit_account_code,
        credit_account_code=credit_account_code,
    )
    created: list[dict] = []
    skipped_duplicates = 0
    for proposal in proposals:
        if _has_existing_employee_reimbursement_accrual_suggestion(deps, proposal):
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
        if (
            output.get("proposal_type") in (None, "wip_accrual")
            and output.get("period") == proposal.period
            and output.get("currency") == proposal.currency
        ):
            return True
    return False


def _has_existing_employee_reimbursement_accrual_suggestion(
    deps: AgentDeps,
    proposal: EmployeeReimbursementAccrualProposal,
) -> bool:
    proposal_expense_ids = set(proposal.expense_ids)
    for output in _active_employee_reimbursement_accrual_outputs(deps):
        output_expense_ids = {str(expense_id) for expense_id in (output.get("expense_ids") or [])}
        if proposal_expense_ids & output_expense_ids:
            return True
    return False


def _already_accrued_reimbursable_expense_ids(deps: AgentDeps) -> set[str]:
    expense_ids: set[str] = set()
    for output in _active_employee_reimbursement_accrual_outputs(deps):
        expense_ids.update(str(expense_id) for expense_id in (output.get("expense_ids") or []))
    return expense_ids


def _active_employee_reimbursement_accrual_outputs(deps: AgentDeps) -> list[dict]:
    rows = (
        deps.db.table("agent_suggestions")
        .select("id, output_snapshot")
        .eq("tenant_id", deps.tenant_id)
        .eq("agent_name", "accrual_agent")
        .eq("action_type", "draft_journal")
        .in_("status", ["pending", "approved", "approved_with_edits", "auto_applied"])
        .execute()
        .data
        or []
    )
    outputs: list[dict] = []
    for row in rows:
        output = row.get("output_snapshot") or {}
        if (
            isinstance(output, dict)
            and output.get("proposal_type") == "employee_reimbursement_accrual"
        ):
            outputs.append(output)
    return outputs


def _decimal_or_zero(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except (ValueError, ArithmeticError):
        return Decimal("0.00")
