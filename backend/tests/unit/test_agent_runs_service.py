"""Unit tests for agent run dashboard service methods."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.agent_run_ledger import stable_payload_hash
from app.services.agents_service import AgentsService


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.filters: list[tuple[str, object]] = []
        self.in_filters: list[tuple[str, list[object]]] = []
        self.is_filters: list[tuple[str, object]] = []
        self.gte_filters: list[tuple[str, object]] = []
        self.lte_filters: list[tuple[str, object]] = []
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

    def is_(self, column: str, value: object) -> _Query:
        self.is_filters.append((column, value))
        return self

    def gte(self, column: str, value: object) -> _Query:
        self.gte_filters.append((column, value))
        return self

    def lte(self, column: str, value: object) -> _Query:
        self.lte_filters.append((column, value))
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
        for column, value in self.is_filters:
            if value == "null":
                rows = [row for row in rows if row.get(column) is None]
            else:
                rows = [row for row in rows if row.get(column) is value]
        for column, value in self.gte_filters:
            rows = [row for row in rows if row.get(column) >= value]
        for column, value in self.lte_filters:
            rows = [row for row in rows if row.get(column) <= value]
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


def _workflow_row(**overrides: object) -> dict:
    row = {
        "id": "workflow-1",
        "tenant_id": "tenant-1",
        "workflow_name": "monthly_retainer_billing_run",
        "status": "waiting_on_human",
        "owner_agent_name": "billing_run_agent",
        "user_id": None,
        "current_step": "awaiting_billing_run_review",
        "goal_snapshot": {"period_start": "2026-06-01"},
        "state_snapshot": {"billing_run_id": "billing-run-1"},
        "trace_id": "trace-workflow-1",
        "replay_pointer": "billing_runs/billing-run-1",
        "error_message": None,
        "started_at": "2026-06-22T06:00:00Z",
        "completed_at": None,
        "created_at": "2026-06-22T06:00:00Z",
        "updated_at": "2026-06-22T06:00:01Z",
    }
    row.update(overrides)
    return row


def _candidate_row(**overrides: object) -> dict:
    row = {
        "id": "candidate-1",
        "tenant_id": "tenant-1",
        "agent_correction_id": "correction-1",
        "agent_suggestion_id": "suggestion-1",
        "agent_name": "copilot_agent",
        "action_type": "copilot_update_rate_card",
        "eval_case_key": "copilot_agent:copilot_update_rate_card:correction:correction-1",
        "status": "candidate",
        "input_hash": "input-hash",
        "original_output_hash": "original-hash",
        "corrected_output_hash": "corrected-hash",
        "reason": "human_edit",
        "created_at": "2026-06-22T06:00:00Z",
        "updated_at": "2026-06-22T06:00:00Z",
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


def test_list_agent_workflow_runs_filters_by_status_and_workflow() -> None:
    db = _Db(
        {
            "agent_workflow_runs": [
                _workflow_row(id="workflow-1", created_at="2026-06-22T06:00:00Z"),
                _workflow_row(
                    id="workflow-2",
                    workflow_name="nightly_collections",
                    status="succeeded",
                    created_at="2026-06-22T07:00:00Z",
                    completed_at="2026-06-22T07:05:00Z",
                ),
                _workflow_row(id="other-tenant-workflow", tenant_id="tenant-2"),
            ],
        }
    )

    result = AgentsService(db, "tenant-1").list_agent_workflow_runs(  # type: ignore[arg-type]
        workflow_name="monthly_retainer_billing_run",
        status="waiting_on_human",
        limit=10,
    )

    assert result["total"] == 1
    assert result["workflow_runs"][0]["id"] == "workflow-1"
    assert result["workflow_runs"][0]["state_snapshot"]["billing_run_id"] == "billing-run-1"


def test_get_agent_workflow_run_returns_detail() -> None:
    db = _Db({"agent_workflow_runs": [_workflow_row(id="workflow-1")]})

    result = AgentsService(db, "tenant-1").get_agent_workflow_run("workflow-1")  # type: ignore[arg-type]

    assert result is not None
    assert result["workflow_name"] == "monthly_retainer_billing_run"
    assert result["current_step"] == "awaiting_billing_run_review"
    assert result["replay_pointer"] == "billing_runs/billing-run-1"


def test_get_agent_workflow_run_returns_none_for_missing_run() -> None:
    db = _Db({"agent_workflow_runs": []})

    assert (
        AgentsService(db, "tenant-1").get_agent_workflow_run("missing")  # type: ignore[arg-type]
        is None
    )


def test_build_agent_run_replay_returns_recorded_tool_manifest() -> None:
    db = _Db(
        {
            "agent_runs": [_run_row(id="run-1")],
            "agent_tool_invocations": [
                _tool_row(
                    id="tool-1",
                    agent_run_id="run-1",
                    created_at="2026-06-22T06:00:00Z",
                ),
                _tool_row(
                    id="tool-2",
                    agent_run_id="run-1",
                    tool_name="log_time_entry",
                    risk_class="write_low_risk",
                    input_snapshot={"project_id": "proj-1", "hours": "2.00"},
                    output_snapshot={"time_entry_id": "time-1"},
                    created_at="2026-06-22T06:00:01Z",
                ),
            ],
        }
    )

    replay = AgentsService(db, "tenant-1").build_agent_run_replay("run-1")  # type: ignore[arg-type]

    assert replay is not None
    assert replay["run_id"] == "run-1"
    assert replay["replay_mode"] == "recorded_snapshot"
    assert replay["can_reexecute"] is False
    assert replay["manifest_hash"]
    assert [step["tool_invocation_id"] for step in replay["steps"]] == ["tool-1", "tool-2"]
    assert replay["steps"][1]["input_snapshot"] == {"project_id": "proj-1", "hours": "2.00"}


def test_build_agent_run_replay_returns_none_for_missing_run() -> None:
    db = _Db({"agent_runs": [], "agent_tool_invocations": []})

    assert AgentsService(db, "tenant-1").build_agent_run_replay("missing") is None  # type: ignore[arg-type]


def test_build_agent_run_replay_validation_executes_read_only_current_code() -> None:
    tool_input = {"status": "active", "limit": 10}
    tool_output = {
        "count": 1,
        "engagements": [
            {
                "id": "eng-1",
                "name": "Meridian Advisory",
                "billing_arrangement": "time_and_materials",
                "currency": "USD",
                "total_value": "12000.00",
                "status": "active",
            }
        ],
    }
    db = _Db(
        {
            "agent_runs": [_run_row(id="run-1")],
            "agent_tool_invocations": [
                _tool_row(
                    id="tool-1",
                    agent_run_id="run-1",
                    tool_name="query_engagements",
                    risk_class="read_only",
                    input_hash=stable_payload_hash(tool_input),
                    input_snapshot=tool_input,
                    output_hash=stable_payload_hash(tool_output),
                    output_snapshot=tool_output,
                ),
            ],
            "engagements": [
                {
                    "id": "eng-1",
                    "tenant_id": "tenant-1",
                    "name": "Meridian Advisory",
                    "billing_arrangement": "time_and_materials",
                    "currency": "USD",
                    "total_value": "12000.00",
                    "status": "active",
                    "deleted_at": None,
                },
                {
                    "id": "eng-2",
                    "tenant_id": "tenant-1",
                    "name": "Archived",
                    "billing_arrangement": "fixed",
                    "currency": "USD",
                    "total_value": "5000.00",
                    "status": "completed",
                    "deleted_at": None,
                },
            ],
        }
    )

    validation = AgentsService(db, "tenant-1").build_agent_run_replay_validation("run-1")  # type: ignore[arg-type]

    assert validation is not None
    assert validation["validation_mode"] == "current_code_dry_run"
    assert validation["overall_status"] == "matched"
    assert validation["can_reexecute"] is True
    assert validation["reexecuted_step_count"] == 1
    assert validation["blocked_step_count"] == 0
    assert validation["steps"][0]["replay_status"] == "matched"
    assert validation["steps"][0]["input_hash_matches"] is True
    assert validation["steps"][0]["output_hash_matches"] is True
    assert validation["steps"][0]["current_output_snapshot"] == tool_output


def test_build_agent_run_replay_validation_plans_write_tools() -> None:
    db = _Db(
        {
            "agent_runs": [_run_row(id="run-1")],
            "agent_tool_invocations": [
                _tool_row(
                    id="tool-1",
                    agent_run_id="run-1",
                    tool_name="log_time_entry",
                    risk_class="write_low_risk",
                    external_tool_call_id=None,
                    input_snapshot={"project_id": "proj-1", "hours": "2.00"},
                    output_snapshot={"time_entry_id": "time-1"},
                ),
            ],
        }
    )

    validation = AgentsService(db, "tenant-1").build_agent_run_replay_validation("run-1")  # type: ignore[arg-type]

    assert validation is not None
    assert validation["overall_status"] == "planned"
    assert validation["can_reexecute"] is False
    assert validation["can_request_human_reexecution"] is True
    assert validation["reexecuted_step_count"] == 0
    assert validation["planned_step_count"] == 1
    assert validation["blocked_step_count"] == 0
    assert validation["steps"][0]["replay_status"] == "planned_for_human_reexecution"
    assert validation["steps"][0]["current_risk_class"] == "write_low_risk"
    plan = validation["steps"][0]["reexecution_plan"]
    assert plan["action_type"] == "copilot_log_time_entry"
    assert plan["approval_role"] == "manager"
    assert plan["external_side_effect"] is False
    assert plan["idempotency_key"]


def test_build_agent_run_replay_validation_flags_external_provider_plan() -> None:
    db = _Db(
        {
            "agent_runs": [_run_row(id="run-1", agent_name="collections_agent")],
            "agent_tool_invocations": [
                _tool_row(
                    id="tool-1",
                    agent_run_id="run-1",
                    tool_name="send_email",
                    risk_class="write_money_in",
                    external_tool_call_id="email-provider-call-1",
                    input_snapshot={"invoice_id": "invoice-1", "tone": "firm"},
                    output_snapshot={"message_id": "msg-1"},
                ),
            ],
        }
    )

    validation = AgentsService(db, "tenant-1").build_agent_run_replay_validation("run-1")  # type: ignore[arg-type]

    assert validation is not None
    assert validation["overall_status"] == "planned"
    plan = validation["steps"][0]["reexecution_plan"]
    assert validation["steps"][0]["replay_status"] == "planned_for_human_reexecution"
    assert plan["action_type"] == "send_email"
    assert plan["external_side_effect"] is True
    assert plan["external_tool_call_id"] == "email-provider-call-1"
    assert "provider" in plan["operator_action"]


def test_build_agent_run_replay_validation_returns_none_for_missing_run() -> None:
    db = _Db({"agent_runs": [], "agent_tool_invocations": []})

    assert (
        AgentsService(db, "tenant-1").build_agent_run_replay_validation("missing")  # type: ignore[arg-type]
        is None
    )


def test_list_eval_candidates_filters_by_agent_and_status() -> None:
    db = _Db(
        {
            "agent_eval_candidates": [
                _candidate_row(id="candidate-1", status="candidate"),
                _candidate_row(id="candidate-2", status="exported"),
                _candidate_row(
                    id="candidate-3",
                    agent_name="invoice_drafter_agent",
                    status="candidate",
                ),
                _candidate_row(id="other-tenant-candidate", tenant_id="tenant-2"),
            ],
        }
    )

    result = AgentsService(db, "tenant-1").list_eval_candidates(  # type: ignore[arg-type]
        agent_name="copilot_agent",
        status="candidate",
    )

    assert result["total"] == 1
    assert result["candidates"][0]["id"] == "candidate-1"
    assert result["candidates"][0]["eval_case_key"].startswith("copilot_agent:")
