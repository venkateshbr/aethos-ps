"""Runtime adapters behind the Aethos Nous chat interface."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

from app.agents.copilot.graph import CopilotAgent, CopilotDeps
from app.core.config import settings
from app.core.db import get_service_role_client
from app.models.ai_settings import AiSettingsResponse
from app.services.ai_settings_service import AiSettingsService, default_ai_settings_response
from app.services.atlas_context import (
    AtlasContextError,
    create_atlas_context_ref,
    create_atlas_tool_session,
)
from app.services.circuit_breaker import get_circuit_breaker
from app.services.hermes_client import HermesClient
from app.services.operational_telemetry import telemetry

logger = logging.getLogger(__name__)

AtlasRuntimeName = Literal["aethos_basic", "hermes_agent"]
ProviderFailureCategory = Literal[
    "quota",
    "auth",
    "rate_limit",
    "timeout",
    "upstream_outage",
    "unknown",
]
_ALLOWED_RUNTIMES = {"aethos_basic", "hermes_agent"}

# How much of the opening assistant text to buffer and classify before the first
# user-visible token. Provider-error and unsafe-output text from Hermes appears
# at the very start of a turn, so a short prefix is enough to gate fallback while
# still letting real answers stream token-by-token afterwards.
_CLASSIFY_PREFIX_CHARS = 160


class HermesProviderError(RuntimeError):
    """Hermes returned upstream-provider failure text instead of assistant output."""

    def __init__(self, category: ProviderFailureCategory) -> None:
        super().__init__(f"Hermes upstream provider failure: {category}")
        self.category = category


class HermesUnsafeOutputError(RuntimeError):
    """Hermes returned empty or internal-control text instead of a user answer."""

    def __init__(self, category: str) -> None:
        super().__init__(f"Hermes unsafe output: {category}")
        self.category = category


_PROVIDER_ERROR_PATTERNS = (
    re.compile(r"\bHTTP\s+(?:4\d{2}|5\d{2})\b", re.IGNORECASE),
    re.compile(r"\b(?:key|credit|quota|total|rate)\s+limit\s+exceeded\b", re.IGNORECASE),
    re.compile(r"\brequires\s+more\s+credits\b", re.IGNORECASE),
    re.compile(r"\bopenrouter\.ai\b", re.IGNORECASE),
)
_INTERNAL_OUTPUT_PATTERNS = (
    re.compile(r"\bwe need to respond to (?:the )?user request\b", re.IGNORECASE),
    re.compile(r"\bwe have to use the appropriate tool", re.IGNORECASE),
    re.compile(r"\bthe system'?s tool\b", re.IGNORECASE),
    re.compile(r"\b(?:query_engagements|query_time_entries|get_wip|get_ar_aging|get_ap_aging)\b"),
    re.compile(r"\baethos\.[a-z0-9_.]+\b", re.IGNORECASE),
    re.compile(r"\bcontext_ref\b", re.IGNORECASE),
    re.compile(r"\bfunction_call\b", re.IGNORECASE),
    re.compile(r"\braw tool (?:output|arguments|payload)\b", re.IGNORECASE),
)


class AtlasRuntime(Protocol):
    """Stable interface used by the chat router for all Nous runtimes."""

    name: AtlasRuntimeName

    async def stream_message(
        self,
        *,
        user_message: str,
        thread_id: str,
    ) -> AsyncIterator[str]:
        """Yield SSE frames for a single Nous message turn."""


@dataclass
class AethosBasicRuntimeAdapter:
    """Current built-in Nous agent path, wrapped behind the runtime seam."""

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
    """Hermes-powered Nous runtime adapter."""

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
        breaker = get_circuit_breaker(f"hermes:{getattr(self.client, 'base_url', 'default')}")
        if not breaker.allow():
            # Hermes is tripped; skip the connect/timeout wait and serve the
            # fallback immediately so the user is not penalised per request.
            _record_provider_failure(
                category="upstream_outage",
                tenant_id=self.tenant_id,
                thread_id=thread_id,
                runtime=self.name,
            )
            if self.fallback_runtime is not None:
                async for frame in self.fallback_runtime.stream_message(
                    user_message=user_message,
                    thread_id=thread_id,
                ):
                    yield frame
                return
            yield f"data: {json.dumps({'error': 'Nous is temporarily unavailable. Please try again shortly.'})}\n\n"
            return
        try:
            emitted_any = False
            async for text in self._safe_hermes_deltas(
                user_message=user_message,
                conversation=conversation,
                instructions=instructions,
            ):
                emitted_any = True
                yield f"data: {json.dumps({'delta': text})}\n\n"
            if not emitted_any:
                # Nothing safe to say — treat as unsafe/empty and fall back.
                raise HermesUnsafeOutputError("empty")
            breaker.record_success()
            yield f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n"
        except HermesProviderError as exc:
            breaker.record_failure()
            _record_provider_failure(
                category=exc.category,
                tenant_id=self.tenant_id,
                thread_id=thread_id,
                runtime=self.name,
            )
            if self.fallback_runtime is not None:
                async for frame in self.fallback_runtime.stream_message(
                    user_message=user_message,
                    thread_id=thread_id,
                ):
                    yield frame
                return
            yield f"data: {json.dumps({'error': 'Nous is temporarily unavailable. Please try again shortly.'})}\n\n"
        except HermesUnsafeOutputError as exc:
            _record_provider_failure(
                category="unknown",
                tenant_id=self.tenant_id,
                thread_id=thread_id,
                runtime=self.name,
            )
            logger.warning(
                "hermes_agent_unsafe_output",
                extra={
                    "tenant_id": self.tenant_id,
                    "thread_id": thread_id,
                    "unsafe_output_category": exc.category,
                },
            )
            if self.fallback_runtime is not None:
                async for frame in self.fallback_runtime.stream_message(
                    user_message=user_message,
                    thread_id=thread_id,
                ):
                    yield frame
                return
            yield f"data: {json.dumps({'error': 'Nous could not produce a safe answer. Please try again.'})}\n\n"
        except Exception as exc:
            provider_failure = _provider_failure_category_from_exception(exc)
            if provider_failure is not None:
                breaker.record_failure()
                _record_provider_failure(
                    category=provider_failure,
                    tenant_id=self.tenant_id,
                    thread_id=thread_id,
                    runtime=self.name,
                )
                if self.fallback_runtime is not None:
                    async for frame in self.fallback_runtime.stream_message(
                        user_message=user_message,
                        thread_id=thread_id,
                    ):
                        yield frame
                    return
                yield f"data: {json.dumps({'error': 'Nous is temporarily unavailable. Please try again shortly.'})}\n\n"
                return
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

    async def _safe_hermes_deltas(
        self,
        *,
        user_message: str,
        conversation: str,
        instructions: str,
    ) -> AsyncIterator[str]:
        """Stream user-safe assistant text, gating fallback on the opening prefix.

        Provider-error and unsafe-output text is only raised **before** the first
        token is yielded, so the caller's fallback path never double-emits after
        the user has already seen text. Once streaming has started, any tail that
        leaks tool internals is suppressed by stopping the stream.
        """
        buffer = ""
        gated = False
        async for delta in self.client.stream_response(
            input_text=user_message,
            conversation=conversation,
            instructions=instructions,
        ):
            if not delta:
                continue
            if gated:
                if _has_internal_control_text(delta):
                    return
                yield delta
                continue
            buffer += delta
            if len(buffer) < _CLASSIFY_PREFIX_CHARS:
                continue
            _raise_if_unsafe_prefix(buffer)
            gated = True
            yield buffer
            buffer = ""

        if not gated:
            # Short turn that never reached the classification threshold.
            _raise_if_unsafe_prefix(buffer)
            if buffer:
                yield buffer


def _raise_if_unsafe_prefix(text: str) -> None:
    """Raise a fallback-triggering error for provider or tool-internal text.

    Only called before any user-visible token is emitted. Empty text is allowed
    through so the caller can treat a genuinely empty turn as an unsafe/empty
    fallback after the stream ends.
    """
    provider_failure = _provider_failure_category_from_text(text)
    if provider_failure is not None:
        raise HermesProviderError(provider_failure)
    if _has_internal_control_text(text):
        raise HermesUnsafeOutputError("internal_control_text")


def _has_internal_control_text(text: str) -> bool:
    """True when text leaks tool names, context refs, or model control phrasing."""
    return any(pattern.search(text) for pattern in _INTERNAL_OUTPUT_PATTERNS)


def _looks_like_provider_error(text: str) -> bool:
    """Detect provider/control-plane failure text that should never reach users."""
    return _provider_failure_category_from_text(text) is not None


def _provider_failure_category_from_text(text: str) -> ProviderFailureCategory | None:
    """Classify provider/control-plane text returned by Hermes."""
    if not text:
        return None
    if not any(pattern.search(text) for pattern in _PROVIDER_ERROR_PATTERNS):
        return None
    lowered = text.lower()
    if any(token in lowered for token in ("quota", "credit", "total limit", "key limit")):
        return "quota"
    if "429" in lowered or "rate limit" in lowered or "too many requests" in lowered:
        return "rate_limit"
    if any(token in lowered for token in ("401", "403", "auth", "invalid key", "token")):
        return "auth"
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if any(token in lowered for token in ("500", "502", "503", "504", "upstream", "unavailable")):
        return "upstream_outage"
    return "unknown"


def _provider_failure_category_from_exception(
    exc: Exception,
) -> ProviderFailureCategory | None:
    """Classify provider/control-plane exceptions without exposing details."""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 402:
            return "quota"
        if status_code in {401, 403}:
            return "auth"
        if status_code == 429:
            return "rate_limit"
        if status_code >= 500:
            return "upstream_outage"
        if status_code >= 400:
            return "unknown"
    return None


def _unsafe_output_category_from_text(text: str) -> str | None:
    """Classify Hermes output that should not be shown as a user response."""
    if not text.strip():
        return "empty"
    if any(pattern.search(text) for pattern in _INTERNAL_OUTPUT_PATTERNS):
        return "internal_control_text"
    return None


def _record_provider_failure(
    *,
    category: ProviderFailureCategory,
    tenant_id: str,
    thread_id: str,
    runtime: AtlasRuntimeName,
) -> None:
    telemetry.record_background_failure(f"atlas_provider_{category}")
    logger.warning(
        "atlas_provider_failure",
        extra={
            "tenant_id": tenant_id,
            "thread_id": thread_id,
            "runtime": runtime,
            "provider_failure_category": category,
        },
    )


def normalise_atlas_runtime_name(value: str | None) -> AtlasRuntimeName:
    """Return a validated Nous runtime name."""
    runtime = (value or "").strip().lower()
    if runtime not in _ALLOWED_RUNTIMES:
        raise ValueError("Nous AI runtime must be 'aethos_basic' or 'hermes_agent'")
    return runtime  # type: ignore[return-value]


async def build_atlas_runtime(
    *,
    tenant_id: str,
    user_id: str,
    db_client: object,
    runtime_name: str | None = None,
    ai_settings: AiSettingsResponse | None = None,
) -> AtlasRuntime:
    """Build the configured Nous runtime adapter for a request."""
    if ai_settings is None:
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
    "You are Aethos Nous, the AI interface for Aethos. "
    "Aethos is the system of record for tenant data, finance records, approvals, "
    "and audit evidence. Use Aethos tools for real data and actions. "
    "When a user asks about an uploaded document, document extraction, an engagement "
    "letter, vendor invoice, COSEC instruction, or source-file evidence, read the "
    "document intake/audit context before answering or preparing work. "
    "When a user asks to create or update an engagement, resolve the client from "
    "business names and prepare the engagement review through Aethos without asking "
    "for internal IDs. "
    "When a user asks to log time or inspect delivery/resource data, use the Aethos "
    "time and delivery tools before answering. "
    "When a user asks about approval authority, pending approvals, controls, or "
    "segregation of duties, read the approval controls context. "
    "When a user asks about manual journals, reversals, close evidence, or decision "
    "history, read the accounting decision trail and state that reversals create "
    "new journals rather than editing posted journals. "
    "When a user asks about operational health, AI/provider status, telemetry, or "
    "Langfuse, use the operational health context and summarize only user-safe "
    "health signals. "
    "Do not expose internal tool names, traces, logs, raw tool outputs, or stack traces "
    "to users. Summarize business outcomes clearly and route sensitive actions to Inbox."
)


def _build_hermes_instructions(
    *,
    tenant_id: str,
    user_id: str,
    thread_id: str,
) -> str:
    """Build per-turn Hermes instructions with an opaque Aethos tool context.

    Prefer a SHORT server-resolved session token (``cts_...``): weaker models
    reliably copy a ~26-char token but mangle the ~360-char signed ref, which the
    broker then rejects (HTTP 400). Falls back to the self-contained signed ref if
    the session cannot be persisted (e.g. DB unavailable), preserving graceful
    degradation.
    """
    context_ref: str | None = None
    try:
        context_ref = create_atlas_tool_session(
            get_service_role_client(),
            tenant_id=tenant_id,
            user_id=user_id,
            thread_id=thread_id,
        )
    except Exception:
        logger.warning(
            "atlas_tool_session_unavailable",
            exc_info=True,
            extra={"tenant_id": tenant_id, "thread_id": thread_id},
        )

    if context_ref is None:
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
