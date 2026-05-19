# Aethos PS — Security Review

> **Owner**: Prahari (Security Engineer)
> **Status**: Skeleton. Populated as each security review completes.
> **Canonical triggers**: [`agent-harness/core/security-review.md`](../../agent-harness/core/security-review.md).

## When Prahari is mandatory

Triggered on every PR that touches:

- Authentication / session handling.
- JWT claims, signing, expiry, refresh, or validation.
- RBAC / ABAC / permission changes.
- Tenant isolation, RLS, or service-role usage.
- Agent tools that read or write protected data.
- External integrations, webhooks, OAuth, payments.
- Secrets, encryption keys, credential storage.
- Infrastructure exposure, CORS, CSP, cookies, network boundaries.

## Aethos-specific checks

- Stripe webhook signature verification (no unsigned callbacks accepted).
- Stripe Connect onboarding return URL validation.
- Supabase RLS policies match application-layer tenant scoping for every tenant table.
- `mask_pii()` called before every LLM invocation.
- Prompt-injection red-team subset in every agent's eval pack (`docs/test/agent_evals/*.yaml`).
- Webhook idempotency: same `event.id` does not double-effect.
- Money-out flows (`bill_pay_agent`) always HITL; never silent execution.
- `accounting_guardian` cannot be disabled at runtime.

## Review log

| Date | PR | Subject | Outcome |
| --- | --- | --- | --- |
| | | | |

## Changelog

### [2026-05-19] — Skeleton created.
