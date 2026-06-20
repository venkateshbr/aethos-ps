"""intelligence_worker — weekly Procrastinate task; surfaces anomaly alerts to Inbox.

Schedule: weekly, Monday 06:00 UTC (cron: ``0 6 * * 1``).

Per tenant, runs all 6 anomaly detection checks from intelligence_agent.
Each detected anomaly is persisted as:
  - An ``agent_suggestions`` row (agent_name='intelligence_agent',
    action_type=<anomaly_type>, status='pending', hitl_required=True)
  - A ``hitl_tasks`` row (kind='intelligence_alert', priority='med')

Graceful degradation: per-anomaly-check exceptions are caught and logged.
The worker continues processing remaining checks and tenants.

Start locally:
    cd backend
    set -a && source .env && set +a
    uv run python -m procrastinate --app=app.workers.procrastinate_app.app worker
"""

from __future__ import annotations

import logging

from app.agents.base import AgentDeps
from app.agents.intelligence_agent import (
    AGENT_NAME,
    IntelligenceAlert,
    check_expense_spike,
    check_fx_exposure,
    check_margin_compression,
    check_overdue_escalation,
    check_retainer_under_utilization,
    check_unbilled_engagement,
)
from app.agents.suggestion_writer import write_agent_suggestion
from app.core.config import settings
from app.workers.procrastinate_app import app
from supabase import create_client

logger = logging.getLogger(__name__)

# All 6 check functions in the order they are executed
_ANOMALY_CHECKS = [
    check_unbilled_engagement,
    check_margin_compression,
    check_expense_spike,
    check_fx_exposure,
    check_retainer_under_utilization,
    check_overdue_escalation,
]


@app.periodic(cron="0 6 * * 1")
@app.task(name="intelligence_worker", queue="cron")
async def intelligence_worker(timestamp: int) -> dict:
    """Weekly anomaly detection run across all active tenants.

    Returns
    -------
    ``{"tenants_processed": int, "alerts_written": int}``
    """
    _ = timestamp  # provided by Procrastinate periodic; unused
    db = create_client(settings.supabase_url, settings.supabase_service_role_key)

    tenants = (
        db.table("tenants").select("id").eq("status", "active").execute().data or []
    )

    total_alerts = 0
    for t in tenants:
        tid = t["id"]
        deps = AgentDeps(tenant_id=tid, user_id=None, db=db)
        try:
            alerts_written = await _run_anomaly_checks(deps)
            total_alerts += alerts_written
        except Exception:
            logger.error(
                "intelligence_worker: unhandled error for tenant %s",
                tid,
                exc_info=True,
            )

    logger.info(
        "intelligence_worker_done",
        extra={"tenants": len(tenants), "alerts_written": total_alerts},
    )
    return {"tenants_processed": len(tenants), "alerts_written": total_alerts}


async def _run_anomaly_checks(deps: AgentDeps) -> int:
    """Run all 6 anomaly checks for a single tenant; persist each alert.

    Per-check exceptions are caught and logged; the function continues
    with remaining checks.

    Returns the total number of alerts written to the DB.
    """
    written = 0

    for check_fn in _ANOMALY_CHECKS:
        try:
            alerts: list[IntelligenceAlert] = await check_fn(deps)
        except Exception:
            logger.error(
                "intelligence_worker: check %s failed for tenant %s",
                check_fn.__name__,
                deps.tenant_id,
                exc_info=True,
            )
            continue

        for alert in alerts:
            try:
                written += await _persist_alert(deps, alert)
            except Exception:
                logger.error(
                    "intelligence_worker: failed to persist alert %s for entity %s",
                    alert.anomaly_type,
                    alert.entity_id,
                    exc_info=True,
                )

    return written


async def _persist_alert(deps: AgentDeps, alert: IntelligenceAlert) -> int:
    """Persist a single IntelligenceAlert as agent_suggestion + hitl_task.

    Uses write_agent_suggestion from the suggestion_writer module.
    Returns 1 on success, 0 if writing fails.
    """
    output = {
        "anomaly_type": alert.anomaly_type,
        "entity_id": alert.entity_id,
        "entity_name": alert.entity_name,
        "metric_current": alert.metric_current,
        "metric_threshold": alert.metric_threshold,
        "narrative": alert.narrative,
        "payload": alert.payload,
    }

    try:
        suggestion = await write_agent_suggestion(
            deps=deps,
            agent_name=AGENT_NAME,
            action_type=alert.anomaly_type,
            document_id=None,
            output=output,
            confidence=alert.confidence,
            autonomy_level=2,  # Always L2 — intelligence alerts never auto-act
        )

        # Stamp the related_entity_id so dedup queries can filter by it.
        # write_agent_suggestion returns the inserted row; we update in-place
        # if the column exists (schema may not have it yet — graceful skip).
        if suggestion and suggestion.get("id"):
            try:
                deps.db.table("agent_suggestions").update(
                    {"related_entity_id": alert.entity_id}
                ).eq("id", suggestion["id"]).execute()
            except Exception:
                # Non-fatal: dedup will work on the next run if this fails
                logger.warning(
                    "intelligence_worker: could not stamp related_entity_id on suggestion %s",
                    suggestion.get("id"),
                )

        logger.info(
            "intelligence_worker: alert persisted",
            extra={
                "anomaly_type": alert.anomaly_type,
                "entity_id": alert.entity_id,
                "tenant_id": deps.tenant_id,
            },
        )
        return 1
    except Exception:
        logger.error(
            "intelligence_worker: write_agent_suggestion failed for %s/%s",
            alert.anomaly_type,
            alert.entity_id,
            exc_info=True,
        )
        return 0
