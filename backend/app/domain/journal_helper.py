"""Journal entry helpers for building and validating double-entry GL postings.

Usage::

    from app.domain.journal_helper import JournalLineSpec, validate_journal_balance

    lines = [
        JournalLineSpec(direction="DR", account_code="5000", account_id="uuid-...", amount=Decimal("1000.00"), description="Expenses"),
        JournalLineSpec(direction="CR", account_code="2000", account_id="uuid-...", amount=Decimal("1000.00"), description="Accounts Payable"),
    ]
    assert validate_journal_balance(lines)

Rules enforced here (not in DB triggers, to enable Python-layer validation before INSERT):
- debits must equal credits within a 1-cent tolerance (GAAP rounding tolerance).
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)


def _journal_idempotency_key(
    tenant_id: str,
    reference_type: str,
    reference_id: str,
    entry_date: str,
    description: str,
    lines: list[dict[str, Any]],
) -> str:
    """Deterministic key so a retried/duplicated post maps to the same entry.

    Derived from the post's content (tenant, source reference, date, description,
    and the sorted lines), so a true retry — or a second API node handling the
    same submit — produces the identical key and the RPC dedupes it, while
    distinct events (e.g. a bill's approval vs its settlement — different lines)
    get distinct keys and both post. See ADR 0001 for the follow-up to let callers
    pass an explicit semantic key.
    """
    parts = [
        str(tenant_id),
        str(reference_type or ""),
        str(reference_id or ""),
        str(entry_date or ""),
        str(description or ""),
    ]
    for line in sorted(
        lines,
        key=lambda ln: (
            str(ln.get("account_id") or ""),
            str(ln.get("direction") or ""),
            str(ln.get("base_amount") or ""),
        ),
    ):
        parts.append(
            f"{line.get('account_id')}:{line.get('direction')}:"
            f"{line.get('base_amount')}:{line.get('currency')}"
        )
    return "je:" + hashlib.sha256("|".join(parts).encode()).hexdigest()


@dataclass
class JournalLineSpec:
    """Specification for a single journal line before it is persisted.

    ``direction`` must be "DR" (debit) or "CR" (credit).
    ``account_code`` is the COA code string (e.g. "5000", "2000").
    ``account_id`` is the UUID of the resolved COA account (optional; required by guardian).
    ``amount`` must be positive; direction carries the sign semantics.
    ``description`` is an optional narrative for the line.
    ``currency`` is the ISO-4217 currency code (default "USD").
    ``base_amount`` is the tenant-base-currency equivalent (defaults to amount for single-currency).
    ``fx_rate_id`` is the immutable FX rate row used for base conversion, when any.
    """

    direction: str  # "DR" or "CR"
    account_code: str
    amount: Decimal
    description: str = ""
    account_id: str | None = None
    currency: str = "USD"
    base_amount: Decimal | None = None
    fx_rate_id: str | None = None

    def __post_init__(self) -> None:
        if self.direction not in ("DR", "CR"):
            raise ValueError(f"direction must be 'DR' or 'CR', got {self.direction!r}")
        if self.amount < Decimal("0"):
            raise ValueError(f"amount must be non-negative, got {self.amount}")
        if self.base_amount is None:
            self.base_amount = self.amount


def journal_line_base_amount(line: JournalLineSpec) -> Decimal:
    return line.base_amount if line.base_amount is not None else line.amount


def validate_journal_balance(lines: list[JournalLineSpec]) -> bool:
    """Return True if the journal balances (debits == credits within 0.01).

    A balanced journal is required before any GL posting.
    Raises no exceptions — callers should raise HTTPException on False.

    Args:
        lines: List of JournalLineSpec entries to check.

    Returns:
        True if |debits - credits| <= 0.01, False otherwise.
    """
    debits = sum(journal_line_base_amount(line) for line in lines if line.direction == "DR")
    credits = sum(journal_line_base_amount(line) for line in lines if line.direction == "CR")
    return abs(debits - credits) <= Decimal("0.01")


def post_journal(
    db: Client,
    tenant_id: str,
    created_by: str,
    description: str,
    entry_date: str,
    reference_type: str,
    reference_id: str,
    lines: list[JournalLineSpec],
    entry_number: str | None = None,
    extra_entry_fields: dict[str, Any] | None = None,
) -> dict:
    """Validate with accounting_guardian then INSERT journal_entry + journal_lines.

    This is the canonical way to post a journal entry from Python code.
    The accounting_guardian runs L3 always and cannot be disabled — it validates
    balance, period lock, and account existence before any INSERT.

    Args:
        db: Supabase service-role client (tenant session var must already be set).
        tenant_id: Tenant UUID string.
        created_by: User UUID string of the person/system posting the entry.
        description: Human-readable description of the journal entry.
        entry_date: ISO date string "YYYY-MM-DD".
        reference_type: Sub-ledger type (e.g. "bill", "invoice", "expense").
        reference_id: UUID of the referencing record.
        lines: List of JournalLineSpec entries (must balance within 0.01).
        entry_number: Optional entry number (auto-generated if not provided).
        extra_entry_fields: Optional additional journal_entries fields to persist.

    Returns:
        The journal_entry row dict as returned by Supabase.

    Raises:
        ValueError: If the accounting_guardian rejects the journal (imbalanced,
                    locked period, or unknown accounts).
    """
    # Import here to avoid circular imports — guardian imports journal_helper
    from app.agents.accounting_guardian import validate_journal

    result = validate_journal(lines, entry_date, tenant_id, db)
    if result["action"] == "reject":
        raise ValueError(f"accounting_guardian rejected: {result['reason']}")

    period = entry_date[:7]  # "YYYY-MM"
    if not entry_number:
        entry_number = f"JE-{str(uuid.uuid4())[:8].upper()}"

    entry_payload = {
        "tenant_id": tenant_id,
        "entry_number": entry_number,
        "entry_type": "auto",
        "description": description,
        "entry_date": entry_date,
        "period": period,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "posted_at": datetime.now(UTC).isoformat(),
        "created_by": created_by,
    }
    if extra_entry_fields:
        entry_payload.update(extra_entry_fields)

    je_lines = []
    for spec in lines:
        je_lines.append(
            {
                "tenant_id": tenant_id,
                "direction": spec.direction,
                "account_id": spec.account_id,
                "amount": str(spec.amount),
                "currency": spec.currency,
                "base_amount": str(spec.base_amount if spec.base_amount is not None else spec.amount),
                "fx_rate_id": spec.fx_rate_id,
                "description": spec.description,
            }
        )

    # Add FX residual line if needed (routes to account 7900 Realized FX Gain/Loss)
    if result.get("fx_residual"):
        fx_acct = (
            db.table("accounts")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("code", "7900")
            .execute()
        )
        fx_acct_id = fx_acct.data[0]["id"] if fx_acct.data else None
        residual: Decimal = result["fx_residual"]
        base_currency = "USD"
        tenant_result = (
            db.table("tenants")
            .select("base_currency")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_result.data:
            base_currency = str(tenant_result.data[0].get("base_currency") or "USD").upper()
        debits = sum(journal_line_base_amount(line) for line in lines if line.direction == "DR")
        credits = sum(journal_line_base_amount(line) for line in lines if line.direction == "CR")
        direction = "CR" if debits > credits else "DR"
        je_lines.append(
            {
                "tenant_id": tenant_id,
                "direction": direction,
                "account_id": fx_acct_id,
                "amount": str(residual),
                "currency": base_currency,
                "base_amount": str(residual),
                "fx_rate_id": None,
                "description": "Realized FX Gain/Loss",
            }
        )

    # Atomic, idempotent post: header + lines in ONE DB transaction, deduped on a
    # deterministic content key so a retry — or a second API node — posts exactly
    # once. Balance (debits == credits) is enforced by the DB constraint trigger
    # trg_journal_entry_balanced at commit. (ADR 0001 / #390)
    idempotency_key = _journal_idempotency_key(
        tenant_id, reference_type, reference_id, entry_date, description, je_lines
    )
    rpc_result = db.rpc(
        "post_journal_entry",
        {
            "p_entry": entry_payload,
            "p_lines": je_lines,
            "p_idempotency_key": idempotency_key,
        },
    ).execute()

    payload = rpc_result.data
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    je = (payload or {}).get("entry") or {}

    logger.info(
        "Journal posted",
        extra={
            "journal_entry_id": je.get("id"),
            "tenant_id": tenant_id,
            "lines": len(je_lines),
            "idempotent_hit": bool((payload or {}).get("idempotent_hit")),
        },
    )
    return je
