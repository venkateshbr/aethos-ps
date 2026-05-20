"""autonomy_promoter_worker — nightly; promotes/demotes agent autonomy per PLAN §6.5.

Schedule: daily at 02:00 UTC (configured in arq_settings.py).

Promotion logic (per agent/action pair, last 30 days):
  - Requires minimum sample count: 60 decisions for money agents, 30 for others.
  - Approval rate threshold: 98% for money agents, 95% for others.
  - Average confidence must be ≥ 85%.
  - Edit rate (approved_with_edits / approved) must be ≤ 15%.
  - Skips pairs already at L3 or locked at L2.
  - Creates a ``hitl_task`` of kind ``promote_autonomy`` for admin review —
    does NOT auto-apply the promotion.

Demotion logic (per L3 agent/action pair, last 14 days):
  - Requires at least 10 decided suggestions.
  - If approval rate falls below 85%, immediately demotes to L2 and creates
    a ``hitl_task`` of kind ``autonomy_demotion`` for awareness.

Money agents (higher thresholds):
  invoice_drafter_agent, accounting_guardian, bill_pay_agent
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.core.config import settings
from supabase import create_client

logger = logging.getLogger(__name__)

# Agents that touch financial transactions — require higher promotion thresholds.
MONEY_AGENTS: frozenset[str] = frozenset(
    {"invoice_drafter_agent", "accounting_guardian", "bill_pay_agent"}
)


async def autonomy_promoter_worker(ctx: dict) -> dict:
    """Nightly autonomy promotion/demotion pass.

    Returns
    -------
    ``{"promotions_proposed": int, "demotions_applied": int}``
    """
    db = create_client(settings.supabase_url, settings.supabase_service_role_key)
    tenants = (
        db.table("tenants").select("id").eq("status", "active").execute().data or []
    )
    proposed = 0
    demoted = 0

    for t in tenants:
        tid = t["id"]
        proposed += _check_promotions(db, tid)
        demoted += _check_demotions(db, tid)

    logger.info(
        "autonomy_promoter_done",
        extra={"proposed": proposed, "demoted": demoted},
    )
    return {"promotions_proposed": proposed, "demotions_applied": demoted}


def _check_promotions(db, tenant_id: str) -> int:
    """Evaluate each (agent_name, action_type) pair for L3 promotion eligibility.

    Returns the number of promotion proposals created.
    """
    since = (date.today() - timedelta(days=30)).isoformat()

    rows = (
        db.table("agent_suggestions")
        .select("agent_name,action_type,status,confidence")
        .eq("tenant_id", tenant_id)
        .gte("created_at", since)
        .not_.is_("status", "pending")
        .execute()
        .data
        or []
    )

    # Group by (agent_name, action_type)
    pairs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        pairs[(r["agent_name"], r["action_type"])].append(r)

    count = 0
    for (agent, action), decided in pairs.items():
        n = len(decided)
        is_money = agent in MONEY_AGENTS
        min_n = 60 if is_money else 30
        min_rate = Decimal("0.98") if is_money else Decimal("0.95")

        if n < min_n:
            continue

        approved = [
            r
            for r in decided
            if r["status"] in ("approved", "auto_applied", "approved_with_edits")
        ]
        edited = [r for r in decided if r["status"] == "approved_with_edits"]

        if not approved:
            continue

        approval_rate = Decimal(str(len(approved) / n))
        edit_rate = Decimal(str(len(edited) / len(approved)))
        avg_conf = sum(
            Decimal(str(r.get("confidence", "0"))) for r in approved
        ) / len(approved)

        if (
            approval_rate < min_rate
            or avg_conf < Decimal("0.85")
            or edit_rate > Decimal("0.15")
        ):
            continue

        # Skip pairs already at L3 or locked at L2
        existing = (
            db.table("agent_autonomy_settings")
            .select("level,locked_at_l2")
            .eq("tenant_id", tenant_id)
            .eq("agent_name", agent)
            .eq("action_type", action)
            .execute()
            .data
        )
        if existing:
            s = existing[0]
            if s.get("level", 2) >= 3:
                continue
            if s.get("locked_at_l2"):
                continue

        # Skip if a pending promotion task already exists for this tenant
        dup = (
            db.table("hitl_tasks")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("kind", "promote_autonomy")
            .eq("status", "open")
            .execute()
            .data
        )
        if any(row.get("id") for row in dup):
            continue

        db.table("hitl_tasks").insert(
            {
                "tenant_id": tenant_id,
                "kind": "promote_autonomy",
                "priority": "med",
                "title": f"Promote {agent} ({action}) to L3?",
                "description": (
                    f"{n} decisions, {float(approval_rate * 100):.1f}% approved, "
                    f"avg conf {float(avg_conf * 100):.1f}%"
                ),
                "payload": {
                    "agent_name": agent,
                    "action_type": action,
                    "approval_rate": str(approval_rate),
                    "avg_confidence": str(avg_conf),
                    "edit_rate": str(edit_rate),
                    "sample_count": n,
                    "proposed_level": 3,
                    "confidence_threshold": "0.90",
                },
                "status": "open",
            }
        ).execute()
        count += 1

    return count


def _check_demotions(db, tenant_id: str) -> int:
    """Demote L3 agents whose approval rate has fallen below 85% in the last 14 days.

    Returns the number of demotions applied.
    """
    since = (date.today() - timedelta(days=14)).isoformat()

    l3_settings = (
        db.table("agent_autonomy_settings")
        .select("id,agent_name,action_type")
        .eq("tenant_id", tenant_id)
        .eq("level", 3)
        .execute()
        .data
        or []
    )

    count = 0
    for s in l3_settings:
        rows = (
            db.table("agent_suggestions")
            .select("status")
            .eq("tenant_id", tenant_id)
            .eq("agent_name", s["agent_name"])
            .eq("action_type", s["action_type"])
            .gte("created_at", since)
            .not_.is_("status", "pending")
            .execute()
            .data
            or []
        )

        if len(rows) < 10:
            # Not enough data to make a demotion call.
            continue

        approved = [
            r
            for r in rows
            if r["status"] in ("approved", "auto_applied", "approved_with_edits")
        ]
        rate = Decimal(str(len(approved) / len(rows)))

        if rate < Decimal("0.85"):
            # Demote to L2, unlock (clear locked_at_l2 flag)
            db.table("agent_autonomy_settings").update(
                {"level": 2, "locked_at_l2": False}
            ).eq("id", s["id"]).execute()

            db.table("hitl_tasks").insert(
                {
                    "tenant_id": tenant_id,
                    "kind": "autonomy_demotion",
                    "priority": "high",
                    "title": (
                        f"{s['agent_name']} demoted to L2 — "
                        f"{float(rate * 100):.1f}% approval"
                    ),
                    "description": "Fell below 85% threshold over 14 days.",
                    "payload": {
                        "agent_name": s["agent_name"],
                        "action_type": s["action_type"],
                        "approval_rate": str(rate),
                    },
                    "status": "open",
                }
            ).execute()

            logger.info(
                "demoted",
                extra={
                    "tenant_id": tenant_id,
                    "agent": s["agent_name"],
                    "approval_rate": str(rate),
                },
            )
            count += 1

    return count
