"""Time Entry Agent — drafts reminders for under-logged weekly timesheets."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field


class TimeEntryProjectContext(BaseModel):
    project_id: str
    project_code: str | None = None
    project_name: str
    role: str | None = None


class TimeEntryReminderDraft(BaseModel):
    employee_id: str
    employee_name: str
    employee_email: str
    week_start: str
    week_end: str
    expected_hours: Decimal
    logged_hours: Decimal
    missing_hours: Decimal
    active_project_count: int
    active_projects: list[TimeEntryProjectContext]
    subject: str
    body_html: str
    source_context: list[str]
    confidence: float = Field(default=0.88, ge=0.0, le=1.0)


def expected_weekly_hours(employee: dict) -> Decimal:
    """Expected weekly billable hours from availability and utilization target."""
    available = _to_decimal(employee.get("available_hours_per_week"), Decimal("40"))
    target_pct = _to_decimal(
        employee.get("target_billable_utilization_pct"),
        Decimal("100"),
    )
    expected = available * target_pct / Decimal("100")
    return _quantize_hours(expected)


def draft_time_entry_reminder(
    *,
    employee: dict,
    projects: list[dict],
    logged_hours: Decimal,
    week_start: date,
    week_end: date,
    tenant_name: str,
) -> TimeEntryReminderDraft | None:
    """Build a reminder draft when the employee is materially under expected hours."""
    expected = expected_weekly_hours(employee)
    missing = _quantize_hours(expected - logged_hours)
    if expected <= 0 or missing < Decimal("1.00") or not projects:
        return None

    employee_name = _employee_name(employee)
    project_context = [
        TimeEntryProjectContext(
            project_id=str(project["project_id"]),
            project_code=project.get("project_code"),
            project_name=str(project.get("project_name") or "Project"),
            role=project.get("role"),
        )
        for project in projects[:5]
    ]
    project_names = ", ".join(
        project.project_code or project.project_name for project in project_context[:3]
    )
    subject = f"Time entry reminder: {missing} hours missing for week of {week_start:%b %d}"
    body_html = (
        f"<p>Hi {employee_name},</p>"
        f"<p>Your timesheet for {week_start:%B %d} - {week_end:%B %d} shows "
        f"<strong>{logged_hours}</strong> hours against an expected "
        f"<strong>{expected}</strong> hours.</p>"
        f"<p>Please update your time for active project work"
        f"{' including ' + project_names if project_names else ''}.</p>"
        f"<p>Thanks, {tenant_name}</p>"
    )

    return TimeEntryReminderDraft(
        employee_id=str(employee["id"]),
        employee_name=employee_name,
        employee_email=str(employee.get("email") or ""),
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        expected_hours=expected,
        logged_hours=_quantize_hours(logged_hours),
        missing_hours=missing,
        active_project_count=len(projects),
        active_projects=project_context,
        subject=subject,
        body_html=body_html,
        source_context=["employees", "project_assignments", "projects", "time_entries"],
    )


def _employee_name(employee: dict) -> str:
    first = str(employee.get("first_name") or "").strip()
    last = str(employee.get("last_name") or "").strip()
    return " ".join(part for part in (first, last) if part) or str(
        employee.get("email") or "Team member"
    )


def _to_decimal(value: object, default: Decimal) -> Decimal:
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _quantize_hours(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
