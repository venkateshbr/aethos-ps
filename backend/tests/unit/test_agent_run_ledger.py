"""Unit tests for the agent run ledger module."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agents.tool_registry import (
    action_type_for_tool,
    risk_class_for_action,
    risk_class_for_tool,
)
from app.services.agent_run_ledger import (
    AgentRunLedger,
    safe_snapshot,
    stable_payload_hash,
)


class _FakeTable:
    def __init__(self, db: _FakeDb, name: str) -> None:
        self.db = db
        self.name = name
        self.operation: str | None = None
        self.payload: dict | None = None
        self.filters: list[tuple[str, object]] = []

    def insert(self, payload: dict) -> _FakeTable:
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload: dict) -> _FakeTable:
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, column: str, value: object) -> _FakeTable:
        self.filters.append((column, value))
        return self

    def execute(self) -> SimpleNamespace:
        if self.db.should_fail:
            raise RuntimeError("database unavailable")
        assert self.payload is not None
        if self.operation == "insert":
            row = {**self.payload, "id": f"{self.name}-{len(self.db.inserts) + 1}"}
            self.db.inserts.setdefault(self.name, []).append(row)
            return SimpleNamespace(data=[row])
        if self.operation == "update":
            self.db.updates.setdefault(self.name, []).append(
                {"patch": self.payload, "filters": list(self.filters)}
            )
            return SimpleNamespace(data=[self.payload])
        raise AssertionError(f"unexpected operation: {self.operation}")


class _FakeDb:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.inserts: dict[str, list[dict]] = {}
        self.updates: dict[str, list[dict]] = {}

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


def test_stable_payload_hash_is_order_independent() -> None:
    left = {"b": [2, 3], "a": Decimal("1.20")}
    right = {"a": Decimal("1.20"), "b": [2, 3]}

    assert stable_payload_hash(left) == stable_payload_hash(right)


def test_safe_snapshot_masks_basic_pii_and_serializes_decimal() -> None:
    snapshot = safe_snapshot(
        {
            "email": "sarah@example.com",
            "card": "4242 4242 4242 4242",
            "amount": Decimal("12.30"),
        }
    )

    assert snapshot["email"] == "[REDACTED]@example.com"
    assert snapshot["card"] == "[REDACTED-CARD]"
    assert snapshot["amount"] == "12.30"


def test_tool_registry_classifies_copilot_tools() -> None:
    assert risk_class_for_tool("copilot_agent", "query_engagements") == "read_only"
    assert risk_class_for_tool("copilot_agent", "run_finance_ops_check") == "read_only"
    assert risk_class_for_tool("copilot_agent", "draft_collection_reminders") == (
        "write_money_in"
    )
    assert risk_class_for_tool("copilot_agent", "log_time_entry") == "write_low_risk"
    assert risk_class_for_tool("copilot_agent", "update_rate_card") == "write_money_in"
    assert risk_class_for_tool("copilot_agent", "prepare_month_end_close") == "accounting"
    assert risk_class_for_tool("copilot_agent", "unknown_tool") == "draft"
    assert risk_class_for_action("copilot_agent", "default") == "accounting"


def test_tool_registry_classifies_persisted_agent_actions() -> None:
    assert action_type_for_tool("collections_agent", "send_email") == "send_email"
    assert risk_class_for_action("collections_agent", "send_email") == "write_money_in"
    assert risk_class_for_action("collections_agent", "find_overdue_invoices") == (
        "read_only"
    )
    assert risk_class_for_action("collections_agent", "draft_collection_email") == "draft"
    assert action_type_for_tool("time_entry_agent", "send_time_entry_reminder") == (
        "send_time_entry_reminder"
    )
    assert risk_class_for_action("time_entry_agent", "send_time_entry_reminder") == (
        "write_low_risk"
    )
    assert risk_class_for_action("billing_run_agent", "approve_billing_run") == ("write_money_in")
    assert risk_class_for_action("bill_pay_agent", "create_bill_payment_batch") == (
        "write_money_out"
    )
    assert risk_class_for_action("accrual_agent", "draft_journal") == "accounting"
    assert risk_class_for_action("prepaid_amortization_agent", "draft_journal") == ("accounting")
    assert risk_class_for_action("recurring_journal_agent", "draft_journal") == ("accounting")
    assert risk_class_for_action("revenue_recognition_agent", "draft_journal") == ("accounting")
    assert risk_class_for_action("project_health_agent", "BUDGET_BURN_WARNING") == ("draft")
    assert risk_class_for_action("intelligence_agent", "EXPENSE_SPIKE") == "draft"
    assert risk_class_for_action("unknown_agent", "unknown_action") == "draft"


@pytest.mark.asyncio
async def test_agent_run_ledger_writes_run_tool_and_completion_rows() -> None:
    db = _FakeDb()
    ledger = AgentRunLedger(db, tenant_id="tenant-1")
    user_id = "00000000-0000-0000-0000-000000000001"

    run_id = await ledger.start_run(
        agent_name="copilot_agent",
        trigger_type="chat",
        user_id=user_id,
        input_payload={"message": "Show WIP"},
        prompt_version="cop-v1",
        trace_id="trace-1",
        replay_pointer="chat_threads/thread-1",
    )

    assert run_id == "agent_runs-1"
    run_row = db.inserts["agent_runs"][0]
    assert run_row["tenant_id"] == "tenant-1"
    assert run_row["agent_name"] == "copilot_agent"
    assert run_row["user_id"] == user_id
    assert run_row["input_hash"] == stable_payload_hash({"message": "Show WIP"})
    assert run_row["replay_pointer"] == "chat_threads/thread-1"

    await ledger.record_tool_invocation(
        run_id,
        tool_name="get_wip",
        risk_class="read_only",
        input_payload={"engagement_id": "eng-1"},
        output_payload={"total": Decimal("25.50")},
        status="succeeded",
        duration_ms=8,
        external_tool_call_id="call-1",
    )

    tool_row = db.inserts["agent_tool_invocations"][0]
    assert tool_row["agent_run_id"] == run_id
    assert tool_row["risk_class"] == "read_only"
    assert tool_row["input_hash"] == stable_payload_hash({"engagement_id": "eng-1"})
    assert tool_row["output_snapshot"] == {"total": "25.50"}

    await ledger.complete_run(
        run_id,
        status="succeeded",
        output_payload={"finish_reason": "stop"},
        model_version="openrouter/test-model",
    )

    completion = db.updates["agent_runs"][0]
    assert completion["filters"] == [("id", run_id)]
    assert completion["patch"]["status"] == "succeeded"
    assert completion["patch"]["model_version"] == "openrouter/test-model"
    assert completion["patch"]["output_hash"] == stable_payload_hash({"finish_reason": "stop"})


@pytest.mark.asyncio
async def test_agent_run_ledger_is_best_effort_on_database_failures() -> None:
    ledger = AgentRunLedger(_FakeDb(should_fail=True), tenant_id="tenant-1")

    run_id = await ledger.start_run(
        agent_name="copilot_agent",
        trigger_type="chat",
        input_payload={"message": "Show WIP"},
    )
    await ledger.record_tool_invocation(
        "run-1",
        tool_name="get_wip",
        risk_class="read_only",
        input_payload={},
        output_payload={},
        status="succeeded",
    )
    await ledger.complete_run("run-1", status="failed", error_message="boom")

    assert run_id is None
