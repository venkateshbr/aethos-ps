# Gemini Adapter

This project uses the reusable Agent Harness. Gemini should follow the core protocols and use this adapter for Gemini-specific project behavior.

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

## Rules

- Vishwa is the default role.
- Create/reuse an issue before changing tracked files.
- Outside-in TDD: failing acceptance test first.
- Follow the role pipeline and lifecycle labels.
- For agent changes, update and run the eval pack before opening the PR.
- Use existing architecture and design patterns.
- Verify current package/API behavior before integration code.
- Never log or return JWTs, API keys, secrets, or raw PII.

## Completion Format

Include:

- Summary.
- Files changed.
- Verification (test runs, eval scores, e2e scenarios touched).
- Security / review gates passed.
- Residual risk.
