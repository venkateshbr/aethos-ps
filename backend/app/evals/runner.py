"""Live runner: send a golden prompt through the real chat API and collect the
assistant answer, so the rubric can score the running agent (Basic or Hermes).

Kept dependency-light and defensive about response shapes so it survives minor
API changes. Used by the opt-in eval test and can be scripted for ad-hoc runs.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.evals.golden_prompts import EvalCase
from app.evals.rubric import RubricResult, evaluate


def _thread_id_from(payload: Any) -> str | None:
    if isinstance(payload, dict):
        if isinstance(payload.get("id"), str):
            return payload["id"]
        thread = payload.get("thread")
        if isinstance(thread, dict) and isinstance(thread.get("id"), str):
            return thread["id"]
    return None


async def collect_answer(
    prompt: str,
    *,
    api_url: str,
    token: str,
    tenant_id: str,
    timeout: float = 120.0,
) -> str:
    """Create a thread, send ``prompt``, and return the streamed assistant text."""
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
    }
    async with httpx.AsyncClient(
        base_url=api_url.rstrip("/"), timeout=timeout, headers=headers
    ) as client:
        created = await client.post("/api/v1/chat/threads", json={"title": "eval"})
        created.raise_for_status()
        thread_id = _thread_id_from(created.json())
        if not thread_id:
            raise RuntimeError("Could not resolve chat thread id from create response")

        parts: list[str] = []
        async with client.stream(
            "POST",
            f"/api/v1/chat/threads/{thread_id}/messages",
            json={"content": prompt},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[len("data:") :].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(event, dict) and isinstance(event.get("delta"), str):
                    parts.append(event["delta"])
        return "".join(parts)


async def run_case(
    case: EvalCase,
    *,
    api_url: str,
    token: str,
    tenant_id: str,
    timeout: float = 120.0,
) -> RubricResult:
    answer = await collect_answer(
        case.prompt,
        api_url=api_url,
        token=token,
        tenant_id=tenant_id,
        timeout=timeout,
    )
    return evaluate(case, answer)
