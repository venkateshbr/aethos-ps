"""Unit tests for agent circuit breaker state updates."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.agent_circuit_breaker import AgentCircuitBreaker


class _Query:
    def __init__(self, table_rows: list[dict]) -> None:
        self.table_rows = table_rows
        self.filters: list[tuple[str, object]] = []
        self.limit_value: int | None = None
        self.mode = "select"
        self.patch: dict | None = None

    def select(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def eq(self, column: str, value: object) -> _Query:
        self.filters.append((column, value))
        return self

    def limit(self, value: int) -> _Query:
        self.limit_value = value
        return self

    def update(self, patch: dict) -> _Query:
        self.mode = "update"
        self.patch = patch
        return self

    def upsert(self, patch: dict, **_kwargs: object) -> _Query:
        self.mode = "upsert"
        self.patch = patch
        return self

    def execute(self) -> SimpleNamespace:
        if self.mode == "select":
            rows = self._filtered_rows()
            if self.limit_value is not None:
                rows = rows[: self.limit_value]
            return SimpleNamespace(data=rows)

        if self.mode == "update":
            for row in self._filtered_rows():
                row.update(self.patch or {})
            return SimpleNamespace(data=self._filtered_rows())

        if self.mode == "upsert":
            assert self.patch is not None
            key = (
                self.patch["tenant_id"],
                self.patch["agent_name"],
                self.patch["action_type"],
            )
            for row in self.table_rows:
                if (row["tenant_id"], row["agent_name"], row["action_type"]) == key:
                    row.update(self.patch)
                    return SimpleNamespace(data=[row])
            row = {
                "failure_threshold": 3,
                "is_enabled": True,
                **self.patch,
            }
            self.table_rows.append(row)
            return SimpleNamespace(data=[row])

        raise AssertionError(f"unexpected mode {self.mode}")

    def _filtered_rows(self) -> list[dict]:
        rows = self.table_rows
        for column, value in self.filters:
            rows = [row for row in rows if row.get(column) == value]
        return rows


class _Db:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def table(self, name: str) -> _Query:
        assert name == "agent_autonomy_settings"
        return _Query(self.rows)


def _control_row(action_type: str) -> dict:
    return {
        "tenant_id": "tenant-1",
        "agent_name": "copilot_agent",
        "action_type": action_type,
        "failure_count": 1,
        "failure_threshold": 2,
        "is_enabled": True,
        "circuit_open_until": None,
        "circuit_open_reason": None,
    }


@pytest.mark.asyncio
async def test_failure_opens_agent_and_tool_circuits_then_success_resets() -> None:
    rows = [_control_row("default"), _control_row("copilot_update_rate_card")]
    breaker = AgentCircuitBreaker(_Db(rows), tenant_id="tenant-1")

    await breaker.record_tool_result(
        agent_name="copilot_agent",
        action_type="copilot_update_rate_card",
        status="failed",
        error_message="boom",
    )

    assert rows[0]["failure_count"] == 2
    assert rows[0]["circuit_open_until"] is not None
    assert rows[0]["circuit_open_reason"] == "boom"
    assert rows[1]["failure_count"] == 2
    assert rows[1]["circuit_open_until"] is not None
    assert rows[1]["circuit_open_reason"] == "boom"

    await breaker.record_tool_result(
        agent_name="copilot_agent",
        action_type="copilot_update_rate_card",
        status="succeeded",
    )

    assert rows[0]["failure_count"] == 0
    assert rows[0]["circuit_open_until"] is None
    assert rows[0]["circuit_open_reason"] is None
    assert rows[1]["failure_count"] == 0
    assert rows[1]["circuit_open_until"] is None
    assert rows[1]["circuit_open_reason"] is None
