"""Private, deterministic Nous channel. No model or user-supplied tool dispatch."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import secrets
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.core.rbac import UserRole, role_meets_minimum
from app.core.tenant import _lookup_active_membership, assert_tenant_write_access
from app.repositories.chat_repo import ChatRepository
from app.repositories.telegram_erp_repo import TelegramErpRepository, deadline
from app.services.atlas_context import AtlasToolContext
from app.services.security_service import SecurityService
from supabase import Client

logger = logging.getLogger(__name__)
_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
_NOT_LINKED = "No active ERP link. Link this sender from your authenticated ERP session."
_NO_CONFIRMATION = (
    "Confirmation is invalid, expired, or already used. Check the ERP Inbox before trying again."
)
_FAILED = "Could not complete the request. Check the ERP Inbox before retrying any change."
_HELP = "Commands: /id, /ar, /draft <engagement UUID> <start YYYY-MM-DD> <end YYYY-MM-DD>, /confirm <code>, /unlink. Use Nous in the ERP for other requests."
ToolDispatch = Callable[[Client, AtlasToolContext, str, dict[str, Any]], Awaitable[Any]]


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _draft_arguments(parts: list[str]) -> dict[str, str] | None:
    if len(parts) != 3:
        return None
    try:
        engagement = str(UUID(parts[0]))
        start, end = (date.fromisoformat(value).isoformat() for value in parts[1:])
    except ValueError:
        return None
    if [engagement, start, end] != parts or start > end:
        return None
    return {"engagement_id": engagement, "period_start": start, "period_end": end}


class TelegramErpService:
    def __init__(self, db: Client, dispatch: ToolDispatch) -> None:
        self.db = db
        self.repo = TelegramErpRepository(db)
        self.dispatch = dispatch

    def issue(self, tenant_id: str, user_id: str, sender: int) -> str:
        membership = _lookup_active_membership(self.db, tenant_id=tenant_id, user_id=user_id)
        if not self._erp_member(membership):
            raise HTTPException(403, "An active ERP membership is required")
        assert membership is not None
        token = secrets.token_urlsafe(32)
        if not self.repo.issue(tenant_id, user_id, str(membership["id"]), sender, _digest(token)):
            raise HTTPException(409, "Revoke the existing link or outstanding challenge first")
        return token

    def revoke(self, tenant_id: str, user_id: str) -> None:
        self.repo.revoke(tenant_id, user_id)

    async def handle(self, sender: int, update_id: int, sent_at: int, text: str) -> str | None:
        command, *parts = text.split()
        if command == "/id" and not parts:
            return f"Your Telegram sender ID is {sender}."
        if command == "/start" and len(parts) == 1 and _TOKEN.fullmatch(parts[0]):
            linked = await asyncio.to_thread(self.repo.redeem, sender, _digest(parts[0]))
            return (
                "ERP sender linked. Send /help for available commands."
                if linked
                else "Link code unavailable. Start again from the ERP."
            )
        if command in {"/start", "/help"}:
            return _HELP

        link = await asyncio.to_thread(self.repo.lookup, sender)
        if link is None or sent_at < int(datetime.fromisoformat(link["linked_at"]).timestamp()):
            return _NOT_LINKED
        if command not in {"/ar", "/draft", "/confirm", "/unlink"}:
            return _HELP
        if not await asyncio.to_thread(self.repo.claim_delivery, link, update_id, command[1:]):
            return None
        if command == "/unlink" and not parts:
            await asyncio.to_thread(
                self.repo.revoke, link["tenant_id"], link["user_id"], link["id"]
            )
            await self._record(link, update_id, "unlinked")
            return "ERP sender unlinked."
        if not await self._authorized(sender, link, write=command in {"/draft", "/confirm"}):
            await self._record(link, update_id, "denied")
            return "This command is unavailable for your ERP account."
        if command == "/draft" and (arguments := _draft_arguments(parts)):
            token = secrets.token_urlsafe(32)
            await self._record(
                link,
                update_id,
                "awaiting_confirmation",
                arguments=arguments,
                confirmation_hash=_digest(token),
                confirmation_expires_at=deadline(minutes=5),
            )
            start, end = arguments["period_start"], arguments["period_end"]
            return (
                f"Queue an invoice draft for Inbox review only? Engagement {arguments['engagement_id']}, "
                f"period {start} to {end}. Send /confirm {token} within 5 minutes. "
                "This will not post or send an invoice."
            )
        if command == "/confirm" and len(parts) == 1 and _TOKEN.fullmatch(parts[0]):
            arguments = await asyncio.to_thread(
                self.repo.claim_confirmation, link, _digest(parts[0])
            )
            if arguments is None:
                await self._record(link, update_id, "confirmation_unavailable")
                return _NO_CONFIRMATION
            return await self._run_chat_tool(sender, link, update_id, arguments)
        if command == "/ar" and not parts:
            return await self._run_chat_tool(sender, link, update_id, None)
        await self._record(link, update_id, "invalid_command")
        return _HELP

    @staticmethod
    def _erp_member(membership: dict[str, Any] | None) -> bool:
        if not membership or membership.get("must_change_password"):
            return False
        try:
            return role_meets_minimum(UserRole(membership["role"]), UserRole.viewer)
        except ValueError:
            return False

    async def _authorized(self, sender: int, link: dict, *, write: bool) -> bool:
        tenant_id, user_id = link["tenant_id"], link["user_id"]
        membership = await asyncio.to_thread(
            _lookup_active_membership,
            self.db,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        if (
            membership is None
            or not self._erp_member(membership)
            or str(membership["id"]) != link["membership_id"]
        ):
            return False
        if write:
            try:
                await asyncio.to_thread(assert_tenant_write_access, self.db, tenant_id=tenant_id)
            except HTTPException:
                return False
            permissions = await SecurityService(self.db, tenant_id).effective_permissions(user_id)
            if "invoices.draft" not in permissions.privilege_codes:
                return False
        # Re-read the link last, after permissions and billing queries. Never
        # resume a command on a new link after an unlink/relink.
        return await asyncio.to_thread(self.repo.lookup, sender) == link

    async def _record(self, link: dict, update_id: int, outcome: str, **extra: Any) -> None:
        await asyncio.to_thread(self.repo.record, link, update_id, outcome=outcome, **extra)

    async def _run_chat_tool(
        self, sender: int, link: dict, update_id: int, arguments: dict | None
    ) -> str:
        write = arguments is not None
        tool = "aethos.o2c.draft_invoice" if write else "aethos.finance.ar_aging"
        title = "Telegram: invoice draft review" if write else "Telegram: AR aging"
        chat = ChatRepository(self.db, link["tenant_id"])
        try:
            thread = await chat.create_thread(user_id=link["user_id"], title=title)
            await chat.create_message(thread["id"], "user", title)
            if not await self._authorized(sender, link, write=write):
                await self._record(link, update_id, "denied")
                return "This command is unavailable for your ERP account."
            context = AtlasToolContext(
                tenant_id=link["tenant_id"],
                user_id=link["user_id"],
                thread_id=thread["id"],
                scope="telegram:confirmed_invoice_review" if write else "telegram:read",
                expires_at=0,
                nonce=str(update_id),  # internal only; not a broker credential
            )
            result = await self.dispatch(self.db, context, tool, arguments or {})
            suggestion_id = None
            if write:
                if not result.get("requires_review") or not result.get("suggestion_id"):
                    await self._record(
                        link, update_id, "denied" if result.get("policy_denied") else "not_queued"
                    )
                    return _FAILED
                suggestion_id = str(UUID(result["suggestion_id"]))
                reply = "Invoice draft queued for review in the ERP Inbox. No invoice was posted or sent."
            else:
                total = result.get("total")
                if not isinstance(total, str) or not re.fullmatch(
                    r"-?[0-9]{1,30}\.[0-9]{2}", total
                ):
                    raise ValueError("Invalid aging total")
                reply = f"Posted accounts receivable total: {total} (workspace base currency)."
            await self._record(
                link, update_id, "queued" if write else "read", suggestion_id=suggestion_id
            )
            # Never ship raw broker output. Suppress even the safe projection
            # if access was revoked while the operation was in flight.
            if not await self._authorized(sender, link, write=write):
                return "This command is unavailable for your ERP account."
            await chat.create_message(
                thread["id"], "assistant", reply, tool_name=tool, model="nous:telegram"
            )
            if await asyncio.to_thread(self.repo.lookup, sender) != link:
                return _NOT_LINKED
            return reply
        except Exception:
            # No DB exceptions, command text, tokens, sender IDs, or payloads in logs.
            logger.warning(
                "telegram_erp_tool_failed",
                extra={"tenant_id": link["tenant_id"], "tool_name": tool},
            )
            return _FAILED
