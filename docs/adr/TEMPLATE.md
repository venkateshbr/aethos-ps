# ADR NNNN — <short imperative title>

- **Status:** Proposed <!-- Proposed | Accepted | Superseded by ADR NNNN | Deprecated -->
- **Date:** YYYY-MM-DD
- **Deciders:** <names / roles — architecture + security sign-off where relevant>
- **Issue:** #NNN
- **Supersedes:** <ADR / prior approach, or "none">

## Context

What forces a decision now? The problem, constraints, and the failure modes or
risks of doing nothing. State the trust boundary involved. Be concrete — cite the
files, tables, or audit items (e.g. LR-NN) at stake.

## Decision

The change we are making, stated plainly. Include the shape of the mechanism
(schema, RPC, dependency, boundary) enough that a reviewer can evaluate it.

## Options considered

- **Option A (chosen):** … — why it wins.
- **Option B:** … — why not.
- **Option C:** … — why not.

## Consequences

Honest results of the choice.

- **Positive:** what gets safer / simpler / faster.
- **Negative / trade-offs:** what gets slower, more complex, or is deferred.
- **Migration / rollout:** backfill, deploy ordering, feature flag, staging gates.
- **Verification:** the tests / checks that prove it holds (unit, e2e, prod probe).
