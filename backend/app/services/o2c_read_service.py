"""Read-only O2C collections and invoice drilldown service."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.agents.collections_agent import collection_tone_for_days
from app.models.collections_policy import CollectionsPolicyConfig
from app.services.collections_policy_service import (
    default_collections_policy,
    row_to_collections_policy,
)
from supabase import Client

logger = logging.getLogger(__name__)

_COLLECTION_SUGGESTION_STATUSES = (
    "pending",
    "approved",
    "approved_with_edits",
    "auto_applied",
    "rejected",
    "expired",
)


class O2CReadService:
    """Tenant-scoped read model for customer collections and invoice state."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def collections_read_pack(
        self,
        *,
        invoice_id: str | None = None,
        invoice_number: str | None = None,
        client_id: str | None = None,
        client_name: str | None = None,
        status: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        capped_limit = max(1, min(limit, 100))
        client_ids = self._client_ids_for_name(client_name) if client_name else None
        invoice_rows = self._fetch_invoice_rows(
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            client_id=client_id,
            client_ids=client_ids,
            status=status,
            limit=capped_limit,
        )
        invoice_ids = [str(row["id"]) for row in invoice_rows]
        payments_by_invoice = self._payments_by_invoice(invoice_ids)
        reminders_by_invoice = self._reminders_by_invoice(invoice_ids)
        policies = self._collections_policies()

        invoices = [
            self._invoice_summary(
                row,
                payments=payments_by_invoice.get(str(row["id"]), []),
                reminders=reminders_by_invoice.get(str(row["id"]), []),
                policy=self._effective_policy(str(row.get("client_id") or ""), policies),
            )
            for row in invoice_rows
        ]
        customers = self._customer_summaries(invoices)
        totals = self._totals(invoices, customers)

        return {
            "tenant_id": self.tenant_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "query": {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "client_id": client_id,
                "client_name": client_name,
                "status": status,
                "limit": capped_limit,
            },
            "totals": totals,
            "customers": customers,
            "invoices": invoices,
        }

    def _client_ids_for_name(self, client_name: str | None) -> list[str]:
        raw = (client_name or "").strip().lower()
        if not raw:
            return []
        rows = (
            self.db.table("clients")
            .select("id,name")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .limit(100)
            .execute()
            .data
            or []
        )
        return [
            str(row["id"])
            for row in rows
            if raw in str(row.get("name") or "").lower()
        ]

    def _fetch_invoice_rows(
        self,
        *,
        invoice_id: str | None,
        invoice_number: str | None,
        client_id: str | None,
        client_ids: list[str] | None,
        status: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if client_ids is not None and not client_ids:
            return []
        query = (
            self.db.table("invoices")
            .select(
                "id,tenant_id,engagement_id,client_id,invoice_number,currency,subtotal,"
                "tax_total,total,status,issue_date,due_date,paid_at,"
                "stripe_payment_link_id,stripe_payment_link_url,public_token,sent_at,"
                "notes,created_at,updated_at,clients(name,billing_email)"
            )
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .order("due_date", desc=False)
            .limit(limit)
        )
        if invoice_id:
            query = query.eq("id", invoice_id)
        if invoice_number:
            query = query.eq("invoice_number", invoice_number)
        if client_id:
            query = query.eq("client_id", client_id)
        if client_ids is not None:
            query = query.in_("client_id", client_ids)
        if status:
            query = query.eq("status", status)
        return query.execute().data or []

    def _payments_by_invoice(self, invoice_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not invoice_ids:
            return {}
        rows = (
            self.db.table("payments")
            .select("id,invoice_id,amount,currency,base_amount,paid_at,notes")
            .eq("tenant_id", self.tenant_id)
            .in_("invoice_id", invoice_ids)
            .order("paid_at", desc=True)
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row.get("invoice_id") or "")].append(row)
        return dict(grouped)

    def _reminders_by_invoice(
        self,
        invoice_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        if not invoice_ids:
            return {}
        rows = (
            self.db.table("agent_suggestions")
            .select("id,related_entity_id,status,output_snapshot,created_at")
            .eq("tenant_id", self.tenant_id)
            .eq("agent_name", "collections_agent")
            .eq("action_type", "send_email")
            .in_("status", list(_COLLECTION_SUGGESTION_STATUSES))
            .order("created_at", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )
        wanted = set(invoice_ids)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            output = row.get("output_snapshot") if isinstance(row, dict) else {}
            if not isinstance(output, dict):
                output = {}
            invoice_id = str(row.get("related_entity_id") or output.get("invoice_id") or "")
            if invoice_id in wanted:
                grouped[invoice_id].append(row)
        return dict(grouped)

    def _collections_policies(self) -> list[dict[str, Any]]:
        try:
            return (
                self.db.table("collections_policies")
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .execute()
                .data
                or []
            )
        except Exception:
            logger.warning(
                "o2c_collections_policy_lookup_failed",
                exc_info=True,
                extra={"tenant_id": self.tenant_id},
            )
            return []

    def _effective_policy(
        self,
        client_id: str,
        policies: list[dict[str, Any]],
    ) -> CollectionsPolicyConfig:
        tenant_policy: dict[str, Any] | None = None
        for row in policies:
            if row.get("client_id") and str(row.get("client_id")) == client_id:
                return row_to_collections_policy(row, source="client_override")
            if row.get("client_id") is None:
                tenant_policy = row
        if tenant_policy is not None:
            return row_to_collections_policy(tenant_policy, source="tenant_default")
        return default_collections_policy()

    def _invoice_summary(
        self,
        row: dict[str, Any],
        *,
        payments: list[dict[str, Any]],
        reminders: list[dict[str, Any]],
        policy: CollectionsPolicyConfig,
    ) -> dict[str, Any]:
        today = date.today()
        total = _decimal(row.get("total"))
        paid_amount = sum(_decimal(payment.get("amount")) for payment in payments)
        balance_due = max(total - paid_amount, Decimal("0"))
        due_date = _parse_date(row.get("due_date"))
        days_overdue = max(0, (today - due_date).days) if due_date else 0
        payment_status = _payment_status(
            persisted_status=str(row.get("status") or ""),
            total=total,
            paid_amount=paid_amount,
        )
        disputed = _is_disputed(row)
        invoice_state = _invoice_state(
            persisted_status=str(row.get("status") or ""),
            payment_status=payment_status,
            due_date=due_date,
            disputed=disputed,
            today=today,
        )
        reminder_history = _reminder_summary(reminders)
        policy_stage = (
            collection_tone_for_days(days_overdue, policy)
            if _is_collectible_state(invoice_state, payment_status) and due_date
            else None
        )
        blockers = _reminder_blockers(
            invoice_state=invoice_state,
            payment_status=payment_status,
            due_date=due_date,
            policy=policy,
            policy_stage=policy_stage,
            reminder_history=reminder_history,
            reminder_count=len(reminders),
        )

        return {
            "id": str(row.get("id") or ""),
            "invoice_number": str(row.get("invoice_number") or ""),
            "client_id": str(row.get("client_id") or ""),
            "client_name": _client_name(row),
            "status": str(row.get("status") or ""),
            "invoice_state": invoice_state,
            "payment_status": payment_status,
            "currency": str(row.get("currency") or "USD"),
            "total": str(total),
            "paid_amount": str(paid_amount),
            "balance_due": str(balance_due),
            "issue_date": _date_text(row.get("issue_date")),
            "due_date": _date_text(row.get("due_date")),
            "sent_at": _date_text(row.get("sent_at")),
            "paid_at": _date_text(row.get("paid_at")),
            "days_overdue": days_overdue,
            "aging_bucket": _aging_bucket(due_date, today, payment_status, invoice_state),
            "public_invoice_available": bool(row.get("public_token"))
            and invoice_state not in {"draft", "voided"},
            "payment_link_state": _payment_link_state(row, invoice_state),
            "reminder_history": reminder_history,
            "collections_policy_stage": policy_stage,
            "recommended_next_action": _recommended_next_action(
                invoice_state=invoice_state,
                payment_status=payment_status,
                days_overdue=days_overdue,
                policy_stage=policy_stage,
                blockers=blockers,
            ),
            "reminder_blockers": blockers,
        }

    def _customer_summaries(
        self,
        invoices: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for invoice in invoices:
            grouped[str(invoice["client_id"])].append(invoice)

        summaries: list[dict[str, Any]] = []
        for client_id, client_invoices in grouped.items():
            balances: dict[str, Decimal] = defaultdict(Decimal)
            overdue: dict[str, Decimal] = defaultdict(Decimal)
            for invoice in client_invoices:
                currency = str(invoice["currency"])
                balance = _decimal(invoice["balance_due"])
                balances[currency] += balance
                if invoice["invoice_state"] in {"overdue", "partially_paid"} and balance > 0:
                    overdue[currency] += balance

            overdue_invoices = [
                invoice
                for invoice in client_invoices
                if invoice["invoice_state"] in {"overdue", "partially_paid"}
                and _decimal(invoice["balance_due"]) > 0
            ]
            summaries.append(
                {
                    "client_id": client_id,
                    "client_name": client_invoices[0].get("client_name"),
                    "invoice_count": len(client_invoices),
                    "open_invoice_count": sum(
                        1
                        for invoice in client_invoices
                        if invoice["payment_status"] not in {"paid", "not_collectible"}
                    ),
                    "overdue_invoice_count": len(overdue_invoices),
                    "balances_by_currency": {
                        currency: str(amount) for currency, amount in balances.items()
                    },
                    "overdue_balance_by_currency": {
                        currency: str(amount) for currency, amount in overdue.items()
                    },
                    "recommended_next_action": _customer_next_action(overdue_invoices),
                    "invoices": client_invoices,
                }
            )
        return summaries

    def _totals(
        self,
        invoices: list[dict[str, Any]],
        customers: list[dict[str, Any]],
    ) -> dict[str, object]:
        balances: dict[str, Decimal] = defaultdict(Decimal)
        overdue: dict[str, Decimal] = defaultdict(Decimal)
        for invoice in invoices:
            currency = str(invoice["currency"])
            balance = _decimal(invoice["balance_due"])
            balances[currency] += balance
            if invoice["invoice_state"] in {"overdue", "partially_paid"} and balance > 0:
                overdue[currency] += balance
        return {
            "invoice_count": len(invoices),
            "customer_count": len(customers),
            "open_invoice_count": sum(
                1
                for invoice in invoices
                if invoice["payment_status"] not in {"paid", "not_collectible"}
            ),
            "overdue_invoice_count": sum(
                1
                for invoice in invoices
                if invoice["invoice_state"] in {"overdue", "partially_paid"}
                and _decimal(invoice["balance_due"]) > 0
            ),
            "balances_by_currency": {
                currency: str(amount) for currency, amount in balances.items()
            },
            "overdue_balance_by_currency": {
                currency: str(amount) for currency, amount in overdue.items()
            },
            "status_counts": dict(Counter(str(invoice["status"]) for invoice in invoices)),
            "state_counts": dict(Counter(str(invoice["invoice_state"]) for invoice in invoices)),
        }


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _date_text(value: object) -> str | None:
    return str(value) if value else None


def _client_name(row: dict[str, Any]) -> str | None:
    client = row.get("clients")
    if isinstance(client, list):
        client = client[0] if client else {}
    if isinstance(client, dict):
        return str(client.get("name")) if client.get("name") else None
    return None


def _payment_status(
    *,
    persisted_status: str,
    total: Decimal,
    paid_amount: Decimal,
) -> str:
    if persisted_status == "voided":
        return "not_collectible"
    if total <= 0 or persisted_status == "paid" or paid_amount >= total:
        return "paid"
    if paid_amount > 0:
        return "partially_paid"
    return "unpaid"


def _is_disputed(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or "").lower()
    if status == "disputed":
        return True
    notes = str(row.get("notes") or "").lower()
    return "dispute" in notes or "do not chase" in notes or "collections hold" in notes


def _invoice_state(
    *,
    persisted_status: str,
    payment_status: str,
    due_date: date | None,
    disputed: bool,
    today: date,
) -> str:
    if disputed:
        return "disputed"
    if persisted_status == "voided":
        return "voided"
    if payment_status == "paid":
        return "paid"
    if payment_status == "partially_paid":
        return "partially_paid"
    if persisted_status == "draft":
        return "draft"
    if persisted_status == "sent":
        return "overdue" if due_date and due_date < today else "sent"
    if persisted_status == "overdue":
        return "overdue"
    if persisted_status == "approved":
        return "overdue" if due_date and due_date < today else "current"
    return persisted_status or "unknown"


def _is_collectible_state(invoice_state: str, payment_status: str) -> bool:
    return invoice_state in {"overdue", "partially_paid", "sent", "current"} and payment_status in {
        "unpaid",
        "partially_paid",
    }


def _aging_bucket(
    due_date: date | None,
    today: date,
    payment_status: str,
    invoice_state: str,
) -> str:
    if payment_status == "paid":
        return "paid"
    if invoice_state in {"draft", "voided", "disputed"}:
        return invoice_state
    if due_date is None:
        return "no_due_date"
    days = (today - due_date).days
    if days <= 0:
        return "current"
    if days <= 30:
        return "0_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    return "over_90"


def _payment_link_state(row: dict[str, Any], invoice_state: str) -> str:
    if row.get("stripe_payment_link_url"):
        return "stripe_payment_link_available"
    if invoice_state == "draft":
        return "not_sent"
    if row.get("public_token") and invoice_state not in {"voided", "draft"}:
        return "public_invoice_only"
    if invoice_state in {"paid", "voided"}:
        return "not_applicable"
    return "missing"


def _reminder_summary(reminders: list[dict[str, Any]]) -> dict[str, Any]:
    if not reminders:
        return {"count": 0, "last_sent_at": None, "last_tone": None, "last_status": None}
    latest = sorted(reminders, key=lambda row: str(row.get("created_at") or ""), reverse=True)[0]
    output = latest.get("output_snapshot") or {}
    if not isinstance(output, dict):
        output = {}
    return {
        "count": len(reminders),
        "last_sent_at": _date_text(latest.get("created_at")),
        "last_tone": output.get("tone"),
        "last_status": latest.get("status"),
    }


def _reminder_blockers(
    *,
    invoice_state: str,
    payment_status: str,
    due_date: date | None,
    policy: CollectionsPolicyConfig,
    policy_stage: str | None,
    reminder_history: dict[str, Any],
    reminder_count: int,
) -> list[str]:
    blockers: list[str] = []
    if invoice_state == "draft":
        blockers.append("invoice_not_approved_or_sent")
    if invoice_state == "voided":
        blockers.append("invoice_voided")
    if invoice_state == "disputed":
        blockers.append("invoice_disputed_or_on_hold")
    if payment_status == "paid":
        blockers.append("invoice_paid")
    if due_date is None:
        blockers.append("missing_due_date")
    if not policy.is_enabled:
        blockers.append("collections_policy_disabled")
    if policy_stage is None and _is_collectible_state(invoice_state, payment_status):
        blockers.append("policy_stage_not_reached")
    if reminder_count >= policy.max_reminders_per_invoice:
        blockers.append("max_reminders_reached")
    if _cooldown_active(reminder_history, policy.cooldown_days):
        blockers.append("cooldown_active")
    return blockers


def _cooldown_active(reminder_history: dict[str, Any], cooldown_days: int) -> bool:
    last_sent_at = reminder_history.get("last_sent_at")
    sent_date = _parse_date(last_sent_at)
    if sent_date is None:
        return False
    return (date.today() - sent_date).days < cooldown_days


def _recommended_next_action(
    *,
    invoice_state: str,
    payment_status: str,
    days_overdue: int,
    policy_stage: str | None,
    blockers: list[str],
) -> str:
    if invoice_state == "draft":
        return "Approve and send the invoice before collections follow-up."
    if invoice_state == "voided":
        return "No collections action; the invoice is voided."
    if payment_status == "paid":
        return "No collections action; the invoice is paid."
    if invoice_state == "disputed":
        return "Do not send a reminder until the dispute or collections hold is resolved."
    if "missing_due_date" in blockers:
        return "Add or verify the due date before collections follow-up."
    if days_overdue <= 0:
        return "No reminder yet; monitor until the invoice reaches the policy stage."
    if "max_reminders_reached" in blockers:
        return "Escalate to the finance manager; the configured reminder limit is reached."
    if "cooldown_active" in blockers:
        return "Wait for the collections cooldown before drafting another reminder."
    if "collections_policy_disabled" in blockers:
        return "Collections policy is disabled; do not draft a reminder."
    if policy_stage:
        prefix = "Collect the remaining balance and " if payment_status == "partially_paid" else ""
        return f"{prefix}draft a {policy_stage} collections reminder for Inbox review."
    return "No collections reminder is due under the current policy."


def _customer_next_action(overdue_invoices: list[dict[str, Any]]) -> str:
    if not overdue_invoices:
        return "No collections follow-up due."
    ordered = sorted(
        overdue_invoices,
        key=lambda invoice: int(invoice.get("days_overdue") or 0),
        reverse=True,
    )
    return ordered[0]["recommended_next_action"]
