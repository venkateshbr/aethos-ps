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

## Audit — 2026-05-23 (Issue #72 — Pre-launch full audit)

**Reviewer**: Prahari
**Scope**: All backend services, agents, migrations, Stripe billing/Connect, HITL, RBAC, RLS, auth, webhooks
**Branch**: feat/72-security-audit

| Check | Result | Notes |
|---|---|---|
| JWT validation | PASS | HS256 enforced in `app/core/auth.py:53`. Secret from `settings.supabase_jwt_secret` (env-loaded). No hardcoded secret found. `alg:none` rejected by python-jose. |
| RLS coverage | WARN | 12/13 tenant-scoped tables have RLS. `tenants` table missing — fixed in migration 0015. `fx_rates` is global (intentional, no PII). `webhook_events` table referenced in code but had no migration — fixed in 0015. |
| Webhook signature | PASS | Raw `bytes` read before parsing. `stripe.Webhook.construct_event()` called first. Signature failure returns HTTP 400 (fail-closed). Full event payload never logged. |
| Payment idempotency | PASS | `provider_event_id` checked in `webhook_events` before dispatch. Duplicate events return 200 immediately. `stripe_payment_intent_id UNIQUE` constraint at DB level on `payments` table. |
| Connect OAuth CSRF | PASS | `state` parameter compared to JWT-derived `tenant_id` in `stripe_connect.py:85`. Mismatch returns HTTP 400. Only `owner` role can initiate Connect. |
| Agent tenant scoping | PASS | All agent tools enforce `.eq("tenant_id", self.deps.tenant_id)` in every query. `AgentDeps` carries `tenant_id` from authenticated request context. |
| PII masking | WARN | `engagement_letter_agent`, `vendor_invoice_agent`, `expense_extractor_agent` call `mask_pii()` before LLM. `CopilotAgent` did not call `mask_pii()` on user message — fixed in `graph.py`. |
| accounting_guardian coverage | FAIL (fixed) | `invoices_service` uses canonical `post_journal()` — correct. `bills_service._post_journal()` bypassed the guardian — fixed by removing it and routing through `post_journal()`. |
| No live secrets in source | PASS | `grep sk_live` — clean. All keys read from `Settings` (pydantic-settings). `.env` not committed. |
| No PII in logs | PASS | Email excluded from log fields in `auth.py`. Agents log `tenant_id` and `suggestion_id` only. Webhook handler logs `event_id` and `event_type` only. LLM calls log token counts, not content. |
| Security headers | WARN | No `X-Content-Type-Options`, `X-Frame-Options`, or `Strict-Transport-Security` middleware. Mitigated at Cloud Run + Vercel edge. Add `SecurityHeadersMiddleware` in Week 6. |
| Rate limiting | WARN | No rate limiter on `/auth/signup` or `/billing/start-trial`. Mitigated by Supabase Auth's built-in rate limiting. Add `slowapi` in Week 6. |
| Service role scope | WARN | `get_service_role_client()` used across all business endpoints. Application-layer `tenant_id` filter compensates. Migrate reads to anon client in Week 6. |
| Stripe Connect error detail | FAIL (fixed) | `stripe_connect.py:100` leaked `BillingError.__str__()` in HTTP 502 body. Fixed to return a generic message and log internally. |
| Billing portal open redirect | FAIL (fixed) | `BillingPortalRequest.return_url` accepted any URL. Fixed with `@field_validator` enforcing same-origin against `settings.frontend_base_url`. |
| Error detail leakage | FAIL (fixed) | `engagements.py:139` forwarded `ValueError` message (containing internal `tenant_id`) to client in 404. Fixed to log internally and return a generic message. |
| deprecated datetime.utcnow() | WARN (fixed) | `bill_payments_service.py` used `datetime.utcnow()` (deprecated Python 3.12). Replaced with `datetime.now(UTC)`. |

### Findings

**FINDING-001: accounting_guardian bypass in bills_service** (CRITICAL — fixed)
- Severity: Critical | OWASP: A04 Insecure Design | CWE: CWE-284
- Location: `backend/app/services/bills_service.py` — `_post_journal()` method (removed)
- Description: `BillsService._post_journal()` inserted `journal_entries` and `journal_lines` directly without calling `accounting_guardian.validate_journal()`. Bill approval could post an imbalanced GL entry, post to a locked period, or post to non-existent account IDs.
- Impact: Financial data integrity violation. Balance-check, period-lock, and account-validity gates all bypassed.
- Fix: Removed `_post_journal()`. `approve_bill()` now routes through canonical `post_journal()` in `journal_helper.py` which calls `validate_journal()` as its first step.

**FINDING-002: tenants table missing RLS** (HIGH — fixed)
- Severity: High | OWASP: A01 Broken Access Control | CWE: CWE-284
- Location: `backend/supabase/migrations/0001_tenants_auth.sql` (3 of 4 tables had RLS; `tenants` did not)
- Description: An anon-key Supabase client could SELECT all tenants rows, including Stripe customer IDs, subscription status, and plan information for every tenant on the platform.
- Impact: Tenant enumeration. Stripe customer IDs exposed.
- Fix: Migration 0015 adds `ALTER TABLE tenants ENABLE ROW LEVEL SECURITY` with a deny-all restrictive policy.

**FINDING-003: webhook_events table has no migration** (HIGH — fixed)
- Severity: High | OWASP: A05 Security Misconfiguration | CWE: CWE-1188
- Location: `backend/app/repositories/tenant_repo.py:145-177`
- Description: `TenantRepository.get_webhook_event()` and `record_webhook_event()` reference `webhook_events` table that has no migration. On a fresh Supabase instance, the idempotency check silently fails and Stripe webhook events process twice.
- Fix: Migration 0015 creates the table with RLS deny-all.

