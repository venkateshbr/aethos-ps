# OpenCode Adapter

Use this as the OpenCode project instruction file or paste it into the OpenCode workspace instructions.

## Agent Harness — Load Order

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

## Default Behavior

- Act as Vishwa unless the user assigns a different role.
- Create or reuse an issue before tracked edits.
- Outside-in TDD: failing acceptance test first.
- For agent changes, update and run the eval pack before opening the PR.
- Keep changes scoped to the issue.
- Preserve unrelated local changes.
- Trigger Prahari (security) for security-sensitive work.
- Use Aksha-quality verification for product workflows.

## Guardrails

- No secrets in commits or responses.
- No raw PII to external LLMs.
- No mock-led acceptance for product workflows.
- No service-role/admin shortcuts for user-facing paths unless explicitly reviewed.
