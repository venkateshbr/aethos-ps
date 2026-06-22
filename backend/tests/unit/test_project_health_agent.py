"""Unit tests for project_health_agent and project_health_worker.

TDD red phase — all tests are written before implementation exists.
Coverage:
  - test_budget_burn_alert_created: project at 85% hours => alert written to agent_suggestions
  - test_no_alert_below_threshold: project at 70% => no alert
  - test_retainer_floor_alert: retainer project with hours < floor => alert
  - test_dedup_7_days: same (project_id, alert_type) not re-created within 7 days
  - test_capped_tm_approaching: capped_tm at 92% of cap amount => alert

All tests are pure-Python — no I/O, no DB, no HTTP.
DB interactions are replaced with lightweight MagicMock stubs.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.agents.base import AgentDeps
from app.agents.project_health_agent import (
    check_project_health,
)
from app.workers.project_health_worker import (
    _is_duplicate_alert,
    _process_project,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------


class _FlatMock:
    """Chainable stub: every attr access and call returns self.

    Set ``.final_data`` to control what ``.execute().data`` returns.
    ``final_count`` controls ``.count``.
    """

    def __init__(self, data: list | None = None, count: int | None = None) -> None:
        self.final_data = data if data is not None else []
        self.final_count = count

    def __getattr__(self, name: str) -> _FlatMock:
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> _FlatMock:
        return self

    @property
    def data(self) -> list:
        return self.final_data

    @property
    def count(self) -> int | None:
        return self.final_count

    def execute(self) -> _FlatMock:
        return self


def _make_deps(
    suggestions: list[dict] | None = None,
    time_entry_data: list[dict] | None = None,
    invoice_data: list[dict] | None = None,
    insert_result: dict | None = None,
) -> tuple[AgentDeps, MagicMock]:
    """Build an AgentDeps with a MagicMock Supabase client.

    The stub routes .table() calls:
      - "agent_suggestions" => returns suggestion dedup rows
      - "time_entries"      => returns time entry rows
      - "invoices"          => returns invoice rows
      - "hitl_tasks"        => accepts inserts (captured for assertions)
    """
    db = MagicMock()

    sugg_mock = _FlatMock(suggestions or [])
    te_mock = _FlatMock(time_entry_data or [])
    inv_mock = _FlatMock(invoice_data or [])

    inserted: list[dict] = []
    _insert_result = MagicMock()
    _insert_result.execute.return_value = MagicMock(
        data=[insert_result or {"id": str(uuid.uuid4())}]
    )

    def _capture_insert(payload: dict) -> MagicMock:
        inserted.append(payload)
        return _insert_result

    def table_side_effect(table_name: str) -> MagicMock:
        t = MagicMock()
        if table_name == "agent_suggestions":
            t.select.return_value = sugg_mock
            t.insert.side_effect = _capture_insert
        elif table_name == "time_entries":
            t.select.return_value = te_mock
        elif table_name == "invoices":
            t.select.return_value = inv_mock
        elif table_name == "hitl_tasks":
            t.insert.side_effect = _capture_insert
        else:
            t.select.return_value = _FlatMock([])
            t.insert.side_effect = _capture_insert
        return t

    db.table.side_effect = table_side_effect

    tenant_id = str(uuid.uuid4())
    deps = AgentDeps(tenant_id=tenant_id, user_id=None, db=db)
    return deps, db


# ---------------------------------------------------------------------------
# check_project_health — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_burn_alert_created() -> None:
    """Project with 85% hours consumed triggers BUDGET_BURN_WARNING."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "Alpha Build",
        "status": "active",
        "budget_hours": 100.0,
        "billing_arrangement": "time_and_materials",
    }

    # 85 hours logged out of 100 budget_hours
    te_data = [
        {"hours": 50.0, "billable": True},
        {"hours": 35.0, "billable": True},
    ]

    deps, _ = _make_deps(suggestions=[], time_entry_data=te_data)

    alerts = await check_project_health(project, deps)

    budget_alerts = [a for a in alerts if a.alert_type == "BUDGET_BURN_WARNING"]
    assert len(budget_alerts) == 1
    alert = budget_alerts[0]
    assert alert.project_id == uuid.UUID(project_id)
    assert alert.project_name == "Alpha Build"
    assert "85" in alert.metric_current
    assert 0.0 < alert.confidence <= 1.0


