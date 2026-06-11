"""Agent base infrastructure — shared deps, PII masking, LLM client.

All agents must import AgentDeps and mask_pii from here.
Never send un-masked text to an external LLM API.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

from openai import AsyncOpenAI, OpenAI

from app.core.config import settings
from supabase import Client


@dataclass
class AgentDeps:
    """Tenant-scoped dependencies injected into every agent call."""

    tenant_id: str
    user_id: str | None
    db: Client  # service-role client for reading storage + writing suggestions


def make_async_llm_client() -> AsyncOpenAI:
    """Async OpenAI-compatible client pointed at OpenRouter."""
    return AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )


def make_sync_llm_client() -> OpenAI:
    """Sync OpenAI-compatible client pointed at OpenRouter."""
    return OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )


def build_document_content(prompt: str, document_bytes: bytes, mime_type: str) -> list[dict]:
    """Build the chat-message ``content`` array for a document extraction call.

    Routes by MIME type so every extraction agent handles documents identically:

    - ``application/pdf`` → sent natively via OpenRouter's ``file`` content type.
      Models with native PDF support (Claude, Gemini) read it directly; others
      fall back to OpenRouter's file-parser. This reads BOTH text and scanned
      PDFs — the old path decoded raw PDF bytes as UTF-8, which produced binary
      garbage and silently broke every PDF upload (#146).
    - ``image/*`` → base64 vision (``image_url``).
    - everything else → decode to text, mask PII, truncate to 8000 chars.

    Note: PDFs and images are sent to the LLM un-masked (PII masking only runs
    on the text path). This matches the pre-existing vision behaviour; masking
    inside binary documents is tracked separately.
    """
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
    text = mask_pii(text)
    return [{"type": "text", "text": prompt + f"\n\nDocument text:\n{text[:8000]}"}]


def mask_pii(text: str) -> str:
    """Redact SSN-like, credit-card-like, and email patterns before LLM calls.

    This is a v1 stub. Week 6 will add a proper NER-based masker.
    Returns the text with sensitive patterns replaced by [REDACTED].
    """
    # SSN-like: XXX-XX-XXXX
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]", text)
    # Credit card-like: 16 digits, optionally space/dash separated
    text = re.sub(r"\b(?:\d[ -]?){15}\d\b", "[REDACTED-CARD]", text)
    # Email: keep domain for context, redact username
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b",
        r"[REDACTED]@\1",
        text,
    )
    return text
