"""Regression tests for Langfuse OpenAI instrumentation."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents import base

pytestmark = pytest.mark.unit


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"args": args, "kwargs": kwargs})
        return {"args": args, "kwargs": kwargs}


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeClient:
    def __init__(self, **kwargs: Any) -> None:
        self.init_kwargs = kwargs
        self.chat = _FakeChat()


def _configure_langfuse_settings(monkeypatch: pytest.MonkeyPatch, *, enabled: bool) -> None:
    monkeypatch.setattr(base.settings, "langfuse_tracing_enabled", enabled)
    monkeypatch.setattr(base.settings, "langfuse_public_key", "pk-test")
    monkeypatch.setattr(base.settings, "langfuse_secret_key", "sk-test")
    monkeypatch.setattr(base.settings, "langfuse_base_url", "https://langfuse.example.test")
    monkeypatch.setattr(base.settings, "langfuse_sample_rate", 0.5)
    monkeypatch.setattr(base.settings, "environment", "test")
    monkeypatch.setattr(base.settings, "openrouter_api_key", "or-test")
    monkeypatch.setattr(base.settings, "openrouter_base_url", "https://openrouter.example.test")


def test_langfuse_client_injects_trace_and_business_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_clients: list[_FakeClient] = []

    def _make_fake_client(**kwargs: Any) -> _FakeClient:
        client = _FakeClient(**kwargs)
        created_clients.append(client)
        return client

    _configure_langfuse_settings(monkeypatch, enabled=True)
    monkeypatch.setattr(base, "LangfuseAsyncOpenAI", _make_fake_client)
    monkeypatch.setattr(base, "LangfuseOpenAI", _make_fake_client)
    trace_token = base.trace_id_var.set("0123456789abcdef0123456789abcdef")
    tenant_token = base.tenant_id_var.set("tenant-from-context")

    try:
        client = base.make_async_llm_client(
            agent_name="vendor_invoice_agent",
            tenant_id="tenant-1",
            user_id="user-1",
            session_id="document-1",
            tags=["stage:extraction"],
            metadata={"document_id": "document-1"},
        )
        result = client.chat.completions.create(
            model="anthropic/claude-3.5-haiku",
            messages=[{"role": "user", "content": "Extract this invoice."}],
            metadata={"request_id": "request-1"},
        )
    finally:
        base.trace_id_var.reset(trace_token)
        base.tenant_id_var.reset(tenant_token)

    assert created_clients[0].init_kwargs == {
        "api_key": "or-test",
        "base_url": "https://openrouter.example.test",
    }
    kwargs = result["kwargs"]
    assert kwargs["name"] == "vendor_invoice_agent"
    assert kwargs["trace_id"] == "0123456789abcdef0123456789abcdef"
    assert kwargs["metadata"]["tenant_id"] == "tenant-1"
    assert kwargs["metadata"]["user_id"] == "user-1"
    assert kwargs["metadata"]["langfuse_user_id"] == "user-1"
    assert kwargs["metadata"]["langfuse_session_id"] == "document-1"
    assert kwargs["metadata"]["agent_name"] == "vendor_invoice_agent"
    assert kwargs["metadata"]["document_id"] == "document-1"
    assert kwargs["metadata"]["request_id"] == "request-1"
    assert "stage:extraction" in kwargs["metadata"]["langfuse_tags"]
    assert "agent:vendor_invoice_agent" in kwargs["metadata"]["langfuse_tags"]
    assert "tenant:tenant-1" in kwargs["metadata"]["langfuse_tags"]


def test_langfuse_disabled_uses_standard_openai_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_standard_clients: list[_FakeClient] = []

    def _make_standard_client(**kwargs: Any) -> _FakeClient:
        client = _FakeClient(**kwargs)
        created_standard_clients.append(client)
        return client

    _configure_langfuse_settings(monkeypatch, enabled=False)
    monkeypatch.setattr(base, "StandardAsyncOpenAI", _make_standard_client)
    monkeypatch.setattr(
        base,
        "LangfuseAsyncOpenAI",
        lambda **_: pytest.fail("Langfuse client should not be created"),
    )

    client = base.make_async_llm_client(agent_name="reporting_agent")

    assert isinstance(client, _FakeClient)
    assert created_standard_clients[0].init_kwargs == {
        "api_key": "or-test",
        "base_url": "https://openrouter.example.test",
    }
