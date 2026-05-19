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

from app.core.config import settings
from supabase import Client, create_client


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

    Use sparingly.  Document every call-site that uses this.
    """
    return _service_role_client()
