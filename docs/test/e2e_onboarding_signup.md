# E2E Scenario — Signup to First Invoice

> Public marketing page → signup → trial subscription → Stripe Connect (optional) → first invoice sent.
> Standard: [`agent-harness/core/saas-onboarding-payments.md`](../../agent-harness/core/saas-onboarding-payments.md) + [`agent-harness/core/e2e-workflow-standard.md`](../../agent-harness/core/e2e-workflow-standard.md).

## Workflow

- **Name**: signup-to-first-invoice
- **Entry point**: `/` (public landing)
- **Exit state**: Tenant exists, trial subscription active, admin logged in, first invoice sent with Stripe Payment Link.

## Pre-conditions

- Stripe test-mode keys configured.
- Stripe webhook endpoint reachable (test tunnel).
- Resend in dev mode.
- Three Stripe Products created with 5 currency-specific Prices each (Starter, Growth, Pro).
- Stripe Tax enabled.
- Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

---

## §1 Happy Path

### §1.1 Public visit and signup

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 1 | Public visitor | Lands on `/` | Static Angular landing page renders; no auth |
| 2 | Visitor | Clicks "Get started" | `/signup` page |
| 3 | Visitor | Enters email, password, tenant name, country | POST `/api/v1/auth/signup` → Supabase Auth user created; tenant row created with `country`, `base_currency` defaulted from country, `timezone`, `locale` |

### §1.2 Plan selection and trial subscription

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 4 | User | Selects Plan (Starter / Growth / Pro) | Plan stored; Stripe Tax computes inclusive total based on `tenant.country` |
| 5 | User | Stripe Setup Intent renders (sandbox card prefilled in dev) | Card confirmed via Stripe.js |
| 6 | system | POST `/api/v1/billing/start-trial` → Stripe Subscription with `trial_period_days=14` | `tenants.stripe_subscription_id` stored idempotently |
| 7 | system | Stripe `customer.subscription.created` webhook → signature verified → idempotency by `event.id` | Tenant `billing_status=trialing`; trial countdown rendered in app shell |

### §1.3 First login and tour

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 8 | User (Alice, now Owner) | Lands on `/copilot` | Empty-state copilot speaks first: "Drop your most recent engagement letter or invoice and I'll set up your first client." |

### §1.4 Optional — Stripe Connect onboarding

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 9 | Alice | `/settings/stripe` → "Connect Stripe" | Redirect to Stripe Connect OAuth |
| 10 | Alice | Completes Connect onboarding (test mode) | Redirect to `/settings/stripe/return` with `code`; backend exchanges for `stripe_connect_account_id`; `account.updated` webhook syncs `charges_enabled` / `payouts_enabled` |
| 11 | Alice | Returns to settings | UI shows "Connected — payouts to {bank}" |

### §1.5 First invoice (full path)

Reuse [`e2e_engagement_to_cash.md`](e2e_engagement_to_cash.md) §1, prefixed with the freshly provisioned tenant. The first-invoice path is the end-to-end smoke for signup correctness.

---

## §2 Variants

- **§2.1 Per market** — repeat §1 with `country` in {US, UK, SG, IN, AU}; verify base currency, tax rate seed, Stripe price in matching currency.
- **§2.2 Skip Connect** — complete signup without §1.4; verify first invoice path uses PDF-only and manual mark-as-paid.
- **§2.3 Existing email** — signup with an email that already exists → clear error, login link surfaced.
- **§2.4 Upgrade plan during trial** — `/settings/billing` plan change → Stripe subscription updated → next-invoice preview rendered.

---

## §3 Unhappy Paths

