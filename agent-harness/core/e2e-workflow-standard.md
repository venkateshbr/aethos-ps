# End-to-End Workflow Standard

A business workflow is a sequence of user actions and system effects that delivers value end-to-end — *engagement to cash*, *procure to pay*, *signup to first invoice*, *record to report*. Every shipped workflow must have a regression suite that exercises it from the same entry point a real user would use.

## Principle

Backend-only verification of a workflow does not prove the workflow works. Acceptance requires:

- Driving the workflow from the **frontend** (real browser session, real auth, real navigation).
- Hitting the **real API** (no mocked services for the system under test).
- Validating **system effects** in both the UI and the backend (records, totals, journal entries, webhook receipts, downstream notifications).
- Running with **deterministic test data** that can be reset between runs.

If any of those is missing, the workflow is not regression-protected.

## Scenario document

Every business workflow gets a scenario document at `docs/test/e2e_<workflow_name>.md`. The document is the canonical test plan and the basis for the executable e2e tests.

A scenario document contains:

1. **Workflow summary** — one paragraph: what value it delivers, who runs it.
2. **Actors and pre-conditions** — tenants, users, roles, seed data, third-party credentials (sandbox).
3. **Happy path** — numbered steps, UI + system effects, expected end state.
4. **Variants** — every meaningful branch (e.g., T&M vs. fixed-fee invoicing, single currency vs. multi-currency, with vs. without payment connector).
5. **Unhappy paths** — every well-known failure mode (webhook miss, validation error, auth denial, network timeout, agent low-confidence, period locked).
6. **Edge cases** — boundary values, race conditions, idempotency under retry, time-zone effects, FX-rate staleness, concurrent modification.
7. **RBAC matrix** — for every role, what is allowed and what must be 403/forbidden in the UI and via direct API call.
8. **Cleanup** — how the test artifacts are torn down (admin UI, documented script, demo-tenant teardown).
9. **Evidence template** — what the QA run produces (screenshots, API responses, DB queries).

See `templates/E2E_WORKFLOW_REGRESSION.md` for the canonical structure.

## Executable mapping

Each scenario step maps to one test. The naming convention couples the document and the test:

```
docs/test/e2e_engagement_to_cash.md   §3.2 "Send invoice, customer pays via Stripe link"
backend/tests/e2e/test_engagement_to_cash.py::test_send_invoice_customer_pays
frontend/e2e/engagement-to-cash.spec.ts::"§3.2 customer pays via Stripe link"
```

When the scenario document changes, the test name changes. PRs that drift between document and code are caught by the QA gate.

## Coverage taxonomy per workflow

For every workflow, the regression suite must cover at minimum:

| Category | What it proves |
| --- | --- |
| **Happy path (UI)** | A real user can complete the workflow start to finish in a browser. |
| **Happy path (API)** | Same workflow driven by API consumers (Postman, third-party integrations). |
| **Multi-variant** | Every meaningfully distinct branch the product supports. |
| **Unhappy — user error** | Validation, missing data, malformed inputs surface clear messages. |
| **Unhappy — system error** | Provider timeout, webhook miss, retry, idempotency. |
| **Unhappy — auth / RBAC** | Forbidden role cannot perform the action via UI or API. |
| **Unhappy — concurrency** | Two clients hitting the same record do not corrupt state. |
| **Unhappy — money** | Imbalanced journal rejected; period-locked txn rejected; precision preserved. |
| **Unhappy — agent** | Agent low-confidence → HITL; agent unavailable → graceful degradation. |
| **Audit** | The expected audit/event trail is written. |
| **Idempotency** | Replaying the same external event (e.g., Stripe webhook) twice causes one effect, not two. |

A workflow is "covered" when each row has at least one test in the suite.

## Test-data discipline

- Tests must seed their own data; they may not rely on data left over from prior runs.
- Tests must use deterministic identifiers (`test-tenant-{run_id}`, `INV-TEST-{seq}`) so artifacts are findable for cleanup.
- Tests must clean up — either via the admin UI (proving cleanup works as a product feature) or via a documented teardown script.
- Provider sandboxes (Stripe test mode, Plaid sandbox, etc.) are used; live keys are forbidden in test runs.
- Sandbox test cards / fixtures from the provider's official docs only.

## Multi-tenant verification

Where the project is multi-tenant, every workflow's e2e suite includes a cross-tenant test:

- Tenant A creates record `R`.
- Tenant B (different user, different tenant) attempts to read/modify `R` via:
  - Direct URL navigation.
  - Direct API call by ID.
  - List endpoint filter manipulation.
- All attempts must return 404 or 403 — not 200 with empty results, not 500.

## Concurrency tests

For workflows with shared state (period close, billing run, invoice numbering, autonomy promotion):

- Submit two requests in quick succession.
- Verify exactly-once effect (e.g., one invoice with one number; no duplicate journals).
- Verify race-loser gets a useful error (409 Conflict, "already locked", etc.), not a silent overwrite.

## Idempotency tests

For workflows that consume external events (webhooks):

- Replay the same event twice with the same idempotency key.
- Verify the resulting state is identical to a single delivery.
- Verify the second delivery is logged (so we can detect provider-side bugs) but not double-effected.

## Performance budgets

Each e2e suite carries a soft performance budget:

- UI e2e: < 60s per scenario.
- API e2e: < 10s per scenario.
- Integration: < 5s per scenario.
- Unit: < 1s per scenario.

Tests that exceed budget are flagged but not failed. Persistent budget breaches turn into perf issues.

## Single browser session pattern

For UI e2e against the real product:

- Launch **one** browser instance per test run.
- Authenticate **once** at the start (`/login` → credentials → dashboard visible).
- Reuse the storage state across tests within the run.
- Run with `headed --slow-mo` locally; headless in CI.

Re-authenticating per test is slow, masks real session bugs, and is forbidden as a default — opt-in only for explicit multi-session tests.

## What a workflow run *outputs*

Every regression run produces:

- A pass/fail per scenario, per variant.
- Trace IDs / video captures for failed runs.
- API/DB validation evidence (which records exist, what totals reconcile).
- A cleanup confirmation (no test artifacts left behind).

This output is attached to the issue or PR — that is the acceptance evidence.

## When to break this rule

Almost never. The narrow exception:

- Pure backend, no-UI service (worker, cron job, internal API): the e2e is driven via API + DB, not browser.
- Even then, the scenario document still exists and the API-driven test runs in the same regression suite.

## References

- Playwright best practices — role-based locators, web-first assertions, isolation, storage-state reuse, network mocking only at the external-service boundary.
- See also: [testing-standard.md](testing-standard.md), [saas-onboarding-payments.md](saas-onboarding-payments.md), [contract-testing.md](contract-testing.md).
