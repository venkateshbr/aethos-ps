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


def test_semantic_router_recognizes_model_and_observability_status() -> None:
    route = AtlasSemanticIntentRouter().classify(
        "Show model provider status, Langfuse observability, and operational alerts for Atlas."
    )

    assert route is not None
    assert route.intent == "configuration_telemetry"
    assert route.confidence >= 0.72
