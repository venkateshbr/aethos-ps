"""Unit tests for copilot action tools: log_time_entry and update_rate_card.

All tests are pure-Python with no I/O — no DB, no LLM API calls. The DB client
is replaced by a lightweight stub that records calls and returns canned data.

TDD: these tests are written BEFORE the implementation so they must be red first.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Test helpers — lightweight DB stub
# ---------------------------------------------------------------------------

def _make_db(tables: dict[str, list[dict]]) -> MagicMock:
    """Return a mock Supabase client pre-loaded with table data.

    Supports the fluent query-builder chain used in the copilot tools:
      db.table(name).select(...).eq(...).eq(...).limit(...).execute()
    and insert / update chains.
    """

    def _build_query_mock(rows: list[dict]) -> MagicMock:
        """Build a chainable query mock that returns ``rows`` on .execute()."""
        result = MagicMock()
        result.data = rows

        q = MagicMock()
        # All chain methods return the same mock
        for method in (
            "select",
            "eq",
            "in_",
            "is_",
            "lt",
            "limit",
            "order",
            "gte",
            "lte",
            "neq",
        ):
            setattr(q, method, MagicMock(return_value=q))
        q.execute = MagicMock(return_value=result)
        return q

    db = MagicMock()
    inserts: dict[str, list] = {}
    updates: dict[str, list] = {}

    def _table(name: str) -> MagicMock:
        rows = list(tables.get(name, []))
        q = _build_query_mock(rows)

        def _insert(payload: dict) -> MagicMock:
            inserts.setdefault(name, []).append(payload)
            inserted = {**payload, "id": f"new-{name}-id"}
            r = MagicMock()
            r.data = [inserted]
            m = _build_query_mock([inserted])
            m.execute = MagicMock(return_value=r)
            return m

        def _update(patch_data: dict) -> MagicMock:
            updates.setdefault(name, []).append(patch_data)
            r = MagicMock()
            r.data = [patch_data]
            m = _build_query_mock([patch_data])
            m.execute = MagicMock(return_value=r)
            return m

        q.insert = MagicMock(side_effect=_insert)
        q.update = MagicMock(side_effect=_update)
        return q

    db.table = MagicMock(side_effect=_table)
    db._inserts = inserts
    db._updates = updates
    return db


def _make_agent(tables: dict[str, list[dict]]):
    """Create a CopilotAgent with a stubbed DB and no real LLM client."""
    from app.agents.copilot.graph import CopilotAgent, CopilotDeps

    db = _make_db(tables)

    with patch("app.agents.copilot.graph.make_async_llm_client", return_value=MagicMock()):
        agent = CopilotAgent(CopilotDeps(
            tenant_id="tenant-abc",
            user_id="user-001",
            db_client=db,
        ))

    return agent, db


# ---------------------------------------------------------------------------
# log_time_entry — tool dispatch via CopilotAgent._execute_tool
# ---------------------------------------------------------------------------


class TestLogTimeEntry:
    """Tests for the log_time_entry copilot action tool."""

    def _projects(self) -> list[dict]:
        return [
            {"id": "proj-1", "name": "Nexus Capital — CFO Advisory", "engagement_id": "eng-1"},
            {"id": "proj-2", "name": "Brightwater Restructure", "engagement_id": "eng-2"},
        ]

    def _employees(self) -> list[dict]:
        return [
            {
                "id": "emp-1",
                "user_id": "user-001",
                "default_bill_rate": "350.00",
                "default_bill_rate_currency": "GBP",
            }
        ]

    def test_log_time_entry_tool_registered(self):
        """log_time_entry must be present in CopilotAgent.TOOLS."""
        from app.agents.copilot.graph import CopilotAgent

        tool_names = [t["name"] for t in CopilotAgent.TOOLS]
        assert "log_time_entry" in tool_names, (
            f"log_time_entry missing from TOOLS. Found: {tool_names}"
        )

    def test_log_time_entry_tool_schema(self):
        """log_time_entry input_schema must declare project_name and hours as required."""
        from app.agents.copilot.graph import CopilotAgent

        tool = next((t for t in CopilotAgent.TOOLS if t["name"] == "log_time_entry"), None)
        assert tool is not None, "log_time_entry tool not found"
        schema = tool["input_schema"]
        assert "project_name" in schema["properties"]
        assert "hours" in schema["properties"]
        required = schema.get("required", [])
        assert "project_name" in required
        assert "hours" in required

    @pytest.mark.asyncio
    async def test_log_time_entry_fuzzy_match(self):
        """'Nexus CFO' fuzzy-matches 'Nexus Capital — CFO Advisory'."""
        agent, _db = _make_agent({
            "projects": self._projects(),
            "employees": self._employees(),
        })

        result = await agent._execute_tool(
            "log_time_entry",
            {
                "project_name": "Nexus CFO",
                "hours": 3.0,
                "date": "2026-06-21",
                "description": "Strategy session",
                "billable": True,
            },
        )

        assert "error" not in result, f"Expected success, got error: {result}"
        assert result["logged"] is True
        assert "Nexus" in result["project"]
        assert result["hours"] == 3.0
        assert result["date"] == "2026-06-21"
        assert result["billable"] is True

    @pytest.mark.asyncio
    async def test_log_time_entry_no_project(self):
        """Returns helpful error when project name doesn't match anything."""
        agent, _db = _make_agent({
            "projects": self._projects(),
            "employees": self._employees(),
        })

        result = await agent._execute_tool(
            "log_time_entry",
            {
                "project_name": "XYZNOTREAL_PROJECT_12345",
                "hours": 2.0,
            },
        )

        assert "error" in result
        # Error should list available projects
        assert "Nexus" in result["error"] or "Brightwater" in result["error"]

    @pytest.mark.asyncio
    async def test_log_time_entry_default_date_is_today(self):
        """When date is omitted, entry is logged for today."""
        import datetime

        agent, _db = _make_agent({
            "projects": self._projects(),
            "employees": self._employees(),
        })

        result = await agent._execute_tool(
            "log_time_entry",
            {
                "project_name": "Brightwater",
                "hours": 1.5,
            },
        )

        if "error" in result:
            pytest.fail(f"Expected success, got: {result}")
        today = datetime.date.today().isoformat()
        assert result["date"] == today

    @pytest.mark.asyncio
    async def test_log_time_entry_billable_value_calculation(self):
        """Billable value = hours * bill_rate, serialised as Decimal string."""
        agent, _db = _make_agent({
            "projects": self._projects(),
            "employees": self._employees(),
        })

        result = await agent._execute_tool(
            "log_time_entry",
            {
                "project_name": "Nexus CFO",  # fuzzy-matches "Nexus Capital — CFO Advisory"
                "hours": 4.0,
                "billable": True,
            },
        )

        if "error" in result:
            pytest.fail(f"Expected success, got: {result}")
        # 4 hours x GBP 350/hr = 1400.00
        assert result["billable_value"] == "1400.00"

    @pytest.mark.asyncio
    async def test_log_time_entry_non_billable_value_is_zero(self):
        """Non-billable entries should return billable_value = '0.00'."""
        agent, _db = _make_agent({
            "projects": self._projects(),
            "employees": self._employees(),
        })

        result = await agent._execute_tool(
            "log_time_entry",
            {
                "project_name": "Brightwater Restructure",  # exact match
                "hours": 2.0,
                "billable": False,
            },
        )

        if "error" in result:
            pytest.fail(f"Expected success, got: {result}")
        assert result["billable_value"] == "0.00"

    @pytest.mark.asyncio
    async def test_log_time_entry_no_active_projects(self):
        """Returns error when tenant has no active projects."""
        agent, _db = _make_agent({
            "projects": [],
            "employees": self._employees(),
        })

        result = await agent._execute_tool(
            "log_time_entry",
            {"project_name": "Nexus", "hours": 1.0},
        )

        assert "error" in result
        assert "project" in result["error"].lower()


