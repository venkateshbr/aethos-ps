"""Unit tests for persisted financial close tasks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from app.services.close_tasks_service import CloseTasksService

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-1"


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _Query:
    def __init__(self, db: _Db, table: str) -> None:
        self.db = db
        self.table = table
        self._eq_filters: list[tuple[str, Any]] = []
        self._null_filters: list[str] = []
        self._order_key: str | None = None
        self._insert_payload: list[dict[str, Any]] | None = None
        self._update_payload: dict[str, Any] | None = None

    def select(self, _columns: str = "*") -> _Query:
        return self

    def eq(self, key: str, value: Any) -> _Query:
        self._eq_filters.append((key, value))
        return self

    def is_(self, key: str, value: Any) -> _Query:
        if value == "null":
            self._null_filters.append(key)
        return self

    def order(self, key: str) -> _Query:
        self._order_key = key
        return self

    def insert(self, payload: list[dict[str, Any]]) -> _Query:
        self._insert_payload = deepcopy(payload)
        return self

    def update(self, payload: dict[str, Any]) -> _Query:
        self._update_payload = dict(payload)
        return self

    def execute(self) -> _Result:
        if self._insert_payload is not None:
            inserted: list[dict[str, Any]] = []
            for idx, payload in enumerate(self._insert_payload, start=1):
                row = {"id": f"task-{idx}", "deleted_at": None, **payload}
                self.db.tables[self.table].append(row)
                inserted.append(row)
            return _Result(deepcopy(inserted))

        rows = [row for row in self.db.tables[self.table] if self._matches(row)]
        if self._update_payload is not None:
            for row in rows:
                row.update(self._update_payload)
            return _Result(deepcopy(rows))
        if self._order_key is not None:
            rows.sort(key=lambda row: row.get(self._order_key) or 0)
        return _Result(deepcopy(rows))

    def _matches(self, row: dict[str, Any]) -> bool:
        return all(row.get(key) == value for key, value in self._eq_filters) and all(
            row.get(key) is None for key in self._null_filters
        )


class _Db:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.tables = {"accounting_close_tasks": rows or []}

    def table(self, name: str) -> _Query:
        return _Query(self, name)


class _MissingCloseTasksDb(_Db):
    def table(self, name: str) -> _Query:
        if name == "accounting_close_tasks":
            raise RuntimeError(
                {
                    "code": "PGRST205",
                    "message": (
                        "Could not find the table 'public.accounting_close_tasks' "
                        "in the schema cache"
                    ),
                }
            )
        return super().table(name)


def test_incomplete_blocking_tasks_treats_missing_table_as_empty() -> None:
    service = CloseTasksService(_MissingCloseTasksDb(), TENANT_ID)  # type: ignore[arg-type]

    assert service.incomplete_blocking_tasks("2026-06") == []


def test_period_lock_action_is_not_its_own_precondition() -> None:
    db = _Db(
        [
            {
                "id": "task-review",
                "tenant_id": TENANT_ID,
                "period": "2026-06",
                "code": "trial_balance_review",
                "status": "done",
                "order_index": 40,
                "deleted_at": None,
            },
            {
                "id": "task-lock",
                "tenant_id": TENANT_ID,
                "period": "2026-06",
                "code": "period_lock",
                "status": "open",
                "order_index": 50,
                "deleted_at": None,
            },
        ]
    )
    service = CloseTasksService(db, TENANT_ID)  # type: ignore[arg-type]

    assert service.incomplete_blocking_tasks("2026-06") == []


@pytest.mark.asyncio
async def test_successful_period_lock_action_completes_its_checklist_item() -> None:
    db = _Db(
        [
            {
                "id": "task-lock",
                "tenant_id": TENANT_ID,
                "period": "2026-06",
                "code": "period_lock",
                "status": "open",
                "order_index": 50,
                "deleted_at": None,
            }
        ]
    )
    service = CloseTasksService(db, TENANT_ID)  # type: ignore[arg-type]

    updated = await service.mark_period_lock_task(
        period="2026-06",
        actor_id="admin-1",
        locked=True,
    )

    assert updated is not None
    assert updated["status"] == "done"
    assert updated["completed_by"] == "admin-1"


@pytest.mark.asyncio
async def test_bootstrap_tasks_returns_empty_when_table_is_missing() -> None:
    service = CloseTasksService(_MissingCloseTasksDb(), TENANT_ID)  # type: ignore[arg-type]

    assert await service.bootstrap_tasks("2026-06", "admin-1") == []


@pytest.mark.asyncio
async def test_update_task_returns_none_when_table_is_missing() -> None:
    service = CloseTasksService(_MissingCloseTasksDb(), TENANT_ID)  # type: ignore[arg-type]

    assert (
        await service.update_task(
            period="2026-06",
            task_id="task-1",
            patch={"status": "done"},
            actor_id="admin-1",
        )
        is None
    )


@pytest.mark.asyncio
async def test_bootstrap_tasks_persists_default_tasks_when_table_exists() -> None:
    db = _Db()
    service = CloseTasksService(db, TENANT_ID)  # type: ignore[arg-type]

    tasks = await service.bootstrap_tasks("2026-06", "admin-1")

    assert len(tasks) == 6
    assert tasks[0]["code"] == "subledger_reconciliation"
    assert tasks[-1]["code"] == "period_lock"
