"""project_health_agent — proactive project risk alerts.

Runs daily at 07:00 UTC via project_health_worker.
Detects 5 alert types and creates HITL tasks in the Inbox.
Always L2 (suggest-only).

Alert types:
  BUDGET_BURN_WARNING     — project hours logged > 80% of budget_hours
  CAPPED_TM_APPROACHING   — T&M hours billed > 90% of cap_amount
  RETAINER_FLOOR_WARNING  — retainer project hours < floor hours for current period
  MILESTONE_OVERDUE       — milestone billing date passed without invoice (future)
  SCOPE_CREEP_RISK        — non-billable time entries > 20% of total in last 30 days
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from app.agents.base import AgentDeps

logger = logging.getLogger(__name__)

AlertType = Literal[
    "BUDGET_BURN_WARNING",
    "CAPPED_TM_APPROACHING",
    "RETAINER_FLOOR_WARNING",
    "MILESTONE_OVERDUE",
    "SCOPE_CREEP_RISK",
]


@dataclass
class ProjectHealthAlert:
    """A single project risk alert raised by a health check."""

    alert_type: str
    project_id: UUID
    project_name: str
    engagement_id: str | None
    tenant_id: str
    metric_current: str
    metric_threshold: str
    recommended_action: str
    confidence: float


def _fetch_time_entries(deps: AgentDeps, project_id: str) -> list[dict]:
    """Fetch all time entries for a project via the agent's DB client."""
    result = (
        deps.db.table("time_entries")
        .select("id, hours, billable, date")
        .eq("tenant_id", deps.tenant_id)
        .eq("project_id", project_id)
        .execute()
    )
    return result.data or []


async def check_project_health(
    project: dict,
    deps: AgentDeps,
) -> list[ProjectHealthAlert]:
    """Run all health checks for a single project. Returns list of triggered alerts.

    Parameters
    ----------
    project:
        A projects table row dict. Expected keys vary per check:
        - budget_hours (float | None)   — for BUDGET_BURN_WARNING
        - billing_arrangement (str)     — routing to the right check
        - cap_amount (float | None)     — for CAPPED_TM_APPROACHING
        - billed_amount (float | None)  — for CAPPED_TM_APPROACHING
        - retainer_floor_hours (float)  — for RETAINER_FLOOR_WARNING
        - hours_this_period (float)     — for RETAINER_FLOOR_WARNING
    deps:
        AgentDeps with tenant-scoped DB client. Time entries are fetched here.
    """
    alerts: list[ProjectHealthAlert] = []

    project_id_str: str = project["id"]
    project_id = UUID(project_id_str)
    project_name: str = project.get("name", "Unknown")
    engagement_id: str | None = project.get("engagement_id")
    billing_arrangement: str = project.get("billing_arrangement", "")

    # Fetch time entries (sync supabase-py — run in thread to avoid blocking)
    time_entries: list[dict] = await asyncio.to_thread(
        _fetch_time_entries, deps, project_id_str
    )

    # ------------------------------------------------------------------
    # Check 1: Budget burn warning — hours > 80% of budget_hours
    # ------------------------------------------------------------------
    budget_hours = project.get("budget_hours")
    if budget_hours and float(budget_hours) > 0:
        logged = sum(float(te.get("hours", 0)) for te in time_entries)
        burn_pct = logged / float(budget_hours)
        if burn_pct >= 0.80:
            pct_str = f"{burn_pct:.0%}"
            alerts.append(
                ProjectHealthAlert(
                    alert_type="BUDGET_BURN_WARNING",
                    project_id=project_id,
                    project_name=project_name,
                    engagement_id=engagement_id,
                    tenant_id=deps.tenant_id,
                    metric_current=f"{pct_str} of budget used ({logged:.1f}/{budget_hours} hrs)",
                    metric_threshold="80% threshold",
                    recommended_action=(
                        "Review remaining scope or request a budget increase from the client."
                    ),
                    confidence=0.95,
                )
            )

    # ------------------------------------------------------------------
    # Check 2: Capped T&M approaching — billed_amount > 90% of cap_amount
    # ------------------------------------------------------------------
    if billing_arrangement == "capped_tm":
        cap_amount = project.get("cap_amount")
        billed_amount = project.get("billed_amount")
        if cap_amount and float(cap_amount) > 0 and billed_amount is not None:
            cap_pct = float(billed_amount) / float(cap_amount)
            if cap_pct >= 0.90:
                pct_str = f"{cap_pct:.0%}"
                alerts.append(
                    ProjectHealthAlert(
                        alert_type="CAPPED_TM_APPROACHING",
                        project_id=project_id,
                        project_name=project_name,
                        engagement_id=engagement_id,
                        tenant_id=deps.tenant_id,
                        metric_current=(
                            f"{pct_str} of cap used "
                            f"({billed_amount}/{cap_amount})"
                        ),
                        metric_threshold="90% cap threshold",
                        recommended_action=(
                            "Notify the client that the billing cap is nearly reached. "
                            "Agree on a cap increase or scope reduction before work continues."
                        ),
                        confidence=0.95,
                    )
                )

    # ------------------------------------------------------------------
    # Check 3: Retainer floor warning — hours_this_period < retainer_floor_hours
    # ------------------------------------------------------------------
    if billing_arrangement == "retainer":
        floor_hours = project.get("retainer_floor_hours")
        hours_this_period = project.get("hours_this_period")
        if floor_hours is not None and hours_this_period is not None:
            if float(hours_this_period) < float(floor_hours):
                alerts.append(
                    ProjectHealthAlert(
                        alert_type="RETAINER_FLOOR_WARNING",
                        project_id=project_id,
                        project_name=project_name,
                        engagement_id=engagement_id,
                        tenant_id=deps.tenant_id,
                        metric_current=(
                            f"{hours_this_period} hrs logged this period"
                        ),
                        metric_threshold=f"floor: {floor_hours} hrs",
                        recommended_action=(
                            "Team is under-delivering against the retainer floor. "
                            "Schedule work or flag under-utilisation risk to the client."
                        ),
                        confidence=0.90,
                    )
                )

    # ------------------------------------------------------------------
    # Check 4: Scope creep risk — non-billable > 20% of recent entries
    # ------------------------------------------------------------------
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    recent = [te for te in time_entries if (te.get("date") or "") >= cutoff]
    if len(recent) >= 5:
        non_billable = sum(1 for te in recent if not te.get("billable", True))
        scope_pct = non_billable / len(recent)
        if scope_pct > 0.20:
            pct_str = f"{scope_pct:.0%}"
            alerts.append(
                ProjectHealthAlert(
                    alert_type="SCOPE_CREEP_RISK",
                    project_id=project_id,
                    project_name=project_name,
                    engagement_id=engagement_id,
                    tenant_id=deps.tenant_id,
                    metric_current=(
                        f"{pct_str} of recent entries non-billable "
                        f"({non_billable}/{len(recent)})"
                    ),
                    metric_threshold="20% threshold (last 30 days)",
                    recommended_action=(
                        "Discuss scope boundaries with the team. "
                        "Confirm if non-billable work should be re-scoped or absorbed."
                    ),
                    confidence=0.85,
                )
            )

    return alerts
