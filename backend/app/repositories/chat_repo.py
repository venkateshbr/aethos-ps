"""Chat repository — thread and message persistence for the copilot.

Uses the anon (RLS-enforced) client so tenant isolation is enforced at the
Postgres layer via ``app.current_tenant_id``.  The caller is responsible for
setting that session variable before using this repo.

All DB calls are synchronous supabase-py calls wrapped in asyncio.to_thread
to avoid blocking the FastAPI event loop.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from supabase import Client

logger = logging.getLogger(__name__)


class ChatRepository:
    """CRUD helpers for ``chat_threads`` and ``chat_messages``."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Threads
    # ------------------------------------------------------------------

    async def create_thread(self, user_id: str, title: str | None = None) -> dict:
        """Insert a new chat thread and return the created row."""

        data: dict = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        if title is not None:
            data["title"] = title

        def _insert() -> dict:
            result = self.db.table("chat_threads").insert(data).execute()
            if not result.data:
                raise RuntimeError("chat_threads insert returned no data")
            return result.data[0]

        row = await asyncio.to_thread(_insert)
        logger.info(
            "Chat thread created",
            extra={"tenant_id": self.tenant_id, "thread_id": row.get("id")},
        )
        return row

    async def list_threads(self, user_id: str, limit: int = 20) -> list[dict]:
        """Return active threads for a user, newest first."""

        def _list() -> list[dict]:
            result = (
                self.db.table("chat_threads")
                .select("id, title, created_at, updated_at")
                .eq("tenant_id", self.tenant_id)
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .order("updated_at", desc=True)
                .limit(min(limit, 100))
                .execute()
            )
            return result.data or []

        return await asyncio.to_thread(_list)

    async def get_thread(self, thread_id: str) -> dict | None:
        """Return a single thread row, or None if not found / deleted."""

        def _get() -> dict | None:
            result = (
                self.db.table("chat_threads")
                .select("id, title, tenant_id, user_id, created_at, updated_at")
                .eq("id", thread_id)
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_get)

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def create_message(
        self,
        thread_id: str,
        role: str,
        content: str | None,
        *,
        tool_name: str | None = None,
        tool_input: dict | None = None,
        tool_output: dict | None = None,
        finish_reason: str | None = None,
        model: str | None = None,
        usage_input_tokens: int | None = None,
        usage_output_tokens: int | None = None,
    ) -> dict:
        """Append a message to a thread and return the created row.

        Valid roles: ``user`` | ``assistant`` | ``tool`` | ``system``.
        """
        data: dict = {
            "thread_id": thread_id,
            "tenant_id": self.tenant_id,
            "role": role,
            "content": content,
        }
        if tool_name is not None:
            data["tool_name"] = tool_name
        if tool_input is not None:
            data["tool_input"] = tool_input
        if tool_output is not None:
            data["tool_output"] = tool_output
        if finish_reason is not None:
            data["finish_reason"] = finish_reason
        if model is not None:
            data["model"] = model
        if usage_input_tokens is not None:
            data["usage_input_tokens"] = usage_input_tokens
        if usage_output_tokens is not None:
            data["usage_output_tokens"] = usage_output_tokens

        def _insert() -> dict:
            result = self.db.table("chat_messages").insert(data).execute()
            if not result.data:
                raise RuntimeError("chat_messages insert returned no data")
            self._touch_thread(thread_id=thread_id, role=role, content=content)
            return result.data[0]

        row = await asyncio.to_thread(_insert)
        logger.debug(
            "Chat message persisted",
            extra={
                "tenant_id": self.tenant_id,
                "thread_id": thread_id,
                "role": role,
            },
        )
        return row

    async def list_messages(self, thread_id: str, limit: int = 50) -> list[dict]:
        """Return messages for a thread in chronological order."""

        def _list() -> list[dict]:
            result = (
                self.db.table("chat_messages")
                .select(
                    "id, role, content, tool_name, finish_reason, "
                    "model, usage_input_tokens, usage_output_tokens, created_at"
                )
                .eq("thread_id", thread_id)
                .eq("tenant_id", self.tenant_id)
                .order("created_at", desc=False)
                .limit(min(limit, 200))
                .execute()
            )
            return result.data or []

        return await asyncio.to_thread(_list)

    def _touch_thread(self, *, thread_id: str, role: str, content: str | None) -> None:
        """Keep thread history named and sorted by real message activity."""

        patch: dict = {"updated_at": datetime.now(UTC).isoformat()}

        if role == "user":
            title = _thread_title_from_message(content)
            if title:
                thread_result = (
                    self.db.table("chat_threads")
                    .select("title")
                    .eq("id", thread_id)
                    .eq("tenant_id", self.tenant_id)
                    .execute()
                )
                existing_title = str((thread_result.data or [{}])[0].get("title") or "").strip()
                if existing_title in {"", "New conversation"}:
                    patch["title"] = title

        (
            self.db.table("chat_threads")
            .update(patch)
            .eq("id", thread_id)
            .eq("tenant_id", self.tenant_id)
            .execute()
        )


def _thread_title_from_message(content: str | None) -> str | None:
    normalized = " ".join((content or "").split())
    if not normalized:
        return None
    if len(normalized) <= 80:
        return normalized
    return f"{normalized[:77]}..."
