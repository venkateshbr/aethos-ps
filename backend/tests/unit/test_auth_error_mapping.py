"""Unit tests for the Supabase ``AuthApiError`` → HTTP exception mapping.

Bug #97 — the signup endpoint used to let ``AuthApiError`` propagate as 500.
We extracted the translation into ``app.api.v1.endpoints.auth._auth_error_to_http``
so it can be unit-tested without the network.

The mapping rules (in order of precedence on the SDK ``code`` field):

* ``user_already_exists`` / ``email_exists`` / ``identity_already_exists`` → **409**
* ``weak_password`` / ``validation_failed`` / ``email_address_invalid`` /
  ``email_address_not_authorized`` → **422**
* ``over_request_rate_limit`` / ``over_email_send_rate_limit`` /
  ``over_sms_send_rate_limit`` → **429**
* ``signup_disabled`` / ``email_provider_disabled`` → **503**
* anything else → **400**

The detail body MUST:

* be a human-readable string (no stack trace, no JWT bits, no table names)
* never mention the vendor by name ("Supabase" must not appear)
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError, AuthWeakPasswordError

pytestmark = pytest.mark.unit


def _mapper():
    """Import the mapper inside the test so failures surface as ImportError, not
    a collection error."""
    from app.api.v1.endpoints.auth import _auth_error_to_http

    return _auth_error_to_http


# ---------------------------------------------------------------------------
# Status-code mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code,expected_status",
    [
        ("user_already_exists", 409),
        ("email_exists", 409),
        ("identity_already_exists", 409),
        ("weak_password", 422),
        ("validation_failed", 422),
        ("email_address_invalid", 422),
        ("email_address_not_authorized", 422),
        ("over_request_rate_limit", 429),
        ("over_email_send_rate_limit", 429),
        ("over_sms_send_rate_limit", 429),
        ("signup_disabled", 503),
        ("email_provider_disabled", 503),
        ("unexpected_failure", 400),
        ("bad_json", 400),
        (None, 400),
    ],
)
def test_status_mapping(code, expected_status):
    err = AuthApiError(message="boom", status=400, code=code)
    http = _mapper()(err)
    assert isinstance(http, HTTPException)
    assert http.status_code == expected_status


# ---------------------------------------------------------------------------
# Detail body sanitisation
# ---------------------------------------------------------------------------


def test_detail_is_string_and_includes_human_message():
    err = AuthApiError(
        message='Email address "foo@example.com" is invalid',
        status=400,
        code="email_address_invalid",
    )
    http = _mapper()(err)
    assert isinstance(http.detail, str)
    assert "invalid" in http.detail.lower()


def test_detail_never_mentions_vendor():
    """The error body is user-facing; the vendor ("Supabase") must not leak."""
    err = AuthApiError(
        message="Supabase auth: user_already_exists, see supabase docs",
        status=400,
        code="user_already_exists",
    )
    http = _mapper()(err)
    assert "supabase" not in http.detail.lower()
    # Code-style names are confusing for end users — should be a friendly phrase.
    assert "user_already_exists" not in http.detail


def test_already_registered_message_is_friendly():
    err = AuthApiError(
        message="User already registered",
        status=400,
        code="user_already_exists",
    )
    http = _mapper()(err)
    assert "already registered" in http.detail.lower()


def test_weak_password_message_is_friendly():
    err = AuthApiError(message="Password is too weak", status=400, code="weak_password")
    http = _mapper()(err)
    assert http.status_code == 422
    assert "password" in http.detail.lower()


def test_rate_limit_status_429_with_retry_after_header():
    err = AuthApiError(
        message="email rate limit exceeded",
        status=429,
        code="over_email_send_rate_limit",
    )
    http = _mapper()(err)
    assert http.status_code == 429
    # Retry-After is a soft requirement — present and a positive integer string.
    assert http.headers is not None
    assert "Retry-After" in http.headers
    assert int(http.headers["Retry-After"]) > 0


# ---------------------------------------------------------------------------
# Weak-password subclass (raised by Supabase when the password hits all the
# validation rules at once; carries a list of reasons)
# ---------------------------------------------------------------------------


def test_weak_password_subclass_is_recognised():
    err = AuthWeakPasswordError(
        message="Password too weak",
        status=400,
        reasons=["length", "characters"],
    )
    http = _mapper()(err)
    assert http.status_code == 422
    assert "password" in http.detail.lower()


# ---------------------------------------------------------------------------
# Substring fallback when ``code`` is not provided
# ---------------------------------------------------------------------------


def test_already_registered_falls_back_on_message_text():
    """Older Supabase responses may not include a structured code — the mapper
    still has to recognise "already registered" in the message."""
    err = AuthApiError(message="User already registered", status=400, code=None)
    http = _mapper()(err)
    assert http.status_code == 409


def test_invalid_email_falls_back_on_message_text():
    err = AuthApiError(
        message='Email address "foo@example.com" is invalid',
        status=400,
        code=None,
    )
    http = _mapper()(err)
    assert http.status_code == 422
