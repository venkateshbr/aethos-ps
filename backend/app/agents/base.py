"""Agent base infrastructure — shared deps, PII masking, LLM client.

All agents must import AgentDeps and mask_pii from here.
Never send un-masked text to an external LLM API.
"""

from __future__ import annotations

import base64
import logging
import os
import re
import string
from dataclasses import dataclass, field
from typing import Any, Literal

from openai import AsyncOpenAI as StandardAsyncOpenAI
from openai import OpenAI as StandardOpenAI

from app.core.config import settings
from app.core.logging import tenant_id_var, trace_id_var
from app.domain.pii import (  # noqa: F401  (mask_pii re-exported for agent modules)
    _detect_pii_types,
    mask_pii,
    mask_pii_deep,
)
from supabase import Client

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised through factory tests with monkeypatching.
    from langfuse import get_client as LangfuseGetClient
    from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI
    from langfuse.openai import OpenAI as LangfuseOpenAI
except Exception:  # pragma: no cover - dependency may be absent in old envs.
    LangfuseGetClient = None  # type: ignore[assignment]
    LangfuseAsyncOpenAI = None  # type: ignore[assignment]
    LangfuseOpenAI = None  # type: ignore[assignment]


_langfuse_client: Any | None = None


@dataclass
class AgentDeps:
    """Tenant-scoped dependencies injected into every agent call."""

    tenant_id: str
    user_id: str | None
    db: Client  # service-role client for reading storage + writing suggestions


@dataclass(frozen=True)
class DocumentSafetyScan:
    """Preflight findings for a document before it is sent to an external LLM."""

    detected_pii_types: frozenset[str] = field(default_factory=frozenset)
    suspected_prompt_injection: bool = False
    extracted_text: str = ""

    @property
    def should_withhold_binary(self) -> bool:
        return bool(self.detected_pii_types or self.suspected_prompt_injection)


BinaryDocumentPolicy = Literal["withhold_on_sensitive_text", "allow_binary"]


