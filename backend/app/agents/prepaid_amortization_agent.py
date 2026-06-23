"""Prepaid expense amortization agent helpers for month-end close.

The agent only drafts journals. Approval and posting still flow through the
HITL Inbox and ``ManualJournalService`` so period locks and accounting guardian
remain authoritative.
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
_ACTIVE_SUGGESTION_STATUSES = [
    "pending",
    "approved",
    "approved_with_edits",
    "auto_applied",
]
_PROPOSAL_TYPE = "prepaid_expense_amortization"
_FINAL_BILL_STATUSES = ["approved", "partially_paid", "paid"]


class PrepaidAmortizationProposalError(ValueError):
    """Raised when a prepaid amortization proposal cannot be built safely."""


class PrepaidAmortizationProposal(BaseModel):
    """HITL-ready prepaid expense amortization proposal."""

    proposal_type: str = _PROPOSAL_TYPE
    period: str
    currency: str
    bill_id: str
    bill_number: str
    bill_line_id: str
    line_description: str
    service_start_date: str
    service_end_date: str
    prepaid_amount: str
    prior_amortized_amount: str
    amortization_amount: str
    prepaid_account_code: str
    expense_account_code: str
    confidence: float
    journal_entry: dict


def build_prepaid_amortization_proposals(
    deps: AgentDeps,
    period: str,
    *,
    prepaid_account_code: str = "1500",
    expense_account_code: str = "5000",
) -> list[PrepaidAmortizationProposal]:
    """Build draft journals for current-period prepaid expense amortization."""
    start, end = _period_bounds(period)
    account_ids = _get_account_ids_by_codes(
        deps,
        [prepaid_account_code, expense_account_code],
    )
    missing_accounts = [
        code for code in (prepaid_account_code, expense_account_code) if code not in account_ids
    ]
    if missing_accounts:
        raise PrepaidAmortizationProposalError(
            f"Missing prepaid amortization account codes: {', '.join(missing_accounts)}"
        )

    lines = _prepaid_bill_lines(deps)
    if not lines:
        return []

    bill_ids = sorted({str(row["bill_id"]) for row in lines if row.get("bill_id")})
    bills = _get_bills_by_ids(deps, bill_ids)
    prior_amounts = _prior_amortized_amounts(
        deps,
        [str(row["id"]) for row in lines if row.get("id")],
        period,
    )

    proposals: list[PrepaidAmortizationProposal] = []
    entry_date = end.isoformat()
    for line in sorted(lines, key=lambda row: (str(row.get("bill_id")), str(row.get("id")))):
        bill = bills.get(str(line.get("bill_id")))
        if not bill or str(bill.get("status") or "") not in _FINAL_BILL_STATUSES:
            continue
        service_start = _parse_date(line.get("service_start_date"))
        service_end = _parse_date(line.get("service_end_date"))
        if not service_start or not service_end or service_end < service_start:
            continue
        if service_start > end or service_end < start:
            continue

        prepaid_amount = _decimal_or_zero(line.get("amount"))
        if prepaid_amount <= Decimal("0.00"):
            continue
        prior_amortized = prior_amounts.get(str(line["id"]), Decimal("0.00"))
        remaining = (prepaid_amount - prior_amortized).quantize(TWO_PLACES)
        if remaining <= Decimal("0.00"):
            continue

        period_amount = _amortization_amount_for_period(
            prepaid_amount,
            service_start,
            service_end,
            start,
            end,
        )
        if service_end <= end:
            period_amount = remaining
        amortization_amount = min(period_amount, remaining).quantize(TWO_PLACES)
        if amortization_amount <= Decimal("0.00"):
            continue

        currency = str(bill.get("currency") or "USD")
        amount_str = serialise_money(amortization_amount) or "0.00"
        bill_number = str(bill.get("bill_number") or "Bill")
        line_description = str(line.get("description") or "Prepaid expense")
        expense_account_id = str(line.get("account_id") or account_ids[expense_account_code])
        description = (
            f"Prepaid amortization for {line_description} ({bill_number}, {period}, {currency})"
        )

        proposals.append(
            PrepaidAmortizationProposal(
                period=period,
                currency=currency,
                bill_id=str(bill["id"]),
                bill_number=bill_number,
                bill_line_id=str(line["id"]),
                line_description=line_description,
                service_start_date=service_start.isoformat(),
                service_end_date=service_end.isoformat(),
                prepaid_amount=serialise_money(prepaid_amount) or "0.00",
                prior_amortized_amount=serialise_money(prior_amortized) or "0.00",
                amortization_amount=amount_str,
                prepaid_account_code=prepaid_account_code,
                expense_account_code=expense_account_code,
                confidence=0.82,
                journal_entry={
                    "description": description,
                    "entry_date": entry_date,
                    "reference": f"prepaid-amortization:{period}:{line['id']}",
                    "lines": [
                        {
                            "direction": "DR",
                            "account_id": expense_account_id,
                            "amount": amount_str,
                            "currency": currency,
                            "description": description,
                        },
                        {
                            "direction": "CR",
                            "account_id": account_ids[prepaid_account_code],
                            "amount": amount_str,
                            "currency": currency,
                            "description": description,
                        },
                    ],
                },
            )
        )
    return proposals


async def write_prepaid_amortization_suggestions(
    deps: AgentDeps,
    period: str,
    *,
    prepaid_account_code: str = "1500",
    expense_account_code: str = "5000",
) -> dict:
    """Persist prepaid amortization proposals as L2 HITL journal suggestions."""
    proposals = build_prepaid_amortization_proposals(
        deps,
        period,
        prepaid_account_code=prepaid_account_code,
        expense_account_code=expense_account_code,
    )
    created: list[dict] = []
    skipped_duplicates = 0
    for proposal in proposals:
        if _has_existing_prepaid_amortization_suggestion(deps, proposal):
            skipped_duplicates += 1
            continue
        suggestion = await write_agent_suggestion(
            deps,
            agent_name="prepaid_amortization_agent",
            action_type="draft_journal",
            document_id=None,
            output=proposal.model_dump(mode="json"),
            confidence=proposal.confidence,
            autonomy_level=2,
            related_entity_type="bill_line",
            related_entity_id=proposal.bill_line_id,
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
        raise PrepaidAmortizationProposalError("Invalid period format; expected YYYY-MM")
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


def _prepaid_bill_lines(deps: AgentDeps) -> list[dict]:
    rows = (
        deps.db.table("bill_lines")
        .select(
            "id, bill_id, description, amount, account_id, is_prepaid, "
            "service_start_date, service_end_date"
        )
        .eq("tenant_id", deps.tenant_id)
        .eq("is_prepaid", True)
        .execute()
        .data
        or []
    )
    return rows


def _get_bills_by_ids(deps: AgentDeps, bill_ids: list[str]) -> dict[str, dict]:
    if not bill_ids:
        return {}
    rows = (
        deps.db.table("bills")
        .select("id, bill_number, status, currency")
        .eq("tenant_id", deps.tenant_id)
        .in_("id", bill_ids)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return {str(row["id"]): row for row in rows}


def _amortization_amount_for_period(
    prepaid_amount: Decimal,
    service_start: date,
    service_end: date,
    period_start: date,
    period_end: date,
) -> Decimal:
    active_start = max(service_start, period_start)
    active_end = min(service_end, period_end)
    if active_start > active_end:
        return Decimal("0.00")
    total_days = Decimal(str((service_end - service_start).days + 1))
    period_days = Decimal(str((active_end - active_start).days + 1))
    return (prepaid_amount * period_days / total_days).quantize(TWO_PLACES)


def _prior_amortized_amounts(
    deps: AgentDeps,
    bill_line_ids: list[str],
    current_period: str,
) -> dict[str, Decimal]:
    bill_line_id_set = set(bill_line_ids)
    prior_amounts: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for output in _active_prepaid_suggestion_outputs(deps):
        if output.get("proposal_type") != _PROPOSAL_TYPE:
            continue
        bill_line_id = str(output.get("bill_line_id") or "")
        if bill_line_id not in bill_line_id_set:
            continue
        output_period = output.get("period")
        if not isinstance(output_period, str) or output_period >= current_period:
            continue
        prior_amounts[bill_line_id] += _decimal_or_zero(output.get("amortization_amount"))
    return dict(prior_amounts)


def _has_existing_prepaid_amortization_suggestion(
    deps: AgentDeps,
    proposal: PrepaidAmortizationProposal,
) -> bool:
    for output in _active_prepaid_suggestion_outputs(deps):
        if (
            output.get("proposal_type") == _PROPOSAL_TYPE
            and output.get("period") == proposal.period
            and output.get("bill_line_id") == proposal.bill_line_id
        ):
            return True
    return False


def _active_prepaid_suggestion_outputs(deps: AgentDeps) -> list[dict]:
    rows = (
        deps.db.table("agent_suggestions")
        .select("id, output_snapshot")
        .eq("tenant_id", deps.tenant_id)
        .eq("agent_name", "prepaid_amortization_agent")
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


def _parse_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _decimal_or_zero(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(TWO_PLACES)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")
