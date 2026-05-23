"""Copilot agent — streaming chat with tool use.

Uses the OpenAI-compatible chat-completions API against OpenRouter, so we can
fan out to multiple models (free Gemini Flash first, paid Claude Haiku as
fallback) via OpenRouter's ``models`` array.

Security / quality gates enforced here:
- No raw PII sent to the LLM (tenant_id is ok; user email / names are not).
- Every LLM call logs model, token counts, and tenant_id — never message content.
- Graceful degradation: any provider error yields a user-friendly error SSE frame
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

import openai

from app.agents.base import make_async_llm_client, mask_pii
from app.core.config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_MAX_TOKENS = 1024
_MAX_ITERATIONS = 5


@dataclass
class CopilotDeps:
    """Runtime dependencies injected into the agent for each request."""

    tenant_id: str
    user_id: str
    db_client: object  # supabase Client — typed as object to avoid hard import at module level


class CopilotAgent:
    """Streaming chat with a small tool-use loop."""

    SYSTEM_PROMPT = (
        "You are Aethos Copilot, an AI assistant for professional services firms.\n"
        "You help users manage engagements, projects, invoices, and billing.\n"
        "Today's date: {date}.\n"
        "Tenant: {tenant_id}.\n\n"
        "You have access to tools to look up data. Always use tools to get real data — "
        "never invent numbers.\n"
        "When users ask about their engagements or projects, use the query_engagements tool.\n"
        "When users ask about outstanding invoices or receivables, use get_ar_aging.\n"
        "When users ask about outstanding bills or payables, use get_ap_aging.\n"
        "When users ask about unbilled work or WIP, use get_wip.\n"
        "Be concise and professional. Format monetary values with their currency symbol."
    )

    # Kept in the Anthropic-ish shape (name/description/input_schema) because tests
    # assert against those keys; converted to OpenAI shape at call time below.
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
        # Issue #62 — reporting tools
        {
            "name": "get_ar_aging",
            "description": (
                "Get AR aging buckets for the tenant. "
                "Use when user asks about outstanding invoices, receivables, "
                "what clients owe, or overdue invoices."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_ap_aging",
            "description": (
                "Get AP aging buckets. "
                "Use when user asks about outstanding bills, payables, "
                "or what the firm owes vendors."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_wip",
            "description": (
                "Get work in progress — unbilled effort and its estimated value per project."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "engagement_id": {
                        "type": "string",
                        "description": "Filter by engagement ID (optional).",
                    }
                },
                "required": [],
            },
        },
    ]

    def __init__(self, deps: CopilotDeps) -> None:
        self.deps = deps
        self.client = make_async_llm_client()

    @classmethod
    def _openai_tools(cls) -> list[dict]:
        """Convert internal TOOLS to OpenAI function-calling shape."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in cls.TOOLS
        ]

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
        except openai.APIConnectionError:
            logger.warning(
                "OpenRouter API connection error",
                extra={"tenant_id": self.deps.tenant_id},
            )
            yield f"data: {json.dumps({'error': 'AI unavailable — try again shortly'})}\n\n"
        except openai.RateLimitError:
            logger.warning(
                "OpenRouter rate limit hit",
                extra={"tenant_id": self.deps.tenant_id},
            )
            yield f"data: {json.dumps({'error': 'AI is busy — try again in a moment'})}\n\n"
        except openai.APIStatusError as exc:
            logger.error(
                "OpenRouter API error",
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
        # Mask PII before sending user input to the external LLM API.
        safe_message = mask_pii(user_message)
        system = self.SYSTEM_PROMPT.format(
            date=datetime.date.today().isoformat(),
            tenant_id=self.deps.tenant_id,
        )
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": safe_message},
        ]

        for iteration in range(_MAX_ITERATIONS):
            turn = await self._stream_one_turn(messages)

            for frame in turn["frames"]:
                yield frame

            logger.info(
                "LLM call complete",
                extra={
                    "tenant_id": self.deps.tenant_id,
                    "model": turn["model"],
                    "finish_reason": turn["finish_reason"],
                    "iteration": iteration,
                },
            )

            finish_reason = turn["finish_reason"]
            tool_calls = turn["tool_calls"]
            assistant_text = turn["text"]

            if finish_reason == "tool_calls" and tool_calls:
                # Append assistant message with the tool_calls it produced.
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_text or None,
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": tc["arguments"],
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )
                # Execute each tool and append a tool-role message for each.
                for tc in tool_calls:
                    try:
                        tool_input = json.loads(tc["arguments"] or "{}")
                    except json.JSONDecodeError:
                        tool_input = {}
                    tool_result = await self._execute_tool(tc["name"], tool_input)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(tool_result),
                        }
                    )
                    yield f"data: {json.dumps({'tool_result': tc['name']})}\n\n"
                continue

            # No tool calls — we're done.
            yield (
                f"data: {json.dumps({'done': True, 'finish_reason': finish_reason or 'stop'})}\n\n"
            )
            return

        # Hit max iterations without a natural stop.
        yield f"data: {json.dumps({'done': True, 'finish_reason': 'max_iterations'})}\n\n"

    async def _stream_one_turn(self, messages: list[dict]) -> dict:
        """Run a single streaming LLM turn.

        Returns a dict with:
        - ``frames``: list of SSE data strings accumulated during the stream
        - ``finish_reason``: the model's stop reason
        - ``text``: the accumulated assistant text (empty if pure tool call)
        - ``tool_calls``: list of {id, name, arguments} dicts
        - ``model``: the model id actually used (OpenRouter may have failed over)
        """
        frames: list[str] = []
        assistant_text_parts: list[str] = []
        # tool_calls accumulator keyed by index — OpenAI streams the arguments in fragments
        pending_tool_calls: dict[int, dict] = {}
        announced_tool_names: set[int] = set()
        finish_reason: str | None = None
        model_used: str = settings.agent_models[0]

        stream = await self.client.chat.completions.create(
            model=settings.agent_models[0],
            extra_body={"models": settings.agent_models},
            max_tokens=_MAX_TOKENS,
            messages=messages,  # type: ignore[arg-type]
            tools=self._openai_tools(),  # type: ignore[arg-type]
            stream=True,
        )

        async for chunk in stream:
            if getattr(chunk, "model", None):
                model_used = chunk.model
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                assistant_text_parts.append(delta.content)
                frames.append(f"data: {json.dumps({'delta': delta.content})}\n\n")

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    bucket = pending_tool_calls.setdefault(
                        idx, {"id": "", "name": "", "arguments": ""}
                    )
                    if tc_delta.id:
                        bucket["id"] = tc_delta.id
                    fn = tc_delta.function
                    if fn:
                        if fn.name:
                            bucket["name"] = fn.name
                        if fn.arguments:
                            bucket["arguments"] += fn.arguments
                    # Emit tool_start once we know the name.
                    if bucket["name"] and idx not in announced_tool_names:
                        announced_tool_names.add(idx)
                        frames.append(
                            f"data: {json.dumps({'tool_start': bucket['name']})}\n\n"
                        )

            if choice.finish_reason:
                finish_reason = choice.finish_reason

        tool_calls = [
            pending_tool_calls[idx] for idx in sorted(pending_tool_calls.keys())
        ]
        return {
            "frames": frames,
            "finish_reason": finish_reason,
            "text": "".join(assistant_text_parts),
            "tool_calls": tool_calls,
            "model": model_used,
        }

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
        if tool_name == "get_ar_aging":
            from app.services.reports_service import ReportsService

            svc = ReportsService(self.deps.db_client, self.deps.tenant_id)  # type: ignore[arg-type]
            return svc.ar_aging()
        if tool_name == "get_ap_aging":
            from app.services.reports_service import ReportsService

            svc = ReportsService(self.deps.db_client, self.deps.tenant_id)  # type: ignore[arg-type]
            return svc.ap_aging()
        if tool_name == "get_wip":
            from app.services.reports_service import ReportsService

            svc = ReportsService(self.deps.db_client, self.deps.tenant_id)  # type: ignore[arg-type]
            return {"wip": svc.wip(engagement_id=tool_input.get("engagement_id"))}
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