# ---------------------------------------------------------------------------
# update_rate_card — tool dispatch via CopilotAgent._execute_tool
# ---------------------------------------------------------------------------


class TestUpdateRateCard:
    """Tests for the update_rate_card copilot action tool."""

    def _employees(self) -> list[dict]:
        return [
            {
                "id": "emp-1",
                "first_name": "Marcus",
                "last_name": "Winters",
                "default_bill_rate": "320.00",
                "default_bill_rate_currency": "GBP",
            },
            {
                "id": "emp-2",
                "first_name": "Alice",
                "last_name": "Chen",
                "default_bill_rate": "280.00",
                "default_bill_rate_currency": "GBP",
            },
        ]

    def _engagements(self) -> list[dict]:
        return [
            {"id": "eng-1", "name": "Nexus Capital — CFO Advisory"},
        ]

    def test_update_rate_card_tool_registered(self):
        """update_rate_card must be present in CopilotAgent.TOOLS."""
        from app.agents.copilot.graph import CopilotAgent

        tool_names = [t["name"] for t in CopilotAgent.TOOLS]
        assert "update_rate_card" in tool_names, (
            f"update_rate_card missing from TOOLS. Found: {tool_names}"
        )

    def test_update_rate_card_tool_schema(self):
        """update_rate_card input_schema must declare employee_name and rate as required."""
        from app.agents.copilot.graph import CopilotAgent

        tool = next((t for t in CopilotAgent.TOOLS if t["name"] == "update_rate_card"), None)
        assert tool is not None, "update_rate_card tool not found"
        schema = tool["input_schema"]
        assert "employee_name" in schema["properties"]
        assert "rate" in schema["properties"]
        required = schema.get("required", [])
        assert "employee_name" in required
        assert "rate" in required

    @pytest.mark.asyncio
    async def test_update_rate_card_default(self):
        """Updates employee default_bill_rate when no engagement_name given."""
        agent, _db = _make_agent({
            "employees": self._employees(),
            "engagements": self._engagements(),
        })

        result = await agent._execute_tool(
            "update_rate_card",
            {
                "employee_name": "Marcus",
                "rate": 380.0,
                "currency": "GBP",
            },
        )

        assert "error" not in result, f"Expected success, got: {result}"
        assert result["updated"] is True
        assert "Marcus" in result["employee"]
        assert "380" in result["new_default_rate"]
        assert "GBP" in result["new_default_rate"]

    @pytest.mark.asyncio
    async def test_update_rate_card_engagement(self):
        """Upserts rate_card_lines entry when engagement_name is given."""
        agent, _db = _make_agent({
            "employees": self._employees(),
            "engagements": self._engagements(),
            "rate_card_lines": [],
        })

        result = await agent._execute_tool(
            "update_rate_card",
            {
                "employee_name": "Marcus",
                "engagement_name": "Nexus CFO",
                "rate": 380.0,
                "currency": "GBP",
            },
        )

        assert "error" not in result, f"Expected success, got: {result}"
        assert result["updated"] is True
        assert "Marcus" in result["employee"]
        assert "Nexus" in result["engagement"]
        assert "380" in result["new_rate"]

    @pytest.mark.asyncio
    async def test_update_rate_card_employee_not_found(self):
        """Returns helpful error when employee name doesn't match."""
        agent, _db = _make_agent({
            "employees": self._employees(),
        })

        result = await agent._execute_tool(
            "update_rate_card",
            {
                "employee_name": "NOBODY_XYZ",
                "rate": 300.0,
            },
        )

        assert "error" in result
        assert (
            "NOBODY_XYZ" in result["error"]
            or "Marcus" in result["error"]
            or "Alice" in result["error"]
        )

    @pytest.mark.asyncio
    async def test_update_rate_card_engagement_not_found(self):
        """Returns error when engagement name doesn't match."""
        agent, _db = _make_agent({
            "employees": self._employees(),
            "engagements": self._engagements(),
        })

        result = await agent._execute_tool(
            "update_rate_card",
            {
                "employee_name": "Marcus",
                "engagement_name": "NOSUCHENGAGEMENT_9999",
                "rate": 300.0,
            },
        )

        assert "error" in result
        assert (
            "NOSUCHENGAGEMENT_9999" in result["error"]
            or "engagement" in result["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_update_rate_card_fuzzy_employee_match(self):
        """'Marcus Winters' fuzzy-matches by full name."""
        agent, _db = _make_agent({
            "employees": self._employees(),
        })

        result = await agent._execute_tool(
            "update_rate_card",
            {
                "employee_name": "Marcus Winters",
                "rate": 400.0,
                "currency": "USD",
            },
        )

        assert "error" not in result, f"Expected success, got: {result}"
        assert result["updated"] is True


# ---------------------------------------------------------------------------
# System prompt coverage
# ---------------------------------------------------------------------------


def test_system_prompt_mentions_log_time():
    """System prompt must mention time-logging capability."""
    from app.agents.copilot.graph import CopilotAgent

    prompt = CopilotAgent.SYSTEM_PROMPT.lower()
    assert "log" in prompt or "time" in prompt or "hours" in prompt, (
        "System prompt must mention time logging so the LLM knows to use log_time_entry"
    )


def test_system_prompt_mentions_rate_card():
    """System prompt must mention rate card / billing rate capability."""
    from app.agents.copilot.graph import CopilotAgent

    prompt = CopilotAgent.SYSTEM_PROMPT.lower()
    assert "rate" in prompt or "billing" in prompt, (
        "System prompt must mention rate updating so the LLM knows to use update_rate_card"
    )


def test_draft_invoice_tool_registered():
    """draft_invoice must be present in CopilotAgent.TOOLS."""
    from app.agents.copilot.graph import CopilotAgent

    tool_names = [t["name"] for t in CopilotAgent.TOOLS]
    assert "draft_invoice" in tool_names, (
        f"draft_invoice missing from TOOLS. Found: {tool_names}"
    )


def test_draft_invoice_tool_schema():
    """draft_invoice schema must identify engagement and billing period inputs."""
    from app.agents.copilot.graph import CopilotAgent

    tool = next((t for t in CopilotAgent.TOOLS if t["name"] == "draft_invoice"), None)
    assert tool is not None, "draft_invoice tool not found"
    schema = tool["input_schema"]
    assert "engagement_name" in schema["properties"]
    assert "engagement_id" in schema["properties"]
    assert "period_start" in schema["properties"]
    assert "period_end" in schema["properties"]


def test_system_prompt_mentions_invoice_drafting():
    """System prompt must mention invoice drafting so the LLM uses the tool."""
    from app.agents.copilot.graph import CopilotAgent

    prompt = CopilotAgent.SYSTEM_PROMPT.lower()
    assert "draft" in prompt and "invoice" in prompt
    assert "inbox" in prompt


def test_finance_ops_tools_registered():
    """Copilot must expose finance-ops orchestration tools."""
    from app.agents.copilot.graph import CopilotAgent

    tool_names = {t["name"] for t in CopilotAgent.TOOLS}
    assert "run_finance_ops_check" in tool_names
    assert "create_finance_ops_action_plan" in tool_names
    assert "draft_collection_reminders" in tool_names
    assert "propose_bill_payment_batch" in tool_names
    assert "prepare_month_end_close" in tool_names
    assert "generate_financial_statement_package" in tool_names


def test_finance_ops_tool_schemas():
    """Finance-ops tools must declare the expected period/payment inputs."""
    from app.agents.copilot.graph import CopilotAgent

    tools = {t["name"]: t for t in CopilotAgent.TOOLS}
    command_center_schema = tools["run_finance_ops_check"]["input_schema"]
    action_plan_schema = tools["create_finance_ops_action_plan"]["input_schema"]
    collections_schema = tools["draft_collection_reminders"]["input_schema"]
    bill_pay_schema = tools["propose_bill_payment_batch"]["input_schema"]
    close_schema = tools["prepare_month_end_close"]["input_schema"]
    statements_schema = tools["generate_financial_statement_package"]["input_schema"]

    assert "period" in command_center_schema["properties"]
    assert "limit" in command_center_schema["properties"]
    assert command_center_schema["required"] == []
    assert "period" in action_plan_schema["properties"]
    assert "limit" in action_plan_schema["properties"]
    assert action_plan_schema["required"] == []
    assert "minimum_days_overdue" in collections_schema["properties"]
    assert "tone" in collections_schema["properties"]
    assert collections_schema["properties"]["tone"]["enum"] == [
        "auto",
        "gentle",
        "firm",
        "final",
    ]
    assert collections_schema["required"] == []
    assert "due_within_days" in bill_pay_schema["properties"]
    assert "bank_account_label" in bill_pay_schema["properties"]
    assert close_schema["required"] == ["period"]
    assert "period" in close_schema["properties"]
    assert statements_schema["required"] == ["period_start"]
    assert "period_end" in statements_schema["properties"]


def test_system_prompt_mentions_finance_ops_tools():
    """System prompt must steer finance-ops requests to the new tools."""
    from app.agents.copilot.graph import CopilotAgent

    prompt = CopilotAgent.SYSTEM_PROMPT.lower()
    assert "finance ops check" in prompt or "command center" in prompt
    assert "action plan" in prompt
    assert "recommended work items" in prompt
    assert "collections reminders" in prompt
    assert "bill pay" in prompt or "payment batch" in prompt
    assert "month-end close" in prompt
    assert "financial statement" in prompt


def test_execute_tool_dispatches_log_time_entry():
    """_execute_tool source must contain a branch for log_time_entry."""
    import inspect

    from app.agents.copilot.graph import CopilotAgent

    source = inspect.getsource(CopilotAgent._execute_tool)
    assert "log_time_entry" in source, "_execute_tool must dispatch log_time_entry"


def test_execute_tool_dispatches_update_rate_card():
    """_execute_tool source must contain a branch for update_rate_card."""
    import inspect

    from app.agents.copilot.graph import CopilotAgent

    source = inspect.getsource(CopilotAgent._execute_tool)
    assert "update_rate_card" in source, "_execute_tool must dispatch update_rate_card"


def test_execute_tool_dispatches_draft_invoice():
    """_execute_tool source must contain a branch for draft_invoice."""
    import inspect

    from app.agents.copilot.graph import CopilotAgent

    source = inspect.getsource(CopilotAgent._execute_tool)
    assert "draft_invoice" in source, "_execute_tool must dispatch draft_invoice"


def test_execute_tool_dispatches_finance_ops_tools():
    """_execute_tool source must contain finance-ops branches."""
    import inspect

    from app.agents.copilot.graph import CopilotAgent

    source = inspect.getsource(CopilotAgent._execute_tool)
    assert "run_finance_ops_check" in source
    assert "create_finance_ops_action_plan" in source
    assert "draft_collection_reminders" in source
    assert "propose_bill_payment_batch" in source
    assert "prepare_month_end_close" in source
    assert "generate_financial_statement_package" in source


@pytest.mark.asyncio
async def test_finance_ops_check_execute_builds_command_center(monkeypatch):
    """Daily command-center synthesis covers finance domains and approval actions."""
    agent, _db = _make_agent({})

    class _ReportsService:
        def __init__(self, _db, _tenant_id):
            pass

        def ar_aging(self):
            return {
                "0_30": "700.00",
                "31_60": "200.00",
                "61_90": "0.00",
                "over_90": "100.00",
                "total": "1000.00",
            }

        def ap_aging(self):
            return {
                "0_30": "300.00",
                "31_60": "0.00",
                "61_90": "0.00",
                "over_90": "0.00",
                "total": "300.00",
            }

        def wip(self):
            return [
                {
                    "project_id": "proj-1",
                    "project_name": "Nexus CFO",
                    "unbilled_hours": "3.00",
                    "wip_value": "750.00",
                }
            ]

        def action_queue(self, **_kwargs):
            return [
                {
                    "id": "queue-1",
                    "role": "finance_manager",
                    "source_type": "ar_aging",
                    "priority": "high",
                    "entity_type": "receivables",
                    "entity_id": "ar-aging",
                    "entity_name": "Accounts receivable",
                    "summary": "Open AR total is 1000.00.",
                    "recommended_action": "Review overdue invoices.",
                    "route_hint": "/app/reports",
                }
            ]

    class _CloseStatus:
        def as_dict(self):
            return {
                "period": "2026-06",
                "status": "blocked",
                "ready_to_lock": False,
                "locked": False,
                "lock_blockers": ["close_reviews"],
                "pending_reviews": [{"id": "review-1"}],
                "checklist": [
                    {
                        "code": "close_reviews",
                        "status": "pending",
                        "summary": "1 close review is pending.",
                    }
                ],
            }

    class _CloseStatusService:
        def __init__(self, _db, _tenant_id):
            pass

        def get_status(self, period):
            assert period == "2026-06"
            return _CloseStatus()

    class _AgentsService:
        def __init__(self, _db, _tenant_id):
            pass

        def list_agent_runs(self, **_kwargs):
            return {
                "runs": [
                    {
                        "id": "run-1",
                        "agent_name": "copilot_agent",
                        "status": "succeeded",
                        "created_at": "2026-06-24T10:00:00Z",
                        "tool_count": 2,
                        "failed_tool_count": 0,
                    }
                ],
                "total": 1,
            }

        def list_agent_workflow_runs(self, **_kwargs):
            return {
                "workflow_runs": [
                    {
                        "id": "wf-1",
                        "workflow_name": "month_end_close",
                        "status": "running",
                        "current_step": "review",
                        "created_at": "2026-06-24T10:05:00Z",
                    }
                ],
                "total": 1,
            }

    monkeypatch.setattr("app.services.reports_service.ReportsService", _ReportsService)
    monkeypatch.setattr(
        "app.services.close_status_service.CloseStatusService",
        _CloseStatusService,
    )
    monkeypatch.setattr("app.services.agents_service.AgentsService", _AgentsService)

    result = await agent._execute_tool(
        "run_finance_ops_check",
        {"period": "2026-06", "limit": 5},
    )

    assert result["finance_ops_check"] is True
    assert result["period"] == "2026-06"
    findings = result["read_only_findings"]
    assert set(findings) >= {
        "ar",
        "ap",
        "wip",
        "close_readiness",
        "action_queue",
        "agent_workflows",
    }
    assert findings["ar"]["total"] == "1000.00"
    assert findings["ap"]["status"] == "attention"
    assert findings["wip"]["total"] == "750.00"
    assert findings["close_readiness"]["lock_blocker_count"] == 1
    assert findings["action_queue"]["item_count"] == 1
    assert findings["agent_workflows"]["recent_run_count"] == 1
    assert any(
        action["suggested_tool"] == "propose_bill_payment_batch"
        and action["requires_inbox_approval"] is True
        for action in result["recommended_actions"]
    )
    assert any(
        action["suggested_tool"] == "draft_invoice"
        and action["requires_inbox_approval"] is True
        for action in result["recommended_actions"]
    )


@pytest.mark.asyncio
async def test_finance_ops_check_reports_explicit_empty_states(monkeypatch):
    """Empty domains are returned as empty states instead of invented values."""
    agent, _db = _make_agent({})

    class _ReportsService:
        def __init__(self, _db, _tenant_id):
            pass

        def ar_aging(self):
            return {"0_30": "0", "31_60": "0", "61_90": "0", "over_90": "0", "total": "0"}

        def ap_aging(self):
            return {"0_30": "0", "31_60": "0", "61_90": "0", "over_90": "0", "total": "0"}

        def wip(self):
            return []

        def action_queue(self, **_kwargs):
            return []

    class _CloseStatus:
        def as_dict(self):
            return {
                "period": "2026-06",
                "status": "ready",
                "ready_to_lock": True,
                "locked": False,
                "lock_blockers": [],
                "pending_reviews": [],
                "checklist": [],
            }

    class _CloseStatusService:
        def __init__(self, _db, _tenant_id):
            pass

        def get_status(self, _period):
            return _CloseStatus()

    class _AgentsService:
        def __init__(self, _db, _tenant_id):
            pass

        def list_agent_runs(self, **_kwargs):
            return {"runs": [], "total": 0}

        def list_agent_workflow_runs(self, **_kwargs):
            return {"workflow_runs": [], "total": 0}

    monkeypatch.setattr("app.services.reports_service.ReportsService", _ReportsService)
    monkeypatch.setattr(
        "app.services.close_status_service.CloseStatusService",
        _CloseStatusService,
    )
    monkeypatch.setattr("app.services.agents_service.AgentsService", _AgentsService)

    result = await agent._execute_tool(
        "run_finance_ops_check",
        {"period": "2026-06"},
    )

    findings = result["read_only_findings"]
    assert findings["ar"]["status"] == "empty"
    assert findings["ap"]["status"] == "empty"
    assert findings["wip"]["status"] == "empty"
    assert findings["action_queue"]["status"] == "empty"
    assert findings["agent_workflows"]["status"] == "empty"
    assert {state["domain"] for state in result["empty_states"]} >= {
        "ar",
        "ap",
        "wip",
        "action_queue",
        "agent_workflows",
    }
    assert result["recommended_actions"] == []


@pytest.mark.asyncio
async def test_finance_ops_action_plan_builds_reviewable_work_items():
    """Action plan converts command-center recommendations into Inbox-ready items."""
    agent, _db = _make_agent({})
    agent._run_finance_ops_check = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "finance_ops_check": True,
            "period": "2026-06",
            "generated_at": "2026-06-24T10:00:00+00:00",
            "read_only_findings": {
                "ar": {"total": "1000.00", "over_90": "250.00"},
                "ap": {"total": "0", "over_90": "0"},
                "wip": {"total": "750.00", "project_count": 2},
                "close_readiness": {
                    "period": "2026-06",
                    "status": "blocked",
                    "lock_blocker_count": 1,
                    "pending_review_count": 2,
                },
            },
            "recommended_actions": [
                {
                    "domain": "ar",
                    "action": "Draft collections reminders for Inbox approval.",
                    "requires_inbox_approval": True,
                    "suggested_agent": "collections_agent",
                    "suggested_tool": "send_email",
                    "risk_class": "write_money_in",
                    "review_path": "/app/inbox",
                },
                {
                    "domain": "wip",
                    "action": "Draft customer invoices for billable WIP.",
                    "requires_inbox_approval": True,
                    "suggested_agent": "copilot_agent",
                    "suggested_tool": "draft_invoice",
                    "risk_class": "write_money_in",
                    "review_path": "/app/inbox",
                },
                {
                    "domain": "close",
                    "action": "Prepare month-end close review package.",
                    "requires_inbox_approval": True,
                    "suggested_agent": "copilot_agent",
                    "suggested_tool": "prepare_month_end_close",
                    "risk_class": "accounting",
                    "review_path": "/app/inbox",
                },
            ],
            "empty_states": [{"domain": "ap", "message": "No open AP balance was found."}],
            "review_paths": ["/app/copilot", "/app/reports", "/app/inbox", "/app/settings"],
        }
    )

    result = await agent._execute_tool(
        "create_finance_ops_action_plan",
        {"period": "2026-06", "limit": 5},
    )

    assert result["finance_ops_action_plan"] is True
    assert result["period"] == "2026-06"
    assert result["status"] == "ready_for_review"
    assert result["action_count"] == 3
    assert result["requires_inbox_approval_count"] == 3
    assert result["preview"] == {
        "period": "2026-06",
        "status": "ready_for_review",
        "action_count": 3,
        "requires_inbox_approval_count": 3,
        "domains": "ar, wip, close",
    }
    assert result["empty_states"][0]["domain"] == "ap"
    first_item = result["action_items"][0]
    assert first_item["domain"] == "ar"
    assert first_item["suggested_tool"] == "send_email"
    assert first_item["risk_class"] == "write_money_in"
    assert first_item["requires_inbox_approval"] is True
    assert "AR aging total" in first_item["rationale"]
    close_item = result["action_items"][2]
    assert close_item["domain"] == "close"
    assert "Close readiness" in close_item["rationale"]
    assert "separately gated by Inbox" in result["approval_effect"]
    agent._run_finance_ops_check.assert_awaited_once_with(
        {"period": "2026-06", "limit": 5}
    )


