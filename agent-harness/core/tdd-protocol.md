# TDD Protocol

Test-driven development is the default discipline for every feature in a project using this harness. This document defines what TDD means in practice — what tests are written, in what order, and what gates they protect.

## Why TDD here

This harness targets software where mistakes are expensive: financial systems, multi-tenant SaaS, AI-generated mutations that touch user data. TDD is not a religious practice — it is the cheapest way we know to keep those systems correct under change.

Tests written first force three things to happen:

1. Acceptance criteria are concretized before code is written.
2. The public contract of a unit is designed by its consumer, not its author.
3. Regressions get caught the moment the next change tries to break them.

If a test is written *after* the code, the code already passes — there is no signal that the test would have caught the bug.

## Outside-in TDD

Default to outside-in (London-school) TDD for any user-facing feature:

```
1. Write the acceptance test (end-to-end, e.g., Playwright or pytest+httpx hitting the API).
   - Expected to fail with a "not implemented" error or a 404.
   - This test is the contract with the user. It is not deleted when the feature ships.

2. Write the integration test at the service-layer boundary.
   - Expected to fail because the service does not exist yet.

3. Drop one layer at a time, writing tests against the next collaborator.
   - Repository / gateway tests.
   - Domain-object tests.
   - Each test red → make it green with the minimum code → next test.

4. Refactor only when all relevant tests are green.
```

For pure logic (money math, journal balancing, parsing, validators), prefer **inside-out / property-based** TDD:

```
1. Identify the invariant.
2. Express it as a property test (Hypothesis or fast-check).
3. Watch it fail. Implement until it passes.
4. Add concrete examples for the hand-picked edge cases the property cannot enumerate.
```

## The TDD cycle

Red → green → refactor.

- **Red**: write a single failing test. If the test passes immediately, either the feature already exists or the test is wrong.
- **Green**: write the smallest amount of code to make the test pass. Speculative generality is a smell.
- **Refactor**: improve structure without changing behavior. The test suite is your safety net — if you cannot refactor without breaking tests, the tests are over-specified.

Each cycle should be measured in minutes, not hours. If the red phase is taking longer than ~15 minutes, the test is too big — split it.

## Test taxonomy and order of writing

| Layer | Tool examples | Written when | Survives? |
| --- | --- | --- | --- |
| **End-to-end (UI)** | Playwright, Cypress | First, for any user-facing feature | Yes — regression suite |
| **End-to-end (API)** | pytest + httpx, supertest | First, for any API-only feature | Yes |
| **Integration / service** | pytest with real DB, Vitest with real adapters | After the e2e is failing, before any production code | Yes |
| **Contract** | Pact, OpenAPI diff | Whenever an inter-service boundary is touched | Yes |
| **Unit / domain** | pytest, Vitest | Inside-out for pure logic | Yes |
| **Property** | Hypothesis, fast-check | For every numeric / accounting / parsing invariant | Yes |
| **Agent eval** | PydanticAI Evals, Langfuse datasets | Before any agent prompt change | Yes — versioned per prompt |
| **Smoke** | curl, ping, health-check | Last; only as a deployment gate | Yes, but separate from regression |

A feature is not "done" until at least one e2e (or API e2e for backend-only features) plus all relevant lower-layer tests are green.

## What counts as "test first"

A test counts as TDD only if, at the moment it was written:

- It compiles / parses.
- It is exercising the not-yet-existing code path.
- It is failing for the right reason (the assertion fails or the symbol is missing) — not because the test file itself is broken.

Tests that are committed already-green do not count and are flagged in PR review.

## Skeleton-test convention (greenfield projects)

When the codebase does not yet exist, write the acceptance scenarios as skeleton tests:

- Use `pytest.mark.xfail(strict=True, reason="not yet implemented — see PLAN §N")` for backend.
- Use `test.fixme()` in Playwright for frontend.
- These tests live in the regression suite from day one. As features land, the marker is removed and the test runs.
- `strict=True` is non-negotiable — if an xfail-marked test starts passing accidentally, the suite must fail until the marker is removed.

This converts the spec into executable acceptance criteria without paying the cost of implementing tests against code that does not exist.

## What TDD does NOT mean here

- It does **not** mean 100% line coverage. Coverage is a side-effect, not a goal.
- It does **not** mean writing a unit test for every getter/setter.
- It does **not** mean mocking the database. Integration tests hit a real DB (or a deterministic test instance).
- It does **not** replace exploratory testing, security review, or production observability.

## Gates

These gates are checked by the QA role (Aksha-equivalent) before promoting an issue to `status:in-review`:

| Gate | Rule |
| --- | --- |
| **Acceptance gate** | An e2e (or API e2e) test exists for the user story and is green on the real stack. |
| **TDD gate** | The first commit on the feature branch is a failing test. If not, the PR description must justify why. |
| **Regression gate** | Every bug fix lands with a test that fails on the unfixed code and passes on the fix. |
| **Coverage gate** | Coverage on touched files does not decrease. Absolute coverage threshold is project-specific. |
| **Property gate** | All money/accounting/parsing changes have a property test or a documented reason none applies. |
| **Eval gate** | Any prompt change ships with an updated eval dataset; average score does not regress. See [agent-eval-standard.md](agent-eval-standard.md). |

## TDD with AI assistance

When an AI agent writes code on your behalf, TDD becomes more important, not less:

- The agent writes the failing test first, commits, then writes the implementation.
- Reviewers can verify the test was actually failing by checking out the test commit and running it.
- This is the cheapest defense against agents writing tests that always pass (e.g., asserting on a mock that was set up to return the expected value).

## References

- "Building Effective Agents" (Anthropic) — start simple, optimize with evals before adding complexity.
- Kent Beck, *Test-Driven Development: By Example*.
- *Growing Object-Oriented Software, Guided by Tests* (Freeman & Pryce) — outside-in / London school.
- See also: [testing-standard.md](testing-standard.md), [agent-eval-standard.md](agent-eval-standard.md), [e2e-workflow-standard.md](e2e-workflow-standard.md).