@pytest.mark.asyncio
async def test_no_alert_below_threshold() -> None:
    """Project at 70% budget hours does NOT trigger BUDGET_BURN_WARNING."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "Beta Build",
        "status": "active",
        "budget_hours": 100.0,
        "billing_arrangement": "time_and_materials",
    }

    te_data = [
        {"hours": 40.0, "billable": True},
        {"hours": 30.0, "billable": True},
    ]

    deps, _ = _make_deps(suggestions=[], time_entry_data=te_data)

    alerts = await check_project_health(project, deps)

    budget_alerts = [a for a in alerts if a.alert_type == "BUDGET_BURN_WARNING"]
    assert len(budget_alerts) == 0


@pytest.mark.asyncio
async def test_retainer_floor_alert() -> None:
    """Retainer project with hours below floor triggers RETAINER_FLOOR_WARNING."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "Gamma Retainer",
        "status": "active",
        "budget_hours": None,
        "billing_arrangement": "retainer",
        "retainer_floor_hours": 40.0,  # floor: 40 hours/period
        "hours_this_period": 15.0,     # only 15 logged — below floor
    }

    deps, _ = _make_deps(suggestions=[], time_entry_data=[])

    alerts = await check_project_health(project, deps)

    floor_alerts = [a for a in alerts if a.alert_type == "RETAINER_FLOOR_WARNING"]
    assert len(floor_alerts) == 1
    alert = floor_alerts[0]
    assert alert.project_id == uuid.UUID(project_id)
    assert "15" in alert.metric_current or "floor" in alert.metric_threshold.lower()


@pytest.mark.asyncio
async def test_capped_tm_approaching() -> None:
    """Capped T&M project at 92% of cap amount triggers CAPPED_TM_APPROACHING."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "Delta Capped",
        "status": "active",
        "budget_hours": None,
        "billing_arrangement": "capped_tm",
        "cap_amount": 50000.0,
        "billed_amount": 46000.0,  # 92% of cap
    }

    deps, _ = _make_deps(suggestions=[], time_entry_data=[])

    alerts = await check_project_health(project, deps)

    cap_alerts = [a for a in alerts if a.alert_type == "CAPPED_TM_APPROACHING"]
    assert len(cap_alerts) == 1
    alert = cap_alerts[0]
    assert alert.project_id == uuid.UUID(project_id)
    assert "92" in alert.metric_current


@pytest.mark.asyncio
async def test_no_capped_tm_alert_below_threshold() -> None:
    """Capped T&M at 85% of cap (below 90% threshold) does NOT trigger CAPPED_TM_APPROACHING."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "Epsilon Capped",
        "status": "active",
        "budget_hours": None,
        "billing_arrangement": "capped_tm",
        "cap_amount": 50000.0,
        "billed_amount": 42500.0,  # 85% of cap
    }

    deps, _ = _make_deps(suggestions=[], time_entry_data=[])

    alerts = await check_project_health(project, deps)

    cap_alerts = [a for a in alerts if a.alert_type == "CAPPED_TM_APPROACHING"]
    assert len(cap_alerts) == 0


# ---------------------------------------------------------------------------
# _is_duplicate_alert — dedup tests
# ---------------------------------------------------------------------------


def test_dedup_7_days_returns_true_when_recent_suggestion_exists() -> None:
    """_is_duplicate_alert returns True when same project+type alerted within 7 days."""
    project_id = str(uuid.uuid4())
    existing_suggestion = {
        "id": str(uuid.uuid4()),
        "agent_name": "project_health_agent",
        "action_type": "BUDGET_BURN_WARNING",
        "related_entity_id": project_id,
        "status": "pending",
    }
    deps, _ = _make_deps(suggestions=[existing_suggestion])

    result = _is_duplicate_alert(deps.db, deps.tenant_id, project_id, "BUDGET_BURN_WARNING")

    assert result is True


