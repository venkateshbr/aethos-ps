"""Deterministic PII redaction — shared by the agent layer and the log boundary.

Lightweight (stdlib only) so it can be imported from ``app.core.logging`` without
pulling the agent stack. ``mask_pii`` redacts the structured identifiers CLAUDE.md
mandates (bank account numbers, tax IDs, full card numbers) plus launch-market
national IDs and emails, before text leaves for an external LLM *or* a log sink.
"""

from __future__ import annotations

import re


def mask_pii(text: str) -> str:
    """Redact high-risk structured identifiers before LLM calls / logs.

    Deterministic, dependency-free redaction of the identifiers CLAUDE.md
    mandates masking (bank account numbers, tax IDs, full card numbers) plus
    the launch-market national IDs. Regex is deliberate here: these are
    *structured* identifiers where pattern matching is more reliable (and
    auditable) than a statistical NER model. Covered:

      - SSN, full PAN (credit card)
      - Tax IDs: US EIN, UK VAT, IN GSTIN, AU ABN
      - Bank accounts: IBAN, and account/routing numbers when context-labelled
      - National IDs: Singapore NRIC/FIN
      - Email (username redacted, domain kept for context)

    Returns the text with sensitive spans replaced by ``[REDACTED-*]``.

    Follow-up (#392): NER-based masking of unstructured PII (person names,
    postal addresses) is not yet covered — those are lower-severity than the
    financial/national identifiers above and need a model dependency.
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
    # IBAN: 2-letter country + 2 check digits + 10-30 alphanumerics. Distinctive
    # enough to match without a context label. Strip spaces the printer inserts.
    text = re.sub(
        r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){10,30}\b",
        "[REDACTED-BANK-ACCOUNT]",
        text,
    )
    # Bank account / routing numbers, but only when context-labelled — masking any
    # 8-17 digit run blindly would eat invoice numbers, amounts, and dates.
    text = re.sub(
        r"\b(account|acct|a/c|iban|routing|aba|sort\s*code|bsb)\b"
        r"\s*(?:number|no\.?|#)?\s*[:#-]?\s*[A-Z0-9][A-Z0-9 -]{5,33}",
        "[REDACTED-BANK-ACCOUNT]",
        text,
        flags=re.IGNORECASE,
    )
    # Singapore NRIC / FIN: prefix letter + 7 digits + checksum letter (e.g. S1234567D).
    text = re.sub(
        r"\b[STFGM]\d{7}[A-Z]\b",
        "[REDACTED-NRIC]",
        text,
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
        "bank_account": (
            r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){10,30}\b"
            r"|\b(?:account|acct|a/c|iban|routing|aba|sort\s*code|bsb)\b"
            r"\s*(?:number|no\.?|#)?\s*[:#-]?\s*[A-Z0-9][A-Z0-9 -]{5,33}"
        ),
        "nric": r"\b[STFGM]\d{7}[A-Z]\b",
    }
    for pii_type, pattern in patterns.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            findings.add(pii_type)
    return findings
