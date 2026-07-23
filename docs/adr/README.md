# Architecture Decision Records (ADRs)

An ADR captures **one architecturally significant decision** — the context that
forced it, the options weighed, the choice made, and its consequences. ADRs are
immutable once **Accepted**: a later decision that changes course is a *new* ADR
that supersedes the old one (never an in-place edit).

## When an ADR is required

Per `docs/team/SDLC_PROTOCOL.md`, any change that moves or hardens a **trust
boundary** needs an ADR reviewed by Vastu (architecture) and, where security is
implicated, Prahari:

- Accounting integrity — journal posting, period close, immutability, GL invariants
- Money movement — payments, settlement, payouts, bank rails
- Security & isolation — auth, RBAC, RLS, tenant boundary, PII handling
- Autonomy — agent authority levels (L2→L3), tool permissions, kill-switches
- Cross-cutting platform shifts — queue/scheduling model, multi-node concurrency

Routine feature work does **not** need an ADR; a well-described issue is enough.

## How to add one

1. Copy `TEMPLATE.md` to `NNNN-short-kebab-title.md` (next zero-padded number).
2. Fill every section; keep **Context** decision-forcing and **Consequences** honest
   (including what gets worse or is deferred).
3. Open with `Status: Proposed`, link the driving issue, and get architecture +
   (if relevant) security sign-off. Flip to `Accepted` on approval.
4. Add a row to the index below.

## Statuses

`Proposed` → `Accepted` → (later) `Superseded by ADR NNNN` / `Deprecated`.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-atomic-journal-posting.md) | Atomic, idempotent journal posting | Accepted | 2026-07-22 |
| [0002](0002-jwt-verification-library.md) | JWT verification on PyJWT (drop python-jose) | Accepted | 2026-07-23 |
| [0003](0003-fx-remeasurement.md) | Period-end FX remeasurement of open foreign balances | Accepted | 2026-07-23 |
