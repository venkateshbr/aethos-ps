"""FX remeasurement agent — period-end revaluation of open foreign balances (#376).

At month-end close, open (unpaid) AR invoices and AP bills denominated in a
currency other than the tenant base are revalued at the period-end rate. The
delta between the remeasured base value and the booked base value is an
*unrealized* FX gain/loss posted to ``7910`` (kept separate from realized FX at
settlement, ``7900``). The agent only drafts journals; posting flows through the
HITL Inbox + ``ManualJournalService`` so the accounting guardian and period lock
stay authoritative.

Policy (approved 2026-07-23, documented in docs/PLAN.md D25 and
docs/adr/0003-fx-remeasurement.md):
  - **Scope v1:** AR (``1200``) + AP (``2000``) **fully-open** balances only.
    Items with any payment applied are skipped (partial-payment remainders and
    foreign cash/bank revaluation are deferred follow-ups).
  - **Unrealized account:** ``7910`` Unrealized FX Gain/Loss.
  - **Materiality:** skip ``|delta| < 1.00`` base.
  - **Reversal:** each entry reverses on the first day of the next period
    (standard remeasurement) so only *realized* gain/loss persists at settlement;
    the reversal date is carried on the proposal as ``reverses_on``.
"""

from __future__ import annotations

import calendar
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.agents.base import AgentDeps
from app.agents.suggestion_writer import write_agent_suggestion
from app.domain.fx import FxRateNotFoundError, get_fx_rate
from app.domain.money import serialise_money

_PERIOD_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
_MATERIALITY = Decimal("1.00")
# Statuses that represent a live, posted obligation (draft is not yet in the GL;
# void/cancelled/paid are not open).
_AR_OPEN_STATUSES = frozenset({"approved", "sent", "overdue"})
_AP_OPEN_STATUSES = frozenset({"approved", "overdue", "pending_payment"})


class FxRemeasurementProposalError(ValueError):
    """Raised when an FX remeasurement proposal cannot be built safely."""


class FxRemeasurementProposal(BaseModel):
    """HITL-ready unrealized-FX remeasurement proposal for one (balance, currency)."""

    proposal_type: str = "fx_remeasurement"
    period: str
    balance_type: str  # "AR" | "AP"
    currency: str
    base_currency: str
    control_account_code: str
    unrealized_account_code: str
    open_foreign_amount: str
    booked_base_amount: str
    period_end_rate: str
    remeasured_base_amount: str
    unrealized_gain_loss: str  # signed: positive = gain, negative = loss
    item_count: int
    reverses_on: str
    confidence: float
    journal_entry: dict


@dataclass
class _Bucket:
    foreign: Decimal = Decimal("0")
    base: Decimal = Decimal("0")
    count: int = 0
    ids: set[str] = field(default_factory=set)


def _period_bounds(period: str) -> tuple[date, date]:
    if not _PERIOD_PATTERN.match(period):
        raise FxRemeasurementProposalError("Invalid period format; expected YYYY-MM")
    year, month = int(period[:4]), int(period[5:])
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def _next_period_start(period_end: date) -> date:
    if period_end.month == 12:
        return date(period_end.year + 1, 1, 1)
    return date(period_end.year, period_end.month + 1, 1)


def _tenant_base_currency(deps: AgentDeps) -> str:
    rows = (
        deps.db.table("tenants").select("base_currency").eq("id", deps.tenant_id).execute().data
        or []
    )
    return str((rows[0].get("base_currency") if rows else None) or "USD").upper()


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


def _ids_with_payments(deps: AgentDeps, table: str, key: str, *, extra_neq: tuple[str, str] | None = None) -> set[str]:
    """IDs (invoice_id / bill_id) that already have a payment applied — skipped so
    we never remeasure a partially/fully-settled item's full face value."""
    query = deps.db.table(table).select(key).eq("tenant_id", deps.tenant_id)
    if extra_neq is not None:
        query = query.neq(*extra_neq)
    rows = query.execute().data or []
    return {str(r[key]) for r in rows if r.get(key)}


