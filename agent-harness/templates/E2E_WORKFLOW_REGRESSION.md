# E2E Workflow Regression Scenario

Use this template for any end-to-end business workflow: engagement-to-cash, procure-to-pay, record-to-report, signup-to-first-invoice, etc.

## Workflow

- **Name**:
- **Owner role**:
- **Value delivered (one sentence)**:
- **Entry point (UI route / API endpoint)**:
- **Exit state (what "done" looks like to the user)**:

## Actors & Pre-conditions

| Actor | Role | Notes |
| --- | --- | --- |
| | | |

- Tenants:
- Seed data:
- Third-party sandbox credentials in `.env`:
- Webhook endpoint reachable by provider:
- Test fixtures (cards, documents, etc.):
- Demo data cleanup path:

## Happy Path

Number each step. Each step has UI action → system effect.

| # | Actor | UI action | API / system effect | Expected end state |
| --- | --- | --- | --- | --- |
| 1 | | | | |

## Variants

List every meaningful branch. Each variant is its own scenario or sub-scenario.

- Variant A:
- Variant B:
- ...

## Unhappy Paths

| # | Failure mode | Trigger | Expected behavior |
| --- | --- | --- | --- |
| U1 | User error: missing required field | Submit form without X | Inline validation, no API call |
| U2 | System error: provider timeout | Provider mock returns 504 | Retried N times, surfaces clear error, no partial state |
| U3 | Auth error: forbidden role | Role X attempts action | UI hides; API returns 403 |
| U4 | Concurrency: race on shared resource | Two clients submit at once | Exactly-one effect; race-loser gets 409 |
| U5 | Money: imbalanced journal | Force debit ≠ credit | Posting rejected at draft and post |
| U6 | Money: period locked | Try to post in closed period | Rejected with clear message |
| U7 | Agent: low confidence | Inject low-confidence input | Routes to HITL, not auto-applied |
| U8 | Agent: provider down | LLM API returns 500 | Graceful degradation; core ERP unaffected |
| U9 | Webhook miss | Provider does not deliver | Reconciliation worker catches and posts |
| U10 | Idempotency: replay | Same webhook delivered twice | One effect, second logged |

## Edge Cases

- Boundary values (zero, negative, max precision):
- Time-zone effects:
- FX-rate staleness (>3 days old):
- Concurrent modification (optimistic-locking conflict):
- Long-running operations and cancellation:

## RBAC Matrix

| Role | UI: visible | UI: enabled | API: GET | API: POST/PUT/DELETE |
| --- | --- | --- | --- | --- |
| Owner / admin | | | | |
| Editor / member | | | | |
| Viewer / read-only | | | | |
| Other tenant | hidden | n/a | 404 / 403 | 404 / 403 |

## Audit Trail

What audit / event records must exist after a successful run?

- `event:` written with fields: ...
- `audit_log:` entries: ...

## Cleanup

- Method: (admin UI / documented script)
- Confirmation: artifacts no longer findable in UI or via API

## Evidence Template

```markdown
## <Workflow> Regression Evidence

- Run ID:
- Frontend URL:
- API URL:
- Payment provider mode: sandbox/test
- Test data prefix:
- Tenant created:
- Initial admin login verified:
- Variants covered: [A, B, ...]
- Happy path: PASS / FAIL (link to trace)
- Unhappy paths covered: [U1, U2, ...] — PASS / FAIL each
- RBAC roles tested:
- Audit trail verified:
- Cleanup completed:
- Performance budget met (yes/no):
- Issues found:
- Residual risk:
```

## Executable mapping

Each step / variant / unhappy path maps to at least one test. Name the tests after the section IDs from this document.

```
docs/test/e2e_<workflow>.md   §3 happy step 5
backend/tests/e2e/test_<workflow>.py::test_happy_step_5
frontend/e2e/<workflow>.spec.ts::"§3 happy step 5"
```

Drift between this document and the tests is a QA-gate failure.
