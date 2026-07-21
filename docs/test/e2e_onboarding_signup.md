# E2E Scenario — Signup to First Invoice

> Public marketing page → account/tenant provisioning → plan/card → trial
> subscription. Stripe Connect and first invoice are separate, currently
> incomplete proof slices.
> Standard: [`agent-harness/core/saas-onboarding-payments.md`](../../agent-harness/core/saas-onboarding-payments.md) + [`agent-harness/core/e2e-workflow-standard.md`](../../agent-harness/core/e2e-workflow-standard.md).

Evidence status: this is a target scenario. Only the files listed in §9 are
executable evidence; absent mappings and browser-blocked flows are not PASS.

## Workflow

- **Name**: signup-to-first-invoice
- **Entry point**: `${PRODUCTION_URL}/` or `${PRODUCTION_URL}/signup`.
- **Exit state**: Tenant exists, owner has the Tenant Owner catalogue role and
  legacy `owner` projection, trial subscription is active, and the owner lands
  at `/app/copilot`. Connect and first invoice require separate evidence.

## Pre-conditions

- Stripe test-mode keys configured.
- Stripe webhook endpoint reachable (test tunnel).
- Email verification is not part of signup; the backend confirms the owner user.
- Price catalogue configured for 3 tiers × 2 intervals × 5 launch currencies
  (30 Price slots), with unavailable entries surfaced as unavailable.
- Do not claim Stripe automatic-tax calculation: current subscription creation
  does not request automatic tax.
- Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

---

## §1 Happy Path

### §1.1 Public visit and signup

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 1 | Public visitor | Lands on `/` | Static Angular landing page renders; no auth |
| 2 | Visitor | Clicks "Get started" | `/signup` page |
| 3 | Visitor | Enters email, password, tenant name, country | POST `/api/v1/auth/signup` creates/confirms the auth user, tenant (`provisioning`/subscription `incomplete`), owner membership plus Tenant Owner assignment, Stripe customer, and SetupIntent; frontend signs the owner in before plan/card |

### §1.2 Plan selection and trial subscription

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 4 | User | Selects plan and monthly/annual interval | UI selects a configured Price ID in the country-derived currency. Account submit initially stores `plan_tier=starter`, and current start-trial does not update it from the later selection; record this mismatch if a non-Starter price is chosen. |
| 5 | User | Stripe Setup Intent renders (sandbox card prefilled in dev) | Card confirmed via Stripe.js |
| 6 | system | POST `/api/v1/billing/start-trial` → Stripe Subscription with `trial_period_days=14` | Tenant subscription ID/status and trial end are stored; duplicate-submit idempotency must be tested rather than assumed |
| 7 | system | `/api/v1/billing/start-trial` synchronously stores subscription ID/status, trial end, and tenant `active`; later signed Stripe subscription webhooks mirror status idempotently | Trial badge derives from stored status/end. The happy path must not depend on an undocumented reconciliation worker. |

### §1.3 First login and tour

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 8 | User (Alice, now Owner) | Lands on `/app/copilot` | Authenticated shell loads with tenant context and legacy role `owner` |

### §1.4 Optional — Stripe Connect onboarding

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 9 | Alice | `/app/settings` → Stripe Connect → "Connect Stripe" | Owner-only API returns a Stripe Connect OAuth URL |
| 10 | Alice | Completes Connect onboarding in test mode | Current backend config returns to `/settings/billing/connect/return`, which is absent from the Angular route table; mark this step BLOCKED unless the visible browser return succeeds on the deployed build. Do not call the backend callback manually to bypass it. |
| 11 | Alice | Returns to `/app/settings` | Only PASS if the visible UI shows accurate connected/charges/payout status after the real browser callback |

### §1.5 First invoice (full path)

Reuse [`e2e_engagement_to_cash.md`](e2e_engagement_to_cash.md) §1, prefixed with the freshly provisioned tenant. The first-invoice path is the end-to-end smoke for signup correctness.

---

## §2 Variants

- **§2.1 Per market** — repeat §1 with `country` in {US, UK, SG, IN, AU}; verify base currency, tax rate seed, Stripe price in matching currency.
- **§2.2 Skip Connect** — Connect is not required for signup. If platform Stripe
  is configured, invoice send can still create a Payment Link without Connect
  destination routing; PDF-only occurs only when server Stripe is absent.
- **§2.3 Existing email** — signup with an existing email returns a clear 409;
  use the page's separate Sign in navigation. Do not claim automatic resume.
- **§2.4 Billing-management limitation** — there is no `/settings/billing`
  Angular route or self-service plan-change/next-invoice UI. The backend portal
  session endpoint is not wired to a visible control.

---

## §3 Unhappy Paths

