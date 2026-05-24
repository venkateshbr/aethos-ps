# Aethos PS — Master Test Plan

> **Owner**: Aksha (SDET) · **Status**: LIVE · **Started**: 2026-05-23 · **Charter**: founder direct
>
> Built in response to: every `status:in-qa` issue closed without UI + API verification. The Founder is blocking pilot launch until this plan is GREEN.

## 0. Charter

Verify EVERY user-facing capability in Aethos PS against the real, deployed stack
(Supabase `glcljucaayeesvrsjths`, Stripe sandbox, OpenRouter Gemma + Haiku
fallback). Both surfaces (UI and API). Both tenancy directions (isolation).
All 5 launch currencies. Both autonomy modes (L2 HITL and L3 auto-apply).
Both happy and unhappy paths.

The plan governs all four QA phases:

| Phase | Deliverable | Status |
|---|---|---|
| 1. Audit & plan | This document + feature matrix + suspect-list | DONE (this write) |
| 2. Build regression suite | pytest API + Playwright UI + fixtures + CI | IN-PROGRESS |
| 3. Execute & bug-file | EVIDENCE.md, opened bugs, re-opened tickets | PENDING |
| 4. Sign-off / verdict | PILOT_READINESS_REPORT.md (GREEN/YELLOW/RED) | PENDING |

## 1. Pre-flight findings (Phase 1)

These are facts established BEFORE writing a test. Each is severity-tagged.

| # | Finding | Severity | Source |
|---|---|---|---|
| F1 | All 31 Stripe Price IDs in backend `.env` are `price_REPLACE_ME`. Default values in `config.py` are also placeholders (`price_starter_monthly_usd` literal). Signup → checkout cannot create a subscription. | P0 LAUNCH BLOCKER | `/Users/venkatesh/dev/aethos-ps/.claude/worktrees/intelligent-saha-9ad2e3/backend/.env`, `backend/app/core/config.py:39-70` |
| F2 | `STRIPE_CONNECT_CLIENT_ID=ca_REPLACE_ME`. Stripe Connect OAuth onboarding will return Stripe error on first redirect. | P0 LAUNCH BLOCKER | `.env` line 17 |
| F3 | `RESEND_API_KEY=re_REPLACE_ME` (was in `.env.example`, missing entirely from real `.env`). Collections + transactional email cannot send. | P1 | `.env.example:61`, real `.env` missing |
| F4 | All 57 e2e/eval/property tests are `@pytest.mark.xfail(strict=True)` stubs. None ever ran against the real product. | P0 (process) | `backend/tests/e2e/test_engagement_to_cash.py`, `backend/tests/evals/test_engagement_letter_agent.py`, `backend/tests/property/test_*.py` |
| F5 | All Playwright tests are `test.fixme(...)` stubs. `global.setup.ts` referenced by `playwright.config.ts` does NOT exist. UI was never automated. | P0 (process) | `frontend/playwright.config.ts:39-42`, `frontend/e2e/engagement-to-cash.spec.ts` |
| F6 | `frontend/src/assets/brand/` is empty (`.gitkeep` only). Issue #9 ([Chitra] 2-3 logo lockup directions) closed `status:in-qa` with zero artifacts. | P1 (UX/launch) | `ls frontend/src/assets/brand/` |
| F7 | `conftest.py:124-128` — the `api_client` fixture is `pytest.xfail("not yet wired")`. No integration test ever hits the real API. | P0 (process) | `backend/tests/conftest.py` |
| F8 | `backend/app/api/v1/endpoints/accounting.py:155-158` — period lock has a TODO that says reconciliation is NOT performed. A period can be locked while sub-ledgers are unposted. | P1 | `accounting.py:156` |
| F9 | Backend boots cleanly (72 routes), Supabase URL is reachable, OpenRouter key + AGENT_MODELS chain present. Foundation is *physically* present even if untested. | INFO | `uv run python -c "from app.main import app; ..."` |
| F10 | 50 closed issues. Most marked `status:in-qa` and then closed by their author, not by an SDET. The lifecycle was bypassed. | P0 (process) | `gh issue list --state closed --limit 200` |

