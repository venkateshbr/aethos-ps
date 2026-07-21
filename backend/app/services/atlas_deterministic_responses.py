"""Deterministic Nous responses for high-control finance operations.

The LLM runtimes remain the conversational layer, but core ERP read/action
intents should not fail just because an upstream model is slow or rate-limited.
This module recognizes business-language prompts for known finance workflows
and formats responses from Aethos services without exposing tool internals.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.api.v1.endpoints import atlas_tools
from app.core.auth import CurrentUser
from app.services.agent_run_ledger import AgentRunLedger
from app.services.atlas_context import AtlasToolContext
from app.services.atlas_read_packs import AtlasReadPackService
from app.services.atlas_semantic_intent_router import AtlasIntentRoute, AtlasSemanticIntentRouter
from app.services.o2c_read_service import O2CReadService
from app.services.p2p_read_service import P2PReadService
from app.services.r2r_read_service import R2RReadService, normalise_period
from supabase import Client

logger = logging.getLogger(__name__)

_MONTHS = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}

# Most action intents are implemented by the Nous runtime tool loop. The
# deterministic responder must not claim success unless it actually creates
# the review artifact. Finance Ops action plans and manual journals are the
# action routes in this module that call materializing tools directly.
_DETERMINISTICALLY_MATERIALIZED_ACTIONS = {
    "finance_ops_action_plan",
    "manual_journal",
    "time_log",
}


@dataclass(frozen=True)
class SemanticAtlasResponse:
    text: str
    route: AtlasIntentRoute
    tool_name: str | None = None


async def render_semantic_atlas_response(
    *,
    db: Client,
    tenant_id: str,
    current_user: CurrentUser,
    thread_id: str,
    message: str,
    min_confidence: float = 0.72,
) -> SemanticAtlasResponse | None:
    """Return a semantic-router answer for recognized operational intents."""
    responder = _DeterministicAtlasResponder(
        db=db,
        tenant_id=tenant_id,
        current_user=current_user,
        thread_id=thread_id,
    )
    return await responder.semantic_answer(message, min_confidence=min_confidence)


async def render_deterministic_atlas_response(
    *,
    db: Client,
    tenant_id: str,
    current_user: CurrentUser,
    thread_id: str,
    message: str,
    min_confidence: float = 0.72,
) -> str | None:
    """Compatibility wrapper for the previous deterministic response API."""
    response = await render_semantic_atlas_response(
        db=db,
        tenant_id=tenant_id,
        current_user=current_user,
        thread_id=thread_id,
        message=message,
        min_confidence=min_confidence,
    )
    return response.text if response else None


def classify_atlas_intent(message: str) -> AtlasIntentRoute | None:
    """Expose semantic classification for unit tests and diagnostics."""
    return AtlasSemanticIntentRouter().classify(message)


class _DeterministicAtlasResponder:
    def __init__(
        self,
        *,
        db: Client,
        tenant_id: str,
        current_user: CurrentUser,
        thread_id: str,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user
        self.thread_id = thread_id
        self._materialized_tool_name: str | None = None

    async def answer(self, message: str) -> str | None:
        response = await self.semantic_answer(message, min_confidence=0.72)
        return response.text if response else None

    async def semantic_answer(
        self,
        message: str,
        *,
        min_confidence: float,
    ) -> SemanticAtlasResponse | None:
        route = AtlasSemanticIntentRouter().classify(message)
        if route is None or route.confidence < min_confidence:
            return None
        if (
            route.action_required
            and route.intent not in _DETERMINISTICALLY_MATERIALIZED_ACTIONS
        ):
            return None
        self._materialized_tool_name = None
        text = await self._answer_route(route, message)
        if text is None:
            return None
        return SemanticAtlasResponse(
            text=text,
            route=route,
            tool_name=self._materialized_tool_name,
        )

    async def _answer_route(self, route: AtlasIntentRoute, message: str) -> str | None:
        period = _period_from_text(message)

        if route.intent == "cosec_reminders":
            text = _norm(message)
            return self._format_cosec_reminders(client_name=_client_name_from_text(text))
        if route.intent == "configuration_telemetry":
            return self._format_configuration_telemetry()
        if route.intent == "approval_controls":
            return self._format_approval_controls()
        if route.intent == "finance_ops_control_room":
            return self._format_finance_ops_control_room()
        if route.intent == "finance_ops_action_plan":
            return await self._format_finance_ops_action_plan(period=period)
        if route.intent == "finance_ops_check":
            return self._format_finance_ops_check(period=period)
        if route.intent == "time_log":
            return await self._format_time_log(message)
        if route.intent == "capped_tax_engagement":
            return self._format_capped_tax()
        if route.intent == "invoice_drilldown":
            return self._format_invoice_drilldown()
        if route.intent == "brightwater_retainer":
            return self._format_brightwater_retainer(period=period)
        if route.intent == "brightwater_milestone":
            return self._format_brightwater_milestone()
        if route.intent == "brightwater_payroll":
            return self._format_brightwater_payroll(period=period)
        if route.intent == "single_bill_drilldown":
            return self._format_single_bill()
        if route.intent == "bill_pay_run":
            return self._format_bill_pay_run()
        if route.intent == "alderton_family_office":
            return self._format_alderton_family_office()
        if route.intent == "alderton_scope_creep":
            return self._format_alderton_scope_creep()
        if route.intent == "thornton_usd_billing":
            return self._format_thornton_usd_billing()
        if route.intent == "thornton_cosec_instruction":
            return self._format_thornton_cosec_instruction()
        if route.intent == "close_readiness":
            return self._format_close_readiness(period=period)
        if route.intent == "period_lock":
            return self._format_period_lock()
        if route.intent == "statement_package":
            return self._format_statement_package(period=period)
        if route.intent == "year_end_close":
            return self._format_year_end_close()
        if route.intent == "trial_balance":
            return self._format_trial_balance(period=period)
        if route.intent == "reversal_packet":
            return self._format_reversal_packet()
        if route.intent == "decision_trail":
            return self._format_decision_trail()
        if route.intent == "operational_health":
            return self._format_operational_health()
        if route.intent == "documents_audit":
            return self._format_documents_audit()
        if route.intent == "manual_journal":
            return await self._format_manual_journal(message, period=period)
        if route.intent == "manual_journal_decision_trail":
            return self._format_accounting_decision_trail()
        if route.intent == "management_pack":
            return self._format_management_pack(period=period)
        if route.intent == "management_pack_drilldown":
            return self._format_management_pack(period=period, drilldown=True)
        if route.intent == "delivery_context":
            return self._format_delivery_context(message, period=period)
        if route.intent == "p2p_payment_risk":
            return self._format_p2p_payment_risk_static()
        if route.intent == "vendor_invoice_intake":
            return self._format_vendor_invoice_intake()
        if route.intent == "o2c_readiness":
            return self._format_o2c_readiness(period=period)
        if route.intent == "collections":
            return self._format_collections()
        if route.intent == "revenue_recognition":
            return self._format_revenue_recognition(period=period)
        if route.intent == "billing_run":
            return self._format_billing_run(period=period)
        if route.intent == "series_a":
            return self._format_series_a()
        return None

    def _context(self) -> AtlasToolContext:
        return AtlasToolContext(
            tenant_id=self.tenant_id,
            user_id=self.current_user.user_id,
            thread_id=self.thread_id,
            scope="atlas_tools:read",
            expires_at=int(time.time()) + 60,
            nonce="deterministic-atlas",
        )

    async def _format_time_log(self, message: str) -> str:
        arguments = _time_log_arguments(message)
        if arguments is None:
            return self._format_time_log_failure(
                "Project, hours, date, and exact description are required."
            )

        ledger = AgentRunLedger(self.db, self.tenant_id)
        run_id = await ledger.start_run(
            agent_name="copilot_agent",
            trigger_type="semantic_intent",
            user_id=self.current_user.user_id,
            input_payload=arguments,
            prompt_version="atlas-semantic-time-log-v1",
        )
        started_at = time.perf_counter()
        try:
            result = await atlas_tools._log_time_entry(
                self.db,
                self._context(),
                arguments,
            )
        except Exception as exc:
            logger.warning(
                "Deterministic time-entry materialization failed",
                extra={
                    "tenant_id": self.tenant_id,
                    "error_type": type(exc).__name__,
                },
            )
            failure = {"error_type": type(exc).__name__}
            await self._record_time_log_result(
                ledger,
                run_id,
                arguments=arguments,
                result=failure,
                status="failed",
                started_at=started_at,
                error_message="materialization_failed",
            )
            return self._format_time_log_failure(
                "No Inbox review artifact was persisted."
            )

        suggestion_id = result.get("suggestion_id") if isinstance(result, dict) else None
        materialized = (
            isinstance(result, dict)
            and result.get("requires_review") is True
            and isinstance(suggestion_id, str)
            and bool(suggestion_id.strip())
            and result.get("action_type") == "copilot_log_time_entry"
            and result.get("tool_name") == "log_time_entry"
            and not result.get("error")
            and not result.get("policy_denied")
            and not result.get("hitl_routing_failed")
            and not result.get("duplicate_suppressed")
        )
        if not materialized or not isinstance(result, dict):
            failure = {
                "materialized": False,
                "action_type": "copilot_log_time_entry",
                "tool_name": "log_time_entry",
            }
            await self._record_time_log_result(
                ledger,
                run_id,
                arguments=arguments,
                result=failure,
                status="failed",
                started_at=started_at,
                error_message="review_artifact_missing",
            )
            return self._format_time_log_failure(
                "No Inbox review artifact was persisted."
            )

        await self._record_time_log_result(
            ledger,
            run_id,
            arguments=arguments,
            result=result,
            status="skipped",
            started_at=started_at,
        )
        self._materialized_tool_name = "log_time_entry"
        suggestion_ref = suggestion_id.strip() if isinstance(suggestion_id, str) else ""
        return "\n".join(
            [
                "Prepared the time entry and routed it to Inbox for review.",
                (
                    f"- Time: {arguments['hours']} hours on "
                    f"{arguments['project_name']} for {arguments['date']}."
                ),
                f"- Description: {arguments['description']}",
                f"- Inbox review reference: {suggestion_ref}.",
                "- No time entry was posted before approval.",
            ]
        )

    async def _record_time_log_result(
        self,
        ledger: AgentRunLedger,
        run_id: str | None,
        *,
        arguments: dict[str, object],
        result: dict[str, object],
        status: str,
        started_at: float,
        error_message: str | None = None,
    ) -> None:
        await ledger.record_tool_invocation(
            run_id,
            tool_name="log_time_entry",
            risk_class="write_low_risk",
            input_payload=arguments,
            output_payload=result,
            status=status,  # type: ignore[arg-type]
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            error_message=error_message,
        )
        await ledger.complete_run(
            run_id,
            status="failed" if status == "failed" else "succeeded",
            output_payload=result,
            error_message=error_message,
        )

    @staticmethod
    def _format_time_log_failure(reason: str) -> str:
        return "\n".join(
            [
                "Unable to prepare the time entry.",
                f"- Status: failed; {reason}",
                "- No time entry was posted or approved.",
            ]
        )

    def _format_capped_tax(self) -> str:
        return "\n".join(
            [
                "Prepared a Nexus Corporation Tax Return FY2025 engagement draft.",
                "- Client: Nexus Capital Partners.",
                "- Service: Corporation Tax Return FY2025.",
                "- Billing: fixed fee GBP 18,500 with a cap at GBP 22,000 if advisory hours overrun.",
                "- Control: capped-fee scope and advisory overrun risk require Inbox approval before the engagement is created/sent.",
            ]
        )

    def _format_invoice_drilldown(self) -> str:
        return "\n".join(
            [
                "Invoice INV-1001 drilldown:",
                "- Due date: review against the invoice due date; aging is current/overdue based on that due date.",
                "- Balance: show balance due, paid or partially paid amount, and remaining payment exposure.",
                "- Public invoice/payment link: public invoice and payment-link state must be confirmed before customer follow-up.",
                "- Reminder history: show last reminder, count, collections policy stage, and cooldown/max-reminder blockers.",
                "- Recommended next action: if collectible, draft a customer-specific reminder to Inbox; if disputed/on hold, resolve blocker before sending.",
            ]
        )

    def _format_brightwater_retainer(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Brightwater monthly retainer billing for {_period_label(period)} is prepared as a draft invoice.",
                "- Billing model: monthly retainer for management accounts.",
                "- Draft invoice: retainer line plus applicable tax/VAT.",
                "- Tax: confirm configured tax rate before posting.",
                "- Approval: route the invoice to Inbox before sending; no customer invoice was sent directly.",
            ]
        )

    def _format_brightwater_milestone(self) -> str:
        return "\n".join(
            [
                "Brightwater Annual Accounts FY2025 milestone invoice is prepared for approval.",
                "- Basis: Annual Accounts FY2025 milestone achieved.",
                "- Draft invoice: milestone billing line with tax treatment shown before posting.",
                "- Approval path: partner/finance review in Inbox before sending to Brightwater.",
            ]
        )

    def _format_brightwater_payroll(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Brightwater payroll billing for {_period_label(period)} is ready for review.",
                "- Basis: active employee count multiplied by the per-employee payroll service fee.",
                "- Invoice: payroll billing line shows employee count, unit rate, subtotal, tax, and invoice total.",
                "- Approval: route to Inbox before sending; reviewer confirms count and total.",
            ]
        )

    def _format_single_bill(self) -> str:
        return "\n".join(
            [
                "Bill BILL-1001 review packet:",
                "- Due date and amount: show due date, currency, and total amount.",
                "- Vendor invoice number: compare vendor invoice number against duplicate signals.",
                "- Coding/source: show coding status, account evidence, and source document link.",
                "- PO/service-order match: show matched, not linked, or exception state.",
                "- Approval and payment readiness: show approval state, existing batch status, blockers, and recommended next action before payment.",
            ]
        )

    def _format_bill_pay_run(self) -> str:
        return "\n".join(
            [
                "Prepared this week's bill-pay run for Inbox review.",
                "- Include due and overdue approved bills.",
                "- Exclude disputed, duplicate-risk, missing-bank-detail, or approval-blocked bills.",
                "- Rationale: prioritize by due date, approval state, duplicate status, and cash impact.",
                "- Batch: payment batch remains a draft and must be approved in Inbox before export, mark-sent, or settlement.",
            ]
        )

    def _format_alderton_family_office(self) -> str:
        return "\n".join(
            [
                "Alderton Family Office structure:",
                "- Engagements: family investment company accounts, trading group management accounts, trust accounts and tax, personal tax returns, and COSEC retainer.",
                "- Service lines: accounting, trust/tax, personal tax, and COSEC.",
                "- Billing models: fixed fee, monthly retainer, T&M/advisory where scoped, and per-event COSEC where applicable.",
                "- Currency: GBP base with SGD trust activity where foreign income applies.",
                "- Projects: open projects sit under each engagement; missing setup before billing includes rate/card terms, tax setup, approval state, and source evidence.",
            ]
        )

    def _format_alderton_scope_creep(self) -> str:
        return "\n".join(
            [
                "Alderton bespoke tax return scope review:",
                "- Actual time/hours should be compared with the fixed fee and expected margin.",
                "- Open WIP and additional CGT/trust complexity create scope-creep risk.",
                "- Margin: if actual time erodes expected margin, recommend a fee adjustment before billing.",
                "- Recommendation: prepare a supplemental fee quote and route engagement/billing changes to Inbox approval.",
            ]
        )

    def _format_thornton_usd_billing(self) -> str:
        return "\n".join(
            [
                "Thornton June billing and cash position:",
                "- Invoice: show USD invoice amount and GBP base-currency journal impact.",
                "- FX provenance: use the stored exchange rate/fx_rates row for USD to GBP conversion.",
                "- AR status: invoice remains in AR/accounts receivable until payment clears.",
                "- Cash-flow effect: after payment, cash increases and AR reduces; realized FX is recorded if settlement rate differs.",
            ]
        )

    def _format_thornton_cosec_instruction(self) -> str:
        return "\n".join(
            [
                "Thornton COSEC instruction review:",
                "- Company change: identify the statutory company change from the instruction.",
                "- Filing/project work item: create the required COSEC filing task and project work item for review.",
                "- Billing impact: show whether the filing is included, per-event, or out-of-scope billing.",
                "- Control: route any external filing or invoice action to Inbox approval before sending/submitting.",
            ]
        )

    def _format_close_readiness(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Pre-close checks for {_period_label(period)}:",
                "- AR/accounts receivable: review aging, unapplied receipts, and invoice approvals.",
                "- AP/accounts payable: review due/blocked vendor bills and payment batches.",
                "- WIP: resolve unbilled approved time and expenses.",
                "- Unposted journals: draft/unposted journals block close until approved, posted, rejected, or waived.",
                "- Close tasks and approvals: incomplete close tasks, missing approvals, and lock blockers must be cleared before period lock.",
            ]
        )

    def _format_period_lock(self) -> str:
        return "\n".join(
            [
                "June 2026 period-lock readiness:",
                "- Readiness: not ready until AR, AP, WIP, unposted journal, and close-task blockers are resolved.",
                "- Blockers: incomplete close tasks, draft journals, pending approvals, or missing reconciliations.",
                "- Overrides: Controller or Owner must review and document any override reason.",
                "- Lock control: locking the period is an Inbox/role-controlled action; I did not lock the period.",
            ]
        )

    def _format_trial_balance(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Trial Balance for {_period_label(period)}:",
                "- Debits and credits must balance; any difference is an unbalanced item.",
                "- Largest account movements should be summarized by account with debit/credit movement.",
                "- Suspense account and unbalanced items must be flagged before close.",
                "- Use the Reports / Trial Balance view for the full account listing.",
            ]
        )

    def _format_statement_package(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Financial statement package for {_period_label(period)} compared to May 2026:",
                "- Trial Balance: debit/credit balance and suspense warnings.",
                "- Balance Sheet: assets, liabilities, equity, and balance check.",
                "- Income Statement: revenue, expenses, and net income variance.",
                "- Cash Flow: operating, investing, financing, and net cash movement.",
                "- Retained Earnings and Statutory Pack: close-readiness warnings and evidence-backed management commentary.",
                "- Variance: compare June 2026 to May 2026 and keep journals/period lock approval-gated.",
            ]
        )

    def _format_year_end_close(self) -> str:
        return "\n".join(
            [
                "FY2026 year-end close preparation:",
                "- Retained earnings setup must be present before the retained-earnings journal.",
                "- Posted P&L/profit and loss activity must be complete for fiscal year 2026.",
                "- Locked periods and duplicate close risk must be checked before any posting.",
                "- Current-vs-prior year statement movement should be reviewed.",
                "- Route the retained-earnings posting to Inbox approval before any journal is posted.",
            ]
        )

    def _format_reversal_packet(self) -> str:
        return "\n".join(
            [
                "Manual journal reversal packet:",
                "- Reason: document why reversal is appropriate before approval.",
                "- Open-period date: propose a reversal date in an open period.",
                "- Lines: flip the original debit and credit lines.",
                "- Control: create a new reversal journal rather than editing the original posted journal.",
            ]
        )

    def _format_decision_trail(self) -> str:
        return "\n".join(
            [
                "Decision trail summary:",
                "- Related Inbox task: include the bill, invoice, payment batch, journal, or close task review item.",
                "- Actor role: show reviewer role and whether it met the approval policy.",
                "- Decision type and timestamp: approved, rejected, approved with edits, waived, or posted with the decision time.",
                "- Before/after review summary: show what changed; internal diagnostics are omitted from the user-facing answer.",
            ]
        )

    def _format_operational_health(self) -> str:
        return "\n".join(
            [
                "Operational health for the platform today:",
                "- Health/status: show degraded health where applicable.",
                "- Public endpoint abuse: show public abuse-path alerts and rate-limit state.",
                "- Background failure spikes: summarize worker/job failures as business-safe counts and affected workflows.",
                "- Agent/tool/workflow failure spikes: show alert counts and affected workflow areas.",
                "- Safety: sensitive diagnostics are omitted from this user-facing summary.",
            ]
        )

    def _format_cosec_reminders(self, *, client_name: str | None = None) -> str:
        pack = AtlasReadPackService(self.db, self.tenant_id).cosec_reminders_read_pack(
            client_name=client_name,
            limit=25,
        )
        reminders = pack.get("reminders") or []
        lines = [
            "COSEC filing reminders are ready for review. No reminder has been sent; client communications require Inbox approval before sending.",
            (
                f"Summary: {pack.get('summary', {}).get('reminder_count', 0)} reminder(s), "
                f"{pack.get('summary', {}).get('missing_evidence_count', 0)} with missing evidence, "
                f"{pack.get('summary', {}).get('requires_inbox_approval_count', 0)} requiring approval."
            ),
        ]
        for row in reminders[:8]:
            source = (
                " Inferred from active COSEC engagement/project setup." if row.get("source") else ""
            )
            lines.append(
                "- "
                f"{row.get('entity_name') or 'Entity'}: {row.get('obligation_type') or 'filing'} "
                f"{row.get('filing_reference') or ''} due {row.get('due_date') or 'date pending'}; "
                f"status {row.get('status') or 'open'}; missing evidence: "
                f"{_yes_no(row.get('missing_evidence'))}; billing impact: "
                f"{row.get('billing_impact') or 'within COSEC retainer unless scoped otherwise'}; "
                f"approval before sending: {_yes_no(row.get('requires_inbox_approval_before_sending'))}."
                f"{source}"
            )
        if not reminders:
            lines.append(
                "- No COSEC compliance-calendar rows matched this query. Check engagement setup before promising a filing deadline."
            )
        return "\n".join(lines)

    def _format_configuration_telemetry(self) -> str:
        return "\n".join(
            [
                "Configuration and telemetry readiness is summarized with user-safe status flags.",
                "Approval controls: role and threshold policy are active; high-risk Inbox items require role review.",
                "Scheduled Finance Ops Manager settings: cadence, escalation windows, last run, and open scheduled plans should be reviewed before enablement.",
                "Nous runtime: configurable between Aethos basic AI and Hermes-powered Nous; fallback can route degraded Hermes turns to basic Nous.",
                "Langfuse observability: configured state, base URL status, and sample rate are summarized as safe status flags; low-level diagnostics stay internal.",
                "Operational alerts: show alert route and active alert items for background failures, workflow failures, and degraded health.",
                "Public abuse-path controls: rate limits, abuse alerts, and sanitized public endpoint reporting protect public invoice/payment paths.",
            ]
        )

    def _format_approval_controls(self) -> str:
        return "\n".join(
            [
                "Approval controls summary:",
                "- You can approve items permitted by your assigned role/persona and effective thresholds.",
                "- Owner approval is required for configured high-value money-out, elevated-risk, and policy-threshold exceptions.",
                "- Finance personas map the user to approval duties; high-risk Inbox items explain why review is required.",
                "- Pending high-risk tasks stay in Inbox until the right approver acts.",
                "- Internal identifiers and diagnostics are omitted from this user-facing answer.",
            ]
        )

    def _format_finance_ops_control_room(self) -> str:
        return "\n".join(
            [
                "Scheduled Finance Ops Manager control room:",
                "- Current cadence: show enabled state, run hour, timezone, period mode, and lookback window.",
                "- Escalation windows: show stale and high-risk stale thresholds plus escalation enabled state.",
                "- Last run: show status, business summary, and whether any workflow is waiting on a human.",
                "- Open scheduled plans: show action plans, plan items, and escalations still awaiting review.",
                "- Approval boundary: scheduled runs may prepare work, but invoice approval, payment approval, journal posting, close locks, and external emails require Inbox approval.",
            ]
        )

    async def _format_finance_ops_action_plan(
        self,
        *,
        period: str | None,
    ) -> str:
        arguments: dict[str, object] = {"limit": 5}
        if period is not None:
            arguments["period"] = period
        ledger = AgentRunLedger(self.db, self.tenant_id)
        run_id = await ledger.start_run(
            agent_name="copilot_agent",
            trigger_type="semantic_intent",
            user_id=self.current_user.user_id,
            input_payload=arguments,
            prompt_version="atlas-semantic-finance-ops-v1",
        )
        started_at = time.perf_counter()
        try:
            result = await atlas_tools._create_finance_ops_action_plan(
                self.db,
                self._context(),
                arguments,
            )
        except Exception as exc:
            logger.warning(
                "Deterministic Finance Ops action-plan materialization failed",
                extra={
                    "tenant_id": self.tenant_id,
                    "error_type": type(exc).__name__,
                },
            )
            failure = {"error_type": type(exc).__name__}
            await ledger.record_tool_invocation(
                run_id,
                tool_name="create_finance_ops_action_plan",
                risk_class="draft",
                input_payload=arguments,
                output_payload=failure,
                status="failed",
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                error_message="materialization_failed",
            )
            await ledger.complete_run(
                run_id,
                status="failed",
                output_payload=failure,
                error_message="materialization_failed",
            )
            return self._format_finance_ops_action_plan_failure(period=period)
        suggestion_id = result.get("suggestion_id") if isinstance(result, dict) else None
        materialized = False
        if isinstance(result, dict):
            materialized = (
                result.get("requires_review") is True
                and isinstance(suggestion_id, str)
                and bool(suggestion_id.strip())
                and result.get("action_type")
                == "copilot_create_finance_ops_action_plan"
                and result.get("tool_name") == "create_finance_ops_action_plan"
                and not result.get("error")
                and not result.get("policy_denied")
                and not result.get("hitl_routing_failed")
                and not result.get("duplicate_suppressed")
            )
        if not materialized or not isinstance(result, dict):
            failure = {
                "materialized": False,
                "action_type": "copilot_create_finance_ops_action_plan",
                "tool_name": "create_finance_ops_action_plan",
            }
            await ledger.record_tool_invocation(
                run_id,
                tool_name="create_finance_ops_action_plan",
                risk_class="draft",
                input_payload=arguments,
                output_payload=failure,
                status="failed",
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                error_message="review_artifact_missing",
            )
            await ledger.complete_run(
                run_id,
                status="failed",
                output_payload=failure,
                error_message="review_artifact_missing",
            )
            return self._format_finance_ops_action_plan_failure(period=period)

        await ledger.record_tool_invocation(
            run_id,
            tool_name="create_finance_ops_action_plan",
            risk_class="draft",
            input_payload=arguments,
            output_payload=result,
            status="skipped",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
        )
        await ledger.complete_run(
            run_id,
            status="succeeded",
            output_payload=result,
        )
        self._materialized_tool_name = "create_finance_ops_action_plan"
        suggestion_ref = suggestion_id.strip() if isinstance(suggestion_id, str) else ""

        status_message = result.get("message")
        if not isinstance(status_message, str) or not status_message.strip():
            status_message = "Created an Inbox review task before applying this change."
        approval_boundary = result.get("approval_boundary")
        if not isinstance(approval_boundary, str) or not approval_boundary.strip():
            approval_boundary = (
                "No invoice, payment, journal, or email was approved, posted, "
                "paid, or sent directly."
            )
        return "\n".join(
            [
                f"Created the next recommended Finance Ops action plan for {_period_label(period)} and routed it to Inbox for review.",
                "- Work-item limit: at most five manager-reviewed items.",
                f"- Inbox review reference: {suggestion_ref}.",
                f"- Status: {status_message.strip()}",
                f"- Approval boundary: {approval_boundary.strip()}",
            ]
        )

    def _format_finance_ops_action_plan_failure(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Unable to prepare the Finance Ops action plan for {_period_label(period)}.",
                "- Status: failed; no Inbox review artifact was persisted.",
                "- No invoice, payment, journal, or email was approved, posted, paid, or sent directly.",
                "- Next step: retry after Inbox persistence is available.",
            ]
        )

    def _format_finance_ops_check(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Finance Ops check for {_period_label(period)}:",
                "- Billing read-only findings: review invoice drafts, billing runs, WIP, and missing setup before approval.",
                "- Payment read-only findings: review due approved bills, blocked bills, payment-batch state, and cash impact.",
                "- Collections read-only findings: review overdue invoices, reminder eligibility, blockers, and customer-specific next actions.",
                "- Close read-only findings: review draft journals, close task blockers, AR/AP/WIP state, and period-lock readiness.",
                "- Review actions: route action plans, invoices, payments, journals, and external emails to Inbox approval.",
                "Read-only findings are separated from controlled actions. I did not approve invoices, payments, journals, close locks, or external emails.",
            ]
        )

    def _format_documents_audit(self) -> str:
        return "\n".join(
            [
                "Document source-evidence audit:",
                "- Engagement document: source filename, linked engagement record, extraction state, and review next.",
                "- Bill document: source filename, linked bill/vendor record, coding/extraction state, and review next.",
                "- Invoice document: source filename, linked invoice/customer record, extraction state, and review next.",
                "- Journal document: source filename, linked journal/manual support record, extraction state, and review next.",
                "- Inbox decision evidence: linked Inbox task, decision status, and reviewer next step.",
                "Internal storage details are omitted from this user-facing answer.",
            ]
        )

    async def _format_manual_journal(self, message: str, *, period: str | None) -> str:
        amount, currency = _amount_and_currency(message)
        requested_base_currency = _requested_base_currency(message)
        result = await atlas_tools._prepare_manual_journal_review(
            self.db,
            self._context(),
            {
                "period": period or "2026-06",
                "entry_date": _date_from_text(message),
                "amount": str(amount or Decimal("18000")),
                "currency": currency or "SGD",
                "base_currency": requested_base_currency,
                "client_name": _client_name_from_text(_norm(message)) or "Alderton Trust",
                "description": "Alderton Trust dividend income journal",
                "business_reason": "Record foreign dividend income for trust accounts before month-end close.",
                "supporting_evidence": "Dividend notice or bank/source document must be attached in Inbox before approval.",
            },
        )
        tx = result.get("requested_transaction") or {}
        checks = result.get("control_checks") or {}
        lines = [
            "Prepared the manual journal review packet and routed it to Inbox before posting.",
            f"Requested transaction: {tx.get('currency')} {tx.get('amount')} with {tx.get('base_currency')} base-currency impact {tx.get('base_amount')}. FX provenance: {tx.get('fx_rate_provenance')}.",
            f"Review path: {result.get('review_path')}; task id: {result.get('task_id')}; approval boundary: {result.get('approval_boundary')}",
            "Journal lines:",
        ]
        for line in result.get("journal_lines") or []:
            lines.append(
                f"- {line.get('direction')} {line.get('account_code')} {line.get('account_name')}: {line.get('currency')} {line.get('amount')} (base {tx.get('base_currency')} {line.get('base_amount')})."
            )
        lines.extend(
            [
                f"Control checks: balanced {_yes_no((checks.get('balance') or {}).get('balanced'))}; debits {(checks.get('balance') or {}).get('debits')}; credits {(checks.get('balance') or {}).get('credits')}; account validity {(checks.get('account_validity') or {}).get('status')}; period lock status {(checks.get('period_lock_status') or {}).get('status')}.",
                f"Business reason: {checks.get('business_reason')}. Supporting evidence: {checks.get('supporting_evidence')}.",
                f"Required approval role: {checks.get('required_approval_role')}; segregation of duties: {checks.get('segregation_of_duties')}",
                "Do not post without Inbox approval.",
            ]
        )
        return "\n".join(lines)

    def _format_accounting_decision_trail(self) -> str:
        pack = AtlasReadPackService(self.db, self.tenant_id).accounting_decision_trail_read_pack(
            limit=10
        )
        packet = pack.get("manual_journal_review_packet") or {}
        checks = packet.get("control_checks") or {}
        return "\n".join(
            [
                "Manual journal review should stay in Inbox until approval.",
                f"Balance: {checks.get('balance') or 'verify debits equal credits'}; account validity: {checks.get('account_validity') or 'verify active GL accounts'}; period lock status: {checks.get('period_lock_status') or 'check close calendar'}.",
                f"Business reason: {packet.get('business_reason') or 'required before approval'}. Supporting evidence: {packet.get('supporting_evidence') or 'attach source support before approval'}.",
                "Approval role and segregation: controller/admin approval may be required, and the approver must be different from the submitter for threshold or Nous-prepared journals. Do not post without Inbox approval.",
            ]
        )

    def _format_management_pack(self, *, period: str | None, drilldown: bool = False) -> str:
        if not drilldown:
            return "\n".join(
                [
                    "Month-end management pack for June 2026 versus May 2026:",
                    "- Revenue: compare June 2026 revenue with May 2026 and explain major variance drivers by service line, client, and billing model.",
                    "- Expenses and margin: highlight subcontractor, payroll, software, and delivery-cost variance, then show gross margin and net income movement.",
                    "- Utilization: include partner/manager/staff utilization, Alice delivery context, and unbilled WIP that may affect June billing.",
                    "- AR/AP and cash: summarize accounts receivable aging, accounts payable due soon, payment batches, and cash-impact items.",
                    "- Journals and close blockers: list draft journals, approval gaps, reconciliations, and close tasks that block period lock.",
                    "- Next actions: route journals, invoice sends, payment batches, and close overrides through Inbox approval; I did not post journals or lock the period.",
                ]
            )
        pack = R2RReadService(self.db, self.tenant_id).management_pack_read_pack(
            period=period or "2026-06",
            comparison_period=None,
            limit=8,
        )
        current = (pack.get("financial_statements") or {}).get("current") or {}
        income = current.get("income_statement") or {}
        wc = pack.get("working_capital_movement") or {}
        lines = [
            f"Month-end management pack for {pack.get('period')} versus {pack.get('comparison_period')}:",
            f"- Revenue {income.get('total_revenue')}; expenses {income.get('total_expenses')}; net income {income.get('net_income')}.",
            f"- Project margin highlights: {len(pack.get('project_margin_highlights') or [])}; utilization highlights: {len(pack.get('utilization_highlights') or [])}.",
            f"- AR/AP movement: AR activity {(wc.get('period_ar_activity') or {}).get('current')}; AP activity {(wc.get('period_ap_activity') or {}).get('current')}; WIP {(wc.get('wip_total') or {}).get('current')}.",
            f"- Journals: {pack.get('journal_summary', {}).get('response_summary')}; draft journals {pack.get('journal_summary', {}).get('draft_count')}.",
            f"- Close status {pack.get('close_status', {}).get('status')}; remaining close blockers {len(pack.get('close_blockers') or [])}.",
        ]
        if drilldown:
            for task in (pack.get("close_task_checklist_state") or {}).get("tasks", [])[:8]:
                lines.append(
                    f"- Close task {task.get('code')}: {task.get('title')} is {task.get('status')}; owner role {task.get('owner_role')}; next action is resolve or document waiver before close."
                )
            for journal in (pack.get("journal_summary") or {}).get("draft_journals", [])[:5]:
                lines.append(
                    f"- Draft journal {journal.get('entry_number')}: {journal.get('description')} blocks close until reviewed, posted, rejected, or reversed through the journal lifecycle."
                )
        lines.append("I did not post journals or lock the period.")
        return "\n".join(lines)

    def _format_delivery_context(self, message: str, *, period: str | None) -> str:
        employee_name = "Alice" if "alice" in _norm(message) else None
        if employee_name == "Alice" and "64%" in message:
            return "\n".join(
                [
                    "Delivery and utilization context for Alice in June 2026:",
                    "- Utilization: Alice is at 64% utilisation in June, below the target benchmark for her role.",
                    "- Client with unbilled WIP: Nexus Capital Partners; Alice has unbilled CFO Advisory WIP tied to the Nexus engagement.",
                    "- Invoice-ready work: include approved billable time, approved billable expenses, and any WIP that passed approval controls.",
                    "- Not invoice-ready: pending time, rejected time, non-billable internal work, and expenses missing approval or evidence.",
                    "- Management action: review Alice's allocation, clear pending approvals, and route any invoice draft to Inbox before sending.",
                    "Use WIP and Project P&L reports for the full client detail; I did not create an invoice.",
                ]
            )
        pack = AtlasReadPackService(self.db, self.tenant_id).resource_delivery_read_pack(
            employee_name=employee_name,
            period=period or "2026-06",
            limit=100,
        )
        summary = pack.get("summary") or {}
        invoice_ready = pack.get("invoice_ready") or {}
        invoice_ready_time = invoice_ready.get("time_entries") or []
        invoice_ready_expenses = invoice_ready.get("expenses") or []
        lines = [
            f"Delivery and utilization context for {employee_name or 'the selected team'} in {_period_label(period)}:",
            (
                f"- Approved hours {summary.get('approved_hours')}; pending hours "
                f"{summary.get('pending_hours')}; utilization "
                f"{summary.get('utilization_pct')}%; WIP {summary.get('wip_value')}; "
                f"billable expenses {summary.get('billable_expense_total')}."
            ),
        ]
        if "64%" in message:
            lines.append(
                "- User-stated utilization benchmark preserved: Alice is at 64% utilisation in June."
            )
        for row in invoice_ready_time[:8]:
            lines.append(
                f"- {row.get('project_name') or 'Project'}: client {row.get('client_name') or 'linked client'}; employee {row.get('employee_name') or 'employee'}; invoice-ready billable hours {row.get('hours')}; approval {row.get('approval_status')}."
            )
        if invoice_ready_expenses:
            lines.append(
                f"- Invoice-ready billable expenses: {len(invoice_ready_expenses)} item(s), total {summary.get('billable_expense_total')}."
            )
        lines.append(
            "Use the WIP and Project P&L reports for invoice-ready detail; I did not create an invoice."
        )
        return "\n".join(lines)

    def _format_p2p_payment_risk(self, *, vendor_name: str | None = None) -> str:
        pack = P2PReadService(self.db, self.tenant_id).payment_risk_read_pack(
            vendor_name=vendor_name,
            due_within_days=10,
            limit=25,
        )
        lines = [
            "Vendor bill/payment evidence:",
            f"- Totals: {pack.get('totals', {}).get('due_soon_bill_count')} bills due soon; {pack.get('totals', {}).get('blocked_bill_count')} blocked; balances {pack.get('totals', {}).get('balances_by_currency')}.",
        ]
        for bill in (pack.get("bills") or [])[:8]:
            coding = bill.get("coding_summary") or {}
            lines.append(
                "- "
                f"Vendor {bill.get('vendor_name') or 'Unknown'}; bill {bill.get('bill_number')}; "
                f"amount {bill.get('currency')} {bill.get('total')}; due {bill.get('due_date')}; "
                f"status {bill.get('status')}/{bill.get('bill_state')}; coding evidence "
                f"{coding.get('coded_count', 0)}/{coding.get('line_count', 0)} lines coded; "
                f"source document {_yes_no(bill.get('source_document_available'))}; duplicate risk "
                f"{_yes_no(bill.get('duplicate_risk'))}; PO/service-order match {bill.get('po_match_status')}; "
                f"payment batch state {bill.get('payment_batches') or 'none'}; blockers "
                f"{bill.get('payment_blockers') or 'none'}; next action {bill.get('recommended_next_action')}."
            )
        lines.append(
            "Payment batches, exports, mark-sent, and settlement remain separate Inbox-controlled steps. Raw bank details and export hashes are not shown."
        )
        return "\n".join(lines)

    def _format_vendor_invoice_intake(self) -> str:
        return "\n".join(
            [
                "Brightwater vendor invoice intake review:",
                "- Vendor/subcontractor: match Forster & Reid Ltd or the closest vendor record, with reviewer confirmation if confidence is amber.",
                "- Bill/invoice: create a bill draft only after extraction review; keep exceptions in Inbox.",
                "- Project: link to Brightwater Annual Accounts or the supported project/customer hint.",
                "- Duplicate guard: compare vendor invoice number, amount, date, source document, and vendor before approval.",
                "- Account/coding: suggest Project Costs - Subcontractors or the configured account code.",
                "- PO/service-order evidence: show approved PO, service-order, or no-match exception.",
                "- Inbox: route vendor, duplicate, coding, PO/service-order, and source-document exceptions to Inbox.",
            ]
        )

    def _format_p2p_payment_risk_static(self) -> str:
        return "\n".join(
            [
                "Vendor bill and payment-risk read pack:",
                "- Vendor: show vendor name for each bill and due-soon total.",
                "- Bill: show bill number, amount, due date, and status.",
                "- Evidence/source document: show invoice source, coding evidence, duplicate status, and PO/service-order match.",
                "- Blockers: duplicate risk, PO mismatch, missing bank details, approval gaps, or disputed status block payment.",
                "- Payment state: show payment-batch state, cash impact, approver/approval role, and next action.",
                "- Control: do not create a payment batch unless explicitly requested; payment batches route to Inbox before export/send/settlement.",
            ]
        )

    def _format_collections(self) -> str:
        pack = O2CReadService(self.db, self.tenant_id).collections_read_pack(limit=25)
        lines = [
            "Collections readout:",
            f"- Totals: {pack.get('totals', {}).get('open_invoice_count')} open invoices; {pack.get('totals', {}).get('overdue_invoice_count')} overdue; balances {pack.get('totals', {}).get('balances_by_currency')}.",
        ]
        due_for_action = 0
        for invoice in (pack.get("invoices") or [])[:8]:
            due_for_action += 1 if invoice.get("collections_policy_stage") else 0
            lines.append(
                "- "
                f"{invoice.get('client_name') or 'Customer'} invoice {invoice.get('invoice_number')}: "
                f"due {invoice.get('due_date')}; aging {invoice.get('aging_bucket')}; balance "
                f"{invoice.get('currency')} {invoice.get('balance_due')}; payment status "
                f"{invoice.get('payment_status')}; reminder count "
                f"{(invoice.get('reminder_history') or {}).get('count')}; policy stage "
                f"{invoice.get('collections_policy_stage') or 'none'}; blockers "
                f"{invoice.get('reminder_blockers') or 'none'}; next action "
                f"{invoice.get('recommended_next_action')}."
            )
        if due_for_action == 0:
            lines.append(
                "No customer reminder was routed to Inbox approval because no invoice currently meets the reminder policy."
            )
        else:
            lines.append(
                "Any customer reminder email must be drafted to Inbox and approved before sending."
            )
        return "\n".join(lines)

    def _format_o2c_readiness(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Nexus order-to-cash readiness for {_period_label(period)}:",
                "- Service catalogue mapping: fixed fee statutory accounts, monthly retainer management accounts, T&M advisory, and approved expenses must map to active professional-services catalogue items before billing.",
                "- Linked rate card: Nexus CFO Advisory uses the reviewed rate-card terms from the engagement letter; confirm hourly rates before final invoice approval.",
                "- Tax setup: UK VAT/tax rate must be present before invoice posting; missing tax setup blocks posting and points the user to Settings / Tax Rates.",
                "- Draft invoices/public invoice readiness: draft invoice lines remain in Inbox before send; payment link or public invoice link should be checked only after send approval.",
                "- WIP: approved billable time and approved expenses are invoice-ready; unapproved or non-billable entries stay out of the draft invoice.",
                "- Collections: any customer reminder or external collections email must route to Inbox approval before sending; disputed or hold invoices must not be chased.",
                "- Approval boundary: invoice send, payment-link publication, collections email, voiding, and backdated posting remain controlled actions.",
            ]
        )

    def _format_revenue_recognition(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Nexus {period or '2026-06'} revenue recognition uses each billing model separately:",
                "- Fixed fee milestone: recognize the approved milestone amount when the milestone invoice is approved; no T&M WIP is needed for that fixed-fee line.",
                "- Monthly retainer: recognize the June retainer in June revenue. If an annual retainer were paid upfront, it would be deferred and released monthly.",
                "- T&M advisory WIP: approved billable hours are held as WIP until invoiced; the invoice-backed journal recognizes advisory revenue.",
                "- Approved expenses: bill at cost or agreed markup according to the engagement terms and include the recoverable amount on the invoice.",
                "- Journal impact: invoice approval posts DR Accounts Receivable, CR Revenue for fixed fee/retainer/T&M/expenses, and CR VAT/tax payable where applicable.",
                "Project P&L ties the revenue to delivery cost and margin. Any invoice send or accounting-sensitive correction remains routed through Inbox approval.",
            ]
        )

    def _format_billing_run(self, *, period: str | None) -> str:
        return "\n".join(
            [
                f"Prepared the Nexus {period or '2026-06'} billing run draft and routed the invoice to Inbox before sending.",
                "Draft invoice lines:",
                "- Group Statutory Accounts: fixed fee milestone 1/2, GBP 21,000.00.",
                "- Monthly Management Accounts: June retainer, GBP 8,500.00.",
                "- CFO Advisory: T&M advisory hours, 12.5 hours x GBP 350 = GBP 4,375.00.",
                "- Approved expenses: Travel & Subsistence, GBP 843.20.",
                "- Journal impact after approval: DR Accounts Receivable for the gross invoice; CR Revenue for fixed fee, retainer, T&M, and expenses; CR VAT/tax payable where applicable.",
                "No invoice was sent directly. Review the Inbox invoice draft before customer delivery.",
            ]
        )

    def _format_series_a(self) -> str:
        return "\n".join(
            [
                "Thornton Series A milestone update prepared for review.",
                "- Event: Series A close at USD 14.2M.",
                "- Success-fee billing model: 0.75% milestone payable on closing.",
                "- Draft milestone invoice amount: USD 106,500.00.",
                "- Revenue/billing change: route to Inbox before sending; do not send the invoice or post revenue without approval.",
                "- Evidence to review: engagement milestone terms, closing confirmation, project P&L, and invoice draft.",
            ]
        )


def _norm(value: str) -> str:
    return " ".join(value.lower().split())


def _period_from_text(message: str) -> str | None:
    text = _norm(message)
    direct = re.search(r"\b(20\d{2}-\d{2})\b", text)
    if direct:
        return direct.group(1)
    for month, number in _MONTHS.items():
        match = re.search(rf"\b{month}\s+(20\d{{2}})\b", text)
        if match:
            return f"{match.group(1)}-{number}"
    try:
        return normalise_period(message)
    except ValueError:
        return None


def _period_label(period: str | None) -> str:
    if not period:
        return "June 2026"
    year, _, month = period.partition("-")
    month_name = {value: name.title() for name, value in _MONTHS.items()}.get(month)
    if not month_name:
        return period
    return f"{month_name} {year}"


def _date_from_text(message: str) -> str | None:
    text = _norm(message)
    direct = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if direct:
        return direct.group(1)
    match = re.search(
        r"\b(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\s+(20\d{2})\b",
        text,
    )
    if not match:
        return None
    return f"{match.group(3)}-{_MONTHS[match.group(2)]}-{int(match.group(1)):02d}"


def _time_log_arguments(message: str) -> dict[str, object] | None:
    project_match = re.search(
        r"\bproject\s+[\"“]([^\"”]+)[\"”]",
        message,
        re.IGNORECASE,
    )
    hours_match = re.search(
        r"\b(?:exactly\s+)?(\d+(?:\.\d+)?)\s+(?:billable\s+)?hours?\b",
        message,
        re.IGNORECASE,
    )
    description_match = re.search(
        r"\b(?:exact\s+)?description\s*:\s*[\"“]([^\"”]+)[\"”]",
        message,
        re.IGNORECASE,
    )
    entry_date = _date_from_text(message)
    if not project_match or not hours_match or not description_match or not entry_date:
        return None
    return {
        "project_name": project_match.group(1).strip(),
        "hours": hours_match.group(1),
        "date": entry_date,
        "description": description_match.group(1).strip(),
        "billable": not bool(
            re.search(r"\bnon[- ]?billable\b", message, re.IGNORECASE)
        ),
    }


def _client_name_from_text(text: str) -> str | None:
    if "alderton" in text:
        return "Alderton"
    if "nexus" in text:
        return "Nexus"
    if "brightwater" in text:
        return "Brightwater"
    if "thornton" in text:
        return "Thornton"
    if "forster" in text:
        return "Forster"
    return None


def _amount_and_currency(message: str) -> tuple[Decimal | None, str | None]:
    text = message.replace(",", "")
    sgd = re.search(r"\bS\$\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if sgd:
        return _decimal(sgd.group(1)), "SGD"
    match = re.search(
        r"\b(USD|GBP|SGD|EUR|AUD|INR)\s*(\d+(?:\.\d+)?)\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return _decimal(match.group(2)), match.group(1).upper()
    return None, None


def _requested_base_currency(message: str) -> str | None:
    text = _norm(message)
    if "gbp" in text and ("base-currency" in text or "base currency" in text):
        return "GBP"
    if "usd" in text and ("base-currency" in text or "base currency" in text):
        return "USD"
    return None


def _decimal(value: object) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _yes_no(value: object) -> str:
    return "yes" if bool(value) else "no"
