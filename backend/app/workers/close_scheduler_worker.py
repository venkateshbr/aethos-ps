"""Procrastinate task: scheduled month-end financial close preparation.

This worker prepares close evidence and HITL journal proposals for the most
recently completed accounting period. It deliberately stops before posting
journals or locking periods; those remain human-controlled accounting actions.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from typing import Any

from app.agents.accrual_agent import (
    write_employee_reimbursement_accrual_suggestions,
    write_wip_accrual_suggestions,
)
from app.agents.base import AgentDeps
from app.agents.prepaid_amortization_agent import write_prepaid_amortization_suggestions
from app.agents.recurring_journal_agent import write_recurring_journal_suggestions
from app.agents.revenue_recognition_agent import (
    write_deferred_revenue_release_suggestions,
    write_milestone_revenue_recognition_suggestions,
    write_percentage_completion_revenue_recognition_suggestions,
)
from app.core.db import get_service_role_client
from app.services.close_package_service import ClosePackageService
from app.services.close_status_service import CloseStatusService
from app.services.close_tasks_service import CloseTasksService
from app.workers.procrastinate_app import app

logger = logging.getLogger(__name__)

ProposalWriter = Callable[..., Awaitable[dict[str, Any]]]

_PROPOSAL_STEPS: tuple[tuple[str, ProposalWriter, dict[str, str]], ...] = (
    ("wip_accrual", write_wip_accrual_suggestions, {}),
    ("employee_reimbursement_accrual", write_employee_reimbursement_accrual_suggestions, {}),
    ("deferred_revenue_release", write_deferred_revenue_release_suggestions, {}),
    ("milestone_revenue_recognition", write_milestone_revenue_recognition_suggestions, {}),
    (
        "percentage_completion_revenue_recognition",
        write_percentage_completion_revenue_recognition_suggestions,
        {},
    ),
    ("prepaid_amortization", write_prepaid_amortization_suggestions, {}),
    ("recurring_journals", write_recurring_journal_suggestions, {}),
)


@app.periodic(cron="0 7 1 * *")
@app.task(name="close_scheduler_worker.run_monthly_financial_close", queue="cron")
async def run_monthly_financial_close(timestamp: int) -> dict[str, Any]:
    """Prepare month-end close for the most recently completed period."""
    db = get_service_role_client()
    as_of = datetime.fromtimestamp(timestamp, UTC).date() if timestamp else date.today()
    period = _previous_period_for(as_of)
    return await _run_monthly_financial_close(db, period)


async def _run_monthly_financial_close(db, period: str) -> dict[str, Any]:
    """Run scheduled close preparation across active tenants."""
    tenants = (
        db.table("tenants")
        .select("id")
        .in_("status", ["active", "trialing"])
        .execute()
        .data
        or []
    )
    totals = {
        "period": period,
        "tenants_processed": len(tenants),
        "waiting_on_human": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped_locked": 0,
        "suggestions_created": 0,
        "proposal_errors": 0,
    }
    for tenant in tenants:
        tenant_id = str(tenant["id"])
        try:
            result = await _run_close_for_tenant(db, tenant_id=tenant_id, period=period)
        except Exception:
            totals["failed"] += 1
            logger.exception(
                "close_scheduler_worker: failed for tenant %s period %s",
                tenant_id,
                period,
            )
            continue

        status = str(result.get("workflow_status") or "succeeded")
        if status == "waiting_on_human":
            totals["waiting_on_human"] += 1
        elif status == "failed":
            totals["failed"] += 1
        else:
            totals["succeeded"] += 1
        if result.get("result") == "skipped_locked":
            totals["skipped_locked"] += 1
        totals["suggestions_created"] += int(result.get("suggestions_created") or 0)
        totals["proposal_errors"] += len(result.get("proposal_errors") or {})

    logger.info("close_scheduler_worker_done", extra=totals)
    return totals


async def _run_close_for_tenant(db, *, tenant_id: str, period: str) -> dict[str, Any]:
    """Prepare one tenant's month-end close workflow."""
    workflow_id = _start_workflow_run(db, tenant_id=tenant_id, period=period)
    try:
        if _period_locked(db, tenant_id=tenant_id, period=period):
            result = {
                "result": "skipped_locked",
                "period": period,
                "workflow_status": "succeeded",
            }
            _finish_workflow_run(
                db,
                workflow_id,
                status="succeeded",
                current_step="complete",
                state_snapshot=result,
            )
            return result

        tasks = await CloseTasksService(db, tenant_id).bootstrap_tasks(
            period,
            "close_scheduler_worker",
        )
        proposal_results, proposal_errors = await _run_close_proposal_steps(
            db,
            tenant_id=tenant_id,
            period=period,
        )
        close_status = CloseStatusService(db, tenant_id).get_status(period)
        close_package = ClosePackageService(db, tenant_id).build_package(period)

        suggestions_created = sum(
            int(result.get("created_count") or 0) for result in proposal_results.values()
        )
        pending_review_count = len(close_status.pending_reviews)
        result = {
            "result": "close_prepared",
            "period": period,
            "workflow_status": "waiting_on_human",
            "task_count": len(tasks),
            "suggestions_created": suggestions_created,
            "proposal_results": proposal_results,
            "proposal_errors": proposal_errors,
            "close_status": close_status.as_dict(),
            "close_package_summary": {
                "period": close_package.get("period"),
                "net_income": close_package.get("net_income"),
                "total_ar": close_package.get("total_ar"),
                "total_ap": close_package.get("total_ap"),
                "pending_review_count": pending_review_count,
                "variance_comment_count": len(close_package.get("variance_commentary") or []),
            },
        }
        _finish_workflow_run(
            db,
            workflow_id,
            status="waiting_on_human",
            current_step="hitl_review" if pending_review_count else "close_task_review",
            state_snapshot=result,
        )
        return result
    except Exception as exc:
        _finish_workflow_run(
            db,
            workflow_id,
            status="failed",
            current_step="failed",
            state_snapshot={"result": "failed", "period": period},
            error_message=str(exc),
        )
        raise


