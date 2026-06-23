"""Revenue recognition agent helpers for deferred revenue release proposals.

The agent only drafts journals. Approval and posting still flow through the
HITL Inbox and ``ManualJournalService`` so period locks and accounting guardian
remain authoritative.
"""

from __future__ import annotations

import calendar
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.agents.base import AgentDeps
from app.agents.suggestion_writer import write_agent_suggestion
from app.domain.money import serialise_money

_PERIOD_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")


class RevenueRecognitionProposalError(ValueError):
    """Raised when a revenue-recognition proposal cannot be built safely."""


class DeferredRevenueReleaseProposal(BaseModel):
    """HITL-ready deferred revenue release proposal."""

    proposal_type: str = "deferred_revenue_release"
    period: str
    currency: str
    deferred_release_amount: str
    deferred_account_code: str
    revenue_account_code: str
    confidence: float
    journal_entry: dict


class MilestoneRevenueRecognitionProposal(BaseModel):
    """HITL-ready milestone recognition proposal tied to a project phase."""

    proposal_type: str = "milestone_revenue_recognition"
    period: str
    currency: str
    phase_id: str
    phase_name: str
    project_id: str
    project_name: str
    engagement_id: str
    engagement_name: str
    recognition_amount: str
    amount_source: str
    deferred_account_code: str
    revenue_account_code: str
    confidence: float
    journal_entry: dict


def build_deferred_revenue_release_proposals(
    deps: AgentDeps,
    period: str,
    *,
    deferred_account_code: str = "2200",
    revenue_account_code: str = "4000",
) -> list[DeferredRevenueReleaseProposal]:
    """Build draft journals for current-period deferred revenue credits.

    Without a durable release schedule, this intentionally proposes only the
    net current-period credits posted to the configured deferred-revenue
    account. Historical balances are left untouched until a schedule exists.
    """
    _start, end = _period_bounds(period)
    account_ids = _get_account_ids_by_codes(
        deps,
        [deferred_account_code, revenue_account_code],
    )
    deferred_account_id = account_ids.get(deferred_account_code)
    if not deferred_account_id:
        return []

    current_period_amounts = _current_period_deferred_credits(
        deps,
        period,
        deferred_account_id,
    )
    positive_amounts = {
        currency: amount
        for currency, amount in current_period_amounts.items()
        if amount > Decimal("0")
    }
    if not positive_amounts:
        return []

    revenue_account_id = account_ids.get(revenue_account_code)
    if not revenue_account_id:
        raise RevenueRecognitionProposalError(
            f"Missing revenue account code: {revenue_account_code}"
        )

    proposals: list[DeferredRevenueReleaseProposal] = []
    entry_date = end.isoformat()
    for currency, amount in sorted(positive_amounts.items()):
        amount_str = serialise_money(amount)
        description = f"Deferred revenue release for {period} ({currency})"
        proposals.append(
            DeferredRevenueReleaseProposal(
                period=period,
                currency=currency,
                deferred_release_amount=amount_str or "0.00",
                deferred_account_code=deferred_account_code,
                revenue_account_code=revenue_account_code,
                confidence=0.72,
                journal_entry={
                    "description": description,
                    "entry_date": entry_date,
                    "reference": f"deferred-revenue-release:{period}:{currency}",
                    "lines": [
                        {
                            "direction": "DR",
                            "account_id": deferred_account_id,
                            "amount": amount_str,
                            "currency": currency,
                            "description": description,
                        },
                        {
                            "direction": "CR",
                            "account_id": revenue_account_id,
                            "amount": amount_str,
                            "currency": currency,
                            "description": description,
                        },
                    ],
                },
            )
        )
    return proposals


