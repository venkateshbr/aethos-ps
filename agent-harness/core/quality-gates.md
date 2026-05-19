# Quality Gates

These are the non-negotiable gates the QA role enforces before promoting an issue to `status:in-review`. Project-specific gates layer on top of these via the domain pack.

## Confidence Gate

Do not modify code until confidence is at least 95%.

If confidence is lower:

- Inspect code.
- Read docs.
- Run focused searches.
- Ask one concise clarification question if needed.

## TDD Gate

See [tdd-protocol.md](tdd-protocol.md).

- The first commit on the feature branch is a failing test, or the PR description justifies why.
- Every bug fix lands with a regression test that fails on the unfixed code and passes on the fix.
- New features for greenfield work land as `xfail(strict=True)` / `test.fixme()` skeletons before any implementation code.
- Coverage on touched files does not decrease.

## Package Verification Gate

Before using a third-party API, library, CLI, or SDK:

- Check installed package versions when available.
- Prefer official docs or source code.
- Verify import paths, method signatures, and required configuration.
- Document assumptions when version-specific behavior matters.

## Money Gate

For financial domains:

- Database: fixed precision decimal, for example `NUMERIC(15,2)` (or `(15,4)` where higher precision is required, e.g., FX).
- Backend: exact decimal type, never floating point.
- API: serialize money as strings.
- Tests: assert exact decimal totals and reconciliation.
- **Property test**: a Hypothesis property test exists for every change that touches a journal-balance, money-arithmetic, or rounding code path.
- **Reversal-only**: posted financial transactions are immutable; corrections are reversing entries, not edits.

## Multi-Tenant Gate

For SaaS or tenant-scoped systems:

- Every tenant-owned table has `tenant_id`.
- Every query is scoped by tenant.
- Database policies enforce tenant isolation when supported (RLS).
- Service-role/admin clients are isolated to intentional admin workflows.
- Cross-tenant access tests exist for every high-risk endpoint (read, write, list-filter manipulation, direct URL navigation).

## AI / Agent Gate

See [agent-eval-standard.md](agent-eval-standard.md).

- Core product functionality must degrade gracefully when AI is unavailable.
- External LLM calls are traced (Langfuse / Pydantic Logfire / equivalent).
- No raw PII is sent to external LLMs — masked at the call site.
- Agent write actions require HITL approval unless explicitly classified as safe.
- **Eval gate**: any prompt, tool, schema, or model change ships with an updated eval pack; average score and pass rate do not regress.
- **Drift gate**: nightly eval against a frozen dataset; alerts on score drop.
- **Replay gate**: a captured failing trace can be replayed deterministically against the current code; this is the basis for the correction loop.
- **Confidence calibration**: if the agent reports 0.9+ confidence but evals score it < 0.7, HITL gating must tighten before the agent is allowed at L3 autonomy.

## Customer Onboarding / Payments Gate

For signup, subscription, payment, webhook, tenant provisioning, or billing portal work:

- Security review is required (see [security-review.md](security-review.md)).
- Use sandbox credentials and provider test fixtures during development.
- Verify webhook signatures; never trust unsigned provider callbacks.
- Store provider customer/subscription IDs idempotently.
- Make provisioning idempotent for duplicate webhook delivery — replay the same event twice in tests.
- Test the public frontend flow first, then validate backend records.
- Verify the initial admin can log in and configure the tenant.
- Verify billing status is visible to both tenant admins and platform admins.
- Document cleanup for demo tenants and provider-side test customers.

See also: [saas-onboarding-payments.md](saas-onboarding-payments.md), [templates/E2E_WORKFLOW_REGRESSION.md](../templates/E2E_WORKFLOW_REGRESSION.md).

## RBAC Regression Gate

For role or permission work:

- Test through the frontend as each role.
- Validate forbidden UI actions are hidden or disabled.
- Validate forbidden API calls return 403 or 404 — never 200 with empty results, never 500.
- Test direct URL access, not only navigation menus.
- Confirm dashboards and detail pages only show permitted data.

## Concurrency / Idempotency Gate

For workflows with shared state (period close, billing run, invoice numbering, autonomy promotion) and any consumer of external events:

- Two clients hitting the same record do not corrupt state — race-loser gets a useful error, not a silent overwrite.
- Replaying the same external event (idempotency key) twice causes one effect, not two.
- Idempotency keys are stored and consulted on every write that accepts them.

## Observability Gate

See [observability-standard.md](observability-standard.md).

- Every new endpoint emits a trace, structured logs, and the relevant metrics.
- Every new agent emits LLM-trace spans with prompt version, model version, token usage, and cost.
- No secrets, raw PII, or credentials in logs or traces.

## Contract Gate

See [contract-testing.md](contract-testing.md).

- Boundaries you control on both ends → consumer-driven contract tests (e.g., Pact).
- External provider boundaries → pinned API version + fixture-driven tests on the fields you depend on.
- Agent ↔ tool boundaries → schema tests in the agent eval pack.
- OpenAPI / schema diff: breaking change blocks PR unless explicitly approved.

## E2E Workflow Gate

See [e2e-workflow-standard.md](e2e-workflow-standard.md).

- Every shipped business workflow has a scenario document at `docs/test/e2e_<workflow>.md`.
- Every scenario step maps to at least one test.
- Coverage taxonomy (happy, multi-variant, unhappy-user, unhappy-system, unhappy-auth, unhappy-concurrency, unhappy-money, unhappy-agent, audit, idempotency) is satisfied.

## Definition of Done

An issue is Done when **all applicable gates above are green**, the QA role has signed off, and the orchestrator (Vishwa-equivalent) has reviewed the PR and the verification evidence.