@pytest.mark.asyncio
async def test_collection_reminders_execute_routes_send_email_to_inbox():
    """Copilot collections sweep drafts reminders and creates Inbox send tasks."""
    due_date = (date.today() - timedelta(days=45)).isoformat()
    agent, db = _make_agent(
        {
            "invoices": [
                {
                    "id": "inv-1",
                    "tenant_id": "tenant-abc",
                    "invoice_number": "INV-OVERDUE-1",
                    "total": "1250.00",
                    "currency": "USD",
                    "due_date": due_date,
                    "client_id": "client-1",
                    "stripe_payment_link_url": "",
                    "status": "sent",
                }
            ],
            "clients": [
                {
                    "id": "client-1",
                    "tenant_id": "tenant-abc",
                    "name": "Acme Finance",
                    "billing_email": "collections@example.com",
                    "billing_address": {},
                }
            ],
            "tenants": [{"id": "tenant-abc", "name": "Aethos Test Firm"}],
            "collections_policies": [],
            "agent_suggestions": [],
        }
    )

    result = await agent._execute_tool(
        "draft_collection_reminders",
        {"minimum_days_overdue": 30, "limit": 5},
    )

    assert result["collections_reminders_drafted"] is True
    assert result["requires_review"] is True
    assert result["target_agent"] == "collections_agent"
    assert result["action_type"] == "send_email"
    assert result["created_review_tasks"] == 1
    assert result["drafts"][0]["invoice_number"] == "INV-OVERDUE-1"
    assert "collections@example.com" not in str(result["drafts"][0])

    suggestion = db._inserts["agent_suggestions"][0]
    assert suggestion["agent_name"] == "collections_agent"
    assert suggestion["action_type"] == "send_email"
    assert suggestion["related_entity_type"] == "invoice"
    assert suggestion["related_entity_id"] == "inv-1"
    assert suggestion["output_snapshot"]["client_email"] == "collections@example.com"
    assert suggestion["output_snapshot"]["tone"] == "final"
    assert suggestion["hitl_required"] is True

    task = db._inserts["hitl_tasks"][0]
    assert task["kind"] == "send_email"
    assert task["status"] == "open"
    assert task["payload"]["invoice_number"] == "INV-OVERDUE-1"
    assert task["payload"]["client_email"] == "collections@example.com"
    assert task["payload"]["body_preview"]

    tool_names = [
        row["tool_name"] for row in db._inserts["agent_tool_invocations"]
    ]
    assert tool_names == [
        "find_overdue_invoices",
        "draft_collection_email",
        "send_email",
    ]
    assert db._inserts["agent_tool_invocations"][-1]["status"] == "skipped"


