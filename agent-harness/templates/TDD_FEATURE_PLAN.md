# TDD Feature Plan

Use this template for any feature large enough to need a plan but small enough to not need an ADR. The plan is committed to the feature branch alongside the failing tests so reviewers can audit the TDD discipline.

## Issue

- **Issue ID**:
- **Title**:
- **Owner role**:

## Acceptance Criteria (verbatim from the issue)

- AC1:
- AC2:
- ...

## Scenario coverage

For each AC, name the test that proves it.

| AC | Test type | Test name | Expected initial state |
| --- | --- | --- | --- |
| AC1 | e2e UI | `frontend/e2e/<workflow>.spec.ts::AC1 ...` | red (test.fixme or failing assertion) |
| AC1 | API e2e | `backend/tests/e2e/test_<workflow>.py::test_ac1_...` | red |
| AC2 | integration | `backend/tests/integration/...` | red |
| AC2 | unit | `backend/tests/unit/...` | red |
| AC2 | property | `backend/tests/property/...` | red, if applicable |

## Order of writing

1. Failing acceptance test (commit `test(<scope>): add failing e2e for AC1`).
2. Failing integration test for the service entry point.
3. Failing unit / domain tests, working inward.
4. Implementation, one collaborator at a time, with each step turning the next red test green.
5. Refactor — tests stay green.

## Red-state evidence

Reviewer expectation: the first commit on the branch shows a failing test. Paste the failing run output (one line per failing test) here.

```
$ pytest backend/tests/integration/test_x.py::test_y -x
=== 1 failed in 0.42s ===
test_y FAILED [100%]
> assert ... <expected failure>
```

## Out of scope

- ...

## Risks

- ...

## Related

- ADR: (if any)
- Scenario document: `docs/test/e2e_<workflow>.md`
- Eval pack: `<eval-path>/<agent_name>.yaml` (if agent change)
