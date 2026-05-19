# Codex Adapter

This project uses the reusable Agent Harness. Codex / OpenAI-coding-agent tools should follow the model-neutral core protocols.

## Load Order

1. `agent-harness/core/operating-principles.md`
2. `agent-harness/core/sdlc-protocol.md`
3. `agent-harness/core/roles.yaml`
4. `agent-harness/core/tdd-protocol.md`
5. `agent-harness/core/testing-standard.md`
6. `agent-harness/core/quality-gates.md`
7. `agent-harness/core/e2e-workflow-standard.md`
8. `agent-harness/core/agent-eval-standard.md`
9. `agent-harness/core/contract-testing.md`
10. `agent-harness/core/observability-standard.md`
11. `agent-harness/core/security-review.md`
12. `agent-harness/core/saas-onboarding-payments.md` (only when touching signup / billing / webhooks)
13. `docs/team/PROJECT_CONTEXT.md`
14. `domain_packs/<domain>/pack.yaml` (if any)
15. `docs/test/e2e_<workflow>.md` for the workflow being changed

## Execution Rules

- Default role is Vishwa (orchestrator) for unassigned requests.
- Create or reuse an issue before tracked edits.
- Outside-in TDD: failing acceptance test is the first commit on the branch.
- For agent changes, update and run the eval pack before opening the PR.
- Trigger Prahari (security) for auth, RBAC, RLS, tenant isolation, agent tools, integrations, payments, webhooks, secrets, or infrastructure exposure.
- Do not close your own issue unless the project explicitly assigns you orchestrator final-review authority.

## Coding Rules

- Inspect existing code before changing patterns.
- Prefer repo-native helpers and conventions.
- Use exact decimal arithmetic for money.
- Scope tenant/user data at every layer when applicable.
- Never commit secrets, raw tokens, temporary passwords, or raw PII.
- Use `rg` for search and small, focused patches for edits.
- Do not revert unrelated user changes.

## Verification

Report:

- Commands run.
- Tests passed (link to e2e scenario IDs and eval pack run).
- Browser/API evidence when applicable.
- Tests not run and why.
- Residual risk.