async def _run_close_proposal_steps(
    db,
    *,
    tenant_id: str,
    period: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    deps = AgentDeps(tenant_id=tenant_id, user_id=None, db=db)
    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for step_name, writer, kwargs in _PROPOSAL_STEPS:
        try:
            results[step_name] = await writer(deps, period, **kwargs)
        except Exception as exc:
            errors[step_name] = str(exc)
            logger.warning(
                "close_scheduler_worker: proposal step failed",
                extra={"tenant_id": tenant_id, "period": period, "step": step_name},
                exc_info=True,
            )
    return results, errors


def _period_locked(db, *, tenant_id: str, period: str) -> bool:
    rows = (
        db.table("period_locks")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("period", period)
        .execute()
        .data
        or []
    )
    return bool(rows)


def _start_workflow_run(db, *, tenant_id: str, period: str) -> str | None:
    try:
        row = (
            db.table("agent_workflow_runs")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "workflow_name": "monthly_financial_close",
                    "status": "running",
                    "owner_agent_name": "close_agent",
                    "current_step": "bootstrap_close_tasks",
                    "goal_snapshot": {"period": period},
                    "state_snapshot": {},
                }
            )
            .execute()
            .data[0]
        )
        return str(row["id"])
    except Exception:
        logger.warning(
            "close_scheduler_worker: could not create workflow run",
            extra={"tenant_id": tenant_id, "period": period},
            exc_info=True,
        )
        return None


def _finish_workflow_run(
    db,
    workflow_id: str | None,
    *,
    status: str,
    current_step: str,
    state_snapshot: dict[str, Any],
    error_message: str | None = None,
) -> None:
    if not workflow_id:
        return
    patch: dict[str, Any] = {
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
            "close_scheduler_worker: could not update workflow run",
            extra={"workflow_id": workflow_id},
            exc_info=True,
        )


def _previous_period_for(as_of: date) -> str:
    if as_of.month == 1:
        return f"{as_of.year - 1:04d}-12"
    return f"{as_of.year:04d}-{as_of.month - 1:02d}"
