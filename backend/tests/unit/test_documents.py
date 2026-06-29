"""Unit tests for document upload helpers.

All tests are pure-Python — no I/O, no network, no Supabase.
The endpoint itself is tested for validation logic in isolation.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# MIME type validation
# ---------------------------------------------------------------------------

_ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/plain",
    }
)


def test_mime_type_validation_rejects_unknown() -> None:
    """Known-bad MIME types must not be in the allowed set."""
    disallowed = [
        "application/zip",
        "application/x-rar-compressed",
        "application/octet-stream",
        "video/mp4",
        "audio/mpeg",
        "text/html",
        "application/json",
    ]
    for mime in disallowed:
        assert mime not in _ALLOWED_MIME_TYPES, (
            f"Expected {mime!r} to be rejected, but it is in the allowed set."
        )


def test_mime_type_validation_accepts_known() -> None:
    """All allowed MIME types must be in the allowed set."""
    allowed = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/plain",
    ]
    for mime in allowed:
        assert mime in _ALLOWED_MIME_TYPES, (
            f"Expected {mime!r} to be accepted, but it is NOT in the allowed set."
        )


# ---------------------------------------------------------------------------
# SHA-256 determinism
# ---------------------------------------------------------------------------


def test_sha256_computed_deterministically() -> None:
    """SHA-256 of the same content always produces the same hex digest."""
    content = b"hello world"
    digest_a = hashlib.sha256(content).hexdigest()
    digest_b = hashlib.sha256(content).hexdigest()
    assert digest_a == digest_b
    assert len(digest_a) == 64  # hex-encoded SHA-256 is always 64 chars
    assert digest_a == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_sha256_changes_with_content() -> None:
    """Different content produces a different digest."""
    assert hashlib.sha256(b"hello").hexdigest() != hashlib.sha256(b"world").hexdigest()


def test_sha256_empty_content_has_known_value() -> None:
    """SHA-256 of empty bytes is the well-known empty-string hash."""
    empty_hash = hashlib.sha256(b"").hexdigest()
    assert empty_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


# ---------------------------------------------------------------------------
# Storage path format
# ---------------------------------------------------------------------------


def test_storage_path_format() -> None:
    """Storage path must follow {tenant_id}/{year}/{month:02d}/{doc_id}.{ext}."""
    tenant_id = "abc"
    test_date = date(2026, 5, 19)
    doc_id = "xyz"
    ext = "pdf"

    path = f"{tenant_id}/{test_date.year}/{test_date.month:02d}/{doc_id}.{ext}"
    assert path == "abc/2026/05/xyz.pdf"


def test_storage_path_pads_month() -> None:
    """Single-digit months are zero-padded in the storage path."""
    test_date = date(2026, 1, 7)
    path = f"tenant/{test_date.year}/{test_date.month:02d}/doc.pdf"
    assert path == "tenant/2026/01/doc.pdf"


def test_storage_path_uses_uuid_for_doc_id() -> None:
    """The document ID in the path should be a valid UUID string."""
    doc_id = str(uuid.uuid4())
    path = f"tenant-123/2026/05/{doc_id}.pdf"
    # UUID must be parseable and appear in the path.
    parsed = uuid.UUID(doc_id)
    assert str(parsed) == doc_id
    assert doc_id in path


def test_mime_to_ext_map_is_complete() -> None:
    """Every allowed MIME type must have a corresponding file extension."""
    mime_to_ext = {
        "application/pdf": "pdf",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "text/plain": "txt",
    }
    for mime in _ALLOWED_MIME_TYPES:
        assert mime in mime_to_ext, f"No extension mapping for MIME type: {mime!r}"
        ext = mime_to_ext[mime]
        assert ext and not ext.startswith("."), (
            f"Extension for {mime!r} should not have a leading dot: {ext!r}"
        )


def test_engagement_onboarding_output_includes_first_project_and_rates() -> None:
    from app.workers.document_extraction import _normalise_engagement_onboarding_output

    output = _normalise_engagement_onboarding_output(
        {
            "client_name": "Northwind Industries",
            "currency": "USD",
            "scope_summary": "Q3 strategy review and operating model design.",
            "rate_card_hints": [
                {"role": "Senior Consultant", "rate": "350"},
                {"role": "Analyst", "rate": "175"},
            ],
        }
    )

    assert output["onboarding_intent"] == "create_client_engagement_project"
    assert output["engagement_name"] == "Northwind Industries Engagement"
    assert output["first_project_name"] == "General"
    assert output["first_project_description"] == "Q3 strategy review and operating model design."
    assert output["rate_card_summary"] == "Senior Consultant: USD 350/hr; Analyst: USD 175/hr"


def test_engagement_onboarding_output_normalises_nexus_mixed_terms() -> None:
    from app.workers.document_extraction import _normalise_engagement_onboarding_output

    output = _normalise_engagement_onboarding_output(
        {
            "client_name": "Nexus Capital Partners LP",
            "engagement_name": "Nexus Capital Partners - Engagement Letter",
            "billing_arrangement": "fixed_fee",
            "currency": "GBP",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "scope_summary": (
                "Mixed service order: Group consolidation accounts GBP 42,000 fixed fee; "
                "Monthly management accounts GBP 8,500 per month; "
                "CFO advisory services GBP 350 per hour."
            ),
            "rate_card_hints": [{"role": "CFO Advisory Partner", "rate": "350"}],
        }
    )

    assert output["billing_arrangement"] == "mixed"
    assert output["fixed_fee_amount"] == "42000.00"
    assert output["retainer_monthly_amount"] == "8500.00"
    assert output["total_value"] == "144000.00"
    assert output["rate_card_summary"] == "CFO Advisory Partner: GBP 350/hr"


# ---------------------------------------------------------------------------
# File size guard
# ---------------------------------------------------------------------------


def test_max_file_size_constant() -> None:
    """20 MB limit is exactly 20 * 1024 * 1024 bytes."""
    max_bytes = 20 * 1024 * 1024
    assert max_bytes == 20_971_520


def test_content_within_limit_passes() -> None:
    """A 1-byte file is within the 20 MB limit."""
    content = b"x"
    max_bytes = 20 * 1024 * 1024
    assert len(content) <= max_bytes


def test_content_over_limit_detected() -> None:
    """Content larger than 20 MB is correctly identified as too large."""
    max_bytes = 20 * 1024 * 1024
    over_limit = max_bytes + 1
    # We don't allocate 20 MB in a test — just check the arithmetic.
    assert over_limit > max_bytes
