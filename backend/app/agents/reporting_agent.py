"""Reporting agent — natural-language financial Q&A.

Wraps all seven ReportsService methods as tool-callable functions behind a
single agentic loop.  The copilot delegates financial query intent here so
the copilot graph stays thin.

Design principles (matching existing agent patterns):
- Uses the same OpenAI-compatible client against OpenRouter as every other
  agent in this codebase (no pydantic_ai dependency installed).
- Follows the CopilotAgent class pattern: TOOLS list + _execute_tool dispatch
  + streaming loop.
- Money amounts passed to the LLM are already serialised as strings by
  ReportsService — no Decimal → float risk.
- Every tool result is a plain dict (JSON-serialisable).  Raw DB rows are
  never forwarded verbatim.
- PII masking applied to user input before LLM call.
- Graceful degradation: any exception returns an error SSE frame, never a 500.

Period parsing:
  "this month"  → YYYY-MM (current month)
  "last month"  → YYYY-MM (previous month)
  "YTD"         → None (caller interprets as Jan to now)
  None          → None (all-time, report default)
  "YYYY-MM"     → passed through unchanged
"""

from __future__ import annotations

import datetime
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import ClassVar

import openai

from app.agents.base import make_async_llm_client, mask_pii, resolve_model_chain

logger = logging.getLogger(__name__)

_MAX_TOKENS = 1500
_MAX_ITERATIONS = 6

# ---------------------------------------------------------------------------
# Period parsing helper
# ---------------------------------------------------------------------------


def _parse_period(period_str: str | None) -> str | None:
    """Parse a natural-language period string to YYYY-MM, or None for all-time.

    Supported forms:
        None / ""         → None   (all-time; each report uses its own default)
        "all time"        → None
        "ytd"             → None   (callers use Jan-current month slice)
        "this month"      → current YYYY-MM
        "last month"      → previous YYYY-MM
        "YYYY-MM"         → passed through as-is
        anything else     → passed through as-is (let the service handle it)
    """
    if not period_str:
        return None
    s = period_str.strip().lower()
    if s in ("all time", "all-time", "ytd", "year to date"):
        return None
    if s in ("this month", "current month"):
        return datetime.date.today().strftime("%Y-%m")
    if s in ("last month", "previous month"):
        today = datetime.date.today()
        first_of_this = today.replace(day=1)
        last_month = first_of_this - datetime.timedelta(days=1)
        return last_month.strftime("%Y-%m")
    # Pass through anything that looks like YYYY-MM or any other string
    return period_str


# ---------------------------------------------------------------------------
# Deps — thin wrapper so tests can inject a mock without importing the
# heavier AgentDeps from base.py (avoids Supabase import at test collection time)
# ---------------------------------------------------------------------------


@dataclass
class ReportingDeps:
    """Dependencies injected into the reporting agent for each request."""

    tenant_id: str
    user_id: str
    db_client: object  # supabase Client — typed as object to avoid hard import


# ---------------------------------------------------------------------------
# Reporting agent
# ---------------------------------------------------------------------------


