# ADR 0001 — Atomic, idempotent journal posting

- **Status:** Accepted (implementation in progress — issue #390 / LR-08)
- **Date:** 2026-07-22
- **Deciders:** Founder + Vastu (architecture); Prahari (security review required)
- **Supersedes:** the two-insert `post_journal` path in `app/domain/journal_helper.py`

## Context

Every GL journal — sub-ledger (invoice/bill/payment/expense) auto-posts, manual
journals, year-end close, and FX gain/loss — funnels through one helper,
`app/domain/journal_helper.py::post_journal` (11 call sites). That helper writes
the header and the lines as **two separate PostgREST calls**:

```
db.table("journal_entries").insert(header).execute()   # transaction 1
db.table("journal_lines").insert(lines).execute()      # transaction 2
```

Two HTTP calls = two transactions, with **no boundary across them**. On a
multi-node deployment this yields three failure modes (audit #368, LR-08):

1. **Not crash-safe.** A crash / network drop / lines-insert failure between the
   two calls leaves an **immutable header with zero or partial lines** (the
   `prevent_posted_journal_edit` trigger then blocks repair — you can only reverse
   a broken entry).
2. **Not idempotent.** A client/proxy/worker retry, or two nodes handling a
   double-submit, runs `post_journal` twice → **double-posted GL**. There is no
   idempotency key on the insert.
3. **Balance only app-enforced.** `accounting_guardian` validates `debits==credits`
   and the period lock in Python *before* the inserts, but there is **no
   DB-level guarantee** — a guardian bypass, a partial write, or a concurrent lock
   can persist a bad entry.

These are correctness/data-integrity hazards on the general ledger, so per the
SDLC protocol this is a trust-boundary change requiring an ADR + Prahari review +
Founder approval before merge.

## Decision

Replace the two-insert path with a **single atomic Postgres function**
`post_journal_entry(p_entry jsonb, p_lines jsonb, p_idempotency_key text)` called
via `db.rpc(...)`, plus two DB-level invariants. All enforcement lives in the DB
so it is **independent of how many API nodes call it**.

1. **Atomicity.** Header + all lines are inserted in one transaction inside the
   function — an orphan header can never persist.
2. **DB-enforced balance.** A `CONSTRAINT TRIGGER ... DEFERRABLE INITIALLY
   DEFERRED` on `journal_lines` fires at commit (after all lines exist) and raises
   unless `sum(base_amount) filter (DR) = sum(base_amount) filter (CR)` per entry.
   A plain `CHECK` can't span rows; a deferred constraint trigger is the standard
   Postgres way to enforce a cross-row invariant like double-entry. This is the
   un-bypassable last line of defense the guardian cannot provide.
3. **Exactly-once.** A `journal_entries.idempotency_key` column with a unique index
   + `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING`; on conflict the RPC
   returns the already-posted entry. The helper derives a **deterministic key**
   from the post's content (tenant, reference, date, sorted lines) so a true retry
   maps to the same key and no-ops, while distinct events (e.g. a bill's approval
   vs its settlement — different lines) get distinct keys and both post.

`accounting_guardian` is retained as the fast pre-check + business layer (FX
residual routing, account validity, friendly error messages), but the DB
constraints become the authoritative last line.

## Alternatives considered

- **App-managed transaction via a direct psycopg connection** (wrap header+lines in
  `BEGIN…COMMIT` in Python). Gets atomicity but adds app-side transaction/pool
  complexity across nodes, loses the PostgREST/RLS convenience, and *still* needs
  the balance constraint + idempotency key. The stored proc keeps enforcement next
  to the data and behaves identically regardless of node count — strictly better.
- **Outbox / event-sourced posting** (project the existing immutable
  `financial_events` into journals via one idempotent consumer). Most robust at
  very high scale/audit, but a large re-architecture. Kept as a possible future
  evolution; not needed now.

## Consequences

- One migration (`0107`) adds the column/index, the deferred balance trigger, and
  the RPC. One helper (`post_journal`) is rewritten to call the RPC — all 11
  callers benefit with no per-caller change.
- **Backfill:** existing orphan/zero-line headers from the old path must be found
  and corrected (via reversing entries) before the deferred trigger is relied on;
  the trigger only guards *new* line writes.
- **Follow-ups (tracked on #390):** move the period-lock check into the same
  transaction (a `BEFORE INSERT` trigger on `journal_entries`) to close the
  guardian/write TOCTOU window; optionally let callers pass an explicit semantic
  idempotency key (e.g. `bill_settled:<id>`) for precision over the content hash.
- **Rollout:** ship behind review; verify on staging with a concurrent
  double-post test (two parallel calls, same key → one entry) and a partial-failure
  test before enabling in production.
