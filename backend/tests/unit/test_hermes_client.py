from __future__ import annotations

import httpx
import pytest

from app.services.hermes_client import HermesClient, extract_response_text

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_hermes_client_health_uses_bearer_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["authorization"] = request.headers.get("authorization", "")
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def _client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _client)

    client = HermesClient(base_url="http://hermes:8642/", api_key="secret-key")
    assert await client.health() == {"status": "ok"}
    assert seen_headers["authorization"] == "Bearer secret-key"


@pytest.mark.asyncio
async def test_hermes_client_create_response_posts_responses_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_payload: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        seen_payload.update(request.read() and __import__("json").loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp-1",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Done"}],
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def _client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _client)

    client = HermesClient(base_url="http://hermes:8642", api_key="secret-key")
    payload = await client.create_response(
        input_text="Show WIP",
        conversation="aethos:tenant:user:thread",
        instructions="Use Aethos tools.",
    )

    assert seen_payload["model"] == "Aethos Nous"
    assert seen_payload["input"] == "Show WIP"
    assert seen_payload["conversation"] == "aethos:tenant:user:thread"
    assert seen_payload["store"] is True
    assert extract_response_text(payload) == "Done"


@pytest.mark.asyncio
async def test_stream_response_yields_only_assistant_text_deltas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = (
        b'data: {"type":"response.created"}\n\n'
        b'data: {"type":"response.output_item.added","item":{"type":"function_call"}}\n\n'
        b'data: {"type":"response.output_text.delta","delta":"Hello "}\n\n'
        b'data: {"type":"response.output_text.delta","delta":"world"}\n\n'
        b'data: {"type":"response.completed"}\n\n'
        b"data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        return httpx.Response(
            200, content=body, headers={"content-type": "text/event-stream"}
        )

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def _client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _client)

    client = HermesClient(base_url="http://hermes:8642", api_key="k")
    deltas = [
        chunk
        async for chunk in client.stream_response(
            input_text="hi", conversation="c", instructions="i"
        )
    ]
    # Tool/control events are dropped; only assistant text deltas survive.
    assert deltas == ["Hello ", "world"]


@pytest.mark.asyncio
async def test_create_response_retries_transient_5xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.services.hermes_client as hc

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(hc.asyncio, "sleep", _no_sleep)

    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"error": "upstream"})
        return httpx.Response(
            200,
            json={
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": "ok"}]}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def _client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _client)

    client = HermesClient(base_url="http://hermes:8642", api_key="k", max_retries=2)
    payload = await client.create_response(input_text="hi", conversation="c", instructions="i")
    assert extract_response_text(payload) == "ok"
    assert calls["n"] == 2  # one transient failure, one success


@pytest.mark.asyncio
async def test_create_response_does_not_retry_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad"})

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def _client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _client)

    client = HermesClient(base_url="http://hermes:8642", api_key="k", max_retries=2)
    with pytest.raises(httpx.HTTPStatusError):
        await client.create_response(input_text="hi", conversation="c", instructions="i")
    assert calls["n"] == 1  # 4xx is a caller error — not retried


def test_extract_response_text_ignores_tool_items() -> None:
    payload = {
        "output": [
            {"type": "function_call", "name": "internal_tool"},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Visible text"}],
            },
        ]
    }

    assert extract_response_text(payload) == "Visible text"
