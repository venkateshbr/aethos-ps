"""Daily project health check worker.

Runs at 07:00 UTC. For each tenant, checks all active projects and
creates agent_suggestions + hitl_tasks for any triggered alerts via
suggestion_writer.

Deduplication: same (project_id, alert_type) not re-alerted within 7 days
when the previous suggestion is still pending or approved.

Graceful degradation: per-project exceptions are logged and skipped
so one bad project never stops the entire tenant sweep.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.agents.base import AgentDeps
from app.agents.project_health_agent import check_project_health
from app.agents.suggestion_writer import write_agent_suggestion
from app.core.db import get_service_role_client
from app.workers.procrastinate_app import app

logger = logging.getLogger(__name__)

DEDUP_DAYS = 7
ACTIVE_PROJECT_SELECT = (
    "id, name, engagement_id, budget_hours, budget, currency, status"
)


# ---------------------------------------------------------------------------
# Deduplication helper
# ---------------------------------------------------------------------------


def _is_duplicate_alert(
    db,
    tenant_id: str,
    project_id: str,
    alert_type: str,
) -> bool:
    """Return True if the same alert was raised within DEDUP_DAYS and is still
    pending or approved.

    Querying agent_suggestions by (tenant_id, agent_name, action_type,
    related_entity_id) within the 7-day window, filtered to pending/approved
    status. If any row exists, suppress the new alert.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=DEDUP_DAYS)).isoformat()
    rows = (
        db.table("agent_suggestions")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("agent_name", "project_health_agent")
        .eq("action_type", alert_type)
        .eq("related_entity_id", project_id)
        .gte("created_at", cutoff)
        .in_("status", ["pending", "approved"])
        .execute()
        .data
    )
    return bool(rows)


def _fetch_active_projects(db, tenant_id: str) -> list[dict]:
    """Fetch active projects using columns that exist on the projects table.

    Billing arrangement, cap, and retainer terms live on engagements and
    engagement_billing_terms.  The agent derives those in context per project.
    """
    return (
        db.table("projects")
        .select(ACTIVE_PROJECT_SELECT)
        .eq("tenant_id", tenant_id)
        .eq("status", "active")
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )


# ---------------------------------------------------------------------------
# Per-project processing
# ---------------------------------------------------------------------------


async def _process_project(project: dict, deps: AgentDeps) -> int:
    """Run health checks for a single project and write suggestions for any alerts.

    Returns the count of suggestions written. Exceptions are caught and logged
    so the caller's sweep continues uninterrupted.
    """
    written = 0
    try:
        alerts = await check_project_health(project, deps)
        for alert in alerts:
            project_id_str = str(alert.project_id)
            if _is_duplicate_alert(
                deps.db, deps.tenant_id, project_id_str, alert.alert_type
            ):
                logger.debug(
                    "project_health_worker: dedup suppressed %s for project %s",
                    alert.alert_type,
                    project_id_str,
                )
                continue

            try:
                await write_agent_suggestion(
                    deps,
                    "project_health_agent",
                    alert.alert_type,
                    None,  # no source document
                    {
                        "project_id": project_id_str,
                        "project_name": alert.project_name,
                        "metric_current": alert.metric_current,
                        "metric_threshold": alert.metric_threshold,
                        "recommended_action": alert.recommended_action,
                    },
                    alert.confidence,
                    autonomy_level=2,  # L2 always — suggest only, never auto-apply
                    related_entity_type="project",
                    related_entity_id=project_id_str,
                )
                written += 1
                logger.info(
                    "project_health_worker: alert written",
                    extra={
                        "alert_type": alert.alert_type,
                        "project_id": project_id_str,
                        "tenant_id": deps.tenant_id,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "project_health_worker: write_agent_suggestion failed for "
                    "project %s alert %s: %s",
                    project_id_str,
                    alert.alert_type,
                    exc,
                )
    except Exception as exc:
        logger.warning(
            "project_health_worker: project %s check failed: %s",
            project.get("id"),
            exc,
        )

    return written


# ---------------------------------------------------------------------------
# Periodic task
# ---------------------------------------------------------------------------


@app.periodic(cron="0 7 * * *")
@app.task(name="project_health_worker.run_project_health_checks", queue="cron")
def run_project_health_checks(timestamp: int) -> dict:
    """Daily project health worker — 07:00 UTC.

    Sweeps all active tenants, checks all active projects, and creates HITL
    tasks for any new risk alerts (deduped over 7 days).

    Returns a summary dict with counts for observability / alerting.
    """
    _ = timestamp
    db = get_service_role_client()

    # Fetch all active tenants
    tenants = (
        db.table("tenants")
        .select("id")
        .in_("status", ["active", "trialing"])
        .execute()
        .data
        or []
    )

    total_alerts = 0
    tenants_checked = 0

    for tenant_row in tenants:
        tenant_id: str = tenant_row["id"]
        try:
            deps = AgentDeps(tenant_id=tenant_id, user_id=None, db=db)

            projects = _fetch_active_projects(db, tenant_id)

            alerts_for_tenant = asyncio.run(
                _run_tenant_checks(projects, deps)
            )
            total_alerts += alerts_for_tenant
            tenants_checked += 1

        except Exception as exc:
            logger.warning(
                "project_health_worker: tenant %s sweep failed: %s",
                tenant_id,
                exc,
            )

    logger.info(
        "project_health_worker: daily sweep complete",
        extra={
            "tenants_checked": tenants_checked,
            "total_alerts_created": total_alerts,
        },
    )
    return {
        "total_alerts_created": total_alerts,
        "tenants_checked": tenants_checked,
    }


async def _run_tenant_checks(projects: list[dict], deps: AgentDeps) -> int:
    """Async helper that processes all projects for one tenant sequentially.

    We keep this sequential (not gathered) to avoid hammering the DB with
    concurrent reads when a tenant has many projects.
    """
    total = 0
    for project in projects:
        count = await _process_project(project, deps)
        total += count
    return total
