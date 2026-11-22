"""Service-role state for one dedicated bot. CAS operations use PostgreSQL constraints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from postgrest.exceptions import APIError

from supabase import Client


def deadline(**offset: int) -> str:
    return (datetime.now(UTC) + timedelta(**offset)).isoformat()


class TelegramErpRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def issue(
        self, tenant_id: str, user_id: str, membership_id: str, sender: int, digest: str
    ) -> bool:
        self._delete_for_user(tenant_id, user_id).lte("expires_at", deadline()).execute()
        try:
            self.db.table("telegram_erp_links").insert(
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "membership_id": membership_id,
                    "sender_id": sender,
                    "challenge_hash": digest,
                    "expires_at": deadline(minutes=5),
                }
            ).execute()
        except APIError as exc:
            if exc.code == "23505":
                return False
            raise
        return True

    def redeem(self, sender: int, digest: str) -> bool:
        # Telegram has no tenant selector: this unique capability + sender pair
        # is the only cross-tenant rendezvous. Never return identity data to the DM.
        try:
            return bool(
                self.db.table("telegram_erp_links")
                .update(
                    {
                        "challenge_hash": None,
                        "linked_at": deadline(),
                        "expires_at": deadline(days=30),
                    }
                )
                .eq("sender_id", sender)
                .eq("challenge_hash", digest)
                .is_("linked_at", "null")
                .gt("expires_at", deadline())
                .execute()
                .data
            )
        except APIError as exc:
            if exc.code == "23505":
                return False
            raise

    def lookup(self, sender: int) -> dict[str, Any] | None:
        rows = (
            self.db.table("telegram_erp_links")
            .select("id,tenant_id,user_id,membership_id,linked_at")
            .eq("sender_id", sender)
            .not_.is_("linked_at", "null")
            .gt("expires_at", deadline())
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None

    def revoke(self, tenant_id: str, user_id: str, link_id: str | None = None) -> None:
        query = self._delete_for_user(tenant_id, user_id)
        if link_id is not None:
            query = query.eq("id", link_id)
        query.execute()

    def _delete_for_user(self, tenant_id: str, user_id: str) -> Any:
        return (
            self.db.table("telegram_erp_links")
            .delete()
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
        )

    def claim_delivery(self, link: dict, update_id: int, command: str) -> bool:
        rows = (
            self.db.table("telegram_erp_deliveries")
            .upsert(
                {
                    "update_id": update_id,
                    "tenant_id": link["tenant_id"],
                    "user_id": link["user_id"],
                    "link_id": link["id"],
                    "command": command,
                },
                on_conflict="update_id",
                ignore_duplicates=True,
            )
            .execute()
            .data
        )
        return bool(rows)

    def record(self, link: dict, update_id: int, **values: Any) -> None:
        self._deliveries(link, values).eq("update_id", update_id).execute()

    def claim_confirmation(self, link: dict, digest: str) -> dict[str, Any] | None:
        # Select the immutable arguments first; only the winner of the CAS is
        # allowed to execute them. Clear the capability and payload on claim.
        rows = (
            self._deliveries(link)
            .eq("confirmation_hash", digest)
            .eq("command", "draft")
            .gt("confirmation_expires_at", deadline())
            .execute()
            .data
        )
        if not rows:
            return None
        pending = rows[0]
        won = (
            self._deliveries(
                link,
                {
                    "confirmation_hash": None,
                    "arguments": None,
                    "outcome": "confirmed",
                },
            )
            .eq("update_id", pending["update_id"])
            .eq("confirmation_hash", digest)
            .gt("confirmation_expires_at", deadline())
            .execute()
            .data
        )
        return pending["arguments"] if won else None

    def _deliveries(self, link: dict, values: dict | None = None) -> Any:
        table = self.db.table("telegram_erp_deliveries")
        query = table.update(values) if values is not None else table.select("update_id,arguments")
        return (
            query.eq("tenant_id", link["tenant_id"])
            .eq("user_id", link["user_id"])
            .eq("link_id", link["id"])
        )
