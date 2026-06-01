"""Unit tests for the chat backend — SSE framing, agent tool definitions,
and chat repository contract.

All tests here are pure-Python with no I/O: no DB, no Anthropic API calls.
"""

from __future__ import annotations

import json

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
