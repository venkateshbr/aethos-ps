"""JWT verification contract for the Supabase auth boundary (#384).

These tests are deliberately **implementation-independent** — they exercise the
public ``get_current_user`` behaviour, not python-jose vs PyJWT internals — so
they pin token compatibility across the library migration:

  - HS256 (legacy + test fixtures) verified against ``SUPABASE_JWT_SECRET``.
  - ES256 / RS256 (Supabase's asymmetric path) resolved via a JWKS ``kid``.
  - JWKS caching + rotation self-heal (kid miss → refetch once).
  - Negative paths: alg ``none``, unknown ``kid``, wrong key, wrong algorithm
    family, expired token, missing ``sub``, missing/blank credentials.

Tokens are minted with PyJWT (a stable dependency on both sides of the
migration); the JWKS fetch is monkeypatched so no network is required.
"""

from __future__ import annotations

import base64
import json
import time

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import app.core.auth as auth_module
from app.core.auth import get_current_user
from app.core.config import settings

pytestmark = pytest.mark.unit

# ≥32 bytes so PyJWT's HS256 minting does not warn; the same singleton is read by
# the auth module, so pinning it here makes the HS256 path deterministic offline.
_TEST_HS_SECRET = "unit-test-supabase-jwt-secret-0123456789abcdef"


@pytest.fixture(autouse=True)
def _pin_hs_secret(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", _TEST_HS_SECRET)


# --------------------------------------------------------------------------
# Key + JWK helpers
# --------------------------------------------------------------------------


def _b64url_uint(value: int, size: int) -> str:
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


def _ec_jwk(public_key: ec.EllipticCurvePublicKey, kid: str) -> dict:
    nums = public_key.public_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64url_uint(nums.x, 32),
        "y": _b64url_uint(nums.y, 32),
        "kid": kid,
        "alg": "ES256",
        "use": "sig",
    }


def _rsa_jwk(public_key: rsa.RSAPublicKey, kid: str) -> dict:
    nums = public_key.public_numbers()
    n_len = (nums.n.bit_length() + 7) // 8
    e_len = (nums.e.bit_length() + 7) // 8
    return {
        "kty": "RSA",
        "n": _b64url_uint(nums.n, n_len),
        "e": _b64url_uint(nums.e, e_len),
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
    }


def _claims(**overrides) -> dict:
    now = int(time.time())
    base = {
        "sub": "user-123",
        "email": "owner@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "iss": "https://project.supabase.co/auth/v1",
        "app_metadata": {"role": "admin"},
    }
    base.update(overrides)
    return base


def _patch_jwks(monkeypatch, jwks: dict) -> list[int]:
    """Point ``_jwks()`` at an in-memory JWKS; return a fetch counter."""
    calls: list[int] = []

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return jwks

    def _fake_get(url, timeout=None):
        calls.append(1)
        return _Resp()

    auth_module._jwks.cache_clear()
    monkeypatch.setattr(auth_module.httpx, "get", _fake_get)
    return calls


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# --------------------------------------------------------------------------
# HS256 (legacy + fixtures)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hs256_valid_token_authenticates() -> None:
    token = pyjwt.encode(_claims(), settings.supabase_jwt_secret, algorithm="HS256")
    user = await get_current_user(_creds(token))
    assert user.user_id == "user-123"
    assert user.email == "owner@example.com"
    assert user.role == "admin"  # app_metadata.role wins over the Postgres role


@pytest.mark.asyncio
async def test_hs256_wrong_secret_rejected() -> None:
    token = pyjwt.encode(_claims(), "not-the-real-secret", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_rejected() -> None:
    token = pyjwt.encode(
        _claims(exp=int(time.time()) - 10), settings.supabase_jwt_secret, algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_sub_rejected() -> None:
    claims = _claims()
    claims.pop("sub")
    token = pyjwt.encode(claims, settings.supabase_jwt_secret, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_credentials_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)
    assert exc.value.status_code == 401


# --------------------------------------------------------------------------
# ES256 / RS256 asymmetric path (JWKS) — the production Supabase path
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_es256_valid_token_via_jwks(monkeypatch) -> None:
    priv = ec.generate_private_key(ec.SECP256R1())
    jwk = _ec_jwk(priv.public_key(), kid="ec-kid-1")
    _patch_jwks(monkeypatch, {"keys": [jwk]})

    token = pyjwt.encode(_claims(), priv, algorithm="ES256", headers={"kid": "ec-kid-1"})
    user = await get_current_user(_creds(token))
    assert user.user_id == "user-123"
    assert user.role == "admin"


@pytest.mark.asyncio
async def test_rs256_valid_token_via_jwks(monkeypatch) -> None:
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(priv.public_key(), kid="rsa-kid-1")
    _patch_jwks(monkeypatch, {"keys": [jwk]})

    token = pyjwt.encode(_claims(), priv, algorithm="RS256", headers={"kid": "rsa-kid-1"})
    user = await get_current_user(_creds(token))
    assert user.user_id == "user-123"


@pytest.mark.asyncio
async def test_unknown_kid_rejected(monkeypatch) -> None:
    priv = ec.generate_private_key(ec.SECP256R1())
    jwk = _ec_jwk(priv.public_key(), kid="server-kid")
    _patch_jwks(monkeypatch, {"keys": [jwk]})

    token = pyjwt.encode(_claims(), priv, algorithm="ES256", headers={"kid": "other-kid"})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_key_rotation_self_heals(monkeypatch) -> None:
    """A rotated signing key (new kid) misses the cache, refetches, and verifies.

    Models Supabase's real rotation shape: a fresh key is published under a new
    ``kid``. The first lookup misses the cached JWKS → the cache clears → the
    refetch resolves the new key.
    """
    old = ec.generate_private_key(ec.SECP256R1())
    new = ec.generate_private_key(ec.SECP256R1())
    state = {"jwks": {"keys": [_ec_jwk(old.public_key(), kid="kid-old")]}}
    calls: list[int] = []

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return state["jwks"]

    def _fake_get(url, timeout=None):
        calls.append(1)
        return _Resp()

    auth_module._jwks.cache_clear()
    monkeypatch.setattr(auth_module.httpx, "get", _fake_get)

    auth_module._jwks()  # prime cache with the old key
    assert len(calls) == 1

    # Server rotates to a new key under a new kid.
    state["jwks"] = {"keys": [_ec_jwk(new.public_key(), kid="kid-new")]}
    token = pyjwt.encode(_claims(), new, algorithm="ES256", headers={"kid": "kid-new"})

    user = await get_current_user(_creds(token))
    assert user.user_id == "user-123"
    assert len(calls) == 2  # primed once, refetched once after the kid miss


@pytest.mark.asyncio
async def test_alg_none_rejected(monkeypatch) -> None:
    _patch_jwks(monkeypatch, {"keys": []})
    # Unsigned token with alg=none.
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(_claims()).encode()).rstrip(b"=")
    token = f"{header.decode()}.{body.decode()}."
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_algorithm_confusion_hs256_with_jwks_kid_rejected(monkeypatch) -> None:
    """A token claiming HS256 but pointing its ``kid`` at a JWKS asymmetric key
    must NOT be verified against that public key — the HS256 path only trusts the
    configured shared secret, so an attacker-chosen secret is rejected."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(priv.public_key(), kid="rsa-kid-1")
    _patch_jwks(monkeypatch, {"keys": [jwk]})
    token = pyjwt.encode(
        _claims(), "attacker-chosen-secret", algorithm="HS256", headers={"kid": "rsa-kid-1"}
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_creds(token))
    assert exc.value.status_code == 401
