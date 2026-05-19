"""Agent base infrastructure — shared deps, PII masking.

All agents must import AgentDeps and mask_pii from here.
Never send un-masked text to an external LLM API.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from supabase import Client


@dataclass
class AgentDeps:
    """Tenant-scoped dependencies injected into every agent call."""

    tenant_id: str
    user_id: str | None
    db: Client  # service-role client for reading storage + writing suggestions


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
