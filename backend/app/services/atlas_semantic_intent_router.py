"""Semantic intent routing for Atlas operational finance prompts.

The router is deterministic and local: it does not call an LLM. It maps user
language into Aethos operational intents using concept groups, action-mode
signals, negation handling, entities, and a confidence score. High-confidence
routes can be answered by Aethos services before the request reaches the model
runtime; low-confidence prompts fall back to Hermes/basic Atlas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

AtlasActionMode = Literal["read", "explain", "prepare", "controlled_action"]

AtlasIntentName = Literal[
    "cosec_reminders",
    "configuration_telemetry",
    "approval_controls",
    "finance_ops_control_room",
    "finance_ops_action_plan",
    "finance_ops_check",
    "time_log",
    "capped_tax_engagement",
    "invoice_drilldown",
    "brightwater_retainer",
    "brightwater_milestone",
    "brightwater_payroll",
    "single_bill_drilldown",
    "bill_pay_run",
    "alderton_family_office",
    "alderton_scope_creep",
    "thornton_usd_billing",
    "thornton_cosec_instruction",
    "close_readiness",
    "period_lock",
    "statement_package",
    "year_end_close",
    "trial_balance",
    "reversal_packet",
    "decision_trail",
    "operational_health",
    "documents_audit",
    "manual_journal",
    "manual_journal_decision_trail",
    "management_pack",
    "management_pack_drilldown",
    "delivery_context",
    "p2p_payment_risk",
    "vendor_invoice_intake",
    "o2c_readiness",
    "collections",
    "revenue_recognition",
    "billing_run",
    "series_a",
]


@dataclass(frozen=True)
class AtlasIntentRoute:
    intent: AtlasIntentName
    confidence: float
    action_mode: AtlasActionMode
    action_required: bool
    entities: dict[str, str]
    matched_concepts: list[str]
    negation_detected: bool
    reason: str


@dataclass(frozen=True)
class _IntentDefinition:
    intent: AtlasIntentName
    concept_groups: tuple[tuple[str, ...], ...]
    priority: int = 0
    action_required: bool = False
    min_concept_hits: int | None = None
    anchor_phrases: tuple[str, ...] = ()


_CLIENT_TERMS = {
    "alderton": "Alderton",
    "brightwater": "Brightwater",
    "forster": "Forster",
    "nexus": "Nexus",
    "thornton": "Thornton",
}

_READ_TERMS = (
    "show",
    "summarize",
    "summarise",
    "review",
    "check",
    "read",
    "list",
    "which",
    "what",
    "who",
    "why",
    "status",
    "tell me",
)
_EXPLAIN_TERMS = ("explain", "describe", "walk me through", "how does", "why")
_PREPARE_TERMS = (
    "prepare",
    "draft",
    "create",
    "route",
    "log",
    "propose",
    "build",
    "generate",
)
_CONTROLLED_ACTION_TERMS = (
    "approve",
    "post",
    "send",
    "pay",
    "lock",
    "submit",
    "export",
    "settle",
)
_NEGATION_PATTERNS = (
    re.compile(r"\bdo not\b", re.IGNORECASE),
    re.compile(r"\bdon'?t\b", re.IGNORECASE),
    re.compile(
        r"\bwithout\s+(?:creating|preparing|drafting|posting|sending|approving|paying|locking)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bno need to\s+(?:create|prepare|draft|post|send|approve|pay|lock)\b", re.IGNORECASE
    ),
    re.compile(r"\bnot\s+(?:create|prepare|draft|post|send|approve|pay|lock)\b", re.IGNORECASE),
)

_DEFINITIONS: tuple[_IntentDefinition, ...] = (
    _IntentDefinition(
        "manual_journal",
        (
            ("manual journal", "journal entry", "journal"),
            ("fx", "foreign currency", "base currency", "base-currency", "sgd", "usd", "gbp"),
            _PREPARE_TERMS,
        ),
        priority=100,
        action_required=True,
        anchor_phrases=("route it to inbox", "before posting", "prepare an sgd"),
    ),
    _IntentDefinition(
        "finance_ops_action_plan",
        (
            ("finance ops", "finance operations", "ops manager"),
            ("work item", "work items", "action plan", "next actions"),
            ("billing", "payments", "collections", "close", "journal"),
            _PREPARE_TERMS,
        ),
        priority=95,
        action_required=True,
        anchor_phrases=("create finance ops", "recommended finance ops action plan"),
    ),
    _IntentDefinition(
        "billing_run",
        (
            ("billing run", "draft invoice lines", "invoice draft", "billing draft"),
            ("nexus", "billing", "invoice", "wip"),
            _PREPARE_TERMS,
        ),
        priority=90,
        action_required=True,
    ),
    _IntentDefinition(
        "bill_pay_run",
        (
            ("bill pay", "bill-pay", "payment run", "payment batch"),
            ("vendor bill", "due", "approved bill", "payables"),
            _PREPARE_TERMS,
        ),
        priority=90,
        action_required=True,
    ),
    _IntentDefinition(
        "time_log",
        (
            ("time", "hours", "timesheet"),
            (
                "project",
                "cfo advisory",
                "board pack",
                "cash flow modelling",
                "cash flow modeling",
            ),
            ("log", "record", "create", "prepare"),
        ),
        priority=88,
        action_required=True,
        anchor_phrases=("log 4.5 hours", "log time entry", "billable hours"),
    ),
    _IntentDefinition(
        "capped_tax_engagement",
        (
            ("corporation tax return", "tax return", "tax engagement"),
            ("cap", "capped", "fixed fee", "overrun"),
            _PREPARE_TERMS,
        ),
        priority=86,
        action_required=True,
    ),
    _IntentDefinition(
        "series_a",
        (
            ("series a", "funding round", "capital raise"),
            ("milestone", "success fee", "invoice"),
            ("thornton", "usd", "closing"),
        ),
        priority=84,
    ),
    _IntentDefinition(
        "thornton_cosec_instruction",
        (
            ("thornton",),
            (
                "cosec instruction",
                "company secretarial instruction",
                "statutory instruction",
                "filing instruction",
            ),
            ("company change", "ap01", "director", "filing", "project work item"),
        ),
        priority=83,
    ),
    _IntentDefinition(
        "vendor_invoice_intake",
        (
            ("vendor invoice", "supplier invoice", "subcontractor invoice", "forster"),
            ("brightwater", "duplicate", "po", "service order", "bill"),
            ("extract", "intake", "upload", "review"),
        ),
        priority=82,
    ),
    _IntentDefinition(
        "configuration_telemetry",
        (
            ("configuration", "settings", "model", "provider", "runtime", "langfuse"),
            ("telemetry", "observability", "operational alerts", "provider status"),
            ("atlas", "ai", "openrouter", "hermes"),
        ),
        priority=80,
        anchor_phrases=("langfuse", "operational alerts", "model provider"),
    ),
    _IntentDefinition(
        "finance_ops_control_room",
        (
            ("finance ops", "finance operations", "ops manager", "scheduled"),
            ("cadence", "schedule", "last run", "control room", "approval boundary"),
            ("approval", "open plans", "escalation", "current cadence"),
        ),
        priority=79,
        anchor_phrases=("current cadence", "approval boundary"),
    ),
    _IntentDefinition(
        "finance_ops_check",
        (
            ("finance ops", "finance operations", "ops manager"),
            ("billing", "payment", "payments"),
            ("collections", "close", "journal"),
        ),
        priority=78,
    ),
    _IntentDefinition(
        "approval_controls",
        (
            ("approval", "approve", "approver", "owner", "persona", "role"),
            ("inbox", "threshold", "segregation", "authority"),
            ("control", "policy", "high risk", "high-risk"),
        ),
        priority=76,
    ),
    _IntentDefinition(
        "cosec_reminders",
        (
            ("cosec", "company secretarial", "statutory filing", "annual confirmation", "filing"),
            ("reminder", "due", "deadline", "calendar", "obligation", "filings"),
            ("approval", "client", "send", "evidence", "missing"),
        ),
        priority=75,
        min_concept_hits=2,
    ),
    _IntentDefinition(
        "invoice_drilldown",
        (
            ("inv-1001", "invoice 1001", "invoice drilldown"),
            ("due date", "balance", "payment link", "reminder history"),
        ),
        priority=74,
        min_concept_hits=1,
    ),
    _IntentDefinition(
        "single_bill_drilldown",
        (
            ("bill-1001", "bill 1001", "single bill"),
            ("vendor invoice number", "due date", "po", "approval", "payment readiness"),
        ),
        priority=74,
        min_concept_hits=1,
    ),
    _IntentDefinition(
        "brightwater_retainer",
        (("brightwater",), ("monthly retainer", "retainer"), ("invoice", "billing", "draft")),
        priority=72,
    ),
    _IntentDefinition(
        "brightwater_milestone",
        (
            ("brightwater",),
            ("annual accounts", "accounts milestone"),
            ("milestone", "invoice", "billing"),
        ),
        priority=72,
    ),
    _IntentDefinition(
        "brightwater_payroll",
        (("brightwater",), ("payroll", "employee count"), ("invoice", "billing", "per employee")),
        priority=72,
    ),
    _IntentDefinition(
        "alderton_family_office",
        (
            ("alderton family office", "alderton"),
            ("structure", "group", "family office"),
            ("engagements", "service lines", "billing models", "projects"),
        ),
        priority=70,
    ),
    _IntentDefinition(
        "alderton_scope_creep",
        (
            ("alderton", "bespoke tax return", "tax return"),
            ("scope creep", "scope", "overrun", "margin"),
            ("fee adjustment", "supplemental fee", "actual time"),
        ),
        priority=70,
    ),
    _IntentDefinition(
        "thornton_usd_billing",
        (
            ("thornton",),
            ("usd", "dollars", "foreign currency"),
            ("gbp", "sterling", "base currency", "cash", "ar"),
        ),
        priority=70,
    ),
    _IntentDefinition(
        "close_readiness",
        (
            ("pre close", "pre-close", "close readiness", "month end", "month-end"),
            ("ar", "ap", "wip", "journals", "close tasks"),
            ("blockers", "ready", "checks"),
        ),
        priority=69,
    ),
    _IntentDefinition(
        "period_lock",
        (
            ("period lock", "period-lock", "lock june", "lock period"),
            ("readiness", "blockers", "override"),
            ("june 2026", "close"),
        ),
        priority=69,
    ),
    _IntentDefinition(
        "statement_package",
        (
            ("financial statement package", "statement package", "financial statements"),
            ("trial balance", "balance sheet", "income statement", "cash flow"),
            ("variance", "may 2026", "june 2026", "statutory pack"),
        ),
        priority=68,
    ),
    _IntentDefinition(
        "year_end_close",
        (
            ("year end close", "year-end close", "fy2026 close"),
            ("retained earnings", "profit and loss", "p&l"),
            ("locked periods", "duplicate close", "posting"),
        ),
        priority=68,
    ),
    _IntentDefinition(
        "trial_balance",
        (
            ("trial balance", "tb"),
            ("debits", "credits", "suspense", "unbalanced"),
            ("largest movements", "account movements", "as of"),
        ),
        priority=67,
        min_concept_hits=1,
    ),
    _IntentDefinition(
        "reversal_packet",
        (
            ("reversal", "reverse journal", "reversal packet"),
            ("manual journal", "posted journal", "open period"),
            ("reason", "flip", "debit", "credit"),
        ),
        priority=67,
    ),
    _IntentDefinition(
        "decision_trail",
        (
            ("decision trail", "approval history", "audit trail"),
            ("inbox", "reviewer", "actor", "timestamp"),
            ("approved", "rejected", "waived", "before after", "before/after"),
        ),
        priority=66,
    ),
    _IntentDefinition(
        "operational_health",
        (
            ("operational health", "platform health", "health status"),
            ("public endpoint", "abuse", "rate limit", "background failure"),
            ("workflow failure", "agent failure", "degraded"),
        ),
        priority=66,
        min_concept_hits=1,
    ),
    _IntentDefinition(
        "documents_audit",
        (
            ("documents", "source evidence", "document audit"),
            ("engagements", "bills", "invoices", "journals"),
            ("extraction", "linked", "inbox decision", "evidence"),
        ),
        priority=65,
    ),
    _IntentDefinition(
        "manual_journal_decision_trail",
        (
            ("manual journal", "journal proposal", "journal review"),
            ("proposal", "approval", "decision", "review"),
            ("balance", "account validity", "period lock", "evidence"),
        ),
        priority=64,
    ),
    _IntentDefinition(
        "management_pack_drilldown",
        (
            ("management pack", "close task blockers", "draft journals"),
            ("blockers", "drilldown", "close task"),
            ("draft journals", "remaining", "resolve"),
        ),
        priority=64,
    ),
    _IntentDefinition(
        "management_pack",
        (
            ("management pack", "management report", "management reporting"),
            ("june 2026", "may 2026", "variance", "month end"),
            ("revenue", "expenses", "margin", "utilization", "utilisation"),
        ),
        priority=63,
    ),
    _IntentDefinition(
        "delivery_context",
        (
            ("utilization", "utilisation", "wip", "people", "delivery"),
            ("alice", "employee", "resource", "allocation"),
            ("unbilled", "invoice ready", "client", "project"),
        ),
        priority=62,
    ),
    _IntentDefinition(
        "p2p_payment_risk",
        (
            ("vendor bills", "ap", "accounts payable", "payment approval packet"),
            ("due soon", "payment risk", "duplicate", "bank detail", "blocked"),
            ("approval", "payment batch", "cash impact"),
        ),
        priority=61,
    ),
    _IntentDefinition(
        "o2c_readiness",
        (
            ("order to cash", "order-to-cash", "o2c"),
            ("service catalogue", "rate card", "tax", "billing setup"),
            ("readiness", "invoice", "revenue", "billing"),
        ),
        priority=60,
    ),
    _IntentDefinition(
        "collections",
        (
            ("collections", "customer reminders", "overdue invoices"),
            ("reminders", "customers", "aging", "ageing"),
            ("cooldown", "dispute", "blocker", "next action"),
        ),
        priority=59,
    ),
    _IntentDefinition(
        "revenue_recognition",
        (
            ("revenue recognition", "recognized revenue", "recognised revenue"),
            ("recognized", "recognised", "deferred", "milestone"),
            ("period", "june 2026", "service line"),
        ),
        priority=58,
    ),
)


class AtlasSemanticIntentRouter:
    """Classify an Atlas prompt into a high-level operational intent."""

    def classify(self, message: str) -> AtlasIntentRoute | None:
        normalized = _normalize(message)
        if not normalized:
            return None
        action_mode = _action_mode(normalized)
        negation_detected = _negation_detected(message)
        entities = _entities(normalized)
        candidates: list[AtlasIntentRoute] = []
        for definition in _DEFINITIONS:
            route = _score_definition(
                definition=definition,
                normalized=normalized,
                entities=entities,
                action_mode=action_mode,
                negation_detected=negation_detected,
            )
            if route is not None:
                candidates.append(route)
        if not candidates:
            return None
        candidates.sort(
            key=lambda route: (
                route.confidence,
                _priority(route.intent),
                len(route.matched_concepts),
            ),
            reverse=True,
        )
        return candidates[0]


def _score_definition(
    *,
    definition: _IntentDefinition,
    normalized: str,
    entities: dict[str, str],
    action_mode: AtlasActionMode,
    negation_detected: bool,
) -> AtlasIntentRoute | None:
    matched: list[str] = []
    for group in definition.concept_groups:
        match = _first_match(normalized, group)
        if match:
            matched.append(match)
    min_hits = definition.min_concept_hits or max(2, min(len(definition.concept_groups), 3))
    if len(matched) < min_hits:
        return None

    concept_ratio = len(matched) / max(len(definition.concept_groups), 1)
    anchor_hits = sum(1 for phrase in definition.anchor_phrases if _contains(normalized, phrase))
    entity_bonus = 0.05 if entities.get("client_name") else 0.0
    confidence = 0.22 + (0.58 * concept_ratio) + min(anchor_hits, 2) * 0.05 + entity_bonus
    requested_action_negated = _matched_action_is_negated(normalized, matched)

    if definition.action_required:
        if action_mode in {"prepare", "controlled_action"} and not requested_action_negated:
            confidence += 0.1
        else:
            confidence -= 0.3
    elif action_mode == "explain":
        confidence += 0.03

    if requested_action_negated and definition.action_required:
        confidence -= 0.2
    confidence = max(0.0, min(0.99, confidence))
    if confidence < 0.5:
        return None

    return AtlasIntentRoute(
        intent=definition.intent,
        confidence=round(confidence, 3),
        action_mode=action_mode,
        action_required=definition.action_required,
        entities=entities,
        matched_concepts=matched,
        negation_detected=negation_detected,
        reason=f"matched {len(matched)}/{len(definition.concept_groups)} concept groups",
    )


def _priority(intent: AtlasIntentName) -> int:
    for definition in _DEFINITIONS:
        if definition.intent == intent:
            return definition.priority
    return 0


def _normalize(value: str) -> str:
    lowered = value.lower().replace("p&l", "profit and loss")
    normalized = re.sub(r"[^a-z0-9$./:-]+", " ", lowered)
    return " ".join(normalized.split())


def _term(value: str) -> str:
    return _normalize(value)


def _contains(text: str, phrase: str) -> bool:
    needle = _term(phrase)
    if not needle:
        return False
    if re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", text):
        return True
    return needle in text


def _first_match(text: str, terms: tuple[str, ...]) -> str | None:
    for term in terms:
        if _contains(text, term):
            return term
    return None


def _action_mode(text: str) -> AtlasActionMode:
    if _first_match(text, _PREPARE_TERMS):
        return "prepare"
    if _first_match(text, _CONTROLLED_ACTION_TERMS):
        return "controlled_action"
    if _first_match(text, _EXPLAIN_TERMS):
        return "explain"
    if _first_match(text, _READ_TERMS):
        return "read"
    return "read"


def _negation_detected(message: str) -> bool:
    return any(pattern.search(message) for pattern in _NEGATION_PATTERNS)


def _matched_action_is_negated(text: str, matched_concepts: list[str]) -> bool:
    """Return true only when the action for this candidate is negated.

    A prompt can request a safe preparatory action while explicitly forbidding a
    different downstream action, for example: create an action plan, but do not
    approve payments. Treating any negation in the prompt as a veto caused the
    requested action-plan route to lose to the read-only finance-ops route.
    """
    action_terms = set(_PREPARE_TERMS) | set(_CONTROLLED_ACTION_TERMS)
    gerunds = {
        "approve": "approving",
        "build": "building",
        "create": "creating",
        "draft": "drafting",
        "export": "exporting",
        "generate": "generating",
        "lock": "locking",
        "log": "logging",
        "pay": "paying",
        "post": "posting",
        "prepare": "preparing",
        "propose": "proposing",
        "route": "routing",
        "send": "sending",
        "settle": "settling",
        "submit": "submitting",
    }
    for action in matched_concepts:
        if action not in action_terms:
            continue
        escaped = re.escape(action)
        if re.search(
            rf"\b(?:do not|don t|dont|no need to|not)\s+{escaped}\b",
            text,
        ):
            return True
        gerund = gerunds.get(action)
        if gerund and re.search(rf"\bwithout\s+{re.escape(gerund)}\b", text):
            return True
    return False


def _entities(text: str) -> dict[str, str]:
    entities: dict[str, str] = {}
    for token, name in _CLIENT_TERMS.items():
        if _contains(text, token):
            entities["client_name"] = name
            break
    invoice = re.search(r"\binv[- ]?(\d+)\b", text, re.IGNORECASE)
    if invoice:
        entities["invoice_number"] = f"INV-{invoice.group(1)}"
    bill = re.search(r"\bbill[- ]?(\d+)\b", text, re.IGNORECASE)
    if bill:
        entities["bill_number"] = f"BILL-{bill.group(1)}"
    currency = re.search(r"\b(usd|gbp|sgd|eur|aud|inr)\b", text, re.IGNORECASE)
    if currency:
        entities["currency"] = currency.group(1).upper()
    amount = re.search(
        r"\b(?:usd|gbp|sgd|eur|aud|inr|s\$)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\b", text, re.IGNORECASE
    )
    if amount:
        entities["amount"] = amount.group(1).replace(",", "")
    period = re.search(r"\b(20\d{2}-\d{2})\b", text)
    if period:
        entities["period"] = period.group(1)
    return entities