@pytest.mark.asyncio
async def test_draft_invoice_execute_persists_generated_payload():
    """Direct execution drafts, then persists the reviewed invoice payload."""
    agent, _db = _make_agent({})
    draft_payload = {
        "invoice_draft": {
            "engagement_id": "eng-1",
            "engagement_name": "Northstar Managed Accounting",
            "client_id": "client-1",
            "currency": "USD",
            "issue_date": "2026-06-30",
            "notes": "June invoice",
            "lines": [
                {
                    "description": "Monthly retainer",
                    "quantity": "1",
                    "unit_price": "12000.00",
                }
            ],
        },
        "preview": {"total": "12000.00"},
    }
    agent._build_invoice_draft_payload = AsyncMock(return_value=draft_payload)  # type: ignore[method-assign]
    agent._persist_invoice_draft_payload = AsyncMock(  # type: ignore[method-assign]
        return_value={"invoice_created": True, "invoice_id": "inv-1"}
    )

    result = await agent._execute_tool(
        "draft_invoice",
        {"engagement_name": "Northstar", "period_end": "2026-06-30"},
    )

    assert result == {"invoice_created": True, "invoice_id": "inv-1"}
    agent._build_invoice_draft_payload.assert_awaited_once_with(
        {"engagement_name": "Northstar", "period_end": "2026-06-30"}
    )
    agent._persist_invoice_draft_payload.assert_awaited_once_with(
        draft_payload["invoice_draft"]
    )


