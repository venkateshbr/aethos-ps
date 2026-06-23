"""Unit tests for copilot action tools: log_time_entry and update_rate_card.

All tests are pure-Python with no I/O — no DB, no LLM API calls. The DB client
is replaced by a lightweight stub that records calls and returns canned data.

TDD: these tests are written BEFORE the implementation so they must be red first.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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
        for method in ("select", "eq", "is_", "limit", "order", "gte", "lte", "neq"):
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