def build_milestone_revenue_recognition_proposals(
    deps: AgentDeps,
    period: str,
    *,
    deferred_account_code: str = "2200",
    revenue_account_code: str = "4000",
) -> list[MilestoneRevenueRecognitionProposal]:
    """Build draft journals for completed milestone phases in a close period.

    The milestone amount comes from ``project_phases.revenue_recognition_amount``.
    Older data may not have that field populated, so phase ``budget`` is accepted
    as a compatibility fallback and flagged in ``amount_source``.
    """
    start, end = _period_bounds(period)
    account_ids = _get_account_ids_by_codes(
        deps,
        [deferred_account_code, revenue_account_code],
    )
    missing_accounts = [
        code
        for code in (deferred_account_code, revenue_account_code)
        if code not in account_ids
    ]
    if missing_accounts:
        raise RevenueRecognitionProposalError(
            f"Missing revenue recognition account codes: {', '.join(missing_accounts)}"
        )

    phases = _completed_milestone_phases_for_period(deps, start, end)
    if not phases:
        return []

    project_ids = sorted({str(row["project_id"]) for row in phases if row.get("project_id")})
    projects = _get_projects_by_ids(deps, project_ids)
    engagement_ids = sorted(
        {
            str(project["engagement_id"])
            for project in projects.values()
            if project.get("engagement_id")
        }
    )
    engagements = _get_engagements_by_ids(deps, engagement_ids)

    proposals: list[MilestoneRevenueRecognitionProposal] = []
    entry_date = end.isoformat()
    for phase in phases:
        project = projects.get(str(phase.get("project_id")))
        if not project:
            continue
        engagement = engagements.get(str(project.get("engagement_id")))
        if not engagement or engagement.get("billing_arrangement") != "milestone":
            continue

        amount_source, amount = _phase_recognition_amount(phase)
        if amount <= Decimal("0"):
            continue

        currency = str(engagement.get("currency") or project.get("currency") or "USD")
        amount_str = serialise_money(amount) or "0.00"
        phase_name = str(phase.get("name") or "Milestone")
        project_name = str(project.get("name") or "Project")
        engagement_name = str(engagement.get("name") or "Engagement")
        description = (
            f"Milestone revenue recognition for {phase_name} "
            f"({project_name}, {period}, {currency})"
        )

        proposals.append(
            MilestoneRevenueRecognitionProposal(
                period=period,
                currency=currency,
                phase_id=str(phase["id"]),
                phase_name=phase_name,
                project_id=str(project["id"]),
                project_name=project_name,
                engagement_id=str(engagement["id"]),
                engagement_name=engagement_name,
                recognition_amount=amount_str,
                amount_source=amount_source,
                deferred_account_code=deferred_account_code,
                revenue_account_code=revenue_account_code,
                confidence=(
                    0.86
                    if amount_source == "revenue_recognition_amount"
                    else 0.68
                ),
                journal_entry={
                    "description": description,
                    "entry_date": entry_date,
                    "reference": f"milestone-recognition:{period}:{phase['id']}",
                    "lines": [
                        {
                            "direction": "DR",
                            "account_id": account_ids[deferred_account_code],
                            "amount": amount_str,
                            "currency": currency,
                            "description": description,
                        },
                        {
                            "direction": "CR",
                            "account_id": account_ids[revenue_account_code],
                            "amount": amount_str,
                            "currency": currency,
                            "description": description,
                        },
                    ],
                },
            )
        )
    return proposals


