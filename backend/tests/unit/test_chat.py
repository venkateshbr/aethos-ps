"""Unit tests for the chat backend — SSE framing, agent tool definitions,
and chat repository contract.

All tests here are pure-Python with no I/O: no DB, no Anthropic API calls.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

# ---------------------------------------------------------------------------
# SSE frame format
# ---------------------------------------------------------------------------


def test_sse_frame_format_delta():
    """SSE data frame must be 'data: {...}\\n\\n'."""
    frame = f"data: {json.dumps({'delta': 'hello'})}\n\n"
    assert frame.startswith("data: ")
    payload = json.loads(frame[6:].strip())
    assert payload["delta"] == "hello"


def test_sse_frame_format_done():
    """Done frame must include done=True and a finish_reason."""
    frame = f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n"
    assert frame.startswith("data: ")
    payload = json.loads(frame[6:].strip())
    assert payload["done"] is True
    assert payload["finish_reason"] == "stop"


def test_sse_frame_format_error():
    """Error frame must include an 'error' key."""
    frame = f"data: {json.dumps({'error': 'AI unavailable — try again shortly'})}\n\n"
    assert frame.startswith("data: ")
    payload = json.loads(frame[6:].strip())
    assert "error" in payload
    assert "unavailable" in payload["error"].lower()


def test_sse_frame_double_newline_terminator():
    """Every SSE frame must end with exactly two newlines."""
    frames = [
        f"data: {json.dumps({'delta': 'x'})}\n\n",
        f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n",
        f"data: {json.dumps({'error': 'oops'})}\n\n",
    ]
    for frame in frames:
        assert frame.endswith("\n\n"), f"Frame does not end with \\n\\n: {frame!r}"


# ---------------------------------------------------------------------------
# CopilotAgent tool definitions
# ---------------------------------------------------------------------------


def test_tool_definition_has_required_fields():
    """Each tool in CopilotAgent.TOOLS must have name, description, input_schema."""
    from app.agents.copilot.graph import CopilotAgent

    for tool in CopilotAgent.TOOLS:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool missing 'description': {tool}"
        assert "input_schema" in tool, f"Tool missing 'input_schema': {tool}"


def test_query_engagements_tool_exists():
    """query_engagements tool must be present in TOOLS."""
    from app.agents.copilot.graph import CopilotAgent

    tool_names = [t["name"] for t in CopilotAgent.TOOLS]
    assert "query_engagements" in tool_names


def test_query_engagements_status_enum():
    """query_engagements status property must enumerate valid statuses."""
    from app.agents.copilot.graph import CopilotAgent

    tool = next(t for t in CopilotAgent.TOOLS if t["name"] == "query_engagements")
    status_prop = tool["input_schema"]["properties"]["status"]
    assert "enum" in status_prop
    expected = {"active", "draft", "completed", "all"}
    assert set(status_prop["enum"]) == expected


def test_system_prompt_no_sensitive_placeholders():
    """System prompt template must not contain email or user name placeholders."""
    from app.agents.copilot.graph import CopilotAgent

    prompt = CopilotAgent.SYSTEM_PROMPT
    assert "{email}" not in prompt
    assert "{user_name}" not in prompt
    assert "{name}" not in prompt
    # tenant_id is allowed
    assert "{tenant_id}" in prompt


# ---------------------------------------------------------------------------
# CopilotDeps
# ---------------------------------------------------------------------------


def test_copilot_deps_fields():
    """CopilotDeps dataclass must carry tenant_id, user_id, db_client."""
    from app.agents.copilot.graph import CopilotDeps

    deps = CopilotDeps(tenant_id="t-1", user_id="u-1", db_client=object())
    assert deps.tenant_id == "t-1"
    assert deps.user_id == "u-1"
    assert deps.db_client is not None


# ---------------------------------------------------------------------------
# ThreadResponse model
# ---------------------------------------------------------------------------


def test_thread_response_model_fields():
    """ThreadResponse must have id, title, created_at, updated_at."""
    from app.api.v1.endpoints.chat import ThreadResponse

    resp = ThreadResponse(
        id="abc",
        tenant_id="tenant-1",
        title="My thread",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert resp.id == "abc"
    assert resp.title == "My thread"


def test_thread_response_title_optional():
    """ThreadResponse title must be optional (can be None)."""
    from app.api.v1.endpoints.chat import ThreadResponse

    resp = ThreadResponse(
        id="abc",
        tenant_id="tenant-1",
        title=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert resp.title is None


# ---------------------------------------------------------------------------
# ChatRepository — constructor contract
# ---------------------------------------------------------------------------


def test_chat_repository_constructor():
    """ChatRepository must accept db and tenant_id arguments."""
    from app.repositories.chat_repo import ChatRepository

    fake_db = object()
    repo = ChatRepository(db=fake_db, tenant_id="tenant-xyz")
    assert repo.tenant_id == "tenant-xyz"
    assert repo.db is fake_db


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------


def test_chat_router_exports_router_object():
    """The chat endpoint module must export an APIRouter named 'router'."""
    from fastapi import APIRouter

    import app.api.v1.endpoints.chat as chat_module

    assert hasattr(chat_module, "router"), "chat module must export a 'router'"
    assert isinstance(chat_module.router, APIRouter)


def test_chat_router_has_expected_paths():
    """The chat router itself must define the required route paths."""
    import app.api.v1.endpoints.chat as chat_module

    paths = {r.path for r in chat_module.router.routes}
    assert "/threads" in paths, f"Missing /threads route. Found: {paths}"
    assert "/threads/{thread_id}/messages" in paths, (
        f"Missing /threads/{{thread_id}}/messages route. Found: {paths}"
    )


def test_router_py_includes_chat_line():
    """router.py source must import and include the chat router."""
    import pathlib

    router_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "app"
        / "api"
        / "v1"
        / "router.py"
    )
    source = router_path.read_text()
    assert "chat" in source, "router.py must import and register the chat router"
    assert 'prefix="/chat"' in source or "prefix='/chat'" in source, (
        "router.py must include chat router with prefix='/chat'"
    )


# ---------------------------------------------------------------------------
# Atlas runtime seam
# ---------------------------------------------------------------------------


def _patch_ai_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    runtime: str,
    model_chain: list[str] | None = None,
) -> None:
    from app.services import atlas_runtime

    class FakeAiSettingsService:
        def __init__(self, db_client: object, tenant_id: str) -> None:
            self.db_client = db_client
            self.tenant_id = tenant_id

        async def get_effective_settings(self):
            return SimpleNamespace(
                atlas_runtime=runtime,
                model_chain=model_chain
                or [
                    "google/gemma-4-31b-it:free",
                    "openrouter/free",
                    "anthropic/claude-haiku-4.5",
                ],
            )

    monkeypatch.setattr(atlas_runtime, "AiSettingsService", FakeAiSettingsService)


@pytest.mark.asyncio
async def test_atlas_runtime_factory_defaults_to_basic(monkeypatch: pytest.MonkeyPatch):
    from app.services import atlas_runtime

    _patch_ai_settings(monkeypatch, runtime="aethos_basic")

    adapter = await atlas_runtime.build_atlas_runtime(
        tenant_id="tenant-1",
        user_id="user-1",
        db_client=object(),
    )

    assert isinstance(adapter, atlas_runtime.AethosBasicRuntimeAdapter)
    assert adapter.name == "aethos_basic"


@pytest.mark.asyncio
async def test_atlas_runtime_factory_uses_tenant_model_chain(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.services import atlas_runtime

    _patch_ai_settings(
        monkeypatch,
        runtime="aethos_basic",
        model_chain=["openrouter/free", "anthropic/claude-haiku-4.5"],
    )

    adapter = await atlas_runtime.build_atlas_runtime(
        tenant_id="tenant-1",
        user_id="user-1",
        db_client=object(),
    )

    assert isinstance(adapter, atlas_runtime.AethosBasicRuntimeAdapter)
    assert adapter.deps.llm_models == ["openrouter/free", "anthropic/claude-haiku-4.5"]


@pytest.mark.asyncio
async def test_atlas_runtime_factory_can_enable_hermes_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.services import atlas_runtime

    _patch_ai_settings(monkeypatch, runtime="hermes_agent")
    monkeypatch.setattr(atlas_runtime.settings, "atlas_hermes_fallback_to_basic", True)

    adapter = await atlas_runtime.build_atlas_runtime(
        tenant_id="tenant-1",
        user_id="user-1",
        db_client=object(),
    )

    assert isinstance(adapter, atlas_runtime.HermesAgentRuntimeAdapter)
    assert isinstance(adapter.fallback_runtime, atlas_runtime.AethosBasicRuntimeAdapter)


@pytest.mark.asyncio
async def test_atlas_runtime_factory_passes_hermes_timeout(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.services import atlas_runtime

    seen: dict[str, object] = {}

    class FakeHermesClient:
        def __init__(self, **kwargs) -> None:
            seen.update(kwargs)

    _patch_ai_settings(monkeypatch, runtime="hermes_agent")
    monkeypatch.setattr(atlas_runtime.settings, "atlas_hermes_api_base_url", "http://hermes")
    monkeypatch.setattr(atlas_runtime.settings, "atlas_hermes_api_server_key", "key")
    monkeypatch.setattr(atlas_runtime.settings, "atlas_hermes_timeout_seconds", 123.0)
    monkeypatch.setattr(atlas_runtime, "HermesClient", FakeHermesClient)

    adapter = await atlas_runtime.build_atlas_runtime(
        tenant_id="tenant-1",
        user_id="user-1",
        db_client=object(),
    )

    assert isinstance(adapter, atlas_runtime.HermesAgentRuntimeAdapter)
    assert seen["timeout_seconds"] == 123.0


@pytest.mark.asyncio
async def test_atlas_basic_runtime_uses_separate_provider_override(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.services import atlas_runtime

    _patch_ai_settings(monkeypatch, runtime="aethos_basic")
    monkeypatch.setattr(atlas_runtime.settings, "atlas_basic_openrouter_api_key", "basic-key")
    monkeypatch.setattr(
        atlas_runtime.settings,
        "atlas_basic_openrouter_base_url",
        "https://basic.example/v1",
    )

    adapter = await atlas_runtime.build_atlas_runtime(
        tenant_id="tenant-1",
        user_id="user-1",
        db_client=object(),
    )

    assert isinstance(adapter, atlas_runtime.AethosBasicRuntimeAdapter)
    assert adapter.deps.llm_api_key == "basic-key"
    assert adapter.deps.llm_base_url == "https://basic.example/v1"


def test_atlas_runtime_factory_rejects_unknown_value():
    from app.services.atlas_runtime import normalise_atlas_runtime_name

    with pytest.raises(ValueError):
        normalise_atlas_runtime_name("unknown")


def test_atlas_provider_failure_text_is_classified():
    from app.services.atlas_runtime import _provider_failure_category_from_text

    assert (
        _provider_failure_category_from_text(
            "HTTP 403: Key limit exceeded (total limit). Manage it using https://openrouter.ai"
        )
        == "quota"
    )
    assert _provider_failure_category_from_text("HTTP 429: rate limit exceeded") == "rate_limit"
    assert _provider_failure_category_from_text("HTTP 401: invalid key") == "auth"
    assert _provider_failure_category_from_text("HTTP 504 upstream unavailable") == "upstream_outage"


@pytest.mark.asyncio
async def test_basic_runtime_adapter_delegates_to_copilot(monkeypatch: pytest.MonkeyPatch):
    from app.agents.copilot.graph import CopilotDeps
    from app.services import atlas_runtime

    class FakeCopilotAgent:
        def __init__(self, deps: CopilotDeps) -> None:
            self.deps = deps

        async def run_stream(self, *, user_message: str, thread_id: str):
            yield f"data: {json.dumps({'delta': f'{thread_id}:{user_message}'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n"

    monkeypatch.setattr(atlas_runtime, "CopilotAgent", FakeCopilotAgent)

    adapter = atlas_runtime.AethosBasicRuntimeAdapter(
        deps=CopilotDeps(tenant_id="tenant-1", user_id="user-1", db_client=object())
    )

    frames = [
        frame
        async for frame in adapter.stream_message(
            user_message="hello",
            thread_id="thread-1",
        )
    ]

    assert frames[0] == f"data: {json.dumps({'delta': 'thread-1:hello'})}\n\n"
    assert json.loads(frames[1][6:].strip())["done"] is True


@pytest.mark.asyncio
async def test_hermes_runtime_adapter_streams_visible_text(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.services import atlas_context
    from app.services.atlas_runtime import HermesAgentRuntimeAdapter

    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "secret")

    class FakeHermesClient:
        async def create_response(self, **kwargs):
            assert kwargs["conversation"] == "aethos:tenant-1:user-1:thread-1"
            assert "context_ref" in kwargs["instructions"]
            return {
                "output": [
                    {"type": "function_call", "name": "internal_tool"},
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Visible reply"}],
                    },
                ]
            }

    adapter = HermesAgentRuntimeAdapter(
        tenant_id="tenant-1",
        user_id="user-1",
        client=FakeHermesClient(),
    )
    frames = [
        frame
        async for frame in adapter.stream_message(
            user_message="hello",
            thread_id="thread-1",
        )
    ]

    assert len(frames) == 2
    payload = json.loads(frames[0][6:].strip())
    assert payload["delta"] == "Visible reply"
    assert json.loads(frames[1][6:].strip())["done"] is True


@pytest.mark.asyncio
async def test_hermes_runtime_adapter_hides_provider_error_text():
    from app.services.atlas_runtime import HermesAgentRuntimeAdapter

    class ProviderErrorHermesClient:
        async def create_response(self, **kwargs):
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "HTTP 403: Key limit exceeded. Manage it using https://openrouter.ai/workspaces/example",
                            }
                        ],
                    }
                ]
            }

    adapter = HermesAgentRuntimeAdapter(
        tenant_id="tenant-1",
        user_id="user-1",
        client=ProviderErrorHermesClient(),
    )
    frames = [
        frame
        async for frame in adapter.stream_message(
            user_message="hello",
            thread_id="thread-1",
        )
    ]

    assert len(frames) == 1
    payload = json.loads(frames[0][6:].strip())
    assert payload["error"] == "Atlas is temporarily unavailable. Please try again shortly."
    assert "openrouter" not in json.dumps(payload).lower()


@pytest.mark.asyncio
async def test_hermes_runtime_adapter_classifies_http_provider_failure():
    from app.services.atlas_runtime import HermesAgentRuntimeAdapter
    from app.services.operational_telemetry import telemetry

    class ProviderFailureHermesClient:
        async def create_response(self, **kwargs):
            request = httpx.Request("POST", "https://hermes.internal/v1/responses")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=request,
                response=response,
            )

    telemetry.reset()
    adapter = HermesAgentRuntimeAdapter(
        tenant_id="tenant-1",
        user_id="user-1",
        client=ProviderFailureHermesClient(),
    )
    frames = [
        frame
        async for frame in adapter.stream_message(
            user_message="hello",
            thread_id="thread-1",
        )
    ]

    payload = json.loads(frames[0][6:].strip())
    assert payload["error"] == "Atlas is temporarily unavailable. Please try again shortly."
    assert telemetry.snapshot()["background_failures"] == [
        {"worker_name": "atlas_provider_rate_limit", "count": 1}
    ]


@pytest.mark.asyncio
async def test_hermes_provider_error_can_fallback_to_basic():
    from app.services.atlas_runtime import HermesAgentRuntimeAdapter

    class ProviderErrorHermesClient:
        async def create_response(self, **kwargs):
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "HTTP 402: This request requires more credits.",
                            }
                        ],
                    }
                ]
            }

    class FallbackRuntime:
        async def stream_message(self, *, user_message: str, thread_id: str):
            assert user_message == "hello"
            assert thread_id == "thread-1"
            yield f"data: {json.dumps({'delta': 'Basic reply'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n"

    adapter = HermesAgentRuntimeAdapter(
        tenant_id="tenant-1",
        user_id="user-1",
        client=ProviderErrorHermesClient(),
        fallback_runtime=FallbackRuntime(),
    )
    frames = [
        frame
        async for frame in adapter.stream_message(
            user_message="hello",
            thread_id="thread-1",
        )
    ]

    assert json.loads(frames[0][6:].strip())["delta"] == "Basic reply"
    assert json.loads(frames[1][6:].strip())["done"] is True


@pytest.mark.asyncio
async def test_hermes_runtime_adapter_degrades_safely():
    from app.services.atlas_runtime import HermesAgentRuntimeAdapter

    class FailingHermesClient:
        async def create_response(self, **kwargs):
            raise RuntimeError("Hermes is down")

    adapter = HermesAgentRuntimeAdapter(
        tenant_id="tenant-1",
        user_id="user-1",
        client=FailingHermesClient(),
    )
    frames = [
        frame
        async for frame in adapter.stream_message(
            user_message="hello",
            thread_id="thread-1",
        )
    ]

    assert len(frames) == 1
    payload = json.loads(frames[0][6:].strip())
    assert payload["error"] == "Hermes Agent runtime is unavailable"


@pytest.mark.asyncio
async def test_hermes_runtime_adapter_can_fallback_to_basic():
    from app.services.atlas_runtime import HermesAgentRuntimeAdapter

    class FailingHermesClient:
        async def create_response(self, **kwargs):
            raise RuntimeError("Hermes is down")

    class FallbackRuntime:
        async def stream_message(self, *, user_message: str, thread_id: str):
            assert user_message == "hello"
            assert thread_id == "thread-1"
            yield f"data: {json.dumps({'delta': 'Basic reply'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n"

    adapter = HermesAgentRuntimeAdapter(
        tenant_id="tenant-1",
        user_id="user-1",
        client=FailingHermesClient(),
        fallback_runtime=FallbackRuntime(),
    )
    frames = [
        frame
        async for frame in adapter.stream_message(
            user_message="hello",
            thread_id="thread-1",
        )
    ]

    assert json.loads(frames[0][6:].strip())["delta"] == "Basic reply"
    assert json.loads(frames[1][6:].strip())["done"] is True
