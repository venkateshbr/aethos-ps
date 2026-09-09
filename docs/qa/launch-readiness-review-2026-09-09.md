# Launch Readiness Review — 2026-09-09

Status: **NOT READY for paid public launch · READY for controlled, founder-led pilot demos** (disposable demo tenant, caveats in §1.3).

> Supersedes the verdict language of
> [`prelaunch-platform-validation-runbook-2026-08-05.md`](prelaunch-platform-validation-runbook-2026-08-05.md)
> (which remains the record of the last passed Demo Guide v2 gate) and extends
> [`launch-readiness-audit-2026-07-11.md`](launch-readiness-audit-2026-07-11.md).
> Tracking: #368 (launch readiness epic). Companion documents produced with this
> review: [`../DEMO_GUIDE_v3_END_TO_END.md`](../DEMO_GUIDE_v3_END_TO_END.md) and
> [`../team/LAUNCH_GAP_IMPLEMENTATION_PLAN.md`](../team/LAUNCH_GAP_IMPLEMENTATION_PLAN.md).

## 0. Scope, method, and evidence standard

| Item | Value |
| --- | --- |
| Repository state reviewed | `main` @ `481013b` |
| Production build | `f170119` — Deploy Hostinger Production run #35 ([33732519598](https://github.com/venkateshbr/aethos-ps/actions/runs/33732519598)), 2026-09-03; `/health/ready` reported `status=ready`, `build_sha` matched; migrations `0121_webhook_event_processing_status.sql` and `0122_billing_runs_table.sql` applied (migrate service log: `apply_migrations: done`) |
| Commits on `main` after the deployed SHA | `ade9472`, `e57f33c`, `ab12537`, `481013b` — CI templates, quality-gate workflow, release workflow, docs. No application code, so production is functionally current with `main`. |
| Live-site browser check | **Not performed from the review environment** — outbound access to `aethos.ishirock.tech` was blocked by the sandbox egress policy. Production state is established from the deploy log and the 2026-08-05 production validation reports. A founder browser pass per the SDLC closure-evidence rule is still required for anything below marked "not browser-verified". |
| Sources | `CLAUDE.md`, harness adapter, `docs/PLAN.md` (v4 + §0.2 drift), `PROJECT_CONTEXT.md`, `SDLC_PROTOCOL.md`, all five published guides, `docs/qa/*`, `docs/test/e2e_*`, all 82 open issues, 16 open PRs, CI / deploy / release workflows, both compose files, `backend/.env.example`, frontend routes / settings / signup / login / people / inbox / copilot, backend routers / services / agents / workers / migrations. |

Evidence standard follows `docs/team/SDLC_PROTOCOL.md`: a claim is "implemented" only when the code path exists and is reachable from the UI; "verified" only when a Playwright spec or a recorded browser walkthrough exists.

## 1. Verdict

### 1.1 Summary

The platform is functionally deep: order-to-cash, procure-to-pay, record-to-report with a close package, a 22-role security catalogue, a human-in-the-loop Inbox that gates every agent write, 19 report tabs, FX provenance, and a Hermes runtime with automatic fallback. The deployed build is current with `main`.

It is not ready to take a paying customer's money. Production runs on Stripe **test mode** against the **same Supabase project as development**. Invoices cannot be emailed. There is no password recovery, and invite credentials are handed to admins as plaintext in the UI. Fifteen P0/P1 security and accounting issues remain open. CI discovers Playwright specs but never executes one. Two-thirds of the Nous semantic-router intents return canned prose rather than tenant data, and the in-app guide library — including the Hermes operations manual with secret-rotation procedures — is readable without authentication.

None of this blocks a scripted demo on a disposable tenant. All of it blocks paid launch.

### 1.2 Scorecard

