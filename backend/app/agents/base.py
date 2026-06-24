"""Agent base infrastructure — shared deps, PII masking, LLM client.

All agents must import AgentDeps and mask_pii from here.
Never send un-masked text to an external LLM API.
"""

from __future__ import annotations

import base64
import re
import string
from dataclasses import dataclass, field
from typing import Literal

from openai import AsyncOpenAI, OpenAI

from app.core.config import settings
from supabase import Client


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
        text = mask_pii(safety.extracted_text)
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
    text = mask_pii(text)
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


def mask_pii(text: str) -> str:
    """Redact SSN-like, credit-card-like, email, and tax-ID patterns before LLM calls.

    This is a v1 stub. Week 6 will add a proper NER-based masker.
    Returns the text with sensitive patterns replaced by [REDACTED].
    """
    # SSN-like: XXX-XX-XXXX
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]", text)
    # Credit card-like: 16 digits, optionally space/dash separated
    text = re.sub(r"\b(?:\d[ -]?){15}\d\b", "[REDACTED-CARD]", text)
    # US EIN-like tax ID: XX-XXXXXXX
    text = re.sub(r"\b\d{2}-\d{7}\b", "[REDACTED-TAX-ID]", text)
    # UK VAT-like: GB123456789
    text = re.sub(r"\bGB\d{9}\b", "[REDACTED-TAX-ID]", text, flags=re.IGNORECASE)
    # India GSTIN-like: 27AAPFU0939F1Z5
    text = re.sub(
        r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
        "[REDACTED-TAX-ID]",
        text,
        flags=re.IGNORECASE,
    )
    # Australia ABN-like: ABN 12 345 678 901
    text = re.sub(
        r"\bABN\s*\d{2}\s*\d{3}\s*\d{3}\s*\d{3}\b",
        "[REDACTED-TAX-ID]",
        text,
        flags=re.IGNORECASE,
    )
    # Email: keep domain for context, redact username
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b",
        r"[REDACTED]@\1",
        text,
    )
    return text


def _detect_pii_types(text: str) -> set[str]:
    findings: set[str] = set()
    patterns = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "card": r"\b(?:\d[ -]?){15}\d\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "tax_id": (
            r"\b\d{2}-\d{7}\b"
            r"|\bGB\d{9}\b"
            r"|\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b"
            r"|\bABN\s*\d{2}\s*\d{3}\s*\d{3}\s*\d{3}\b"
        ),
    }
    for pii_type, pattern in patterns.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            findings.add(pii_type)
    return findings


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
