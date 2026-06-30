"""Agents service — autonomy status and level management.

Provides read-only aggregated autonomy status per agent (last 30 days)
and a write path to manually set an agent's autonomy level.

The ``agent_autonomy_settings`` table keyed by ``(tenant_id, agent_name, action_type)``.
For the per-agent UI we use ``action_type = 'default'`` as the canonical
manually-managed row.  The autonomy_promoter worker continues to use
fine-grained ``action_type`` rows for promotion/demotion logic.

Thresholds mirror autonomy_promoter.py:
  - Money agents: 98% approval, 60 samples
  - Others:       95% approval, 30 samples
  - Both require avg_confidence >= 0.85 AND current_level == 2
"""

from __future__ import annotations

import calendar
import logging
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from app.agents.tool_registry import (
    action_type_for_tool,
    risk_class_allows,
    risk_class_for_action,
    risk_class_for_tool,
)
from app.core.finance_personas import finance_persona_catalog, persona_ids_for_role
from app.core.rbac import ROLE_HIERARCHY, UserRole, role_allows_approval
from app.services.agent_run_ledger import safe_snapshot, stable_payload_hash
from app.services.approval_policy import (
    ApprovalPolicyDecision,
    ApprovalPolicyMatrix,
    ApprovalPolicySettings,
    approval_policy_settings_from_mapping,
    default_approval_policy_settings,
)
from supabase import Client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent catalog — single source of truth for the UI
# ---------------------------------------------------------------------------

AGENT_CATALOG: list[tuple[str, str, str]] = [
    (
        "copilot_agent",
        "Copilot",
        "Answers ERP questions and routes write-capable tools through review",
    ),
    (
        "expense_extractor_agent",
        "Expense Extractor",
        "Extracts expense data from uploaded receipts",
    ),
    (
        "vendor_invoice_agent",
        "Vendor Invoice Extractor",
        "Extracts bill data from vendor invoices",
    ),
    (
        "engagement_letter_agent",
        "Engagement Letter Parser",
        "Extracts engagement terms from letters",
    ),
    (
        "invoice_drafter_agent",
        "Invoice Drafter",
        "Drafts invoices from time entries and billing terms",
    ),
    (
        "collections_agent",
        "Collections Agent",
        "Drafts payment reminder emails for overdue invoices",
    ),
    (
        "finance_ops_manager",
        "AI Finance Ops Manager",
        "Runs scheduled finance command-center checks and routes work plans to Inbox",
    ),
    (
        "time_entry_agent",
        "Time Entry Agent",
        "Drafts weekly reminders for under-logged assigned staff",
    ),
    (
        "bill_pay_agent",
        "Bill Pay Agent",
        "Proposes vendor payment batches",
    ),
    (
        "prepaid_amortization_agent",
        "Prepaid Amortization Agent",
        "Drafts prepaid expense amortization journals for month-end close",
    ),
    (
        "recurring_journal_agent",
        "Recurring Journal Agent",
        "Drafts recurring journal entries from active close templates",
    ),
    (
        "project_health_agent",
        "Project Health Monitor",
        "Detects budget burn and scope risk in projects",
    ),
    (
        "accounting_guardian",
        "Accounting Guardian",
        "Validates all journal entries — always L3, cannot be changed",
    ),
]

MONEY_AGENTS: frozenset[str] = frozenset(
    {
        "accrual_agent",
        "accounting_guardian",
        "bill_pay_agent",
        "billing_run_agent",
        "collections_agent",
        "copilot_agent",
        "finance_ops_manager",
        "invoice_drafter_agent",
        "prepaid_amortization_agent",
        "recurring_journal_agent",
        "revenue_recognition_agent",
    }
)

LOCKED_AGENTS: frozenset[str] = frozenset({"accounting_guardian"})

# Valid autonomy levels
_MIN_LEVEL = 1
_MAX_LEVEL = 3

# action_type used for manually-managed (UI-set) rows
_DEFAULT_ACTION_TYPE = "default"

# Decided statuses (suggestions that have been acted upon)
_DECIDED_STATUSES = ("approved", "approved_with_edits", "rejected", "auto_applied")
# Positive statuses (count toward approval)
_APPROVED_STATUSES = ("approved", "approved_with_edits", "auto_applied")
_VALID_AUTO_RISKS = {
    "read_only",
    "draft",
    "write_low_risk",
    "write_money_in",
    "write_money_out",
    "accounting",
}
_EXTERNAL_PROVIDER_TOOLS = frozenset(
    {
        ("collections_agent", "send_email"),
        ("time_entry_agent", "send_time_entry_reminder"),
    }
)

_AUTONOMY_COLUMNS = (
    "agent_name,action_type,level,is_enabled,failure_count,failure_threshold,"
    "circuit_open_until,circuit_open_reason,l3_opt_in,eval_passed_at,eval_score,"
    "max_auto_risk"
)

_AGENT_RUN_COLUMNS = (
    "id,agent_name,trigger_type,status,user_id,source_document_hash,prompt_version,"
    "model_version,input_hash,output_hash,usage_input_tokens,usage_output_tokens,"
    "cost_usd,trace_id,replay_pointer,error_message,started_at,completed_at,created_at"
)

_AGENT_TOOL_COLUMNS = (
    "id,agent_run_id,tool_name,risk_class,status,external_tool_call_id,input_hash,"
    "output_hash,input_snapshot,output_snapshot,duration_ms,error_message,created_at"
)

_AGENT_WORKFLOW_RUN_COLUMNS = (
    "id,tenant_id,workflow_name,status,owner_agent_name,user_id,current_step,"
    "goal_snapshot,state_snapshot,trace_id,replay_pointer,error_message,started_at,"
    "completed_at,created_at,updated_at"
)

_AGENT_EVAL_CANDIDATE_COLUMNS = (
    "id,agent_correction_id,agent_suggestion_id,agent_name,action_type,eval_case_key,"
    "status,input_hash,original_output_hash,corrected_output_hash,reason,created_at,updated_at"
)
_FINANCE_OPS_SCHEDULE_COLUMNS = (
    "tenant_id,is_enabled,cadence,run_hour_utc,run_weekday_utc,timezone,period_mode,"
    "lookback_limit,stale_after_hours,high_risk_stale_after_hours,escalation_enabled,"
    "created_at,updated_at"
)
_FINANCE_OPS_SCHEDULE_DEFAULTS: dict[str, Any] = {
    "is_enabled": True,
    "cadence": "daily",
    "run_hour_utc": 7,
    "run_weekday_utc": 0,
    "timezone": "UTC",
    "period_mode": "current_month",
    "lookback_limit": 10,
    "stale_after_hours": 24,
    "high_risk_stale_after_hours": 4,
    "escalation_enabled": True,
}
_FINANCE_OPS_WORKFLOW_NAME = "scheduled_finance_ops_manager"
_FINANCE_OPS_ACTION_PLAN_KIND = "copilot_create_finance_ops_action_plan"
_FINANCE_OPS_ACTION_ITEM_KIND = "finance_ops_action_item"
_FINANCE_OPS_ESCALATION_KIND = "finance_ops_escalation"
_FINANCE_OPS_TASK_KINDS = (
    _FINANCE_OPS_ACTION_PLAN_KIND,
    _FINANCE_OPS_ACTION_ITEM_KIND,
    _FINANCE_OPS_ESCALATION_KIND,
)
_OPEN_INBOX_STATUSES = ("open", "in_progress")
_HIGH_RISK_APPROVAL_CLASSES = {
    "write_money_out",
    "accounting",
    "external_send",
    "high_risk",
}


class AgentAutonomyError(ValueError):
    """Raised when a level-change is invalid."""