async def write_deferred_revenue_release_suggestions(
    deps: AgentDeps,
    period: str,
    *,
    deferred_account_code: str = "2200",
    revenue_account_code: str = "4000",
) -> dict:
    """Persist deferred revenue release proposals as L2 HITL journal suggestions."""
    proposals = build_deferred_revenue_release_proposals(
        deps,
        period,
        deferred_account_code=deferred_account_code,
        revenue_account_code=revenue_account_code,
    )
    created: list[dict] = []
    skipped_duplicates = 0
    for proposal in proposals:
        if _has_existing_deferred_release_suggestion(deps, proposal):
            skipped_duplicates += 1
            continue
        suggestion = await write_agent_suggestion(
            deps,
            agent_name="revenue_recognition_agent",
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


async def write_milestone_revenue_recognition_suggestions(
    deps: AgentDeps,
    period: str,
    *,
    deferred_account_code: str = "2200",
    revenue_account_code: str = "4000",
) -> dict:
    """Persist milestone recognition proposals as L2 HITL journal suggestions."""
    proposals = build_milestone_revenue_recognition_proposals(
        deps,
        period,
        deferred_account_code=deferred_account_code,
        revenue_account_code=revenue_account_code,
    )
    created: list[dict] = []
    skipped_duplicates = 0
    for proposal in proposals:
        if _has_existing_milestone_recognition_suggestion(deps, proposal):
            skipped_duplicates += 1
            continue
        suggestion = await write_agent_suggestion(
            deps,
            agent_name="revenue_recognition_agent",
            action_type="draft_journal",
            document_id=None,
            output=proposal.model_dump(mode="json"),
            confidence=proposal.confidence,
            autonomy_level=2,
            related_entity_type="project_phase",
            related_entity_id=proposal.phase_id,
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
        raise RevenueRecognitionProposalError("Invalid period format; expected YYYY-MM")
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


def _completed_milestone_phases_for_period(
    deps: AgentDeps,
    start: date,
    end: date,
) -> list[dict]:
    rows = (
        deps.db.table("project_phases")
        .select(
            "id, project_id, name, status, end_date, budget, "
            "revenue_recognition_amount, percent_complete"
        )
        .eq("tenant_id", deps.tenant_id)
        .eq("status", "completed")
        .gte("end_date", start.isoformat())
        .lte("end_date", end.isoformat())
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return rows


def _get_projects_by_ids(deps: AgentDeps, project_ids: list[str]) -> dict[str, dict]:
    if not project_ids:
        return {}
    rows = (
        deps.db.table("projects")
        .select("id, engagement_id, name, currency")
        .eq("tenant_id", deps.tenant_id)
        .in_("id", project_ids)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return {str(row["id"]): row for row in rows}


def _get_engagements_by_ids(
    deps: AgentDeps,
    engagement_ids: list[str],
) -> dict[str, dict]:
    if not engagement_ids:
        return {}
    rows = (
        deps.db.table("engagements")
        .select("id, name, billing_arrangement, currency")
        .eq("tenant_id", deps.tenant_id)
        .in_("id", engagement_ids)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return {str(row["id"]): row for row in rows}


def _phase_recognition_amount(phase: dict) -> tuple[str, Decimal]:
    amount = phase.get("revenue_recognition_amount")
    if amount is not None:
        return "revenue_recognition_amount", Decimal(str(amount))
    return "phase_budget", Decimal(str(phase.get("budget") or "0"))


def _current_period_deferred_credits(
    deps: AgentDeps,
    period: str,
    deferred_account_id: str,
) -> dict[str, Decimal]:
    rows = (
        deps.db.table("journal_lines")
        .select("direction, amount, currency, journal_entries!journal_entry_id(period, posted_at)")
        .eq("tenant_id", deps.tenant_id)
        .eq("account_id", deferred_account_id)
        .execute()
        .data
        or []
    )
    by_currency: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        journal = row.get("journal_entries") or {}
        if journal.get("period") != period or not journal.get("posted_at"):
            continue
        currency = str(row.get("currency") or "USD")
        amount = Decimal(str(row.get("amount") or "0"))
        if row.get("direction") == "CR":
            by_currency[currency] += amount
        elif row.get("direction") == "DR":
            by_currency[currency] -= amount
    return dict(by_currency)


def _has_existing_deferred_release_suggestion(
    deps: AgentDeps,
    proposal: DeferredRevenueReleaseProposal,
) -> bool:
    rows = (
        deps.db.table("agent_suggestions")
        .select("id, output_snapshot")
        .eq("tenant_id", deps.tenant_id)
        .eq("agent_name", "revenue_recognition_agent")
        .eq("action_type", "draft_journal")
        .in_("status", ["pending", "approved", "auto_applied"])
        .execute()
        .data
        or []
    )
    for row in rows:
        output = row.get("output_snapshot") or {}
        if not isinstance(output, dict):
            continue
        if (
            output.get("proposal_type") == "deferred_revenue_release"
            and output.get("period") == proposal.period
            and output.get("currency") == proposal.currency
        ):
            return True
    return False


def _has_existing_milestone_recognition_suggestion(
    deps: AgentDeps,
    proposal: MilestoneRevenueRecognitionProposal,
) -> bool:
    rows = (
        deps.db.table("agent_suggestions")
        .select("id, output_snapshot")
        .eq("tenant_id", deps.tenant_id)
        .eq("agent_name", "revenue_recognition_agent")
        .eq("action_type", "draft_journal")
        .in_("status", ["pending", "approved", "auto_applied"])
        .execute()
        .data
        or []
    )
    for row in rows:
        output = row.get("output_snapshot") or {}
        if not isinstance(output, dict):
            continue
        if (
            output.get("proposal_type") == "milestone_revenue_recognition"
            and output.get("period") == proposal.period
            and output.get("phase_id") == proposal.phase_id
        ):
            return True
    return False
