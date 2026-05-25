"""Supabase JWT validation and FastAPI auth dependency.

Supabase rolled out asymmetric JWT signing (ECDSA P-256 / ES256, with JWKS-
based key resolution) as the default for new projects in late 2025. Existing
projects retain a legacy HS256 path keyed off ``SUPABASE_JWT_SECRET``.

This module accepts BOTH:

  - **ES256 / RS256** (Supabase's modern path) — the token header's ``kid``
    indexes into ``/auth/v1/.well-known/jwks.json``; we resolve the matching
    public key, verify, and decode.
  - **HS256** (legacy + test fixtures) — verified against
    ``SUPABASE_JWT_SECRET`` as before. The test harness's ``mint_jwt``
    still signs HS256 so existing tests keep passing.

JWKS is cached (LRU) — Supabase rotates rarely and we don't want to make a
network call per request. If a key rotation makes a token unverifiable,
``InvalidKidError`` is raised, the cache is cleared, and the request retries
once with a fresh fetch.

Never log the raw token or any field that might contain PII beyond what is
necessary for debugging (user_id is fine; email is PII — omit from error logs).

Fixes #124.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Algorithms accepted on the asymmetric path. Supabase emits ES256 today; we
# keep RS256 in case a future rotation moves to RSA.
_ASYMMETRIC_ALGS: tuple[str, ...] = ("ES256", "RS256")


class _InvalidKidError(Exception):
    """Token's `kid` header doesn't match any cached JWKS key. Triggers a refetch."""


@lru_cache(maxsize=1)
def _jwks() -> dict:
    """Fetch and cache the Supabase project's JWKS.

    Cleared on `_InvalidKidError` so a key rotation self-heals on the next
    request. Network failure surfaces as a 503-equivalent — `get_current_user`
    translates it to 401 to avoid leaking infra state to unauthenticated callers.
    """
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    response = httpx.get(url, timeout=5.0)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or "keys" not in data:
        raise ValueError(f"Malformed JWKS response from {url}: {data!r}")
    return data


def _signing_key_for(token: str) -> dict:
    """Return the JWK that signed this token, or raise `_InvalidKidError`."""
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise _InvalidKidError("Token header has no `kid`")
    for key in _jwks().get("keys", []):
        if key.get("kid") == kid:
            return key
    raise _InvalidKidError(f"No JWKS key matches kid={kid}")


def _decode_token(token: str) -> dict:
    """Decode + verify a Supabase JWT. Supports HS256 and ES256/RS256."""
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "")

    if alg == "HS256":
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

    if alg in _ASYMMETRIC_ALGS:
        # Try with the cached JWKS first; on `kid` miss, clear and retry once.
        try:
            key = _signing_key_for(token)
        except _InvalidKidError:
            _jwks.cache_clear()
            key = _signing_key_for(token)  # second miss → caller catches
        return jwt.decode(
            token,
            key,
            algorithms=[alg],
            options={"verify_aud": False},
        )

    raise JWTError(f"Unsupported JWT algorithm: {alg!r}")


@dataclass(frozen=True)
class CurrentUser:
    """Decoded, validated JWT claims for the authenticated caller."""

    user_id: str
    email: str
    role: str  # Supabase role — "authenticated", "anon", or custom (RBAC role in app_metadata)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> CurrentUser:
    """FastAPI dependency: decode and validate the Supabase JWT.

    Accepts HS256 (legacy + test fixtures) and ES256/RS256 (Supabase's
    modern asymmetric path via JWKS). Raises ``HTTP 401`` on missing
    or invalid token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload: dict = _decode_token(token)
    except (JWTError, _InvalidKidError, httpx.HTTPError, ValueError) as exc:
        logger.debug("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id: str | None = payload.get("sub")
    email: str = payload.get("email", "")
    # Supabase puts the Postgres role in "role"; RBAC role may live in app_metadata
    supabase_role: str = payload.get("role", "authenticated")
    app_metadata: dict = payload.get("app_metadata", {})
    # If the app has set a custom role in app_metadata, prefer that
    app_role: str = app_metadata.get("role", supabase_role)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(user_id=user_id, email=email, role=app_role)
