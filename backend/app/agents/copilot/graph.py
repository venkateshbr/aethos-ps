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
import difflib
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

import openai

from app.agents.base import AgentDeps, make_async_llm_client, mask_pii
from app.agents.suggestion_writer import write_agent_suggestion
from app.agents.tool_registry import action_type_for_tool, risk_class_for_tool
from app.core.config import settings
from app.core.logging import trace_id_var
from app.services.agent_run_ledger import AgentRunLedger
from app.services.agent_tool_policy import AgentToolPolicy, AgentToolPolicyDecision

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
        "You help users manage engagements, projects, invoices, billing, and time tracking.\n"
        "Today's date: {date}.\n"
        "Tenant: {tenant_id}.\n\n"
        "You have access to tools to look up data and perform actions. Always use tools to get "
        "real data — never invent numbers.\n"
        "When users ask about their engagements or projects, use the query_engagements tool.\n"
        "When users ask about outstanding invoices or receivables, use get_ar_aging.\n"
        "When users ask about outstanding bills or payables, use get_ap_aging.\n"
        "When users ask to pay vendors or run bill pay, use the "
        "propose_bill_payment_batch tool. It creates an Inbox review task before "
        "any payment batch is created.\n"
        "When users ask to prepare month-end close, use the prepare_month_end_close "
        "tool. It creates an Inbox review task before bootstrapping close tasks "
        "or journal proposals.\n"
        "When users ask for financial statements or a statement package, use the "
        "generate_financial_statement_package tool.\n"
        "When users ask about unbilled work or WIP, use get_wip.\n"
        "When users ask to log hours or time (e.g. 'log 3 hours on Nexus for today'), "
        "use the log_time_entry tool — match the project name from what the user says.\n"
        "When users ask to update a billing rate or set an employee's rate "
        "(e.g. 'Set Marcus rate to £380/hr'), use the update_rate_card tool.\n"
        "When users ask to draft, create, or prepare a customer invoice for an "
        "engagement, use the draft_invoice tool. It drafts the invoice for Inbox "
        "review only; it does not approve, send, or collect payment.\n"
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
        {
            "name": "log_time_entry",
            "description": (
                "Log billable or non-billable hours to a project. "
                "Use when the user asks to log time, record hours, or track work "
                "(e.g. 'Log 3 hours on Nexus CFO Advisory for today')."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": (
                            "Name of the project to log time against. "
                            "Will be fuzzy-matched to active projects."
                        ),
                    },
                    "hours": {
                        "type": "number",
                        "description": "Number of hours to log (e.g. 4.5).",
                    },
                    "date": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD. Defaults to today if omitted.",
                    },
                    "description": {
                        "type": "string",
                        "description": "What was done during this time.",
                    },
                    "billable": {
                        "type": "boolean",
                        "description": "Whether the hours are billable to the client. Default true.",
                    },
                },
                "required": ["project_name", "hours"],
            },
        },
        {
            "name": "update_rate_card",
            "description": (
                "Set or update an employee's billing rate — either their default rate "
                "or a rate specific to an engagement. "
                "Use when the user asks to change a rate "
                "(e.g. 'Set Marcus rate on Nexus to £380/hr' or 'Update Alice default rate to £300')."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "employee_name": {
                        "type": "string",
                        "description": (
                            "Name of the employee whose rate to update. "
                            "Will be fuzzy-matched to employees."
                        ),
                    },
                    "rate": {
                        "type": "number",
                        "description": "New hourly billing rate (e.g. 380.0).",
                    },
                    "currency": {
                        "type": "string",
                        "description": "3-letter currency code, e.g. GBP, USD. Default GBP.",
                    },
                    "engagement_name": {
                        "type": "string",
                        "description": (
                            "Name of the engagement to set the rate for. "
                            "If omitted, updates the employee's default bill rate."
                        ),
                    },
                    "effective_date": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD. Defaults to today.",
                    },
                },
                "required": ["employee_name", "rate"],
            },
        },
        {
            "name": "draft_invoice",
            "description": (
                "Draft a customer invoice for an engagement using billing terms, "
                "approved/unbilled time, expenses, retainers, milestones, and taxes. "
                "Use when the user asks to invoice a client or prepare an invoice. "
                "The draft is routed to Inbox before any invoice row is created."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "engagement_name": {
                        "type": "string",
                        "description": (
                            "Name of the engagement to invoice. Will be fuzzy-matched."
                        ),
                    },
                    "engagement_id": {
                        "type": "string",
                        "description": (
                            "Known engagement ID from a prior tool result, if available."
                        ),
                    },
                    "period_start": {
                        "type": "string",
                        "description": "Optional billing period start date, YYYY-MM-DD.",
                    },
                    "period_end": {
                        "type": "string",
                        "description": "Optional billing period end date, YYYY-MM-DD.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "propose_bill_payment_batch",
            "description": (
                "Ask the bill-pay specialist to propose a controlled vendor payment "
                "batch from approved bills. Use when the user asks to pay bills, "
                "run bill pay, or prepare vendor payments. The proposal is routed "
                "to Inbox before any payment batch is created."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "due_within_days": {
                        "type": "integer",
                        "default": 7,
                        "minimum": 1,
                        "maximum": 90,
                        "description": "Include approved bills due within this many days.",
                    },
                    "bank_account_label": {
                        "type": "string",
                        "description": (
                            "Optional operator-facing bank account label. "
                            "Never include raw bank account numbers."
                        ),
                    },
                },
                "required": [],
            },
        },
        {
            "name": "prepare_month_end_close",
            "description": (
                "Prepare the month-end close workflow for an accounting period. "
                "Use when the user asks to run or prepare month-end close. The "
                "request is routed to Inbox before creating close tasks or journal "
                "review proposals."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}$",
                        "description": "Accounting period to prepare, formatted YYYY-MM.",
                    },
                },
                "required": ["period"],
            },
        },
        {
            "name": "generate_financial_statement_package",
            "description": (
                "Generate a read-only financial statement package from posted journals, "
                "including trial balance, balance sheet, income statement, cash flow, "
                "retained earnings, and tax controls. Use when the user asks for "
                "financial statements or a statement package."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "period_start": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}$",
                        "description": "First accounting period in the package, YYYY-MM.",
                    },
                    "period_end": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}$",
                        "description": (
                            "Last accounting period in the package, YYYY-MM. "
                            "Defaults to period_start."
                        ),
                    },
                },
                "required": ["period_start"],
            },
        },
    ]

    def __init__(self, deps: CopilotDeps) -> None:
        self.deps = deps
        self.client = make_async_llm_client()
        self.tool_policy = AgentToolPolicy(deps.db_client, deps.tenant_id)

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
            async for frame in self._run_agentic_loop(
                user_message,
                thread_id=thread_id,
            ):
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

    async def _run_agentic_loop(
        self,
        user_message: str,
        thread_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Inner agentic loop — may call tools before yielding a final response."""
        # Mask PII before sending user input to the external LLM API.
        safe_message = mask_pii(user_message)
        system = self.SYSTEM_PROMPT.format(
            date=datetime.date.today().isoformat(),
            tenant_id=self.deps.tenant_id,
        )
        ledger = AgentRunLedger(self.deps.db_client, self.deps.tenant_id)
        run_id = await ledger.start_run(
            agent_name="copilot_agent",
            trigger_type="chat",
            user_id=str(self.deps.user_id),
            input_payload={"message": safe_message},
            prompt_version="cop-v1",
            trace_id=trace_id_var.get("") or None,
            replay_pointer=f"chat_threads/{thread_id}" if thread_id else None,
        )
        last_model: str | None = None
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": safe_message},
        ]

        try:
            for iteration in range(_MAX_ITERATIONS):
                turn = await self._stream_one_turn(messages)
                last_model = turn["model"]

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
                        started_at = time.perf_counter()
                        tool_result = await self._execute_tool_with_policy(
                            tc["name"],
                            tool_input,
                        )
                        duration_ms = int((time.perf_counter() - started_at) * 1000)
                        error_message = (
                            str(tool_result.get("error"))
                            if isinstance(tool_result, dict) and tool_result.get("error")
                            else None
                        )
                        invocation_status = "skipped" if tool_result.get("requires_review") else "succeeded"
                        if error_message:
                            invocation_status = "failed"
                        await ledger.record_tool_invocation(
                            run_id,
                            agent_name="copilot_agent",
                            action_type=action_type_for_tool("copilot_agent", tc["name"]),
                            tool_name=tc["name"],
                            risk_class=risk_class_for_tool("copilot_agent", tc["name"]),
                            input_payload=tool_input,
                            output_payload=tool_result,
                            status=invocation_status,
                            duration_ms=duration_ms,
                            error_message=error_message,
                            external_tool_call_id=tc["id"],
                        )
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
                done_payload = {
                    "finish_reason": finish_reason or "stop",
                    "assistant_text": assistant_text,
                }
                await ledger.complete_run(
                    run_id,
                    status="succeeded",
                    output_payload=done_payload,
                    model_version=last_model,
                )
                yield (
                    f"data: {json.dumps({'done': True, 'finish_reason': finish_reason or 'stop'})}\n\n"
                )
                return

            # Hit max iterations without a natural stop.
            await ledger.complete_run(
                run_id,
                status="failed",
                output_payload={"finish_reason": "max_iterations"},
                error_message="max_iterations",
                model_version=last_model,
            )
            yield f"data: {json.dumps({'done': True, 'finish_reason': 'max_iterations'})}\n\n"
        except Exception as exc:
            await ledger.complete_run(
                run_id,
                status="failed",
                error_message=str(exc),
                model_version=last_model,
            )
            raise

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
        if tool_name == "log_time_entry":
            return await self._log_time_entry(tool_input)
        if tool_name == "update_rate_card":
            return await self._update_rate_card(tool_input)
        if tool_name == "draft_invoice":
            payload = await self._build_invoice_draft_payload(tool_input)
            if payload.get("error"):
                return payload
            return await self._persist_invoice_draft_payload(payload["invoice_draft"])
        if tool_name == "propose_bill_payment_batch":
            return await self._build_bill_payment_batch_payload(tool_input)
        if tool_name == "prepare_month_end_close":
            return await self._prepare_month_end_close(tool_input)
        if tool_name == "generate_financial_statement_package":
            return await self._generate_financial_statement_package(tool_input)
        logger.warning(
            "Unknown tool requested by LLM",
            extra={"tool_name": tool_name, "tenant_id": self.deps.tenant_id},
        )
        return {"error": f"Unknown tool: {tool_name}"}

    async def _execute_tool_with_policy(self, tool_name: str, tool_input: dict) -> dict:
        """Apply tool policy before dispatching a Copilot tool call."""
        if tool_name not in {tool["name"] for tool in self.TOOLS}:
            return await self._execute_tool(tool_name, tool_input)

        risk_class = risk_class_for_tool("copilot_agent", tool_name)
        action_type = action_type_for_tool("copilot_agent", tool_name)
        decision = await self.tool_policy.decide(
            agent_name="copilot_agent",
            action_type=action_type,
            tool_name=tool_name,
            risk_class=risk_class,
            user_id=str(self.deps.user_id),
        )
        if not decision.allowed:
            return {
                "error": decision.reason,
                "policy_denied": True,
                "tool_name": tool_name,
                "risk_class": risk_class,
                "minimum_role": decision.minimum_role.value,
                "user_role": decision.user_role.value,
            }
        if decision.route_to_hitl:
            return await self._route_tool_to_hitl(
                tool_name=tool_name,
                tool_input=tool_input,
                risk_class=risk_class,
                action_type=action_type,
                decision=decision,
            )
        return await self._execute_tool(tool_name, tool_input)

    async def _route_tool_to_hitl(
        self,
        *,
        tool_name: str,
        tool_input: dict,
        risk_class: str,
        action_type: str,
        decision: AgentToolPolicyDecision,
    ) -> dict:
        """Create a HITL suggestion/task for a write-capable Copilot tool."""
        try:
            output: dict = {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "risk_class": risk_class,
                "policy_reason": decision.reason,
                "requested_by_user_id": str(self.deps.user_id),
            }
            if tool_name == "draft_invoice":
                draft_payload = await self._build_invoice_draft_payload(tool_input)
                if draft_payload.get("error"):
                    return {
                        "error": draft_payload["error"],
                        "tool_name": tool_name,
                        "risk_class": risk_class,
                    }
                output.update(draft_payload)
            elif tool_name == "propose_bill_payment_batch":
                bill_pay_payload = await self._build_bill_payment_batch_payload(tool_input)
                if bill_pay_payload.get("error"):
                    return {
                        "error": bill_pay_payload["error"],
                        "tool_name": tool_name,
                        "risk_class": risk_class,
                    }
                duplicate_id = bill_pay_payload.pop("duplicate_suggestion_id", None)
                if duplicate_id:
                    return {
                        "requires_review": True,
                        "suggestion_id": duplicate_id,
                        "action_type": action_type,
                        "tool_name": tool_name,
                        "risk_class": risk_class,
                        "duplicate_suppressed": True,
                        "message": (
                            "An open Inbox review task already covers this bill-pay batch."
                        ),
                    }
                output.update(bill_pay_payload)
            elif tool_name == "prepare_month_end_close":
                close_payload = await self._build_month_end_close_review_payload(tool_input)
                if close_payload.get("error"):
                    return {
                        "error": close_payload["error"],
                        "tool_name": tool_name,
                        "risk_class": risk_class,
                    }
                output.update(close_payload)

            suggestion = await write_agent_suggestion(
                deps=AgentDeps(
                    tenant_id=self.deps.tenant_id,
                    user_id=str(self.deps.user_id),
                    db=self.deps.db_client,  # type: ignore[arg-type]
                ),
                agent_name="copilot_agent",
                action_type=action_type,
                document_id=None,
                output=output,
                confidence=0.0,
                autonomy_level=decision.autonomy_level,
                confidence_threshold=1.0,
            )
            return {
                "requires_review": True,
                "suggestion_id": suggestion.get("id"),
                "action_type": action_type,
                "tool_name": tool_name,
                "risk_class": risk_class,
                "message": "Created an Inbox review task before applying this change.",
            }
        except Exception as exc:
            logger.error(
                "Copilot HITL routing failed",
                exc_info=True,
                extra={
                    "tenant_id": self.deps.tenant_id,
                    "tool_name": tool_name,
                    "risk_class": risk_class,
                },
            )
            return {"error": str(exc), "tool_name": tool_name, "hitl_routing_failed": True}

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

    async def _build_bill_payment_batch_payload(self, args: dict) -> dict:
        """Build a reviewable bill-payment proposal without creating a batch."""
        import asyncio

        try:
            due_within_days = int(args.get("due_within_days") or 7)
            if due_within_days < 1 or due_within_days > 90:
                raise ValueError("due_within_days must be between 1 and 90")

            from app.agents.bill_pay_agent import (
                find_duplicate_payment_proposal,
                propose_payment_batch,
            )

            deps = AgentDeps(
                tenant_id=self.deps.tenant_id,
                user_id=str(self.deps.user_id),
                db=self.deps.db_client,  # type: ignore[arg-type]
            )
            proposal = await asyncio.to_thread(
                lambda: propose_payment_batch(deps, due_within_days)
            )
            payload = proposal.model_dump(mode="json")
            bank_account_label = str(args.get("bank_account_label") or "").strip()
            if bank_account_label:
                payload["bank_account_label"] = bank_account_label

            bill_ids = payload.get("proposed_bill_ids") or []
            if not bill_ids:
                return {
                    "error": (
                        "No approved bills were available for a bill-pay batch. "
                        "Approve vendor bills before asking Copilot to run bill pay."
                    ),
                    "proposal": payload,
                }

            duplicate_id = await asyncio.to_thread(
                lambda: find_duplicate_payment_proposal(deps, proposal.proposed_bill_ids)
            )
            payload["preview"] = {
                "bill_count": len(bill_ids),
                "currency": payload.get("currency"),
                "total": payload.get("total_amount"),
                "proposed_pay_date": payload.get("proposed_pay_date"),
                "early_pay_discount_captured": payload.get(
                    "early_pay_discount_captured"
                ),
                "flagged_for_review_count": len(
                    payload.get("flagged_for_review") or []
                ),
            }
            if duplicate_id:
                payload["duplicate_suggestion_id"] = duplicate_id
            return payload
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            logger.error(
                "bill-pay proposal build failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}

    async def _build_month_end_close_review_payload(self, args: dict) -> dict:
        """Build the review payload shown before preparing month-end close."""
        import asyncio

        try:
            period = self._parse_period(args.get("period"))

            from app.services.close_package_service import ClosePackageService
            from app.services.close_status_service import CloseStatusService

            close_status = await asyncio.to_thread(
                lambda: CloseStatusService(
                    self.deps.db_client,  # type: ignore[arg-type]
                    self.deps.tenant_id,
                ).get_status(period)
            )
            close_package = await asyncio.to_thread(
                lambda: ClosePackageService(
                    self.deps.db_client,  # type: ignore[arg-type]
                    self.deps.tenant_id,
                ).build_package(period)
            )
            status_payload = close_status.as_dict()
            gl_summary = close_package.get("gl_summary") or {}
            working_capital = close_package.get("working_capital") or {}

            return {
                "period": period,
                "preview": {
                    "period": period,
                    "workflow": "month_end_close",
                    "lock_blocker_count": len(status_payload.get("lock_blockers") or []),
                    "pending_review_count": len(status_payload.get("pending_reviews") or []),
                    "net_income": gl_summary.get("net_income"),
                    "ar_open_total": working_capital.get("ar_open_total"),
                    "ap_open_total": working_capital.get("ap_open_total"),
                    "wip_total": working_capital.get("wip_total"),
                    "variance_comment_count": len(
                        close_package.get("variance_commentary") or []
                    ),
                },
                "close_status": status_payload,
                "close_package_summary": {
                    "period": period,
                    "period_start": close_package.get("period_start"),
                    "period_end": close_package.get("period_end"),
                    "gl_summary": gl_summary,
                    "working_capital": working_capital,
                    "variance_commentary": close_package.get(
                        "variance_commentary",
                        [],
                    )[:5],
                },
            }
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            logger.error(
                "month-end close review payload build failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}

    async def _prepare_month_end_close(self, args: dict) -> dict:
        """Run the existing close-preparation workflow after Inbox approval."""
        try:
            period = self._parse_period(args.get("period"))

            from app.workers.close_scheduler_worker import _run_close_for_tenant

            result = await _run_close_for_tenant(
                self.deps.db_client,  # type: ignore[arg-type]
                tenant_id=self.deps.tenant_id,
                period=period,
                created_by="copilot_agent",
            )
            return {"close_prepared": True, **result}
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            logger.error(
                "month-end close preparation failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}

    async def _generate_financial_statement_package(self, args: dict) -> dict:
        """Generate a compact read-only financial statement package summary."""
        import asyncio

        try:
            period_start = self._parse_period(args.get("period_start"), "period_start")
            period_end = self._parse_period(
                args.get("period_end") or period_start,
                "period_end",
            )
            if period_end < period_start:
                raise ValueError("period_end must be the same as or after period_start")

            from app.services.reports_service import ReportsService

            package = await asyncio.to_thread(
                lambda: ReportsService(
                    self.deps.db_client,  # type: ignore[arg-type]
                    self.deps.tenant_id,
                ).statutory_reporting_pack(
                    period_start=period_start,
                    period_end=period_end,
                )
            )
            data = package.model_dump(mode="json")
            balance_sheet = data["balance_sheet"]
            income_statement = data["income_statement"]
            cash_flow = data["cash_flow"]
            retained_earnings = data["retained_earnings_roll_forward"]
            tax_summary = data["tax_summary"]

            return {
                "generated_statement_package": True,
                "period_start": period_start,
                "period_end": period_end,
                "as_of_period": data["as_of_period"],
                "review_path": "/app/reports",
                "summary": {
                    "trial_balance_balanced": data["trial_balance"]["is_balanced"],
                    "balance_sheet": {
                        "total_assets": balance_sheet["total_assets"],
                        "total_liabilities": balance_sheet["total_liabilities"],
                        "total_equity": balance_sheet["total_equity"],
                        "is_balanced": balance_sheet["is_balanced"],
                    },
                    "income_statement": {
                        "total_revenue": income_statement["total_revenue"],
                        "total_expenses": income_statement["total_expenses"],
                        "net_income": income_statement["net_income"],
                        "revenue_line_count": len(
                            income_statement["revenue_lines"]
                        ),
                        "expense_line_count": len(
                            income_statement["expense_lines"]
                        ),
                    },
                    "cash_flow": {
                        "net_change_in_cash": cash_flow["net_change_in_cash"],
                        "ending_cash": cash_flow["ending_cash"],
                    },
                    "retained_earnings": {
                        "ending_retained_earnings": retained_earnings[
                            "ending_retained_earnings"
                        ],
                    },
                    "tax_summary": {
                        "tax_label": tax_summary["tax_label"],
                        "ledger_net_tax_payable": tax_summary[
                            "ledger_net_tax_payable"
                        ],
                    },
                },
            }
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            logger.error(
                "financial statement package generation failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}

    async def _build_invoice_draft_payload(self, args: dict) -> dict:
        """Build a reviewable invoice draft payload without persisting it."""
        try:
            engagement = await self._resolve_invoice_engagement(args)
            if engagement.get("error"):
                return engagement

            period_start = self._parse_optional_date(args.get("period_start"))
            period_end = self._parse_optional_date(args.get("period_end"))

            from app.agents.invoice_drafter_agent import draft_invoice

            invoice_draft = draft_invoice(
                engagement["id"],
                AgentDeps(
                    tenant_id=self.deps.tenant_id,
                    user_id=str(self.deps.user_id),
                    db=self.deps.db_client,  # type: ignore[arg-type]
                ),
                period_start=period_start,
                period_end=period_end,
            )

            if invoice_draft.error:
                return {"error": invoice_draft.error}
            if not invoice_draft.lines:
                return {
                    "error": (
                        "No invoiceable lines were found for "
                        f"{engagement['name']}. Add approved time, billable expenses, "
                        "or billing terms before drafting an invoice."
                    )
                }

            issue_date = period_end or datetime.date.today()
            lines = [
                {
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price),
                    "tax_rate_id": line.tax_rate_id,
                    "time_entry_id": line.time_entry_id,
                    "expense_id": line.expense_id,
                    "service_catalogue_id": line.service_catalogue_id,
                    "amount": str(line.amount),
                    "tax_amount": str(line.tax_amount),
                }
                for line in invoice_draft.lines
            ]
            invoice_payload = {
                "engagement_id": invoice_draft.engagement_id,
                "engagement_name": engagement["name"],
                "client_id": invoice_draft.client_id,
                "currency": invoice_draft.currency,
                "issue_date": issue_date.isoformat(),
                "period_start": (
                    period_start.isoformat()
                    if period_start
                    else invoice_draft.period_start
                ),
                "period_end": (
                    period_end.isoformat() if period_end else invoice_draft.period_end
                ),
                "notes": invoice_draft.summary,
                "billing_arrangement": invoice_draft.billing_arrangement,
                "subtotal": str(invoice_draft.subtotal),
                "tax_total": str(invoice_draft.tax_total),
                "total": str(invoice_draft.total),
                "confidence": invoice_draft.confidence,
                "lines": lines,
            }
            return {
                "invoice_draft": invoice_payload,
                "preview": {
                    "engagement": engagement["name"],
                    "currency": invoice_draft.currency,
                    "subtotal": str(invoice_draft.subtotal),
                    "tax_total": str(invoice_draft.tax_total),
                    "total": str(invoice_draft.total),
                    "line_count": len(lines),
                    "billing_arrangement": invoice_draft.billing_arrangement,
                    "issue_date": issue_date.isoformat(),
                },
            }
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            logger.error(
                "draft_invoice payload build failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}

    async def _resolve_invoice_engagement(self, args: dict) -> dict:
        """Resolve an engagement by explicit ID or fuzzy name for invoice drafting."""
        import asyncio

        db = self.deps.db_client  # type: ignore[assignment]
        engagement_id = str(args.get("engagement_id") or "").strip()
        engagement_name = str(args.get("engagement_name") or "").strip()

        if engagement_id:
            def _fetch_by_id() -> list[dict]:
                result = (
                    db.table("engagements")
                    .select("id, name, client_id, currency, billing_arrangement, status")
                    .eq("tenant_id", self.deps.tenant_id)
                    .eq("id", engagement_id)
                    .is_("deleted_at", "null")
                    .limit(1)
                    .execute()
                )
                return result.data or []

            rows = await asyncio.to_thread(_fetch_by_id)
            if rows:
                return rows[0]
            return {"error": f"Could not find engagement ID {engagement_id!r}."}

        if not engagement_name:
            return {
                "error": (
                    "Tell me which engagement to invoice, for example "
                    "'draft an invoice for Northstar Managed Accounting for June'."
                )
            }

        def _fetch_engagements() -> list[dict]:
            result = (
                db.table("engagements")
                .select("id, name, client_id, currency, billing_arrangement, status")
                .eq("tenant_id", self.deps.tenant_id)
                .is_("deleted_at", "null")
                .limit(100)
                .execute()
            )
            return result.data or []

        engagements = await asyncio.to_thread(_fetch_engagements)
        if not engagements:
            return {"error": "No engagements found for this tenant."}

        for engagement in engagements:
            if str(engagement.get("name", "")).casefold() == engagement_name.casefold():
                return engagement

        names = [str(engagement["name"]) for engagement in engagements]
        matches = difflib.get_close_matches(engagement_name, names, n=3, cutoff=0.4)
        if not matches:
            return {
                "error": (
                    f"Could not find an engagement matching '{engagement_name}'. "
                    f"Available engagements: {', '.join(names)}"
                )
            }
        if len(matches) > 1 and len(engagement_name) < 6:
            return {
                "error": (
                    f"Which engagement did you mean: {', '.join(matches)}?"
                )
            }
        return next(engagement for engagement in engagements if engagement["name"] == matches[0])

    async def _persist_invoice_draft_payload(self, invoice_draft: dict) -> dict:
        """Persist an approved Copilot invoice draft as an invoice in draft status."""
        try:
            from app.models.invoices import InvoiceCreate, InvoiceLineCreate
            from app.services.invoices_service import InvoicesService

            issue_date = None
            if invoice_draft.get("issue_date"):
                issue_date = datetime.date.fromisoformat(str(invoice_draft["issue_date"]))

            invoice_lines = [
                InvoiceLineCreate(
                    description=str(line["description"]),
                    quantity=Decimal(str(line["quantity"])),
                    unit_price=Decimal(str(line["unit_price"])),
                    tax_rate_id=line.get("tax_rate_id"),
                    time_entry_id=line.get("time_entry_id"),
                    expense_id=line.get("expense_id"),
                    service_catalogue_id=line.get("service_catalogue_id"),
                )
                for line in invoice_draft.get("lines", [])
            ]
            if not invoice_lines:
                return {"error": "Approved invoice draft has no lines."}

            invoice_create = InvoiceCreate(
                engagement_id=str(invoice_draft["engagement_id"]),
                client_id=str(invoice_draft["client_id"]),
                currency=str(invoice_draft.get("currency") or "USD"),
                issue_date=issue_date,
                notes=invoice_draft.get("notes") or invoice_draft.get("summary"),
                lines=invoice_lines,
            )
            invoice = await InvoicesService(
                self.deps.db_client,  # type: ignore[arg-type]
                self.deps.tenant_id,
            ).create_invoice(invoice_create, str(self.deps.user_id) or "copilot_agent")

            return {
                "invoice_created": True,
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "status": invoice.status,
                "engagement_id": invoice.engagement_id,
                "engagement": invoice_draft.get("engagement_name"),
                "currency": invoice.currency,
                "total": invoice.total,
                "line_count": len(invoice_lines),
            }
        except Exception as exc:
            logger.error(
                "Copilot approved invoice draft persistence failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}

    @staticmethod
    def _parse_optional_date(value: object) -> datetime.date | None:
        if not value:
            return None
        if isinstance(value, datetime.date):
            return value
        return datetime.date.fromisoformat(str(value))

    @staticmethod
    def _parse_period(value: object, field_name: str = "period") -> str:
        period = str(value or "").strip()
        if len(period) != 7 or period[4] != "-":
            raise ValueError(f"{field_name} must be formatted as YYYY-MM")
        try:
            year = int(period[:4])
            month = int(period[5:7])
        except ValueError as exc:
            raise ValueError(f"{field_name} must be formatted as YYYY-MM") from exc
        if year < 1900 or month < 1 or month > 12:
            raise ValueError(f"{field_name} must be a valid accounting period")
        return f"{year:04d}-{month:02d}"

    async def _log_time_entry(self, args: dict) -> dict:
        """Log a time entry via chat — fuzzy-matches project name, resolves employee from user_id.

        Security: only non-PII fields are returned to the LLM (no employee names,
        emails, or raw rates — only hours, project name, and calculated billable value).
        """
        import asyncio

        try:
            db = self.deps.db_client  # type: ignore[assignment]

            # 1. Fetch active projects for this tenant
            def _fetch_projects() -> list[dict]:
                result = (
                    db.table("projects")
                    .select("id, name, engagement_id")
                    .eq("tenant_id", self.deps.tenant_id)
                    .eq("status", "active")
                    .is_("deleted_at", "null")
                    .execute()
                )
                return result.data or []

            projects = await asyncio.to_thread(_fetch_projects)

            if not projects:
                return {"error": "No active projects found for this tenant."}

            # 2. Fuzzy-match project name
            project_names = [p["name"] for p in projects]
            query_name = args.get("project_name", "")
            matches = difflib.get_close_matches(query_name, project_names, n=1, cutoff=0.4)

            if not matches:
                return {
                    "error": (
                        f"Could not find a project matching '{query_name}'. "
                        f"Active projects: {', '.join(project_names)}"
                    )
                }

            matched_project = next(p for p in projects if p["name"] == matches[0])

            # 3. Resolve employee from authenticated user_id — optional (manager may log on behalf)
            def _fetch_employee() -> list[dict]:
                result = (
                    db.table("employees")
                    .select("id, default_bill_rate, default_bill_rate_currency")
                    .eq("tenant_id", self.deps.tenant_id)
                    .eq("user_id", str(self.deps.user_id))
                    .limit(1)
                    .execute()
                )
                return result.data or []

            employee_rows = await asyncio.to_thread(_fetch_employee)
            employee_id: str | None = employee_rows[0]["id"] if employee_rows else None
            bill_rate = (
                Decimal(str(employee_rows[0].get("default_bill_rate") or "0"))
                if employee_rows
                else Decimal("0")
            )

            # 4. Build and insert the entry
            entry_date = args.get("date") or datetime.date.today().isoformat()
            hours = Decimal(str(args.get("hours", 0)))
            billable: bool = args.get("billable", True)
            description: str = args.get("description") or ""

            payload: dict = {
                "tenant_id": str(self.deps.tenant_id),
                "project_id": matched_project["id"],
                "date": entry_date,
                "hours": str(hours),
                "description": description,
                "billable": billable,
                "billing_status": "unbilled" if billable else "non_billable",
                "status": "submitted",
            }
            if employee_id:
                payload["employee_id"] = employee_id

            def _insert() -> dict:
                result = db.table("time_entries").insert(payload).execute()
                return result.data[0]

            row = await asyncio.to_thread(_insert)

            billable_value = (hours * bill_rate).quantize(Decimal("0.01")) if billable else Decimal("0.00")

            logger.info(
                "log_time_entry tool: entry created",
                extra={
                    "tenant_id": self.deps.tenant_id,
                    "project_id": matched_project["id"],
                    "hours": str(hours),
                    "billable": billable,
                },
            )

            return {
                "logged": True,
                "project": matched_project["name"],
                "hours": float(hours),
                "date": entry_date,
                "billable": billable,
                "billable_value": str(billable_value),
                "description": description,
                "entry_id": row["id"],
            }

        except Exception as exc:
            logger.error(
                "log_time_entry tool failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}

    async def _update_rate_card(self, args: dict) -> dict:
        """Set or update an employee's billing rate via chat.

        Two paths:
        - engagement_name provided: upsert a rate_card_lines row scoped to that engagement.
        - engagement_name absent: update the employee's default_bill_rate on the employees table.

        Security: employee names are looked up from DB and passed back only as confirmation
        — no email, user_id, or cost rates are returned to the LLM.
        """
        import asyncio

        try:
            db = self.deps.db_client  # type: ignore[assignment]

            # 1. Fetch employees for fuzzy matching
            def _fetch_employees() -> list[dict]:
                result = (
                    db.table("employees")
                    .select("id, first_name, last_name, default_bill_rate, default_bill_rate_currency")
                    .eq("tenant_id", self.deps.tenant_id)
                    .execute()
                )
                return result.data or []

            employees = await asyncio.to_thread(_fetch_employees)

            if not employees:
                return {"error": "No employees found for this tenant."}

            # Build full-name list for fuzzy matching
            emp_names = [f"{e['first_name']} {e['last_name']}" for e in employees]
            query_name = args.get("employee_name", "")
            matches = difflib.get_close_matches(query_name, emp_names, n=1, cutoff=0.4)

            if not matches:
                return {
                    "error": (
                        f"Could not find employee '{query_name}'. "
                        f"Employees: {', '.join(emp_names)}"
                    )
                }

            employee = next(
                e for e in employees if f"{e['first_name']} {e['last_name']}" == matches[0]
            )
            employee_full_name = f"{employee['first_name']} {employee['last_name']}"

            rate = Decimal(str(args.get("rate", 0)))
            currency: str = args.get("currency") or "GBP"
            effective_date: str = args.get("effective_date") or datetime.date.today().isoformat()

            # 2. If engagement_name given, upsert a rate_card_lines row for that engagement
            if args.get("engagement_name"):
                def _fetch_engagements() -> list[dict]:
                    result = (
                        db.table("engagements")
                        .select("id, name")
                        .eq("tenant_id", self.deps.tenant_id)
                        .is_("deleted_at", "null")
                        .execute()
                    )
                    return result.data or []

                engagements = await asyncio.to_thread(_fetch_engagements)
                eng_names = [e["name"] for e in engagements]
                eng_matches = difflib.get_close_matches(
                    args["engagement_name"], eng_names, n=1, cutoff=0.4
                )

                if not eng_matches:
                    return {
                        "error": (
                            f"Could not find engagement '{args['engagement_name']}'. "
                            f"Engagements: {', '.join(eng_names) if eng_names else 'none found'}"
                        )
                    }

                engagement = next(e for e in engagements if e["name"] == eng_matches[0])

                # Check for existing rate_card_lines row scoped to this employee+engagement
                def _fetch_existing_line() -> list[dict]:
                    result = (
                        db.table("rate_card_lines")
                        .select("id")
                        .eq("tenant_id", self.deps.tenant_id)
                        .eq("engagement_id", engagement["id"])
                        .eq("employee_id", employee["id"])
                        .limit(1)
                        .execute()
                    )
                    return result.data or []

                existing = await asyncio.to_thread(_fetch_existing_line)

                if existing:
                    def _update_line() -> None:
                        db.table("rate_card_lines").update({
                            "rate": str(rate),
                            "currency": currency,
                        }).eq("id", existing[0]["id"]).execute()

                    await asyncio.to_thread(_update_line)
                else:
                    def _insert_line() -> None:
                        db.table("rate_card_lines").insert({
                            "tenant_id": str(self.deps.tenant_id),
                            "engagement_id": engagement["id"],
                            "employee_id": employee["id"],
                            "rate": str(rate),
                            "currency": currency,
                            "effective_date": effective_date,
                        }).execute()

                    await asyncio.to_thread(_insert_line)

                logger.info(
                    "update_rate_card tool: engagement rate updated",
                    extra={
                        "tenant_id": self.deps.tenant_id,
                        "engagement_id": engagement["id"],
                        "employee_id": employee["id"],
                    },
                )

                return {
                    "updated": True,
                    "employee": employee_full_name,
                    "engagement": engagement["name"],
                    "new_rate": f"{currency} {rate}/hr",
                }

            # 3. No engagement — update default bill rate on employees table
            def _update_default_rate() -> None:
                db.table("employees").update({
                    "default_bill_rate": str(rate),
                    "default_bill_rate_currency": currency,
                }).eq("id", employee["id"]).execute()

            await asyncio.to_thread(_update_default_rate)

            logger.info(
                "update_rate_card tool: default rate updated",
                extra={
                    "tenant_id": self.deps.tenant_id,
                    "employee_id": employee["id"],
                },
            )

            return {
                "updated": True,
                "employee": employee_full_name,
                "new_default_rate": f"{currency} {rate}/hr",
            }

        except Exception as exc:
            logger.error(
                "update_rate_card tool failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}
