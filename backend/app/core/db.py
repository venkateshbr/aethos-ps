"""Supabase client factories and FastAPI dependencies.

Two clients are provided:
1. ``get_anon_client`` — uses the anon key; subject to Row-Level Security.
   Use for regular tenant-scoped operations after a user is authenticated.
2. ``get_service_role_client`` — bypasses RLS.  ONLY for:
   - Tenant provisioning during signup (user not yet in tenant_users).
   - Webhook handlers that process events before any user session exists.
   - Admin / super-admin operations.

Never expose the service-role client to untrusted callers.

The supabase-py v2 sync Client is synchronous; we use asyncio.to_thread in
repositories to avoid blocking the event loop.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from supabase import Client, create_client

_rls_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _anon_client() -> Client:
    """Singleton anon client (anon key, RLS enforced)."""
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache(maxsize=1)
def _service_role_client() -> Client:
    """Singleton service-role client (bypasses RLS).

    Only used for signup provisioning and webhook processing.
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_anon_client() -> Client:
    """FastAPI dependency: return the shared anon supabase client."""
    return _anon_client()


def get_service_role_client() -> Client:
    """FastAPI dependency: return the service-role supabase client.

    NOTE: We return a FRESH client per-request (not the singleton) to avoid
    thread-safety issues when many concurrent requests share the same
    supabase-py Client under load.  The singleton is still used for signup
    and webhook paths (low-concurrency, already correct).  High-concurrency
    authenticated routes inject a fresh client each request; the overhead is
    acceptable (TLS connection pooling is handled by httpx).

    Use sparingly.  Document every call-site that uses this.
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_user_rls_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(_rls_bearer_scheme),  # noqa: B008
) -> Client:
    """FastAPI dependency: return an anon-key Supabase client carrying the caller JWT.

    Use this for authenticated tenant-scoped routes when the operation can rely
    on Postgres RLS. The route should still inject ``get_tenant_id`` so the API
    verifies membership before calling the service layer; RLS then becomes a
    second enforcement boundary instead of being bypassed by service-role.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(credentials.credentials)
    return client
