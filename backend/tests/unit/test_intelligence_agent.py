"""Unit tests for intelligence_agent anomaly detection and intelligence_worker.

TDD red phase — tests written before implementation exists.

Coverage:
  - test_unbilled_engagement_detected: active engagement with no invoice in 50 days => alert
  - test_no_alert_recent_invoice: invoice sent 20 days ago => no alert
  - test_dedup_14_days: same (anomaly_type, entity_id) not re-created within 14 days
  - test_expense_spike_detected: project expense this week 3x 4-week avg => alert
  - test_margin_compression_detected: project GM < 20% (was >30%) => alert
  - test_no_margin_alert_healthy: GM > 30% => no alert
  - test_fx_exposure_detected: net AR-AP exposure > $10,000 eq => alert
  - test_overdue_escalation_detected: invoice overdue > 60 days, no collection => alert
  - test_retainer_under_utilization_detected: client billed <50% of retainer => alert
  - test_generate_alert_narrative_fallback: LLM failure => fallback template used
  - test_check_anomalies_graceful_degradation: one check raises => worker continues

All tests are pure-Python — no I/O, no DB, no HTTP.
DB interactions replaced with lightweight MagicMock stubs.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import AgentDeps
from app.agents.intelligence_agent import (
    ANOMALY_TYPES,
    FALLBACK_TEMPLATES,
    IntelligenceAlert,
    check_expense_spike,
    check_fx_exposure,
    check_margin_compression,
    check_overdue_escalation,
    check_retainer_under_utilization,
    check_unbilled_engagement,
    generate_alert_narrative,
    is_duplicate_anomaly,
)
from app.workers.intelligence_worker import (
    _run_anomaly_checks,
    _uuid_or_none,
)

pytestmark = pytest.mark.unit


def test_intelligence_worker_related_entity_id_accepts_uuid_only() -> None:
    """Synthetic anomaly ids stay out of the UUID related_entity_id column."""
    entity_id = str(uuid.uuid4())

    assert _uuid_or_none(entity_id) == entity_id
    assert _uuid_or_none("tenant-001:USD") is None


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------


class _FlatMock:
    """Chainable stub: every attr access and call returns self.

    Set ``.final_data`` to control what ``.execute().data`` returns.
    """

    def __init__(self, data: list | None = None) -> None:
        self.final_data = data if data is not None else []

    def __getattr__(self, name: str) -> _FlatMock:
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> _FlatMock:
        return self

    @property
    def data(self) -> list:
        return self.final_data

    def execute(self) -> _FlatMock:
        return self


def _make_deps(
    *,
    suggestions: list[dict] | None = None,
    engagements: list[dict] | None = None,
    invoices: list[dict] | None = None,
    expenses: list[dict] | None = None,
    projects: list[dict] | None = None,
    fx_rates: list[dict] | None = None,
    collection_activities: list[dict] | None = None,
    billing_runs: list[dict] | None = None,
    base_currency: str = "USD",
    insert_result: dict | None = None,
) -> tuple[AgentDeps, MagicMock]:
    """Build AgentDeps with a MagicMock Supabase client routing by table name."""
    db = MagicMock()

    sugg_mock = _FlatMock(suggestions or [])
    eng_mock = _FlatMock(engagements or [])
    inv_mock = _FlatMock(invoices or [])
    exp_mock = _FlatMock(expenses or [])
    proj_mock = _FlatMock(projects or [])
    fx_mock = _FlatMock(fx_rates or [])
    coll_mock = _FlatMock(collection_activities or [])
    br_mock = _FlatMock(billing_runs or [])
    tenant_mock = _FlatMock([{"base_currency": base_currency}])

    inserted: list[dict] = []
    _insert_res = MagicMock()
    _insert_res.execute.return_value = MagicMock(
        data=[insert_result or {"id": str(uuid.uuid4())}]
    )

    def _capture_insert(payload: dict) -> MagicMock:
        inserted.append(payload)
        return _insert_res

    def table_side_effect(table_name: str) -> MagicMock:
        t = MagicMock()
        if table_name == "agent_suggestions":
            t.select.return_value = sugg_mock
            t.insert.side_effect = _capture_insert
        elif table_name == "engagements":
            t.select.return_value = eng_mock
        elif table_name == "invoices":
            t.select.return_value = inv_mock
        elif table_name == "expenses":
            t.select.return_value = exp_mock
        elif table_name == "projects":
            t.select.return_value = proj_mock
        elif table_name == "fx_rates":
            t.select.return_value = fx_mock
        elif table_name == "hitl_tasks":
            t.insert.side_effect = _capture_insert
        elif table_name == "collection_activities":
            t.select.return_value = coll_mock
        elif table_name == "billing_runs":
            t.select.return_value = br_mock
        elif table_name == "tenants":
            t.select.return_value = tenant_mock
        else:
            t.select.return_value = _FlatMock([])
            t.insert.side_effect = _capture_insert
        return t

    db.table.side_effect = table_side_effect

    tenant_id = str(uuid.uuid4())
    deps = AgentDeps(tenant_id=tenant_id, user_id=None, db=db)
    return deps, db


# ---------------------------------------------------------------------------
# ANOMALY_TYPES constant check
# ---------------------------------------------------------------------------


def test_all_six_anomaly_types_defined() -> None:
    """ANOMALY_TYPES must contain exactly the 6 specified anomaly kinds."""
    expected = {
        "UNBILLED_ENGAGEMENT",
        "MARGIN_COMPRESSION",
        "EXPENSE_SPIKE",
        "FX_EXPOSURE",
        "RETAINER_UNDER_UTILIZATION",
        "OVERDUE_ESCALATION",
    }
    assert set(ANOMALY_TYPES) == expected


def test_fallback_templates_cover_all_types() -> None:
    """FALLBACK_TEMPLATES must have an entry for every anomaly type."""
    for anomaly_type in ANOMALY_TYPES:
        assert anomaly_type in FALLBACK_TEMPLATES, (
            f"Missing fallback template for {anomaly_type}"
        )


# ---------------------------------------------------------------------------
# IntelligenceAlert model
# ---------------------------------------------------------------------------


def test_intelligence_alert_model() -> None:
    """IntelligenceAlert is a valid Pydantic model with required fields."""
    alert = IntelligenceAlert(
        anomaly_type="UNBILLED_ENGAGEMENT",
        entity_id=str(uuid.uuid4()),
        entity_name="Acme Corp — Annual Retainer",
        metric_current="52 days since last invoice",
        metric_threshold="45 days",
        narrative="Engagement has not been billed in 52 days.",
        confidence=0.95,
    )
    assert alert.anomaly_type == "UNBILLED_ENGAGEMENT"
    assert 0.0 < alert.confidence <= 1.0


# ---------------------------------------------------------------------------
# is_duplicate_anomaly
# ---------------------------------------------------------------------------


def test_dedup_14_days_returns_true_when_recent_suggestion_exists() -> None:
    """is_duplicate_anomaly returns True when same entity+type alerted within 14 days."""
    entity_id = str(uuid.uuid4())
    existing = [
        {
            "id": str(uuid.uuid4()),
            "agent_name": "intelligence_agent",
            "action_type": "UNBILLED_ENGAGEMENT",
            "status": "pending",
        }
    ]
    deps, _ = _make_deps(suggestions=existing)

    result = is_duplicate_anomaly(
        deps.db, deps.tenant_id, entity_id, "UNBILLED_ENGAGEMENT"
    )
    assert result is True


def test_dedup_14_days_returns_false_when_no_recent_suggestion() -> None:
    """is_duplicate_anomaly returns False when no recent alert exists."""
    entity_id = str(uuid.uuid4())
    deps, _ = _make_deps(suggestions=[])

    result = is_duplicate_anomaly(
        deps.db, deps.tenant_id, entity_id, "UNBILLED_ENGAGEMENT"
    )
    assert result is False


def test_dedup_14_days() -> None:
    """Same anomaly is not re-created within 14 days — dedup check returns True."""
    entity_id = str(uuid.uuid4())
    # Simulate existing pending suggestion within 14 days
    existing = [{"id": str(uuid.uuid4()), "status": "pending"}]
    deps, _ = _make_deps(suggestions=existing)

    result = is_duplicate_anomaly(
        deps.db, deps.tenant_id, entity_id, "EXPENSE_SPIKE"
    )
    assert result is True


# ---------------------------------------------------------------------------
# check_unbilled_engagement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unbilled_engagement_detected() -> None:
    """Active engagement with no invoice in 50 days triggers UNBILLED_ENGAGEMENT alert."""
    engagement_id = str(uuid.uuid4())
    fifty_days_ago = (date.today() - timedelta(days=50)).isoformat()

    engagements = [
        {
            "id": engagement_id,
            "name": "Acme Corp — Strategy Advisory",
            "status": "active",
            "billing_arrangement": "time_and_materials",
            "start_date": (date.today() - timedelta(days=90)).isoformat(),
        }
    ]
    # Last invoice sent 50 days ago (past the 45-day threshold)
    invoices = [
        {
            "id": str(uuid.uuid4()),
            "engagement_id": engagement_id,
            "sent_at": fifty_days_ago,
            "status": "sent",
        }
    ]

    deps, _ = _make_deps(suggestions=[], engagements=engagements, invoices=invoices)

    alerts = await check_unbilled_engagement(deps)

    unbilled_alerts = [a for a in alerts if a.anomaly_type == "UNBILLED_ENGAGEMENT"]
    assert len(unbilled_alerts) >= 1
    alert = unbilled_alerts[0]
    assert alert.entity_id == engagement_id
    assert "50" in alert.metric_current or "day" in alert.metric_current.lower()


@pytest.mark.asyncio
async def test_no_alert_recent_invoice() -> None:
    """Engagement with invoice sent 20 days ago does NOT trigger UNBILLED_ENGAGEMENT."""
    engagement_id = str(uuid.uuid4())
    twenty_days_ago = (date.today() - timedelta(days=20)).isoformat()

    engagements = [
        {
            "id": engagement_id,
            "name": "Beta Corp — Audit",
            "status": "active",
            "billing_arrangement": "fixed_fee",
            "start_date": (date.today() - timedelta(days=60)).isoformat(),
        }
    ]
    invoices = [
        {
            "id": str(uuid.uuid4()),
            "engagement_id": engagement_id,
            "sent_at": twenty_days_ago,
            "status": "sent",
        }
    ]

    deps, _ = _make_deps(suggestions=[], engagements=engagements, invoices=invoices)

    alerts = await check_unbilled_engagement(deps)

    unbilled_alerts = [a for a in alerts if a.anomaly_type == "UNBILLED_ENGAGEMENT"]
    assert len(unbilled_alerts) == 0


@pytest.mark.asyncio
async def test_unbilled_engagement_with_no_invoices_at_all() -> None:
    """Active engagement started 50 days ago with NO invoices at all triggers alert."""
    engagement_id = str(uuid.uuid4())

    engagements = [
        {
            "id": engagement_id,
            "name": "Gamma Corp — Due Diligence",
            "status": "active",
            "billing_arrangement": "time_and_materials",
            "start_date": (date.today() - timedelta(days=50)).isoformat(),
        }
    ]
    # No invoices at all
    invoices: list[dict] = []

    deps, _ = _make_deps(suggestions=[], engagements=engagements, invoices=invoices)

    alerts = await check_unbilled_engagement(deps)

    unbilled_alerts = [a for a in alerts if a.anomaly_type == "UNBILLED_ENGAGEMENT"]
    assert len(unbilled_alerts) >= 1


# ---------------------------------------------------------------------------
# check_expense_spike
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expense_spike_detected() -> None:
    """Project expense this week 3x the 4-week avg triggers EXPENSE_SPIKE alert."""
    project_id = str(uuid.uuid4())

    projects = [
        {
            "id": project_id,
            "name": "Delta Build",
            "status": "active",
        }
    ]

    # 4-week historical avg: $500/week; this week: $1,500 (3x)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday of current week

    expenses = []
    # Three previous weeks: $500 each
    for w in range(1, 5):
        week_date = (week_start - timedelta(weeks=w)).isoformat()
        expenses.append(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "amount": "500.00",
                "currency": "USD",
                "expense_date": week_date,
            }
        )
    # This week: $1,500
    expenses.append(
        {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "amount": "1500.00",
            "currency": "USD",
            "expense_date": week_start.isoformat(),
        }
    )

    deps, _ = _make_deps(suggestions=[], projects=projects, expenses=expenses)

    alerts = await check_expense_spike(deps)

    spike_alerts = [a for a in alerts if a.anomaly_type == "EXPENSE_SPIKE"]
    assert len(spike_alerts) >= 1
    alert = spike_alerts[0]
    assert alert.entity_id == project_id


@pytest.mark.asyncio
async def test_no_expense_spike_below_threshold() -> None:
    """Project expense 1.5x the weekly avg does NOT trigger EXPENSE_SPIKE."""
    project_id = str(uuid.uuid4())

    projects = [{"id": project_id, "name": "Epsilon Build", "status": "active"}]

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    expenses = []
    # Four previous weeks: $1,000 each → avg $1,000
    for w in range(1, 5):
        week_date = (week_start - timedelta(weeks=w)).isoformat()
        expenses.append(
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "amount": "1000.00",
                "currency": "USD",
                "expense_date": week_date,
            }
        )
    # This week: $1,500 (1.5x — below 2x threshold)
    expenses.append(
        {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "amount": "1500.00",
            "currency": "USD",
            "expense_date": week_start.isoformat(),
        }
    )

    deps, _ = _make_deps(suggestions=[], projects=projects, expenses=expenses)

    alerts = await check_expense_spike(deps)

    spike_alerts = [a for a in alerts if a.anomaly_type == "EXPENSE_SPIKE"]
    assert len(spike_alerts) == 0


# ---------------------------------------------------------------------------
# check_margin_compression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_margin_compression_detected() -> None:
    """Project gross margin < 20% (was >30% last month) triggers MARGIN_COMPRESSION."""
    project_id = str(uuid.uuid4())

    # Current period: revenue $10,000, cost $8,500 → GM = 15%
    # Previous period: revenue $10,000, cost $6,500 → GM = 35%
    projects = [
        {
            "id": project_id,
            "name": "Zeta Project",
            "status": "active",
            "current_revenue": "10000.00",
            "current_cost": "8500.00",
            "prev_revenue": "10000.00",
            "prev_cost": "6500.00",
        }
    ]

    deps, _ = _make_deps(suggestions=[], projects=projects)

    alerts = await check_margin_compression(deps)

    margin_alerts = [a for a in alerts if a.anomaly_type == "MARGIN_COMPRESSION"]
    assert len(margin_alerts) >= 1
    alert = margin_alerts[0]
    assert alert.entity_id == project_id


@pytest.mark.asyncio
async def test_no_margin_alert_healthy() -> None:
    """Project with GM > 30% does NOT trigger MARGIN_COMPRESSION."""
    project_id = str(uuid.uuid4())

    # Revenue $10,000, cost $6,500 → GM = 35%
    projects = [
        {
            "id": project_id,
            "name": "Healthy Project",
            "status": "active",
            "current_revenue": "10000.00",
            "current_cost": "6500.00",
            "prev_revenue": "10000.00",
            "prev_cost": "5000.00",
        }
    ]

    deps, _ = _make_deps(suggestions=[], projects=projects)

    alerts = await check_margin_compression(deps)

    margin_alerts = [a for a in alerts if a.anomaly_type == "MARGIN_COMPRESSION"]
    assert len(margin_alerts) == 0


# ---------------------------------------------------------------------------
# check_fx_exposure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fx_exposure_detected() -> None:
    """Net AR-AP exposure > $10,000 equivalent triggers FX_EXPOSURE alert."""
    # Simulate $15,000 GBP net exposure with GBP/USD = 1.27 => $19,050 exposure
    invoices = [
        {
            "id": str(uuid.uuid4()),
            "total": "15000.00",
            "currency": "GBP",
            "status": "sent",
            "base_total": "19050.00",  # USD equivalent
        }
    ]

    deps, _ = _make_deps(suggestions=[], invoices=invoices)

    alerts = await check_fx_exposure(deps)

    fx_alerts = [a for a in alerts if a.anomaly_type == "FX_EXPOSURE"]
    assert len(fx_alerts) >= 1


@pytest.mark.asyncio
async def test_no_fx_alert_below_threshold() -> None:
    """Net FX exposure < $10,000 does NOT trigger FX_EXPOSURE."""
    # $7,000 USD — below threshold, base currency (no FX risk)
    invoices = [
        {
            "id": str(uuid.uuid4()),
            "total": "7000.00",
            "currency": "EUR",
            "status": "sent",
            "base_total": "7560.00",  # USD equivalent — under $10k
        }
    ]

    deps, _ = _make_deps(suggestions=[], invoices=invoices)

    alerts = await check_fx_exposure(deps)

    fx_alerts = [a for a in alerts if a.anomaly_type == "FX_EXPOSURE"]
    assert len(fx_alerts) == 0


# ---------------------------------------------------------------------------
# check_retainer_under_utilization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retainer_under_utilization_detected() -> None:
    """Retainer client billed <50% of retainer value in last 3 months => alert."""
    engagement_id = str(uuid.uuid4())

    engagements = [
        {
            "id": engagement_id,
            "name": "Eta Corp — Monthly Retainer",
            "status": "active",
            "billing_arrangement": "retainer",
            "retainer_amount": "5000.00",
            "currency": "USD",
        }
    ]
    # 3 months x $5,000 retainer = $15,000 expected; only $6,000 billed (40%)
    invoices = [
        {
            "id": str(uuid.uuid4()),
            "engagement_id": engagement_id,
            "total": "6000.00",
            "currency": "USD",
            "status": "paid",
            "issued_at": (date.today() - timedelta(days=30)).isoformat(),
        }
    ]

    deps, _ = _make_deps(suggestions=[], engagements=engagements, invoices=invoices)

    alerts = await check_retainer_under_utilization(deps)

    retainer_alerts = [a for a in alerts if a.anomaly_type == "RETAINER_UNDER_UTILIZATION"]
    assert len(retainer_alerts) >= 1
    alert = retainer_alerts[0]
    assert alert.entity_id == engagement_id


@pytest.mark.asyncio
async def test_no_retainer_alert_when_fully_utilized() -> None:
    """Retainer client billed >= 50% of retainer value does NOT trigger alert."""
    engagement_id = str(uuid.uuid4())

    engagements = [
        {
            "id": engagement_id,
            "name": "Theta Corp — Monthly Retainer",
            "status": "active",
            "billing_arrangement": "retainer",
            "retainer_amount": "5000.00",
            "currency": "USD",
        }
    ]
    # 3 months x $5,000 = $15,000; $9,000 billed (60% — above 50% threshold)
    invoices = [
        {
            "id": str(uuid.uuid4()),
            "engagement_id": engagement_id,
            "total": "9000.00",
            "currency": "USD",
            "status": "paid",
            "issued_at": (date.today() - timedelta(days=30)).isoformat(),
        }
    ]

    deps, _ = _make_deps(suggestions=[], engagements=engagements, invoices=invoices)

    alerts = await check_retainer_under_utilization(deps)

    retainer_alerts = [a for a in alerts if a.anomaly_type == "RETAINER_UNDER_UTILIZATION"]
    assert len(retainer_alerts) == 0


# ---------------------------------------------------------------------------
# check_overdue_escalation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overdue_escalation_detected() -> None:
    """Invoice overdue > 60 days with no collection activity => OVERDUE_ESCALATION."""
    invoice_id = str(uuid.uuid4())
    due_date = (date.today() - timedelta(days=65)).isoformat()

    invoices = [
        {
            "id": invoice_id,
            "invoice_number": "INV-001",
            "total": "5000.00",
            "currency": "USD",
            "due_date": due_date,
            "status": "overdue",
            "client_id": str(uuid.uuid4()),
        }
    ]
    # No collection activities logged
    collection_activities: list[dict] = []

    deps, _ = _make_deps(
        suggestions=[], invoices=invoices, collection_activities=collection_activities
    )

    alerts = await check_overdue_escalation(deps)

    overdue_alerts = [a for a in alerts if a.anomaly_type == "OVERDUE_ESCALATION"]
    assert len(overdue_alerts) >= 1
    alert = overdue_alerts[0]
    assert alert.entity_id == invoice_id


@pytest.mark.asyncio
async def test_no_overdue_escalation_when_collection_logged() -> None:
    """Invoice overdue > 60 days WITH recent collection activity => no alert."""
    invoice_id = str(uuid.uuid4())
    due_date = (date.today() - timedelta(days=65)).isoformat()

    invoices = [
        {
            "id": invoice_id,
            "invoice_number": "INV-002",
            "total": "5000.00",
            "currency": "USD",
            "due_date": due_date,
            "status": "overdue",
            "client_id": str(uuid.uuid4()),
        }
    ]
    collection_activities = [
        {
            "id": str(uuid.uuid4()),
            "invoice_id": invoice_id,
            "activity_type": "email_sent",
            "created_at": (date.today() - timedelta(days=5)).isoformat(),
        }
    ]

    deps, _ = _make_deps(
        suggestions=[], invoices=invoices, collection_activities=collection_activities
    )

    alerts = await check_overdue_escalation(deps)

    overdue_alerts = [a for a in alerts if a.anomaly_type == "OVERDUE_ESCALATION"]
    assert len(overdue_alerts) == 0


@pytest.mark.asyncio
async def test_no_overdue_escalation_when_recent_invoice() -> None:
    """Invoice overdue but only 30 days old does NOT trigger OVERDUE_ESCALATION."""
    invoice_id = str(uuid.uuid4())
    due_date = (date.today() - timedelta(days=30)).isoformat()

    invoices = [
        {
            "id": invoice_id,
            "invoice_number": "INV-003",
            "total": "3000.00",
            "currency": "USD",
            "due_date": due_date,
            "status": "overdue",
            "client_id": str(uuid.uuid4()),
        }
    ]

    deps, _ = _make_deps(suggestions=[], invoices=invoices, collection_activities=[])

    alerts = await check_overdue_escalation(deps)

    overdue_alerts = [a for a in alerts if a.anomaly_type == "OVERDUE_ESCALATION"]
    assert len(overdue_alerts) == 0


# ---------------------------------------------------------------------------
# generate_alert_narrative — LLM fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_alert_narrative_fallback() -> None:
    """When the LLM call raises, generate_alert_narrative returns the fallback template."""
    context = {
        "entity_name": "Acme Corp",
        "days": "52",
        "threshold": "45",
    }

    with patch(
        "app.agents.intelligence_agent.make_async_llm_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        mock_client_factory.return_value = mock_client

        result = await generate_alert_narrative("UNBILLED_ENGAGEMENT", context)

    assert isinstance(result, str)
    assert len(result) > 0
    # Fallback must not be an empty string or an error message
    assert "error" not in result.lower() or "Acme" in result or "engagement" in result.lower()


@pytest.mark.asyncio
async def test_generate_alert_narrative_success() -> None:
    """When LLM returns a response, narrative is the LLM output."""
    context = {"entity_name": "Beta Corp", "days": "70", "threshold": "60"}
    expected_narrative = "Invoice for Beta Corp is 70 days overdue with no collection activity."

    with patch(
        "app.agents.intelligence_agent.make_async_llm_client"
    ) as mock_client_factory:
        mock_choice = MagicMock()
        mock_choice.message.content = expected_narrative
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_factory.return_value = mock_client

        result = await generate_alert_narrative("OVERDUE_ESCALATION", context)

    assert result == expected_narrative


# ---------------------------------------------------------------------------
# _run_anomaly_checks — graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_anomalies_graceful_degradation() -> None:
    """If one anomaly check raises, the worker catches it and continues.

    All remaining checks still run; the function does not propagate the exception.
    """
    deps, db = _make_deps()

    # Make the DB raise on any table access to simulate a mid-flight error
    # for the unbilled_engagement check, but let others pass via the suggestions mock
    call_count = {"n": 0}
    def _failing_table(name: str) -> MagicMock:
        call_count["n"] += 1
        if name == "engagements":
            raise RuntimeError("Simulated DB error")
        return MagicMock()

    db.table.side_effect = _failing_table

    # Should NOT raise — exceptions per check are caught
    result = await _run_anomaly_checks(deps)

    # Worker continues — result is the number of alerts written (may be 0)
    assert isinstance(result, int)
    assert result >= 0
