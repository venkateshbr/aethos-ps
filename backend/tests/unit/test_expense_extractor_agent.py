"""Deterministic contracts for the expense extractor's LLM response boundary."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents import expense_extractor_agent
from app.agents.base import AgentDeps

pytestmark = pytest.mark.unit


def _completion(content: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        model="test/structured-model",
        usage=None,
    )


def _deps() -> AgentDeps:
    return AgentDeps(
        tenant_id="00000000-0000-0000-0000-000000000000",
        user_id=None,
        db=None,  # type: ignore[arg-type] -- model-chain lookup is stubbed below.
    )


def _stub_provider(
    monkeypatch: pytest.MonkeyPatch,
    *,
    content: str | None,
) -> AsyncMock:
    create = AsyncMock(return_value=_completion(content))
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    )
    monkeypatch.setattr(
        expense_extractor_agent,
        "make_async_llm_client",
        lambda **_kwargs: client,
    )
    monkeypatch.setattr(
        expense_extractor_agent,
        "resolve_model_chain",
        AsyncMock(return_value=["test/structured-model"]),
    )
    return create


@pytest.mark.asyncio
async def test_valid_provider_json_returns_typed_expense(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create = _stub_provider(
        monkeypatch,
        content=(
            '{"vendor":"ACME CAB COMPANY","amount":49.00,"currency":"USD",'
            '"category":"transport","expense_date":"2026-05-20",'
            '"description":"Airport taxi","confidence":0.98,'
            '"suspected_injection":false}'
        ),
    )

    result = await expense_extractor_agent.run_expense_extractor_agent(
        document_id="deterministic-valid-json",
        deps=_deps(),
        document_bytes=b"synthetic receipt",
        mime_type="text/plain",
    )

    assert result.vendor == "ACME CAB COMPANY"
    assert str(result.amount) == "49.0"
    assert result.category == "transport"
    assert result.confidence == 0.98
    assert result.suspected_injection is False
    create.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [None, "", "{}", "not JSON"])
async def test_empty_or_malformed_provider_reply_returns_safe_sentinel(
    monkeypatch: pytest.MonkeyPatch,
    content: str | None,
) -> None:
    _stub_provider(monkeypatch, content=content)

    result = await expense_extractor_agent.run_expense_extractor_agent(
        document_id="deterministic-empty-json",
        deps=_deps(),
        document_bytes=b"synthetic receipt",
        mime_type="text/plain",
    )

    assert result.vendor == "unknown"
    assert result.amount == 0
    assert result.currency == "USD"
    assert result.category == "other"
    assert result.description == "(extraction failed — LLM returned no usable JSON)"
    assert result.confidence == 0.0
    assert result.suspected_injection is True
