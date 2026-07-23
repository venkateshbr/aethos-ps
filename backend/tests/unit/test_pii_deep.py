"""#392 — deep (NER) PII masking with graceful fallback."""

from __future__ import annotations

import pytest

from app.domain.pii import mask_names, mask_pii, mask_pii_deep

pytestmark = pytest.mark.unit


class _Ent:
    def __init__(self, start: int, end: int, label: str) -> None:
        self.start_char, self.end_char, self.label_ = start, end, label


class _Doc:
    def __init__(self, ents: list[_Ent]) -> None:
        self.ents = ents


def _pipeline_for(*phrases_labels: tuple[str, str]):
    def _nlp(text: str) -> _Doc:
        ents = []
        for phrase, label in phrases_labels:
            idx = text.find(phrase)
            if idx >= 0:
                ents.append(_Ent(idx, idx + len(phrase), label))
        return _Doc(ents)

    return _nlp


def test_deep_without_model_is_regex_only() -> None:
    # CI has no spaCy model → mask_pii_deep must equal regex mask_pii (no crash,
    # names left intact, structured PII still redacted).
    text = "Pay IBAN GB29NWBK60161331926819 to John Smith"
    assert mask_pii_deep(text) == mask_pii(text)
    assert "[REDACTED-BANK-ACCOUNT]" in mask_pii_deep(text)


def test_mask_names_redacts_person_and_place() -> None:
    nlp = _pipeline_for(("John Smith", "PERSON"), ("Singapore", "GPE"))
    out = mask_names("John Smith met in Singapore", nlp=nlp)
    assert "John Smith" not in out and "Singapore" not in out
    assert out.count("[REDACTED-NAME]") == 2


def test_deep_masks_structured_and_names_together() -> None:
    nlp = _pipeline_for(("Jane Doe", "PERSON"))
    out = mask_pii_deep("Jane Doe — card 4111111111111111", nlp=nlp)
    assert "Jane Doe" not in out
    assert "4111111111111111" not in out
    assert "[REDACTED-NAME]" in out and "[REDACTED-CARD]" in out


def test_mask_names_no_model_is_noop() -> None:
    assert mask_names("John Smith", nlp=None) == "John Smith" or "[REDACTED-NAME]" not in mask_names("x")