def _open_foreign_buckets(
    deps: AgentDeps,
    *,
    table: str,
    open_statuses: frozenset[str],
    end_date: date,
    base_currency: str,
    paid_ids: set[str],
) -> dict[str, _Bucket]:
    rows = (
        deps.db.table(table)
        .select("id, currency, total, base_total, status, issue_date")
        .eq("tenant_id", deps.tenant_id)
        .is_("paid_at", "null")
        .is_("deleted_at", "null")
        .lte("issue_date", end_date.isoformat())
        .execute()
        .data
        or []
    )
    buckets: dict[str, _Bucket] = defaultdict(_Bucket)
    for row in rows:
        if str(row["id"]) in paid_ids:
            continue  # has a payment → not a fully-open balance (v1 scope)
        if str(row.get("status") or "") not in open_statuses:
            continue
        currency = str(row.get("currency") or base_currency).upper()
        if currency == base_currency:
            continue
        foreign = Decimal(str(row.get("total") or "0"))
        base = Decimal(str(row.get("base_total") or "0"))
        if foreign <= 0:
            continue
        bucket = buckets[currency]
        bucket.foreign += foreign
        bucket.base += base
        bucket.count += 1
        bucket.ids.add(str(row["id"]))
    return buckets


def _remeasurement_lines(
    *,
    balance_type: str,
    control_account_id: str,
    unrealized_account_id: str,
    delta: Decimal,
    base_currency: str,
    description: str,
) -> list[dict]:
    """Balanced base-currency lines for an unrealized remeasurement.

    ``delta`` = remeasured_base - booked_base (signed). Double-entry differs by
    balance type because AR is an asset (debit-normal) and AP a liability
    (credit-normal):

      AR  delta>0 (asset worth more)  -> DR 1200 / CR 7910  (gain)
      AR  delta<0                     -> DR 7910 / CR 1200  (loss)
      AP  delta>0 (owe more in base)  -> DR 7910 / CR 2000  (loss)
      AP  delta<0                     -> DR 2000 / CR 7910  (gain)
    """
    amount = serialise_money(abs(delta)) or "0.00"

    def line(direction: str, account_id: str) -> dict:
        return {
            "direction": direction,
            "account_id": account_id,
            "amount": amount,
            "currency": base_currency,
            "base_amount": amount,
            "description": description,
        }

    control_is_debit = (balance_type == "AR" and delta > 0) or (
        balance_type == "AP" and delta < 0
    )
    if control_is_debit:
        return [line("DR", control_account_id), line("CR", unrealized_account_id)]
    return [line("DR", unrealized_account_id), line("CR", control_account_id)]


