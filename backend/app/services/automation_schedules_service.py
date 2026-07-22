"""Configurable automation schedules for the tenant-facing recurring workers.

Generalizes the finance-ops cadence pattern (``finance_ops_schedules`` +
``finance_ops_manager_worker``) so a tenant admin can enable/disable each
recurring job and choose when it runs. The periodic workers sweep tenants on an
hourly tick and call :func:`is_due` to decide what to run — moving the on/off and
timing decision from hardcoded ``@app.periodic`` crons into the DB.

Platform-global jobs (``fx_refresh``, ``autonomy_promoter``) are operator-
controlled and intentionally out of this tenant-scoped table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# job_key -> defaults, derived from the workers' original hardcoded crons.
JOB_DEFINITIONS: dict[str, dict[str, Any]] = {
    "collections": {
        "label": "Collections reminders",
        "description": "Daily dunning: drafts overdue-invoice reminders to Inbox.",
        "cadence": "daily", "run_hour_utc": 6, "run_weekday_utc": 0,
    },
    "billing_run": {
        "label": "Monthly billing run",
        "description": "Prepares the monthly pre-bill draft invoices.",
        "cadence": "monthly", "run_hour_utc": 8, "run_weekday_utc": 0,
    },
    "close_prep": {
        "label": "Month-end close preparation",
        "description": "Proposes deferred-revenue/accrual/prepaid/recurring close journals.",
        "cadence": "monthly", "run_hour_utc": 7, "run_weekday_utc": 0,
    },
    "project_health": {
        "label": "Project health checks",
        "description": "Scores project health (budget/margin/scope) and raises alerts.",
        "cadence": "daily", "run_hour_utc": 7, "run_weekday_utc": 0,
    },
    "time_reminder": {
        "label": "Timesheet reminders",
        "description": "Weekly nudge to employees with missing time entries.",
        "cadence": "weekly", "run_hour_utc": 16, "run_weekday_utc": 4,
    },
}

VALID_JOB_KEYS = frozenset(JOB_DEFINITIONS)
VALID_CADENCES = frozenset({"daily", "weekly", "monthly"})

_EDITABLE_FIELDS = ("is_enabled", "cadence", "run_hour_utc", "run_weekday_utc", "timezone")


def default_schedule(job_key: str) -> dict[str, Any]:
    """Effective defaults for a job when no row is configured."""
    defn = JOB_DEFINITIONS[job_key]
    return {
        "job_key": job_key,
        "is_enabled": True,
        "cadence": defn["cadence"],
        "run_hour_utc": defn["run_hour_utc"],
        "run_weekday_utc": defn["run_weekday_utc"],
        "timezone": "UTC",
    }


def schedule_is_due(schedule: dict[str, Any], *, as_of: datetime) -> bool:
    """True when a job should run for this UTC ``as_of`` tick."""
    if int(schedule.get("run_hour_utc") or 0) != as_of.hour:
        return False
    cadence = str(schedule.get("cadence") or "daily")
    if cadence == "daily":
        return True
    if cadence == "weekly":
        return int(schedule.get("run_weekday_utc") or 0) == as_of.weekday()
    if cadence == "monthly":
        return as_of.day == 1
    return False


def _configured_rows(db: Any, job_key: str) -> dict[str, dict[str, Any]]:
    """tenant_id -> configured row for a job (empty on any read failure)."""
    try:
        rows = (
            db.table("automation_schedules")
            .select("*")
            .eq("job_key", job_key)
            .execute()
            .data
            or []
        )
    except Exception:
        return {}
    return {str(r["tenant_id"]): dict(r) for r in rows if r.get("tenant_id")}


def eligible_tenants(db: Any, job_key: str, *, as_of: datetime) -> list[str]:
    """Tenant IDs for which ``job_key`` is enabled and due at ``as_of``.

    Mirrors ``finance_ops_manager_worker._eligible_schedules``: an unconfigured
    tenant falls back to the job's default schedule, so behaviour is unchanged
    until an admin edits it.
    """
    if job_key not in VALID_JOB_KEYS:
        return []
    tenants = (
        db.table("tenants").select("id").in_("status", ["active", "trialing"]).execute().data
        or []
    )
    configured = _configured_rows(db, job_key)
    due: list[str] = []
    for tenant in tenants:
        tenant_id = str(tenant["id"])
        schedule = {**default_schedule(job_key), **configured.get(tenant_id, {})}
        if schedule.get("is_enabled") and schedule_is_due(schedule, as_of=as_of):
            due.append(tenant_id)
    return due


def is_due(db: Any, job_key: str, tenant_id: str, *, as_of: datetime) -> bool:
    """Whether a single tenant's job is enabled and due at ``as_of``."""
    if job_key not in VALID_JOB_KEYS:
        return False
    row = _configured_rows(db, job_key).get(str(tenant_id))
    schedule = {**default_schedule(job_key), **(row or {})}
    return bool(schedule.get("is_enabled")) and schedule_is_due(schedule, as_of=as_of)


def list_for_tenant(db: Any, tenant_id: str) -> list[dict[str, Any]]:
    """All jobs with effective (configured-or-default) settings for the admin UI."""
    try:
        rows = (
            db.table("automation_schedules")
            .select("*")
            .eq("tenant_id", str(tenant_id))
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []
    by_job = {str(r["job_key"]): dict(r) for r in rows if r.get("job_key")}
    result: list[dict[str, Any]] = []
    for job_key, defn in JOB_DEFINITIONS.items():
        effective = {**default_schedule(job_key), **by_job.get(job_key, {})}
        result.append(
            {
                "job_key": job_key,
                "label": defn["label"],
                "description": defn["description"],
                "is_enabled": bool(effective["is_enabled"]),
                "cadence": effective["cadence"],
                "run_hour_utc": int(effective["run_hour_utc"]),
                "run_weekday_utc": int(effective["run_weekday_utc"]),
                "timezone": effective["timezone"],
                "configured": job_key in by_job,
            }
        )
    return result


def update_schedule(
    db: Any, tenant_id: str, job_key: str, patch: dict[str, Any]
) -> dict[str, Any]:
    """Upsert one tenant's schedule for a job. Validates job_key/cadence/hour."""
    if job_key not in VALID_JOB_KEYS:
        raise ValueError(f"Unknown job_key: {job_key}")
    payload: dict[str, Any] = {"tenant_id": str(tenant_id), "job_key": job_key}
    for field in _EDITABLE_FIELDS:
        if field in patch and patch[field] is not None:
            payload[field] = patch[field]
    if "cadence" in payload and payload["cadence"] not in VALID_CADENCES:
        raise ValueError(f"Invalid cadence: {payload['cadence']}")
    if "run_hour_utc" in payload and not (0 <= int(payload["run_hour_utc"]) <= 23):
        raise ValueError("run_hour_utc must be 0-23")
    if "run_weekday_utc" in payload and not (0 <= int(payload["run_weekday_utc"]) <= 6):
        raise ValueError("run_weekday_utc must be 0-6")
    (
        db.table("automation_schedules")
        .upsert(payload, on_conflict="tenant_id,job_key")
        .execute()
    )
    return next(
        (row for row in list_for_tenant(db, tenant_id) if row["job_key"] == job_key),
        default_schedule(job_key),
    )
