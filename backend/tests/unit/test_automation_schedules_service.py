"""Unit tests for automation_schedules_service (configurable job scheduling)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from app.services import automation_schedules_service as svc

pytestmark = pytest.mark.unit


class _Query:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows
        self._filters: list[tuple[str, Any]] = []

    def select(self, *_a, **_k) -> _Query:
        return self

    def eq(self, column: str, value: Any) -> _Query:
        self._filters.append((column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> _Query:
        self._filters.append((column, tuple(values)))
        return self

    def execute(self) -> Any:
        rows = self._rows
        for col, val in self._filters:
            if isinstance(val, tuple):
                rows = [r for r in rows if r.get(col) in val]
            else:
                rows = [r for r in rows if str(r.get(col)) == str(val)]
        return type("Result", (), {"data": list(rows)})()


class _FakeDb:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]):
        self._tables = tables
        self.upserts: list[dict[str, Any]] = []

    def table(self, name: str) -> Any:
        db = self

        class _Table(_Query):
            def upsert(self, payload: dict[str, Any], on_conflict: str = "") -> _Table:
                db.upserts.append(payload)
                # reflect the upsert into the backing table for read-back
                rows = db._tables.setdefault(name, [])
                key = (payload.get("tenant_id"), payload.get("job_key"))
                for r in rows:
                    if (r.get("tenant_id"), r.get("job_key")) == key:
                        r.update(payload)
                        break
                else:
                    rows.append(dict(payload))
                return self

        return _Table(db._tables.get(name, []))


def test_schedule_is_due_daily_weekly_monthly() -> None:
    daily = {"cadence": "daily", "run_hour_utc": 6}
    assert svc.schedule_is_due(daily, as_of=datetime(2026, 7, 21, 6))
    assert not svc.schedule_is_due(daily, as_of=datetime(2026, 7, 21, 7))

    weekly = {"cadence": "weekly", "run_hour_utc": 16, "run_weekday_utc": 4}  # Friday
    assert svc.schedule_is_due(weekly, as_of=datetime(2026, 7, 24, 16))  # 2026-07-24 = Friday
    assert not svc.schedule_is_due(weekly, as_of=datetime(2026, 7, 23, 16))  # Thursday

    monthly = {"cadence": "monthly", "run_hour_utc": 8}
    assert svc.schedule_is_due(monthly, as_of=datetime(2026, 8, 1, 8))
    assert not svc.schedule_is_due(monthly, as_of=datetime(2026, 8, 2, 8))


def test_eligible_tenants_uses_defaults_when_unconfigured() -> None:
    db = _FakeDb(
        {
            "tenants": [
                {"id": "t1", "status": "active"},
                {"id": "t2", "status": "trialing"},
                {"id": "t3", "status": "provisioning"},  # excluded
            ],
            "automation_schedules": [],
        }
    )
    # collections default: daily @ 06:00 UTC
    due = svc.eligible_tenants(db, "collections", as_of=datetime(2026, 7, 21, 6))
    assert set(due) == {"t1", "t2"}
    assert svc.eligible_tenants(db, "collections", as_of=datetime(2026, 7, 21, 9)) == []


def test_eligible_tenants_honours_disable_and_custom_hour() -> None:
    db = _FakeDb(
        {
            "tenants": [{"id": "t1", "status": "active"}, {"id": "t2", "status": "active"}],
            "automation_schedules": [
                {"tenant_id": "t1", "job_key": "collections", "is_enabled": False,
                 "cadence": "daily", "run_hour_utc": 6, "run_weekday_utc": 0},
                {"tenant_id": "t2", "job_key": "collections", "is_enabled": True,
                 "cadence": "daily", "run_hour_utc": 9, "run_weekday_utc": 0},
            ],
        }
    )
    assert svc.eligible_tenants(db, "collections", as_of=datetime(2026, 7, 21, 6)) == []  # t1 off, t2 @9
    assert svc.eligible_tenants(db, "collections", as_of=datetime(2026, 7, 21, 9)) == ["t2"]


def test_list_for_tenant_returns_all_jobs_with_effective_settings() -> None:
    db = _FakeDb(
        {
            "automation_schedules": [
                {"tenant_id": "t1", "job_key": "collections", "is_enabled": False,
                 "cadence": "weekly", "run_hour_utc": 10, "run_weekday_utc": 2, "timezone": "UTC"},
            ],
        }
    )
    rows = svc.list_for_tenant(db, "t1")
    assert {r["job_key"] for r in rows} == set(svc.JOB_DEFINITIONS)
    collections = next(r for r in rows if r["job_key"] == "collections")
    assert collections["is_enabled"] is False
    assert collections["configured"] is True
    billing = next(r for r in rows if r["job_key"] == "billing_run")
    assert billing["configured"] is False  # falls back to default
    assert billing["cadence"] == "monthly"


def test_update_schedule_validates_and_upserts() -> None:
    db = _FakeDb({"automation_schedules": []})
    out = svc.update_schedule(db, "t1", "collections", {"is_enabled": False, "run_hour_utc": 9})
    assert out["is_enabled"] is False
    assert out["run_hour_utc"] == 9
    assert db.upserts and db.upserts[0]["job_key"] == "collections"

    with pytest.raises(ValueError):
        svc.update_schedule(db, "t1", "not_a_job", {})
    with pytest.raises(ValueError):
        svc.update_schedule(db, "t1", "collections", {"run_hour_utc": 99})
    with pytest.raises(ValueError):
        svc.update_schedule(db, "t1", "collections", {"cadence": "hourly"})