async def build_fx_remeasurement_proposals(
    deps: AgentDeps,
    period: str,
    *,
    ar_account_code: str = "1200",
    ap_account_code: str = "2000",
    unrealized_account_code: str = "7910",
    materiality: Decimal = _MATERIALITY,
) -> list[FxRemeasurementProposal]:
    """Build draft unrealized-FX remeasurement journals for open foreign AR/AP."""
    _start, end = _period_bounds(period)
    base_currency = _tenant_base_currency(deps)
    reverses_on = _next_period_start(end).isoformat()

    account_ids = _get_account_ids_by_codes(
        deps, [ar_account_code, ap_account_code, unrealized_account_code]
    )
    missing = [
        code
        for code in (ar_account_code, ap_account_code, unrealized_account_code)
        if code not in account_ids
    ]
    if missing:
        raise FxRemeasurementProposalError(
            f"Missing FX remeasurement account codes: {', '.join(missing)}"
        )

    ar_paid = _ids_with_payments(deps, "payments", "invoice_id")
    ap_paid = _ids_with_payments(
        deps, "bill_payment_items", "bill_id", extra_neq=("status", "cancelled")
    )

    specs = [
        ("AR", ar_account_code, _AR_OPEN_STATUSES, "invoices", ar_paid),
        ("AP", ap_account_code, _AP_OPEN_STATUSES, "bills", ap_paid),
    ]
    proposals: list[FxRemeasurementProposal] = []
    for balance_type, control_code, open_statuses, table, paid_ids in specs:
        buckets = _open_foreign_buckets(
            deps,
            table=table,
            open_statuses=open_statuses,
            end_date=end,
            base_currency=base_currency,
            paid_ids=paid_ids,
        )
        for currency, bucket in sorted(buckets.items()):
            try:
                rate = await get_fx_rate(currency, base_currency, end, deps.db)
            except FxRateNotFoundError:
                # No period-end rate → cannot remeasure this currency safely; skip.
                continue
            remeasured = (bucket.foreign * rate).quantize(Decimal("0.01"))
            delta = remeasured - bucket.base
            if abs(delta) < materiality:
                continue

            description = (
                f"Unrealized FX remeasurement — {balance_type} {currency} at "
                f"{period} close (reverse {reverses_on})"
            )
            lines = _remeasurement_lines(
                balance_type=balance_type,
                control_account_id=account_ids[control_code],
                unrealized_account_id=account_ids[unrealized_account_code],
                delta=delta,
                base_currency=base_currency,
                description=description,
            )
            proposals.append(
                FxRemeasurementProposal(
                    period=period,
                    balance_type=balance_type,
                    currency=currency,
                    base_currency=base_currency,
                    control_account_code=control_code,
                    unrealized_account_code=unrealized_account_code,
                    open_foreign_amount=serialise_money(bucket.foreign) or "0.00",
                    booked_base_amount=serialise_money(bucket.base) or "0.00",
                    period_end_rate=str(rate),
                    remeasured_base_amount=serialise_money(remeasured) or "0.00",
                    unrealized_gain_loss=serialise_money(delta) or "0.00",
                    item_count=bucket.count,
                    reverses_on=reverses_on,
                    confidence=0.80,
                    journal_entry={
                        "description": description,
                        "entry_date": end.isoformat(),
                        "reference": f"fx-remeasurement:{period}:{balance_type}:{currency}",
                        "reverses_on": reverses_on,
                        "lines": lines,
                    },
                )
            )
    return proposals


def _active_fx_remeasurement_outputs(deps: AgentDeps) -> list[dict]:
    rows = (
        deps.db.table("agent_suggestions")
        .select("id, output_snapshot")
        .eq("tenant_id", deps.tenant_id)
        .eq("agent_name", "fx_remeasurement_agent")
        .eq("action_type", "draft_journal")
        .in_("status", ["pending", "approved", "approved_with_edits", "auto_applied"])
        .execute()
        .data
        or []
    )
    return [r.get("output_snapshot") or {} for r in rows if isinstance(r.get("output_snapshot"), dict)]


def _has_existing_suggestion(deps: AgentDeps, proposal: FxRemeasurementProposal) -> bool:
    for output in _active_fx_remeasurement_outputs(deps):
        if (
            output.get("proposal_type") == "fx_remeasurement"
            and output.get("period") == proposal.period
            and output.get("balance_type") == proposal.balance_type
            and output.get("currency") == proposal.currency
        ):
            return True
    return False


async def write_fx_remeasurement_suggestions(
    deps: AgentDeps,
    period: str,
    *,
    ar_account_code: str = "1200",
    ap_account_code: str = "2000",
    unrealized_account_code: str = "7910",
) -> dict:
    """Persist unrealized-FX remeasurement proposals as L2 HITL journal suggestions."""
    proposals = await build_fx_remeasurement_proposals(
        deps,
        period,
        ar_account_code=ar_account_code,
        ap_account_code=ap_account_code,
        unrealized_account_code=unrealized_account_code,
    )
    created: list[dict] = []
    skipped_duplicates = 0
    for proposal in proposals:
        if _has_existing_suggestion(deps, proposal):
            skipped_duplicates += 1
            continue
        suggestion = await write_agent_suggestion(
            deps,
            agent_name="fx_remeasurement_agent",
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
        "proposals": [p.model_dump(mode="json") for p in proposals],
    }