@pytest.mark.asyncio
async def test_bill_pay_execute_builds_review_payload():
    """Direct bill-pay execution returns a proposal payload, not a payment batch."""
    agent, _db = _make_agent({})
    agent._build_bill_payment_batch_payload = AsyncMock(  # type: ignore[method-assign]
        return_value={"proposed_bill_ids": ["bill-1"], "total_amount": "900.00"}
    )

    result = await agent._execute_tool(
        "propose_bill_payment_batch",
        {"due_within_days": 14},
    )

    assert result == {"proposed_bill_ids": ["bill-1"], "total_amount": "900.00"}
    agent._build_bill_payment_batch_payload.assert_awaited_once_with(
        {"due_within_days": 14}
    )


@pytest.mark.asyncio
async def test_prepare_month_end_close_execute_runs_workflow():
    """Direct close execution delegates to the close workflow helper."""
    agent, _db = _make_agent({})
    agent._prepare_month_end_close = AsyncMock(  # type: ignore[method-assign]
        return_value={"close_prepared": True, "period": "2026-06"}
    )

    result = await agent._execute_tool("prepare_month_end_close", {"period": "2026-06"})

    assert result == {"close_prepared": True, "period": "2026-06"}
    agent._prepare_month_end_close.assert_awaited_once_with({"period": "2026-06"})


