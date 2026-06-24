"""Unit tests for scheduled month-end close preparation."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


def test_close_scheduler_worker_is_registered() -> None:
    from procrastinate.tasks import Task

    from app.workers.close_scheduler_worker import run_monthly_financial_close

    assert isinstance(run_monthly_financial_close, Task)


def test_previous_period_for_handles_january_boundary() -> None:
    from app.workers.close_scheduler_worker import _previous_period_for

    assert _previous_period_for(date(2026, 6, 1)) == "2026-05"
    assert _previous_period_for(date(2026, 1, 1)) == "2025-12"


@pytest.mark.asyncio
async def test_run_close_for_tenant_bootstraps_tasks_and_records_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers import close_scheduler_worker

    finished: list[dict[str, Any]] = []
    calls: list[str] = []

    monkeypatch.setattr(
        close_scheduler_worker,
        "_start_workflow_run",
        lambda *_args, **_kwargs: "workflow-1",
    )
    monkeypatch.setattr(
        close_scheduler_worker,
        "_finish_workflow_run",
        lambda _db, _workflow_id, **kwargs: finished.append(kwargs),
    )
    monkeypatch.setattr(
        close_scheduler_worker,
        "_period_locked",
        lambda *_args, **_kwargs: False,
    )

    async def _bootstrap(_self: object, period: str, created_by: str) -> list[dict]:
        assert period == "2026-06"
        assert created_by == "close_scheduler_worker"
        return [{"id": "task-1"}, {"id": "task-2"}]

    monkeypatch.setattr(
        close_scheduler_worker.CloseTasksService,
        "bootstrap_tasks",
        _bootstrap,
    )

    def _writer(name: str) -> AsyncMock:
        async def _impl(deps: object, period: str, **_kwargs: str) -> dict[str, Any]:
            assert deps.tenant_id == "tenant-1"  # type: ignore[attr-defined]
            assert deps.user_id is None  # type: ignore[attr-defined]
            assert period == "2026-06"
            calls.append(name)
            return {"created_count": 1, "suggestion_ids": [f"{name}-suggestion"]}

        return AsyncMock(side_effect=_impl)

    patched_steps = tuple(
        (name, _writer(name), {})
        for name, _writer_ref, _kwargs in close_scheduler_worker._PROPOSAL_STEPS
    )
    monkeypatch.setattr(close_scheduler_worker, "_PROPOSAL_STEPS", patched_steps)

    status = SimpleNamespace(
        pending_reviews=[SimpleNamespace(id="suggestion-1")],
        as_dict=lambda: {
            "period": "2026-06",
            "status": "blocked",
            "pending_reviews": [{"id": "suggestion-1"}],
        },
    )
    monkeypatch.setattr(
        close_scheduler_worker.CloseStatusService,
        "get_status",
        lambda _self, _period: status,
    )
    monkeypatch.setattr(
        close_scheduler_worker.ClosePackageService,
        "build_package",
        lambda _self, _period: {
            "period": "2026-06",
            "net_income": "100.00",
            "total_ar": "250.00",
            "total_ap": "75.00",
            "variance_commentary": [{"code": "net_income"}],
        },
    )

    result = await close_scheduler_worker._run_close_for_tenant(
        object(),
        tenant_id="tenant-1",
        period="2026-06",
    )

    assert result["workflow_status"] == "waiting_on_human"
    assert result["task_count"] == 2
    assert result["suggestions_created"] == len(patched_steps)
    assert result["proposal_errors"] == {}
    assert set(calls) == {step[0] for step in patched_steps}
    assert finished[-1]["status"] == "waiting_on_human"
    assert finished[-1]["current_step"] == "hitl_review"
    assert finished[-1]["state_snapshot"]["close_package_summary"]["net_income"] == "100.00"


@pytest.mark.asyncio
async def test_run_close_for_tenant_skips_locked_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers import close_scheduler_worker

    finished: list[dict[str, Any]] = []
    monkeypatch.setattr(
        close_scheduler_worker,
        "_start_workflow_run",
        lambda *_args, **_kwargs: "workflow-1",
    )
    monkeypatch.setattr(
        close_scheduler_worker,
        "_finish_workflow_run",
        lambda _db, _workflow_id, **kwargs: finished.append(kwargs),
    )
    monkeypatch.setattr(
        close_scheduler_worker,
        "_period_locked",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        close_scheduler_worker.CloseTasksService,
        "bootstrap_tasks",
        AsyncMock(side_effect=AssertionError("locked close should not bootstrap tasks")),
    )

    result = await close_scheduler_worker._run_close_for_tenant(
        object(),
        tenant_id="tenant-1",
        period="2026-06",
    )

    assert result["result"] == "skipped_locked"
    assert finished[-1]["status"] == "succeeded"
    assert finished[-1]["current_step"] == "complete"


@pytest.mark.asyncio
async def test_run_close_for_tenant_fails_when_task_bootstrap_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers import close_scheduler_worker

    finished: list[dict[str, Any]] = []
    monkeypatch.setattr(
        close_scheduler_worker,
        "_start_workflow_run",
        lambda *_args, **_kwargs: "workflow-1",
    )
    monkeypatch.setattr(
        close_scheduler_worker,
        "_finish_workflow_run",
        lambda _db, _workflow_id, **kwargs: finished.append(kwargs),
    )
    monkeypatch.setattr(
        close_scheduler_worker,
        "_period_locked",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        close_scheduler_worker.CloseTasksService,
        "bootstrap_tasks",
        AsyncMock(return_value=[]),
    )

    with pytest.raises(RuntimeError, match="migration 0068_accounting_close_tasks"):
        await close_scheduler_worker._run_close_for_tenant(
            object(),
            tenant_id="tenant-1",
            period="2026-06",
        )

    assert finished[-1]["status"] == "failed"
    assert finished[-1]["current_step"] == "failed"
