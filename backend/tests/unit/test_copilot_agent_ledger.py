"""Tests for Copilot agent ledger integration."""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _CapturingLedger:
    instances: ClassVar[list[_CapturingLedger]] = []

    def __init__(self, db: object, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.start_kwargs: dict | None = None
        self.tool_calls: list[tuple[str | None, dict]] = []
        self.complete_calls: list[tuple[str | None, dict]] = []
        _CapturingLedger.instances.append(self)

    async def start_run(self, **kwargs: object) -> str:
        self.start_kwargs = kwargs
        return "run-1"

    async def record_tool_invocation(
        self,
        run_id: str | None,
        **kwargs: object,
    ) -> None:
        self.tool_calls.append((run_id, kwargs))

    async def complete_run(self, run_id: str | None, **kwargs: object) -> None:
        self.complete_calls.append((run_id, kwargs))


def _make_agent():
    from app.agents.copilot.graph import CopilotAgent, CopilotDeps

    with patch("app.agents.copilot.graph.make_async_llm_client", return_value=MagicMock()):
        return CopilotAgent(
            CopilotDeps(
                tenant_id="tenant-abc",
                user_id="00000000-0000-0000-0000-000000000001",
                db_client=object(),
            )
        )


@pytest.mark.asyncio
async def test_copilot_records_run_and_tool_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.copilot import graph

    _CapturingLedger.instances.clear()
    monkeypatch.setattr(graph, "AgentRunLedger", _CapturingLedger)
    trace_token = graph.trace_id_var.set("trace-123")

    try:
        agent = _make_agent()
        agent._stream_one_turn = AsyncMock(
            side_effect=[
                {
                    "frames": ['data: {"tool_start": "update_rate_card"}\n\n'],
                    "finish_reason": "tool_calls",
                    "text": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "name": "update_rate_card",
                            "arguments": '{"employee_name": "Sarah", "rate": 425}',
                        }
                    ],
                    "model": "model-a",
                },
                {
                    "frames": ['data: {"delta": "Updated."}\n\n'],
                    "finish_reason": "stop",
                    "text": "Updated.",
                    "tool_calls": [],
                    "model": "model-b",
                },
            ]
        )
        agent._execute_tool = AsyncMock(return_value={"updated": True})

        frames = [
            frame
            async for frame in agent._run_agentic_loop(
                "Update Sarah's card 4242 4242 4242 4242 rate to 425",
                thread_id="thread-1",
            )
        ]
    finally:
        graph.trace_id_var.reset(trace_token)

    ledger = _CapturingLedger.instances[0]
    assert ledger.start_kwargs is not None
    assert ledger.start_kwargs["agent_name"] == "copilot_agent"
    assert ledger.start_kwargs["trigger_type"] == "chat"
    assert ledger.start_kwargs["trace_id"] == "trace-123"
    assert ledger.start_kwargs["replay_pointer"] == "chat_threads/thread-1"
    assert "[REDACTED-CARD]" in ledger.start_kwargs["input_payload"]["message"]

    assert len(ledger.tool_calls) == 1
    run_id, tool_call = ledger.tool_calls[0]
    assert run_id == "run-1"
    assert tool_call["tool_name"] == "update_rate_card"
    assert tool_call["risk_class"] == "write_money_in"
    assert tool_call["status"] == "succeeded"
    assert tool_call["external_tool_call_id"] == "call-1"
    assert tool_call["input_payload"] == {"employee_name": "Sarah", "rate": 425}
    assert tool_call["output_payload"] == {"updated": True}

    assert ledger.complete_calls == [
        (
            "run-1",
            {
                "status": "succeeded",
                "output_payload": {
                    "finish_reason": "stop",
                    "assistant_text": "Updated.",
                },
                "model_version": "model-b",
            },
        )
    ]
    assert any('"tool_result": "update_rate_card"' in frame for frame in frames)
    assert any('"done": true' in frame for frame in frames)


@pytest.mark.asyncio
async def test_copilot_records_failed_tool_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.copilot import graph

    _CapturingLedger.instances.clear()
    monkeypatch.setattr(graph, "AgentRunLedger", _CapturingLedger)

    agent = _make_agent()
    agent._stream_one_turn = AsyncMock(
        side_effect=[
            {
                "frames": [],
                "finish_reason": "tool_calls",
                "text": "",
                "tool_calls": [
                    {
                        "id": "call-2",
                        "name": "query_engagements",
                        "arguments": '{"limit": 3}',
                    }
                ],
                "model": "model-a",
            },
            {
                "frames": [],
                "finish_reason": "stop",
                "text": "No data found.",
                "tool_calls": [],
                "model": "model-a",
            },
        ]
    )
    agent._execute_tool = AsyncMock(return_value={"error": "database unavailable"})

    async for _ in agent._run_agentic_loop("Show engagements"):
        pass

    ledger = _CapturingLedger.instances[0]
    _, tool_call = ledger.tool_calls[0]
    assert tool_call["tool_name"] == "query_engagements"
    assert tool_call["risk_class"] == "read_only"
    assert tool_call["status"] == "failed"
    assert tool_call["error_message"] == "database unavailable"
