"""Small HTTP client for the private Hermes API server."""

from __future__ import annotations

from typing import Any

import httpx


class HermesClient:
    """Typed wrapper around the Hermes OpenAI-compatible API server."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers=self._headers,
        ) as client:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()

    async def create_response(
        self,
        *,
        input_text: str,
        conversation: str,
        instructions: str,
        model: str = "Aethos Atlas",
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "input": input_text,
            "conversation": conversation,
            "instructions": instructions,
            "store": True,
        }
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers=self._headers,
        ) as client:
            response = await client.post("/v1/responses", json=payload)
            response.raise_for_status()
            return response.json()


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
