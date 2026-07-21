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
    - Read-only thread listing uses the authenticated RLS Supabase client.
      Thread creation and message streaming remain service-role-backed because
      they persist user/assistant messages and execute write-capable tools.
    - No PII is logged; thread/message IDs and tenant_id are safe to log.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client, get_user_rls_client
from app.core.logging import trace_id_var
from app.core.tenant import get_tenant_id
from app.models.ai_settings import AiSettingsResponse
from app.repositories.chat_repo import ChatRepository
from app.services.agent_run_ledger import AgentRunLedger
from app.services.ai_settings_service import AiSettingsService, default_ai_settings_response
from app.services.atlas_deterministic_responses import (
    SemanticAtlasResponse,
    render_semantic_atlas_response,
)
from app.services.atlas_runtime import build_atlas_runtime
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


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str | None
    tool_name: str | None = None
    finish_reason: str | None = None
    model: str | None = None
    created_at: str


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


def _message_to_response(row: dict) -> MessageResponse:
    return MessageResponse(
        id=str(row["id"]),
        role=str(row["role"]),
        content=row.get("content"),
        tool_name=row.get("tool_name"),
        finish_reason=row.get("finish_reason"),
        model=row.get("model"),
        created_at=str(row["created_at"]),
    )


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
    db: Client = Depends(get_user_rls_client),  # noqa: B008
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


@router.get(
    "/threads/{thread_id}/messages",
    response_model=list[MessageResponse],
    summary="List messages for a chat thread",
)
async def list_messages(
    thread_id: str,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_user_rls_client),  # noqa: B008
) -> list[MessageResponse]:
    """Return persisted messages for one authenticated user's thread."""
    repo = _build_repo(db, tenant_id)
    thread = await repo.get_thread(thread_id)
    if thread is None or str(thread.get("user_id")) != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    rows = await repo.list_messages(
        thread_id=thread_id,
        limit=min(limit, 200),
    )
    return [_message_to_response(row) for row in rows]


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
    if thread is None or str(thread.get("user_id")) != current_user.user_id:
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

    async def event_stream() -> AsyncIterator[str]:
        """Consume the agent stream, accumulate the reply, persist it on done."""
        accumulated_text: list[str] = []
        finish_reason: str = "stop"
        had_error = False

        try:
            ai_settings = await AiSettingsService(db, tenant_id).get_effective_settings()
        except Exception:
            logger.warning(
                "tenant_ai_settings_unavailable",
                exc_info=True,
                extra={"tenant_id": tenant_id},
            )
            ai_settings = default_ai_settings_response(tenant_id=tenant_id)

        async def maybe_semantic_response(
            settings: AiSettingsResponse,
        ) -> SemanticAtlasResponse | None:
            if not settings.semantic_router_enabled:
                return None
            try:
                semantic_reply = await render_semantic_atlas_response(
                    db=db,
                    tenant_id=tenant_id,
                    current_user=current_user,
                    thread_id=thread_id,
                    message=payload.content,
                    min_confidence=settings.semantic_router_min_confidence,
                )
            except Exception:
                logger.warning(
                    "atlas_semantic_response_failed",
                    exc_info=True,
                    extra={"tenant_id": tenant_id, "thread_id": thread_id},
                )
                return None

            if semantic_reply is None:
                return None
            return semantic_reply

        async def stream_runtime(settings: AiSettingsResponse) -> AsyncIterator[str]:
            nonlocal finish_reason, had_error
            runtime = await build_atlas_runtime(
                tenant_id=tenant_id,
                user_id=current_user.user_id,
                db_client=db,
                ai_settings=settings,
            )
            runtime_model = f"nous:{runtime.name}"

            # The Basic runtime records its own agent_run inside the graph loop.
            # Record one for the Hermes runtime here so Hermes turns also appear
            # in the Agent Run Ledger with runtime, status, and trace.
            hermes_ledger: AgentRunLedger | None = None
            hermes_run_id: str | None = None
            if runtime.name == "hermes_agent":
                hermes_ledger = AgentRunLedger(db, tenant_id)
                hermes_run_id = await hermes_ledger.start_run(
                    agent_name="nous_hermes_runtime",
                    trigger_type="chat",
                    user_id=str(current_user.user_id),
                    input_payload={"message": payload.content[:2000]},
                    prompt_version="hermes-v1",
                    model_version=runtime_model,
                    trace_id=trace_id_var.get("") or None,
                    replay_pointer=f"chat_threads/{thread_id}",
                )

            async for frame in runtime.stream_message(
                user_message=payload.content,
                thread_id=thread_id,
            ):
                yield frame

                # Parse the frame payload to accumulate assistant reply
                try:
                    raw = frame[len("data: ") :].strip()
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
                        model=runtime_model,
                    )
                except Exception:
                    # Non-fatal: the user got their response; persistence failure
                    # should not surface as an error in the stream.
                    logger.error(
                        "Failed to persist assistant message",
                        exc_info=True,
                        extra={"tenant_id": tenant_id, "thread_id": thread_id},
                    )

            if hermes_ledger is not None:
                await hermes_ledger.complete_run(
                    hermes_run_id,
                    status="failed" if had_error else "succeeded",
                    output_payload={
                        "finish_reason": finish_reason,
                        "chars": len(assistant_content or ""),
                    },
                    model_version=runtime_model,
                )

        response_order = ai_settings.atlas_response_order or ["semantic_intent", "atlas_runtime"]
        for stage in response_order:
            if stage == "semantic_intent":
                semantic_reply = await maybe_semantic_response(ai_settings)
                if semantic_reply is not None:
                    tool_name = getattr(semantic_reply, "tool_name", None)
                    if tool_name:
                        yield f"data: {json.dumps({'tool_start': tool_name})}\n\n"
                        yield f"data: {json.dumps({'tool_result': tool_name})}\n\n"
                    frame = f"data: {json.dumps({'delta': semantic_reply.text})}\n\n"
                    yield frame
                    accumulated_text.append(semantic_reply.text)
                    yield f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n"
                    try:
                        await repo.create_message(
                            thread_id=thread_id,
                            role="assistant",
                            content="".join(accumulated_text),
                            finish_reason=finish_reason,
                            model="aethos-semantic-intent",
                        )
                    except Exception:
                        logger.error(
                            "Failed to persist assistant message",
                            exc_info=True,
                            extra={"tenant_id": tenant_id, "thread_id": thread_id},
                        )
                    logger.info(
                        "atlas_semantic_response_used",
                        extra={
                            "tenant_id": tenant_id,
                            "thread_id": thread_id,
                            "intent": semantic_reply.route.intent,
                            "confidence": semantic_reply.route.confidence,
                            "action_mode": semantic_reply.route.action_mode,
                        },
                    )
                    return
            if stage == "atlas_runtime":
                async for frame in stream_runtime(ai_settings):
                    yield frame
                return

        async for frame in stream_runtime(ai_settings):
            yield frame

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        },
    )
