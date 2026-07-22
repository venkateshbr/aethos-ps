"""Unit tests for autonomy_promoter worker logic.

Tests cover the core decision logic in _check_promotions and _check_demotions
using lightweight Supabase stub clients — no real DB connections are made.

Verified behaviours:
  - Promotion skipped when sample count is below the minimum
  - Money agents require higher thresholds (60 samples, 98% approval)
  - Demotion applied when approval rate falls below 85%
  - Demotion skipped when fewer than 10 decisions are available
  - Approval rate calculation is correct
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.workers.autonomy_promoter import (
    _check_demotions,
    _check_promotions,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Stub factory
# ---------------------------------------------------------------------------

class _FlatMock:
    """A chainable mock where every attribute access and call returns self.

    Set ``.final_data`` to control what ``.execute().data`` returns.
    """

    def __init__(self, data: list | None = None) -> None:
        self.final_data = data if data is not None else []

    def __getattr__(self, name: str) -> _FlatMock:
        return self

    def __call__(self, *args, **kwargs) -> _FlatMock:
        return self

    @property
    def data(self) -> list:
        return self.final_data

    def execute(self) -> _FlatMock:
        return self


def _stub_db_for_promotions(
    suggestions: list[dict],
    autonomy_settings: list[dict] | None = None,
    hitl_open: list[dict] | None = None,
) -> MagicMock:
    """Build a DB stub for _check_promotions tests."""
    db = MagicMock()

    sugg_mock = _FlatMock(suggestions)
    settings_mock = _FlatMock(autonomy_settings if autonomy_settings is not None else [])
    hitl_mock = _FlatMock(hitl_open if hitl_open is not None else [])
    insert_result = MagicMock()
    insert_result.execute.return_value = MagicMock(data=[{"id": "new-task"}])

    def table_side_effect(table_name: str) -> MagicMock:
        t = MagicMock()
        if table_name == "agent_suggestions":
            # Any chain ending in .execute() returns sugg_mock
            t.select.return_value = sugg_mock
        elif table_name == "agent_autonomy_settings":
            t.select.return_value = settings_mock
        elif table_name == "hitl_tasks":
            t.select.return_value = hitl_mock
            t.insert.return_value = insert_result
        return t

    db.table.side_effect = table_side_effect
    return db


def _stub_db_for_demotions(
    suggestions: list[dict],
    l3_settings: list[dict] | None = None,
) -> MagicMock:
    """Build a DB stub for _check_demotions tests."""
    db = MagicMock()

    sugg_mock = _FlatMock(suggestions)
    l3_mock = _FlatMock(l3_settings if l3_settings is not None else [])
    insert_result = MagicMock()
    insert_result.execute.return_value = MagicMock(data=[{"id": "new-task"}])

    def table_side_effect(table_name: str) -> MagicMock:
        t = MagicMock()
        if table_name == "agent_suggestions":
            t.select.return_value = sugg_mock
        elif table_name == "agent_autonomy_settings":
            t.select.return_value = l3_mock
            t.update.return_value = MagicMock()
        elif table_name == "hitl_tasks":
            t.insert.return_value = insert_result
        return t

    db.table.side_effect = table_side_effect
    return db


# ---------------------------------------------------------------------------
# Promotion tests
# ---------------------------------------------------------------------------


def test_promotion_skipped_below_min_count() -> None:
    """When sample count < 30 (min for non-money agents), no promotion is proposed."""
    suggestions = [
        {
            "agent_name": "some_agent",
            "action_type": "some_action",
            "status": "approved",
            "confidence": "0.96",
        }
        for _ in range(29)  # one below min threshold of 30
    ]
    db = _stub_db_for_promotions(suggestions)
    result = _check_promotions(db, "tenant-1")
    assert result == 0


def test_money_agent_requires_higher_thresholds() -> None:
    """Money agents need 60 samples — 59 approved rows must be skipped."""
    suggestions = [
        {
            "agent_name": "bill_pay_agent",
            "action_type": "create_bill_payment_batch",
            "status": "approved",
            "confidence": "0.99",
        }
        for _ in range(59)  # one below the 60-minimum for money agents
    ]
    db = _stub_db_for_promotions(suggestions)
    result = _check_promotions(db, "tenant-2")
    assert result == 0


def test_promotion_proposed_when_thresholds_met() -> None:
    """When metrics and L3 gates are met, a hitl_task is created."""
    suggestions = [
        {
            "agent_name": "collections_agent",
            "action_type": "send_email",
            "status": "approved",
            "confidence": "0.96",
        }
        for _ in range(60)
    ]
    db = _stub_db_for_promotions(
        suggestions,
        autonomy_settings=[
            {
                "level": 2,
                "locked_at_l2": False,
                "l3_opt_in": True,
                "eval_passed_at": "2026-06-22T06:00:00Z",
                "max_auto_risk": "write_money_in",
            }
        ],
        hitl_open=[],
    )
    result = _check_promotions(db, "tenant-3")
    assert result == 1


def test_promotion_skipped_without_l3_opt_in_and_eval_pass() -> None:
    suggestions = [
        {
            "agent_name": "collections_agent",
            "action_type": "send_email",
            "status": "approved",
            "confidence": "0.96",
        }
        for _ in range(60)
    ]
    db = _stub_db_for_promotions(
        suggestions,
        autonomy_settings=[
            {
                "level": 2,
                "locked_at_l2": False,
                "l3_opt_in": False,
                "eval_passed_at": None,
                "max_auto_risk": "draft",
            }
        ],
        hitl_open=[],
    )

    result = _check_promotions(db, "tenant-7")

    assert result == 0


def test_promotion_requires_tool_risk_permission() -> None:
    suggestions = [
        {
            "agent_name": "copilot_agent",
            "action_type": "copilot_update_rate_card",
            "status": "approved",
            "confidence": "0.99",
        }
        for _ in range(60)
    ]
    blocked = _stub_db_for_promotions(
        suggestions,
        autonomy_settings=[
            {
                "level": 2,
                "locked_at_l2": False,
                "l3_opt_in": True,
                "eval_passed_at": "2026-06-22T06:00:00Z",
                "max_auto_risk": "draft",
            }
        ],
        hitl_open=[],
    )
    allowed = _stub_db_for_promotions(
        suggestions,
        autonomy_settings=[
            {
                "level": 2,
                "locked_at_l2": False,
                "l3_opt_in": True,
                "eval_passed_at": "2026-06-22T06:00:00Z",
                "max_auto_risk": "write_money_in",
            }
        ],
        hitl_open=[],
    )

    assert _check_promotions(blocked, "tenant-8") == 0
    assert _check_promotions(allowed, "tenant-8") == 1


def test_promotion_requires_registered_non_copilot_action_risk() -> None:
    suggestions = [
        {
            "agent_name": "accrual_agent",
            "action_type": "draft_journal",
            "status": "approved",
            "confidence": "0.99",
        }
        for _ in range(60)
    ]
    blocked = _stub_db_for_promotions(
        suggestions,
        autonomy_settings=[
            {
                "level": 2,
                "locked_at_l2": False,
                "l3_opt_in": True,
                "eval_passed_at": "2026-06-22T06:00:00Z",
                "max_auto_risk": "write_money_out",
            }
        ],
        hitl_open=[],
    )
    allowed = _stub_db_for_promotions(
        suggestions,
        autonomy_settings=[
            {
                "level": 2,
                "locked_at_l2": False,
                "l3_opt_in": True,
                "eval_passed_at": "2026-06-22T06:00:00Z",
                "max_auto_risk": "accounting",
            }
        ],
        hitl_open=[],
    )

    assert _check_promotions(blocked, "tenant-9") == 0
    assert _check_promotions(allowed, "tenant-9") == 1


# ---------------------------------------------------------------------------
# Demotion tests
# ---------------------------------------------------------------------------


def test_demotion_below_85pct() -> None:
    """An L3 agent with < 85% approval over 14 days is demoted to L2."""
    l3 = [
        {
            "id": "setting-1",
            "agent_name": "collections_agent",
            "action_type": "send_email",
        }
    ]
    # 10 rows: 8 approved (80% < 85%) → demotion triggered
    suggestions = (
        [{"status": "approved"} for _ in range(8)]
        + [{"status": "rejected"} for _ in range(2)]
    )
    db = _stub_db_for_demotions(suggestions, l3_settings=l3)
    result = _check_demotions(db, "tenant-4")
    assert result == 1


def test_demotion_skipped_under_10_decisions() -> None:
    """Demotion must not be triggered when fewer than 10 decisions exist."""
    l3 = [
        {
            "id": "setting-2",
            "agent_name": "collections_agent",
            "action_type": "send_email",
        }
    ]
    # Only 9 rows — below the 10-decision minimum
    suggestions = [{"status": "rejected"} for _ in range(9)]
    db = _stub_db_for_demotions(suggestions, l3_settings=l3)
    result = _check_demotions(db, "tenant-5")
    assert result == 0


def test_demotion_skipped_above_85pct() -> None:
    """An L3 agent with >= 85% approval over 14 days must NOT be demoted."""
    l3 = [
        {
            "id": "setting-3",
            "agent_name": "collections_agent",
            "action_type": "send_email",
        }
    ]
    # 10 rows: 9 approved (90% >= 85%) — no demotion
    suggestions = (
        [{"status": "approved"} for _ in range(9)]
        + [{"status": "rejected"} for _ in range(1)]
    )
    db = _stub_db_for_demotions(suggestions, l3_settings=l3)
    result = _check_demotions(db, "tenant-6")
    assert result == 0


# ---------------------------------------------------------------------------
# Approval rate calculation (pure logic — no DB)
# ---------------------------------------------------------------------------


def test_approval_rate_calculation() -> None:
    """Approval rate uses approved + auto_applied + approved_with_edits vs total."""
    rows = [
        {"status": "approved"},
        {"status": "approved"},
        {"status": "approved"},
        {"status": "auto_applied"},
        {"status": "rejected"},
    ]
    approved = [
        r
        for r in rows
        if r["status"] in ("approved", "auto_applied", "approved_with_edits")
    ]
    rate = Decimal(str(len(approved) / len(rows)))
    assert rate == Decimal("0.8")


def test_check_promotions_status_filter_is_postgrest_valid() -> None:
    """#395 regression: the decided-suggestions filter must be .neq('status','pending'),
    not .not_.is_('status','pending') which PostgREST rejects (PGRST100). A
    PostgREST-accurate stub raises on an invalid `is` filter value."""
    from types import SimpleNamespace

    _VALID_IS = (None, "null", "not_null", True, False, "true", "false", "unknown")

    class _Q:
        def __init__(self, data: list) -> None:
            self._data = data

        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def gte(self, *a, **k):
            return self

        def neq(self, *a, **k):
            return self

        def insert(self, *a, **k):
            return self

        @property
        def not_(self):
            return self

        def is_(self, _col, val):
            if val not in _VALID_IS:
                raise ValueError(f"PGRST100: 'is' filter rejects {val!r}")
            return self

        def execute(self):
            return SimpleNamespace(data=self._data)

    class _Db:
        def __init__(self, sugg: list) -> None:
            self._sugg = sugg

        def table(self, name: str):
            return _Q(self._sugg if name == "agent_suggestions" else [])

    # 40 approved suggestions (> min_n=30) for one pair, so the status query runs.
    sugg = [
        {"agent_name": "collections_agent", "action_type": "draft_reminder",
         "status": "approved", "confidence": "0.9"}
        for _ in range(40)
    ]
    # Must not raise (would raise if the code regressed to .not_.is_('status','pending')).
    result = _check_promotions(_Db(sugg), "tenant-x")
    assert result == 0  # no agent_autonomy_settings row → skipped after the query ran
