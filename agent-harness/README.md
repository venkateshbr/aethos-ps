# Agent Harness

A reusable AI operating system for software projects. It packages issue-first, role-based, TDD-disciplined, eval-gated software delivery into a portable harness that can be copied into any repository and used with Codex, Claude Code, Gemini, OpenCode, or other coding agents.

The harness is intentionally model-neutral. The core protocols define how work should happen; the adapters translate those protocols into the files each agent tool naturally reads.

**Version**: 0.2.0 — adds TDD protocol, agent-evaluation standard, end-to-end workflow standard, observability standard, and contract-testing standard.

## What It Provides

- **Issue-first SDLC** with explicit lifecycle states.
- **Named specialist roles** for requirements, architecture, design, implementation, security, testing, deployment, observability, and final review.
- **Outside-in TDD discipline** — failing acceptance test first, then layer by layer.
- **Agent-evaluation standard** — deterministic eval packs, drift detection, correction-loop integration, red-team sets, calibration checks.
- **End-to-end workflow standard** — scenario documents + executable mapping + coverage taxonomy (happy / variant / unhappy / edge / RBAC / audit / idempotency).
- **Contract testing** — consumer-driven contracts for inter-service boundaries, agent-tool schema tests, provider fixture pinning.
- **Observability standard** — trace IDs, structured logs, LLM-trace spans, metrics, SLOs.
- **Security review gates** — Prahari-style triggers and checklist.
- **SaaS onboarding / payments / webhook / RBAC / tenant-cleanup regression playbook.**
- **Architecture and code quality patterns.**
- **Reusable skill templates** — TDD, agent eval, e2e workflow, frontend design, package verification.
- **Model adapters** for Codex, Claude Code, Gemini, OpenCode.
- **Project bootstrap templates** — project context, domain pack, issue templates, PR template, environment configuration, workflow regression, agent eval pack, TDD feature plan.

## Directory Layout

```text
agent-harness/
  README.md
  HARNESS_MANIFEST.yaml
  EXTRACTION_MAP.md
  core/
    operating-principles.md
    sdlc-protocol.md
    roles.yaml
    tdd-protocol.md                  # new in 0.2.0
    testing-standard.md              # refreshed
    quality-gates.md                 # refreshed
    architecture-patterns.md
    security-review.md
    e2e-workflow-standard.md         # new in 0.2.0
    agent-eval-standard.md           # new in 0.2.0
    contract-testing.md              # new in 0.2.0
    observability-standard.md        # new in 0.2.0
    saas-onboarding-payments.md
  skills/
    SKILL_TEMPLATE.md
    tdd-skill.md                     # new in 0.2.0
    agent-eval-skill.md              # new in 0.2.0
    e2e-workflow-skill.md            # new in 0.2.0
    frontend-design-skill.md
    package-verification-skill.md
  adapters/
    codex/AGENTS.md
    claude/CLAUDE.md
    gemini/GEMINI.md
    opencode/AGENTS.md
  templates/
    PROJECT_CONTEXT.md
    DOMAIN_PACK.yaml
    ISSUE_TEMPLATES.md
    PR_TEMPLATE.md
    ENVIRONMENT_CONFIGURATION.md
    E2E_ONBOARDING_REGRESSION.md
    E2E_WORKFLOW_REGRESSION.md       # new in 0.2.0 — generalized workflow template
    AGENT_EVAL_PACK.yaml             # new in 0.2.0
    TDD_FEATURE_PLAN.md              # new in 0.2.0
```

## Quick Start In Another Project

1. Copy the harness into the target repo:

   ```bash
   cp -R agent-harness /path/to/target-repo/agent-harness
   ```

2. Pick the adapter files for the tools you use:

   ```bash
   cp agent-harness/adapters/codex/AGENTS.md /path/to/target-repo/AGENTS.md
   cp agent-harness/adapters/claude/CLAUDE.md /path/to/target-repo/CLAUDE.md
   cp agent-harness/adapters/gemini/GEMINI.md /path/to/target-repo/GEMINI.md
   ```

   For OpenCode, copy `agent-harness/adapters/opencode/AGENTS.md` or paste it into the workspace instructions.

