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
| 2026-05-19 | [#17](https://github.com/venkateshbr/aethos-ps/pull/17) / [#19](https://github.com/venkateshbr/aethos-ps/pull/19) | Stripe SaaS signup — Setup Intent, trial subscription, webhook handler, billing portal | **PASS** — webhook sig on raw body ✅, idempotency via provider_event_id ✅, no secret hardcoding ✅, no payload logging ✅, tenant isolation via JWT-derived tenant_id ✅, no float money ✅. Minor: duplicate-email 503 message could be friendlier (UX only, not a security issue). |

## Changelog

### [2026-05-19] — Skeleton created.