| Area | State | Evidence |
| --- | --- | --- |
| Deployed build = `main` | ✅ | Deploy run #35 → `f170119`; later commits are CI/docs only |
| Availability / TLS / readiness | ✅ (as of 2026-09-03) | Deploy log: `status=ready`, `build_sha` match |
| Migrations current | ✅ | 0121, 0122 applied; `tests/unit/test_migration_chain_contract.py` guards the chain |
| Signup → trial → app | ✅ (test mode) | `backend/app/api/v1/endpoints/auth.py:284`, `billing.py:39`; `frontend/e2e/00-signup.spec.ts` |
| Stripe live mode | ❌ | `frontend/src/environments/environment.prod.ts` ships `pk_test_…` (#514) |
| Environment separation | ❌ | Same Supabase project ref and anon key in `environment.ts` and `environment.prod.ts` (#514) |
| Stripe Connect | ❌ | `STRIPE_CONNECT_CLIENT_ID=ca_REPLACE_ME` (#95, open since 2026-05-23) |
| Invoice delivery (email / PDF) | ❌ | `invoices_service.send_invoice` only creates a Payment Link (#516) |
| Password recovery / invite email | ❌ | `auth.py` exposes two routes; invites return `temp_password` + `set_password_url` in the API response, no email |
| Post-signup onboarding / T&C | ❌ | `frontend/src/app/features/onboarding/` is a `.gitkeep` (#519) |
| Guide library access control | ❌ | `frontend/public/guide-content/*.html` served anonymously; `core/guards/admin.guard.ts:31-34` documents itself as "UI affordance only" |
| Period lock at API for invoices / payments / bills / batches / expenses | ❌ | `assert_period_open` called only from time entries and manual journals (#500) |
| Stripe idempotency keys | ❌ | No `idempotency_key` on any Stripe write; blocking SDK calls in async `send_invoice` (#502) |
| Tool-broker policy bypass | ❌ | `atlas_tools.py:439-521` and `:689-874` write suggestions without `AgentToolPolicy` (#529) |
| Hermes memory tenant isolation | ❌ unproven | Single `hermes-data` volume, no retention or clearing (#531) |
| Rate limit on LLM-spend endpoints | ❌ | Only signup and public invoice are limited; `RATE_LIMIT_BACKEND=memory` in production compose (#503) |
| Scanned documents sent raw to model | ❌ | `agents/base.py:339-414` withholds binary only when extractable text contains PII (#498) |
| Nous card "Edit" silently approves | ❌ | `copilot.component.ts:1098-1102` (#507) |
| Inbox keyboard-approve bug | ✅ fixed and deployed | #494 fixed in `f170119` (issue still open — close it) |
| Webhook swallowed exception → 200 | ✅ fixed and deployed | #493 fixed in `f170119` (issue still open — close it) |
| `billing_runs` CREATE TABLE | ✅ fixed and deployed | #492 migration 0122 (issue still open — close it) |
| Autonomy demotion filter | ✅ fixed | #496 demotion PGRST100 fixed; promotion path still inert |
| Hermes default runtime | 🟡 | `config.py:119` defaults to `hermes_agent`; no Hermes check in `/health/ready`, no runtime badge (#530 residual) |
| Release workflow | 🟡 | #550 fix in PR #551, `mergeable_state: clean`, unmerged |
| CI gates | 🟡 | ruff, pytest (79 % coverage), agent-eval gate, frontend typecheck/unit/build, gitleaks block; **mypy and pip-audit are warning-only; Playwright runs `--list` only; no frontend lint target (#495)** |
| Angular advisories | 🟡 | #477 open; eight Dependabot PRs to Angular 22 unmerged, dev-deps bump CI red |
| Documentation | 🟡 | Reconciled 2026-09-03; 14 material mismatches remain (§2) |

### 1.3 Demo-safety caveats (apply even to pilot demos)

1. Use a **disposable Meridian tenant**. Never mutate Sterling Bridge Advisory Group (retained tenant, expired trial, governed override per #481).
2. Do not demonstrate: invoice email, password reset, Stripe Connect payout routing, the Payment Link completion redirect (`/p/:token/thanks` is not a route), mobile layout (#510), autonomy L3 promotion (#496/#497), expense approval or GL posting (#518), invoice void or credit notes (#517).
3. Nous prompts should name one of the five router-known clients (Nexus, Brightwater, Forster, Alderton, Thornton); other names fall through to the model runtime and the answer is non-deterministic.
4. Keep Stripe in test mode and say so. The card step shows the `4242` helper text in production builds.

### 1.4 Open-issue triage (82 open on 2026-09-09)

| Bucket | Issues |
| --- | --- |
| P0 open, **fixed on `main` and deployed — close with evidence** | #492, #493, #494 (and the demotion half of #496) |
| P0 open, unfixed | #95 Connect placeholder · #371 AR payment lifecycle · #377 P2P double-settlement · #378 server-side role enforcement · #379 close controls · #477 Angular advisories · #495 lint gate · #529 broker bypass · #530 runtime verification (residual) · #531 Hermes memory · #550 release workflow (PR #551 ready) |
| P1 launch-blocking (money / security / data) | #373, #375, #498, #500, #501, #502, #503, #504, #505, #509, #511, #514 |
| P1 product completeness | #497 L3 auto-apply · #515 Billing Runs UI · #516 invoice delivery · #517 void / credit notes · #518 expense lifecycle · #519 onboarding · #536 Hermes hardening |
| P1 quality | #507, #508, #510, #532 |
| P2 / P3 roadmap | #520–#528, #404–#419, #353–#365 (Atlas read packs, in-qa), #533–#535 learning loop |

## 2. User-guide audit — claims versus implementation

Five guides are published in-app (`frontend/src/app/features/guides/guide-catalog.generated.ts`): the platform user guide, the Nous prompt library, Demo Guide v2, the Nous-on-Hermes operations manual, and the archived Demo Guide v1. The route table, the 19 Settings panels, roughly 190 API endpoints, and all 39 router intents were compared against the guides.

Overall: the route map, Settings inventory, O2C / P2P / R2R module claims, and the stated limitation lists are accurate. The mismatches below are what must be fixed in documentation or code.

### 2.1 Material mismatches

| # | Guide / section | Claim | Reality | Fix |
| --- | --- | --- | --- | --- |
| G1 | User guide §1 | Guide library requires a signed-in owner or admin | HTML under `frontend/public/guide-content/` is served anonymously; `admin.guard.ts:31-34` says "UI affordance only" | Code (serve through an authenticated endpoint) — plan item A1 |
| G2 | User guide §3.1 | Number-fidelity guard checks every stated figure | Guard runs only in the Basic tool loop (`agents/copilot/graph.py:754`); the semantic-router path streams template text unguarded; 26 of 39 intents are static, several with hardcoded figures | Code + doc — B1 |
| G3 | User guide §3 approval-boundary table | Draft invoice / bill-pay proposal / engagement-by-prompt route to Inbox | On the router path only `manual_journal`, `finance_ops_action_plan`, `time_log` materialise; `billing_run`, `bill_pay_run`, `capped_tax_engagement` fall through to the model runtime; there is no engagement-creation intent (#363) | Doc now (done in this change), code via B2 |
| G4 | User guide §4 Inbox | "Approve with edits" corrects the payload | True in the Inbox drawer; the Nous chat card `editCard()` calls `approveCard()` | Code — A9 (#507) |
| G5 | User guide §1 module map | Dashboard shows AR/AP, WIP, open Inbox work, trial state | Dashboard shows receivables, payables, net position and aging bars only | Doc (done) |
| G6 | User guide §5 | Viewer cannot "void" an invoice | No invoice void endpoint exists (#517) | Doc (done) |
| G7 | User guide §3 / §10 | Nous operational-health, control-room, configuration-telemetry and approval-controls read packs | HTTP read packs exist (`endpoints/agents.py:126-153`); the chat responders are static templates | Doc (done) + code — B1 |
| G8 | User guide §6 | Nous P2P payment-risk read is live | `atlas_deterministic_responses.py:224` dispatches the static variant; the live `_format_p2p_payment_risk` at `:1026` is unreachable | Code — B1 (one-line dispatch fix) |
| G9 | Hermes ops manual §1 | "38 static intents" | 39 (`atlas_semantic_intent_router.py:18-58`); prompt library already says 39 | Doc (done) |
| G10 | Demo v2 §5.2 | "Accounting → Period Locks" screen | Lock / unlock is embedded in the Journal Entries screen; no Period Locks route | Doc (done) |
| G11 | Demo v2 §3.2, §3.4, §4.2, §4.3, §5.1 | Nous cites comparable-matter pricing; retainer-floor alerts notify a user; Series A milestone updated and invoiced; COSEC per-event billing created; pre-close checklist with figures | Static narrative; nothing is computed or created | Superseded by Demo Guide v3, which marks these as talk-track only |
| G12 | Landing page | "No credit card required at signup" | Step 3 of the wizard requires a card | Code — A13 |
| G13 | Demo v2 §3.3 | SGD dividend journal from prompt | Works, but falls back to hardcoded "Alderton Trust / SGD / 18000 / 2026-06" when the prompt does not parse | Code — B1/B10 |
| G14 | `backend/CLAUDE.md` gotchas | "`billing_runs` has no CREATE TABLE migration" | Migration 0122 exists | Doc (done) |

### 2.2 Documented limitations confirmed accurate

No forgot-password; plan changes only via the Stripe Customer Portal; Connect needs a real client ID; `/p/:token` is the only customer-facing page; no platform-administrator role; invoice send does not email or render a PDF; expenses have no GL posting; Pay Bills has no partial payments, early-pay discounts, mixed-currency batches, bank-balance gate or vendor-bank validation; no report-currency toggle; WIP is a current-rate estimate; name and address masking only with the optional NER model; autonomy promotion disabled; no thumbs-up/down feedback; Hermes has no tool chips, number-fidelity guard or Langfuse trace.

### 2.3 Shipped but undocumented

Inbox **Escalate**, **Approve all**, **Dismiss (14d)**, **Approve L3**, **Investigate** actions; detail routes `/app/invoices/:id`, `/app/clients/:id`, `/app/bills/:id`; timesheet portal routes; Settings panels Change password, Security Roles and Integration Roadmap are missing from the §10 demo checklist; `/api/v1/billing-runs` pre-bill API (no UI); `DELETE /api/v1/tenants` (undocumented destructive endpoint); `POST /employees/{id}/invite`.

## 3. Agentic process inventory

All three agentic surfaces — Nous chat, document extraction, Procrastinate cron — converge on one write path: `agents/suggestion_writer.write_agent_suggestion()` → `agent_suggestions` + `hitl_tasks` → Inbox approve → `InboxService._materialise()` (`services/inbox_service.py:646`). `hitl_tasks.kind` is free text equal to the `action_type`, so agents can mint kinds that have no approve handler, and several do.

### 3.1 Process → agent → HITL kind → what Approve materialises

| Process | Trigger | Agent (LLM?) | HITL kind | Approve materialises | Demo status |
| --- | --- | --- | --- | --- | --- |
| Engagement letter / SOW intake | Upload, filename contains `engagement` / `letter` / `sow`; Hermes `aethos.engagements.create_review` | `engagement_letter_agent` (LLM) | `create_engagement_draft` | client + engagement + billing terms + rate card and lines + first project | ✅ Reliable end to end. Filename containing `nexus` and `engagement` returns a fixture at confidence 1.0 without calling the model |
| Vendor invoice intake | Upload (default classification) | `vendor_invoice_agent` (3 LLM calls: extract, vendor match, GL code) + duplicate guard | `create_bill_draft` | vendor client + bill + lines; journal posts on bill approve, not here | ✅ Reliable. `brightwater` + `subcontractor` filename returns a fixture |
| Expense receipt intake | Upload, filename `receipt` / `expense` | `expense_extractor_agent` (LLM) | `create_expense_draft` | `project_expenses` **only if `project_id` is present**; the extractor never sets it, so approve silently no-ops | ❌ Broken unless the reviewer edits in a project |
| COSEC instruction | Upload, filename `cosec` | inline hardcoded dict, no LLM, confidence 0.98 | `cosec_instruction_review` | nothing (catch-all warning) | ❌ Talk-track only |
| Time log by chat | `time_log` router intent → `log_time_entry` | copilot tool (`write_low_risk`) | `copilot_log_time_entry` | `time_entries` row | ✅ Reliable (user must be linked to an employee) |
| Draft invoice by chat | Model runtime → `draft_invoice` | `invoice_drafter_agent` (deterministic Decimal math, 7 billing models) | `copilot_draft_invoice` | invoice + lines | ✅ Via runtime, not router |
| Rate change by chat | Model runtime → `update_rate_card` | copilot tool (`write_money_in`) | `copilot_update_rate_card` | `rate_card_lines` | ✅ |
| Collections | Model runtime → `draft_collection_reminders`; cron 06:00 daily | `collections_agent` (LLM body) | `send_email` per invoice | sends via Resend | ✅ Needs `RESEND_API_KEY` |
| Bill-pay proposal | Model runtime → `propose_bill_payment_batch`; Hermes tool | `bill_pay_agent` (deterministic) | `create_bill_payment_batch` | `bill_payment_batches` + items → Pay Bills wizard: approve → export → mark sent → settle (DR AP / CR Bank) | ✅ |
| Finance Ops action plan | `finance_ops_action_plan` router intent; hourly scheduled worker | deterministic plan builder | `copilot_create_finance_ops_action_plan` → child `finance_ops_action_item` | plan approve fans out items; item approve dispatches a specialist tool through policy | ✅ Best "AI manager" showpiece |
| Finance Ops escalation | scheduled worker (stale > 24 h, high-risk > 4 h) | deterministic | `finance_ops_escalation` | nothing | 🟡 Informational card |
| Manual journal by prompt | `manual_journal` router intent → `_prepare_manual_journal_review` | deterministic (real FX lookup, account existence, period lock, segregation of duties) | `draft_journal` | posts journal via `ManualJournalService` → `post_journal()` → guardian → atomic RPC | ✅ Reliable; defaults to Alderton / SGD / 18000 if the prompt does not parse |
| Manual journal above threshold (UI) | `POST /accounting/journal-entries` above threshold | `manual_journal_service` | `draft_journal` | posts journal; same-user approval denied | ✅ |
| Month-end close proposals | cron 07:00 on the 1st (9 steps); 7 API endpoints `/accounting/periods/{p}/propose-*`; chat `prepare_month_end_close` | accrual, prepaid, recurring, revenue-recognition, FX-remeasurement agents (deterministic) | `draft_journal` × N + close tasks + close package + workflow run | each approve posts a journal | ✅ FX remeasurement and scheduled revenue release have no API endpoint (cron only) |
| Year-end close | chat / Hermes `prepare_year_end_close`; `POST /accounting/years/{y}/year-end-close` | deterministic | `copilot_prepare_year_end_close` | retained-earnings journal `YE-YYYY`; duplicate blocked | ✅ |
| Monthly billing run | cron 08:00 on the 1st | deterministic (retainer / retainer draw) | `approve_billing_run` | `billing_runs.status=approved` + drafted invoices | ✅ Backend only; no UI (#515) |
| Project health alerts | cron 07:00 daily | `project_health_agent` (4 checks) | `BUDGET_BURN_WARNING`, `CAPPED_TM_APPROACHING`, `RETAINER_FLOOR_WARNING`, `SCOPE_CREEP_RISK` | nothing | 🟡 Card only |
| Intelligence anomalies | cron Monday 06:00 | `intelligence_agent` (LLM narrative), 6 checks | `UNBILLED_ENGAGEMENT` etc. | nothing; 2 of 6 checks always error (tables `expenses`, `collection_activities` do not exist, #499); the frontend filters on kind `intelligence_alert`, which is never written | ❌ |
| Autonomy promotion | cron 02:00 | `autonomy_promoter` | `promote_autonomy` / `autonomy_demotion` | nothing; approve does not raise the level; `eval_passed_at` is never written so L3 is unreachable | ❌ (#496 / #497) |
| Accounting guardian | every `post_journal()` | deterministic validator, L3 locked | n/a | balance ± 0.01, period lock, account validity, FX residual → 7900 | ✅ |
| Stripe payment → paid → journal | webhook `checkout.session.completed`; hourly `reconcile_sent_invoices_all_tenants` | deterministic | n/a | payment row + DR Bank / CR AR (+ realised FX 7900) | ✅ Webhook now returns 500 on handler failure so Stripe retries |
| Timesheet submit → approve | portal `/timesheet` → `/app/approvals` | none | n/a | time entries `submitted` → `approved` | ✅ |
| Reporting Q&A (`reporting_agent`) | no caller — dead code | LLM | n/a | n/a | ❌ |

### 3.2 Nous routing reality

- Stage 1, the **semantic router**, is regex and concept scoring with no model call: 39 intents, threshold 0.72, entity bonus only for five hardcoded demo client names. Three intents materialise (`manual_journal`, `finance_ops_action_plan`, `time_log`); seven read live data (`collections`, `single_bill_drilldown`, `cosec_reminders`, `management_pack`, `management_pack_drilldown`, `manual_journal_decision_trail`, `delivery_context`); **26 return static template prose**, several with hardcoded figures; three action intents (`billing_run`, `bill_pay_run`, `capped_tax_engagement`) fall through to stage 2.
- Stage 2, the **runtime**, is Hermes by default (external container, 29 broker tools, Claude Haiku 4.5, fallback to Basic on error) or Aethos Basic (in-process tool loop, 15 tools, at most 5 iterations, OpenRouter chain). Basic has the number-fidelity guard and tool chips; Hermes has neither; the semantic path has neither.
- **Every non-read tool routes to Inbox unconditionally** (`services/agent_tool_policy.py:113-132`). The "AI proposes, human disposes" story is real and enforced.
- Basic and Hermes turns write `agent_runs`; semantic answers do not.

### 3.3 Autonomy

Default L2 everywhere, read through three inconsistent paths (policy service, direct table read, nine hardcoded literals). Kill switch and circuit breaker (3 failures → 15 minutes open) work. The promotion loop is inert because `eval_passed_at` is never written. The only true L3 side-effect paths are the two email workers, and only if `level=3` is set by a direct database write. There is no auto-apply executor for extraction, journals, invoices, payments or close.

### 3.4 Document pipeline privacy posture

`build_document_content` (`agents/base.py:339`) scans raw bytes for PII and prompt injection. Text-layer PDFs with PII are reduced to masked text. **Scanned PDFs and images, which yield no extractable text, are sent whole as base64** — the cases that matter most (#498). The chat path masks correctly.

### 3.5 Code-level gaps not yet tracked as issues

- Missing tables queried: `expenses`, `collection_activities` (`agents/intelligence_agent.py:417`, `:723`).
- Dead modules: `services/automation_schedules_service.py` and table 0109 (zero importers); `agents/reporting_agent.py` (zero callers); live `_format_p2p_payment_risk` (not dispatched); two `atlas_runtime` helpers.
- 13 of 14 eval packs under `docs/test/agent_evals/` are never executed; the CI gate runs eight hardcoded cases.
- `atlas_hide_tool_events` honoured only on the semantic path; the Basic runtime emits tool events regardless.
- Hermes-prepared manual journals attributed to `accounting_guardian` (pollutes promoter statistics); `manual_journal_service` uses an agent name absent from every catalogue.
- `manual_journal_service.py:510-556` and `atlas_tools.py:838-874` insert suggestions directly, bypassing `suggestion_writer`.
- `stripe_reconcile.reconcile_sent_invoices` has no queue and no periodic decorator (the all-tenants wrapper is scheduled).
- FX refresh "already ran today" guard is global, not per tenant; promoter dedup is tenant-wide; `finance_controller` used as an approval-role string but is not a `UserRole`; Hermes `tools.include` (28) and `_TOOL_DISPATCH` (29) are hand-maintained with no test tying them together.
- Landing page copy promises no card at signup; the wizard requires one. The signup success step is dead code; `plan_tier` is hardcoded to `starter`.

## 4. Decision and next steps

Verdict changes to READY for paid launch only when W0 and W1 of
[`../team/LAUNCH_GAP_IMPLEMENTATION_PLAN.md`](../team/LAUNCH_GAP_IMPLEMENTATION_PLAN.md)
are merged and deployed, the deployed SHA is re-verified, and a founder
browser pass of Demo Guide v3 is recorded on a disposable tenant.

| Approver | Decision | Date |
| --- | --- | --- |
| QA (Aksha) | NOT SIGNED | |
| Security (Prahari) | NOT SIGNED | |
| Product (Netra) | NOT SIGNED | |
| Launch authority (Founder) | NOT SIGNED | |
