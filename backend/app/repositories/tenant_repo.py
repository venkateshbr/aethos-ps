"""Tenant repository — thin async data-access layer for the tenants table.

Uses the Supabase service-role client so it can bypass RLS during tenant
provisioning (before the new user is added to tenant_users).  Every method is
explicit about which columns it touches — no ``SELECT *`` in write paths.

Thread safety: supabase-py v2 sync client is used from async FastAPI handlers.
The calls are short DB round-trips so the overhead of anyio.to_thread is
acceptable; this module wraps them in `asyncio.to_thread` for non-blocking IO.
"""

from __future__ import annotations

import asyncio
import logging

from app.domain.exceptions import TenantNotFoundError
from supabase import Client

logger = logging.getLogger(__name__)


class TenantRepository:
    """CRUD helpers for the ``tenants`` table using service-role client."""

    def __init__(self, service_role_client: Client) -> None:
        self.client = service_role_client

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, tenant_id: str) -> dict | None:
        """Return a tenant row by primary key, or None."""

        def _get() -> dict | None:
            result = (
                self.client.table("tenants")
                .select("*")
                .eq("id", tenant_id)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    async def get_by_stripe_customer(self, customer_id: str) -> dict | None:
        """Return the tenant whose ``stripe_customer_id`` matches, or None.

        Used by webhook handlers to look up a tenant from an incoming Stripe event.
        """

        def _get() -> dict | None:
            result = (
                self.client.table("tenants")
                .select(
                    "id, name, stripe_customer_id, stripe_subscription_status, "
                    "stripe_subscription_event_at"
                )
                .eq("stripe_customer_id", customer_id)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    async def get_by_user_email(self, email: str) -> dict | None:
        """Return the tenant for a user email, joining through tenant_users.

        Used during idempotent signup to find an existing tenant when the
        Supabase auth user already exists.
        """

        def _get() -> dict | None:
            result = self.client.rpc(
                "get_tenant_for_email",
                {"p_email": email},
            ).execute()
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_tenant(self, data: dict) -> dict:
        """Insert a new tenant row.  Returns the created row.

        Caller is responsible for including all required fields:
        ``id``, ``name``, ``slug``, ``base_currency``, ``country``,
        ``status``, ``plan_tier``.
        """

        def _create() -> dict:
            result = self.client.table("tenants").insert(data).execute()
            if not result.data:
                raise RuntimeError("Tenant insert returned no data")
            return result.data[0]

        row = await asyncio.to_thread(_create)
        logger.info("Tenant created", extra={"tenant_id": row.get("id")})
        return row

    async def update_tenant(self, tenant_id: str, data: dict) -> dict:
        """Update specific columns on a tenant row.  Returns the updated row."""

        def _update() -> dict:
            result = (
                self.client.table("tenants")
                .update(data)
                .eq("id", tenant_id)
                .execute()
            )
            if not result.data:
                raise TenantNotFoundError(f"Tenant {tenant_id!r} not found")
            return result.data[0]

        row = await asyncio.to_thread(_update)
        logger.info(
            "Tenant updated",
            extra={"tenant_id": tenant_id, "fields": list(data.keys())},
        )
        return row

    # ------------------------------------------------------------------
    # Tenant users
    # ------------------------------------------------------------------

    async def create_tenant_user(self, data: dict) -> dict:
        """Insert a row in ``tenant_users``.

        Required keys: ``tenant_id``, ``user_id``, ``role``.
        """

        def _create() -> dict:
            result = self.client.table("tenant_users").insert(data).execute()
            if not result.data:
                raise RuntimeError("tenant_users insert returned no data")
            return result.data[0]

        return await asyncio.to_thread(_create)

    # ------------------------------------------------------------------
    # Webhook idempotency
    # ------------------------------------------------------------------

    async def get_webhook_event(self, provider_event_id: str) -> dict | None:
        """Return a webhook_events row if this event has been processed."""

        def _get() -> dict | None:
            result = (
                self.client.table("webhook_events")
                .select("id, provider_event_id, processed_at")
                .eq("provider_event_id", provider_event_id)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    async def record_webhook_event(
        self,
        provider_event_id: str,
        event_type: str,
        tenant_id: str | None = None,
    ) -> None:
        """Record that a webhook event has been processed (idempotency log)."""

        def _insert() -> None:
            self.client.table("webhook_events").insert(
                {
                    "provider_event_id": provider_event_id,
                    "event_type": event_type,
                    "tenant_id": tenant_id,
                    "provider": "stripe",
                }
            ).execute()

        await asyncio.to_thread(_insert)
