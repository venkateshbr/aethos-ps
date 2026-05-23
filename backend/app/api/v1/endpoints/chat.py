"""Chat router — copilot thread management and SSE streaming.

Endpoints:
    POST /api/v1/chat/threads              — create a new thread
    GET  /api/v1/chat/threads              — list threads for the current user
    POST /api/v1/chat/threads/{id}/messages — send a message; returns SSE stream

SSE frame format (text/event-stream):
    data: {"delta": "<token>"}\\n\\n          — incremental text token
    data: {"tool_start": "<name>"}\\n\\n     — tool call starting
    data: {"tool_result": "<name>"}\\n\\n    — tool call returned
    data: {"done": true, "finish_reason": "stop"}\\n\\n  — stream complete
    data: {"error": "<msg>"}\\n\\n           — graceful degradation; never a 500

Security:
    - All endpoints require a valid JWT (get_current_user) and tenant context
      (get_tenant_id).
    - The service-role Supabase client is used; tenant isolation is enforced at
      the application/repository layer via explicit ``tenant_id`` filtering on
      every query and insert.  This matches the pattern used by every other
      service in the codebase (bills_service, invoices_service, etc.) — see
      bug #98 for why RLS-on-anon-client did not work without middleware that
      sets ``app.current_tenant_id``.
    - No PII is logged; thread/message IDs and tenant_id are safe to log.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.copilot.graph import CopilotAgent, CopilotDeps
from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.repositories.chat_repo import ChatRepository
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ThreadResponse(BaseModel):
    id: str
    tenant_id: str
    title: str | None
    created_at: str
    updated_at: str


class CreateThreadRequest(BaseModel):
    title: str | None = None


class SendMessageRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _thread_to_response(row: dict, tenant_id: str) -> ThreadResponse:
    """Map a DB row dict to ThreadResponse, normalising datetime fields.

    ``tenant_id`` is supplied by the caller (router) rather than read from the
    row so that responses are correct even when the repo's SELECT omits it.
    Surfacing ``tenant_id`` in the response enables tenant-isolation regression
    tests on the wire.
    """
    return ThreadResponse(
        id=str(row["id"]),
        tenant_id=str(row.get("tenant_id") or tenant_id),
        title=row.get("title"),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _build_repo(db: Client, tenant_id: str) -> ChatRepository:
    return ChatRepository(db=db, tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Thread endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/threads",
    response_model=ThreadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat thread",
)
async def create_thread(
    payload: CreateThreadRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> ThreadResponse:
    """Create a new copilot conversation thread for the authenticated user."""
    repo = _build_repo(db, tenant_id)
    try:
        row = await repo.create_thread(
            user_id=current_user.user_id,
            title=payload.title,
        )
    except Exception as exc:
        logger.error(
            "Failed to create chat thread",
            exc_info=True,
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create thread. Please try again.",
        ) from exc
    return _thread_to_response(row, tenant_id)


@router.get(
    "/threads",
    response_model=list[ThreadResponse],
    summary="List chat threads for the current user",
)
async def list_threads(
    limit: int = 20,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> list[ThreadResponse]:
    """Return active threads for the authenticated user, newest first."""
    repo = _build_repo(db, tenant_id)
    try:
        rows = await repo.list_threads(
            user_id=current_user.user_id,
            limit=min(limit, 100),
        )
    except Exception as exc:
        logger.error(
            "Failed to list chat threads",
            exc_info=True,
            extra={"tenant_id": tenant_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch threads. Please try again.",
        ) from exc
    return [_thread_to_response(r, tenant_id) for r in rows]


# ---------------------------------------------------------------------------
# Message / SSE streaming endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/threads/{thread_id}/messages",
    summary="Send a message and stream the assistant response via SSE",
)
async def send_message(
    thread_id: str,
    payload: SendMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> StreamingResponse:
    """Send a user message to the copilot and receive a streaming SSE response.

    The thread must belong to the authenticated user's tenant.  The user message
    is persisted immediately; the assistant message is persisted after streaming
    completes.

    **SSE frame protocol**:
    - ``{"delta": "<token>"}`` — one or more tokens of assistant text
    - ``{"tool_start": "<name>"}`` — agent is calling a tool
    - ``{"tool_result": "<name>"}`` — tool call returned
    - ``{"done": true, "finish_reason": "stop"}`` — stream complete
    - ``{"error": "<msg>"}`` — AI unavailable; stream ends gracefully
    """
    repo = _build_repo(db, tenant_id)

    # Validate thread exists and belongs to this tenant
    thread = await repo.get_thread(thread_id)
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    # Persist the user message immediately (before streaming)
    try:
        await repo.create_message(
            thread_id=thread_id,
            role="user",
            content=payload.content,
        )
    except Exception as exc:
        logger.error(
            "Failed to persist user message",
            exc_info=True,
            extra={"tenant_id": tenant_id, "thread_id": thread_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save message. Please try again.",
        ) from exc

    logger.info(
        "Chat message received — starting SSE stream",
        extra={"tenant_id": tenant_id, "thread_id": thread_id},
    )

    # Build the agent
    deps = CopilotDeps(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        db_client=db,
    )
    agent = CopilotAgent(deps=deps)

    async def event_stream() -> AsyncIterator[str]:
        """Consume the agent stream, accumulate the reply, persist it on done."""
        accumulated_text: list[str] = []
        finish_reason: str = "stop"
        had_error = False

        async for frame in agent.run_stream(
            user_message=payload.content,
            thread_id=thread_id,
        ):
            yield frame

            # Parse the frame payload to accumulate assistant reply
            try:
                raw = frame[len("data: "):].strip()
                parsed = json.loads(raw)
                if "delta" in parsed:
                    accumulated_text.append(parsed["delta"])
                if "done" in parsed:
                    finish_reason = parsed.get("finish_reason", "stop")
                if "error" in parsed:
                    had_error = True
            except (ValueError, KeyError):
                pass

        # Persist assistant reply (even on error — record what we got)
        assistant_content = "".join(accumulated_text) or None
        if not had_error or assistant_content:
            try:
                await repo.create_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=assistant_content,
                    finish_reason=finish_reason,
                    model="claude-sonnet-4-6",
                )
            except Exception:
                # Non-fatal: the user got their response; persistence failure
                # should not surface as an error in the stream.
                logger.error(
                    "Failed to persist assistant message",
                    exc_info=True,
                    extra={"tenant_id": tenant_id, "thread_id": thread_id},
                )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        },
    )
