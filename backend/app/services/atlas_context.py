"""Opaque context references for Nous-to-Aethos internal tool calls."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

_DEFAULT_SCOPE = "atlas_tools:read"
_DEFAULT_TTL_SECONDS = 15 * 60
_CONTEXT_REF_PREFIX = "ctx_"


class AtlasContextError(ValueError):
    """Raised when an Nous context reference is missing, expired, or invalid."""


@dataclass(frozen=True)
class AtlasToolContext:
    """Verified tenant/user/thread context for an internal Nous tool call."""

    tenant_id: str
    user_id: str
    thread_id: str
    scope: str
    expires_at: int
    nonce: str


def create_atlas_context_ref(
    *,
    tenant_id: str,
    user_id: str,
    thread_id: str,
    scope: str = _DEFAULT_SCOPE,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    now: int | None = None,
) -> str:
    """Create a short-lived opaque context token for Hermes tool calls."""
    issued_at = int(time.time()) if now is None else now
    expires_at = issued_at + ttl_seconds
    payload = [
        tenant_id,
        user_id,
        thread_id,
        scope,
        expires_at,
        secrets.token_urlsafe(9),
    ]
    payload_b64 = _b64encode(_canonical_json_array(payload))
    signature_b64 = _b64encode(_sign(payload_b64.encode("ascii"))[:16])
    return f"{_CONTEXT_REF_PREFIX}{payload_b64}.{signature_b64}"


def create_signed_atlas_context_ref(
    *,
    tenant_id: str,
    user_id: str,
    thread_id: str,
    scope: str = _DEFAULT_SCOPE,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    now: int | None = None,
) -> str:
    """Create the legacy stateless signed context reference format."""
    issued_at = int(time.time()) if now is None else now
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "scope": scope,
        "exp": issued_at + ttl_seconds,
        "nonce": uuid.uuid4().hex,
    }
    payload_bytes = _canonical_json(payload)
    payload_b64 = _b64encode(payload_bytes)
    signature_b64 = _b64encode(_sign(payload_b64.encode("ascii")))
    return f"{payload_b64}.{signature_b64}"


def verify_atlas_context_ref(
    context_ref: str,
    *,
    required_scope: str = _DEFAULT_SCOPE,
    now: int | None = None,
) -> AtlasToolContext:
    """Verify and decode an Nous context reference."""
    current_time = int(time.time()) if now is None else now
    if context_ref.startswith(_CONTEXT_REF_PREFIX):
        return _verify_compact_context_ref(
            context_ref,
            required_scope=required_scope,
            current_time=current_time,
        )

    try:
        payload_b64, signature_b64 = context_ref.split(".", 1)
    except ValueError as exc:
        raise AtlasContextError("Invalid context reference") from exc

    expected_signature = _b64encode(_sign(payload_b64.encode("ascii")))
    if not hmac.compare_digest(signature_b64, expected_signature):
        raise AtlasContextError("Invalid context signature")

    try:
        payload = json.loads(_b64decode(payload_b64))
    except (json.JSONDecodeError, ValueError) as exc:
        raise AtlasContextError("Invalid context payload") from exc

    expires_at = _require_int(payload, "exp")
    if expires_at < current_time:
        raise AtlasContextError("Context reference expired")

    scope = _require_str(payload, "scope")
    if scope != required_scope:
        raise AtlasContextError("Context reference scope is not allowed")

    return AtlasToolContext(
        tenant_id=_require_str(payload, "tenant_id"),
        user_id=_require_str(payload, "user_id"),
        thread_id=_require_str(payload, "thread_id"),
        scope=scope,
        expires_at=expires_at,
        nonce=_require_str(payload, "nonce"),
    )


def _sign(payload: bytes) -> bytes:
    return hmac.new(_context_signing_secret(), payload, hashlib.sha256).digest()


def _context_signing_secret() -> bytes:
    secret = (
        settings.atlas_context_signing_secret
        or settings.supabase_jwt_secret
        or settings.aethos_hermes_tool_token
    )
    if not secret:
        raise AtlasContextError("Nous context signing secret is not configured")
    return secret.encode("utf-8")


def _verify_compact_context_ref(
    context_ref: str,
    *,
    required_scope: str,
    current_time: int,
) -> AtlasToolContext:
    token = context_ref[len(_CONTEXT_REF_PREFIX):]
    try:
        payload_b64, signature_b64 = token.split(".", 1)
    except ValueError as exc:
        raise AtlasContextError("Invalid context reference") from exc

    expected_signature = _b64encode(_sign(payload_b64.encode("ascii"))[:16])
    if not hmac.compare_digest(signature_b64, expected_signature):
        raise AtlasContextError("Invalid context signature")

    try:
        payload = json.loads(_b64decode(payload_b64))
    except (json.JSONDecodeError, ValueError) as exc:
        raise AtlasContextError("Invalid context payload") from exc
    if not isinstance(payload, list) or len(payload) != 6:
        raise AtlasContextError("Invalid context payload")

    tenant_id, user_id, thread_id, scope, expires_at, nonce = payload
    if not isinstance(expires_at, int):
        raise AtlasContextError("Context payload missing exp")
    if expires_at < current_time:
        raise AtlasContextError("Context reference expired")
    if scope != required_scope:
        raise AtlasContextError("Context reference scope is not allowed")
    for value, name in (
        (tenant_id, "tenant_id"),
        (user_id, "user_id"),
        (thread_id, "thread_id"),
        (scope, "scope"),
        (nonce, "nonce"),
    ):
        if not isinstance(value, str) or not value:
            raise AtlasContextError(f"Context payload missing {name}")
    return AtlasToolContext(
        tenant_id=tenant_id,
        user_id=user_id,
        thread_id=thread_id,
        scope=scope,
        expires_at=expires_at,
        nonce=nonce,
    )


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _canonical_json_array(payload: list[Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}").decode("utf-8")


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise AtlasContextError(f"Context payload missing {key}")
    return value


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise AtlasContextError(f"Context payload missing {key}")
    return value
