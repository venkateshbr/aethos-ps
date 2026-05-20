"""accounting_guardian — L3 always, cannot be disabled.

Validates every journal proposal before it is posted:
  1. Balance check: sum(DR) == sum(CR) within ±0.01 (FX residual tolerance)
  2. Period lock: entry_date must not fall in a locked period
  3. Account validity: all account_ids must exist in accounts for this tenant

Returns a result dict:
  {"action": "post",              "reason": "",               "fx_residual": None}
  {"action": "post_with_residual","reason": "FX residual ...", "fx_residual": Decimal}
  {"action": "reject",            "reason": "<explanation>",  "fx_residual": None}

If there is a tiny FX residual (0 < abs(DR-CR) <= 0.01), the guardian
routes the residual to account 7900 (Realized FX Gain/Loss) automatically
and returns action='post_with_residual'.

Security / quality gates:
- This guardian runs at L3 always — it is a hard gate, not a suggestion.
- It cannot be disabled by any configuration or feature flag.
- If the guardian cannot reach the DB (e.g. Supabase outage), it REJECTS the
  journal (fail-closed) rather than allowing an unvalidated posting.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TypedDict

from app.domain.journal_helper import JournalLineSpec
from supabase import Client

logger = logging.getLogger(__name__)

FX_RESIDUAL_ACCOUNT_CODE = "7900"
FX_TOLERANCE = Decimal("0.01")


class GuardianResult(TypedDict):
    action: str  # "post" | "post_with_residual" | "reject"
    reason: str
    fx_residual: Decimal | None


def validate_journal(
    lines: list[JournalLineSpec],
    entry_date: str,
    tenant_id: str,
    db: Client,
) -> GuardianResult:
    """Run all L3 accounting validations against the proposed journal.

    This function is the single enforcement point for GAAP posting rules.
    It must be called before every journal INSERT — use ``post_journal()``
    from ``journal_helper`` rather than calling this directly.

    Args:
        lines: List of JournalLineSpec — the proposed journal lines.
        entry_date: ISO date string "YYYY-MM-DD".
        tenant_id: Tenant UUID string.
        db: Supabase service-role client.

    Returns:
        GuardianResult with action, reason, and optional fx_residual.
    """
    # ------------------------------------------------------------------
    # 1. Balance check
    # ------------------------------------------------------------------
    debits = sum(line.amount for line in lines if line.direction == "DR")
    credits = sum(line.amount for line in lines if line.direction == "CR")
    diff = abs(debits - credits)

    if diff > FX_TOLERANCE:
        return GuardianResult(
            action="reject",
            reason=(
                f"Journal imbalanced: DR={debits} CR={credits} diff={diff}. "
                f"Debits must equal credits within {FX_TOLERANCE}."
            ),
            fx_residual=None,
        )

    # ------------------------------------------------------------------
    # 2. Period lock check
    # ------------------------------------------------------------------
    period = entry_date[:7]  # "YYYY-MM"
    try:
        lock_result = (
            db.table("period_locks")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("period", period)
            .execute()
        )
    except Exception:
        logger.exception(
            "accounting_guardian: DB error checking period_locks for tenant=%s period=%s",
            tenant_id,
            period,
        )
        return GuardianResult(
            action="reject",
            reason="accounting_guardian: failed to check period lock status — DB error. Journal rejected (fail-closed).",
            fx_residual=None,
        )

    if lock_result.data:
        return GuardianResult(
            action="reject",
            reason=(
                f"Period {period} is locked. "
                "Post a reversing entry in an open period instead."
            ),
            fx_residual=None,
        )

    # ------------------------------------------------------------------
    # 3. Account validity check (only for lines that supply account_id)
    # ------------------------------------------------------------------
    account_ids = [
        line.account_id
        for line in lines
        if line.account_id is not None
    ]

    if account_ids:
        try:
            valid_result = (
                db.table("accounts")
                .select("id")
                .eq("tenant_id", tenant_id)
                .in_("id", account_ids)
                .execute()
            )
        except Exception:
            logger.exception(
                "accounting_guardian: DB error checking accounts for tenant=%s",
                tenant_id,
            )
            return GuardianResult(
                action="reject",
                reason="accounting_guardian: failed to validate account IDs — DB error. Journal rejected (fail-closed).",
                fx_residual=None,
            )

        valid_ids = {r["id"] for r in (valid_result.data or [])}
        invalid = [aid for aid in account_ids if aid not in valid_ids]
        if invalid:
            return GuardianResult(
                action="reject",
                reason=f"Unknown account IDs for this tenant: {invalid}",
                fx_residual=None,
            )

    # ------------------------------------------------------------------
    # 4. FX residual routing (0 < diff <= FX_TOLERANCE)
    # ------------------------------------------------------------------
    if diff > Decimal("0"):
        logger.info(
            "accounting_guardian: routing FX residual %s to account %s",
            diff,
            FX_RESIDUAL_ACCOUNT_CODE,
        )
        return GuardianResult(
            action="post_with_residual",
            reason=f"FX residual {diff} routed to {FX_RESIDUAL_ACCOUNT_CODE} Realized FX Gain/Loss",
            fx_residual=diff,
        )

    return GuardianResult(action="post", reason="", fx_residual=None)