def make_async_llm_client(
    *,
    agent_name: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> StandardAsyncOpenAI:
    """Async OpenAI-compatible client pointed at OpenRouter.

    When Langfuse keys are configured, this returns Langfuse's OpenAI drop-in
    wrapper and injects tenant/user/trace metadata into each chat completion.
    """
    resolved_api_key = api_key or settings.openrouter_api_key
    resolved_base_url = base_url or settings.openrouter_base_url
    if _langfuse_available():
        client = LangfuseAsyncOpenAI(  # type: ignore[misc,operator]
            api_key=resolved_api_key,
            base_url=resolved_base_url,
        )
        return _InstrumentedOpenAIClient(
            client,
            default_metadata=_langfuse_metadata(
                agent_name=agent_name,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                tags=tags,
                metadata=metadata,
            ),
            default_name=agent_name,
        )

    return StandardAsyncOpenAI(
        api_key=resolved_api_key,
        base_url=resolved_base_url,
    )


def make_sync_llm_client(
    *,
    agent_name: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> StandardOpenAI:
    """Sync OpenAI-compatible client pointed at OpenRouter."""
    resolved_api_key = api_key or settings.openrouter_api_key
    resolved_base_url = base_url or settings.openrouter_base_url
    if _langfuse_available():
        client = LangfuseOpenAI(  # type: ignore[misc,operator]
            api_key=resolved_api_key,
            base_url=resolved_base_url,
        )
        return _InstrumentedOpenAIClient(
            client,
            default_metadata=_langfuse_metadata(
                agent_name=agent_name,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                tags=tags,
                metadata=metadata,
            ),
            default_name=agent_name,
        )

    return StandardOpenAI(
        api_key=resolved_api_key,
        base_url=resolved_base_url,
    )


async def resolve_model_chain(db: Client | object, tenant_id: str) -> list[str]:
    """Return tenant AI model chain, falling back to deployment defaults.

    Agents should call this when they already have tenant-scoped dependencies.
    If the settings table is unavailable during startup/migration windows, the
    global configured chain is safer than blocking document or reporting work.
    """
    try:
        from app.services.ai_settings_service import AiSettingsService

        return await AiSettingsService(db, tenant_id).get_effective_model_chain()  # type: ignore[arg-type]
    except Exception:
        logger.warning(
            "tenant_ai_model_chain_unavailable",
            exc_info=True,
            extra={"tenant_id": tenant_id},
        )
        return settings.agent_models


def flush_langfuse() -> None:
    """Flush queued events only when this process initialized Langfuse."""
    client = _langfuse_client
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        logger.warning("langfuse_flush_failed", exc_info=True)


def _initialise_langfuse_client() -> None:
    """Remember the real SDK client before the first instrumented call.

    Initializing here (during normal runtime) lets FastAPI flush an active
    client without creating executor-backed SDK state during interpreter
    teardown. Langfuse registers its own worker-process shutdown hook when this
    client is created, so CLI workers retain graceful telemetry delivery.
    """
    global _langfuse_client
    if _langfuse_client is None and LangfuseGetClient is not None:
        _langfuse_client = LangfuseGetClient()


def _langfuse_available() -> bool:
    if not settings.langfuse_tracing_enabled:
        return False
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return False
    if LangfuseGetClient is None or LangfuseAsyncOpenAI is None or LangfuseOpenAI is None:
        logger.warning("langfuse_sdk_missing")
        return False

    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    if settings.langfuse_base_url:
        os.environ["LANGFUSE_BASE_URL"] = settings.langfuse_base_url
    os.environ["LANGFUSE_TRACING_ENABLED"] = "true"
    os.environ["LANGFUSE_SAMPLE_RATE"] = str(settings.langfuse_sample_rate)
    return True


def _langfuse_metadata(
    *,
    agent_name: str | None,
    tenant_id: str | None,
    user_id: str | None,
    session_id: str | None,
    tags: list[str] | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    current_trace_id = trace_id_var.get("")
    current_tenant_id = tenant_id or tenant_id_var.get("")
    merged: dict[str, Any] = {
        "environment": settings.environment,
    }
    if current_tenant_id:
        merged["tenant_id"] = current_tenant_id
    if current_trace_id:
        merged["trace_id"] = current_trace_id
    if agent_name:
        merged["agent_name"] = agent_name
    if user_id:
        merged["user_id"] = user_id
        merged["langfuse_user_id"] = user_id
    if session_id or current_trace_id:
        merged["langfuse_session_id"] = session_id or current_trace_id

    langfuse_tags = [
        f"env:{settings.environment}",
        *(tags or []),
    ]
    if agent_name:
        langfuse_tags.append(f"agent:{agent_name}")
    if current_tenant_id:
        langfuse_tags.append(f"tenant:{current_tenant_id}")
    merged["langfuse_tags"] = langfuse_tags

    if metadata:
        merged.update(metadata)
    return merged


def _merge_langfuse_call_kwargs(
    kwargs: dict[str, Any],
    *,
    default_metadata: dict[str, Any],
    default_name: str | None,
) -> dict[str, Any]:
    merged = dict(kwargs)
    metadata = dict(default_metadata)
    metadata.update(merged.get("metadata") or {})
    merged["metadata"] = metadata
    if default_name and "name" not in merged:
        merged["name"] = default_name
    trace_id = str(metadata.get("trace_id") or "")
    if _valid_langfuse_trace_id(trace_id) and "trace_id" not in merged:
        merged["trace_id"] = trace_id
    return merged


def _valid_langfuse_trace_id(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{32}", value))


class _InstrumentedOpenAIClient:
    def __init__(
        self,
        client: Any,
        *,
        default_metadata: dict[str, Any],
        default_name: str | None,
    ) -> None:
        self._client = client
        self.chat = _InstrumentedChat(
            client.chat,
            default_metadata=default_metadata,
            default_name=default_name,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class _InstrumentedChat:
    def __init__(
        self,
        chat: Any,
        *,
        default_metadata: dict[str, Any],
        default_name: str | None,
    ) -> None:
        self._chat = chat
        self.completions = _InstrumentedCompletions(
            chat.completions,
            default_metadata=default_metadata,
            default_name=default_name,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class _InstrumentedCompletions:
    def __init__(
        self,
        completions: Any,
        *,
        default_metadata: dict[str, Any],
        default_name: str | None,
    ) -> None:
        self._completions = completions
        self._default_metadata = default_metadata
        self._default_name = default_name

    def create(self, *args: Any, **kwargs: Any) -> Any:
        _initialise_langfuse_client()
        return self._completions.create(
            *args,
            **_merge_langfuse_call_kwargs(
                kwargs,
                default_metadata=self._default_metadata,
                default_name=self._default_name,
            ),
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)


def build_document_content(
    prompt: str,
    document_bytes: bytes,
    mime_type: str,
    *,
    binary_policy: BinaryDocumentPolicy = "withhold_on_sensitive_text",
) -> list[dict]:
    """Build the chat-message ``content`` array for a document extraction call.

    Routes by MIME type so every extraction agent handles documents identically:

    - ``application/pdf`` → sent natively via OpenRouter's ``file`` content type.
      Models with native PDF support (Claude, Gemini) read it directly; others
      fall back to OpenRouter's file-parser. This reads BOTH text and scanned
      PDFs — the old path decoded raw PDF bytes as UTF-8, which produced binary
      garbage and silently broke every PDF upload (#146).
    - ``image/*`` → base64 vision (``image_url``).
    - everything else → decode to text, mask PII, truncate to 8000 chars.

    Before binary files leave Aethos, a deterministic scan looks for extractable
    PII or prompt-injection text. If found, the raw binary is withheld and only
    a masked text representation is sent. This does not OCR scanned images; it
    prevents known text-bearing PDFs and image metadata from bypassing masking.
    """
    safety = scan_document_safety(document_bytes)

    if binary_policy == "withhold_on_sensitive_text" and safety.should_withhold_binary:
        text = mask_pii_deep(safety.extracted_text)
        return [
            {
                "type": "text",
                "text": (
                    prompt
                    + "\n\nDocument safety preflight: raw binary withheld before "
                    "external LLM call because sensitive or adversarial text was detected."
                    + f"\nDetected markers: {', '.join(sorted(safety.detected_pii_types)) or 'prompt_injection'}"
                    + f"\n\nDocument text (masked):\n{text[:8000]}"
                ),
            }
        ]

    if mime_type == "application/pdf":
        encoded = base64.standard_b64encode(document_bytes).decode()
        return [
            {
                "type": "file",
                "file": {
                    "filename": "document.pdf",
                    "file_data": f"data:application/pdf;base64,{encoded}",
                },
            },
            {"type": "text", "text": prompt},
        ]

    if mime_type.startswith("image/"):
        encoded = base64.standard_b64encode(document_bytes).decode()
        media_type = mime_type.replace("image/jpg", "image/jpeg")
        return [
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}},
            {"type": "text", "text": prompt},
        ]

    try:
        text = document_bytes.decode("utf-8", errors="replace")
    except Exception:
        text = document_bytes.decode("latin-1", errors="replace")
    text = mask_pii_deep(text)
    return [{"type": "text", "text": prompt + f"\n\nDocument text:\n{text[:8000]}"}]


def scan_document_safety(document_bytes: bytes) -> DocumentSafetyScan:
    """Return deterministic safety findings from extractable document bytes.

    This is intentionally conservative and dependency-free. It catches obvious
    text-bearing PDFs, plain text, and image metadata. Scanned image/OCR redaction
    remains a separate production-hardening step.
    """
    extracted_text = _extract_printable_text(document_bytes)
    return DocumentSafetyScan(
        detected_pii_types=frozenset(_detect_pii_types(extracted_text)),
        suspected_prompt_injection=_detect_prompt_injection(extracted_text),
        extracted_text=extracted_text,
    )


def _detect_prompt_injection(text: str) -> bool:
    return bool(
        re.search(
            r"\b(ignore|disregard|override)\s+(all\s+)?(previous|prior|system)\s+instructions\b"
            r"|\bapprove\s+(and\s+)?pay\b"
            r"|\bdo\s+not\s+follow\s+the\s+rules\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _extract_printable_text(document_bytes: bytes) -> str:
    text = document_bytes.decode("utf-8", errors="ignore")
    if len(text.strip()) < 20:
        text = document_bytes.decode("latin-1", errors="ignore")
    allowed = set(string.printable)
    cleaned = "".join(ch if ch in allowed else " " for ch in text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:20000]


def mask_registration_number(reg_number: str) -> str:
    """Mask a tax / registration number for safe LLM transmission.

    Replaces the middle digits/characters with asterisks, keeping only the
    first 4 and last 2 characters visible for context (e.g. format detection).

    Examples:
        "GB123456789"  → "GB12*****89"
        "12-3456789"   → "12-3*****89"
        "27AAPFU0939F1Z5" → "27AA*********Z5"
    """
    if not reg_number or len(reg_number) <= 6:
        return "[REDACTED-REGNUM]"
    return reg_number[:4] + ("*" * (len(reg_number) - 6)) + reg_number[-2:]


def mask_address(address: str) -> str:
    """Mask a street address before sending to LLM.

    Keeps only the country/region portion (last comma-separated segment)
    to allow country-cross-check without transmitting full postal details.
    """
    if not address:
        return "[REDACTED-ADDR]"
    parts = [p.strip() for p in address.split(",")]
    if len(parts) > 1:
        # Keep only the last segment (country or state/country)
        return f"[REDACTED], {', '.join(parts[-1:])}"
    return "[REDACTED-ADDR]"
