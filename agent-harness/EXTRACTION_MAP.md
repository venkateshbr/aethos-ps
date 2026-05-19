# Extraction Map

This harness is extracted from working practices across multiple projects (Transmuter origin; refined for Aethos-class AI-native financial SaaS).

## What Was Extracted

| Practice | Reusable harness artifact |
| --- | --- |
| Vishwa-first issue triage | `core/sdlc-protocol.md`, `core/roles.yaml` |
| Named specialist agents | `core/roles.yaml` |
| Issue lifecycle labels | `core/sdlc-protocol.md`, `templates/ISSUE_TEMPLATES.md` |
| Outside-in TDD discipline | `core/tdd-protocol.md`, `skills/tdd-skill.md`, `templates/TDD_FEATURE_PLAN.md` |
| Prahari security review | `core/security-review.md` |
| Real API/browser acceptance standard | `core/testing-standard.md`, `core/e2e-workflow-standard.md` |
| Router → Service → Repository | `core/architecture-patterns.md` |
| Money, multi-tenancy, AI guardrails | `core/quality-gates.md` |
| Agent evaluation, drift detection, correction loop | `core/agent-eval-standard.md`, `skills/agent-eval-skill.md`, `templates/AGENT_EVAL_PACK.yaml` |
| End-to-end business workflow regression | `core/e2e-workflow-standard.md`, `skills/e2e-workflow-skill.md`, `templates/E2E_WORKFLOW_REGRESSION.md` |
| Frontend design skill | `skills/frontend-design-skill.md` |
| Package/API verification habit | `skills/package-verification-skill.md` |
| Contract testing (consumer-driven, agent-tool schema, provider fixtures) | `core/contract-testing.md` |
| Trace IDs, structured logs, LLM traces, metrics, SLOs | `core/observability-standard.md` |
| Stripe onboarding and webhook regression lessons | `core/saas-onboarding-payments.md`, `templates/E2E_ONBOARDING_REGRESSION.md` |
| "Always validate through frontend" acceptance habit | `core/testing-standard.md`, `core/e2e-workflow-standard.md` |
| Persistent project context docs | `templates/PROJECT_CONTEXT.md` |
| Domain packs | `templates/DOMAIN_PACK.yaml` |
| Codex/Claude/Gemini/OpenCode instructions | `adapters/*` |

## External References Cited

- Anthropic — "Building Effective Agents" (engineering blog): simplicity, transparency, tool design; evaluator-optimizer; when to add complexity.
- Anthropic — Tool use protocol (client vs server tools, `tool_use`/`tool_result`, strict tool use).
- PydanticAI Evals — `Dataset`, `Case`, `Evaluator` (`IsInstance`, `LLMJudge`, custom).
- Playwright Best Practices — role-based locators, web-first assertions, single-session login, sharded CI.
- Pact — consumer-driven contract testing, broker, can-i-deploy; message-vs-behavior caveat.
- Hypothesis — property-based testing, `@given`, `@composite`, shrinking; financial-invariant examples.
- Langfuse — LLM-as-judge + human annotations + custom evaluators; prompt-update regression detection.

## What Was Deliberately Not Extracted

- Real secrets or credentials.
- Production tenant/customer data.
- Temporary passwords.
- Project-specific hostnames as default harness values.
- Product-specific implementation details that would confuse other projects.

## How To Extend

Add new protocols only when they apply to multiple projects. Put product-specific facts in the target project's `docs/team/PROJECT_CONTEXT.md`.

Good additions:

- A reusable mobile app testing gate.
- A reusable data migration checklist.
- A reusable SOC2 evidence checklist.
- A reusable agent prompt-engineering review.

Poor additions:

- A single project's staging URL.
- A one-off customer workflow.
- Any secret or copied production config.
