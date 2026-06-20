"""intelligence_agent — weekly anomaly detection surfacing Inbox alerts.

Detects 6 financial anomaly types (all L2 — suggest only, never auto-act):
  1. UNBILLED_ENGAGEMENT      — active engagement, no invoice sent in 45+ days
  2. MARGIN_COMPRESSION       — project gross margin < 20% (was > 30% last period)
  3. EXPENSE_SPIKE            — project expense this week > 2x weekly avg (last 4 weeks)
  4. FX_EXPOSURE              — net AR-AP exposure in non-base currency > $10,000 equivalent
  5. RETAINER_UNDER_UTILIZATION — retainer client billed < 50% of retainer value last 3 months
  6. OVERDUE_ESCALATION       — invoice overdue > 60 days, no collection activity logged

Detection logic is pure Python/SQL — no LLM used for the decision.
LLM (Haiku) is used only to generate a human-readable 1-sentence narrative.

Dedup: same (anomaly_type, entity_id) not re-created within 14 days.

Design notes:
  - All checks are async; they may be run in parallel in the future.
  - Each check returns a list of IntelligenceAlert instances.
  - PII masking is applied before any LLM call.
  - Graceful degradation: LLM failure falls back to a template string.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from pydantic import BaseModel, Field

from app.agents.base import AgentDeps, make_async_llm_client, mask_pii

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_NAME = "intelligence_agent"
AUTONOMY_LEVEL = 2  # L2 — suggest only, never auto-act
DEDUP_DAYS = 14
HAIKU_MODEL = "anthropic/claude-haiku-4-5-20251001"

ANOMALY_TYPES: list[str] = [
    "UNBILLED_ENGAGEMENT",
    "MARGIN_COMPRESSION",
    "EXPENSE_SPIKE",
    "FX_EXPOSURE",
    "RETAINER_UNDER_UTILIZATION",
    "OVERDUE_ESCALATION",
]

# Threshold constants
UNBILLED_DAYS_THRESHOLD = 45
MARGIN_LOW_PCT = Decimal("0.20")   # < 20% current GM triggers alert
MARGIN_WAS_HIGH_PCT = Decimal("0.30")  # only alert if prev period was > 30%
EXPENSE_SPIKE_MULTIPLIER = Decimal("2.0")  # this week > 2x 4-week avg
FX_EXPOSURE_THRESHOLD = Decimal("10000")  # USD equivalent
RETAINER_UTILIZATION_MIN = Decimal("0.50")  # < 50% billed vs retainer value
OVERDUE_ESCALATION_DAYS = 60  # invoice must be > 60 days past due

# Fallback narrative templates (used when Haiku call fails)
FALLBACK_TEMPLATES: dict[str, str] = {
    "UNBILLED_ENGAGEMENT": (
        "Engagement '{entity_name}' has not been invoiced in {days} days "
        "(threshold: {threshold} days)."
    ),
    "MARGIN_COMPRESSION": (
        "Project '{entity_name}' gross margin has compressed to {current_margin}% "
        "(previously {prev_margin}%, threshold: {threshold}%)."
    ),
    "EXPENSE_SPIKE": (
        "Project '{entity_name}' recorded {current_week} in expenses this week, "
        "{multiplier}x the {avg} 4-week average."
    ),
    "FX_EXPOSURE": (
        "Net FX exposure in {currency} is {exposure} USD equivalent, "
        "exceeding the {threshold} threshold."
    ),
    "RETAINER_UNDER_UTILIZATION": (
        "Retainer engagement '{entity_name}' was only {pct_billed}% utilised "
        "over the last 3 months (threshold: {threshold}%)."
    ),
    "OVERDUE_ESCALATION": (
        "Invoice {entity_name} is {days} days overdue with no collection activity "
        "on record (threshold: {threshold} days)."
    ),
}


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------


class IntelligenceAlert(BaseModel):
    """Typed output produced by each anomaly detection check."""

    anomaly_type: str
    entity_id: str
    entity_name: str
    metric_current: str
    metric_threshold: str
    narrative: str
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    payload: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Dedup helper
# ---------------------------------------------------------------------------


def is_duplicate_anomaly(
    db,
    tenant_id: str,
    entity_id: str,
    anomaly_type: str,
) -> bool:
    """Return True if a pending/approved alert for this entity+type exists within 14 days.

    Queries agent_suggestions filtered by:
      - agent_name = 'intelligence_agent'
      - action_type = anomaly_type
      - related_entity_id = entity_id
      - status in ('pending', 'approved', 'auto_applied')
      - created_at >= today - 14 days
    """
    since = (date.today() - timedelta(days=DEDUP_DAYS)).isoformat()

    rows = (
        db.table("agent_suggestions")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("agent_name", AGENT_NAME)
        .eq("action_type", anomaly_type)
        .eq("related_entity_id", entity_id)
        .in_("status", ["pending", "approved", "auto_applied"])
        .gte("created_at", since)
        .execute()
        .data
    )
    return bool(rows)


# ---------------------------------------------------------------------------
# LLM narrative generator
# ---------------------------------------------------------------------------


async def generate_alert_narrative(anomaly_type: str, context: dict) -> str:
    """Use Haiku to write a human-friendly 1-sentence alert summary.

    Falls back to the FALLBACK_TEMPLATES entry if the LLM call fails or
    returns empty content. Context values are mask_pii-sanitised before
    being sent to the LLM.
    """
    safe_context = {k: mask_pii(str(v)) for k, v in context.items()}
    template = FALLBACK_TEMPLATES.get(anomaly_type, "{entity_name}: anomaly detected.")

    try:
        client = make_async_llm_client()
        prompt = (
            f"Write a single concise sentence (max 25 words) for a financial alert card.\n"
            f"Anomaly type: {anomaly_type}\n"
            f"Context: {safe_context}\n"
            f"Sentence:"
        )
        response = await client.chat.completions.create(
            model=HAIKU_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        content = content.strip()
        if content:
            return content
    except Exception:
        logger.warning(
            "intelligence_agent: LLM narrative failed for %s — using template",
            anomaly_type,
        )

    # Fallback: fill template with context values, defaulting missing keys to ""
    try:
        return template.format(**{**{k: "" for k in ["entity_name", "days", "threshold",
                                                      "current_margin", "prev_margin",
                                                      "current_week", "avg", "multiplier",
                                                      "currency", "exposure", "pct_billed"]},
                                  **context})
    except (KeyError, ValueError):
        return template


# ---------------------------------------------------------------------------
# Anomaly check 1: UNBILLED_ENGAGEMENT
# ---------------------------------------------------------------------------


async def check_unbilled_engagement(deps: AgentDeps) -> list[IntelligenceAlert]:
    """Return UNBILLED_ENGAGEMENT alerts for active engagements not invoiced in 45+ days.

    Logic:
    1. Fetch all active engagements for the tenant.
    2. For each engagement, find the most recent invoice (sent_at or issued_at).
    3. If the most recent invoice is > 45 days ago (or there are no invoices and
       the engagement started > 45 days ago), flag it.
    """
    alerts: list[IntelligenceAlert] = []

    engagements = (
        deps.db.table("engagements")
        .select("id,name,billing_arrangement,start_date")
        .eq("tenant_id", deps.tenant_id)
        .eq("status", "active")
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )

    today = date.today()

    for eng in engagements:
        eng_id = eng["id"]

        # Most recent invoice for this engagement
        inv_rows = (
            deps.db.table("invoices")
            .select("id,sent_at,issued_at,status")
            .eq("tenant_id", deps.tenant_id)
            .eq("engagement_id", eng_id)
            .not_.in_("status", ["draft", "cancelled"])
            .order("sent_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )

        if inv_rows:
            inv = inv_rows[0]
            # Prefer sent_at; fall back to issued_at
            last_date_str = inv.get("sent_at") or inv.get("issued_at") or ""
            if not last_date_str:
                continue
            try:
                last_date = date.fromisoformat(last_date_str[:10])
            except ValueError:
                continue
            days_since = (today - last_date).days
        else:
            # No invoice at all — use engagement start_date
            start_str = eng.get("start_date") or ""
            if not start_str:
                continue
            try:
                start = date.fromisoformat(start_str[:10])
            except ValueError:
                continue
            days_since = (today - start).days

        if days_since < UNBILLED_DAYS_THRESHOLD:
            continue

        if is_duplicate_anomaly(deps.db, deps.tenant_id, eng_id, "UNBILLED_ENGAGEMENT"):
            logger.debug(
                "intelligence_agent: dedup skip UNBILLED_ENGAGEMENT for engagement %s", eng_id
            )
            continue

        context = {
            "entity_name": eng.get("name", ""),
            "days": str(days_since),
            "threshold": str(UNBILLED_DAYS_THRESHOLD),
        }
        narrative = await generate_alert_narrative("UNBILLED_ENGAGEMENT", context)

        alerts.append(
            IntelligenceAlert(
                anomaly_type="UNBILLED_ENGAGEMENT",
                entity_id=eng_id,
                entity_name=eng.get("name", ""),
                metric_current=f"{days_since} days since last invoice",
                metric_threshold=f"{UNBILLED_DAYS_THRESHOLD} days",
                narrative=narrative,
                confidence=0.92,
                payload=context,
            )
        )

    return alerts


# ---------------------------------------------------------------------------
# Anomaly check 2: MARGIN_COMPRESSION
# ---------------------------------------------------------------------------


async def check_margin_compression(deps: AgentDeps) -> list[IntelligenceAlert]:
    """Return MARGIN_COMPRESSION alerts for projects with GM < 20% (was > 30% last period).

    Relies on project rows pre-populated with current_revenue, current_cost,
    prev_revenue, prev_cost fields (computed by the DB or a reporting view).
    Projects without those fields are skipped.
    """
    alerts: list[IntelligenceAlert] = []

    projects = (
        deps.db.table("projects")
        .select(
            "id,name,current_revenue,current_cost,prev_revenue,prev_cost"
        )
        .eq("tenant_id", deps.tenant_id)
        .eq("status", "active")
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )

    for proj in projects:
        proj_id = proj["id"]

        try:
            cur_rev = Decimal(str(proj.get("current_revenue") or "0"))
            cur_cost = Decimal(str(proj.get("current_cost") or "0"))
            prev_rev = Decimal(str(proj.get("prev_revenue") or "0"))
            prev_cost = Decimal(str(proj.get("prev_cost") or "0"))
        except Exception:
            continue

        if cur_rev <= 0:
            continue

        cur_gm = (cur_rev - cur_cost) / cur_rev
        prev_gm = (prev_rev - prev_cost) / prev_rev if prev_rev > 0 else Decimal("0")

        # Only alert if: current GM < 20% AND previous period was > 30%
        if cur_gm >= MARGIN_LOW_PCT or prev_gm <= MARGIN_WAS_HIGH_PCT:
            continue

        if is_duplicate_anomaly(deps.db, deps.tenant_id, proj_id, "MARGIN_COMPRESSION"):
            continue

        cur_pct = f"{float(cur_gm * 100):.1f}"
        prev_pct = f"{float(prev_gm * 100):.1f}"
        context = {
            "entity_name": proj.get("name", ""),
            "current_margin": cur_pct,
            "prev_margin": prev_pct,
            "threshold": str(int(MARGIN_LOW_PCT * 100)),
        }
        narrative = await generate_alert_narrative("MARGIN_COMPRESSION", context)

        alerts.append(
            IntelligenceAlert(
                anomaly_type="MARGIN_COMPRESSION",
                entity_id=proj_id,
                entity_name=proj.get("name", ""),
                metric_current=f"{cur_pct}% gross margin",
                metric_threshold=f"{int(MARGIN_LOW_PCT * 100)}% minimum",
                narrative=narrative,
                confidence=0.88,
                payload=context,
            )
        )

    return alerts


# ---------------------------------------------------------------------------
# Anomaly check 3: EXPENSE_SPIKE
# ---------------------------------------------------------------------------


async def check_expense_spike(deps: AgentDeps) -> list[IntelligenceAlert]:
    """Return EXPENSE_SPIKE alerts for projects where this week's expenses > 2x 4-week avg.

    Logic:
    1. Fetch all active projects.
    2. For each project, fetch expenses from the last 5 weeks.
    3. Compute avg weekly spend for weeks 1-4 (excluding current week).
    4. If current week > 2x avg, fire alert.
    """
    alerts: list[IntelligenceAlert] = []

    projects = (
        deps.db.table("projects")
        .select("id,name")
        .eq("tenant_id", deps.tenant_id)
        .eq("status", "active")
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )

    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday of current week
    four_weeks_ago = week_start - timedelta(weeks=4)

    for proj in projects:
        proj_id = proj["id"]

        expense_rows = (
            deps.db.table("expenses")
            .select("id,amount,currency,expense_date")
            .eq("tenant_id", deps.tenant_id)
            .eq("project_id", proj_id)
            .gte("expense_date", four_weeks_ago.isoformat())
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )

        if not expense_rows:
            continue

        # Bucket expenses into current week vs prior 4 weeks
        current_week_total = Decimal("0")
        prior_weeks: dict[int, Decimal] = {1: Decimal("0"), 2: Decimal("0"),
                                            3: Decimal("0"), 4: Decimal("0")}

        for exp in expense_rows:
            try:
                exp_date = date.fromisoformat(str(exp["expense_date"])[:10])
                amount = Decimal(str(exp.get("amount") or "0"))
            except Exception:
                continue

            if exp_date >= week_start:
                current_week_total += amount
            else:
                days_back = (week_start - exp_date).days
                week_num = (days_back // 7) + 1
                if 1 <= week_num <= 4:
                    prior_weeks[week_num] += amount

        prior_total = sum(prior_weeks.values())
        n_prior_weeks = sum(1 for v in prior_weeks.values() if v > 0)

        if n_prior_weeks == 0 or prior_total <= 0:
            continue

        weekly_avg = prior_total / n_prior_weeks

        if current_week_total <= weekly_avg * EXPENSE_SPIKE_MULTIPLIER:
            continue

        if is_duplicate_anomaly(deps.db, deps.tenant_id, proj_id, "EXPENSE_SPIKE"):
            continue

        multiplier = float(current_week_total / weekly_avg) if weekly_avg > 0 else 0
        context = {
            "entity_name": proj.get("name", ""),
            "current_week": str(current_week_total),
            "avg": str(weekly_avg.quantize(Decimal("0.01"))),
            "multiplier": f"{multiplier:.1f}",
        }
        narrative = await generate_alert_narrative("EXPENSE_SPIKE", context)

        alerts.append(
            IntelligenceAlert(
                anomaly_type="EXPENSE_SPIKE",
                entity_id=proj_id,
                entity_name=proj.get("name", ""),
                metric_current=f"{current_week_total} this week ({multiplier:.1f}x avg)",
                metric_threshold=f"2x weekly avg ({weekly_avg.quantize(Decimal('0.01'))})",
                narrative=narrative,
                confidence=0.90,
                payload=context,
            )
        )

    return alerts


# ---------------------------------------------------------------------------
# Anomaly check 4: FX_EXPOSURE
# ---------------------------------------------------------------------------


async def check_fx_exposure(deps: AgentDeps) -> list[IntelligenceAlert]:
    """Return FX_EXPOSURE alerts when net AR-AP in non-base currency > $10,000 equivalent.

    Groups outstanding invoices by currency, sums base_total (USD equivalent),
    and fires if any single non-base-currency bucket exceeds the threshold.
    Base currency is read from the tenants table (falls back to "USD").
    """
    alerts: list[IntelligenceAlert] = []

    # Fetch tenant base currency
    tenant_rows = (
        deps.db.table("tenants")
        .select("base_currency")
        .eq("id", deps.tenant_id)
        .execute()
        .data
        or []
    )
    base_currency: str = (tenant_rows[0].get("base_currency") or "USD") if tenant_rows else "USD"

    # Fetch all outstanding (sent/overdue) invoices with their base amounts
    invoice_rows = (
        deps.db.table("invoices")
        .select("id,currency,total,base_total,status")
        .eq("tenant_id", deps.tenant_id)
        .in_("status", ["sent", "overdue", "partial"])
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )

    if not invoice_rows:
        return alerts

    # Group non-base-currency invoices by currency
    by_currency: dict[str, Decimal] = {}
    for inv in invoice_rows:
        currency = inv.get("currency", base_currency)
        if currency == base_currency:
            continue  # no FX risk on base-currency invoices
        try:
            base_amount = Decimal(str(inv.get("base_total") or inv.get("total") or "0"))
        except Exception:
            continue
        by_currency[currency] = by_currency.get(currency, Decimal("0")) + base_amount

    if not by_currency:
        return alerts

    for currency, exposure in by_currency.items():
        if exposure < FX_EXPOSURE_THRESHOLD:
            continue

        # Use currency as entity_id for dedup (one alert per currency per tenant)
        entity_id = f"{deps.tenant_id}:{currency}"

        if is_duplicate_anomaly(deps.db, deps.tenant_id, entity_id, "FX_EXPOSURE"):
            continue

        context = {
            "entity_name": f"{currency} exposure",
            "currency": currency,
            "exposure": str(exposure.quantize(Decimal("0.01"))),
            "threshold": str(FX_EXPOSURE_THRESHOLD),
        }
        narrative = await generate_alert_narrative("FX_EXPOSURE", context)

        alerts.append(
            IntelligenceAlert(
                anomaly_type="FX_EXPOSURE",
                entity_id=entity_id,
                entity_name=f"{currency} FX Exposure",
                metric_current=f"{currency} {exposure.quantize(Decimal('0.01'))} outstanding",
                metric_threshold=f"${FX_EXPOSURE_THRESHOLD} USD equivalent",
                narrative=narrative,
                confidence=0.87,
                payload=context,
            )
        )

    return alerts


# ---------------------------------------------------------------------------
# Anomaly check 5: RETAINER_UNDER_UTILIZATION
# ---------------------------------------------------------------------------


async def check_retainer_under_utilization(deps: AgentDeps) -> list[IntelligenceAlert]:
    """Return RETAINER_UNDER_UTILIZATION alerts for retainer engagements billed < 50%
    of the retainer value over the last 3 months.

    Logic:
    1. Find all active retainer/retainer_draw engagements.
    2. Sum invoices issued in the last 3 calendar months.
    3. Compare against 3x retainer_amount.
    4. Fire if billed < 50% of expected.
    """
    alerts: list[IntelligenceAlert] = []

    engagements = (
        deps.db.table("engagements")
        .select("id,name,billing_arrangement,retainer_amount,currency")
        .eq("tenant_id", deps.tenant_id)
        .eq("status", "active")
        .in_("billing_arrangement", ["retainer", "retainer_draw"])
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )

    three_months_ago = (date.today() - timedelta(days=91)).isoformat()

    for eng in engagements:
        eng_id = eng["id"]

        try:
            monthly_amount = Decimal(str(eng.get("retainer_amount") or "0"))
        except Exception:
            continue

        if monthly_amount <= 0:
            continue

        expected = monthly_amount * 3  # 3-month expected billing

        # Sum invoices issued/sent in the last 3 months
        inv_rows = (
            deps.db.table("invoices")
            .select("id,total")
            .eq("tenant_id", deps.tenant_id)
            .eq("engagement_id", eng_id)
            .not_.in_("status", ["draft", "cancelled", "void"])
            .gte("issued_at", three_months_ago)
            .execute()
            .data
            or []
        )

        billed = sum(Decimal(str(r.get("total") or "0")) for r in inv_rows)

        if expected <= 0:
            continue

        utilization = billed / expected

        if utilization >= RETAINER_UTILIZATION_MIN:
            continue

        if is_duplicate_anomaly(deps.db, deps.tenant_id, eng_id, "RETAINER_UNDER_UTILIZATION"):
            continue

        pct_billed = f"{float(utilization * 100):.1f}"
        context = {
            "entity_name": eng.get("name", ""),
            "pct_billed": pct_billed,
            "threshold": str(int(RETAINER_UTILIZATION_MIN * 100)),
            "billed": str(billed),
            "expected": str(expected),
        }
        narrative = await generate_alert_narrative("RETAINER_UNDER_UTILIZATION", context)

        alerts.append(
            IntelligenceAlert(
                anomaly_type="RETAINER_UNDER_UTILIZATION",
                entity_id=eng_id,
                entity_name=eng.get("name", ""),
                metric_current=f"{pct_billed}% billed vs retainer value",
                metric_threshold=f"{int(RETAINER_UTILIZATION_MIN * 100)}% minimum",
                narrative=narrative,
                confidence=0.91,
                payload=context,
            )
        )

    return alerts


# ---------------------------------------------------------------------------
# Anomaly check 6: OVERDUE_ESCALATION
# ---------------------------------------------------------------------------


async def check_overdue_escalation(deps: AgentDeps) -> list[IntelligenceAlert]:
    """Return OVERDUE_ESCALATION alerts for invoices > 60 days overdue with no
    collection activity on record.

    Logic:
    1. Fetch all sent/overdue invoices with due_date < today - 60 days.
    2. For each, check collection_activities for any record linked to the invoice.
    3. If none exist, fire alert.
    """
    alerts: list[IntelligenceAlert] = []

    cutoff = (date.today() - timedelta(days=OVERDUE_ESCALATION_DAYS)).isoformat()

    invoice_rows = (
        deps.db.table("invoices")
        .select("id,invoice_number,total,currency,due_date,client_id")
        .eq("tenant_id", deps.tenant_id)
        .in_("status", ["sent", "overdue"])
        .lt("due_date", cutoff)
        .is_("deleted_at", "null")
        .execute()
        .data
        or []
    )

    for inv in invoice_rows:
        inv_id = inv["id"]

        # Compute days overdue and skip if below threshold.
        # This double-check is necessary because mock stubs used in tests
        # cannot enforce DB-level filter predicates.
        due_date_str = inv.get("due_date", "")
        try:
            due_date = date.fromisoformat(str(due_date_str)[:10])
            days_overdue = (date.today() - due_date).days
        except ValueError:
            days_overdue = OVERDUE_ESCALATION_DAYS + 1

        if days_overdue <= OVERDUE_ESCALATION_DAYS:
            continue

        # Check if any collection activity has been logged
        activity_rows = (
            deps.db.table("collection_activities")
            .select("id")
            .eq("tenant_id", deps.tenant_id)
            .eq("invoice_id", inv_id)
            .execute()
            .data
            or []
        )

        if activity_rows:
            # Collection is being worked — skip
            continue

        if is_duplicate_anomaly(deps.db, deps.tenant_id, inv_id, "OVERDUE_ESCALATION"):
            continue

        inv_num = inv.get("invoice_number", inv_id)
        context = {
            "entity_name": inv_num,
            "days": str(days_overdue),
            "threshold": str(OVERDUE_ESCALATION_DAYS),
            "amount": str(inv.get("total", "")),
            "currency": str(inv.get("currency", "USD")),
        }
        narrative = await generate_alert_narrative("OVERDUE_ESCALATION", context)

        alerts.append(
            IntelligenceAlert(
                anomaly_type="OVERDUE_ESCALATION",
                entity_id=inv_id,
                entity_name=inv_num,
                metric_current=f"{days_overdue} days overdue",
                metric_threshold=f"{OVERDUE_ESCALATION_DAYS} days",
                narrative=narrative,
                confidence=0.93,
                payload=context,
            )
        )

    return alerts