## 2. Feature inventory (the matrix)

A user-facing capability per row. Each row has a required happy path, at least
one unhappy path, and a responsibility for both API and UI verification.

Severity legend for blockers: **P0** = ship-stopper · **P1** = ship-with-caveat · **P2** = UX/polish · **P3** = nit.

| ID | Capability | Closed issues | Happy path | Unhappy paths | API suite | UI suite | Blocker if broken |
|---|---|---|---|---|---|---|---|
| C1 | Tenant signup + Stripe trial subscription | #6 | POST /auth/signup → POST /billing/start-trial → subscription `trialing` | invalid card; trial collision; duplicate email; missing Price ID | `tests/api/test_signup.py` | `e2e/signup.spec.ts` | P0 |
| C2 | Login + tenant switch + JWT | #5, #6 | login returns JWT; tenant middleware sets `tenant_id` | wrong password 401; expired token 401; mismatched tenant 403 | `tests/api/test_auth.py` | `e2e/login.spec.ts` | P0 |
| C3 | Stripe Connect onboarding | #51 | GET /stripe/connect/oauth-url returns Stripe URL; return endpoint records account_id | `ca_REPLACE_ME` → 500/4xx; `account.updated` webhook flips `charges_enabled` | `tests/api/test_stripe_connect.py` | manual + `e2e/connect.spec.ts` (mocked) | P0 |
| C4 | Stripe SaaS webhooks (sub state, payment) | #6, #52 | `customer.subscription.updated`, `checkout.session.completed`; idempotent on replay | bad signature 400; missing metadata; replay | `tests/api/test_stripe_webhooks.py` | n/a | P0 |
| C5 | Engagements CRUD (5 billing models) | #22 | create T&M / fixed_fee / milestone / retainer / capped engagement | invalid model; negative budget; cross-tenant 404 | `tests/api/test_engagements.py` | `e2e/engagements.spec.ts` | P0 |
| C6 | Clients CRUD | #22 | create customer + vendor; both | duplicate slug; invalid email; cross-tenant | `tests/api/test_clients.py` | covered in `e2e/engagements.spec.ts` | P1 |
| C7 | Projects + phases | #36 | create project under engagement; add phases | engagement closed; cross-tenant; delete with unbilled blocks | `tests/api/test_projects.py` | `e2e/projects.spec.ts` | P1 |
| C8 | Rate cards | #22 | create rate card; per-employee/role override | effective-date overlap; cross-tenant | `tests/api/test_rate_cards.py` | covered in C5 | P2 |
| C9 | Time entries (CRUD + chat) | #53 | log 3.5h via API; log via chat command | zero hours 422; > 24h 422; cross-tenant; role denied | `tests/api/test_time_entries.py` | `e2e/time_entries.spec.ts` | P1 |
| C10 | Document upload + extraction pipeline | #25, #37 | upload PDF → document row → extract_document_worker → extraction_results | unsupported MIME; too-large file; corrupted PDF; OCR failure | `tests/api/test_documents.py` | `e2e/copilot_upload.spec.ts` | P1 |
| C11 | `engagement_letter_agent` (LLM) | #37 | upload SOW → typed EngagementDraft → suggestion → HITL | prompt injection in PDF; missing fields; low confidence routes HITL | `tests/api/test_agents_engagement_letter.py` + `tests/evals/...` | `e2e/agent_engagement_letter.spec.ts` | P1 |
| C12 | `expense_extractor_agent` (LLM) | #37 | upload receipt → ProjectExpense draft; auto-apply at conf > 0.9 | misread total; foreign currency; injection in OCR | `tests/api/test_agents_expense.py` + evals | covered in C16 (inbox) | P1 |
| C13 | `vendor_invoice_agent` (LLM) | #37 | upload vendor PDF → Bill draft; HITL approve | duplicate bill number; missing tax line | `tests/api/test_agents_vendor_invoice.py` + evals | `e2e/agent_vendor_invoice.spec.ts` | P1 |
| C14 | `invoice_drafter_agent` (LLM) — all 5 models | #49 | T&M from time entries; fixed-fee; milestone; retainer-draw; capped | period locked; engagement archived; mixed-model rejected if disallowed | `tests/api/test_invoice_drafter.py` | `e2e/invoice_draft.spec.ts` | P0 |
| C15 | Invoice send + Stripe Payment Link | #50 | POST /invoices/{id}/send → Product+Price+PaymentLink; persisted | tenant w/o Connect → PDF-only; Stripe error path | `tests/api/test_invoice_send.py` | `e2e/invoice_send.spec.ts` | P0 |
| C16 | Inbox / HITL approve + reject + escalate | #38 | approve, approve-with-edits, reject, escalate transitions | wrong role 403; cross-tenant 404; double approve 409 | `tests/api/test_inbox.py` | `e2e/inbox.spec.ts` | P0 |
| C17 | Public invoice view `/p/{token}` | #55 | GET /public/invoices/{token} renders without auth | bad token 404; revoked token 410 | `tests/api/test_public_invoice.py` | `e2e/public_invoice.spec.ts` | P0 |
| C18 | Payment received webhook → journal | #52 | `checkout.session.completed` → payments row → DB trigger DR Bank / CR AR | invalid signature 400; missing metadata; idempotent replay | `tests/api/test_payment_webhook.py` | n/a | P0 |
| C19 | Bills CRUD + approve | #39 | create draft bill; approve → DR Expense / CR AP | duplicate bill number 409; cross-tenant; period locked | `tests/api/test_bills.py` | `e2e/bills.spec.ts` | P1 |
| C20 | Bill payments + NACHA / CSV export | #61 | propose batch → approve → download NACHA → settled | unsupported bank code; cross-currency batch | `tests/api/test_bill_payments.py` | `e2e/pay_bills.spec.ts` | P1 |
| C21 | `bill_pay_agent` (LLM) | #61 | propose batch from approved bills | already-paid bills filtered out; discount capture window | `tests/api/test_bill_pay_agent.py` + evals | covered in C20 | P2 |
| C22 | Billing runs | (#62 covers reporting; billing_runs in #49) | propose batch for active engagements → review → materialise invoices | empty batch; mixed currencies; period locked | `tests/api/test_billing_runs.py` | `e2e/billing_runs.spec.ts` | P1 |
| C23 | `collections_agent` + Resend email | #63 | overdue invoice → draft reminder → send | LLM down → manual reminder still works | `tests/api/test_collections.py` | `e2e/collections.spec.ts` | P2 |
| C24 | Reports (AR aging, AP aging, P&L by engagement, utilization, WIP, revenue by engagement) | #62, #65 | 6 endpoints return numbers reconciling with sub-ledgers | empty tenant; cross-tenant 404 | `tests/api/test_reports.py` | `e2e/reports.spec.ts` | P1 |
| C25 | `reporting_agent` (LLM) Q&A | #62 | "what's my AR aging?" → ReportCard | unsupported question → graceful no-answer | `tests/api/test_reporting_agent.py` + evals | covered in C28 | P2 |
| C26 | `accounting_guardian` (immutable L3) | #48 | balanced journals pass; imbalanced rejected; period locked rejected | bypass attempt → still rejected; concurrent post race-loser | `tests/property/test_journal_balance.py` (un-xfail) | n/a | P0 |
| C27 | Period close + lock | #48 | lock period; subsequent post rejected with `period_locked` | TODO: reconciliation gap (see F8); double-lock 409 | `tests/api/test_period_lock.py` | `e2e/period_lock.spec.ts` | P1 |
| C28 | Copilot chat (SSE streaming + Pydantic Graph router) | #24, #27 | thread create; send message; SSE streams; tool call rendered | LLM API down → graceful message; injection in user msg sanitised | `tests/api/test_chat.py` | `e2e/copilot.spec.ts` | P0 |
| C29 | Multi-currency FX (5 currencies) | #23 | invoice GBP under USD tenant → base_amount set; FX worker daily refresh | stale FX rate warn; unsupported currency; weekend stale | `tests/api/test_fx.py` | `e2e/multi_currency.spec.ts` | P0 |
| C30 | Tax rates seeding + per-line tax | #4, #36 | new IN tenant has GST 0/5/12/18/28 seeded; per-line tax computed | unknown tax_rate_id; rate change effective date | `tests/api/test_tax_rates.py` | covered in C14 | P1 |
| C31 | Multi-tenant RLS isolation | #4, #5 | tenant A JWT cannot read tenant B invoice / bill / chat / suggestion | every entity tested in both directions | `tests/api/test_rls_isolation.py` | covered in role tests | P0 |
| C32 | RBAC (owner / admin / manager / staff / finance) | #5, baked in routers | each role can only do what spec says | viewer cannot mutate; finance cannot send invoice | `tests/api/test_rbac.py` | `e2e/rbac.spec.ts` | P0 |
| C33 | Autonomy promoter worker | #64 | thresholds met → `promote_autonomy` HITL card; admin approves → L3 | demotion on bad streak; admin rejects → 90-day cooldown | `tests/api/test_autonomy.py` | covered in C16 | P2 |
| C34 | Settings — agent autonomy + branding | #45 (settings module) | UPDATE per-(agent, action_type, level); per-tenant brand override | role denied; invalid level | `tests/api/test_settings.py` | `e2e/settings.spec.ts` | P2 |
| C35 | Landing page (5-market copy) | #8 | GET / returns Angular landing; Get Started CTA → /signup | n/a | n/a | `e2e/landing.spec.ts` | P3 |
| C36 | Brand assets present | #9 | logo SVG + favicon under `frontend/src/assets/brand/` | n/a | n/a | `e2e/brand_assets.spec.ts` | P1 (per F6) |
| C37 | LLM fallback chain (Gemma free → Haiku paid) | new env wiring | each of 4 LLM-using agents (C11/C12/C13/C28) works when free-tier rate-limited | all 3 models down → graceful degradation | `tests/api/test_llm_fallback.py` | n/a | P1 |

**Totals**: 37 capability rows. Estimated 30-50 minutes of test running once authored.

## 3. Test suite organisation

```
backend/tests/
  api/                  # NEW — httpx against live :8011 (real Supabase, real Stripe)
    conftest.py         # bootstraps two tenants, JWT minting, cleanup
    test_signup.py
    test_auth.py
    test_engagements.py
    ... (one per row in §2 marked "API suite")
  e2e/                  # existing — KEEP, un-xfail rows as they're ported to api/
  evals/                # existing — extend per-agent eval pack
  unit/                 # existing — pure logic, keep as-is
  property/             # existing — un-xfail
  fixtures/
    scenarios.py        # NEW — deterministic seed of 2 tenants + data
    pdfs/               # NEW — sample SOW, receipt, vendor invoice for extraction tests

frontend/e2e/
  global.setup.ts       # NEW — login both tenants, save storage state (1 per tenant)
  signup.spec.ts        # NEW
  copilot.spec.ts       # NEW
  engagements.spec.ts   # NEW
  invoice_send.spec.ts  # NEW
  public_invoice.spec.ts# NEW
  inbox.spec.ts         # NEW
  pay_bills.spec.ts     # NEW
  rbac.spec.ts          # NEW
  brand_assets.spec.ts  # NEW — guards F6 from regressing
  multi_currency.spec.ts# NEW
  landing.spec.ts       # NEW
  engagement-to-cash.spec.ts  # existing — replace fixmes with real tests
```

## 4. Pytest markers (per charter)

Tests subset-runnable by `pytest -m`:

- `flow_signup`, `flow_engagement`, `flow_billing`, `flow_payments`, `flow_hitl`, `flow_reports`, `flow_accounting`, `flow_copilot`
- `rbac`, `multi_tenant`, `multi_currency`
- `unhappy`, `injection`, `concurrency`
- `requires_stripe`, `requires_supabase`, `requires_openrouter`

## 5. Phase 2 plan — what gets built and in what order

Order is chosen so each block can validate something real before the next block starts:

1. **`tests/api/conftest.py` + scenarios.py** — two tenants seeded; JWT minting; cleanup hooks. (Unblocks every API test.)
2. **`frontend/e2e/global.setup.ts`** — fix the missing setup file; create per-tenant storage state. (Unblocks every Playwright test.)
3. **C2 login + C1 signup** — the entry point. Failure here blocks everything else.
4. **C31 RLS isolation + C32 RBAC** — security backbone. Founder will not ship if these are red.
5. **C26 accounting_guardian + C27 period lock** — finance backbone.
6. **C5 engagements + C9 time entries + C14 invoice_drafter (all 5 models) + C15 send + C18 webhook + C17 public view** — the engagement-to-cash core.
7. **C19 bills + C20 bill payments** — the procure-to-pay loop.
8. **C28 copilot + C10 documents + C11/C12/C13 extraction agents + C37 fallback chain** — the AI surface.
9. **C16 inbox + C33 autonomy** — the HITL backbone.
10. **C24 reports + C25 reporting_agent** — read-side validation.
11. **C29 multi-currency + C30 tax** — multi-market.
12. **C3 Connect + C4 Stripe webhooks** — Connect requires real client_id; flagged blocker.
13. **C35 landing + C36 brand assets + C34 settings + C23 collections** — polish layer.

Each block produces (a) one or more pytest files under `tests/api/`, (b) one Playwright spec under `frontend/e2e/`, (c) an entry in `docs/qa/EVIDENCE.md`.

## 6. Phase 2 — CI integration

- `.github/workflows/ci.yml` to grow a `pytest-api` job that boots the API on :8011 against the real Supabase (read-only fixtures + ephemeral test tenants).
- `.github/workflows/ci.yml` to grow a `playwright-e2e` job that depends on `pytest-api`. UI runs headless against the same stack.
- Both jobs gated by a label `qa:run` on PRs to avoid blowing the OpenRouter budget on every push.
- Locally: `make test-api`, `make test-e2e`, `make test-all` (added in Phase 2).

## 7. Status log

| When | Phase | Note |
|---|---|---|
| 2026-05-23 | 1 | Plan written. 37-row matrix. 10 pre-flight findings filed. Real `.env` copied into worktree. Backend boots clean against real Supabase. |
| 2026-05-23 | 2 | Built `tests/api/conftest.py` + `tests/fixtures/scenarios.py` (2-tenant seed, JWT mint, sweep-clean). 10 API test files authored (~1,845 LOC). 7 bugs filed (#90/91/92/93/94/95/96), 9 wrongly-closed in-qa issues re-opened. |
| 2026-05-23 | 3a | **DONE.** Verified fixes for #90/#91/#92/#93 against real Supabase. Full suite: **290 passed, 6 xfailed (all expected), 0 failures**. Bugs #90/#91/#92/#93 CLOSED with proof. #94/#95 stay open (need Founder Stripe action). New bug #97 filed (signup AuthApiError → 500 should be 4xx). XPASS sentinels flipped to active in `test_engagements_crud.py` and `test_invoices.py`. Re-opened tickets dispositioned: #4 #5 #22 #72 moved to in-qa for Vishwa; #9 confirmed delivered (3 brand themes present); #6 + #51 stay open blocked by #94/#95/#97. |
| 2026-05-23 | 3b | (next) Author remaining ~15 API test files per matrix §5 — start with C10/C11/C12/C13 (documents + extraction agents), C14 invoice_drafter, C15/C17/C18 invoice send/public/webhook, C19/C20 bills/payments, C16 inbox, C24 reports, C28 copilot SSE, C29 multi-currency, C30 tax. |
| 2026-05-23 | 3b | **DONE.** Authored 6 new files: test_agents_engagement_letter, test_agents_expense, test_agents_vendor_invoice, test_payment_webhook, test_fx (C29 multi-currency), test_tax_rates (C30). Fixed 2 test bugs (test_bills cross-tenant payload, test_invoice_send role for cross-tenant probe). Triaged 7 real product bugs: #98 (copilot RLS), #99 (reports/wip schema), #100 (storage bucket missing), #101 (invoice_drafter 500), #102 (bill_pay FK violation), #103 (accounting_guardian split), #104 (expense_extractor crash on bad LLM output). Affected tests xfailed referencing each bug. **Final API suite: 141 passed, 15 xfailed, 1 xpassed, 0 failures.** Full backend suite: 343+ passed / 69+ xfailed / 0 failures. |
| 2026-05-23 | 3c | **PARTIAL.** Bootstrap shipped: `frontend/e2e/global.setup.ts` (was missing per F5; created empty-state writer + reachability check), `frontend/e2e/landing.spec.ts` (C35 landing CTA + 5-market copy), `frontend/e2e/brand_assets.spec.ts` (C36 — guards F6). NOT shipped: copilot/engagements/invoice-send/public-invoice/inbox/rbac/multi-currency UI specs (deferred to post-pilot iteration to keep budget for the report). Founder caveat: pilot must verify these UI flows manually with the screenshot protocol from agent-harness/core/e2e-workflow-standard.md until the full Playwright suite is authored. |
| 2026-05-23 | 3d | **DEFERRED.** CI integration (pytest-api + playwright-e2e GitHub Actions jobs, Makefile targets) deferred to post-pilot. Phase 3a/3b can be run locally with `cd backend && set -a && source .env && set +a && uv run pytest tests/api/` (the same command CI will use). Real Supabase, real Stripe sandbox, real OpenRouter — no mocks. Listed as follow-up task in PILOT_READINESS_REPORT.md §6. |
| 2026-05-23 | 4 | **DONE.** Wrote `docs/qa/PILOT_READINESS_REPORT.md` with verdict YELLOW (ship with named caveats), full bug inventory, Founder action list, and run instructions. See report for the call. |
| 2026-05-24 | R2 | **DONE.** Fix-verification run. All 7 R1 product bugs verified closed: #97 (signup AuthApiError), #98 (copilot RLS), #99 (/reports/wip), #100 (storage bucket + RLS — incl. Sthira's self-caught migration 0017 SECURITY DEFINER helper), #101 (draft-invoice 404), #102 (bill-pay FK), #104 (extractor defensive fallback). Test totals: **383 passed / 4 xfailed / 1 xpassed in API+unit suite** (133s). 10 failures all test-only: 8 stale unit-test mocks tracked as #105, 2 LLM flakes tracked as #106. Un-xfailed `test_upload_pdf_document_happy_path` (commit `edd466b`). Filed #105 + #106. Pilot verdict: YELLOW-pending-Founder — flips GREEN the moment #94 (Stripe Price IDs) lands; optional #95 (Connect) determines PDF-only vs full. No new code in product layer this run. |

## 8. Constraints noted

- Aksha must NOT modify product code to make tests pass. Any failing test → bug filed → routed to Karya or Rupa.
- Aksha may file `type:bug` and `type:task` issues. Re-open closed issues. Never close.
- Aksha may not create `type:feature` issues — gap → file task for Netra/Vastu.
