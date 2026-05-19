# Testing Standard

## Acceptance Principle

Smoke tests and mocked API responses are useful developer checks, but they do not count as product acceptance.

Acceptance requires evidence against the real stack or a deterministic test stack.

For user workflows, backend-only verification is not enough. If a real user will click through the flow, acceptance must include frontend/browser execution against the real API and then backend validation that the data landed correctly.

## TDD is the default

See [tdd-protocol.md](tdd-protocol.md). The short version:

- Acceptance test first (failing).
- Then integration test (failing).
- Then drop one layer at a time until the unit / domain test is green.
- Refactor only when all relevant tests are green.
- For greenfield work, write the regression suite as `xfail(strict=True)` / `test.fixme()` skeletons against the scenario document so the test list is locked in from day one.

## Required Evidence

For backend changes:

- Unit or service tests for logic.
- API tests against a running API when behavior is user-facing.
- Database tests or migration verification when schema changes.
- Security tests for auth, RBAC, tenant isolation, and integrations.
- Property tests (Hypothesis) for any change that touches money, accounting invariants, or parsing.

For frontend changes:

- Type-check/build.
- Browser verification against real API for touched workflows.
- Accessibility checks for interactive controls.
- Responsive verification for important layouts.

For end-to-end product workflows:

See [e2e-workflow-standard.md](e2e-workflow-standard.md). Required:

- Start from the same entry point a customer or operator uses.
- Complete the flow in the frontend without manual database shortcuts.
- Validate the frontend displays the resulting state correctly.
- Validate backend records, totals, permissions, and integration state.
- Repeat with role-specific users when RBAC is involved.
- Capture reusable scenario steps in `docs/test/e2e_<workflow>.md` and link tests by name.

For agent changes:

See [agent-eval-standard.md](agent-eval-standard.md). Required:

- Deterministic eval pack at `agent_evals/<agent_name>.yaml` (or project equivalent).
- Structural, field-exact, numeric-close, set, and LLM-judge evaluators as appropriate.
- HITL routing accuracy: low-confidence inputs must route to human; ambiguity must yield a clarifying question, not a guess.
- Red-team subset (prompt-injection, PII smuggling, OOD inputs) with pass threshold = 1.00.
- Graceful degradation tests when the model provider is unavailable — core product must keep working.

For inter-service / inter-tool boundaries:

See [contract-testing.md](contract-testing.md).

## Sample Data

- Tests must reset or isolate data.
- Tests must not depend on manually created browser state.
- Seed data should be deterministic and named as test/demo data (`test-tenant-{run_id}`, `INV-TEST-{seq}`).
- Demo tenants/customers should be disposable and deletable through product/admin workflows where possible (proves cleanup as a feature).

## Revenue-Critical Regression Standard

For onboarding, subscriptions, billing, payment webhooks, tenant provisioning, or customer admin setup, see [saas-onboarding-payments.md](saas-onboarding-payments.md). In summary:

- Sandbox/test-mode provider credentials only.
- Provider-recommended test cards or fixtures.
- Checkout through the public frontend.
- Verify webhook delivery and signature validation.
- Verify tenant/customer/subscription records are created exactly once (idempotency under retry).
- Log in as the initial admin through the frontend.
- Create representative business data through the frontend.
- Validate dashboards/totals in the frontend and via API/database checks.
- Test RBAC with at least admin, owner/editor, and viewer/read-only users.
- Test cancellation/failure/retry paths when feasible.
- Clean up demo tenant/customer data through the admin UI or documented cleanup path.

## Verification Report

Every completion should include:

- Commands run.
- Tests passed.
- Frontend workflows executed.
- Backend/API records validated.
- Tests not run and why.
- Residual risks.

## Tooling defaults (project may override)

| Layer | Default tool |
| --- | --- |
| Backend unit / service / integration | pytest, pytest-asyncio |
| Backend property | Hypothesis |
| Backend API e2e | pytest + httpx against running API |
| Frontend unit | project framework's native (Jasmine/Karma for Angular, Vitest for Vite, Jest for Next) |
| Frontend e2e | Playwright (role-based locators, web-first assertions, single-session login) |
| Agent evals | PydanticAI Evals (or equivalent that produces a Dataset/Case/Evaluator structure) |
| LLM observability | Langfuse or Pydantic Logfire (project chooses one and configures it) |
| Contract | Pact (consumer-driven); JSON Schema diff for OpenAPI |
| Load | Locust or k6 |

If the project picks a different tool, the choice goes in `docs/team/TEST_STRATEGY.md` with rationale.

## References

- [tdd-protocol.md](tdd-protocol.md)
- [agent-eval-standard.md](agent-eval-standard.md)
- [e2e-workflow-standard.md](e2e-workflow-standard.md)
- [contract-testing.md](contract-testing.md)
- [observability-standard.md](observability-standard.md)
