# Claude Code Adapter

This project uses the reusable Agent Harness. Claude Code should follow the
model-neutral core protocols and use this adapter for Claude-specific behavior.

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
14. `domain_packs/<domain>/pack.yaml` (project domain pack, if any)
15. The relevant scenario document for the workflow being changed: `docs/test/e2e_<workflow>.md`

## Work Protocol

- Default role is Vishwa (orchestrator).
- Open or reuse an issue before tracked edits.
- Practice outside-in TDD: failing acceptance test first, then drop one layer at a time.
- For agent changes, update the eval pack at `<eval-path>/<agent_name>.yaml` and run it before opening the PR.
- Keep implementation narrow and evidence-backed.
- Ask a clarifying question only when a safe assumption is not possible (95% confidence rule).
- Use the security review triggers exactly as defined in [`core/security-review.md`](../../core/security-review.md).

## Claude Code Notes

- Prefer concise plans, then execute.
- Use existing project commands rather than inventing toolchains.
- Keep final responses focused on changed files, verification evidence, residual risk.
- Do not expose secrets in logs or responses.
- When delegating to a sub-agent (Task tool), pass the file paths and the precise scope — never delegate understanding.

## Test-first checklist (before opening PR)

- [ ] Failing acceptance test was the first commit on the branch (or PR description justifies why).
- [ ] All gates in [`core/quality-gates.md`](../../core/quality-gates.md) applicable to the change are green.
- [ ] Scenario document at `docs/test/e2e_<workflow>.md` was updated if the workflow changed.
- [ ] Eval pack at `<eval-path>/<agent_name>.yaml` was updated and run, if an agent changed.
- [ ] Verification evidence is in the PR body.
