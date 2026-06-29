"""Runtime adapters behind the Aethos Atlas chat interface."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

from app.agents.copilot.graph import CopilotAgent, CopilotDeps
from app.core.config import settings
from app.services.ai_settings_service import AiSettingsService, default_ai_settings_response
from app.services.atlas_context import AtlasContextError, create_atlas_context_ref
from app.services.hermes_client import HermesClient, extract_response_text

logger = logging.getLogger(__name__)

AtlasRuntimeName = Literal["aethos_basic", "hermes_agent"]
_ALLOWED_RUNTIMES = {"aethos_basic", "hermes_agent"}


class HermesProviderError(RuntimeError):
    """Hermes returned upstream-provider failure text instead of assistant output."""


_PROVIDER_ERROR_PATTERNS = (
    re.compile(r"\bHTTP\s+(?:4\d{2}|5\d{2})\b", re.IGNORECASE),
    re.compile(r"\b(?:key|credit|quota|total|rate)\s+limit\s+exceeded\b", re.IGNORECASE),
    re.compile(r"\brequires\s+more\s+credits\b", re.IGNORECASE),
    re.compile(r"\bopenrouter\.ai\b", re.IGNORECASE),
)


class AtlasRuntime(Protocol):
    """Stable interface used by the chat router for all Atlas runtimes."""

    name: AtlasRuntimeName

    async def stream_message(
        self,
        *,
        user_message: str,
        thread_id: str,
    ) -> AsyncIterator[str]:
        """Yield SSE frames for a single Atlas message turn."""


@dataclass
class AethosBasicRuntimeAdapter:
    """Current built-in Atlas agent path, wrapped behind the runtime seam."""

    deps: CopilotDeps
    name: AtlasRuntimeName = "aethos_basic"

    async def stream_message(
        self,
        *,
        user_message: str,
        thread_id: str,
    ) -> AsyncIterator[str]:
        agent = CopilotAgent(deps=self.deps)
        async for frame in agent.run_stream(
            user_message=user_message,
            thread_id=thread_id,
        ):
            yield frame


@dataclass
class HermesAgentRuntimeAdapter:
    """Hermes-powered Atlas runtime adapter."""

    tenant_id: str
    user_id: str
    client: HermesClient
    fallback_runtime: AtlasRuntime | None = None
    name: AtlasRuntimeName = "hermes_agent"

    async def stream_message(
        self,
        *,
        user_message: str,
        thread_id: str,
    ) -> AsyncIterator[str]:
        conversation = f"aethos:{self.tenant_id}:{self.user_id}:{thread_id}"
        instructions = _build_hermes_instructions(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            thread_id=thread_id,
        )
        try:
            response = await self.client.create_response(
                input_text=user_message,
                conversation=conversation,
                instructions=instructions,
            )
            text = extract_response_text(response)
            if _looks_like_provider_error(text):
                raise HermesProviderError("Hermes returned an upstream provider error")
            if text:
                yield f"data: {json.dumps({'delta': text})}\n\n"
            yield f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n"
        except HermesProviderError:
            logger.warning(
                "hermes_agent_provider_error",
                exc_info=True,
                extra={"tenant_id": self.tenant_id, "thread_id": thread_id},
            )
            if self.fallback_runtime is not None:
                async for frame in self.fallback_runtime.stream_message(
                    user_message=user_message,
                    thread_id=thread_id,
                ):
                    yield frame
                return
            yield f"data: {json.dumps({'error': 'Atlas is temporarily unavailable. Please try again shortly.'})}\n\n"
        except Exception:
            logger.warning(
                "hermes_agent_runtime_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id, "thread_id": thread_id},
            )
            if self.fallback_runtime is not None:
                async for frame in self.fallback_runtime.stream_message(
                    user_message=user_message,
                    thread_id=thread_id,
                ):
                    yield frame
                return
            yield f"data: {json.dumps({'error': 'Hermes Agent runtime is unavailable'})}\n\n"


def _looks_like_provider_error(text: str) -> bool:
    """Detect provider/control-plane failure text that should never reach users."""
    if not text:
        return False
    return any(pattern.search(text) for pattern in _PROVIDER_ERROR_PATTERNS)


def normalise_atlas_runtime_name(value: str | None) -> AtlasRuntimeName:
    """Return a validated Atlas runtime name."""
    runtime = (value or "").strip().lower()
    if runtime not in _ALLOWED_RUNTIMES:
        raise ValueError("Atlas AI runtime must be 'aethos_basic' or 'hermes_agent'")
    return runtime  # type: ignore[return-value]


async def build_atlas_runtime(
    *,
    tenant_id: str,
    user_id: str,
    db_client: object,
    runtime_name: str | None = None,
) -> AtlasRuntime:
    """Build the configured Atlas runtime adapter for a request."""
    try:
        ai_settings = await AiSettingsService(db_client, tenant_id).get_effective_settings()  # type: ignore[arg-type]
    except Exception:
        logger.warning(
            "tenant_ai_settings_unavailable",
            exc_info=True,
            extra={"tenant_id": tenant_id},
        )
        ai_settings = default_ai_settings_response(tenant_id=tenant_id)
    runtime = normalise_atlas_runtime_name(runtime_name or ai_settings.atlas_runtime)
    model_chain = ai_settings.model_chain
    if runtime == "aethos_basic":
        return AethosBasicRuntimeAdapter(
            deps=CopilotDeps(
                tenant_id=tenant_id,
                user_id=user_id,
                db_client=db_client,
                llm_api_key=_basic_runtime_api_key(),
                llm_base_url=_basic_runtime_base_url(),
                llm_models=model_chain,
            )
        )
    fallback_runtime = None
    if settings.atlas_hermes_fallback_to_basic:
        fallback_runtime = AethosBasicRuntimeAdapter(
            deps=CopilotDeps(
                tenant_id=tenant_id,
                user_id=user_id,
                db_client=db_client,
                llm_api_key=_basic_runtime_api_key(),
                llm_base_url=_basic_runtime_base_url(),
                llm_models=model_chain,
            )
        )

    return HermesAgentRuntimeAdapter(
        tenant_id=tenant_id,
        user_id=user_id,
        client=HermesClient(
            base_url=settings.atlas_hermes_api_base_url,
            api_key=settings.atlas_hermes_api_server_key,
            timeout_seconds=settings.atlas_hermes_timeout_seconds,
        ),
        fallback_runtime=fallback_runtime,
    )


def _basic_runtime_api_key() -> str:
    return settings.atlas_basic_openrouter_api_key or settings.openrouter_api_key


def _basic_runtime_base_url() -> str:
    return settings.atlas_basic_openrouter_base_url or settings.openrouter_base_url


_ATLAS_HERMES_INSTRUCTIONS = (
    "You are Aethos Atlas, the AI interface for Aethos. "
    "Aethos is the system of record for tenant data, finance records, approvals, "
    "and audit evidence. Use Aethos tools for real data and actions. "
    "Do not expose internal tool names, traces, logs, raw tool outputs, or stack traces "
    "to users. Summarize business outcomes clearly and route sensitive actions to Inbox."
)


def _build_hermes_instructions(
    *,
    tenant_id: str,
    user_id: str,
    thread_id: str,
) -> str:
    """Build per-turn Hermes instructions with an opaque Aethos tool context."""
    try:
        context_ref = create_atlas_context_ref(
            tenant_id=tenant_id,
            user_id=user_id,
            thread_id=thread_id,
        )
    except AtlasContextError:
        logger.warning(
            "atlas_context_ref_unavailable",
            exc_info=True,
            extra={"tenant_id": tenant_id, "thread_id": thread_id},
        )
        return _ATLAS_HERMES_INSTRUCTIONS

    return (
        f"{_ATLAS_HERMES_INSTRUCTIONS} "
        "For every Aethos MCP tool call, pass this short opaque context_ref "
        f"exactly as provided: `{context_ref}`. Do not reveal the context_ref "
        "to users."
    )