| ID | Trigger | Expected behavior |
| --- | --- | --- |
| §3.1 | Card declined (test card `4000 0000 0000 0002`) | Stripe returns failure; UI shows specific message; tenant is NOT created (signup is transactional with billing) |
| §3.2 | Stripe webhook signature invalid | 400; no tenant state change; security log entry; alert after N failures |
| §3.3 | Webhook delivered twice (same `event.id`) | Second processed but no double effect; idempotency key recorded |
| §3.4 | Stripe webhook delayed > N minutes | Reconciliation worker creates tenant state from Stripe API directly |
| §3.5 | Subscription created without webhook delivery in 5 minutes | Tenant `billing_status` stays `provisioning`; banner says "Finalizing billing"; admin actions allowed read-only until reconciled |
| §3.6 | Stripe Connect onboarding abandoned mid-flow | `stripe_connect_status=pending`; Settings shows "Resume Connect onboarding" |
| §3.7 | Stripe Connect `charges_enabled=false` after onboarding | UI surfaces "Stripe needs more info" with the Stripe-provided requirements link; invoice send disabled until cleared |
| §3.8 | First-invoice send before Stripe Tax registration in tenant's country | Stripe Tax warns; tenant can either register or proceed without tax line; per-market policy |
| §3.9 | Owner password reset email lost | Standard recovery flow via Supabase Auth; trace event recorded |
| §3.10 | Owner deletes tenant (admin UI) | All tenant data removed; Stripe customer canceled; webhook for `customer.subscription.deleted` is the source of truth for state |
| §3.11 | Prompt injection at signup (e.g., embedded in `tenant_name`) | Stored verbatim; never interpreted as instruction by any agent (agents always treat user data as data); red-team eval case |

---

## §4 Edge Cases

| # | Edge case | Expected behavior |
| --- | --- | --- |
| E1 | User signs up while a webhook from a previous attempt is still in flight | Idempotency on `email` + `stripe_setup_intent_id`; no duplicate tenant |
| E2 | Currency mismatch (user in India picks Starter USD plan deliberately) | Allowed; Stripe Tax applies; invoice rendered with chosen currency |
| E3 | Tenant name with emoji / RTL characters | Stored verbatim; rendered safely (no XSS); appears in invoice template |
| E4 | Country in CSV-only Stripe Connect region | Connect onboarding still works; Stripe handles the eligibility |
| E5 | Trial expires while user is mid-action | Subscription auto-converts to paid; if card declines, tenant gated to read-only after grace period |

---

## §5 RBAC Matrix

Signup flow is unauth → owner only. After signup:

| Action | Owner | Admin | Manager | Member | Viewer |
| --- | --- | --- | --- | --- | --- |
| Invite users | ✅ | ✅ | ❌ | ❌ | ❌ |
| Connect Stripe | ✅ | ❌ | ❌ | ❌ | ❌ |
| Change plan | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete tenant | ✅ | ❌ | ❌ | ❌ | ❌ |
| View billing portal | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## §6 Audit Trail

- `events`: `tenant.created`, `subscription.created`, `subscription.trialing`, `stripe_connect.connected`, `tenant.first_invoice_sent`
- `webhook_events`: every Stripe event id stored idempotently
- `audit_log`: signup IP, user agent, country detected

## §7 Performance Budget

| Step | Soft budget |
| --- | --- |
| Signup form submit → tenant exists | p95 < 3s |
| Stripe Setup Intent → subscription active | p95 < 5s |
| Webhook receipt → DB write | p95 < 500ms |
| Stripe Connect redirect roundtrip | p95 < 10s (depends on Stripe) |

## §8 Cleanup

- Use admin UI "Delete tenant" — proves cleanup as a feature.
- Stripe-side: cancel test subscription and delete test customer via Stripe API.
- Stripe Connect test account: left intact (Stripe sandbox does not allow programmatic delete).
- Verify: no `tenants` row, no `users` row for this tenant's emails, no `webhook_events` retained beyond audit window.

## §9 Executable Test Mapping

```
backend/tests/e2e/test_onboarding_signup.py::test_§<id>_<slug>
frontend/e2e/onboarding-signup.spec.ts::"§<id> <description>"
```

## §10 Evidence Template

See [`agent-harness/templates/E2E_ONBOARDING_REGRESSION.md`](../../agent-harness/templates/E2E_ONBOARDING_REGRESSION.md) for the field-by-field evidence template.