3. Create project-specific context:

   ```bash
   mkdir -p docs/team docs/test domain_packs/<your-domain> .github
   cp agent-harness/templates/PROJECT_CONTEXT.md docs/team/PROJECT_CONTEXT.md
   cp agent-harness/templates/DOMAIN_PACK.yaml domain_packs/<your-domain>/pack.yaml
   cp agent-harness/templates/PR_TEMPLATE.md .github/pull_request_template.md
   ```

4. Customize the placeholders:

   - Repository URL and issue tracker.
   - Stack and package manager commands.
   - Domain pack name.
   - Security-sensitive areas.
   - Real acceptance test commands.
   - Design system and frontend conventions.
   - Deployment and environment docs.
   - LLM observability backend (Langfuse / Pydantic Logfire / equivalent).
   - Eval-pack path and agent registry.

5. Ask every agent to read:

   - `AGENTS.md` or its model-specific equivalent.
   - The full core/* set (load order is defined in each adapter).
   - `docs/team/PROJECT_CONTEXT.md`.
   - Any domain-specific architecture/design/test docs.

## Recommended Adoption Order

1. Start with `core/operating-principles.md` and `core/sdlc-protocol.md`.
2. Add `roles.yaml` so agents know which hat they are wearing.
3. Add `core/tdd-protocol.md` and `core/testing-standard.md` together — they define the working discipline.
4. Add `core/quality-gates.md` and `core/security-review.md`.
5. Add `core/e2e-workflow-standard.md` and the first scenario document at `docs/test/e2e_<your-flagship-workflow>.md`.
6. Add `core/agent-eval-standard.md` and one eval pack per in-scope agent before you ship the first agent.
7. Add `core/contract-testing.md` and `core/observability-standard.md`.
8. Add architecture and design skills once the repo has enough patterns.
9. Add model adapters only after the core docs are stable.

## Project Customization Rules

- Keep the core protocol generic.
- Put project facts in `docs/team/PROJECT_CONTEXT.md`.
- Put domain entities and workflow gates in `domain_packs/<domain>/pack.yaml`.
- Put business-workflow scenarios in `docs/test/e2e_<workflow>.md`.
- Put agent eval packs in `<eval-path>/<agent_name>.yaml`.
- Put model-specific quirks in `adapters/<tool>/`.
- Never store secrets in the harness.
- Prefer examples with placeholders over real production values.

## How To Use During Work

Every request should start the same way:

1. Vishwa triages the request.
2. Create or reuse an issue.
3. Identify required roles and gates.
4. Load the narrowest relevant context (per the adapter's Load Order).
5. **Write the failing acceptance test first** (TDD discipline).
6. Implement with repo-native patterns, one inner layer at a time.
7. For agent changes, **update the eval pack and run it before opening the PR**.
8. Verify with real acceptance evidence — frontend + backend + integration state.
9. Document residual risk and close through the issue lifecycle.

For customer onboarding, billing, role access, and other revenue-critical flows, acceptance must include the full user journey through the frontend, then backend validation that the records, totals, subscriptions, and permissions are correct.

## What's New In 0.2.0

The 0.2.0 release codifies practices that were implicit in 0.1.0:

- **TDD as the default discipline**, with outside-in for user-facing work and inside-out / property-based for pure logic.
- **Agent evaluation** is now a first-class gate, not an afterthought. Every in-scope agent has a versioned eval pack with golden / correction / red-team / HITL-routing subsets.
- **End-to-end workflows** are defined as scenario documents that are linked one-to-one to executable tests. Drift between document and tests is a QA-gate failure.
- **Contract testing** clarifies where Pact-style contracts beat e2e tests, and where they do not.
- **Observability** is wired in from the start — every endpoint, every agent run, every webhook gets a trace.

## Naming

You can call this an **Agent Harness**, **AI Operating System**, or **Agentic SDLC Harness**. In code and docs, `agent-harness` is short, portable, and tool-neutral.
