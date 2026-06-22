"""Unit tests for agent kill-switch service methods."""

from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest

from app.services.agents_service import AgentAutonomyError, AgentsService


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.filters: list[tuple[str, object]] = []
        self.in_filters: list[tuple[str, list[object]]] = []
        self.limit_value: int | None = None
        self.mode = "select"
        self.patch: dict | None = None

    def select(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def eq(self, column: str, value: object) -> _Query:
        self.filters.append((column, value))
        return self

    def in_(self, column: str, values: list[object]) -> _Query:
        self.in_filters.append((column, values))
        return self

    def gte(self, _column: str, _value: object) -> _Query:
        return self

    def limit(self, value: int) -> _Query:
        self.limit_value = value
        return self

    def upsert(self, patch: dict, **_kwargs: object) -> _Query:
        self.mode = "upsert"
        self.patch = patch
        return self

    def execute(self) -> SimpleNamespace:
        if self.mode == "upsert":
            assert self.patch is not None
            key = (
                self.patch["tenant_id"],
                self.patch["agent_name"],
                self.patch["action_type"],
            )
            for row in self.rows:
                if (row["tenant_id"], row["agent_name"], row["action_type"]) == key:
                    row.update(self.patch)
                    return SimpleNamespace(data=[row])
            row = {
                "level": 2,
                "is_enabled": True,
                "failure_count": 0,
                "failure_threshold": 3,
                "circuit_open_until": None,
                "circuit_open_reason": None,
                **self.patch,
            }
            self.rows.append(row)
            return SimpleNamespace(data=[row])

        rows = self._filtered_rows()
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)

    def _filtered_rows(self) -> list[dict]:
        rows = self.rows
        for column, value in self.filters:
            rows = [row for row in rows if row.get(column) == value]
        for column, values in self.in_filters:
            rows = [row for row in rows if row.get(column) in values]
        return rows


class _Db:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.setdefault(name, []))

    def rpc(self, _name: str, _params: dict) -> SimpleNamespace:
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=[]))


def _control_row(**overrides: object) -> dict:
    future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=10)
    row = {
        "tenant_id": "tenant-1",
        "agent_name": "copilot_agent",
        "action_type": "default",
        "level": 2,
        "is_enabled": False,
        "failure_count": 2,
        "failure_threshold": 3,
        "circuit_open_until": future.isoformat(),
        "circuit_open_reason": "boom",
        "l3_opt_in": False,
        "eval_passed_at": None,
        "eval_score": None,
        "max_auto_risk": "draft",
    }
    row.update(overrides)
    return row


def _suggestion_row(**overrides: object) -> dict:
    row = {
        "tenant_id": "tenant-1",
        "agent_name": "copilot_agent",
        "action_type": "default",
        "status": "approved",
        "confidence": "0.99",
        "created_at": "2026-06-22T06:00:00Z",
    }
    row.update(overrides)
    return row


def test_get_autonomy_status_includes_control_state() -> None:
    db = _Db(
        {
            "agent_suggestions": [],
            "agent_autonomy_settings": [_control_row()],
        }
    )

    result = AgentsService(db, "tenant-1").get_autonomy_status()  # type: ignore[arg-type]
    copilot = next(agent for agent in result if agent["agent_name"] == "copilot_agent")

    assert copilot["is_enabled"] is False
    assert copilot["failure_count"] == 2
    assert copilot["failure_threshold"] == 3
    assert copilot["circuit_open_reason"] == "boom"
    assert copilot["is_circuit_open"] is True


def test_set_agent_control_updates_existing_row_and_resets_circuit() -> None:
    rows = [_control_row()]
    db = _Db({"agent_autonomy_settings": rows})

    result = AgentsService(db, "tenant-1").set_agent_control(  # type: ignore[arg-type]
        "copilot_agent",
        is_enabled=True,
        reset_circuit=True,
    )

    assert result["is_enabled"] is True
    assert result["failure_count"] == 0
    assert result["circuit_open_until"] is None
    assert result["is_circuit_open"] is False
    assert rows[0]["is_enabled"] is True
    assert rows[0]["failure_count"] == 0
    assert rows[0]["circuit_open_until"] is None


def test_set_agent_control_rejects_guardian_disable() -> None:
    db = _Db({"agent_autonomy_settings": []})

    with pytest.raises(AgentAutonomyError, match="cannot be disabled"):
        AgentsService(db, "tenant-1").set_agent_control(  # type: ignore[arg-type]
            "accounting_guardian",
            is_enabled=False,
        )


def test_set_autonomy_level_l3_requires_l3_policy_gates() -> None:
    db = _Db(
        {
            "agent_autonomy_settings": [_control_row(l3_opt_in=False)],
            "agent_suggestions": [_suggestion_row() for _ in range(60)],
        }
    )

    with pytest.raises(AgentAutonomyError, match="admin opt-in"):
        AgentsService(db, "tenant-1").set_autonomy_level(  # type: ignore[arg-type]
            "copilot_agent",
            3,
        )


def test_set_autonomy_level_l3_requires_default_risk_permission() -> None:
    db = _Db(
        {
            "agent_autonomy_settings": [
                _control_row(
                    is_enabled=True,
                    l3_opt_in=True,
                    eval_passed_at="2026-06-22T06:00:00Z",
                    max_auto_risk="draft",
                )
            ],
            "agent_suggestions": [_suggestion_row() for _ in range(60)],
        }
    )

    with pytest.raises(AgentAutonomyError, match="max_auto_risk >= write_money_in"):
        AgentsService(db, "tenant-1").set_autonomy_level(  # type: ignore[arg-type]
            "copilot_agent",
            3,
        )


def test_set_autonomy_level_l3_allowed_when_all_gates_pass() -> None:
    db = _Db(
        {
            "agent_autonomy_settings": [
                _control_row(
                    is_enabled=True,
                    l3_opt_in=True,
                    eval_passed_at="2026-06-22T06:00:00Z",
                    max_auto_risk="write_money_in",
                )
            ],
            "agent_suggestions": [_suggestion_row() for _ in range(60)],
        }
    )

    result = AgentsService(db, "tenant-1").set_autonomy_level(  # type: ignore[arg-type]
        "copilot_agent",
        3,
    )

    assert result == {"agent_name": "copilot_agent", "level": 3}
    assert db.tables["agent_autonomy_settings"][0]["level"] == 3
