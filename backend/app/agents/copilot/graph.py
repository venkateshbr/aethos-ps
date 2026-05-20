"""Copilot agent — Week 2 stub using the Anthropic SDK with streaming.

Architecture:
    Week 2 (this file): single-tool agentic loop, direct Anthropic SDK calls.
    Week 3: full Pydantic Graph router with specialist sub-agents.

Security / quality gates enforced here:
- No raw PII sent to the LLM (tenant_id is ok; user email / names are not).
- Every LLM call logs model, token counts, and tenant_id — never message content.
- Graceful degradation: any Anthropic error yields a user-friendly error SSE frame
  and returns cleanly — never propagates a 500 to the streaming client.
- Tool results are structured dicts — raw DB rows with sensitive fields are never
  forwarded directly to the model.
"""

from __future__ import annotations

import datetime
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import anthropic

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024
_MAX_ITERATIONS = 5


@dataclass
class CopilotDeps:
    """Runtime dependencies injected into the agent for each request."""

    tenant_id: str
    user_id: str
    db_client: object  # supabase Client — typed as object to avoid hard import at module level


class CopilotAgent:
    """Week 2 stub: routes to query_engagements_agent only.

    Week 3 will add the full Pydantic Graph router with all specialist agents.
    """

    SYSTEM_PROMPT = (
        "You are Aethos Copilot, an AI assistant for professional services firms.\n"
        "You help users manage engagements, projects, invoices, and billing.\n"
        "Today's date: {date}.\n"
        "Tenant: {tenant_id}.\n\n"
        "You have access to tools to look up data. Always use tools to get real data — "
        "never invent numbers.\n"
        "When users ask about their engagements or projects, use the query_engagements tool.\n"
        "Be concise and professional. Format monetary values with their currency symbol."
    )

    TOOLS: ClassVar[list[dict]] = [
        {
            "name": "query_engagements",
            "description": (
                "List engagements for the current tenant. "
                "Use this when the user asks about their engagements, clients, or projects."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "draft", "completed", "all"],
                        "description": "Filter by engagement status. Default: all.",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Max results.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "query_time_entries",
            "description": (
                "List time entries for a project. "
                "Use when the user asks about logged hours, timesheets, or billable time."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Project ID to query",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD",
                    },
                },
                "required": ["project_id"],
            },
        },
    ]

    def __init__(self, deps: CopilotDeps) -> None:
        self.deps = deps
        self.client = anthropic.Anthropic()

    async def run_stream(
        self,
        user_message: str,
        thread_id: str,
    ) -> AsyncIterator[str]:
        """Stream the copilot response as SSE data frames.

        Yields strings of the form ``data: {...}\\n\\n``.

        Frames emitted:
        - ``{"delta": "<token>"}``         — incremental text token
        - ``{"tool_start": "<name>"}``     — tool execution beginning
        - ``{"tool_result": "<name>"}``    — tool execution finished
        - ``{"done": true, "finish_reason": "stop"}``  — completion
        - ``{"error": "<msg>"}``           — graceful degradation on LLM failure
        """
        try:
            async for frame in self._run_agentic_loop(user_message):
                yield frame
        except anthropic.APIConnectionError:
            logger.warning(
                "Anthropic API connection error",
                extra={"tenant_id": self.deps.tenant_id},
            )
            yield f"data: {json.dumps({'error': 'AI unavailable — try again shortly'})}\n\n"
        except anthropic.RateLimitError:
            logger.warning(
                "Anthropic rate limit hit",
                extra={"tenant_id": self.deps.tenant_id},
            )
            yield f"data: {json.dumps({'error': 'AI is busy — try again in a moment'})}\n\n"
        except anthropic.APIStatusError as exc:
            logger.error(
                "Anthropic API error",
                extra={"tenant_id": self.deps.tenant_id, "status_code": exc.status_code},
            )
            yield f"data: {json.dumps({'error': 'AI unavailable — try again shortly'})}\n\n"
        except Exception:
            logger.exception(
                "Unexpected error in copilot agent",
                extra={"tenant_id": self.deps.tenant_id},
            )
            yield f"data: {json.dumps({'error': 'An unexpected error occurred — try again'})}\n\n"

    async def _run_agentic_loop(self, user_message: str) -> AsyncIterator[str]:
        """Inner agentic loop — may call tools before yielding a final response."""
        messages: list[dict] = [{"role": "user", "content": user_message}]
        system = self.SYSTEM_PROMPT.format(
            date=datetime.date.today().isoformat(),
            tenant_id=self.deps.tenant_id,
        )

        for iteration in range(_MAX_ITERATIONS):
            # Run one streaming turn. supabase-py is sync; anthropic SDK stream
            # context manager is used synchronously here as the library provides
            # a sync streaming interface. We run it in a thread to avoid blocking.
            import asyncio

            result = await asyncio.to_thread(
                self._stream_one_turn, system, messages
            )

            # Yield accumulated SSE frames from the sync turn
            for frame in result["frames"]:
                yield frame

            final_message = result["final_message"]

            # Log LLM metadata — never log content (may contain PII)
            usage = final_message.usage
            logger.info(
                "LLM call complete",
                extra={
                    "tenant_id": self.deps.tenant_id,
                    "model": _MODEL,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "stop_reason": final_message.stop_reason,
                    "iteration": iteration,
                },
            )

            if final_message.stop_reason == "end_turn":
                yield f"data: {json.dumps({'done': True, 'finish_reason': 'stop'})}\n\n"
                return

            if final_message.stop_reason == "tool_use":
                tool_results: list[dict] = []
                for content_block in final_message.content:
                    if content_block.type == "tool_use":
                        tool_result = await self._execute_tool(
                            content_block.name, content_block.input
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": json.dumps(tool_result),
                            }
                        )
                        yield f"data: {json.dumps({'tool_result': content_block.name})}\n\n"

                # Extend conversation with assistant turn + tool results
                messages.append({"role": "assistant", "content": final_message.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason — treat as done
                yield (
                    f"data: {json.dumps({'done': True, 'finish_reason': final_message.stop_reason})}\n\n"
                )
                return

        # Hit max iterations without end_turn
        yield f"data: {json.dumps({'done': True, 'finish_reason': 'max_iterations'})}\n\n"

    def _stream_one_turn(
        self, system: str, messages: list[dict]
    ) -> dict:
        """Run a single streaming LLM turn synchronously.

        Returns a dict with:
        - ``frames``: list of SSE data strings accumulated during the stream
        - ``final_message``: the completed anthropic Message object
        """
        frames: list[str] = []

        with self.client.messages.stream(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=messages,
            tools=self.TOOLS,  # type: ignore[arg-type]
        ) as stream:
            for event in stream:
                if not hasattr(event, "type"):
                    continue

                if event.type == "content_block_start":
                    block = getattr(event, "content_block", None)
                    if block and getattr(block, "type", None) == "tool_use":
                        frames.append(
                            f"data: {json.dumps({'tool_start': block.name})}\n\n"
                        )

                elif event.type == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    if delta and hasattr(delta, "text"):
                        frames.append(
                            f"data: {json.dumps({'delta': delta.text})}\n\n"
                        )
                    # partial_json deltas (tool input accumulation) are handled
                    # by the SDK internally; we don't need to forward them.

            final_message = stream.get_final_message()

        return {"frames": frames, "final_message": final_message}

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Dispatch a tool call and return a structured result dict."""
        if tool_name == "query_engagements":
            return await self._query_engagements(
                status=tool_input.get("status", "all"),
                limit=int(tool_input.get("limit", 10)),
            )
        if tool_name == "query_time_entries":
            return await self._query_time_entries(
                project_id=tool_input["project_id"],
                date_from=tool_input.get("date_from"),
                date_to=tool_input.get("date_to"),
            )
        logger.warning(
            "Unknown tool requested by LLM",
            extra={"tool_name": tool_name, "tenant_id": self.deps.tenant_id},
        )
        return {"error": f"Unknown tool: {tool_name}"}

    async def _query_engagements(self, status: str, limit: int) -> dict:
        """Fetch engagements from DB for the current tenant.

        Only safe, non-sensitive fields are returned — raw DB rows are never
        forwarded directly to the model.
        """
        import asyncio

        try:
            db = self.deps.db_client  # type: ignore[assignment]

            def _fetch() -> list[dict]:
                q = (
                    db.table("engagements")
                    .select(
                        "id, name, billing_arrangement, currency, total_value, status"
                    )
                    .eq("tenant_id", self.deps.tenant_id)
                    .is_("deleted_at", "null")
                    .limit(min(limit, 50))
                )
                if status != "all":
                    q = q.eq("status", status)
                result = q.execute()
                return result.data or []

            engagements = await asyncio.to_thread(_fetch)

            return {
                "count": len(engagements),
                "engagements": [
                    {
                        "id": e["id"],
                        "name": e["name"],
                        "billing_arrangement": e.get("billing_arrangement"),
                        "currency": e.get("currency"),
                        "total_value": e.get("total_value"),
                        "status": e["status"],
                    }
                    for e in engagements
                ],
            }
        except Exception as exc:
            logger.error(
                "query_engagements tool failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc), "engagements": []}

    async def _query_time_entries(
        self,
        project_id: str,
        date_from: str | None,
        date_to: str | None,
    ) -> dict:
        """Fetch time entries for a project.

        Only non-PII fields are returned to the model.
        """
        import asyncio

        try:
            db = self.deps.db_client  # type: ignore[assignment]

            def _fetch() -> list[dict]:
                q = (
                    db.table("time_entries")
                    .select("id, date, hours, description, billable, billing_status, employee_id")
                    .eq("tenant_id", self.deps.tenant_id)
                    .eq("project_id", project_id)
                    .is_("deleted_at", "null")
                    .order("date", desc=True)
                    .limit(50)
                )
                if date_from:
                    q = q.gte("date", date_from)
                if date_to:
                    q = q.lte("date", date_to)
                result = q.execute()
                return result.data or []

            entries = await asyncio.to_thread(_fetch)

            total_hours = sum(float(e.get("hours", 0)) for e in entries)
            return {
                "count": len(entries),
                "total_hours": round(total_hours, 2),
                "entries": [
                    {
                        "id": e["id"],
                        "date": str(e["date"]),
                        "hours": str(e["hours"]),
                        "description": e.get("description") or "",
                        "billable": e.get("billable"),
                        "billing_status": e.get("billing_status"),
                    }
                    for e in entries
                ],
            }
        except Exception as exc:
            logger.error(
                "query_time_entries tool failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc), "entries": []}
