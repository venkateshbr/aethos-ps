# Backend Tests

Test taxonomy mirrors [`agent-harness/core/testing-standard.md`](../../agent-harness/core/testing-standard.md).

```
tests/
  unit/          Pure logic. No I/O. < 1s per test.
  integration/   Real DB + real services. < 10s per test.
  e2e/           Full stack against a running API. < 60s per test.
  property/      Hypothesis property tests for invariants (money, accounting, parsing).
  evals/         PydanticAI Evals — agent eval packs from docs/test/agent_evals/.
  security/      RLS, RBAC, tenant isolation, cross-tenant access tests.
  fixtures/      Test data (PDFs, JSONs). Deterministic, named for cleanup.
  conftest.py    Pytest fixtures (tenants, Decimal helpers, balanced journals, agent mocks).
```

## TDD posture

All skeleton tests in this suite are `xfail(strict=True)` until the relevant feature ships. When a feature lands:

1. The implementing agent (Karya) removes the `xfail` marker.
2. Re-runs the test — it should pass.
3. `xfail_strict = true` in `pyproject.toml` ensures that any accidental "test passes while still marked xfail" fails CI.

## Running

```bash
# All tests
uv run pytest

# Just the engagement-to-cash skeleton
uv run pytest tests/e2e/test_engagement_to_cash.py -v

# Property tests
uv run pytest -m property -v

# Eval packs
uv run pytest tests/evals/ -v
```

## What is here on day one

- Skeleton tests for every section in [`docs/test/e2e_engagement_to_cash.md`](../../docs/test/e2e_engagement_to_cash.md). All marked `xfail(strict=True)`.
- Property tests for the journal-balance invariant (I1) and money precision (I6).
- Skeleton eval for `engagement_letter_agent`.
- `conftest.py` with the basic fixtures the harness expects.

## What is NOT here

- Any implementation of services, repositories, or routers.
- Any real DB connectivity (the integration/e2e tests will need that wired by Sthira when the backend is bootstrapped).
- Real fixture files (PDFs etc.) — paths are referenced in the eval packs and the e2e scenarios, but the actual files are created when the relevant feature ships.
