"""Dedicated Telegram Bot API webhook and authenticated ERP link management."""

from __future__ import annotations

import hmac
import json
import re
import time
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.v1.endpoints.atlas_tools import dispatch_atlas_tool
from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.services.telegram_erp_service import TelegramErpService
from supabase import Client

router = APIRouter()
_SECRET = re.compile(r"[A-Za-z0-9_-]{32,256}")
_TelegramId = Annotated[int, Field(strict=True, ge=1, le=2**52 - 1)]


def _enabled() -> None:
    if not settings.telegram_erp_enabled or not _SECRET.fullmatch(
        settings.telegram_erp_webhook_secret
    ):
        raise HTTPException(404, "Not found")


def _verify_webhook(request: Request) -> None:
    _enabled()
    values = request.headers.getlist("X-Telegram-Bot-Api-Secret-Token")
    if len(values) != 1 or not hmac.compare_digest(
        values[0].encode(), settings.telegram_erp_webhook_secret.encode()
    ):
        raise HTTPException(401, "Invalid webhook credential")


class LinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sender_id: _TelegramId


class LinkChallenge(BaseModel):
    start_payload: str
    expires_in_seconds: Literal[300] = 300


class _Chat(BaseModel):
    id: _TelegramId
    type: Literal["private"]


class _Sender(BaseModel):
    id: _TelegramId
    is_bot: Annotated[bool, Field(strict=True)]


class _Message(BaseModel):
    chat: _Chat
    sender: _Sender = Field(alias="from")
    text: Annotated[str, Field(strict=True, min_length=1, max_length=512)]
    date: Annotated[int, Field(strict=True, ge=1)]


class _Update(BaseModel):
    update_id: Annotated[int, Field(strict=True, ge=0, le=2**52 - 1)]
    message: _Message


def _private_update(raw: object) -> _Update | None:
    if not isinstance(raw, dict) or set(raw) != {"update_id", "message"}:
        return None
    message = raw["message"]
    if not isinstance(message, dict) or message.keys() & {
        "sender_chat",
        "forward_origin",
        "forward_from",
        "forward_from_chat",
        "forward_date",
        "forward_sender_name",
        "is_automatic_forward",
        "via_bot",
        "business_connection_id",
    }:
        return None
    try:
        update = _Update.model_validate(raw)
    except ValidationError:
        return None
    msg = update.message
    if (
        msg.sender.is_bot
        or msg.sender.id != msg.chat.id
        or not msg.text.strip()
        or not -30 <= time.time() - msg.date <= 300
    ):
        return None
    return update


@router.post(
    "/link", response_model=LinkChallenge, status_code=201, dependencies=[Depends(_enabled)]
)
def create_link_challenge(
    payload: LinkRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    db: Annotated[Client, Depends(get_service_role_client)],
    response: Response,
) -> LinkChallenge:
    response.headers["Cache-Control"] = "no-store"
    service = TelegramErpService(db, dispatch_atlas_tool)
    return LinkChallenge(start_payload=service.issue(tenant_id, user.user_id, payload.sender_id))


@router.delete("/link", status_code=204)
def revoke_link(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Client, Depends(get_service_role_client)],
    tenant_id: Annotated[UUID, Header(alias="X-Tenant-ID")],
) -> Response:
    # Revocation remains available when disabled or if membership/billing
    # changed. It only deletes this authenticated subject's own link/challenge.
    if not settings.telegram_erp_enabled and not settings.telegram_erp_webhook_secret:
        raise HTTPException(404, "Not found")
    service = TelegramErpService(db, dispatch_atlas_tool)
    service.revoke(str(tenant_id), user.user_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/webhook", include_in_schema=False, dependencies=[Depends(_verify_webhook)])
async def telegram_webhook(
    request: Request,
    db: Annotated[Client, Depends(get_service_role_client)],
) -> JSONResponse:
    # Avoid FastAPI validation echoing webhook bodies (including link codes).
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 16_384:
            raise HTTPException(413, "Update too large")
        body.extend(chunk)
    try:
        update = _private_update(json.loads(body))
    except (ValueError, RecursionError):
        update = None
    response: dict = {}
    if update is not None:
        service = TelegramErpService(db, dispatch_atlas_tool)
        msg = update.message
        reply = await service.handle(msg.sender.id, update.update_id, msg.date, msg.text)
        if reply:
            response = {
                "method": "sendMessage",
                "chat_id": msg.sender.id,
                "text": reply,
                "protect_content": True,
            }
    # Telegram performs sendMessage from this webhook reply. Aethos does not
    # need a bot token or issue outbound requests with user-controlled targets.
    return JSONResponse(response, headers={"Cache-Control": "no-store"})