class ReportingAgent:
    """Stateless financial Q&A agent with 7 reporting tools.

    Usage::

        deps = ReportingDeps(tenant_id=..., user_id=..., db_client=...)
        agent = ReportingAgent(deps)
        async for frame in agent.run_stream("Which clients owe us money?"):
            ...  # yield SSE frames to caller

    Or for a single non-streamed result (copilot delegation)::

        result = await agent.run_once("Show me WIP for this month")
    """

    SYSTEM_PROMPT = (
        "You are the Aethos financial reporting assistant for a professional services firm.\n\n"
        "Rules:\n"
        "- ALWAYS call a tool to get data. NEVER invent or estimate financial figures.\n"
        "- If no data exists for a query, say so explicitly: 'No data found for this period.'\n"
        "- Present money amounts as returned by the tool (already in the tenant base currency).\n"
        "- When a period is not specified, default to the current calendar month.\n"
        "- Parse natural language periods: 'this month' → current YYYY-MM, "
        "'last month' → previous YYYY-MM, 'YTD' → year to date.\n"
        "- Be concise. Lead with the answer, then supporting detail.\n"
        "- Never reveal tenant data to another tenant — you only see data for tenant {tenant_id}.\n"
        "Today's date: {date}."
    )

    TOOLS: ClassVar[list[dict]] = [
        {
            "name": "get_ar_aging",
            "description": (
                "Get accounts receivable aging report — which customers owe money and how "
                "overdue. Returns buckets: 0-30, 31-60, 61-90, 90+ days past due and a total."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_ap_aging",
            "description": (
                "Get accounts payable aging report — which vendor bills are outstanding and "
                "how overdue. Returns buckets: 0-30, 31-60, 61-90, 90+ days and a total."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_wip",
            "description": (
                "Get work in progress — unbilled hours and their estimated value across all "
                "projects.  Optionally filter to a single engagement."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "engagement_id": {
                        "type": "string",
                        "description": "Optional engagement UUID to narrow results.",
                    }
                },
                "required": [],
            },
        },
        {
            "name": "get_project_pnl",
            "description": (
                "Get project profit & loss — revenue vs direct cost with gross margin per "
                "project.  Optionally filter to one project or a date range."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Optional project UUID to filter to a single project.",
                    },
                    "period_start": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD (optional).",
                    },
                    "period_end": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD (optional).",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_utilization",
            "description": (
                "Get employee utilization — billable hours as a percentage of total hours "
                "logged.  Accepts a natural-language period like 'this month' or 'last month'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": (
                            "Natural-language period: 'this month', 'last month', 'YYYY-MM', "
                            "or omit for all-time."
                        ),
                    },
                    "employee_id": {
                        "type": "string",
                        "description": "Optional employee UUID to filter to one employee.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_revenue",
            "description": (
                "Get revenue by engagement — total invoiced amount per engagement for an "
                "optional period.  Accepts a natural-language period."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": (
                            "Natural-language period: 'this month', 'last month', 'YYYY-MM', "
                            "or omit for all-time."
                        ),
                    }
                },
                "required": [],
            },
        },
        {
            "name": "get_trial_balance",
            "description": (
                "Get trial balance — DR/CR totals by account through the specified period. "
                "Useful for 'what is our trial balance as of June 2026' or similar."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "as_of_period": {
                        "type": "string",
                        "description": (
                            "Cumulative through this YYYY-MM period. "
                            "Omit for all posted entries."
                        ),
                    }
                },
                "required": [],
            },
        },
    ]

    def __init__(self, deps: ReportingDeps) -> None:
        self.deps = deps
        self.client = make_async_llm_client(
            agent_name="reporting_agent",
            tenant_id=deps.tenant_id,
            user_id=deps.user_id,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_stream(self, user_message: str) -> AsyncIterator[str]:
        """Stream the reporting agent response as SSE data frames.

        Yields strings of the form ``data: {...}\\n\\n``.  Same frame schema
        as CopilotAgent so the chat router can forward them unchanged.
        """
        try:
            async for frame in self._run_agentic_loop(user_message):
                yield frame
        except openai.APIConnectionError:
            logger.warning(
                "ReportingAgent: OpenRouter connection error",
                extra={"tenant_id": self.deps.tenant_id},
            )
            yield f"data: {json.dumps({'error': 'AI unavailable — try again shortly'})}\n\n"
        except openai.RateLimitError:
            logger.warning(
                "ReportingAgent: rate limit",
                extra={"tenant_id": self.deps.tenant_id},
            )
            yield f"data: {json.dumps({'error': 'AI is busy — try again in a moment'})}\n\n"
        except openai.APIStatusError as exc:
            logger.error(
                "ReportingAgent: API status error",
                extra={"tenant_id": self.deps.tenant_id, "status_code": exc.status_code},
            )
            yield f"data: {json.dumps({'error': 'AI unavailable — try again shortly'})}\n\n"
        except Exception:
            logger.exception(
                "ReportingAgent: unexpected error",
                extra={"tenant_id": self.deps.tenant_id},
            )
            yield f"data: {json.dumps({'error': 'An unexpected error occurred — try again'})}\n\n"

    async def run_once(self, user_message: str) -> str:
        """Run the agent and return the final text response (non-streaming).

        Collects all SSE frames, extracts delta tokens, and returns the
        assembled text.  Used for copilot delegation without streaming.
        """
        parts: list[str] = []
        async for frame in self.run_stream(user_message):
            if not frame.startswith("data: "):
                continue
            payload = json.loads(frame[6:].strip())
            if "delta" in payload:
                parts.append(payload["delta"])
        return "".join(parts)

    # ------------------------------------------------------------------
    # Internal agentic loop
    # ------------------------------------------------------------------

    @classmethod
    def _openai_tools(cls) -> list[dict]:
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

    async def _run_agentic_loop(self, user_message: str) -> AsyncIterator[str]:
        safe_message = mask_pii(user_message)
        system = self.SYSTEM_PROMPT.format(
            tenant_id=self.deps.tenant_id,
            date=datetime.date.today().isoformat(),
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
                "ReportingAgent: LLM turn complete",
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

            yield f"data: {json.dumps({'done': True, 'finish_reason': finish_reason or 'stop'})}\n\n"
            return

        yield f"data: {json.dumps({'done': True, 'finish_reason': 'max_iterations'})}\n\n"

    async def _stream_one_turn(self, messages: list[dict]) -> dict:
        """Single streaming LLM turn — same structure as CopilotAgent._stream_one_turn."""
        frames: list[str] = []
        assistant_text_parts: list[str] = []
        pending_tool_calls: dict[int, dict] = {}
        announced_tool_names: set[int] = set()
        finish_reason: str | None = None
        model_chain = await resolve_model_chain(self.deps.db_client, self.deps.tenant_id)
        model_used: str = model_chain[0]

        stream = await self.client.chat.completions.create(
            model=model_chain[0],
            extra_body={"models": model_chain},
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
                    if bucket["name"] and idx not in announced_tool_names:
                        announced_tool_names.add(idx)
                        frames.append(
                            f"data: {json.dumps({'tool_start': bucket['name']})}\n\n"
                        )

            if choice.finish_reason:
                finish_reason = choice.finish_reason

        tool_calls = [pending_tool_calls[idx] for idx in sorted(pending_tool_calls.keys())]
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
        """Dispatch a tool call and return a JSON-serialisable result dict."""
        from app.services.reports_service import ReportsService

        svc = ReportsService(self.deps.db_client, self.deps.tenant_id)  # type: ignore[arg-type]

        try:
            if tool_name == "get_ar_aging":
                return svc.ar_aging()

            if tool_name == "get_ap_aging":
                return svc.ap_aging()

            if tool_name == "get_wip":
                rows = svc.wip(engagement_id=tool_input.get("engagement_id"))
                return {"wip": rows}

            if tool_name == "get_project_pnl":
                rows = svc.project_pnl(
                    project_id=tool_input.get("project_id"),
                    period_start=tool_input.get("period_start"),
                    period_end=tool_input.get("period_end"),
                )
                return {"projects": rows}

            if tool_name == "get_utilization":
                period = _parse_period(tool_input.get("period"))
                # Convert YYYY-MM period to start/end date range for the service
                period_start: str | None = None
                period_end: str | None = None
                if period:
                    period_start = f"{period}-01"
                    # Last day of the month: first day of next month minus 1 day
                    import calendar

                    year, month = int(period[:4]), int(period[5:7])
                    last_day = calendar.monthrange(year, month)[1]
                    period_end = f"{period}-{last_day:02d}"
                rows = svc.utilization(
                    employee_id=tool_input.get("employee_id"),
                    period_start=period_start,
                    period_end=period_end,
                )
                return {"utilization": rows, "period": period}

            if tool_name == "get_revenue":
                period = _parse_period(tool_input.get("period"))
                period_start = None
                period_end = None
                if period:
                    import calendar

                    year, month = int(period[:4]), int(period[5:7])
                    last_day = calendar.monthrange(year, month)[1]
                    period_start = f"{period}-01"
                    period_end = f"{period}-{last_day:02d}"
                rows = svc.revenue_by_engagement(
                    period_start=period_start,
                    period_end=period_end,
                )
                return {"revenue_by_engagement": rows, "period": period}

            if tool_name == "get_trial_balance":
                as_of = tool_input.get("as_of_period")
                report = svc.trial_balance(as_of_period=as_of)
                # Serialise the Pydantic model to a plain dict for LLM context
                return report.model_dump(mode="json")

            logger.warning(
                "ReportingAgent: unknown tool requested by LLM",
                extra={"tool_name": tool_name, "tenant_id": self.deps.tenant_id},
            )
            return {"error": f"Unknown tool: {tool_name}"}

        except Exception as exc:
            logger.error(
                "ReportingAgent: tool execution failed",
                exc_info=True,
                extra={"tool_name": tool_name, "tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}
