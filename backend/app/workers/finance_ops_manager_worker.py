"""Scheduled AI Finance Ops Manager worker.

The worker runs the same read-only command-center analysis used by Copilot,
creates a manager-reviewed action-plan Inbox task, and emits separate
non-destructive escalation notices for stale or high-risk Inbox work.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.agents.base import AgentDeps
from app.agents.copilot.graph import CopilotAgent, CopilotDeps
from app.agents.suggestion_writer import write_agent_suggestion
from app.core.db import get_service_role_client
from app.core.rbac import ROLE_HIERARCHY, UserRole
from app.services.approval_policy import ApprovalPolicyMatrix
from app.workers.procrastinate_app import app
from app.workers.workflow_runs import finish_workflow_run, start_workflow_run

logger = logging.getLogger(__name__)

WORKFLOW_NAME = "scheduled_finance_ops_manager"
ACTION_PLAN_KIND = "copilot_create_finance_ops_action_plan"
ESCALATION_KIND = "finance_ops_escalation"
DEFAULT_SCHEDULE: dict[str, Any] = {
    "is_enabled": True,
    "cadence": "daily",
    "run_hour_utc": 7,
    "run_weekday_utc": 0,
    "timezone": "UTC",
    "period_mode": "current_month",
    "lookback_limit": 10,
    "stale_after_hours": 24,
    "high_risk_stale_after_hours": 4,
    "escalation_enabled": True,
}


@app.periodic(cron="5 * * * *")
@app.task(name="finance_ops_manager_worker.run_scheduled_finance_ops_manager", queue="cron")
async def run_scheduled_finance_ops_manager(timestamp: int) -> dict[str, Any]:
    """Hourly sweep; tenant cadence settings decide whether work is due."""
    db = get_service_role_client()
    as_of = datetime.fromtimestamp(timestamp, UTC) if timestamp else datetime.now(UTC)
    return await _run_scheduled_finance_ops_manager(db, as_of=as_of)


async def _run_scheduled_finance_ops_manager(
    db: Any,
    *,
    as_of: datetime,
) -> dict[str, Any]:
    schedules = _eligible_schedules(db, as_of=as_of)
    totals: dict[str, Any] = {
        "tenants_due": len(schedules),
        "tenants_processed": 0,
        "plans_created": 0,
        "plans_skipped_duplicate": 0,
        "escalations_created": 0,
        "failed": 0,
    }
    for schedule in schedules:
        tenant_id = str(schedule["tenant_id"])
        workflow_id = start_workflow_run(
            db,
            tenant_id=tenant_id,
            workflow_name=WORKFLOW_NAME,
            owner_agent_name="finance_ops_manager",
            current_step="build_command_center_plan",
            goal_snapshot={
                "cadence": schedule["cadence"],
                "schedule_key": _schedule_key(tenant_id, schedule, as_of),
                "approval_boundary": "reviewed_action_plan_only",
            },
        )
        try:
            result = await _run_for_tenant(db, schedule=schedule, as_of=as_of)
            totals["tenants_processed"] += 1
            totals["plans_created"] += int(bool(result.get("plan_created")))
            totals["plans_skipped_duplicate"] += int(
                bool(result.get("plan_skipped_duplicate"))
            )
            totals["escalations_created"] += int(result.get("escalations_created") or 0)
            workflow_status = (
                "waiting_on_human"
                if result.get("plan_created") or result.get("escalations_created")
                else "succeeded"
            )
            finish_workflow_run(
                db,
                workflow_id,
                status=workflow_status,
                current_step=(
                    "hitl_review"
                    if workflow_status == "waiting_on_human"
                    else "completed"
                ),
                state_snapshot=result,
            )
        except Exception as exc:
            totals["failed"] += 1
            finish_workflow_run(
                db,
                workflow_id,
                status="failed",
                current_step="failed",
                state_snapshot={"result": "failed"},
                error_message=str(exc),
            )
            logger.warning(
                "finance_ops_manager_worker: tenant run failed",
                exc_info=True,
                extra={"tenant_id": tenant_id},
            )
    logger.info("finance_ops_manager_worker_done", extra=totals)
    return totals


async def _run_for_tenant(
    db: Any,
    *,
    schedule: dict[str, Any],
    as_of: datetime,
) -> dict[str, Any]:
    tenant_id = str(schedule["tenant_id"])
    schedule_key = _schedule_key(tenant_id, schedule, as_of)
    result: dict[str, Any] = {
        "result": "scheduled_finance_ops_review",
        "tenant_id": tenant_id,
        "schedule_key": schedule_key,
        "cadence": schedule["cadence"],
        "period": _period_for(as_of, str(schedule.get("period_mode") or "current_month")),
        "plan_created": False,
        "plan_skipped_duplicate": False,
        "escalations_created": 0,
    }

    if _open_scheduled_plan_exists(db, tenant_id=tenant_id, schedule_key=schedule_key):
        result["plan_skipped_duplicate"] = True
    else:
        suggestion = await _create_action_plan_review(
            db,
            tenant_id=tenant_id,
            schedule=schedule,
            as_of=as_of,
            schedule_key=schedule_key,
        )
        result["plan_created"] = True
        result["suggestion_id"] = str(suggestion.get("id") or "")

    if bool(schedule.get("escalation_enabled", True)):
        result["escalations_created"] = _create_escalation_tasks(
            db,
            tenant_id=tenant_id,
            schedule=schedule,
            as_of=as_of,
        )
    return result


async def _create_action_plan_review(
    db: Any,
    *,
    tenant_id: str,
    schedule: dict[str, Any],
    as_of: datetime,
    schedule_key: str,
) -> dict[str, Any]:
    period = _period_for(as_of, str(schedule.get("period_mode") or "current_month"))
    tool_input = {
        "period": period,
        "limit": int(schedule.get("lookback_limit") or 10),
    }
    plan_payload = await _build_finance_ops_action_plan(
        db,
        tenant_id=tenant_id,
        tool_input=tool_input,
    )
    plan_payload.update(
        {
            "tool_name": "create_finance_ops_action_plan",
            "tool_input": tool_input,
            "risk_class": "draft",
            "policy_reason": "scheduled_finance_ops_manager",
            "requested_by_user_id": None,
            "scheduled_run": True,
            "source_schedule_key": schedule_key,
            "source_schedule_cadence": schedule.get("cadence"),
            "source_workflow_name": WORKFLOW_NAME,
            "approval_boundary": (
                "Approval records manager review and fans out child Inbox work items; "
                "specialist execution remains separately approval-gated."
            ),
        }
    )
    return await write_agent_suggestion(
        deps=AgentDeps(tenant_id=tenant_id, user_id=None, db=db),
        agent_name="copilot_agent",
        action_type=ACTION_PLAN_KIND,
        document_id=None,
        output=plan_payload,
        confidence=0.0,
        autonomy_level=2,
        confidence_threshold=1.0,
    )


async def _build_finance_ops_action_plan(
    db: Any,
    *,
    tenant_id: str,
    tool_input: dict[str, Any],
) -> dict[str, Any]:
    agent = CopilotAgent(
        CopilotDeps(
            tenant_id=tenant_id,
            user_id="scheduled_finance_ops_manager",
            db_client=db,
        )
    )
    payload = await agent._build_finance_ops_action_plan_payload(tool_input)
    if payload.get("error"):
        raise RuntimeError(str(payload["error"]))
    return payload


def _create_escalation_tasks(
    db: Any,
    *,
    tenant_id: str,
    schedule: dict[str, Any],
    as_of: datetime,
) -> int:
    existing_source_ids = _open_escalation_source_ids(db, tenant_id=tenant_id)
    open_tasks = _open_hitl_tasks(db, tenant_id=tenant_id)
    created = 0
    for task in open_tasks:
        source_task_id = str(task.get("id") or "")
        if not source_task_id or source_task_id in existing_source_ids:
            continue
        if str(task.get("kind") or "") in {ESCALATION_KIND, ACTION_PLAN_KIND}:
            continue

        escalation = _escalation_payload_for_task(task, schedule=schedule, as_of=as_of)
        if escalation is None:
            continue
        suggestion_result = (
            db.table("agent_suggestions")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "agent_name": "finance_ops_manager",
                    "action_type": ESCALATION_KIND,
                    "input_snapshot": {
                        "source_task_id": source_task_id,
                        "schedule_key": _schedule_key(tenant_id, schedule, as_of),
                    },
                    "output_snapshot": escalation,
                    "confidence": "0.00",
                    "status": "pending",
                    "hitl_required": True,
                    "related_entity_type": "hitl_task",
                    "related_entity_id": source_task_id,
                }
            )
            .execute()
        )
        suggestion_rows = getattr(suggestion_result, "data", None) or []
        suggestion_id = suggestion_rows[0].get("id") if suggestion_rows else None
        assigned_to = _find_reviewer_for_role(
            db,
            tenant_id=tenant_id,
            required_role=UserRole(escalation["required_approval_role"]),
        )
        db.table("hitl_tasks").insert(
            {
                "tenant_id": tenant_id,
                "agent_suggestion_id": suggestion_id,
                "kind": ESCALATION_KIND,
                "priority": "critical" if escalation["high_risk"] else "high",
                "assigned_to": assigned_to,
                "title": f"Escalate stale AI review: {escalation['source_task_title'][:80]}",
                "description": (
                    "Scheduled Finance Ops Manager found a stale or high-risk "
                    "Inbox task. Review the source task before taking action."
                ),
                "payload": escalation,
                "status": "open",
            }
        ).execute()
        created += 1
    return created


def _eligible_schedules(db: Any, *, as_of: datetime) -> list[dict[str, Any]]:
    tenants = (
        db.table("tenants")
        .select("id")
        .in_("status", ["active", "trialing"])
        .execute()
        .data
        or []
    )
    configured = _configured_schedules(db)
    schedules: list[dict[str, Any]] = []
    for tenant in tenants:
        tenant_id = str(tenant["id"])
        schedule = {
            **DEFAULT_SCHEDULE,
            **configured.get(tenant_id, {}),
            "tenant_id": tenant_id,
        }
        if schedule.get("is_enabled") and _schedule_is_due(schedule, as_of=as_of):
            schedules.append(schedule)
    return schedules


def _configured_schedules(db: Any) -> dict[str, dict[str, Any]]:
    try:
        rows = (
            db.table("finance_ops_schedules")
            .select("*")
            .execute()
            .data
            or []
        )
    except Exception:
        return {}
    return {str(row["tenant_id"]): dict(row) for row in rows if row.get("tenant_id")}


def _schedule_is_due(schedule: dict[str, Any], *, as_of: datetime) -> bool:
    if int(schedule.get("run_hour_utc") or 0) != as_of.hour:
        return False
    cadence = str(schedule.get("cadence") or "daily")
    if cadence == "daily":
        return True
    if cadence == "weekly":
        return int(schedule.get("run_weekday_utc") or 0) == as_of.weekday()
    return False


def _open_scheduled_plan_exists(
    db: Any,
    *,
    tenant_id: str,
    schedule_key: str,
) -> bool:
    rows = (
        db.table("hitl_tasks")
        .select("id,payload,status,created_at")
        .eq("tenant_id", tenant_id)
        .eq("kind", ACTION_PLAN_KIND)
        .in_("status", ["open", "in_progress"])
        .execute()
        .data
        or []
    )
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if payload.get("source_schedule_key") == schedule_key:
            return True
    return False


def _open_escalation_source_ids(db: Any, *, tenant_id: str) -> set[str]:
    rows = (
        db.table("hitl_tasks")
        .select("id,payload,status")
        .eq("tenant_id", tenant_id)
        .eq("kind", ESCALATION_KIND)
        .in_("status", ["open", "in_progress"])
        .execute()
        .data
        or []
    )
    result: set[str] = set()
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        source_id = str(payload.get("source_task_id") or "")
        if source_id:
            result.add(source_id)
    return result


def _open_hitl_tasks(db: Any, *, tenant_id: str) -> list[dict[str, Any]]:
    return (
        db.table("hitl_tasks")
        .select("id,kind,priority,title,description,payload,status,due_at,created_at,updated_at")
        .eq("tenant_id", tenant_id)
        .in_("status", ["open", "in_progress"])
        .execute()
        .data
        or []
    )


def _escalation_payload_for_task(
    task: dict[str, Any],
    *,
    schedule: dict[str, Any],
    as_of: datetime,
) -> dict[str, Any] | None:
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    decision = ApprovalPolicyMatrix.decision_for_task(str(task.get("kind") or ""), payload)
    high_risk = (
        str(task.get("priority") or "") in {"high", "critical"}
        or decision.risk_class in {"write_money_in", "write_money_out", "accounting"}
        or ROLE_HIERARCHY.get(decision.required_role, 0)
        >= ROLE_HIERARCHY[UserRole.admin]
    )
    age_hours = _task_age_hours(task, as_of=as_of)
    due_at = _parse_datetime(task.get("due_at"))
    due_overdue = due_at is not None and due_at <= as_of
    threshold = int(
        schedule.get(
            "high_risk_stale_after_hours" if high_risk else "stale_after_hours",
        )
        or (4 if high_risk else 24)
    )
    if not due_overdue and age_hours < threshold:
        return None
    reason = "due_date_overdue" if due_overdue else "high_risk_stale" if high_risk else "stale"
    return {
        "finance_ops_escalation": True,
        "source_task_id": str(task.get("id") or ""),
        "source_task_kind": str(task.get("kind") or ""),
        "source_task_priority": str(task.get("priority") or ""),
        "source_task_title": str(task.get("title") or "Inbox task"),
        "source_task_created_at": str(task.get("created_at") or ""),
        "age_hours": round(age_hours, 2),
        "reason": reason,
        "high_risk": high_risk,
        "risk_class": decision.risk_class,
        "required_approval_role": decision.required_role.value,
        "approval_policy_reason": decision.reason,
        "review_path": "/app/inbox",
        "payload_summary": _task_payload_summary(payload),
        "approval_effect": (
            "Acknowledges the escalation notice only. The original Inbox task "
            "must still be reviewed through its own approval path."
        ),
    }


def _task_payload_summary(payload: dict[str, Any]) -> dict[str, str]:
    summary: dict[str, str] = {}
    for key in (
        "tool_name",
        "risk_class",
        "total_amount",
        "amount",
        "vendor_name",
        "client_name",
        "period",
    ):
        value = payload.get(key)
        if value is not None:
            summary[key] = str(value)[:120]
    return summary


def _find_reviewer_for_role(
    db: Any,
    *,
    tenant_id: str,
    required_role: UserRole,
) -> str | None:
    rows = (
        db.table("tenant_users")
        .select("user_id,role,deleted_at")
        .eq("tenant_id", tenant_id)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    candidates: list[tuple[int, str]] = []
    required_rank = ROLE_HIERARCHY[required_role]
    for row in rows:
        try:
            role = UserRole(row.get("role"))
        except (TypeError, ValueError):
            continue
        rank = ROLE_HIERARCHY.get(role, 0)
        user_id = str(row.get("user_id") or "")
        if user_id and rank >= required_rank:
            candidates.append((rank, user_id))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _task_age_hours(task: dict[str, Any], *, as_of: datetime) -> float:
    created_at = _parse_datetime(task.get("created_at"))
    if created_at is None:
        return 0.0
    return max((as_of - created_at).total_seconds() / 3600, 0.0)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _schedule_key(tenant_id: str, schedule: dict[str, Any], as_of: datetime) -> str:
    cadence = str(schedule.get("cadence") or "daily")
    if cadence == "weekly":
        _, week, _ = as_of.isocalendar()
        bucket = f"{as_of.year:04d}-W{week:02d}"
    else:
        bucket = as_of.date().isoformat()
    return f"{tenant_id}:{cadence}:{bucket}"


def _period_for(as_of: datetime, period_mode: str) -> str:
    if period_mode == "previous_month":
        previous = as_of.replace(day=1) - timedelta(days=1)
        return previous.strftime("%Y-%m")
    return as_of.strftime("%Y-%m")