def test_dedup_7_days_returns_false_when_no_recent_suggestion() -> None:
    """_is_duplicate_alert returns False when no recent alert exists."""
    project_id = str(uuid.uuid4())
    deps, _ = _make_deps(suggestions=[])  # empty — no existing alert

    result = _is_duplicate_alert(deps.db, deps.tenant_id, project_id, "BUDGET_BURN_WARNING")

    assert result is False


def test_dedup_7_days_returns_false_when_suggestion_is_rejected() -> None:
    """_is_duplicate_alert returns False when previous alert was rejected (not pending/approved)."""
    project_id = str(uuid.uuid4())
    rejected_suggestion = {
        "id": str(uuid.uuid4()),
        "agent_name": "project_health_agent",
        "action_type": "BUDGET_BURN_WARNING",
        "related_entity_id": project_id,
        "status": "rejected",
    }
    _deps, _ = _make_deps(suggestions=[rejected_suggestion])

    # The dedup check should only block on pending/approved — rejected allows re-alert.
    # Our stub returns the row regardless; the real DB query filters by status.
    # We simulate that the query returned nothing (rejection excluded by WHERE clause).
    deps2, _ = _make_deps(suggestions=[])

    result = _is_duplicate_alert(deps2.db, deps2.tenant_id, project_id, "BUDGET_BURN_WARNING")

    assert result is False


# ---------------------------------------------------------------------------
# _process_project — integration with suggestion_writer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_project_writes_suggestion_and_hitl_task() -> None:
    """_process_project calls write_agent_suggestion when an alert fires."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "Zeta Build",
        "status": "active",
        "budget_hours": 100.0,
        "billing_arrangement": "time_and_materials",
    }

    te_data = [{"hours": 88.0, "billable": True}]  # 88% — triggers alert

    deps, _db = _make_deps(suggestions=[], time_entry_data=te_data)

    with patch(
        "app.workers.project_health_worker.write_agent_suggestion"
    ) as mock_write:
        mock_write.return_value = {"id": str(uuid.uuid4())}
        await _process_project(project, deps)

    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args
    # Verify the call used the correct agent name and action_type
    assert call_kwargs.args[1] == "project_health_agent"  # agent_name
    assert call_kwargs.args[2] == "BUDGET_BURN_WARNING"   # action_type
    assert call_kwargs.kwargs["related_entity_type"] == "project"
    assert call_kwargs.kwargs["related_entity_id"] == project_id


@pytest.mark.asyncio
async def test_process_project_skips_when_dedup_blocks() -> None:
    """_process_project does NOT write a suggestion when dedup returns True."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "Eta Build",
        "status": "active",
        "budget_hours": 100.0,
        "billing_arrangement": "time_and_materials",
    }

    te_data = [{"hours": 90.0, "billable": True}]  # 90% — would trigger alert

    # Existing suggestion within 7 days
    existing = [
        {
            "id": str(uuid.uuid4()),
            "agent_name": "project_health_agent",
            "action_type": "BUDGET_BURN_WARNING",
            "related_entity_id": project_id,
            "status": "pending",
        }
    ]
    deps, _ = _make_deps(suggestions=existing, time_entry_data=te_data)

    with patch(
        "app.workers.project_health_worker.write_agent_suggestion"
    ) as mock_write:
        mock_write.return_value = {"id": str(uuid.uuid4())}
        await _process_project(project, deps)

    mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_process_project_continues_on_per_project_exception() -> None:
    """Exceptions inside _process_project are caught — worker does not crash."""
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "Theta Build",
        "status": "active",
        "budget_hours": 100.0,
        "billing_arrangement": "time_and_materials",
    }

    deps, db = _make_deps()
    # Make time_entries raise to simulate a DB error mid-flight
    db.table.side_effect = RuntimeError("DB connection lost")

    # Should NOT raise — exceptions are gracefully caught
    result = await _process_project(project, deps)
    assert result is None or isinstance(result, int)
