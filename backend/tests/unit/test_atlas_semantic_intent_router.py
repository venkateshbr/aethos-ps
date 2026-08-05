from __future__ import annotations

import pytest

from app.services.atlas_semantic_intent_router import AtlasSemanticIntentRouter

pytestmark = pytest.mark.unit


def test_semantic_router_handles_cosec_paraphrase() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Which statutory filings are due for Thornton, and what needs approval "
        "before client reminders go out?"
    )

    assert route is not None
    assert route.intent == "cosec_reminders"
    assert route.confidence >= 0.72
    assert route.entities["client_name"] == "Thornton"


def test_semantic_router_does_not_create_negated_finance_ops_work_items() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Do not create Finance Ops work items; just explain the current cadence, "
        "approval boundary, last run, and open plans."
    )

    assert route is not None
    assert route.intent == "finance_ops_control_room"
    assert route.action_mode == "prepare"
    assert route.negation_detected is True
    assert route.confidence >= 0.72


def test_semantic_router_keeps_requested_action_plan_when_only_downstream_actions_are_negated() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Create the next recommended finance ops work items for 2026-06. "
        "Create at most five manager-reviewed work items. "
        "Route the manager action plan to Inbox for review. "
        "Do not approve invoices, payments, journals, or emails directly."
    )

    assert route is not None
    assert route.intent == "finance_ops_action_plan"
    assert route.action_mode == "prepare"
    assert route.negation_detected is True
    assert route.confidence >= 0.80


def test_semantic_router_routes_away_when_the_plan_action_itself_is_negated() -> None:
    # #381 mirror: when the *requested* action (create the plan) is the negated
    # one, the scoped-negation check must route away from the action-plan intent.
    route = AtlasSemanticIntentRouter().classify(
        "Do not create any finance ops work items for 2026-06 — just show me the "
        "current status."
    )
    assert route is None or route.intent != "finance_ops_action_plan"


def test_semantic_router_recognizes_controlled_manual_journal() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Prepare an SGD 18,000 dividend income journal for Alderton Trust for "
        "June 2026. Show the GBP base-currency impact, FX rate provenance, "
        "required approval role, and route it to Inbox before posting."
    )

    assert route is not None
    assert route.intent == "manual_journal"
    assert route.action_mode == "prepare"
    assert route.confidence >= 0.80
    assert route.entities["client_name"] == "Alderton"
    assert route.entities["currency"] == "SGD"


def test_semantic_router_recognizes_explicit_project_time_log() -> None:
    route = AtlasSemanticIntentRouter().classify(
        'Log exactly 4.5 billable hours on project "Nexus Advisory" for '
        '2026-07-11. Use this exact description: "Board pack review". '
        "Use the log_time_entry tool and create the review task."
    )

    assert route is not None
    assert route.intent == "time_log"
    assert route.action_mode == "prepare"
    assert route.action_required is True
    assert route.confidence >= 0.80


def test_semantic_router_prefers_single_bill_for_demo_guide_prompt() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Review bill BILL-1001. Show due date, amount, vendor invoice number, "
        "coding status, source document, duplicate signals, PO/service-order "
        "match, approval state, payment readiness, existing batch status, and "
        "recommended next action."
    )

    assert route is not None
    assert route.intent == "single_bill_drilldown"


def test_semantic_router_prefers_management_pack_for_demo_guide_prompt() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Give me the June 2026 month-end management pack. Explain the major "
        "variances versus May 2026, show revenue, expenses, project margin, "
        "utilization, AR/AP movement, journals, close task blockers, draft "
        "journals, and remaining close blockers. Do not post journals or lock "
        "the period."
    )

    assert route is not None
    assert route.intent == "management_pack"


def test_semantic_router_recognizes_demo_revenue_explanation_prompt() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Explain how Nexus June revenue is recognized across fixed-fee milestone, "
        "retainer, T&M advisory WIP, and expenses. Tie the explanation to "
        "invoice-backed journals and Project P&L."
    )

    assert route is not None
    assert route.intent == "revenue_recognition"


def test_semantic_router_recognizes_model_and_observability_status() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Show model provider status, Langfuse observability, and operational alerts for Atlas."
    )

    assert route is not None
    assert route.intent == "configuration_telemetry"
    assert route.confidence >= 0.72
