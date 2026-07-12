"""Regression tests for Langfuse OpenAI instrumentation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import langfuse
import pytest

from app.agents import base

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_tracked_langfuse_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(base, "_langfuse_client", None)


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


class _FakeTelemetryClient:
    def __init__(self) -> None:
        self.flush_calls = 0

    def flush(self) -> None:
        self.flush_calls += 1


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
    monkeypatch.setattr(base, "LangfuseGetClient", _FakeTelemetryClient)
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


def test_shutdown_flush_does_not_lazily_initialize_langfuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry_client = _FakeTelemetryClient()
    get_client_calls = 0

    def _get_client() -> _FakeTelemetryClient:
        nonlocal get_client_calls
        get_client_calls += 1
        return telemetry_client

    _configure_langfuse_settings(monkeypatch, enabled=True)
    monkeypatch.setattr(base, "LangfuseAsyncOpenAI", _FakeClient)
    monkeypatch.setattr(base, "LangfuseOpenAI", _FakeClient)
    monkeypatch.setattr(base, "_langfuse_client", None, raising=False)
    monkeypatch.setattr(langfuse, "get_client", _get_client)

    base.flush_langfuse()

    assert get_client_calls == 0
    assert telemetry_client.flush_calls == 0


def test_instrumented_call_tracks_and_flushes_initialized_langfuse_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry_client = _FakeTelemetryClient()
    get_client_calls = 0

    def _get_client() -> _FakeTelemetryClient:
        nonlocal get_client_calls
        get_client_calls += 1
        return telemetry_client

    _configure_langfuse_settings(monkeypatch, enabled=True)
    monkeypatch.setattr(base, "LangfuseAsyncOpenAI", _FakeClient)
    monkeypatch.setattr(base, "LangfuseOpenAI", _FakeClient)
    monkeypatch.setattr(base, "LangfuseGetClient", _get_client, raising=False)
    monkeypatch.setattr(base, "_langfuse_client", None, raising=False)

    client = base.make_async_llm_client(agent_name="reporting_agent")
    assert get_client_calls == 0

    client.chat.completions.create(model="test-model", messages=[])
    assert get_client_calls == 1

    base.flush_langfuse()
    assert get_client_calls == 1
    assert telemetry_client.flush_calls == 1


def test_configured_langfuse_import_exits_without_shutdown_traceback() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    env = {
        **os.environ,
        "LANGFUSE_TRACING_ENABLED": "true",
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "LANGFUSE_BASE_URL": "http://127.0.0.1:9",
    }

    result = subprocess.run(
        [sys.executable, "-c", "import app.agents.base"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0
    assert "langfuse_flush_failed" not in result.stderr
    assert "cannot schedule new futures after interpreter shutdown" not in result.stderr
