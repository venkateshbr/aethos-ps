# Aethos PS — Test Strategy

> **Owner**: Aksha (SDET)
> **Status**: Skeleton. Test discipline is canonical in [`agent-harness/core/testing-standard.md`](../../agent-harness/core/testing-standard.md); this document is the Aethos-specific overlay.

## Canonical standards (read these first)

1. [`agent-harness/core/testing-standard.md`](../../agent-harness/core/testing-standard.md)
2. [`agent-harness/core/tdd-protocol.md`](../../agent-harness/core/tdd-protocol.md)
3. [`agent-harness/core/e2e-workflow-standard.md`](../../agent-harness/core/e2e-workflow-standard.md)
4. [`agent-harness/core/agent-eval-standard.md`](../../agent-harness/core/agent-eval-standard.md)
5. [`agent-harness/core/contract-testing.md`](../../agent-harness/core/contract-testing.md)
6. [`agent-harness/core/quality-gates.md`](../../agent-harness/core/quality-gates.md)

## Aethos-specific tooling

| Layer | Tool | Location |
| --- | --- | --- |
| Backend unit / service / integration | `pytest`, `pytest-asyncio` | `backend/tests/{unit,integration}/` |
| Backend property | `hypothesis` | `backend/tests/property/` |
| Backend e2e (API) | `pytest` + `httpx` against `:8011` | `backend/tests/e2e/` |
| Frontend unit | Jasmine / Karma | `frontend/src/**/*.spec.ts` |
| Frontend e2e | Playwright | `frontend/e2e/` |
| Agent evals | PydanticAI Evals | `backend/tests/evals/` reading `docs/test/agent_evals/*.yaml` |
| LLM observability (test capture) | Langfuse + Pydantic Logfire | configured via `.env.test` |
| Contract | JSON Schema diff on `shared/schemas/`; Pact (v1.x) | `tests/contracts/` (planned) |
| Security | `pytest` security marker | `backend/tests/security/` |
| Load | Locust | `tests/load/` (planned) |

## Workflow scenario index

- [`docs/test/regression_suites.md`](../test/regression_suites.md) — top-level map
- [`docs/test/e2e_engagement_to_cash.md`](../test/e2e_engagement_to_cash.md) — flagship
- [`docs/test/e2e_procure_to_pay.md`](../test/e2e_procure_to_pay.md)
- [`docs/test/e2e_record_to_report.md`](../test/e2e_record_to_report.md)
- [`docs/test/e2e_onboarding_signup.md`](../test/e2e_onboarding_signup.md)
- [`docs/test/accounting_invariants.md`](../test/accounting_invariants.md)

## Agent eval pack index

See [`docs/test/agent_evals/`](../test/agent_evals/) — one YAML per registered agent.

## Coverage taxonomy per workflow (enforced)

For every workflow, the regression suite must cover:

- Happy path (UI + API)
- Multi-variant (every meaningful branch)
- Unhappy: user error, system error, auth/RBAC, concurrency, money, agent
- Audit trail completeness
- Idempotency under retry
- Performance budget

See [`agent-harness/core/e2e-workflow-standard.md`](../../agent-harness/core/e2e-workflow-standard.md).

## Aksha's QA Sign-off Criteria (Aethos specific)

A transaction is **validated** only when:
1. UI view shows correct data.
2. Downstream effects (GL postings, status changes) are visible in the browser.
3. API-only verification is supplemental, not sufficient on its own.

See [`agent-harness/core/e2e-workflow-standard.md`](../../agent-harness/core/e2e-workflow-standard.md) for the rationale.

## Test data discipline

- Test tenant prefix: `test-tenant-<run_id>`.
- Test invoice prefix: `INV-TEST-<seq>`.
- All artifacts deletable through admin UI (proves cleanup as a feature) or `scripts/teardown_test_tenant.py`.

## Changelog

### [2026-05-19] — Skeleton created; pointers to harness standards added.
