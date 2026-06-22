"""Unit tests for agent run dashboard service methods."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.agents_service import AgentsService


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.filters: list[tuple[str, object]] = []
        self.in_filters: list[tuple[str, list[object]]] = []
        self.limit_value: int | None = None
        self.order_column: str | None = None
        self.order_desc = False

    def select(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def eq(self, column: str, value: object) -> _Query:
        self.filters.append((column, value))
        return self

    def in_(self, column: str, values: list[object]) -> _Query:
        self.in_filters.append((column, values))
        return self

    def order(self, column: str, *, desc: bool = False) -> _Query:
        self.order_column = column
        self.order_desc = desc
        return self

    def limit(self, value: int) -> _Query:
        self.limit_value = value
        return self

    def execute(self) -> SimpleNamespace:
        rows = list(self.rows)
        for column, value in self.filters:
            rows = [row for row in rows if row.get(column) == value]
        for column, values in self.in_filters:
            rows = [row for row in rows if row.get(column) in values]
        if self.order_column:
            rows = sorted(
                rows,
                key=lambda row: str(row.get(self.order_column) or ""),
                reverse=self.order_desc,
            )
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)


class _Db:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(list(self.tables.get(name, [])))


def _run_row(**overrides: object) -> dict:
    row = {
        "id": "run-1",
        "tenant_id": "tenant-1",
        "agent_name": "copilot_agent",
        "trigger_type": "chat",
        "status": "succeeded",
        "user_id": "user-1",
        "source_document_hash": None,
        "prompt_version": "cop-v1",
        "model_version": "model-a",
        "input_hash": "input-hash",
        "output_hash": "output-hash",
        "usage_input_tokens": 10,
        "usage_output_tokens": 20,
        "cost_usd": "0.001000",
        "trace_id": "trace-1",
        "replay_pointer": "chat_threads/thread-1",
        "error_message": None,
        "started_at": "2026-06-22T06:00:00Z",
        "completed_at": "2026-06-22T06:00:01Z",
        "created_at": "2026-06-22T06:00:00Z",
    }
    row.update(overrides)
    return row


def _tool_row(**overrides: object) -> dict:
    row = {
        "id": "tool-1",
        "tenant_id": "tenant-1",
        "agent_run_id": "run-1",
        "tool_name": "get_wip",
        "risk_class": "read_only",
        "status": "succeeded",
        "external_tool_call_id": "call-1",
        "input_hash": "tool-input",
        "output_hash": "tool-output",
        "input_snapshot": {"engagement_id": "eng-1"},
        "output_snapshot": {"wip": []},
        "duration_ms": 12,
        "error_message": None,
        "created_at": "2026-06-22T06:00:00Z",
    }
    row.update(overrides)
    return row


def test_list_agent_runs_returns_recent_runs_with_tool_counts() -> None:
    db = _Db(
        {
            "agent_runs": [
                _run_row(id="run-1", created_at="2026-06-22T06:00:00Z"),
                _run_row(id="run-2", status="failed", created_at="2026-06-22T07:00:00Z"),
                _run_row(id="other-tenant-run", tenant_id="tenant-2"),
            ],
            "agent_tool_invocations": [
                _tool_row(agent_run_id="run-1"),
                _tool_row(agent_run_id="run-1", id="tool-2", status="failed"),
                _tool_row(agent_run_id="run-2", id="tool-3"),
                _tool_row(agent_run_id="other-tenant-run", tenant_id="tenant-2"),
            ],
        }
    )

    result = AgentsService(db, "tenant-1").list_agent_runs(limit=10)  # type: ignore[arg-type]

    assert result["total"] == 2
    assert [run["id"] for run in result["runs"]] == ["run-2", "run-1"]
    assert result["runs"][0]["tool_count"] == 1
    assert result["runs"][0]["failed_tool_count"] == 0
    assert result["runs"][1]["tool_count"] == 2
    assert result["runs"][1]["failed_tool_count"] == 1
    assert result["runs"][1]["cost_usd"] == "0.001000"


def test_list_agent_runs_filters_by_agent_and_status() -> None:
    db = _Db(
        {
            "agent_runs": [
                _run_row(id="run-1", agent_name="copilot_agent", status="succeeded"),
                _run_row(id="run-2", agent_name="reporting_agent", status="succeeded"),
                _run_row(id="run-3", agent_name="copilot_agent", status="failed"),
            ],
            "agent_tool_invocations": [],
        }
    )

    result = AgentsService(db, "tenant-1").list_agent_runs(  # type: ignore[arg-type]
        agent_name="copilot_agent",
        status="failed",
    )

    assert result["total"] == 1
    assert result["runs"][0]["id"] == "run-3"


def test_get_agent_run_returns_detail_with_tool_invocations() -> None:
    db = _Db(
        {
            "agent_runs": [_run_row(id="run-1")],
            "agent_tool_invocations": [
                _tool_row(id="tool-2", agent_run_id="run-1", status="failed"),
                _tool_row(id="tool-1", agent_run_id="run-1"),
            ],
        }
    )

    result = AgentsService(db, "tenant-1").get_agent_run("run-1")  # type: ignore[arg-type]

    assert result is not None
    assert result["id"] == "run-1"
    assert result["tool_count"] == 2
    assert result["failed_tool_count"] == 1
    assert [tool["id"] for tool in result["tool_invocations"]] == ["tool-2", "tool-1"]
    assert result["tool_invocations"][0]["input_snapshot"] == {"engagement_id": "eng-1"}


def test_get_agent_run_returns_none_for_missing_run() -> None:
    db = _Db({"agent_runs": [], "agent_tool_invocations": []})

    assert AgentsService(db, "tenant-1").get_agent_run("missing") is None  # type: ignore[arg-type]
