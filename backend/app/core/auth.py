"""Supabase JWT validation and FastAPI auth dependency.

The Supabase JWT is a HS256-signed token.  The JWT secret comes from the
Supabase project settings (not the anon key).

Never log the raw token or any field that might contain PII beyond what is
necessary for debugging (user_id is fine; email is PII — omit from error logs).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


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

    Raises ``HTTP 401`` on missing or invalid token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload: dict = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
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
