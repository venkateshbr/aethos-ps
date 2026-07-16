"""Small HTTP client for the private Hermes API server.

Adds three reliability properties over a bare request:

* split connect/read/write/pool timeouts so a slow upstream cannot pin a worker
  on connect while still allowing long agentic reads;
* bounded retries with jittered backoff for transient connect/timeout/5xx
  failures on the non-streaming path;
* a true streaming path (``stream_response``) that yields assistant text deltas
  from the Hermes Responses SSE stream, so the user sees tokens as they arrive
  instead of waiting for the whole turn.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator
from typing import Any

import httpx

# Transient failures worth a bounded retry on the non-streaming path. 4xx
# (except 429, handled separately) is a caller/config error and is not retried.
_RETRYABLE_STATUS = {429, 502, 503, 504}
_RETRYABLE_EXC = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)


def _hermes_timeout(read_seconds: float) -> httpx.Timeout:
    """Split timeouts: fail fast on connect, allow long agentic reads."""
    return httpx.Timeout(read_seconds, connect=5.0, write=10.0, pool=5.0)


class HermesClient:
    """Typed wrapper around the Hermes OpenAI-compatible API server."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)

    @property
    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=_hermes_timeout(self.timeout_seconds),
            headers=self._headers,
        )

    async def health(self) -> dict[str, Any]:
        async with self._new_client() as client:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()

    async def create_response(
        self,
        *,
        input_text: str,
        conversation: str,
        instructions: str,
        model: str = "Aethos Nous",
    ) -> dict[str, Any]:
        """Non-streaming turn. Retries transient failures with jittered backoff."""
        payload = _responses_payload(
            input_text=input_text,
            conversation=conversation,
            instructions=instructions,
            model=model,
            stream=False,
        )
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with self._new_client() as client:
                    response = await client.post("/v1/responses", json=payload)
                    if response.status_code in _RETRYABLE_STATUS:
                        response.raise_for_status()
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRYABLE_STATUS:
                    raise
            except _RETRYABLE_EXC as exc:
                last_exc = exc
            if attempt < self.max_retries:
                await asyncio.sleep(_backoff_seconds(attempt))
        assert last_exc is not None
        raise last_exc

    async def stream_response(
        self,
        *,
        input_text: str,
        conversation: str,
        instructions: str,
        model: str = "Aethos Nous",
    ) -> AsyncIterator[str]:
        """Yield assistant text deltas from the Hermes Responses SSE stream.

        Only user-safe assistant text is yielded. Tool-progress events
        (``response.output_item.*``, ``response.function_call*``) and any other
        control events are consumed server-side and never surfaced, per the
        "hide tool internals" product constraint.
        """
        payload = _responses_payload(
            input_text=input_text,
            conversation=conversation,
            instructions=instructions,
            model=model,
            stream=True,
        )
        async with self._new_client() as client:
            async with client.stream("POST", "/v1/responses", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    for text in _assistant_text_from_sse_line(line):
                        yield text


def _responses_payload(
    *,
    input_text: str,
    conversation: str,
    instructions: str,
    model: str,
    stream: bool,
) -> dict[str, Any]:
    return {
        "model": model,
        "input": input_text,
        "conversation": conversation,
        "instructions": instructions,
        "store": True,
        "stream": stream,
    }


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with full jitter, capped, to avoid thundering herds."""
    base = min(2.0, 0.25 * (2**attempt))
    return random.uniform(0.0, base)


def _assistant_text_from_sse_line(line: str) -> list[str]:
    """Extract user-safe assistant text deltas from one SSE ``data:`` line.

    Supports the OpenAI-compatible Responses streaming event shapes Hermes
    emits: ``response.output_text.delta`` (incremental text) and the terminal
    ``response.output_text.done`` / ``response.completed`` events. Anything else
    — tool events, reasoning, control frames — yields nothing.
    """
    if not line or not line.startswith("data:"):
        return []
    raw = line[len("data:") :].strip()
    if not raw or raw == "[DONE]":
        return []
    try:
        event = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(event, dict):
        return []
    event_type = event.get("type")
    if event_type == "response.output_text.delta":
        delta = event.get("delta")
        return [delta] if isinstance(delta, str) and delta else []
    # Some servers stream the full text on a single "output_text" delta event
    # without a type discriminator; accept a bare {"delta": "..."} as text too.
    if event_type is None and isinstance(event.get("delta"), str) and event["delta"]:
        return [event["delta"]]
    return []


def extract_response_text(payload: dict[str, Any]) -> str:
    """Extract assistant output text from a Hermes Responses API payload."""
    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "".join(chunks).strip()
