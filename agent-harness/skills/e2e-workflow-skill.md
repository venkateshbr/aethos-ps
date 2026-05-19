---
name: e2e-workflow
description: Use when shipping or modifying a business workflow that crosses UI, API, database, and external providers. Produces or updates the scenario document and the executable test suite.
---

# E2E Workflow Skill

Use this skill when the change adds or alters a workflow that delivers user-visible value end-to-end (signup → first invoice, engagement → cash, procure → pay, etc.).

## Required Context

- `agent-harness/core/e2e-workflow-standard.md`.
- `agent-harness/templates/E2E_WORKFLOW_REGRESSION.md`.
- The existing scenario document at `docs/test/e2e_<workflow>.md` if any.
- The project's e2e tool defaults (Playwright for UI by default; pytest+httpx for API e2e).

## Workflow

1. **Write the scenario document** — `docs/test/e2e_<workflow>.md`, using the template. Cover happy / variant / unhappy / edge / RBAC / audit / cleanup.
2. **Map every step to a test name** — section IDs in the document become test names in the suite. Drift between document and tests is forbidden.
3. **Scaffold the tests** — for greenfield, use `xfail(strict=True)` / `test.fixme()` skeletons so the test list is locked from day one.
4. **Implement the workflow** in red-green-refactor cycles, removing markers as each scenario becomes real.
5. **Run with deterministic data** — seed via tests, name with run-IDs, clean up at the end through the admin UI or documented teardown.
6. **Run RBAC matrix** — every role × every action, UI and API.
7. **Run cross-tenant tests** — tenant A's data is invisible to tenant B via every read path.
8. **Run idempotency tests** — replay external events; assert exactly-one effect.
9. **Capture evidence** — pass/fail per scenario, trace IDs, API/DB validation, cleanup confirmation. Attach to the issue or PR.

## Must Do

- Drive the workflow through the **frontend** for any user-facing path — no API-only acceptance.
- Use **sandbox** provider credentials and **official provider test fixtures**.
- Single-session login per test run (storage state reuse).
- Web-first assertions (`expect(locator).toBeVisible()`) — never manual sleeps.
- Role-based locators (`getByRole`, `getByLabel`); reserve `getByTestId` for cases where a role/label is not available.

## Avoid

- Cypress vs Playwright drift — pick one e2e tool per project; default is Playwright.
- Hand-crafted fake webhooks — replay real captured fixtures from the provider.
- Tests that depend on data created by prior runs.
- Tests that pass without exercising the real backend.
- Skipping the cleanup step "because it's just test data."

## Verification

```bash
# UI e2e (Playwright)
npx playwright test --headed --slow-mo=300 frontend/e2e/<workflow>.spec.ts

# API e2e
<project test command> backend/tests/e2e/test_<workflow>.py -v

# RBAC matrix
<project test command> backend/tests/e2e/test_<workflow>_rbac.py -v
```
