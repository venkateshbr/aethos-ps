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
from uuid import uuid4

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
        "When users ask for today's finance ops check, a daily finance ops check, "
        "or the AI Finance Ops Manager command center, use run_finance_ops_check. "
        "It is read-only and separates findings from actions that need Inbox approval.\n"
        "When users ask to create the next recommended work items or action plan "
        "from the finance ops check, use create_finance_ops_action_plan. It creates "
        "one Inbox review task for the manager-level action plan and does not "
        "approve invoices, payments, journals, or emails.\n"
        "When users ask to draft, send, or prepare collections reminders for "
        "overdue customer invoices, use draft_collection_reminders. It creates "
        "Inbox review tasks and never sends customer email without approval.\n"
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
            "name": "run_finance_ops_check",
            "description": (
                "Compile a read-only AI Finance Ops Manager command-center summary "
                "across AR, AP, WIP, close readiness, the report action queue, "
                "and recent agent/workflow status. Use when the user asks for "
                "today's finance ops check or a daily command-center review."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}$",
                        "description": (
                            "Accounting period for close readiness, formatted YYYY-MM. "
                            "Defaults to the current month."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 25,
                        "description": "Maximum queue/run/project examples to include.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "create_finance_ops_action_plan",
            "description": (
                "Create a manager-level AI Finance Ops action plan from the live "
                "daily finance ops check. Use after run_finance_ops_check when the "
                "user asks to create the next recommended work items, work queue, "
                "or action plan. The plan is routed to Inbox for review and does "
                "not directly approve invoices, payments, journals, or emails."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}$",
                        "description": (
                            "Accounting period for the plan, formatted YYYY-MM. "
                            "Defaults to the current month."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 25,
                        "description": "Maximum queue/run/project examples to include.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "draft_collection_reminders",
            "description": (
                "Draft collections reminder emails for eligible overdue customer "
                "invoices and route each send action to Inbox for human approval. "
                "Use when the user asks to send, draft, or prepare reminders for "
                "overdue receivables. This tool never sends email directly."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "minimum_days_overdue": {
                        "type": "integer",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 365,
                        "description": (
                            "Only consider invoices at least this many days overdue."
                        ),
                    },
                    "tone": {
                        "type": "string",
                        "enum": ["auto", "gentle", "firm", "final"],
                        "default": "auto",
                        "description": (
                            "Reminder tone. Use auto to let the collections policy "
                            "choose gentle, firm, or final from days overdue."
                        ),
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Optional client-name filter.",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 25,
                        "description": "Maximum reminder drafts to queue for review.",
                    },
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
            prompt_version="cop-v3",
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
        if tool_name == "run_finance_ops_check":
            return await self._run_finance_ops_check(tool_input)
        if tool_name == "create_finance_ops_action_plan":
            return await self._build_finance_ops_action_plan_payload(tool_input)
        if tool_name == "draft_collection_reminders":
            return await self._draft_collection_reminders(tool_input)
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
            elif tool_name == "create_finance_ops_action_plan":
                plan_payload = await self._build_finance_ops_action_plan_payload(tool_input)
                if plan_payload.get("error"):
                    return {
                        "error": plan_payload["error"],
                        "tool_name": tool_name,
                        "risk_class": risk_class,
                    }
                output.update(plan_payload)
            elif tool_name == "draft_collection_reminders":
                return await self._draft_collection_reminders(tool_input)

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
            readiness_evidence = close_package.get("readiness_evidence") or {}

            return {
                "period": period,
                "preview": {
                    "period": period,
                    "workflow": "month_end_close",
                    "lock_blocker_count": len(status_payload.get("lock_blockers") or []),
                    "pending_review_count": len(status_payload.get("pending_reviews") or []),
                    "override_count": len(status_payload.get("overrides") or []),
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
                    "readiness_evidence": readiness_evidence,
                    "close_overrides": close_package.get("close_overrides", []),
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

    async def _draft_collection_reminders(self, args: dict) -> dict:
        """Draft overdue-invoice reminders and route sends to Inbox approval."""
        import asyncio

        collections_run_id: str | None = None
        collections_ledger = AgentRunLedger(self.deps.db_client, self.deps.tenant_id)
        try:
            minimum_days_overdue = int(args.get("minimum_days_overdue") or 1)
            limit = int(args.get("limit") or 10)
            tone_arg = str(args.get("tone") or "auto").strip().lower()
            client_filter = str(args.get("client_name") or "").strip()
            if minimum_days_overdue < 1 or minimum_days_overdue > 365:
                raise ValueError("minimum_days_overdue must be between 1 and 365")
            if limit < 1 or limit > 25:
                raise ValueError("limit must be between 1 and 25")
            if tone_arg not in {"auto", "gentle", "firm", "final"}:
                raise ValueError("tone must be one of auto, gentle, firm, or final")
            requested_tone = None if tone_arg == "auto" else tone_arg

            ledger_input = {
                "minimum_days_overdue": minimum_days_overdue,
                "tone": tone_arg,
                "client_name": client_filter or None,
                "limit": limit,
            }
            collections_run_id = await collections_ledger.start_run(
                agent_name="collections_agent",
                trigger_type="chat",
                user_id=str(self.deps.user_id),
                input_payload=ledger_input,
                prompt_version="collections-copilot-v1",
                trace_id=trace_id_var.get("") or None,
            )

            from app.agents.collections_agent import (
                collection_tone_for_days,
                days_overdue_for_invoice,
                draft_collection_email,
            )
            from app.workers.collections import (
                _collections_action_count,
                _recent_collections_action_exists,
                _resolve_collections_policy,
            )

            today = datetime.date.today()
            read_started = time.perf_counter()
            candidates = await asyncio.to_thread(
                lambda: self._collection_invoice_candidates(
                    today=today,
                    limit=limit,
                )
            )
            await self._record_collections_tool_step(
                collections_ledger,
                collections_run_id,
                tool_name="find_overdue_invoices",
                risk_class="read_only",
                input_payload={
                    "as_of": today.isoformat(),
                    "statuses": ["sent", "overdue"],
                    "minimum_days_overdue": minimum_days_overdue,
                    "client_name": client_filter or None,
                    "limit": limit,
                },
                output_payload={
                    "candidate_count": len(candidates),
                    "candidate_invoice_ids": [
                        str(row.get("id") or "") for row in candidates[:limit]
                    ],
                },
                status="succeeded",
                started_at=read_started,
            )

            deps = AgentDeps(
                tenant_id=self.deps.tenant_id,
                user_id=str(self.deps.user_id),
                db=self.deps.db_client,  # type: ignore[arg-type]
            )
            queued: list[dict] = []
            skipped: list[dict] = []
            draft_started = time.perf_counter()
            db = self.deps.db_client  # type: ignore[assignment]

            for invoice in candidates:
                if len(queued) >= limit:
                    break
                invoice_id = str(invoice.get("id") or "")
                try:
                    days_overdue = days_overdue_for_invoice(invoice)
                    invoice_client_id = invoice.get("client_id")
                    client = await asyncio.to_thread(
                        lambda client_id=invoice_client_id: self._collection_client(
                            client_id
                        )
                    )
                    client_name = str(client.get("name") or "Valued Client")
                    if client_filter and client_filter.lower() not in client_name.lower():
                        skipped.append(
                            self._collection_skip(
                                invoice,
                                reason="client_filter_mismatch",
                                days_overdue=days_overdue,
                                client_name=client_name,
                            )
                        )
                        continue
                    if days_overdue < minimum_days_overdue:
                        skipped.append(
                            self._collection_skip(
                                invoice,
                                reason="below_minimum_days_overdue",
                                days_overdue=days_overdue,
                                client_name=client_name,
                            )
                        )
                        continue

                    policy = await asyncio.to_thread(
                        lambda client_id=invoice_client_id: _resolve_collections_policy(
                            db,
                            self.deps.tenant_id,
                            client_id,
                        )
                    )
                    policy_tone = collection_tone_for_days(days_overdue, policy)
                    if policy_tone is None:
                        skipped.append(
                            self._collection_skip(
                                invoice,
                                reason="outside_collections_policy",
                                days_overdue=days_overdue,
                                client_name=client_name,
                            )
                        )
                        continue

                    reminder_count = await asyncio.to_thread(
                        lambda current_invoice_id=invoice_id: _collections_action_count(
                            db,
                            self.deps.tenant_id,
                            current_invoice_id,
                        )
                    )
                    if reminder_count >= policy.max_reminders_per_invoice:
                        skipped.append(
                            self._collection_skip(
                                invoice,
                                reason="max_reminders_reached",
                                days_overdue=days_overdue,
                                client_name=client_name,
                            )
                        )
                        continue

                    resolved_tone = requested_tone or policy_tone
                    duplicate = await asyncio.to_thread(
                        lambda current_invoice_id=invoice_id,
                        current_tone=str(resolved_tone),
                        cooldown_days=policy.cooldown_days: _recent_collections_action_exists(
                            db,
                            self.deps.tenant_id,
                            current_invoice_id,
                            current_tone,
                            cooldown_days=cooldown_days,
                        )
                    )
                    if duplicate:
                        skipped.append(
                            self._collection_skip(
                                invoice,
                                reason="cooldown_duplicate_suppressed",
                                days_overdue=days_overdue,
                                client_name=client_name,
                            )
                        )
                        continue

                    client_email = self._collection_client_email(client)
                    if not client_email:
                        skipped.append(
                            self._collection_skip(
                                invoice,
                                reason="missing_client_email",
                                days_overdue=days_overdue,
                                client_name=client_name,
                            )
                        )
                        continue

                    draft = await asyncio.to_thread(
                        lambda current_invoice=invoice,
                        current_policy=policy,
                        current_tone=resolved_tone: draft_collection_email(
                            current_invoice,
                            deps,
                            policy=current_policy,
                            tone=current_tone,  # type: ignore[arg-type]
                        )
                    )
                    draft.client_email = client_email
                    draft_payload = draft.model_dump(mode="json")
                    draft_payload.update(
                        {
                            "amount": draft_payload.get("amount_due"),
                            "body_preview": self._body_preview(draft.body_html),
                            "eligibility_reason": (
                                f"Invoice {draft.invoice_number} is "
                                f"{days_overdue} days overdue with status "
                                f"{invoice.get('status', 'unknown')}."
                            ),
                            "requested_by_user_id": str(self.deps.user_id),
                            "source_agent": "copilot_agent",
                        }
                    )
                    suggestion = await write_agent_suggestion(
                        deps=deps,
                        agent_name="collections_agent",
                        action_type="send_email",
                        document_id=None,
                        output=draft_payload,
                        confidence=draft.confidence,
                        autonomy_level=2,
                        related_entity_type="invoice",
                        related_entity_id=invoice_id,
                    )
                    queued.append(
                        self._collection_review_summary(
                            draft_payload,
                            suggestion_id=str(suggestion.get("id") or ""),
                        )
                    )
                except Exception as exc:
                    skipped.append(
                        self._collection_skip(
                            invoice,
                            reason=f"draft_failed:{str(exc)[:80]}",
                            days_overdue=None,
                            client_name=None,
                        )
                    )

            await self._record_collections_tool_step(
                collections_ledger,
                collections_run_id,
                tool_name="draft_collection_email",
                risk_class="draft",
                input_payload={
                    "candidate_count": len(candidates),
                    "minimum_days_overdue": minimum_days_overdue,
                    "tone": tone_arg,
                },
                output_payload={
                    "draft_count": len(queued),
                    "skipped_count": len(skipped),
                    "drafts": queued,
                    "skipped": skipped[:limit],
                },
                status="succeeded",
                started_at=draft_started,
            )
            send_started = time.perf_counter()
            await self._record_collections_tool_step(
                collections_ledger,
                collections_run_id,
                tool_name="send_email",
                risk_class="write_money_in",
                input_payload={
                    "draft_count": len(queued),
                    "approval_surface": "/app/inbox",
                },
                output_payload={
                    "status": "routed_to_inbox",
                    "suggestion_ids": [row["suggestion_id"] for row in queued],
                    "review_tasks_created": len(queued),
                },
                status="skipped",
                started_at=send_started,
            )

            result = {
                "collections_reminders_drafted": True,
                "requires_review": bool(queued),
                "target_agent": "collections_agent",
                "action_type": "send_email",
                "tool_name": "draft_collection_reminders",
                "risk_class": "write_money_in",
                "eligible_invoice_count": len(queued),
                "created_review_tasks": len(queued),
                "review_path": "/app/inbox",
                "drafts": queued,
                "skipped": skipped[:limit],
                "message": (
                    f"Created {len(queued)} Inbox review task(s) for collections "
                    "reminders. No email was sent."
                ),
            }
            await collections_ledger.complete_run(
                collections_run_id,
                status="succeeded",
                output_payload=result,
            )
            return result
        except ValueError as exc:
            await collections_ledger.complete_run(
                collections_run_id,
                status="failed",
                error_message=str(exc),
            )
            return {"error": str(exc), "tool_name": "draft_collection_reminders"}
        except Exception as exc:
            await collections_ledger.complete_run(
                collections_run_id,
                status="failed",
                error_message=str(exc),
            )
            logger.error(
                "collections reminder drafting failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc), "tool_name": "draft_collection_reminders"}

    def _collection_invoice_candidates(
        self,
        *,
        today: datetime.date,
        limit: int,
    ) -> list[dict]:
        rows = (
            self.deps.db_client.table("invoices")  # type: ignore[attr-defined]
            .select(
                "id,invoice_number,total,currency,due_date,client_id,"
                "stripe_payment_link_url,status"
            )
            .eq("tenant_id", self.deps.tenant_id)
            .in_("status", ["sent", "overdue"])
            .lt("due_date", today.isoformat())
            .is_("deleted_at", "null")
            .order("due_date")
            .limit(limit * 5)
            .execute()
            .data
            or []
        )
        return list(rows)

    def _collection_client(self, client_id: object) -> dict:
        if not client_id:
            return {}
        rows = (
            self.deps.db_client.table("clients")  # type: ignore[attr-defined]
            .select("id,name,billing_email,billing_address")
            .eq("tenant_id", self.deps.tenant_id)
            .eq("id", str(client_id))
            .limit(1)
            .execute()
            .data
            or []
        )
        return dict(rows[0]) if rows else {}

    @staticmethod
    def _collection_client_email(client: dict) -> str:
        billing_address = client.get("billing_address") or {}
        if not isinstance(billing_address, dict):
            billing_address = {}
        return str(
            billing_address.get("email")
            or client.get("billing_email")
            or client.get("email")
            or ""
        ).strip()

    @staticmethod
    def _body_preview(body_html: str, *, limit: int = 240) -> str:
        import re

        text = re.sub(r"<[^>]+>", " ", body_html)
        text = " ".join(text.split())
        if len(text) <= limit:
            return text
        return f"{text[: limit - 1].rstrip()}..."

    @staticmethod
    def _collection_skip(
        invoice: dict,
        *,
        reason: str,
        days_overdue: int | None,
        client_name: str | None,
    ) -> dict:
        return {
            "invoice_id": str(invoice.get("id") or ""),
            "invoice_number": str(invoice.get("invoice_number") or ""),
            "client_name": client_name or "",
            "days_overdue": days_overdue,
            "reason": reason,
        }

    @staticmethod
    def _collection_review_summary(payload: dict, *, suggestion_id: str) -> dict:
        return {
            "suggestion_id": suggestion_id,
            "invoice_id": str(payload.get("invoice_id") or ""),
            "invoice_number": str(payload.get("invoice_number") or ""),
            "client_name": str(payload.get("client_name") or ""),
            "recipient": mask_pii(str(payload.get("client_email") or "")),
            "tone": str(payload.get("tone") or ""),
            "subject": str(payload.get("subject") or ""),
            "days_overdue": int(payload.get("days_overdue") or 0),
            "amount_due": str(payload.get("amount_due") or "0"),
            "currency": str(payload.get("currency") or ""),
            "body_preview": str(payload.get("body_preview") or ""),
            "requires_inbox_approval": True,
            "review_path": "/app/inbox",
        }

    async def _record_collections_tool_step(
        self,
        ledger: AgentRunLedger,
        run_id: str | None,
        *,
        tool_name: str,
        risk_class: str,
        input_payload: dict,
        output_payload: dict,
        status: str,
        started_at: float,
    ) -> None:
        await ledger.record_tool_invocation(
            run_id,
            tool_name=tool_name,
            risk_class=risk_class,  # type: ignore[arg-type]
            input_payload=input_payload,
            output_payload=output_payload,
            status=status,  # type: ignore[arg-type]
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )

    async def _run_finance_ops_check(self, args: dict) -> dict:
        """Build a read-only finance-ops command-center synthesis."""
        import asyncio

        try:
            period = self._parse_period(
                args.get("period") or datetime.date.today().strftime("%Y-%m")
            )
            limit = int(args.get("limit") or 10)
            if limit < 1 or limit > 25:
                raise ValueError("limit must be between 1 and 25")

            from app.services.agents_service import AgentsService
            from app.services.close_status_service import CloseStatusService
            from app.services.reports_service import ReportsService

            def _build() -> dict:
                reports = ReportsService(
                    self.deps.db_client,  # type: ignore[arg-type]
                    self.deps.tenant_id,
                )
                agents = AgentsService(
                    self.deps.db_client,  # type: ignore[arg-type]
                    self.deps.tenant_id,
                )
                close_status_obj = CloseStatusService(
                    self.deps.db_client,  # type: ignore[arg-type]
                    self.deps.tenant_id,
                ).get_status(period)

                close_status = (
                    close_status_obj.as_dict()
                    if hasattr(close_status_obj, "as_dict")
                    else dict(close_status_obj or {})
                )
                ar_aging = reports.ar_aging() or {}
                ap_aging = reports.ap_aging() or {}
                wip = reports.wip() or []
                action_queue = reports.action_queue(role="all", limit=limit) or []
                agent_runs = (agents.list_agent_runs(limit=limit) or {}).get("runs") or []
                workflow_runs = (
                    (agents.list_agent_workflow_runs(limit=limit) or {}).get(
                        "workflow_runs"
                    )
                    or []
                )
                return self._format_finance_ops_check(
                    period=period,
                    limit=limit,
                    ar_aging=ar_aging,
                    ap_aging=ap_aging,
                    wip=wip,
                    close_status=close_status,
                    action_queue=action_queue,
                    agent_runs=agent_runs,
                    workflow_runs=workflow_runs,
                )

            return await asyncio.to_thread(_build)
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            logger.error(
                "finance ops command-center check failed",
                exc_info=True,
                extra={"tenant_id": self.deps.tenant_id},
            )
            return {"error": str(exc)}

    async def _build_finance_ops_action_plan_payload(self, args: dict) -> dict:
        """Create a reviewable manager-level action plan from the daily check.

        The plan is intentionally not an auto-dispatcher. It records which
        specialist workflows should run next, while the specialist workflows
        themselves continue to create their own Inbox-gated tasks.
        """
        check = await self._run_finance_ops_check(args)
        if check.get("error"):
            return check

        findings = check.get("read_only_findings")
        if not isinstance(findings, dict):
            findings = {}
        recommended_actions = check.get("recommended_actions")
        if not isinstance(recommended_actions, list):
            recommended_actions = []

        action_items = [
            self._finance_ops_action_plan_item(
                idx=idx,
                action=action,
                findings=findings,
            )
            for idx, action in enumerate(recommended_actions, start=1)
            if isinstance(action, dict)
        ]
        domains = [item["domain"] for item in action_items]
        approval_count = sum(
            1 for item in action_items if item.get("requires_inbox_approval")
        )
        period = str(check.get("period") or args.get("period") or "")
        plan_id = f"finance-ops-plan-{uuid4()}"
        summary = (
            f"{len(action_items)} finance ops work item"
            f"{'' if len(action_items) == 1 else 's'} proposed for {period}."
            if action_items
            else f"No finance ops work items are currently required for {period}."
        )

        preview = {
            "period": period,
            "status": "ready_for_review" if action_items else "no_actions",
            "action_count": len(action_items),
            "requires_inbox_approval_count": approval_count,
            "domains": ", ".join(domains) if domains else "none",
        }
        return {
            "finance_ops_action_plan": True,
            "plan_id": plan_id,
            "period": period,
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "source_tool": "run_finance_ops_check",
            "source_check_generated_at": check.get("generated_at"),
            "summary": summary,
            "status": preview["status"],
            "action_count": len(action_items),
            "requires_inbox_approval_count": approval_count,
            "domains": domains,
            "action_items": action_items,
            "empty_states": check.get("empty_states") or [],
            "source_findings": findings,
            "review_paths": check.get("review_paths") or [
                "/app/copilot",
                "/app/reports",
                "/app/inbox",
                "/app/settings",
            ],
            "approval_effect": (
                "Approval records manager review of this action plan only. "
                "Specialist invoice, payment, journal, and email actions remain "
                "separately gated by Inbox."
            ),
            "preview": preview,
        }

    def _format_finance_ops_check(
        self,
        *,
        period: str,
        limit: int,
        ar_aging: dict,
        ap_aging: dict,
        wip: list[dict],
        close_status: dict,
        action_queue: list[dict],
        agent_runs: list[dict],
        workflow_runs: list[dict],
    ) -> dict:
        ar_total = self._money_decimal(ar_aging.get("total"))
        ap_total = self._money_decimal(ap_aging.get("total"))
        wip_total = self._sum_money_rows(wip, "wip_value")
        failed_run_count = sum(
            1
            for row in agent_runs
            if row.get("status") == "failed" or int(row.get("failed_tool_count") or 0) > 0
        )
        failed_workflow_count = sum(
            1 for row in workflow_runs if row.get("status") == "failed"
        )
        active_workflow_count = sum(
            1
            for row in workflow_runs
            if row.get("status") in {"running", "pending", "queued"}
        )

        read_only_findings = {
            "ar": {
                "source": "reports.ar_aging",
                "status": "empty" if ar_total == 0 else "attention",
                "total": str(ar_aging.get("total", "0")),
                "over_90": str(ar_aging.get("over_90", "0")),
                "buckets": self._money_buckets(ar_aging),
                "review_path": "/app/reports",
            },
            "ap": {
                "source": "reports.ap_aging",
                "status": "empty" if ap_total == 0 else "attention",
                "total": str(ap_aging.get("total", "0")),
                "over_90": str(ap_aging.get("over_90", "0")),
                "buckets": self._money_buckets(ap_aging),
                "review_path": "/app/reports",
            },
            "wip": {
                "source": "reports.wip",
                "status": "empty" if wip_total == 0 else "attention",
                "project_count": len(wip),
                "total": str(wip_total.quantize(Decimal("0.01"))),
                "top_projects": self._top_wip_projects(wip, limit),
                "review_path": "/app/reports",
            },
            "close_readiness": {
                "source": "close_status",
                "status": close_status.get("status") or "unknown",
                "period": period,
                "ready_to_lock": bool(close_status.get("ready_to_lock")),
                "locked": bool(close_status.get("locked")),
                "lock_blocker_count": len(close_status.get("lock_blockers") or []),
                "pending_review_count": len(close_status.get("pending_reviews") or []),
                "checklist": [
                    {
                        "code": item.get("code"),
                        "status": item.get("status"),
                        "summary": item.get("summary"),
                    }
                    for item in close_status.get("checklist") or []
                ][:limit],
                "review_path": "/app/accounting/journals",
            },
            "action_queue": {
                "source": "reports.action_queue",
                "status": "empty" if not action_queue else "attention",
                "item_count": len(action_queue),
                "items": [
                    self._summarise_action_queue_item(item)
                    for item in action_queue[:limit]
                ],
                "review_path": "/app/reports",
            },
            "agent_workflows": {
                "source": "agents_service",
                "status": self._agent_workflow_status(
                    agent_runs,
                    workflow_runs,
                    failed_run_count + failed_workflow_count,
                ),
                "recent_run_count": len(agent_runs),
                "failed_run_count": failed_run_count,
                "recent_workflow_count": len(workflow_runs),
                "active_workflow_count": active_workflow_count,
                "failed_workflow_count": failed_workflow_count,
                "recent_runs": [
                    self._summarise_agent_run(row) for row in agent_runs[:limit]
                ],
                "recent_workflows": [
                    self._summarise_workflow_run(row)
                    for row in workflow_runs[:limit]
                ],
                "review_path": "/app/settings",
            },
        }
        empty_states = self._finance_ops_empty_states(read_only_findings)
        return {
            "finance_ops_check": True,
            "period": period,
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "read_only_findings": read_only_findings,
            "recommended_actions": self._finance_ops_recommended_actions(
                ar_total=ar_total,
                ap_total=ap_total,
                wip_total=wip_total,
                close_status=close_status,
            ),
            "empty_states": empty_states,
            "review_paths": [
                "/app/copilot",
                "/app/reports",
                "/app/inbox",
                "/app/settings",
            ],
        }

    @classmethod
    def _finance_ops_action_plan_item(
        cls,
        *,
        idx: int,
        action: dict,
        findings: dict,
    ) -> dict:
        domain = str(action.get("domain") or "ops")
        return {
            "action_id": f"finance-ops-{idx:02d}-{domain}",
            "domain": domain,
            "recommendation": str(action.get("action") or "Review finance ops item."),
            "suggested_agent": str(action.get("suggested_agent") or "copilot_agent"),
            "suggested_tool": str(action.get("suggested_tool") or ""),
            "risk_class": str(action.get("risk_class") or "draft"),
            "requires_inbox_approval": bool(action.get("requires_inbox_approval")),
            "rationale": cls._finance_ops_action_rationale(domain, findings),
            "review_path": str(action.get("review_path") or "/app/inbox"),
            "status": "proposed",
        }

    @staticmethod
    def _finance_ops_action_rationale(domain: str, findings: dict) -> str:
        finding_key = "close_readiness" if domain == "close" else domain
        finding = findings.get(finding_key)
        if not isinstance(finding, dict):
            return "Recommended by the live finance ops command-center check."
        if domain == "ar":
            return (
                f"AR aging total is {finding.get('total', '0')} with "
                f"{finding.get('over_90', '0')} over 90 days."
            )
        if domain == "ap":
            return (
                f"AP aging total is {finding.get('total', '0')} with "
                f"{finding.get('over_90', '0')} over 90 days."
            )
        if domain == "wip":
            return (
                f"WIP totals {finding.get('total', '0')} across "
                f"{finding.get('project_count', 0)} projects."
            )
        if domain == "close":
            return (
                f"Close readiness for {finding.get('period', 'the period')} is "
                f"{finding.get('status', 'unknown')} with "
                f"{finding.get('lock_blocker_count', 0)} lock blockers and "
                f"{finding.get('pending_review_count', 0)} pending reviews."
            )
        return "Recommended by the live finance ops command-center check."

    @staticmethod
    def _money_decimal(value: object) -> Decimal:
        try:
            return Decimal(str(value or "0"))
        except Exception:
            return Decimal("0")

    @classmethod
    def _sum_money_rows(cls, rows: list[dict], key: str) -> Decimal:
        total = Decimal("0")
        for row in rows:
            total += cls._money_decimal(row.get(key))
        return total

    @staticmethod
    def _money_buckets(payload: dict) -> dict:
        return {
            "0_30": str(payload.get("0_30", "0")),
            "31_60": str(payload.get("31_60", "0")),
            "61_90": str(payload.get("61_90", "0")),
            "over_90": str(payload.get("over_90", "0")),
        }

    @classmethod
    def _top_wip_projects(cls, rows: list[dict], limit: int) -> list[dict]:
        sorted_rows = sorted(
            rows,
            key=lambda row: cls._money_decimal(row.get("wip_value")),
            reverse=True,
        )
        return [
            {
                "project_id": str(row.get("project_id") or ""),
                "project_name": str(row.get("project_name") or ""),
                "unbilled_hours": str(row.get("unbilled_hours") or "0"),
                "wip_value": str(row.get("wip_value") or "0"),
            }
            for row in sorted_rows[:limit]
        ]

    @staticmethod
    def _summarise_action_queue_item(item: dict) -> dict:
        return {
            "id": str(item.get("id") or ""),
            "role": item.get("role"),
            "source_type": item.get("source_type"),
            "priority": item.get("priority"),
            "entity_type": item.get("entity_type"),
            "entity_id": str(item.get("entity_id") or ""),
            "entity_name": str(item.get("entity_name") or ""),
            "summary": item.get("summary"),
            "recommended_action": item.get("recommended_action"),
            "route_hint": item.get("route_hint"),
        }

    @staticmethod
    def _summarise_agent_run(row: dict) -> dict:
        return {
            "id": str(row.get("id") or ""),
            "agent_name": row.get("agent_name"),
            "status": row.get("status"),
            "tool_count": int(row.get("tool_count") or 0),
            "failed_tool_count": int(row.get("failed_tool_count") or 0),
            "created_at": str(row.get("created_at") or ""),
            "completed_at": (
                str(row.get("completed_at")) if row.get("completed_at") else None
            ),
        }

    @staticmethod
    def _summarise_workflow_run(row: dict) -> dict:
        return {
            "id": str(row.get("id") or ""),
            "workflow_name": row.get("workflow_name"),
            "status": row.get("status"),
            "current_step": row.get("current_step"),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
        }

    @staticmethod
    def _agent_workflow_status(
        agent_runs: list[dict],
        workflow_runs: list[dict],
        failed_count: int,
    ) -> str:
        if not agent_runs and not workflow_runs:
            return "empty"
        return "attention" if failed_count else "ok"

    @staticmethod
    def _finance_ops_empty_states(read_only_findings: dict) -> list[dict]:
        messages = {
            "ar": "No open AR balance was found.",
            "ap": "No open AP balance was found.",
            "wip": "No unbilled WIP was found.",
            "action_queue": "No finance action queue items were found.",
            "agent_workflows": "No recent agent runs or workflows were found.",
        }
        return [
            {"domain": domain, "message": messages[domain]}
            for domain in messages
            if read_only_findings.get(domain, {}).get("status") == "empty"
        ]

    @staticmethod
    def _finance_ops_recommended_actions(
        *,
        ar_total: Decimal,
        ap_total: Decimal,
        wip_total: Decimal,
        close_status: dict,
    ) -> list[dict]:
        actions: list[dict] = []
        if ar_total > 0:
            actions.append(
                {
                    "domain": "ar",
                    "action": (
                        "Review overdue invoices and draft collections reminders "
                        "for Inbox approval."
                    ),
                    "requires_inbox_approval": True,
                    "suggested_agent": "collections_agent",
                    "suggested_tool": "send_email",
                    "risk_class": "write_money_in",
                    "review_path": "/app/inbox",
                }
            )
        if ap_total > 0:
            actions.append(
                {
                    "domain": "ap",
                    "action": (
                        "Prepare a controlled bill-pay proposal for approved bills "
                        "and route it to Inbox."
                    ),
                    "requires_inbox_approval": True,
                    "suggested_agent": "copilot_agent",
                    "suggested_tool": "propose_bill_payment_batch",
                    "risk_class": "write_money_out",
                    "review_path": "/app/inbox",
                }
            )
        if wip_total > 0:
            actions.append(
                {
                    "domain": "wip",
                    "action": (
                        "Draft customer invoices for billable WIP and route them "
                        "to Inbox before creation."
                    ),
                    "requires_inbox_approval": True,
                    "suggested_agent": "copilot_agent",
                    "suggested_tool": "draft_invoice",
                    "risk_class": "write_money_in",
                    "review_path": "/app/inbox",
                }
            )
        if close_status.get("status") == "blocked" or close_status.get("pending_reviews"):
            actions.append(
                {
                    "domain": "close",
                    "action": (
                        "Prepare or refresh the month-end close review package "
                        "before creating close tasks."
                    ),
                    "requires_inbox_approval": True,
                    "suggested_agent": "copilot_agent",
                    "suggested_tool": "prepare_month_end_close",
                    "risk_class": "accounting",
                    "review_path": "/app/inbox",
                }
            )
        return actions

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
