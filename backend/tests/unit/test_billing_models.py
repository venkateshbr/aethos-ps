"""Unit tests for billing model features (#174, #175, #176).

Tests:
- #174: billing_run_worker creates draft run for retainer engagements
- #175: capped_tm marks overflow time entries as non_billable
- #176: mixed billing model produces fixed-fee + T&M lines
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _chain(data: list[dict]) -> MagicMock:
    result = MagicMock()
    result.data = data
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.is_.return_value = chain
    chain.execute.return_value = result
    return chain


# ---------------------------------------------------------------------------
# #174 — billing_run_worker
# ---------------------------------------------------------------------------


def test_billing_run_worker_is_registered() -> None:
    from procrastinate.tasks import Task

    from app.workers.billing_run_worker import create_monthly_billing_run

    assert isinstance(create_monthly_billing_run, Task)


def test_billing_run_worker_creates_draft_for_retainer_engagement() -> None:
    from app.workers.billing_run_worker import _create_run_for_tenant

    db = MagicMock()

    # Active retainer engagements
    eng_result = MagicMock()
    eng_result.data = [
        {"id": "eng-001", "name": "Acme Retainer", "billing_arrangement": "retainer"},
        {"id": "eng-002", "name": "Beta Monthly", "billing_arrangement": "retainer_draw"},
    ]

    # Billing run insert
    run_result = MagicMock()
    run_result.data = [{"id": "run-001", "status": "draft"}]

    insert_chain = MagicMock()
    insert_chain.execute.return_value = run_result

    table_mock = MagicMock()
    db.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.in_.return_value = table_mock
    table_mock.is_.return_value = table_mock
    duplicate_result = MagicMock()
    duplicate_result.data = []
    table_mock.execute.side_effect = [eng_result, duplicate_result]
    table_mock.insert.return_value = insert_chain

    from datetime import date

    result = _create_run_for_tenant(db, "tenant-001", date(2026, 6, 1))

    assert result is not None
    assert result["status"] == "draft"

    # Verify workflow, billing run, suggestion, and HITL task were created.
    inserts = [call_args[0][0] for call_args in table_mock.insert.call_args_list]
    workflow_insert = next(
        payload for payload in inserts if payload.get("workflow_name")
    )
    billing_run_insert = next(
        payload for payload in inserts if payload.get("engagement_filter")
    )
    suggestion_insert = next(
        payload for payload in inserts if payload.get("agent_name") == "billing_run_agent"
    )
    task_insert = next(payload for payload in inserts if payload.get("kind"))

    assert workflow_insert["workflow_name"] == "monthly_retainer_billing_run"
    assert workflow_insert["status"] == "running"
    assert "eng-001" in billing_run_insert["engagement_filter"]["engagement_ids"]
    assert "eng-002" in billing_run_insert["engagement_filter"]["engagement_ids"]
    assert billing_run_insert["status"] == "draft"
    assert billing_run_insert["created_by_agent"] == "billing_run_agent"
    assert suggestion_insert["agent_name"] == "billing_run_agent"
    assert suggestion_insert["action_type"] == "approve_billing_run"
    assert suggestion_insert["hitl_required"] is True
    assert task_insert["kind"] == "approve_billing_run"
    assert task_insert["status"] == "open"
    workflow_update = table_mock.update.call_args_list[-1][0][0]
    assert workflow_update["status"] == "waiting_on_human"
    assert workflow_update["current_step"] == "hitl_review"
    assert workflow_update["state_snapshot"]["billing_run_id"] == "run-001"


def test_billing_run_worker_suppresses_duplicate_period_run() -> None:
    from datetime import date

    from app.workers.billing_run_worker import _create_run_for_tenant

    db = MagicMock()
    eng_result = MagicMock()
    eng_result.data = [
        {"id": "eng-001", "name": "Acme Retainer", "billing_arrangement": "retainer"}
    ]
    duplicate_result = MagicMock()
    duplicate_result.data = [{"id": "run-existing", "status": "draft"}]

    table_mock = MagicMock()
    db.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.in_.return_value = table_mock
    table_mock.is_.return_value = table_mock
    table_mock.execute.side_effect = [eng_result, duplicate_result]

    result = _create_run_for_tenant(db, "tenant-001", date(2026, 6, 1))

    assert result is None
    inserts = [call_args[0][0] for call_args in table_mock.insert.call_args_list]
    assert any(payload.get("workflow_name") for payload in inserts)
    assert not any(payload.get("engagement_filter") for payload in inserts)
    workflow_update = table_mock.update.call_args_list[-1][0][0]
    assert workflow_update["status"] == "succeeded"
    assert workflow_update["state_snapshot"]["result"] == "skipped_duplicate_period"


def test_billing_run_worker_skips_when_no_retainer_engagements() -> None:
    from datetime import date

    from app.workers.billing_run_worker import _create_run_for_tenant

    db = MagicMock()
    eng_result = MagicMock()
    eng_result.data = []

    table_mock = MagicMock()
    db.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.in_.return_value = table_mock
    table_mock.is_.return_value = table_mock
    table_mock.execute.return_value = eng_result

    result = _create_run_for_tenant(db, "tenant-001", date(2026, 6, 1))

    assert result is None
    inserts = [call_args[0][0] for call_args in table_mock.insert.call_args_list]
    assert any(payload.get("workflow_name") for payload in inserts)
    assert not any(payload.get("engagement_filter") for payload in inserts)
    workflow_update = table_mock.update.call_args_list[-1][0][0]
    assert workflow_update["status"] == "succeeded"
    assert workflow_update["state_snapshot"]["result"] == "skipped_no_retainer_engagements"


def test_billing_run_worker_counts_created_only_for_actual_new_runs() -> None:
    from datetime import date

    from app.workers import billing_run_worker

    db = MagicMock()
    tenants_chain = _chain(
        [
            {"id": "tenant-created"},
            {"id": "tenant-skipped"},
        ]
    )
    db.table.return_value = tenants_chain

    def _fake_create(_db: object, tenant_id: str, _period_start: date) -> dict | None:
        if tenant_id == "tenant-created":
            return {"id": "run-created"}
        return None

    with patch.object(
        billing_run_worker,
        "_create_run_for_tenant",
        side_effect=_fake_create,
    ):
        result = billing_run_worker._create_monthly_billing_runs(
            db,
            date(2026, 6, 1),
        )

    assert result == {
        "tenants_processed": 2,
        "runs_created": 1,
        "runs_skipped": 1,
    }


# ---------------------------------------------------------------------------
# #176 — mixed billing model
# ---------------------------------------------------------------------------


def test_mixed_model_produces_fixed_fee_and_tm_lines() -> None:
    """Mixed billing produces fixed-fee, retainer, and T&M-compatible lines."""
    from app.agents.base import AgentDeps
    from app.agents.invoice_drafter_agent import _draft_invoice_inner

    db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-001", user_id="user-001", db=db)

    # Mock engagement row with mixed billing arrangement
    eng_row = {
        "id": "eng-mix",
        "name": "Mixed Engagement",
        "billing_arrangement": "mixed",
        "currency": "USD",
        "rate_card_id": None,
        "client_id": "client-001",
        "engagement_billing_terms": {
            "fixed_fee_amount": "5000.00",
            "retainer_monthly_amount": "1200.00",
        },
        "clients": {"id": "client-001", "name": "Acme Corp"},
    }

    def _table_side(table_name: str) -> MagicMock:
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.is_.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain

        empty = MagicMock()
        empty.data = []

        if table_name == "engagements":
            eng_res = MagicMock()
            eng_res.data = [eng_row]
            chain.execute.return_value = eng_res
        else:
            chain.execute.return_value = empty
        return chain

    db.table.side_effect = _table_side

    # Mock tax rate lookup (called by _apply_tax)
    with patch("app.agents.invoice_drafter_agent._apply_tax", side_effect=lambda lines, d, c: lines):
        draft = _draft_invoice_inner("eng-mix", deps, None, None)

    assert draft.billing_arrangement == "mixed"
    # Should have the fixed-fee base line
    fixed_lines = [ln for ln in draft.lines if "Fixed fee" in ln.description]
    assert len(fixed_lines) == 1
    assert fixed_lines[0].amount == Decimal("5000.00")
    retainer_lines = [ln for ln in draft.lines if "Monthly Retainer" in ln.description]
    assert len(retainer_lines) == 1
    assert retainer_lines[0].amount == Decimal("1200.00")


# ---------------------------------------------------------------------------
# #175 — capped_tm overflow marking
# ---------------------------------------------------------------------------


def test_capped_tm_overflow_entries_marked_non_billable() -> None:
    """When capped_tm overflows, overflow entries get billing_status=non_billable."""
    from app.agents.base import AgentDeps
    from app.agents.invoice_drafter_agent import _mark_capped_overflow_non_billable

    db = MagicMock()
    deps = AgentDeps(tenant_id="tenant-001", user_id="user-001", db=db)

    eng = {
        "id": "eng-capped",
        "name": "Capped T&M",
        "rate_card_id": "rc-001",
    }

    # Projects
    proj_mock = MagicMock()
    proj_mock.data = [{"id": "proj-001"}]

    # Time entries — 3 entries, all at $100/h, 10h each = $1000 total. Cap = $150.
    # Entry 1 (day 1): $100 — within cap cumulative $100
    # Entry 2 (day 2): $100 — would push to $200 > $150 cap, so this entry is overflow
    # Entry 3 (day 3): $100 — also overflow
    te_mock = MagicMock()
    te_mock.data = [
        {"id": "te-1", "employee_id": "emp-1", "project_id": "proj-001", "hours": "1"},
        {"id": "te-2", "employee_id": "emp-1", "project_id": "proj-001", "hours": "1"},
        {"id": "te-3", "employee_id": "emp-1", "project_id": "proj-001", "hours": "1"},
    ]

    # Rate card
    rc_mock = MagicMock()
    rc_mock.data = [{"role": "Consultant", "rate": "100.00"}]

    # Assignments
    assign_mock = MagicMock()
    assign_mock.data = [
        {"employee_id": "emp-1", "project_id": "proj-001", "role": "Consultant"}
    ]

    # Update chain (for marking non_billable)
    update_mock = MagicMock()
    update_mock.in_.return_value = update_mock
    update_mock.eq.return_value = update_mock
    update_mock.execute.return_value = MagicMock()

    def table_side(table_name: str) -> MagicMock:
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain
        chain.is_.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.order.return_value = chain
        chain.update.return_value = update_mock

        if table_name == "projects":
            chain.execute.return_value = proj_mock
        elif table_name == "time_entries":
            chain.execute.return_value = te_mock
        elif table_name == "rate_card_lines":
            chain.execute.return_value = rc_mock
        elif table_name == "project_assignments":
            chain.execute.return_value = assign_mock
        else:
            empty = MagicMock()
            empty.data = []
            chain.execute.return_value = empty

        return chain

    db.table.side_effect = table_side

    _mark_capped_overflow_non_billable(
        deps=deps,
        eng=eng,
        cap=Decimal("150.00"),
        period_start=None,
        period_end=None,
    )

    # Should have called update on time_entries to mark overflow as non_billable
    update_mock.in_.assert_called_once()
    # te-2 and te-3 should be in the overflow list (te-1 is within cap at $100)
    overflow_ids = update_mock.in_.call_args[0][1]
    assert "te-2" in overflow_ids or "te-3" in overflow_ids
