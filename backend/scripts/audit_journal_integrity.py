"""Pre-deploy integrity audit for the atomic-journal-posting constraints (#372).

Migration 0107 adds a DEFERRABLE ``trg_journal_entry_balanced`` trigger and an
``idempotency_key`` unique index. The balance trigger fires on ``journal_lines``
changes, so it does NOT retroactively validate existing rows — and a **zero-line
posted header** never fires it at all. Before enabling these constraints in a
live environment, ADR 0001 / #372 (AC 7) require auditing existing data and
reporting any invalid posted journals.

This script is **read-only**. It reports, per tenant:

  1. Orphan headers   — posted journal_entries with zero journal_lines.
  2. Unbalanced entries — posted entries where sum (DR base_amount - CR base_amount)
     exceeds 0.01 (the same tolerance the trigger enforces).

Exit code 0 = clean (safe to enable constraints); 1 = issues found (remediate via
reversal entries first). Credentials come from the environment or backend/.env /
root .env (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY).

Usage:
    uv run python -m scripts.audit_journal_integrity
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from supabase import Client, create_client

_PAGE = 1000
_TOLERANCE = Decimal("0.01")


def _load_env(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    root = Path(__file__).resolve().parents[2]
    for candidate in (root / "backend" / ".env", root / ".env"):
        if not candidate.exists():
            continue
        for line in candidate.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def _client() -> Client:
    url = _load_env("SUPABASE_URL")
    key = _load_env("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY unavailable.")
    return create_client(url, key)


def _paged(db: Client, table: str, columns: str):
    start = 0
    while True:
        rows = (
            db.table(table).select(columns).range(start, start + _PAGE - 1).execute().data or []
        )
        yield from rows
        if len(rows) < _PAGE:
            return
        start += _PAGE


def audit() -> int:
    db = _client()

    # Posted headers: id -> tenant_id. Posted state is `posted_at IS NOT NULL`
    # (journal_entries carry no status column); the immutable GL lives here.
    headers: dict[str, str] = {}
    for row in _paged(db, "journal_entries", "id,tenant_id,posted_at"):
        if row.get("posted_at"):
            headers[str(row["id"])] = str(row.get("tenant_id") or "")

    # Aggregate posted lines by entry.
    line_count: dict[str, int] = defaultdict(int)
    balance: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in _paged(db, "journal_lines", "journal_entry_id,direction,base_amount"):
        entry_id = str(row.get("journal_entry_id") or "")
        if entry_id not in headers:
            continue  # only posted headers are in scope
        line_count[entry_id] += 1
        base = Decimal(str(row.get("base_amount") or "0"))
        balance[entry_id] += base if row.get("direction") == "DR" else -base

    orphans = [(eid, headers[eid]) for eid in headers if line_count[eid] == 0]
    unbalanced = [
        (eid, headers[eid], balance[eid])
        for eid in headers
        if line_count[eid] > 0 and abs(balance[eid]) > _TOLERANCE
    ]

    print(f"Posted journal entries audited: {len(headers)}")
    print(f"Orphan headers (0 lines):       {len(orphans)}")
    print(f"Unbalanced entries (>0.01):     {len(unbalanced)}")

    for eid, tenant in orphans[:50]:
        print(f"  ORPHAN     tenant={tenant} entry={eid}")
    for eid, tenant, diff in unbalanced[:50]:
        print(f"  UNBALANCED tenant={tenant} entry={eid} DR-CR base diff={diff}")

    if orphans or unbalanced:
        print("\nRESULT: INVALID journals found — remediate via reversal before "
              "enabling the 0107 constraints in this environment.")
        return 1
    print("\nRESULT: clean — safe to enable the atomic-posting constraints.")
    return 0


if __name__ == "__main__":
    sys.exit(audit())
