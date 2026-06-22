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

import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from supabase import Client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent catalog — single source of truth for the UI
# ---------------------------------------------------------------------------

AGENT_CATALOG: list[tuple[str, str, str]] = [
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
        "bill_pay_agent",
        "Bill Pay Agent",
        "Proposes vendor payment batches",
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
    {"invoice_drafter_agent", "bill_pay_agent", "accounting_guardian"}
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

        Always returns 8 entries (one per AGENT_CATALOG entry).
        Agents with no suggestion data show sample_count=0 and
        approval_rate=None / avg_confidence=None.
        """
        # Note: tenant isolation enforced via .eq("tenant_id", ...) in every query.
        # The service-role client bypasses RLS; no set_config RPC needed here.
        stats = self._fetch_suggestion_stats_30d()
        levels = self._fetch_autonomy_levels()

        results: list[dict] = []
        for agent_name, display_name, description in AGENT_CATALOG:
            s = stats.get(agent_name, {})
            sample_count = s.get("sample_count", 0)
            approval_rate = s.get("approval_rate")
            avg_confidence = s.get("avg_confidence")

            is_locked = agent_name in LOCKED_AGENTS
            current_level = levels.get(agent_name, 3 if is_locked else 2)

            # Locked agents are always L3 regardless of DB value
            if is_locked:
                current_level = 3

            is_eligible = self._is_eligible_for_promotion(
                agent_name=agent_name,
                current_level=current_level,
                approval_rate=approval_rate,
                avg_confidence=avg_confidence,
                sample_count=sample_count,
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
            raise AgentAutonomyError(
                f"{agent_name!r} is locked at L3 and cannot be changed"
            )

        if not (_MIN_LEVEL <= level <= _MAX_LEVEL):
            raise AgentAutonomyError(
                f"Level must be between {_MIN_LEVEL} and {_MAX_LEVEL}; got {level}"
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
            approved_count = sum(
                1 for r in decided if r["status"] in _APPROVED_STATUSES
            )
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
                avg_confidence = round(
                    float(sum(confidences) / len(confidences)), 4
                )

            stats[agent] = {
                "sample_count": n,
                "approval_rate": float(approval_rate) if approval_rate is not None else None,
                "avg_confidence": avg_confidence,
            }

        return stats

    def _fetch_autonomy_levels(self) -> dict[str, int]:
        """Return current autonomy level per agent_name.

        Looks at ``action_type = 'default'`` rows (UI-managed).  Falls back
        to the maximum level across all action_type rows for that agent if
        no 'default' row exists (backward-compat with promoter-written rows).
        """
        rows = (
            self.db.table("agent_autonomy_settings")
            .select("agent_name,action_type,level")
            .eq("tenant_id", self.tenant_id)
            .execute()
            .data
            or []
        )

        # Collect all rows per agent
        per_agent: dict[str, dict[str, int]] = {}
        for row in rows:
            agent = row["agent_name"]
            action = row["action_type"]
            lvl = row["level"]
            per_agent.setdefault(agent, {})[action] = lvl

        levels: dict[str, int] = {}
        for agent, action_map in per_agent.items():
            if _DEFAULT_ACTION_TYPE in action_map:
                levels[agent] = action_map[_DEFAULT_ACTION_TYPE]
            else:
                # Fall back to max level (most permissive) across all action types
                levels[agent] = max(action_map.values())

        return levels

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

        return (
            sample_count >= min_samples
            and approval_rate >= min_rate
            and avg_confidence >= 0.85
        )
