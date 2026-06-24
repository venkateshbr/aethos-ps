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
from datetime import UTC, date, datetime

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
    return _create_monthly_billing_runs(db, period_start)


def _create_monthly_billing_runs(db, period_start: date) -> dict:
    """Create monthly retainer billing runs across active tenants."""
    # Find all active retainer engagements across this tenant's scope
    tenants_result = (
        db.table("tenants")
        .select("id")
        .in_("status", ["active", "trialing"])
        .execute()
    )
    tenant_rows = tenants_result.data or []

    created = 0
    skipped = 0
    for tenant_row in tenant_rows:
        tenant_id: str = tenant_row["id"]
        try:
            row = _create_run_for_tenant(db, tenant_id, period_start)
            if row is None:
                skipped += 1
            else:
                created += 1
        except Exception:
            logger.error(
                "billing_run_worker: failed for tenant %s",
                tenant_id,
                exc_info=True,
            )

    return {
        "tenants_processed": len(tenant_rows),
        "runs_created": created,
        "runs_skipped": skipped,
    }


def _create_run_for_tenant(db, tenant_id: str, period_start: date) -> dict | None:
    """Create a draft billing_run for a single tenant if retainer engagements exist."""
    import calendar

    # Last day of current month
    last_day = calendar.monthrange(period_start.year, period_start.month)[1]
    period_end = period_start.replace(day=last_day)
    workflow_id = _start_workflow_run(
        db,
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
    )

    try:
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
            _finish_workflow_run(
                db,
                workflow_id,
                status="succeeded",
                current_step="complete",
                state_snapshot={
                    "result": "skipped_no_retainer_engagements",
                    "engagement_count": 0,
                },
            )
            return None

        existing = _find_existing_run_for_period(
            db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        if existing:
            logger.info(
                "billing_run_worker: duplicate suppressed for tenant %s period %s",
                tenant_id,
                period_start.strftime("%Y-%m"),
            )
            _finish_workflow_run(
                db,
                workflow_id,
                status="succeeded",
                current_step="complete",
                state_snapshot={
                    "result": "skipped_duplicate_period",
                    "existing_billing_run_id": existing.get("id"),
                    "existing_status": existing.get("status"),
                },
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
        _finish_workflow_run(
            db,
            workflow_id,
            status="waiting_on_human",
            current_step="hitl_review",
            state_snapshot={
                "result": "billing_run_created",
                "billing_run_id": row.get("id"),
                "engagement_count": len(engagement_ids),
                "engagement_ids": engagement_ids,
            },
        )

        logger.info(
            "billing_run_worker: created billing_run %s for tenant %s with %d engagements",
            row.get("id"),
            tenant_id,
            len(engagement_ids),
        )
        return row
    except Exception as exc:
        _finish_workflow_run(
            db,
            workflow_id,
            status="failed",
            current_step="failed",
            state_snapshot={"result": "failed"},
            error_message=str(exc),
        )
        raise


def _start_workflow_run(
    db,
    *,
    tenant_id: str,
    period_start: date,
    period_end: date,
) -> str | None:
    """Create a durable workflow container for monthly billing-run automation."""
    try:
        row = (
            db.table("agent_workflow_runs")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "workflow_name": "monthly_retainer_billing_run",
                    "status": "running",
                    "owner_agent_name": "billing_run_agent",
                    "current_step": "discover_retainer_engagements",
                    "goal_snapshot": {
                        "period_start": period_start.isoformat(),
                        "period_end": period_end.isoformat(),
                        "billing_arrangements": sorted(_RETAINER_ARRANGEMENTS),
                    },
                    "state_snapshot": {},
                }
            )
            .execute()
            .data[0]
        )
        return str(row["id"])
    except Exception:
        logger.warning(
            "billing_run_worker: could not create workflow run for tenant %s",
            tenant_id,
            exc_info=True,
        )
        return None


def _finish_workflow_run(
    db,
    workflow_id: str | None,
    *,
    status: str,
    current_step: str,
    state_snapshot: dict,
    error_message: str | None = None,
) -> None:
    """Update workflow status; failures here must not affect business work."""
    if not workflow_id:
        return
    patch: dict = {
        "status": status,
        "current_step": current_step,
        "state_snapshot": state_snapshot,
    }
    if status in {"succeeded", "failed", "cancelled"}:
        patch["completed_at"] = datetime.now(UTC).isoformat()
    if error_message:
        patch["error_message"] = error_message
    try:
        db.table("agent_workflow_runs").update(patch).eq("id", workflow_id).execute()
    except Exception:
        logger.warning(
            "billing_run_worker: could not update workflow run %s",
            workflow_id,
            exc_info=True,
        )


def _find_existing_run_for_period(
    db,
    *,
    tenant_id: str,
    period_start: date,
    period_end: date,
) -> dict | None:
    """Return an existing active agent-created run for the same tenant/month."""
    rows = (
        db.table("billing_runs")
        .select("id, status")
        .eq("tenant_id", tenant_id)
        .eq("period_start", period_start.isoformat())
        .eq("period_end", period_end.isoformat())
        .eq("created_by_agent", "billing_run_agent")
        .in_("status", ["draft", "reviewed", "approved", "invoiced"])
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


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
