"""Weekly time-entry reminder worker."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.agents.base import AgentDeps
from app.agents.suggestion_writer import write_agent_suggestion
from app.agents.time_entry_agent import (
    TimeEntryReminderDraft,
    draft_time_entry_reminder,
)
from app.core.config import settings
from app.services.resend_service import ResendService
from app.workers.procrastinate_app import app
from supabase import create_client

logger = logging.getLogger(__name__)

_ACTION_TYPE = "send_time_entry_reminder"
_DECIDED_STATUSES = ("pending", "approved", "auto_applied")


@app.periodic(cron="0 16 * * 5")
@app.task(name="time_entry_reminder_worker", queue="cron")
async def time_entry_reminder_worker(timestamp: int) -> dict:
    """Draft/send weekly reminders for active assigned employees under expected hours."""
    _ = timestamp
    db = create_client(settings.supabase_url, settings.supabase_service_role_key)
    resend = ResendService()
    as_of = date.today()
    tenants = (
        db.table("tenants")
        .select("id, name")
        .in_("status", ["active", "trialing"])
        .execute()
        .data
        or []
    )

    totals = {
        "tenants_processed": len(tenants),
        "sent": 0,
        "hitl_queued": 0,
        "skipped_duplicates": 0,
        "skipped_not_needed": 0,
    }
    for tenant in tenants:
        result = await _process_tenant_week(
            db,
            resend=resend,
            tenant_id=str(tenant["id"]),
            tenant_name=str(tenant.get("name") or "Your firm"),
            as_of=as_of,
        )
        for key in ("sent", "hitl_queued", "skipped_duplicates", "skipped_not_needed"):
            totals[key] += int(result[key])

    logger.info("time_entry_reminder_done", extra=totals)
    return totals


async def _process_tenant_week(
    db,
    *,
    resend: ResendService,
    tenant_id: str,
    tenant_name: str,
    as_of: date,
) -> dict:
    week_start, week_end = _week_bounds(as_of)
    workflow_id = _start_workflow_run(
        db,
        tenant_id=tenant_id,
        week_start=week_start,
        week_end=week_end,
    )
    result = {
        "sent": 0,
        "hitl_queued": 0,
        "skipped_duplicates": 0,
        "skipped_not_needed": 0,
    }
    try:
        drafts = _build_weekly_reminder_drafts(
            db,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            week_start=week_start,
            week_end=week_end,
        )
        deps = AgentDeps(tenant_id=tenant_id, user_id=None, db=db)
        for draft in drafts:
            if _recent_time_entry_reminder_exists(
                db,
                tenant_id=tenant_id,
                employee_id=draft.employee_id,
                week_start=draft.week_start,
            ):
                result["skipped_duplicates"] += 1
                continue

            autonomy = _time_entry_autonomy_settings(db, tenant_id)
            level = int(autonomy.get("level", 2))
            threshold = float(autonomy.get("confidence_threshold", 0.85))
            if level >= 3 and draft.confidence >= threshold and draft.employee_email:
                suggestion = await write_agent_suggestion(
                    deps,
                    "time_entry_agent",
                    _ACTION_TYPE,
                    document_id=None,
                    output=draft.model_dump(mode="json"),
                    confidence=draft.confidence,
                    autonomy_level=3,
                    confidence_threshold=threshold,
                    related_entity_type="employee",
                    related_entity_id=draft.employee_id,
                )
                send_result = resend.send_email(
                    draft.employee_email,
                    draft.subject,
                    draft.body_html,
                )
                if send_result.get("status") == "error":
                    _mark_suggestion_rejected(db, tenant_id, str(suggestion["id"]))
                    raise RuntimeError(
                        f"time entry reminder provider failed: {send_result.get('error')}"
                    )
                result["sent"] += 1
            else:
                await write_agent_suggestion(
                    deps,
                    "time_entry_agent",
                    _ACTION_TYPE,
                    document_id=None,
                    output=draft.model_dump(mode="json"),
                    confidence=draft.confidence,
                    autonomy_level=2,
                    related_entity_type="employee",
                    related_entity_id=draft.employee_id,
                )
                result["hitl_queued"] += 1

        if not drafts:
            result["skipped_not_needed"] = 1

        _finish_workflow_run(
            db,
            workflow_id,
            status="waiting_on_human" if result["hitl_queued"] else "succeeded",
            current_step="hitl_review" if result["hitl_queued"] else "complete",
            state_snapshot={
                "result": "reminders_processed",
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                **result,
            },
        )
        return result
    except Exception as exc:
        _finish_workflow_run(
            db,
            workflow_id,
            status="failed",
            current_step="failed",
            state_snapshot={"result": "failed", "week_start": week_start.isoformat()},
            error_message=str(exc),
        )
        raise


def _build_weekly_reminder_drafts(
    db,
    *,
    tenant_id: str,
    tenant_name: str,
    week_start: date,
    week_end: date,
) -> list[TimeEntryReminderDraft]:
    employees = (
        db.table("employees")
        .select(
            "id, first_name, last_name, email, available_hours_per_week, "
            "target_billable_utilization_pct"
        )
        .eq("tenant_id", tenant_id)
        .eq("status", "active")
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    assignments = (
        db.table("project_assignments")
        .select("id, employee_id, project_id, role, start_date, end_date")
        .eq("tenant_id", tenant_id)
        .execute()
        .data
        or []
    )
    active_assignments = [
        row for row in assignments if _assignment_overlaps(row, week_start, week_end)
    ]
    project_ids = sorted({str(row["project_id"]) for row in active_assignments})
    projects = _projects_by_id(db, tenant_id, project_ids)
    active_project_ids = {
        project_id
        for project_id, project in projects.items()
        if project.get("status") in {"active", "planning"}
        and _project_overlaps(project, week_start, week_end)
    }

    assignments_by_employee: dict[str, list[dict]] = {}
    for assignment in active_assignments:
        project_id = str(assignment["project_id"])
        if project_id not in active_project_ids:
            continue
        employee_id = str(assignment["employee_id"])
        project = projects[project_id]
        assignments_by_employee.setdefault(employee_id, []).append(
            {
                "project_id": project_id,
                "project_code": project.get("code"),
                "project_name": project.get("name"),
                "role": assignment.get("role"),
            }
        )

    logged_by_employee = _logged_hours_by_employee(
        db,
        tenant_id=tenant_id,
        week_start=week_start,
        week_end=week_end,
    )

    drafts: list[TimeEntryReminderDraft] = []
    for employee in employees:
        employee_id = str(employee["id"])
        projects_for_employee = assignments_by_employee.get(employee_id, [])
        draft = draft_time_entry_reminder(
            employee=employee,
            projects=projects_for_employee,
            logged_hours=logged_by_employee.get(employee_id, Decimal("0")),
            week_start=week_start,
            week_end=week_end,
            tenant_name=tenant_name,
        )
        if draft is not None:
            drafts.append(draft)
    return drafts


def _projects_by_id(db, tenant_id: str, project_ids: list[str]) -> dict[str, dict]:
    if not project_ids:
        return {}
    rows = (
        db.table("projects")
        .select("id, code, name, status, start_date, end_date")
        .eq("tenant_id", tenant_id)
        .in_("id", project_ids)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    return {str(row["id"]): row for row in rows}


def _logged_hours_by_employee(
    db,
    *,
    tenant_id: str,
    week_start: date,
    week_end: date,
) -> dict[str, Decimal]:
    rows = (
        db.table("time_entries")
        .select("employee_id, hours, status")
        .eq("tenant_id", tenant_id)
        .gte("date", week_start.isoformat())
        .lte("date", week_end.isoformat())
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )
    totals: dict[str, Decimal] = {}
    for row in rows:
        if row.get("status") == "rejected":
            continue
        employee_id = str(row["employee_id"])
        totals[employee_id] = totals.get(employee_id, Decimal("0")) + Decimal(
            str(row.get("hours") or "0")
        )
    return totals


def _recent_time_entry_reminder_exists(
    db,
    *,
    tenant_id: str,
    employee_id: str,
    week_start: str,
) -> bool:
    rows = (
        db.table("agent_suggestions")
        .select("id, related_entity_id, output_snapshot")
        .eq("tenant_id", tenant_id)
        .eq("agent_name", "time_entry_agent")
        .eq("action_type", _ACTION_TYPE)
        .in_("status", list(_DECIDED_STATUSES))
        .execute()
        .data
        or []
    )
    for row in rows:
        output = row.get("output_snapshot") or {}
        if not isinstance(output, dict):
            continue
        same_employee = str(row.get("related_entity_id") or output.get("employee_id")) == str(
            employee_id
        )
        if same_employee and output.get("week_start") == week_start:
            return True
    return False


def _time_entry_autonomy_settings(db, tenant_id: str) -> dict:
    rows = (
        db.table("agent_autonomy_settings")
        .select("level, confidence_threshold")
        .eq("tenant_id", tenant_id)
        .eq("agent_name", "time_entry_agent")
        .eq("action_type", _ACTION_TYPE)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else {"level": 2, "confidence_threshold": 0.85}


def _week_bounds(as_of: date) -> tuple[date, date]:
    week_start = as_of - timedelta(days=as_of.weekday())
    return week_start, week_start + timedelta(days=6)


def _assignment_overlaps(row: dict, start: date, end: date) -> bool:
    row_start = _parse_date(row.get("start_date")) or start
    row_end = _parse_date(row.get("end_date")) or end
    return row_start <= end and row_end >= start


def _project_overlaps(row: dict, start: date, end: date) -> bool:
    row_start = _parse_date(row.get("start_date")) or start
    row_end = _parse_date(row.get("end_date")) or end
    return row_start <= end and row_end >= start


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if value:
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None
    return None


def _start_workflow_run(
    db,
    *,
    tenant_id: str,
    week_start: date,
    week_end: date,
) -> str | None:
    try:
        row = (
            db.table("agent_workflow_runs")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "workflow_name": "weekly_time_entry_reminders",
                    "status": "running",
                    "owner_agent_name": "time_entry_agent",
                    "current_step": "discover_underlogged_staff",
                    "goal_snapshot": {
                        "week_start": week_start.isoformat(),
                        "week_end": week_end.isoformat(),
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
            "time_entry_reminder_worker: could not create workflow run",
            extra={"tenant_id": tenant_id},
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
            "time_entry_reminder_worker: could not update workflow run",
            extra={"workflow_id": workflow_id},
            exc_info=True,
        )


def _mark_suggestion_rejected(db, tenant_id: str, suggestion_id: str) -> None:
    try:
        db.table("agent_suggestions").update({"status": "rejected"}).eq(
            "tenant_id", tenant_id
        ).eq("id", suggestion_id).execute()
    except Exception:
        logger.warning(
            "time_entry_reminder_worker: failed to reject failed auto-send suggestion",
            extra={"tenant_id": tenant_id, "suggestion_id": suggestion_id},
        )