**FINDING-004: CopilotAgent sends raw user message to Anthropic without mask_pii()** (MEDIUM — fixed)
- Severity: Medium | OWASP: A02 Cryptographic Failures | CWE: CWE-312
- Location: `backend/app/agents/copilot/graph.py:204` (before fix)
- Description: User message passed directly to Anthropic API. SSNs, card numbers, or emails in chat would be sent to an external LLM in plain text.
- Fix: `mask_pii(user_message)` called before constructing the messages list.

**FINDING-005: Billing portal return_url open redirect** (MEDIUM — fixed)
- Severity: Medium | OWASP: A01 Broken Access Control | CWE: CWE-601
- Location: `backend/app/models/auth.py:47-53` (before fix)
- Description: `BillingPortalRequest.return_url` accepted any string URL. Could redirect user to attacker-controlled domain after billing portal session.
- Fix: Pydantic `@field_validator` enforces same-origin check against `settings.frontend_base_url`.

**FINDING-006: Stripe Connect error detail leakage** (LOW — fixed)
- Severity: Low | OWASP: A05 Security Misconfiguration | CWE: CWE-209
- Location: `backend/app/api/v1/endpoints/stripe_connect.py:100` (before fix)
- Description: `BillingError.__str__()` forwarded in HTTP 502 response body.
- Fix: Generic user-facing message; full detail logged server-side.

**FINDING-007: Internal tenant_id in 404 response for invoice drafting** (LOW — fixed)
- Severity: Low | OWASP: A05 Security Misconfiguration | CWE: CWE-209
- Location: `backend/app/api/v1/endpoints/engagements.py:139` (before fix)
- Description: `ValueError` from `invoice_drafter_agent.py:105` included `tenant_id` UUID forwarded to 404 HTTP response.
- Fix: Warning logged internally; response returns generic message.

**FINDING-008: deprecated datetime.utcnow() in bill_payments_service** (LOW — fixed)
- Severity: Low | OWASP: A06 Vulnerable Components | CWE: CWE-563
- Location: `backend/app/services/bill_payments_service.py:166, 187, 239, 285`
- Fix: Replaced with `datetime.now(UTC)` throughout.

### Deferred findings (WARN — not blocking pre-launch)

1. No `X-Content-Type-Options` / `X-Frame-Options` / HSTS headers in FastAPI middleware. Mitigated at Cloud Run + Vercel edge. Add `SecurityHeadersMiddleware` in Week 6.
2. No rate limiter on `/auth/signup` or `/billing/start-trial`. Mitigated by Supabase Auth's built-in rate limiting. Add `slowapi` in Week 6.
3. `get_service_role_client()` used for all business endpoints. RLS compensated by application-layer `tenant_id` filter. Migrate reads to anon client in Week 6.
4. Three pre-existing test stubs failing: `test_payment_idempotency_skips_duplicate`, `test_connect_oauth_url_includes_client_id_and_state`, `test_exchange_connect_code_returns_account_id` — references `StripeService` methods not yet implemented. Requires Karya.

### Fixed in this PR

- `bills_service._post_journal()` removed; `approve_bill()` routes through canonical `post_journal()` (accounting_guardian L3)
- Migration 0015: `tenants` table RLS enabled (deny-all restrictive policy)
- Migration 0015: `webhook_events` table created with RLS
- `CopilotAgent` — `mask_pii()` applied to user message before LLM call
- `BillingPortalRequest.return_url` — same-origin validator
- `stripe_connect.py` — generic error message for OAuth exchange failure
- `engagements.py` — safe 404 message for invoice drafting errors
- `bill_payments_service.py` — `datetime.utcnow()` replaced with `datetime.now(UTC)` (4 locations)

## Re-audit — 2026-06-12 (Issue #72 closure)

**Reviewer**: Prahari (automated)
**Scope**: Delta review since 2026-05-23 audit, plus resolution of deferred items.

### New findings (all fixed)

| ID | Severity | Title | Status |
|---|---|---|---|
| R-001 | Medium | `code_sequences` table missing RLS (has tenant_id) | FIXED — migration 0022 |
| R-002 | Low | `fx_rates` table missing RLS (global data) | FIXED — migration 0022 (read-only for auth users) |
| R-003 | Low | `procrastinate_*` tables missing RLS | FIXED — migration 0022 (deny-all restrictive) |
| R-004 | Low | Date parse errors leaked in HTTP responses | FIXED — generic messages |
| R-005 | Medium | Employee service leaks email + auth error in response body | FIXED — generic message, log internally |
| R-006 | Medium | No security response headers (HSTS, X-Frame-Options) | FIXED — SecurityHeadersMiddleware in main.py |

### Still deferred (acceptable pre-launch)

1. No application-level rate limiting on `/auth/signup` or `/public/invoices/{token}`. Mitigated by Supabase Auth rate limiting and 192-bit public tokens.
2. Service-role client used on all endpoints. Mitigated by application-layer tenant_id filter in every repository. Architectural change planned post-launch.

## Changelog

### [2026-05-19] — Skeleton created.
### [2026-05-23] — Pre-launch full audit completed (issue #72). 8 findings — 2 critical/high, 2 medium, 4 low/warn. All critical and medium fixed inline; 4 deferred to Week 6.
### [2026-06-12] — Re-audit and closure. 6 additional findings found and fixed. 2 items deferred as acceptable pre-launch risk. SecurityHeadersMiddleware added. RLS hardening migration 0022 for 3 tables.
