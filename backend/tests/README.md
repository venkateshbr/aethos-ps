# Backend Tests

Test taxonomy mirrors [`agent-harness/core/testing-standard.md`](../../agent-harness/core/testing-standard.md). Actual layout (2026-09-03):

```
tests/
  unit/          Pure logic + API contract tests with stubbed DB. No network. Runs in CI (~1,440 tests).
  property/      Hypothesis property tests for invariants (journal balance, money precision). Runs in CI.
  api/           Real-stack tests against a running API on :8011 + real Supabase (markers: api, flow_*, rbac, multi_tenant).
  e2e/           Engagement-to-cash scenario skeleton — still 51 strict-xfail placeholders (#373, #511).
  eval/          Live/network evaluation tests (agent eval live, atomic posting live) — opt-in via env vars.
  evals/         YAML eval-pack runner (only engagement_letter_agent today).
  fixtures/      Test documents (engagement letters, receipts, vendor invoices).
  conftest.py    Shared fixtures.
```

There is no `integration/` or `security/` directory yet; cross-tenant probes live in `tests/api/test_multi_tenant_isolation.py` and `tests/unit/test_employee_erp_firewall*.py` (#505 proposes `tests/security/`).

## Running

```bash
# CI set (no DB needed)
uv run pytest tests/unit/ tests/property/ -q

# Offline agent-eval gate (CI step, writes a drift report)
uv run python -m scripts.agent_eval_gate

# Real-stack API suite (needs .env with Supabase + API on :8011)
set -a && source ../.env && set +a && uv run pytest tests/api -q

# Live evals (needs provider keys)
uv run pytest tests/eval -q

# Engagement-to-cash skeleton (all xfail until implemented)
uv run pytest tests/e2e/test_engagement_to_cash.py -v
```

## xfail posture

Skeleton tests are `xfail(strict=True)`. When a feature lands, remove the marker in the same PR; a passing test still marked xfail fails CI.