@pytest.mark.asyncio
async def test_financial_statement_package_execute_generates_summary():
    """Direct statement-package execution returns the read-only summary."""
    agent, _db = _make_agent({})
    agent._generate_financial_statement_package = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "generated_statement_package": True,
            "period_start": "2026-06",
            "period_end": "2026-06",
        }
    )

    result = await agent._execute_tool(
        "generate_financial_statement_package",
        {"period_start": "2026-06"},
    )

    assert result["generated_statement_package"] is True
    agent._generate_financial_statement_package.assert_awaited_once_with(
        {"period_start": "2026-06"}
    )


@pytest.mark.asyncio
async def test_financial_statement_package_includes_close_commentary(
    monkeypatch: pytest.MonkeyPatch,
):
    """Statement packages include close readiness and evidence-backed commentary."""
    agent, _db = _make_agent({})

    class _StatementPack:
        def model_dump(self, *, mode: str = "python") -> dict:
            assert mode == "json"
            return {
                "as_of_period": "2026-06",
                "trial_balance": {"is_balanced": True},
                "balance_sheet": {
                    "total_assets": "1000.00",
                    "total_liabilities": "300.00",
                    "total_equity": "700.00",
                    "is_balanced": True,
                },
                "income_statement": {
                    "total_revenue": "1200.00",
                    "total_expenses": "800.00",
                    "net_income": "400.00",
                    "revenue_lines": [{"account": "4000"}],
                    "expense_lines": [{"account": "5000"}],
                },
                "cash_flow": {
                    "net_change_in_cash": "50.00",
                    "ending_cash": "250.00",
                },
                "retained_earnings_roll_forward": {
                    "ending_retained_earnings": "700.00",
                },
                "tax_summary": {
                    "tax_label": "GST",
                    "ledger_net_tax_payable": "30.00",
                },
            }

    def _statutory_pack(self, *, period_start: str, period_end: str) -> _StatementPack:
        assert period_start == "2026-06"
        assert period_end == "2026-06"
        return _StatementPack()

    def _close_package(self, period: str) -> dict:
        assert period == "2026-06"
        return {
            "close_status": {
                "status": "blocked",
                "ready_to_lock": False,
                "locked": False,
                "lock_blockers": ["close_reviews"],
                "pending_reviews": [{"id": "review-1"}],
                "incomplete_tasks": [],
                "overrides": [],
            },
            "readiness_evidence": {
                "approvals": {"status": "blocked", "pending_review_count": 1}
            },
            "variance_commentary": [
                {
                    "code": "net_income_variance",
                    "severity": "watch",
                    "summary": "Net income increased by 100.00.",
                    "evidence": {"source": "period_gl_summary"},
                }
            ],
        }

    monkeypatch.setattr(
        "app.services.reports_service.ReportsService.statutory_reporting_pack",
        _statutory_pack,
    )
    monkeypatch.setattr(
        "app.services.close_package_service.ClosePackageService.build_package",
        _close_package,
    )

    result = await agent._generate_financial_statement_package({"period_start": "2026-06"})

    assert result["generated_statement_package"] is True
    assert result["close_prerequisites"]["status"] == "blocked"
    assert result["close_prerequisites"]["lock_blockers"] == ["close_reviews"]
    assert result["close_prerequisites"]["warnings"]
    assert result["management_commentary"][0]["evidence"]["source"] == "period_gl_summary"