class AgentsService:
    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # GET /agents/autonomy-status
    # ------------------------------------------------------------------

    def get_autonomy_status(self) -> list[dict]:
        """Return autonomy status for all known agents.

        Always returns one entry per AGENT_CATALOG item.
        Agents with no suggestion data show sample_count=0 and
        approval_rate=None / avg_confidence=None.
        """
        # Note: tenant isolation enforced via .eq("tenant_id", ...) in every query.
        # The service-role client bypasses RLS; no set_config RPC needed here.
        stats = self._fetch_suggestion_stats_30d()
        settings_by_agent = self._fetch_default_autonomy_settings()

        results: list[dict] = []
        for agent_name, display_name, description in AGENT_CATALOG:
            s = stats.get(agent_name, {})
            sample_count = s.get("sample_count", 0)
            approval_rate = s.get("approval_rate")
            avg_confidence = s.get("avg_confidence")

            is_locked = agent_name in LOCKED_AGENTS
            setting = settings_by_agent.get(agent_name, {})
            current_level = _int_or_default(
                setting.get("level"),
                3 if is_locked else 2,
            )

            # Locked agents are always L3 regardless of DB value
            if is_locked:
                current_level = 3
            is_enabled = bool(setting.get("is_enabled", True))
            if is_locked:
                is_enabled = True
            circuit_open_until = (
                str(setting["circuit_open_until"]) if setting.get("circuit_open_until") else None
            )

            is_eligible = self._is_eligible_for_promotion(
                agent_name=agent_name,
                current_level=current_level,
                approval_rate=approval_rate,
                avg_confidence=avg_confidence,
                sample_count=sample_count,
            )
            if is_eligible:
                is_eligible = (
                    bool(setting.get("l3_opt_in"))
                    and bool(setting.get("eval_passed_at"))
                    and risk_class_allows(
                        setting.get("max_auto_risk") or "draft",
                        risk_class_for_action(agent_name, _DEFAULT_ACTION_TYPE),
                    )
                )

            results.append(
                {
                    "agent_name": agent_name,
                    "display_name": display_name,
                    "current_level": current_level,
                    "is_locked": is_locked,
                    "approval_rate_30d": approval_rate,
                    "sample_count_30d": sample_count,
                    "avg_confidence_30d": avg_confidence,
                    "is_enabled": is_enabled,
                    "failure_count": _int_or_default(setting.get("failure_count"), 0),
                    "failure_threshold": _int_or_default(
                        setting.get("failure_threshold"),
                        3,
                    ),
                    "circuit_open_until": circuit_open_until,
                    "circuit_open_reason": setting.get("circuit_open_reason"),
                    "is_circuit_open": _circuit_is_open(circuit_open_until),
                    "l3_opt_in": bool(setting.get("l3_opt_in", False)),
                    "eval_passed_at": (
                        str(setting["eval_passed_at"]) if setting.get("eval_passed_at") else None
                    ),
                    "eval_score": (
                        str(setting["eval_score"])
                        if setting.get("eval_score") is not None
                        else None
                    ),
                    "max_auto_risk": setting.get("max_auto_risk") or "draft",
                    "is_eligible_for_promotion": is_eligible,
                    "description": description,
                }
            )

        return results

    # ------------------------------------------------------------------
    # POST /agents/{agent_name}/set-level
    # ------------------------------------------------------------------

    def set_autonomy_level(self, agent_name: str, level: int) -> dict:
        """Manually set an agent's autonomy level (manager+ can call this).

        Raises AgentAutonomyError for:
        - Unknown agent name
        - Locked agent (accounting_guardian)
        - Out-of-range level (must be 1-3)
        """
        known_agents = {a[0] for a in AGENT_CATALOG}
        if agent_name not in known_agents:
            raise AgentAutonomyError(f"Unknown agent: {agent_name!r}")

        if agent_name in LOCKED_AGENTS:
            raise AgentAutonomyError(f"{agent_name!r} is locked at L3 and cannot be changed")

        if not (_MIN_LEVEL <= level <= _MAX_LEVEL):
            raise AgentAutonomyError(
                f"Level must be between {_MIN_LEVEL} and {_MAX_LEVEL}; got {level}"
            )

        if level == 3:
            self._assert_l3_promotion_allowed(
                agent_name=agent_name,
                action_type=_DEFAULT_ACTION_TYPE,
            )

        self.db.rpc(
            "set_config",
            {"setting": "app.current_tenant_id", "value": self.tenant_id},
        ).execute()

        self.db.table("agent_autonomy_settings").upsert(
            {
                "tenant_id": self.tenant_id,
                "agent_name": agent_name,
                "action_type": _DEFAULT_ACTION_TYPE,
                "level": level,
            },
            on_conflict="tenant_id,agent_name,action_type",
        ).execute()

        logger.info(
            "agent_level_set",
            extra={
                "tenant_id": self.tenant_id,
                "agent_name": agent_name,
                "level": level,
            },
        )

        return {"agent_name": agent_name, "level": level}

    def set_agent_control(
        self,
        agent_name: str,
        *,
        action_type: str = _DEFAULT_ACTION_TYPE,
        is_enabled: bool | None = None,
        failure_threshold: int | None = None,
        reset_circuit: bool = False,
    ) -> dict:
        """Update an agent/action kill switch, threshold, or circuit reset."""
        self._validate_agent_control_update(
            agent_name=agent_name,
            action_type=action_type,
            is_enabled=is_enabled,
            failure_threshold=failure_threshold,
            reset_circuit=reset_circuit,
        )

        patch: dict[str, object] = {
            "tenant_id": self.tenant_id,
            "agent_name": agent_name,
            "action_type": action_type,
        }
        if is_enabled is not None:
            patch["is_enabled"] = is_enabled
        if failure_threshold is not None:
            patch["failure_threshold"] = failure_threshold
        if reset_circuit:
            patch.update(
                {
                    "failure_count": 0,
                    "last_failure_at": None,
                    "circuit_opened_at": None,
                    "circuit_open_until": None,
                    "circuit_open_reason": None,
                }
            )

        self.db.rpc(
            "set_config",
            {"setting": "app.current_tenant_id", "value": self.tenant_id},
        ).execute()

        result = (
            self.db.table("agent_autonomy_settings")
            .upsert(patch, on_conflict="tenant_id,agent_name,action_type")
            .execute()
        )
        rows = result.data or []
        row = rows[0] if rows else self._fetch_control_row(agent_name, action_type)
        if row is None:
            row = patch

        logger.info(
            "agent_control_set",
            extra={
                "tenant_id": self.tenant_id,
                "agent_name": agent_name,
                "action_type": action_type,
                "is_enabled": is_enabled,
                "failure_threshold": failure_threshold,
                "reset_circuit": reset_circuit,
            },
        )
        return self._control_response(row, agent_name, action_type)

    def set_l3_policy(
        self,
        agent_name: str,
        *,
        action_type: str = _DEFAULT_ACTION_TYPE,
        l3_opt_in: bool,
        max_auto_risk: str,
    ) -> dict:
        """Set admin-controlled L3 promotion policy for an agent/action."""
        self._validate_agent_control_update(
            agent_name=agent_name,
            action_type=action_type,
            is_enabled=None,
            failure_threshold=None,
            reset_circuit=True,
        )
        if max_auto_risk not in _VALID_AUTO_RISKS:
            raise AgentAutonomyError(f"Unknown max_auto_risk: {max_auto_risk!r}")

        patch: dict[str, object] = {
            "tenant_id": self.tenant_id,
            "agent_name": agent_name,
            "action_type": action_type,
            "l3_opt_in": l3_opt_in,
            "max_auto_risk": max_auto_risk,
        }

        self.db.rpc(
            "set_config",
            {"setting": "app.current_tenant_id", "value": self.tenant_id},
        ).execute()

        result = (
            self.db.table("agent_autonomy_settings")
            .upsert(patch, on_conflict="tenant_id,agent_name,action_type")
            .execute()
        )
        rows = result.data or []
        row = rows[0] if rows else self._fetch_control_row(agent_name, action_type)
        if row is None:
            row = patch
        return self._l3_policy_response(row, agent_name, action_type)

    def get_finance_ops_schedule(self) -> dict:
        """Return a tenant's configured or seeded Finance Ops Manager cadence."""
        row = self._fetch_finance_ops_schedule()
        return self._finance_ops_schedule_response(
            row or {"tenant_id": self.tenant_id, **_FINANCE_OPS_SCHEDULE_DEFAULTS},
            is_seeded_default=row is None,
        )

    def get_finance_ops_control_room(
        self,
        *,
        workflow_limit: int = 10,
        task_limit: int = 10,
    ) -> dict:
        """Return the safe Finance Ops Manager command-center state.

        This deliberately omits raw traces, replay pointers, context refs,
        stack traces, and tool internals. It is meant for Atlas and manager
        dashboards, not low-level debugging.
        """
        generated_at = datetime.now(UTC)
        schedule = self.get_finance_ops_schedule()
        capped_workflow_limit = max(1, min(workflow_limit, 25))
        capped_task_limit = max(1, min(task_limit, 25))
        recent_scheduled = self.list_agent_workflow_runs(
            workflow_name=_FINANCE_OPS_WORKFLOW_NAME,
            limit=capped_workflow_limit,
        )["workflow_runs"]
        recent_all = self.list_agent_workflow_runs(limit=capped_workflow_limit)[
            "workflow_runs"
        ]
        open_tasks = self._fetch_open_finance_ops_tasks(limit=capped_task_limit)

        return {
            "tenant_id": self.tenant_id,
            "generated_at": generated_at.isoformat(),
            "schedule": schedule,
            "next_run_at": self._next_finance_ops_run_at(schedule, now=generated_at),
            "latest_scheduled_run": (
                self._workflow_control_room_summary(recent_scheduled[0])
                if recent_scheduled
                else None
            ),
            "recent_scheduled_runs": [
                self._workflow_control_room_summary(row) for row in recent_scheduled
            ],
            "recent_workflow_status_counts": dict(
                Counter(str(row.get("status") or "unknown") for row in recent_all)
            ),
            "waiting_on_human_workflows": [
                self._workflow_control_room_summary(row)
                for row in recent_all
                if row.get("status") == "waiting_on_human"
            ],
            "failed_or_skipped_workflows": [
                self._workflow_control_room_summary(row)
                for row in recent_all
                if row.get("status") in {"failed", "skipped", "cancelled"}
            ],
            "open_action_plans": [
                self._finance_ops_task_summary(row)
                for row in open_tasks
                if row.get("kind") == _FINANCE_OPS_ACTION_PLAN_KIND
            ],
            "open_plan_items": [
                self._finance_ops_task_summary(row)
                for row in open_tasks
                if row.get("kind") == _FINANCE_OPS_ACTION_ITEM_KIND
            ],
            "open_escalations": [
                self._finance_ops_task_summary(row)
                for row in open_tasks
                if row.get("kind") == _FINANCE_OPS_ESCALATION_KIND
            ],
            "operational_health": self._safe_operational_health(),
        }

    def get_approval_controls_read_pack(
        self,
        *,
        user_id: str,
        fallback_role: str | None = None,
        inbox_limit: int = 10,
    ) -> dict:
        """Return role-aware approval controls, persona, and Inbox-risk state."""
        generated_at = datetime.now(UTC)
        user_role = self._resolve_tenant_user_role(
            user_id,
            fallback_role=fallback_role,
        )
        if ROLE_HIERARCHY.get(user_role, 0) < ROLE_HIERARCHY[UserRole.viewer]:
            raise PermissionError("Approval controls read pack requires viewer or higher")

        settings, policy_source = self._effective_approval_policy_settings()
        capped_limit = max(1, min(inbox_limit, 50))
        inbox_items = [
            self._approval_controls_inbox_item(
                row,
                settings=settings,
                user_role=user_role,
            )
            for row in self._fetch_open_inbox_tasks(limit=capped_limit)
        ]
        high_risk_items = [
            item for item in inbox_items if self._is_high_risk_inbox_item(item)
        ]
        higher_role_items = [
            item for item in inbox_items if not item["current_user_can_approve"]
        ]
        policy_rules = self._approval_controls_policy_rules(
            settings,
            user_role=user_role,
        )
        matched_persona_ids = persona_ids_for_role(user_role)

        return {
            "tenant_id": self.tenant_id,
            "generated_at": generated_at.isoformat(),
            "current_user_role": user_role.value,
            "policy_source": policy_source,
            "matched_persona_ids": matched_persona_ids,
            "personas": self._approval_controls_personas(
                matched_persona_ids=matched_persona_ids,
            ),
            "policy_rules": policy_rules,
            "visible_open_inbox_item_count": len(inbox_items),
            "pending_high_risk_inbox": high_risk_items,
            "pending_items_requiring_higher_role": higher_role_items,
            "denied_action_explanations": self._denied_action_explanations(
                user_role=user_role,
                policy_rules=policy_rules,
            ),
        }

    def set_finance_ops_schedule(
        self,
        *,
        is_enabled: bool,
        cadence: str,
        run_hour_utc: int,
        run_weekday_utc: int,
        timezone: str,
        period_mode: str,
        lookback_limit: int,
        stale_after_hours: int,
        high_risk_stale_after_hours: int,
        escalation_enabled: bool,
    ) -> dict:
        """Upsert tenant-level cadence controls for scheduled Finance Ops."""
        self._validate_finance_ops_schedule(
            cadence=cadence,
            run_hour_utc=run_hour_utc,
            run_weekday_utc=run_weekday_utc,
            timezone=timezone,
            period_mode=period_mode,
            lookback_limit=lookback_limit,
            stale_after_hours=stale_after_hours,
            high_risk_stale_after_hours=high_risk_stale_after_hours,
        )
        payload = {
            "tenant_id": self.tenant_id,
            "is_enabled": is_enabled,
            "cadence": cadence,
            "run_hour_utc": run_hour_utc,
            "run_weekday_utc": run_weekday_utc,
            "timezone": timezone,
            "period_mode": period_mode,
            "lookback_limit": lookback_limit,
            "stale_after_hours": stale_after_hours,
            "high_risk_stale_after_hours": high_risk_stale_after_hours,
            "escalation_enabled": escalation_enabled,
        }

        self.db.rpc(
            "set_config",
            {"setting": "app.current_tenant_id", "value": self.tenant_id},
        ).execute()

        result = (
            self.db.table("finance_ops_schedules")
            .upsert(payload, on_conflict="tenant_id")
            .execute()
        )
        rows = result.data or []
        row = rows[0] if rows else self._fetch_finance_ops_schedule() or payload
        logger.info(
            "finance_ops_schedule_set",
            extra={
                "tenant_id": self.tenant_id,
                "cadence": cadence,
                "run_hour_utc": run_hour_utc,
                "escalation_enabled": escalation_enabled,
            },
        )
        return self._finance_ops_schedule_response(row, is_seeded_default=False)

    def list_agent_runs(
        self,
        *,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict:
        """Return recent agent runs with aggregate tool counts."""
        capped_limit = max(1, min(limit, 100))
        query = (
            self.db.table("agent_runs")
            .select(_AGENT_RUN_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .order("created_at", desc=True)
            .limit(capped_limit)
        )
        if agent_name:
            query = query.eq("agent_name", agent_name)
        if status:
            query = query.eq("status", status)

        rows = query.execute().data or []
        run_ids = [row["id"] for row in rows]
        tool_counts = self._fetch_tool_counts(run_ids)

        runs = []
        for row in rows:
            counts = tool_counts.get(row["id"], {"tool_count": 0, "failed_tool_count": 0})
            runs.append({**self._run_summary(row), **counts})

        return {"runs": runs, "total": len(runs)}

    def get_agent_run(self, run_id: str) -> dict | None:
        """Return one agent run and its ordered tool invocations."""
        result = (
            self.db.table("agent_runs")
            .select(_AGENT_RUN_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .eq("id", run_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None

        row = result.data[0]
        tools = (
            self.db.table("agent_tool_invocations")
            .select(_AGENT_TOOL_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .eq("agent_run_id", run_id)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )
        failed_count = sum(1 for tool in tools if tool.get("status") == "failed")
        return {
            **self._run_summary(row),
            "tool_count": len(tools),
            "failed_tool_count": failed_count,
            "tool_invocations": [self._tool_invocation(tool) for tool in tools],
        }

    def list_agent_workflow_runs(
        self,
        *,
        workflow_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict:
        """Return recent durable agent workflow containers."""
        capped_limit = max(1, min(limit, 100))
        query = (
            self.db.table("agent_workflow_runs")
            .select(_AGENT_WORKFLOW_RUN_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .order("created_at", desc=True)
            .limit(capped_limit)
        )
        if workflow_name:
            query = query.eq("workflow_name", workflow_name)
        if status:
            query = query.eq("status", status)
        rows = query.execute().data or []
        return {
            "workflow_runs": [self._workflow_run(row) for row in rows],
            "total": len(rows),
        }

    def get_agent_workflow_run(self, workflow_run_id: str) -> dict | None:
        """Return a single durable agent workflow container."""
        result = (
            self.db.table("agent_workflow_runs")
            .select(_AGENT_WORKFLOW_RUN_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .eq("id", workflow_run_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return self._workflow_run(rows[0]) if rows else None

    def build_agent_run_replay(self, run_id: str) -> dict | None:
        """Return a deterministic, non-mutating replay package for a recorded run.

        This is an audit replay, not a live rerun. It reconstructs the ordered
        tool-call transcript from snapshots already stored in the ledger so an
        operator can reproduce the agent's inputs and outputs without executing
        any write-capable tool again.
        """
        run = self.get_agent_run(run_id)
        if run is None:
            return None

        steps = [
            {
                "index": index,
                "tool_invocation_id": tool["id"],
                "tool_name": tool["tool_name"],
                "risk_class": tool["risk_class"],
                "status": tool["status"],
                "input_hash": tool.get("input_hash"),
                "output_hash": tool.get("output_hash"),
                "input_snapshot": tool.get("input_snapshot") or {},
                "output_snapshot": tool.get("output_snapshot") or {},
                "error_message": tool.get("error_message"),
                "created_at": tool["created_at"],
            }
            for index, tool in enumerate(run["tool_invocations"], start=1)
        ]
        manifest = {
            "run_id": run["id"],
            "agent_name": run["agent_name"],
            "status": run["status"],
            "trace_id": run.get("trace_id"),
            "replay_pointer": run.get("replay_pointer"),
            "input_hash": run.get("input_hash"),
            "output_hash": run.get("output_hash"),
            "prompt_version": run.get("prompt_version"),
            "model_version": run.get("model_version"),
            "steps": steps,
        }
        return {
            "run_id": run["id"],
            "agent_name": run["agent_name"],
            "status": run["status"],
            "replay_mode": "recorded_snapshot",
            "can_reexecute": False,
            "trace_id": run.get("trace_id"),
            "replay_pointer": run.get("replay_pointer"),
            "input_hash": run.get("input_hash"),
            "output_hash": run.get("output_hash"),
            "prompt_version": run.get("prompt_version"),
            "model_version": run.get("model_version"),
            "manifest_hash": stable_payload_hash(manifest),
            "steps": steps,
        }

    def build_agent_run_replay_validation(self, run_id: str) -> dict | None:
        """Dry-run read-only replay steps against current code and compare hashes.

        This intentionally does not replay write-capable, money movement, or
        accounting tools. Those steps are classified as blocked by current risk
        policy until a dedicated executor with sandbox/compensation semantics
        exists.
        """
        run = self.get_agent_run(run_id)
        if run is None:
            return None

        steps = [
            self._validate_replay_step(run["agent_name"], index, tool)
            for index, tool in enumerate(run["tool_invocations"], start=1)
        ]
        executed_count = sum(
            1
            for step in steps
            if step["replay_status"]
            in {"matched", "drift_detected", "executed_no_baseline"}
        )
        blocked_count = sum(
            1
            for step in steps
            if step["replay_status"] in {"blocked_by_risk", "unsupported_executor"}
        )
        planned_count = sum(
            1
            for step in steps
            if step["replay_status"] == "planned_for_human_reexecution"
        )
        drift_count = sum(1 for step in steps if step["replay_status"] == "drift_detected")
        failed_count = sum(1 for step in steps if step["replay_status"] == "failed")

        if failed_count:
            overall_status = "failed"
        elif drift_count:
            overall_status = "drift_detected"
        elif planned_count and executed_count:
            overall_status = "partially_planned"
        elif planned_count:
            overall_status = "planned"
        elif executed_count and blocked_count:
            overall_status = "partially_reexecuted"
        elif executed_count:
            overall_status = "matched"
        elif steps:
            overall_status = "blocked"
        else:
            overall_status = "no_steps"

        manifest = {
            "run_id": run["id"],
            "agent_name": run["agent_name"],
            "validation_mode": "current_code_dry_run",
            "overall_status": overall_status,
            "steps": [
                {
                    "tool_invocation_id": step["tool_invocation_id"],
                    "tool_name": step["tool_name"],
                    "replay_status": step["replay_status"],
                    "current_output_hash": step.get("current_output_hash"),
                }
                for step in steps
            ],
        }
        return {
            "run_id": run["id"],
            "agent_name": run["agent_name"],
            "validation_mode": "current_code_dry_run",
            "overall_status": overall_status,
            "can_reexecute": bool(steps) and executed_count == len(steps) and failed_count == 0,
            "can_request_human_reexecution": bool(planned_count)
            and failed_count == 0
            and drift_count == 0
            and blocked_count == 0,
            "manifest_hash": stable_payload_hash(manifest),
            "reexecuted_step_count": executed_count,
            "planned_step_count": planned_count,
            "blocked_step_count": blocked_count,
            "drift_step_count": drift_count,
            "failed_step_count": failed_count,
            "steps": steps,
        }

    def list_eval_candidates(
        self,
        *,
        agent_name: str | None = None,
        status: str | None = "candidate",
        limit: int = 50,
    ) -> dict:
        """Return correction-backed eval candidates for review/export."""
        capped_limit = max(1, min(limit, 100))
        query = (
            self.db.table("agent_eval_candidates")
            .select(_AGENT_EVAL_CANDIDATE_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .order("created_at", desc=True)
            .limit(capped_limit)
        )
        if agent_name:
            query = query.eq("agent_name", agent_name)
        if status:
            query = query.eq("status", status)

        rows = query.execute().data or []
        candidates = [self._eval_candidate(row) for row in rows]
        return {"candidates": candidates, "total": len(candidates)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_suggestion_stats_30d(self) -> dict[str, dict]:
        """Return per-agent suggestion stats for the last 30 days.

        Returns a mapping of agent_name -> {sample_count, approval_rate,
        avg_confidence}.  Only agents with at least one decided suggestion
        appear in the dict.
        """
        since = (date.today() - timedelta(days=30)).isoformat()

        rows = (
            self.db.table("agent_suggestions")
            .select("agent_name,status,confidence")
            .eq("tenant_id", self.tenant_id)
            .in_("status", list(_DECIDED_STATUSES))
            .gte("created_at", since)
            .execute()
            .data
            or []
        )

        # Group by agent_name
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            agent = row["agent_name"]
            grouped.setdefault(agent, []).append(row)

        stats: dict[str, dict] = {}
        for agent, decided in grouped.items():
            n = len(decided)
            approved_count = sum(1 for r in decided if r["status"] in _APPROVED_STATUSES)
            approval_rate = round(approved_count / n, 4) if n > 0 else None

            confidences: list[Decimal] = []
            for r in decided:
                raw = r.get("confidence")
                if raw is not None:
                    try:
                        confidences.append(Decimal(str(raw)))
                    except InvalidOperation:
                        pass

            avg_confidence: float | None = None
            if confidences:
                avg_confidence = round(float(sum(confidences) / len(confidences)), 4)

            stats[agent] = {
                "sample_count": n,
                "approval_rate": float(approval_rate) if approval_rate is not None else None,
                "avg_confidence": avg_confidence,
            }

        return stats

    def _fetch_default_autonomy_settings(self) -> dict[str, dict]:
        """Return the UI-managed default autonomy/control row per agent."""
        rows = (
            self.db.table("agent_autonomy_settings")
            .select(_AUTONOMY_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .execute()
            .data
            or []
        )

        per_agent: dict[str, dict[str, dict]] = {}
        for row in rows:
            agent = row["agent_name"]
            action = row["action_type"]
            per_agent.setdefault(agent, {})[action] = row

        settings: dict[str, dict] = {}
        for agent, action_map in per_agent.items():
            if _DEFAULT_ACTION_TYPE in action_map:
                settings[agent] = action_map[_DEFAULT_ACTION_TYPE]
            else:
                # Backward compat with promoter-written action rows: expose the
                # most permissive action level but keep default control values.
                fallback = max(action_map.values(), key=lambda row: row.get("level", 2))
                settings[agent] = {
                    "agent_name": agent,
                    "action_type": _DEFAULT_ACTION_TYPE,
                    "level": fallback.get("level", 2),
                }

        return settings

    def _fetch_control_row(self, agent_name: str, action_type: str) -> dict | None:
        result = (
            self.db.table("agent_autonomy_settings")
            .select(_AUTONOMY_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .eq("agent_name", agent_name)
            .eq("action_type", action_type)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def _fetch_finance_ops_schedule(self) -> dict | None:
        result = (
            self.db.table("finance_ops_schedules")
            .select(_FINANCE_OPS_SCHEDULE_COLUMNS)
            .eq("tenant_id", self.tenant_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def _fetch_open_finance_ops_tasks(self, *, limit: int) -> list[dict]:
        try:
            result = (
                self.db.table("hitl_tasks")
                .select("id,tenant_id,kind,priority,title,payload,status,created_at,updated_at")
                .eq("tenant_id", self.tenant_id)
                .in_("kind", list(_FINANCE_OPS_TASK_KINDS))
                .in_("status", ["open", "in_progress"])
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        except Exception:
            logger.warning(
                "finance_ops_control_room_open_tasks_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id},
            )
            return []
        return result.data or []

    def _resolve_tenant_user_role(
        self,
        user_id: str,
        *,
        fallback_role: str | None,
    ) -> UserRole:
        try:
            result = (
                self.db.table("tenant_users")
                .select("role")
                .eq("tenant_id", self.tenant_id)
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                return _user_role_or_default(rows[0].get("role"), UserRole.viewer)
        except Exception:
            logger.warning(
                "approval_controls_role_lookup_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id, "user_id": user_id},
            )

        if fallback_role is not None:
            return _user_role_or_default(fallback_role, UserRole.viewer)
        return UserRole.employee

    def _effective_approval_policy_settings(
        self,
    ) -> tuple[ApprovalPolicySettings, str]:
        row = self._fetch_tenant_approval_policy()
        if row is None:
            return default_approval_policy_settings(), "system_default"
        return (
            approval_policy_settings_from_mapping(
                row,
                policy_source="tenant_default",
            ),
            "tenant_default",
        )

    def _fetch_tenant_approval_policy(self) -> dict | None:
        try:
            result = (
                self.db.table("tenant_approval_policies")
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.warning(
                "approval_controls_policy_lookup_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id},
            )
            return None
        rows = result.data or []
        return rows[0] if rows else None

    def _fetch_open_inbox_tasks(self, *, limit: int) -> list[dict]:
        try:
            result = (
                self.db.table("hitl_tasks")
                .select(
                    "id,tenant_id,kind,priority,title,payload,status,created_at,updated_at,"
                    "agent_suggestions(agent_name,confidence,output_snapshot,action_type)"
                )
                .eq("tenant_id", self.tenant_id)
                .in_("status", list(_OPEN_INBOX_STATUSES))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        except Exception:
            logger.warning(
                "approval_controls_open_inbox_lookup_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id},
            )
            return []
        return result.data or []

    def _approval_controls_policy_rules(
        self,
        settings: ApprovalPolicySettings,
        *,
        user_role: UserRole,
    ) -> list[dict]:
        return [
            self._approval_policy_rule(
                rule_id="draft_low_risk",
                label="Draft and low-risk changes",
                required_role=settings.draft_role,
                user_role=user_role,
                explanation=(
                    "Draft invoices, low-risk record preparation, and reviewed "
                    "work items require Manager review before materialising."
                ),
            ),
            self._approval_policy_rule(
                rule_id="money_in",
                label="Money-in actions",
                required_role=settings.money_in_role,
                user_role=user_role,
                explanation=(
                    "Customer invoices and other money-in changes require "
                    "review before the finance record changes."
                ),
            ),
            self._approval_policy_rule(
                rule_id="external_send",
                label="External communications",
                required_role=settings.external_send_role,
                user_role=user_role,
                explanation=(
                    "Customer or vendor emails are drafted by AI but require "
                    "review before any external send path."
                ),
            ),
            self._approval_policy_rule(
                rule_id="money_out_default",
                label="Money-out actions",
                required_role=settings.money_out_default_role,
                user_role=user_role,
                explanation=(
                    "Vendor payment proposals and other money-out work require "
                    "the configured money-out approver."
                ),
            ),
            self._approval_policy_rule(
                rule_id="money_out_owner_threshold",
                label="High-value money-out actions",
                required_role=settings.money_out_owner_role,
                user_role=user_role,
                threshold=str(settings.money_out_owner_threshold),
                explanation=(
                    "Money-out at or above the owner threshold requires Owner "
                    "approval even if the default money-out role is lower."
                ),
            ),
            self._approval_policy_rule(
                rule_id="accounting",
                label="Accounting and close actions",
                required_role=settings.accounting_role,
                user_role=user_role,
                explanation=(
                    "Journals, close preparation, and accounting workflows "
                    "require the configured accounting approver."
                ),
            ),
            self._approval_policy_rule(
                rule_id="manual_journal_threshold",
                label="High-value manual journals",
                required_role=settings.accounting_role,
                user_role=user_role,
                threshold=str(settings.manual_journal_approval_threshold),
                explanation=(
                    "Manual journals at or above the threshold route to Inbox "
                    "and must be approved by a different permitted approver."
                ),
            ),
            self._approval_policy_rule(
                rule_id="high_risk_ai_action",
                label="High-risk AI actions",
                required_role=settings.high_risk_role,
                user_role=user_role,
                explanation=(
                    "High-risk AI-recommended finance actions require the "
                    "configured elevated approver."
                ),
            ),
        ]

    def _approval_policy_rule(
        self,
        *,
        rule_id: str,
        label: str,
        required_role: UserRole,
        user_role: UserRole,
        explanation: str,
        threshold: str | None = None,
    ) -> dict:
        return {
            "id": rule_id,
            "label": label,
            "required_role": required_role.value,
            "current_user_can_approve": _role_allows(user_role, required_role),
            "threshold": threshold,
            "explanation": explanation,
        }

    def _approval_controls_personas(
        self,
        *,
        matched_persona_ids: list[str],
    ) -> list[dict]:
        matched = set(matched_persona_ids)
        return [
            {
                "id": str(persona["id"]),
                "label": str(persona["label"]),
                "description": str(persona["description"]),
                "matched_current_role": str(persona["id"]) in matched,
                "read_only": bool(persona["read_only"]),
                "mapped_roles": [str(role) for role in persona["mapped_roles"]],
                "areas": [str(area) for area in persona["areas"]],
                "allowed_actions": [
                    str(action) for action in persona["allowed_actions"]
                ],
                "restricted_actions": [
                    str(action) for action in persona["restricted_actions"]
                ],
            }
            for persona in finance_persona_catalog()
        ]

    def _approval_controls_inbox_item(
        self,
        row: dict,
        *,
        settings: ApprovalPolicySettings,
        user_role: UserRole,
    ) -> dict:
        payload = _combined_inbox_payload(row)
        decision = ApprovalPolicyMatrix.decision_for_task(
            str(row.get("kind") or ""),
            payload,
            settings=settings,
        )
        return {
            "id": str(row.get("id") or ""),
            "kind": str(row.get("kind") or ""),
            "priority": str(row.get("priority") or "normal"),
            "title": str(row.get("title") or ""),
            "status": str(row.get("status") or "open"),
            "created_at": str(row.get("created_at") or ""),
            "risk_category": _risk_category_label(decision.risk_class),
            "required_approval_role": decision.required_role.value,
            "current_user_can_approve": _role_allows(
                user_role,
                decision.required_role,
            ),
            "business_reason": _approval_business_reason(decision),
            "amount": _decimal_text(decision.amount),
            "threshold": _decimal_text(decision.threshold),
        }

    def _is_high_risk_inbox_item(self, item: dict) -> bool:
        return (
            item.get("risk_category")
            in {
                "Money out",
                "Accounting",
                "External send",
                "High-risk AI action",
            }
            or item.get("required_approval_role") in {"admin", "owner"}
            or str(item.get("priority") or "").lower() in {"high", "critical", "urgent"}
        )

    def _denied_action_explanations(
        self,
        *,
        user_role: UserRole,
        policy_rules: list[dict],
    ) -> list[str]:
        explanations: list[str] = []
        if user_role == UserRole.approver:
            explanations.append(
                "Your current role can approve manager-threshold Inbox work, "
                "but cannot create, edit, post, pay, send, lock, or change settings."
            )
        elif not role_allows_approval(user_role, UserRole.manager):
            explanations.append(
                "Your current role can inspect permitted tenant records and "
                "decision evidence, but cannot approve, edit, reject, post, "
                "pay, send, lock, or change settings."
            )
        if ROLE_HIERARCHY.get(user_role, 0) < ROLE_HIERARCHY[UserRole.admin]:
            explanations.append(
                "Approval policy changes and elevated finance operations "
                "require Admin or Owner."
            )

        for rule in policy_rules:
            if rule["current_user_can_approve"]:
                continue
            explanations.append(
                f"{rule['label']} require {str(rule['required_role']).title()} "
                "or higher approval."
            )

        return list(dict.fromkeys(explanations))

    def _safe_operational_health(self) -> dict:
        from app.services.operational_telemetry import TenantHealthService

        try:
            summary = TenantHealthService(self.db, self.tenant_id).summary()
        except Exception:
            logger.warning(
                "finance_ops_control_room_health_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id},
            )
            return {
                "status": "unknown",
                "failure_counts": {},
                "alerts": {"route": {}, "count": 0, "items": []},
            }

        telemetry = summary.get("telemetry") or {}
        request_failures = telemetry.get("request_failures") or []
        background_failures = telemetry.get("background_failures") or []
        alerts = summary.get("alerts") or {}
        runtime = summary.get("runtime") or {}
        return {
            "status": summary.get("status") or "unknown",
            "runtime": {
                "environment": runtime.get("environment"),
                "queue_configured": runtime.get("queue_configured"),
                "queue_required": runtime.get("queue_required"),
                "extraction_mode": runtime.get("extraction_mode"),
            },
            "rate_limit": summary.get("rate_limit") or {},
            "failure_counts": {
                "request_failures": sum(int(row.get("count") or 0) for row in request_failures),
                "background_failures": sum(
                    int(row.get("count") or 0) for row in background_failures
                ),
                "failed_agent_runs_24h": int(telemetry.get("failed_agent_runs_24h") or 0),
                "failed_tool_invocations_24h": int(
                    telemetry.get("failed_tool_invocations_24h") or 0
                ),
                "failed_workflow_runs_24h": int(
                    telemetry.get("failed_workflow_runs_24h") or 0
                ),
            },
            "alerts": {
                "route": alerts.get("route") or {},
                "count": len(alerts.get("items") or []),
                "items": alerts.get("items") or [],
            },
        }

    def _assert_l3_promotion_allowed(self, agent_name: str, action_type: str) -> None:
        row = self._fetch_control_row(agent_name, action_type) or {}
        if not row.get("l3_opt_in"):
            raise AgentAutonomyError("L3 promotion requires explicit admin opt-in")
        if not row.get("eval_passed_at"):
            raise AgentAutonomyError("L3 promotion requires a passing eval gate")

        actual_risk = risk_class_for_action(agent_name, action_type)
        max_auto_risk = row.get("max_auto_risk") or "draft"
        if not risk_class_allows(max_auto_risk, actual_risk):
            raise AgentAutonomyError(
                f"L3 promotion requires max_auto_risk >= {actual_risk}; "
                f"current max_auto_risk is {max_auto_risk}"
            )

        stats = self._fetch_suggestion_stats_30d().get(agent_name, {})
        if not self._is_eligible_for_promotion(
            agent_name=agent_name,
            current_level=_int_or_default(row.get("level"), 2),
            approval_rate=stats.get("approval_rate"),
            avg_confidence=stats.get("avg_confidence"),
            sample_count=_int_or_default(stats.get("sample_count"), 0),
        ):
            raise AgentAutonomyError("L3 promotion requires sufficient approval history")

    @staticmethod
    def _validate_agent_control_update(
        *,
        agent_name: str,
        action_type: str,
        is_enabled: bool | None,
        failure_threshold: int | None,
        reset_circuit: bool,
    ) -> None:
        known_agents = {a[0] for a in AGENT_CATALOG}
        if agent_name not in known_agents and agent_name != "copilot_agent":
            raise AgentAutonomyError(f"Unknown agent: {agent_name!r}")
        if not action_type:
            raise AgentAutonomyError("action_type is required")
        if is_enabled is None and failure_threshold is None and not reset_circuit:
            raise AgentAutonomyError("No control change requested")
        if failure_threshold is not None and not (1 <= failure_threshold <= 25):
            raise AgentAutonomyError("failure_threshold must be between 1 and 25")
        if agent_name in LOCKED_AGENTS and is_enabled is False:
            raise AgentAutonomyError(
                f"{agent_name!r} is required for accounting controls and cannot be disabled"
            )

    @staticmethod
    def _validate_finance_ops_schedule(
        *,
        cadence: str,
        run_hour_utc: int,
        run_weekday_utc: int,
        timezone: str,
        period_mode: str,
        lookback_limit: int,
        stale_after_hours: int,
        high_risk_stale_after_hours: int,
    ) -> None:
        if cadence not in {"daily", "weekly"}:
            raise AgentAutonomyError("cadence must be daily or weekly")
        if not (0 <= run_hour_utc <= 23):
            raise AgentAutonomyError("run_hour_utc must be between 0 and 23")
        if not (0 <= run_weekday_utc <= 6):
            raise AgentAutonomyError("run_weekday_utc must be between 0 and 6")
        if not timezone.strip() or len(timezone) > 64:
            raise AgentAutonomyError("timezone must be 1-64 characters")
        if period_mode not in {"current_month", "previous_month"}:
            raise AgentAutonomyError("period_mode must be current_month or previous_month")
        if not (1 <= lookback_limit <= 25):
            raise AgentAutonomyError("lookback_limit must be between 1 and 25")
        if not (1 <= high_risk_stale_after_hours <= 720):
            raise AgentAutonomyError(
                "high_risk_stale_after_hours must be between 1 and 720"
            )
        if not (high_risk_stale_after_hours <= stale_after_hours <= 720):
            raise AgentAutonomyError(
                "stale_after_hours must be between high_risk_stale_after_hours and 720"
            )

    def _finance_ops_schedule_response(
        self,
        row: dict,
        *,
        is_seeded_default: bool,
    ) -> dict:
        data = {**_FINANCE_OPS_SCHEDULE_DEFAULTS, **row}
        return {
            "tenant_id": str(data.get("tenant_id") or self.tenant_id),
            "is_enabled": bool(data.get("is_enabled", True)),
            "cadence": str(data.get("cadence") or "daily"),
            "run_hour_utc": _int_or_default(data.get("run_hour_utc"), 7),
            "run_weekday_utc": _int_or_default(data.get("run_weekday_utc"), 0),
            "timezone": str(data.get("timezone") or "UTC"),
            "period_mode": str(data.get("period_mode") or "current_month"),
            "lookback_limit": _int_or_default(data.get("lookback_limit"), 10),
            "stale_after_hours": _int_or_default(data.get("stale_after_hours"), 24),
            "high_risk_stale_after_hours": _int_or_default(
                data.get("high_risk_stale_after_hours"),
                4,
            ),
            "escalation_enabled": bool(data.get("escalation_enabled", True)),
            "is_seeded_default": is_seeded_default,
            "created_at": str(data["created_at"]) if data.get("created_at") else None,
            "updated_at": str(data["updated_at"]) if data.get("updated_at") else None,
        }

    def _fetch_tool_counts(self, run_ids: list[str]) -> dict[str, dict[str, int]]:
        if not run_ids:
            return {}
        rows = (
            self.db.table("agent_tool_invocations")
            .select("agent_run_id,status")
            .eq("tenant_id", self.tenant_id)
            .in_("agent_run_id", run_ids)
            .execute()
            .data
            or []
        )
        counts: dict[str, dict[str, int]] = {}
        for row in rows:
            run_id = row["agent_run_id"]
            bucket = counts.setdefault(run_id, {"tool_count": 0, "failed_tool_count": 0})
            bucket["tool_count"] += 1
            if row.get("status") == "failed":
                bucket["failed_tool_count"] += 1
        return counts

    @staticmethod
    def _run_summary(row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "agent_name": row["agent_name"],
            "trigger_type": row["trigger_type"],
            "status": row["status"],
            "user_id": str(row["user_id"]) if row.get("user_id") else None,
            "source_document_hash": row.get("source_document_hash"),
            "prompt_version": row.get("prompt_version"),
            "model_version": row.get("model_version"),
            "input_hash": row.get("input_hash"),
            "output_hash": row.get("output_hash"),
            "usage_input_tokens": row.get("usage_input_tokens"),
            "usage_output_tokens": row.get("usage_output_tokens"),
            "cost_usd": str(row["cost_usd"]) if row.get("cost_usd") is not None else None,
            "trace_id": row.get("trace_id"),
            "replay_pointer": row.get("replay_pointer"),
            "error_message": row.get("error_message"),
            "started_at": str(row["started_at"]),
            "completed_at": str(row["completed_at"]) if row.get("completed_at") else None,
            "created_at": str(row["created_at"]),
        }

    @staticmethod
    def _tool_invocation(row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "tool_name": row["tool_name"],
            "risk_class": row["risk_class"],
            "status": row["status"],
            "external_tool_call_id": row.get("external_tool_call_id"),
            "input_hash": row.get("input_hash"),
            "output_hash": row.get("output_hash"),
            "input_snapshot": row.get("input_snapshot") or {},
            "output_snapshot": row.get("output_snapshot") or {},
            "duration_ms": row.get("duration_ms"),
            "error_message": row.get("error_message"),
            "created_at": str(row["created_at"]),
        }

    @staticmethod
    def _workflow_run(row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "workflow_name": row["workflow_name"],
            "status": row["status"],
            "owner_agent_name": row.get("owner_agent_name"),
            "user_id": str(row["user_id"]) if row.get("user_id") else None,
            "current_step": row.get("current_step"),
            "goal_snapshot": row.get("goal_snapshot") or {},
            "state_snapshot": row.get("state_snapshot") or {},
            "trace_id": row.get("trace_id"),
            "replay_pointer": row.get("replay_pointer"),
            "error_message": row.get("error_message"),
            "started_at": str(row["started_at"]),
            "completed_at": str(row["completed_at"]) if row.get("completed_at") else None,
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    @staticmethod
    def _next_finance_ops_run_at(schedule: dict, *, now: datetime) -> str | None:
        if not bool(schedule.get("is_enabled", True)):
            return None

        run_hour = _int_or_default(schedule.get("run_hour_utc"), 7)
        candidate = now.replace(hour=run_hour, minute=0, second=0, microsecond=0)
        cadence = str(schedule.get("cadence") or "daily")
        if cadence == "weekly":
            target_weekday = _int_or_default(schedule.get("run_weekday_utc"), 0)
            days_ahead = (target_weekday - candidate.weekday()) % 7
            candidate = candidate + timedelta(days=days_ahead)
            if candidate <= now:
                candidate = candidate + timedelta(days=7)
            return candidate.isoformat()

        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate.isoformat()

    @classmethod
    def _workflow_control_room_summary(cls, row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "workflow_name": str(row.get("workflow_name") or ""),
            "status": str(row.get("status") or "unknown"),
            "owner_agent_name": row.get("owner_agent_name"),
            "current_step": row.get("current_step"),
            "period": cls._workflow_period(row),
            "started_at": str(row.get("started_at") or row.get("created_at") or ""),
            "completed_at": str(row["completed_at"]) if row.get("completed_at") else None,
            "updated_at": str(row.get("updated_at") or row.get("created_at") or ""),
            "has_error": bool(row.get("error_message")),
            "business_summary": cls._workflow_business_summary(row),
        }

    @staticmethod
    def _workflow_period(row: dict) -> str | None:
        for snapshot_name in ("state_snapshot", "goal_snapshot"):
            snapshot = row.get(snapshot_name)
            if not isinstance(snapshot, dict):
                continue
            for key in ("period", "period_start", "month", "schedule_key"):
                value = snapshot.get(key)
                if value:
                    return str(value)
        return None

    @staticmethod
    def _workflow_business_summary(row: dict) -> str:
        status_value = str(row.get("status") or "unknown")
        workflow_name = str(row.get("workflow_name") or "workflow").replace("_", " ")
        step = str(row.get("current_step") or "").replace("_", " ")
        if status_value == "waiting_on_human":
            return f"{workflow_name} is waiting for human review at {step or 'review'}."
        if status_value == "failed":
            return f"{workflow_name} failed and needs operator review."
        if status_value == "cancelled":
            return f"{workflow_name} was cancelled before completion."
        if status_value == "skipped":
            return f"{workflow_name} skipped because no eligible work was due."
        if status_value == "running":
            return f"{workflow_name} is currently running."
        if status_value == "succeeded":
            return f"{workflow_name} completed successfully."
        return f"{workflow_name} is {status_value.replace('_', ' ')}."

    @staticmethod
    def _finance_ops_task_summary(row: dict) -> dict:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        source_action = payload.get("source_plan_action")
        source_action = source_action if isinstance(source_action, dict) else {}
        return {
            "id": str(row["id"]),
            "kind": str(row.get("kind") or ""),
            "priority": str(row.get("priority") or "normal"),
            "title": str(row.get("title") or "Finance Ops work item"),
            "status": str(row.get("status") or "open"),
            "period": (
                str(payload.get("period"))
                if payload.get("period")
                else str(source_action.get("period")) if source_action.get("period") else None
            ),
            "action_count": _optional_int(payload.get("action_count")),
            "source_schedule_key": (
                str(payload.get("source_schedule_key"))
                if payload.get("source_schedule_key")
                else None
            ),
            "risk_class": (
                str(payload.get("risk_class")) if payload.get("risk_class") else None
            ),
            "required_approval_role": (
                str(payload.get("required_approval_role"))
                if payload.get("required_approval_role")
                else None
            ),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
        }

    @staticmethod
    def _eval_candidate(row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "agent_correction_id": str(row["agent_correction_id"]),
            "agent_suggestion_id": str(row["agent_suggestion_id"]),
            "agent_name": row["agent_name"],
            "action_type": row["action_type"],
            "eval_case_key": row["eval_case_key"],
            "status": row["status"],
            "input_hash": row.get("input_hash"),
            "original_output_hash": row.get("original_output_hash"),
            "corrected_output_hash": row.get("corrected_output_hash"),
            "reason": row.get("reason"),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def _validate_replay_step(self, agent_name: str, index: int, tool: dict) -> dict:
        input_snapshot = tool.get("input_snapshot") or {}
        recorded_input_hash = tool.get("input_hash")
        recorded_output_hash = tool.get("output_hash")
        current_risk = risk_class_for_tool(agent_name, tool["tool_name"])
        base = {
            "index": index,
            "tool_invocation_id": tool["id"],
            "tool_name": tool["tool_name"],
            "recorded_risk_class": tool["risk_class"],
            "current_risk_class": current_risk,
            "recorded_status": tool["status"],
            "input_hash": recorded_input_hash,
            "recorded_output_hash": recorded_output_hash,
            "current_output_hash": None,
            "input_hash_matches": (
                stable_payload_hash(input_snapshot) == recorded_input_hash
                if recorded_input_hash
                else None
            ),
            "output_hash_matches": None,
            "duration_ms": None,
            "current_output_snapshot": None,
            "reexecution_plan": None,
            "error_message": None,
        }

        if current_risk != "read_only":
            reexecution_plan = self._build_reexecution_plan(
                agent_name=agent_name,
                tool=tool,
                current_risk=current_risk,
                input_snapshot=input_snapshot,
            )
            return {
                **base,
                "replay_status": "planned_for_human_reexecution",
                "reason": (
                    f"Current tool risk is {current_risk}; validation built a "
                    "human-approved re-execution plan and did not execute side effects"
                ),
                "reexecution_plan": reexecution_plan,
            }

        started_at = time.perf_counter()
        try:
            current_output = self._execute_current_read_only_tool(
                agent_name,
                tool["tool_name"],
                input_snapshot,
            )
        except NotImplementedError as exc:
            return {
                **base,
                "replay_status": "unsupported_executor",
                "reason": str(exc),
            }
        except Exception as exc:  # pragma: no cover - defensive audit path
            return {
                **base,
                "replay_status": "failed",
                "reason": "Current read-only tool execution failed",
                "duration_ms": int((time.perf_counter() - started_at) * 1000),
                "error_message": str(exc),
            }

        current_hash = stable_payload_hash(current_output)
        output_hash_matches = (
            current_hash == recorded_output_hash if recorded_output_hash else None
        )
        if output_hash_matches is True:
            replay_status = "matched"
            reason = "Current read-only output hash matches recorded output"
        elif output_hash_matches is False:
            replay_status = "drift_detected"
            reason = "Current read-only output hash differs from recorded output"
        else:
            replay_status = "executed_no_baseline"
            reason = "Current read-only tool executed; no recorded output hash to compare"

        return {
            **base,
            "replay_status": replay_status,
            "reason": reason,
            "current_output_hash": current_hash,
            "output_hash_matches": output_hash_matches,
            "duration_ms": int((time.perf_counter() - started_at) * 1000),
            "current_output_snapshot": safe_snapshot(current_output),
        }

    def _build_reexecution_plan(
        self,
        *,
        agent_name: str,
        tool: dict,
        current_risk: str,
        input_snapshot: dict[str, Any],
    ) -> dict:
        tool_name = tool["tool_name"]
        action_type = action_type_for_tool(agent_name, tool_name)
        external_side_effect = bool(tool.get("external_tool_call_id")) or (
            agent_name,
            tool_name,
        ) in _EXTERNAL_PROVIDER_TOOLS
        idempotency_key = stable_payload_hash(
            {
                "tenant_id": self.tenant_id,
                "agent_name": agent_name,
                "tool_invocation_id": tool["id"],
                "tool_name": tool_name,
                "input_hash": tool.get("input_hash")
                or stable_payload_hash(input_snapshot),
            }
        )
        approval_role = "admin" if current_risk in {"write_money_out", "accounting"} else "manager"
        if external_side_effect:
            operator_action = (
                "Review the recorded provider call, verify the recipient/amount/content, "
                "and replay through the provider-specific workflow only after human approval."
            )
        else:
            operator_action = (
                "Replay through the normal application service after human approval; "
                "do not bypass tool policy, HITL, or accounting guards."
            )
        return {
            "mode": "human_approved_current_code_reexecution",
            "dry_run_only": True,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "action_type": action_type,
            "risk_class": current_risk,
            "requires_human_approval": True,
            "approval_role": approval_role,
            "external_side_effect": external_side_effect,
            "external_tool_call_id": tool.get("external_tool_call_id"),
            "idempotency_key": idempotency_key,
            "input_hash": tool.get("input_hash") or stable_payload_hash(input_snapshot),
            "recorded_output_hash": tool.get("output_hash"),
            "preconditions": [
                "tenant scope must match the recorded run",
                "input hash must match the reviewed replay payload",
                "agent/tool circuit breaker must be closed",
                "current role and autonomy policy must still allow the action",
                "business idempotency check must pass before any mutation",
            ],
            "operator_action": operator_action,
        }

    def _execute_current_read_only_tool(
        self,
        agent_name: str,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict:
        if agent_name == "copilot_agent":
            if tool_name == "query_engagements":
                return self._replay_query_engagements(tool_input)
            if tool_name == "query_time_entries":
                return self._replay_query_time_entries(tool_input)
            if tool_name in {"get_ar_aging", "get_ap_aging", "get_wip"}:
                return self._replay_reporting_tool(tool_name, tool_input)

        if agent_name == "reporting_agent" and tool_name in {
            "get_ar_aging",
            "get_ap_aging",
            "get_wip",
            "get_project_pnl",
            "get_utilization",
            "get_revenue",
            "get_trial_balance",
        }:
            return self._replay_reporting_tool(tool_name, tool_input)

        raise NotImplementedError(
            f"No current-code dry-run executor is registered for {agent_name}.{tool_name}"
        )

    def _replay_query_engagements(self, tool_input: dict[str, Any]) -> dict:
        status = str(tool_input.get("status") or "all")
        limit = _int_or_default(tool_input.get("limit"), 10)
        query = (
            self.db.table("engagements")
            .select("id, name, billing_arrangement, currency, total_value, status")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .limit(min(max(limit, 1), 50))
        )
        if status != "all":
            query = query.eq("status", status)
        engagements = query.execute().data or []
        return {
            "count": len(engagements),
            "engagements": [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "billing_arrangement": row.get("billing_arrangement"),
                    "currency": row.get("currency"),
                    "total_value": row.get("total_value"),
                    "status": row["status"],
                }
                for row in engagements
            ],
        }

    def _replay_query_time_entries(self, tool_input: dict[str, Any]) -> dict:
        project_id = tool_input.get("project_id")
        if not project_id:
            raise ValueError("query_time_entries replay requires project_id")
        query = (
            self.db.table("time_entries")
            .select("id, date, hours, description, billable, billing_status, employee_id")
            .eq("tenant_id", self.tenant_id)
            .eq("project_id", project_id)
            .is_("deleted_at", "null")
            .order("date", desc=True)
            .limit(50)
        )
        if tool_input.get("date_from"):
            query = query.gte("date", tool_input["date_from"])
        if tool_input.get("date_to"):
            query = query.lte("date", tool_input["date_to"])
        entries = query.execute().data or []
        total_hours = sum(float(row.get("hours", 0)) for row in entries)
        return {
            "count": len(entries),
            "total_hours": round(total_hours, 2),
            "entries": [
                {
                    "id": str(row["id"]),
                    "date": str(row["date"]),
                    "hours": str(row["hours"]),
                    "description": row.get("description") or "",
                    "billable": row.get("billable"),
                    "billing_status": row.get("billing_status"),
                }
                for row in entries
            ],
        }

    def _replay_reporting_tool(self, tool_name: str, tool_input: dict[str, Any]) -> dict:
        from app.services.reports_service import ReportsService

        svc = ReportsService(self.db, self.tenant_id)  # type: ignore[arg-type]
        if tool_name == "get_ar_aging":
            return svc.ar_aging()
        if tool_name == "get_ap_aging":
            return svc.ap_aging()
        if tool_name == "get_wip":
            return {"wip": svc.wip(engagement_id=tool_input.get("engagement_id"))}
        if tool_name == "get_project_pnl":
            return {
                "projects": svc.project_pnl(
                    project_id=tool_input.get("project_id"),
                    period_start=tool_input.get("period_start"),
                    period_end=tool_input.get("period_end"),
                )
            }
        if tool_name == "get_utilization":
            period_start, period_end = _period_bounds(tool_input.get("period"))
            return {
                "utilization": svc.utilization(
                    employee_id=tool_input.get("employee_id"),
                    period_start=period_start,
                    period_end=period_end,
                ),
                "period": tool_input.get("period"),
            }
        if tool_name == "get_revenue":
            period_start, period_end = _period_bounds(tool_input.get("period"))
            return {
                "revenue_by_engagement": svc.revenue_by_engagement(
                    period_start=period_start,
                    period_end=period_end,
                ),
                "period": tool_input.get("period"),
            }
        if tool_name == "get_trial_balance":
            return svc.trial_balance(
                as_of_period=tool_input.get("as_of_period")
            ).model_dump(mode="json")
        raise NotImplementedError(
            f"No current-code dry-run executor is registered for reporting tool {tool_name}"
        )

    @staticmethod
    def _control_response(row: dict, agent_name: str, action_type: str) -> dict:
        circuit_open_until = (
            str(row["circuit_open_until"]) if row.get("circuit_open_until") else None
        )
        return {
            "agent_name": row.get("agent_name", agent_name),
            "action_type": row.get("action_type", action_type),
            "is_enabled": bool(row.get("is_enabled", True)),
            "failure_count": _int_or_default(row.get("failure_count"), 0),
            "failure_threshold": _int_or_default(row.get("failure_threshold"), 3),
            "circuit_open_until": circuit_open_until,
            "circuit_open_reason": row.get("circuit_open_reason"),
            "is_circuit_open": _circuit_is_open(circuit_open_until),
        }

    @staticmethod
    def _l3_policy_response(row: dict, agent_name: str, action_type: str) -> dict:
        return {
            "agent_name": row.get("agent_name", agent_name),
            "action_type": row.get("action_type", action_type),
            "l3_opt_in": bool(row.get("l3_opt_in", False)),
            "max_auto_risk": row.get("max_auto_risk") or "draft",
            "eval_passed_at": (str(row["eval_passed_at"]) if row.get("eval_passed_at") else None),
            "eval_score": (str(row["eval_score"]) if row.get("eval_score") is not None else None),
        }

    @staticmethod
    def _is_eligible_for_promotion(
        *,
        agent_name: str,
        current_level: int,
        approval_rate: float | None,
        avg_confidence: float | None,
        sample_count: int,
    ) -> bool:
        """True iff this agent meets L2→L3 promotion thresholds."""
        if current_level != 2:
            return False
        if agent_name in LOCKED_AGENTS:
            return False
        if approval_rate is None or avg_confidence is None:
            return False

        is_money = agent_name in MONEY_AGENTS
        min_rate = 0.98 if is_money else 0.95
        min_samples = 60 if is_money else 30

        return sample_count >= min_samples and approval_rate >= min_rate and avg_confidence >= 0.85


def _int_or_default(value: object, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _optional_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _role_allows(user_role: UserRole, required_role: UserRole) -> bool:
    return role_allows_approval(user_role, required_role)


def _user_role_or_default(value: object, default: UserRole) -> UserRole:
    try:
        return UserRole(str(value))
    except ValueError:
        return default


def _combined_inbox_payload(row: dict) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    suggestion = row.get("agent_suggestions")
    if isinstance(suggestion, list):
        suggestion = suggestion[0] if suggestion else {}
    if isinstance(suggestion, dict):
        output_snapshot = suggestion.get("output_snapshot")
        if isinstance(output_snapshot, dict):
            payload.update(output_snapshot)
    task_payload = row.get("payload")
    if isinstance(task_payload, dict):
        payload.update(task_payload)
    return payload


def _risk_category_label(risk_class: str) -> str:
    labels = {
        "read_only": "Read only",
        "draft": "Draft",
        "write_low_risk": "Low-risk write",
        "write_money_in": "Money in",
        "write_money_out": "Money out",
        "accounting": "Accounting",
        "external_send": "External send",
        "high_risk": "High-risk AI action",
    }
    return labels.get(risk_class, "Review required")


def _approval_business_reason(decision: ApprovalPolicyDecision) -> str:
    amount = _decimal_text(decision.amount)
    threshold = _decimal_text(decision.threshold)
    if decision.reason == "money_out_above_owner_review_threshold":
        return (
            f"Money-out amount {amount} is at or above the Owner review "
            f"threshold {threshold}."
        )
    if decision.reason == "manual_journal_above_approval_threshold":
        return (
            f"Manual journal total {amount} is at or above the accounting "
            f"approval threshold {threshold}."
        )
    if decision.reason == "external_send_requires_review":
        return "External communications require human review before sending."
    if decision.risk_class == "write_money_out":
        return "Money-out work requires the configured elevated approver."
    if decision.risk_class == "accounting":
        return "Accounting and close work requires the configured accounting approver."
    if decision.risk_class == "write_money_in":
        return "Money-in changes require Manager-or-higher review."
    if decision.risk_class == "high_risk":
        return "High-risk AI action requires elevated review."
    if decision.risk_class in {"draft", "write_low_risk"}:
        return "Draft or low-risk work requires Manager-or-higher review."
    return "Inbox work requires human review before materialising."


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _circuit_is_open(value: object) -> bool:
    if not value:
        return False
    try:
        if isinstance(value, datetime):
            opened_until = value
        else:
            opened_until = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if opened_until.tzinfo is None:
            opened_until = opened_until.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return False
    return opened_until > datetime.now(UTC)


def _period_bounds(period: object) -> tuple[str | None, str | None]:
    if not period:
        return None, None
    raw = str(period)
    if len(raw) != 7 or raw[4] != "-":
        return None, None
    try:
        year = int(raw[:4])
        month = int(raw[5:7])
    except ValueError:
        return None, None
    if not (1 <= month <= 12):
        return None, None
    last_day = calendar.monthrange(year, month)[1]
    return (
        f"{year:04d}-{month:02d}-01",
        f"{year:04d}-{month:02d}-{last_day:02d}",
    )
