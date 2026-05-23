# Aethos PS — Pilot Readiness Evidence

> **Owner**: Aksha (SDET) · **Source**: All tests run against real Supabase `glcljucaayeesvrsjths`, port 8011, Stripe sandbox, real OpenRouter (Gemma free → Haiku paid).
>
> One-line evidence pointer per capability. Test IDs are pytest node ids. "PASS" = green on the run dated in §0.

## 0. Provenance

| Run | Date | Stack | Result |
|---|---|---|---|
| R1 | 2026-05-23 | local backend :8011 + real Supabase + real OpenRouter | **290 passed, 6 xfailed, 0 failures** |

## 1. Foundation (security + auth)

| ID | Capability | Status | Evidence |
|---|---|---|---|
| C2 / C31 | Multi-tenant isolation | PASS | `tests/api/test_multi_tenant_isolation.py::test_clients_get_returns_404_for_tenant_b_id` + 8 more in that file (R1) |
| C2 / #90 | X-Tenant-ID spoof rejected | PASS | `tests/api/test_tenant_membership_check.py` (10 tests, R1) |
| C2 | JWT auth | PASS | `tests/api/test_smoke.py::test_owner_jwt_passes_through_auth`, `test_missing_jwt_returns_401` (R1) |
| C32 | RBAC matrix | PASS | `tests/api/test_rbac_matrix.py` (8 tests covering viewer/manager/admin/owner, R1) |
| #92 | FK tenant validation (write path) | PASS | `tests/api/test_engagements_crud.py::test_create_engagement_with_cross_tenant_client_id_blocked`, `tests/api/test_invoices.py::test_create_invoice_with_cross_tenant_engagement_blocked` (both formerly xfail, now active, R1) |
| C4 | Stripe webhook signature verification | PASS | `tests/api/test_stripe_webhook_signature.py` (3 tests: missing/invalid/empty sig all rejected, R1) |

## 2. Engagement-to-Cash core

| ID | Capability | Status | Evidence |
|---|---|---|---|
| C5 | Engagements CRUD — all 6 billing arrangements | PASS | `tests/api/test_engagements_crud.py::test_create_engagement_for_each_billing_arrangement` (6/6 parametrize: T&M, fixed_fee, milestone, retainer, retainer_draw, capped_tm) (R1) |
| C5 | Engagement money serialisation | PASS | `tests/api/test_engagements_crud.py::test_create_engagement_money_serialises_as_string`, `test_create_engagement_money_quantized_to_two_decimals` (R1) |
| C5 | Soft-delete excluded from list | PASS | `tests/api/test_engagements_crud.py::test_list_engagements_excludes_soft_deleted` (R1) |
| C15 | Invoice CRUD + line math | PASS | `tests/api/test_invoices.py::test_create_invoice_with_lines_sums_correctly` (3500.00 subtotal arithmetic, R1) |
| C15 | Invoice number monotonicity | PASS | `tests/api/test_invoices.py::test_invoice_number_monotonic_within_tenant` (R1) |
| C15 | Invoice approve role gate | PASS | `tests/api/test_invoices.py::test_manager_cannot_approve_invoice_admin_can` (R1) |
| C17 | Public invoice token endpoint | PASS | `tests/api/test_invoices.py::test_public_invoice_bad_token_returns_404`, `test_public_invoice_endpoint_does_not_require_auth` (R1) |

## 3. Accounting backbone

| ID | Capability | Status | Evidence |
|---|---|---|---|
| C27 | Period lock — happy path | PASS | `tests/api/test_period_lock.py::test_period_lock_happy_path` (R1) |
| C27 | Period lock — double lock 409 | PASS | `tests/api/test_period_lock.py::test_period_lock_double_returns_409` (R1) |
| C27 | Period lock — bad format 422 | PASS | `tests/api/test_period_lock.py::test_period_lock_invalid_format_returns_422` (R1) |
| C27 | Period lock — cross-tenant 404 | PASS | `tests/api/test_period_lock.py::test_period_lock_cross_tenant_isolation` (R1) |
| C27 / F8 | Sub-ledger reconciliation before lock | **XFAIL** (real bug) | `tests/api/test_period_lock.py::test_period_lock_rejects_when_subledger_unbalanced` — accounting.py:155-158 TODO |
| Money | 2-decimal quantization across USD/GBP/SGD/INR/AUD | PASS | `tests/unit/test_engagement_models.py::test_engagement_response_total_value_quantises_short_decimal[*]` (5 parametrize, R1) |
| Money | Decimal arithmetic property | PASS | `tests/property/test_money_precision.py::test_addition_preserves_two_decimal_places` + 6 more (R1) |
| C26 | accounting_guardian L3 | **XFAIL** | `tests/property/test_journal_balance.py::test_accounting_guardian_accepts_balanced` — implementation present but not in test path yet |

## 4. AI surface

| ID | Capability | Status | Evidence |
|---|---|---|---|
| C12 / C37 | expense_extractor_agent live OpenRouter | PASS | `tests/api/test_llm_fallback_chain.py::test_expense_extractor_runs_against_real_openrouter_chain` (R1) |
| C12 | Prompt injection guard | PASS | `tests/api/test_llm_fallback_chain.py::test_expense_extractor_flags_prompt_injection` (R1) |
| C11 | engagement_letter_agent | UNTESTED | Pending — Phase 3b |
| C13 | vendor_invoice_agent | UNTESTED | Pending — Phase 3b |
| C28 | Copilot SSE chat | UNTESTED | Pending — Phase 3b |

## 5. Stripe

| ID | Capability | Status | Evidence |
|---|---|---|---|
| C1 | Signup happy path | **XFAIL** | Blocked by bug #97 (uncaught AuthApiError → 500) + Supabase email-allowlist config |
| C1 | Signup validation 422s | PASS | `tests/api/test_signup_and_billing.py` (short password, invalid country, invalid plan tier — 3 tests, R1) |
| C1 | Billing prices endpoint | PASS | `tests/api/test_signup_and_billing.py::test_billing_prices_returns_currency_for_country` (US→USD, R1) |
| C1 | Real Stripe Price IDs (not placeholders) | **XFAIL** | Blocked by bug #94 — `price_REPLACE_ME` in `.env` |
| C3 | Stripe Connect onboarding | UNTESTED — blocked | Blocked by bug #95 — `ca_REPLACE_ME` client_id |
| C4 | Stripe webhook signature | PASS | See §1 |

## 6. Untested capabilities (Phase 3b backlog)

These rows in the §2 matrix are not yet exercised by an API test:

- C7 Projects + phases (create/CRUD beyond list)
- C8 Rate cards
- C9 Time entries
- C10 Documents (upload + extraction pipeline)
- C11 engagement_letter_agent
- C13 vendor_invoice_agent
- C14 invoice_drafter_agent (the headline AI capability — 5 billing models)
- C15 Invoice send + Stripe Payment Link
- C16 Inbox / HITL
- C18 Payment webhook → journal
- C19 Bills CRUD
- C20 Bill payments + NACHA
- C21 bill_pay_agent
- C22 Billing runs
- C23 collections_agent
- C24 Reports (6 endpoints)
- C25 reporting_agent
- C28 Copilot chat (SSE)
- C29 Multi-currency FX
- C30 Tax rates
- C33 Autonomy promoter
- C34 Settings
- C35 Landing page (UI only)
- C36 Brand assets — VERIFIED present in `frontend/src/assets/brand/themes/` (3 directions)
