---
name: tdd
description: Use for every feature or bug-fix change. Drives outside-in TDD — failing acceptance test first, then failing tests at each inner layer, then implementation, then refactor.
---

# TDD Skill

Use this skill when the task matches any tracked feature, bug-fix, or refactor with observable behavior.

## Required Context

- Read `agent-harness/core/tdd-protocol.md`.
- Read the project's testing tools (in `docs/team/TEST_STRATEGY.md` or equivalent).
- Read or write the scenario document (`docs/test/e2e_<workflow>.md`) if this touches a business workflow.

## Workflow

1. **Acceptance first** — write the failing e2e (or API e2e) test for the user-visible behavior. Commit with `test(<scope>): add failing e2e for <story>`.
2. **Drop one layer** — write the failing integration test at the service-layer entry point. Commit.
3. **Continue inward** — repository, gateway, domain, unit, in that order. Each test red → minimal code → green → next test.
4. **Property tests** — for money, journal, parsing, or anything with an enumerable invariant, write a Hypothesis property test alongside the example tests.
5. **Refactor** — only when all relevant tests are green. The refactor commit must keep them green.
6. **Verify** — run the full touched-file test set; confirm coverage on touched files did not drop.

## Must Do

- The first commit on the branch is a failing test, or the PR description justifies why not.
- Tests are named after the scenario document section IDs where applicable.
- For bug fixes, the regression test must fail on the unfixed code and pass on the fix — paste the red-state output in the PR description.
- For greenfield work where the code does not yet exist, the regression suite is written as `xfail(strict=True)` (pytest) or `test.fixme()` (Playwright) skeletons covering the full scenario document.

## Avoid

- Writing tests after the code.
- Mocking the database or downstream collaborators that are part of the system under test.
- Asserting on what the mock was set up to return (the test must exercise real behavior).
- Over-specified tests that lock in implementation details — assert on outputs, not internals.
- Removing `xfail(strict=True)` markers without making the test green for the right reason.

## Verification

```bash
# Backend
<project test command> --tb=short --cov=<touched-paths>

# Frontend e2e
npx playwright test --headed --slow-mo=300 <touched-spec>

# Property
<project test command> -k property
```