| ID | Trigger | Expected behavior |
| --- | --- | --- |
| §3.1 | Card declined (test card `4000 0000 0000 0002`) | UI shows a controlled error; no trial subscription is created. The user, tenant, owner membership, Stripe customer, and SetupIntent already exist from Account step and must be recorded/recoverable. |
| §3.2 | Stripe webhook signature invalid | 400 and no subscription-state mutation; do not claim a dedicated security-log/alert row unless observed |
| §3.3 | Webhook delivered twice (same `event.id`) | Second processed but no double effect; idempotency key recorded |
| §3.4 | Stripe webhook delayed | Start-trial has already persisted subscription state; verify later webhook convergence. No subscription reconciliation worker is currently proven. |
| §3.5 | Subscription creation succeeds but tenant update fails | Current code logs the DB failure and can return subscription success; detect Stripe/tenant divergence and treat it as a recovery blocker. There is no documented provisioning read-only gate/banner. |
| §3.6 | Stripe Connect onboarding abandoned mid-flow | `stripe_connect_status=pending`; Settings shows "Resume Connect onboarding" |
| §3.7 | Stripe Connect `charges_enabled=false` after onboarding | Settings shows pending/needs-more-information and a Complete setup button. Invoice send is not disabled solely by Connect: platform Stripe can still create a non-destination Payment Link. |
| §3.8 | Tax registration/automatic-tax expectation | Current signup/subscription code has no automatic-tax request or registration-warning UI. Validate configured product/tax behavior separately and do not claim a warning. |
| §3.9 | Owner forgets password | `/login` has no self-service recovery UI. Signed-in password change and admin-created-user set-password links do not solve a locked-out owner; use an approved support/admin recovery process and file the product gap. |
| §3.10 | Owner deletes tenant | No Delete Tenant UI exists. Owner-only API cancels the subscription and soft-deletes the tenant; it does not delete user/tenant rows or the Stripe customer. Do not describe it as cascading removal. |
| §3.11 | Prompt injection at signup (e.g., embedded in `tenant_name`) | Must be safely rendered and treated as untrusted data in every later model context; absence of an executable signup-to-agent red-team test is a coverage gap |

---

## §4 Edge Cases

| # | Edge case | Expected behavior |
| --- | --- | --- |
| E1 | User retries Account step or reuses an email | Current duplicate email path returns 409; the documented existing-user idempotency branch is effectively unreachable. Verify no second tenant/customer and provide a recovery path. |
| E2 | User wants a plan currency different from country | Current catalogue currency is derived from tenant country; arbitrary USD selection is not exposed. Do not claim automatic-tax behavior. |
| E3 | Tenant name with emoji / RTL characters | Store/render safely without XSS; verify each actual surface rather than assuming invoice-template inclusion |
| E4 | Country with limited Stripe Connect eligibility | Stripe decides eligibility, but the current missing Angular callback remains a blocker; record the visible provider/UI result |
| E5 | Trial expires or renewal fails mid-action | Stripe controls subscription outcome; current read-only grace gating is not proven. Verify actual webhook/status/UI behavior and file any unrestricted-access gap. |

---

## §5 RBAC Matrix

Signup flow is unauth → owner only. After signup:

| Action | Owner | Admin | Manager | Member | Viewer |
| --- | --- | --- | --- | --- | --- |
| Invite users | ✅ | ✅ | ❌ | ❌ | ❌ |
| Connect Stripe | ✅ | ❌ | ❌ | ❌ | ❌ |
| Change plan in app | ❌ no current UI | ❌ | ❌ | ❌ | ❌ |
| Delete tenant through API | ✅ (no UI) | ❌ | ❌ | ❌ | ❌ |
| Open billing portal in app | ❌ no current UI | ❌ | ❌ | ❌ | ❌ |

This matrix is legacy-role oriented. Signup creates the Tenant Owner catalogue
assignment and projects it to `owner`; there is no Platform Administrator role.
The backend portal endpoint is authenticated but its authorization/UI contract
must be fixed and tested before documenting owner/admin access.

---

## §6 Audit Trail

- Record the auth user ID, tenant ID/status, owner membership and security-role
  assignment, Stripe customer/SetupIntent/subscription IDs, trial end, selected
  Price ID, and deployed SHA in redacted evidence.
- `webhook_events` provides provider-event idempotency/status evidence for
  delivered Stripe events.
- Do not claim generic `events` or `audit_log` signup rows, IP/user-agent audit,
  Connect completion, or first-invoice events unless those exact persisted
  records are observed; the former list was aspirational.

## §7 Performance Budget

| Step | Soft budget |
| --- | --- |
| Signup form submit → tenant exists | p95 < 3s |
| Stripe Setup Intent → subscription active | p95 < 5s |
| Webhook receipt → DB write | p95 < 500ms |
| Stripe Connect redirect roundtrip | p95 < 10s (depends on Stripe) |

## §8 Cleanup / Retention

Retain the Ishantech production validation tenant as requested. Do not call the
delete endpoint or Stripe APIs for cleanup. For a separately authorized
disposable test, the current owner DELETE API cancels the subscription and
soft-deletes the tenant; it does not remove auth users/tenant rows or delete the
Stripe customer. Record residual data instead of asserting it disappeared.

## §9 Executable Test Mapping

The formerly mapped `backend/tests/e2e/test_onboarding_signup.py` and
`frontend/e2e/onboarding-signup.spec.ts` do not exist.

| Existing evidence | Scope and limitation |
| --- | --- |
| `frontend/e2e/00-signup.spec.ts` | One visible-browser three-page happy path against a configurable host; not Connect, recovery, billing management, edge matrix, or first invoice. |
| `frontend/e2e/landing.spec.ts` | Landing/signup navigation smoke. |
| `backend/tests/api/test_signup_and_billing.py` | Signup validation, SetupIntent, and price-catalogue integration; no complete start-trial lifecycle test. |
| `backend/tests/api/test_stripe_connect.py` | Bounded Connect API proof; does not prove the missing Angular return route. |
| `tests/e2e-real/step1-real-signup.js` | Legacy/supplemental step-one script, not the current complete browser workflow. |

No combined executable proof currently covers signup → Connect → first invoice.
The retained production run must use the visible UI only; API-seeded or direct
callback setup is supplemental and cannot convert a BLOCKED browser step into
PASS.

## §10 Evidence Template

See [`agent-harness/templates/E2E_ONBOARDING_REGRESSION.md`](../../agent-harness/templates/E2E_ONBOARDING_REGRESSION.md) for the field-by-field evidence template.
