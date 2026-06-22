"""Procrastinate task: monthly billing run for retainer engagements.

Creates a draft billing_run containing all active retainer engagements for
a tenant, then the owner approves the run to materialise invoices.

Scheduled monthly on the 1st at 08:00 UTC. Can also be triggered manually:
    uv run python -m procrastinate --app=app.workers.procrastinate_app.app \
        defer app.workers.billing_run_worker.create_monthly_billing_run \
        --args '{"tenant_id": "<uuid>"}'
"""

from __future__ import annotations

import logging
from datetime import date

from app.core.db import get_service_role_client
from app.workers.procrastinate_app import app

logger = logging.getLogger(__name__)

_RETAINER_ARRANGEMENTS: frozenset[str] = frozenset({"retainer", "retainer_draw"})


@app.periodic(cron="0 8 1 * *")
@app.task(name="billing_run_worker.create_monthly_billing_run", queue="cron")
def create_monthly_billing_run(timestamp: int) -> dict:
    """Create a draft billing_run for all active retainer engagements.

    Runs monthly on the 1st. Finds all active engagements with retainer or
    retainer_draw billing and creates a single billing_run row with
    status='draft' and engagement_filter.engagement_ids populated.

    Returns:
        {"billing_run_id": str | None, "engagement_count": int, "skipped": bool}
    """
    _ = timestamp
    db = get_service_role_client()
    today = date.today()
    period_start = today.replace(day=1)

    # Find all active retainer engagements across this tenant's scope
    tenants_result = (
        db.table("tenants")
        .select("id")
        .in_("status", ["active", "trialing"])
        .execute()
    )
    tenant_rows = tenants_result.data or []

    created = 0
    for tenant_row in tenant_rows:
        tenant_id: str = tenant_row["id"]
        try:
            _create_run_for_tenant(db, tenant_id, period_start)
            created += 1
        except Exception:
            logger.error(
                "billing_run_worker: failed for tenant %s",
                tenant_id,
                exc_info=True,
            )

    return {"tenants_processed": len(tenant_rows), "runs_created": created}


def _create_run_for_tenant(db, tenant_id: str, period_start: date) -> dict | None:
    """Create a draft billing_run for a single tenant if retainer engagements exist."""
    import calendar

    # Last day of current month
    last_day = calendar.monthrange(period_start.year, period_start.month)[1]
    period_end = period_start.replace(day=last_day)

    # Find active retainer engagements
    eng_result = (
        db.table("engagements")
        .select("id, name, billing_arrangement")
        .eq("tenant_id", tenant_id)
        .eq("status", "active")
        .in_("billing_arrangement", list(_RETAINER_ARRANGEMENTS))
        .is_("deleted_at", "null")
        .execute()
    )
    engagements = eng_result.data or []

    if not engagements:
        logger.debug(
            "billing_run_worker: no active retainer engagements for tenant %s",
            tenant_id,
        )
        return None

    engagement_ids = [e["id"] for e in engagements]
    run_name = f"Retainer billing {period_start.strftime('%B %Y')}"

    row = (
        db.table("billing_runs")
        .insert(
            {
                "tenant_id": tenant_id,
                "name": run_name,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "status": "draft",
                "engagement_filter": {"engagement_ids": engagement_ids},
                "created_by_agent": "billing_run_agent",
                "summary": {
                    "retainer_engagement_count": len(engagement_ids),
                    "billing_arrangements": sorted(_RETAINER_ARRANGEMENTS),
                },
            }
        )
        .execute()
        .data[0]
    )
    _create_billing_run_review_task(
        db,
        tenant_id=tenant_id,
        billing_run=row,
        engagements=engagements,
        period_start=period_start,
        period_end=period_end,
    )

    logger.info(
        "billing_run_worker: created billing_run %s for tenant %s with %d engagements",
        row.get("id"),
        tenant_id,
        len(engagement_ids),
    )
    return row


def _create_billing_run_review_task(
    db,
    *,
    tenant_id: str,
    billing_run: dict,
    engagements: list[dict],
    period_start: date,
    period_end: date,
) -> None:
    """Create the HITL review task for a scheduled billing-run proposal."""
    engagement_ids = [engagement["id"] for engagement in engagements]
    output_snapshot = {
        "billing_run_id": billing_run["id"],
        "billing_run_name": billing_run.get("name"),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "engagement_ids": engagement_ids,
        "engagement_count": len(engagement_ids),
    }
    suggestion = (
        db.table("agent_suggestions")
        .insert(
            {
                "tenant_id": tenant_id,
                "agent_name": "billing_run_agent",
                "action_type": "approve_billing_run",
                "input_snapshot": {
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "billing_arrangements": sorted(_RETAINER_ARRANGEMENTS),
                },
                "output_snapshot": output_snapshot,
                "confidence": "0.95",
                "status": "pending",
                "hitl_required": True,
                "related_entity_type": "billing_run",
                "related_entity_id": billing_run["id"],
            }
        )
        .execute()
        .data[0]
    )
    db.table("hitl_tasks").insert(
        {
            "tenant_id": tenant_id,
            "agent_suggestion_id": suggestion["id"],
            "kind": "approve_billing_run",
            "priority": "med",
            "title": f"Review {billing_run.get('name', 'billing run')}",
            "description": (
                f"{len(engagement_ids)} retainer engagements are ready for billing."
            ),
            "payload": output_snapshot,
            "status": "open",
        }
    ).execute()
