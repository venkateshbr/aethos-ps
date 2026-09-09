# Launch Gap Implementation Plan

> Owner: Vishwa (CPTO) · Design: Vastu · Date: 2026-09-09 · Source review:
> [`../qa/launch-readiness-review-2026-09-09.md`](../qa/launch-readiness-review-2026-09-09.md).
> Every item below becomes a GitHub Issue before code is written; this document
> is the sequencing and design reference, not the tracker.

## Conventions

Failing test first (`agent-harness/core/tdd-protocol.md`). Router → Service → Repository. Journals only through `app/domain/journal_helper.post_journal`. Agent proposals only through `agents/suggestion_writer.write_agent_suggestion`. `Decimal` money. Every query tenant-scoped. UI closure requires a Playwright spec under `frontend/e2e/`; backend closure requires a real-stack pytest run.

Prahari review is mandatory on A1, A2, A3, A6, A7, A8, A12, A14, B5. Tier-1 founder approval is required for A7 (new dependency and `agents/base.py` change → ADR-006), A8 (tenant isolation), B5 (L3 autonomy), B7 (financial data → ADR-007). Sizes: S ≤ 1 day, M 2–3 days, L 1 week or more.

## W0 — Close and merge what is done (half a day)

| Item | Issues | Owner | Action | Evidence |
| --- | --- | --- | --- | --- |
| A10 | #550 | Sthira | Merge PR #551. Follow-up: strip `-rc.N` before the version compare in `release.yml`. Dry-run with tag `v0.1.0-rc.1`. | Green Release run; rc images in GHCR |
| A15 | #492 #493 #494 #496 (demotion) | Aksha → Vishwa | Attach deploy run 33732519598, the migrate log, and the passing specs (`frontend/e2e/enterprise-controls-audit-rbac.spec.ts`, `backend/tests/api/test_payment_webhook.py`). Close with `state_reason=completed`; on #496 comment that promotion remains inert (B5). | Issue comments |

## W1 — Launch blockers (paid launch)

| ID | Gap | Owner | Size | Approach | Failing test first → acceptance |
| --- | --- | --- | --- | --- | --- |
| A2 | #514 environment separation, live keys | Sthira + Prahari | M | Runtime config injection instead of build-time constants: `frontend/public/runtime-config.template.js` rendered by an nginx entrypoint (`envsubst`) into `window.__AETHOS_CONFIG__` (Supabase URL, anon key, Stripe publishable key); `environment.prod.ts` reads it and hard-fails if absent. Compose passes the three values to `frontend` and `timesheet` from `AETHOS_PRODUCTION_ENV`. New production Supabase project: apply 0001–0122 through the `migrate` profile, run `scripts/seed_master_config.py`, register the live Stripe webhook and 30 live price IDs. `config.py` guard: production with a non-`sk_live_` key raises unless `ALLOW_TEST_BILLING_IN_PRODUCTION=true`. `/health/ready` surfaces `supabase_project_ref`. | `tests/unit/test_config.py::test_production_rejects_test_stripe_key`; `tests/unit/test_hostinger_deployment_contract.py::test_frontend_service_receives_runtime_config_env`; Playwright `production-config.spec.ts` → deploy run plus `/health/ready` showing `billing.mode=live` |
| A1 | Guide HTML public | Karya + Rupa + Prahari | M | **Option 1 (recommended):** `frontend/scripts/generate-guides.mjs` writes HTML to `backend/app/assets/guides/`; new thin router `GET /api/v1/guides` and `GET /api/v1/guides/{slug}` (`get_current_user`, tenant membership, `require_role(UserRole.admin)`, slug regex `^[a-z0-9-]+$`, `Cache-Control: private, no-store`); `guide-reader.component.ts:114` fetches `/api/v1/guides/{slug}` through the auth interceptor; delete `frontend/public/guide-content/`; nginx `location /guide-content/ { return 404; }`; CI step regenerates and `git diff --exit-code`. Rejected: nginx `auth_request` (no `ng serve` parity, two code paths) and a lazy Angular chunk behind the guard (chunks are public JS). | `tests/unit/test_guides_api_contract.py` (anonymous 401, member 403, admin 200 text/html, unknown 404, `../` 422); `tests/api/test_guides.py` cross-tenant probe; `frontend/e2e/guides.spec.ts` updated (member sees the error state) |
| A3 | #529 tool-broker bypass | Karya + Prahari | M | Extend `write_agent_suggestion` with optional `title`, `description`, `priority`, `task_payload_extra`, and `autonomy_level=None` (resolve via policy). `_create_engagement_review` calls `AgentToolPolicy.decide(engagement_letter_agent, create_engagement_draft, …)` and returns the `policy_denied` shape from `graph.py:952-960` when blocked; payload building moves to `EngagementsService.prepare_engagement_draft_from_prompt` (reused by B2). `_prepare_manual_journal_review` and `manual_journal_service._create_manual_journal_approval_task` replace direct inserts with the writer. Contract test greps `app/` for direct `agent_suggestions` / `hitl_tasks` inserts outside the writer (temporary allowlist for promoter, billing-run worker, finance-ops worker, inbox service). | `tests/unit/test_atlas_tools_api_contract.py::test_create_engagement_review_denied_by_policy_writes_nothing`; `tests/unit/test_suggestion_writer_is_sole_writer.py` → `tests/api/test_manual_journal.py`, `tests/api/test_copilot_chat.py` |
| A4 | #500 period lock at the API layer | Karya | M | `period_lock_service.assert_period_open` (today called only from time entries and manual journals) added to invoice create / approve / payment recording, bill create / approve, batch settle, expense create. Defense in depth: `journal_helper.post_journal` checks the lock on `entry_date` through a sync-safe helper. | Unit tests per service → `tests/api/test_period_lock.py` matrix: lock `2026-06`, seven June-dated writes → 422 `period_locked`, July-dated → success |
| A5 | #502 Stripe idempotency | Karya | S | `asyncio.to_thread` plus `idempotency_key` for Product / Price / PaymentLink (`inv:{id}:product`, `inv:{id}:price:{amount}:{ccy}`, `inv:{id}:plink:{amount}:{ccy}`); same in `stripe_service.py`, Connect account creation, refunds. Grep-contract test: every `stripe.<X>.create|modify(` includes `idempotency_key=`. | `tests/unit/test_invoices_service.py::test_send_invoice_passes_idempotency_keys_and_runs_off_event_loop` → `tests/api/test_invoice_send.py` |
| A6 | #503 rate limits | Karya + Sthira | S | Rules `chat_messages` (30/min per bearer hash) and `atlas_tools_execute` (120/min per IP plus per-tenant check after session resolution); `RateLimitRule.subject: ip \| bearer`; compose default `RATE_LIMIT_BACKEND=supabase` (RPC from migration 0089 exists). | `tests/unit/test_ops_hardening.py::test_chat_messages_rate_limited_per_bearer` → `tests/api/test_copilot_chat.py::test_chat_rate_limit_returns_429_with_retry_after` |
| A7 | #498 scanned documents raw to model | Karya + Prahari + Aksha | M (ADR-006) | `BinaryDocumentPolicy`: `ocr_verify` default — when extracted text is under 40 characters run local OCR (`rapidocr-onnxruntime`, verified through the package-verification skill; fallback tesseract), mask PII in the OCR text and send only masked text when PII is found; OCR unavailable → withhold the binary and cap confidence at 0.5 so the reviewer keys fields. Tenant override in AI settings. | `tests/unit/test_document_binary_policy.py` (three cases); scanned-receipt case in `docs/test/agent_evals/expense_extractor_agent.yaml` → `tests/api/test_agents_expense.py` |
| A8 | #531 Hermes memory | Sthira + Prahari | S / M | Launch posture: disable Hermes persistent memory in `integrations/hermes/aethos-atlas-profile/config.yaml` (Aethos already persists `chat_messages`); two-direction isolation probe; `delete_tenant` purge hook for when memory is re-enabled; ops-manual section on memory and retention. | `tests/api/test_hermes_isolation.py` both directions → deploy run with `ls /opt/data` evidence |
| A9 | #507 Nous card Edit approves | Rupa | S | `editCard()` navigates to `/app/inbox?task=<id>&edit=1`; Inbox reads the query params, focuses the card and opens the approve-with-edits drawer. | Karma spec on `copilot.component`; Playwright `copilot-edit-routes-to-inbox.spec.ts` asserting the task remains `open` |
| A11 | CI gates (#495) | Sthira + Aksha | M | mypy hard-fail on a curated file list and ratchet outward; `pip-audit --strict` with a Prahari-reviewed ignore file; `ng add @angular-eslint/schematics` and a `npm run lint` step; new `e2e-smoke` job for same-repo PRs using a CI Supabase project, `webServer` entries in `playwright.config.ts`, running `@smoke` specs (landing, login, 00-signup, auth-guard, guides, copilot-thread-tenant-header). | `tests/unit/test_ci_workflow_contract.py` (no `\|\|` on mypy / pip-audit, lint and e2e-smoke jobs present) → green CI run. Depends on A2 |
| A12 | Password recovery and invite email | Karya + Rupa + Prahari | M | `POST /auth/forgot-password` always 202; `auth.admin.generate_link(type=recovery, redirect_to=<FRONTEND_BASE_URL>/reset-password)` → `ResendService.send_email` using a new `email_templates.py` (reset, invite, invoice); rate-limit rule 5 per 15 minutes. `POST /auth/password-reset/complete` (authenticated) clears `must_change_password`. Invites in `tenant_users_service` and `employees_service` email the link; `temp_password` returned only when the caller supplied one; `set_password_url` returned only in non-production when email is skipped. Resend sender configurable. Frontend routes `/forgot-password` and `/reset-password` (handles Supabase `PASSWORD_RECOVERY` → `updateUser`), "Forgot password?" link on `/login`, invite dialogs show "Invitation emailed" with resend. Supabase redirect allowlist per environment. | `tests/unit/test_auth_api_contract.py` (202 always, unknown email sends nothing, rate limited); `tests/unit/test_tenant_users_invite_email.py` → `tests/api/test_auth_password_reset.py`; Playwright `forgot-password.spec.ts`, `invite-user.spec.ts`. Depends on A2, A6 |
| A13 | Landing and signup truth | Rupa + Karya | S | Copy becomes "14-day free trial · cancel anytime"; test-card helper only when the key starts with `pk_test_`; `start_trial` maps `price_id` to tier and updates `tenants.plan_tier`; wire the step-4 success screen with "Open Nous" and an onboarding link. | `tests/unit/test_stripe_service.py::test_start_trial_sets_plan_tier_from_price` → updated `00-signup.spec.ts`, `landing.spec.ts` |
| A14 | #516 invoice delivery | Karya + Rupa | M | After Payment Link creation send a Resend email with the public invoice URL and pay link (422 `client_email_missing` unless `deliver_email=false`); migration `0123_invoice_delivery.sql` adds `delivery_status`, `delivered_at`, `resend_message_id`; route `p/:token/thanks` renders the public invoice with a payment-received banner; server-side PDF deferred to W3 (public page prints). | `tests/unit/test_invoices_service.py::test_send_invoice_emails_client_with_public_link` → `tests/api/test_invoice_send.py`; Playwright `public-invoice-thanks.spec.ts`. Depends on A5, A12 |

**Critical path to paid launch:** A2 → A12 → A14 (environment → auth email → invoice email), roughly 2.5–3 weeks with three engineers in parallel lanes:

- Sthira / Prahari: A10 → A2 → A6 (backend) → A8 → A11
- Karya: A3 → A4 → A5 → A6 (rules) → A12 → A14 → A7
- Rupa: A9 → A13 → A1 (frontend) → A12 (routes) → A14 (thanks route)
- Aksha: the Playwright specs above; A15 evidence

A7 can ship the `withhold_unverified` fallback first; A11 can slip a few days without blocking the first paid tenant.

## W2 — Credible agentic demo on a fresh tenant

### B1 — Live semantic responders, entity resolution, parametric intents (Karya, Dhruva for evals) — L, split B1a / B1b

Responder → source-of-truth mapping for the 26 static intents (every read pack exists unless marked new):

| Intent (current) | New name | Source of truth |
| --- | --- | --- |
| `configuration_telemetry` | same | `AtlasReadPackService.operational_health_read_pack` |
| `approval_controls` | same | `AgentsService.get_approval_controls_read_pack(user_id)` |
| `finance_ops_control_room` | same | `AgentsService.get_finance_ops_control_room()` |
| `finance_ops_check` | same | `atlas_tools._finance_ops_snapshot` |
| `invoice_drilldown` | same | `O2CReadService.collections_read_pack(invoice_number)` |
| `brightwater_retainer` / `_milestone` / `_payroll` | `client_billing_model` | `engagement_structure_read_pack(client)` + billing terms; action mode → B2 `draft_invoice` |
| `alderton_family_office` | `client_structure` | `engagement_structure_read_pack` + `ClientGroupsService` |
| `alderton_scope_creep` | `project_scope_review` | `ReportsService.scope_change_advisor` + `project_pnl` |
| `thornton_usd_billing` | `client_fx_billing` | collections pack filtered to non-base currency + `fx_gain_loss_service` + `ar_aging` |
| `thornton_cosec_instruction` | `cosec_instruction` | `cosec_reminders_read_pack`; action → B4 `cosec_instruction_review` |
| `close_readiness` / `period_lock` | same | `CloseStatusService.get_status(period)` |
| `statement_package` | same | `_generate_financial_statement_package` |
| `year_end_close` | same | `YearEndCloseService.preview_year_end_close(year)` |
| `trial_balance` | same | `ReportsService.trial_balance` |
| `reversal_packet` | same | new `R2RReadService.reversal_preview(entry_number)` |
| `decision_trail` | same | new generalised `decision_trail_read_pack(entity_type, ref)` |
| `operational_health` | same | `operational_health_read_pack` |
| `documents_audit` | same | `documents_audit_read_pack` |
| `vendor_invoice_intake` | same | `document_intake_read_pack` |
| `p2p_payment_risk` | same | fix dispatch at `atlas_deterministic_responses.py:224` to the existing live `_format_p2p_payment_risk`; delete the static variant |
| `o2c_readiness` | same | new `O2CReadService.billing_readiness_read_pack` (catalogue coverage, rate card, tax rates, WIP, drafts) |
| `revenue_recognition` | same | `RevenueRecognitionScheduleService` + `revenue_by_engagement` |
| `delivery_context` | same | `resource_delivery_read_pack`; delete the Alice / 64 % branch |
| `series_a` | `milestone_billing_event` | billing terms success-fee percentage × event amount; action → `draft_invoice` |

Entity resolution: new `services/atlas_entity_resolver.py` — `TenantEntityResolver(db, tenant_id).resolve(message)` returns client / vendor / engagement / project / employee with `{id, name, score}` plus `ambiguous`; tenant-scoped loads (≤ 250 rows, 60 s cache); normalised substring → distinctive-token overlap with a legal-suffix stoplist → `SequenceMatcher ≥ 0.8`; a top-two gap under 0.1 asks and takes no action. The router stays database-free: `AtlasSemanticIntentRouter(lexicon)` replaces `_CLIENT_TERMS`, client-named intents become parametric, and the period default becomes the tenant's current period.

Deterministic demo preserved: the Meridian seed creates the five names, so routing is unchanged on the demo tenant while figures come from rows. Golden tests keep every Demo Guide prompt with a lexicon fixture plus a Hypothesis test that any other client name yields the same intent. `tests/unit/test_seed_demo_v2.py::test_seed_totals_match_demo_guide_table` pins seeded amounts to the guide's quoted numbers.

Also in B1a: the number-fidelity guard on the semantic path (`unsupported_money_figures` over the pack payload before emit) and an `agent_runs` row for every semantic answer (`_run_with_ledger(intent, …, risk_class="read_only")`).

Tests: one unit test per mapping row (`tests/unit/test_atlas_deterministic_live_responders.py`), `tests/unit/test_atlas_entity_resolver.py`; acceptance `tests/api/test_copilot_chat.py` on a tenant with non-Meridian names; Playwright `copilot-live-readouts.spec.ts` (eight prompts compared to `/api/v1/reports/*`); `docs/test/agent_evals/copilot_agent.yaml` extended. Depends on A3.

### B2 — Materialise action intents; `create_engagement` tool (#363) — Karya — M

Add `billing_run`, `bill_pay_run`, `engagement_create` to `_DETERMINISTICALLY_MATERIALIZED_ACTIONS`. `billing_run` → `_draft_invoice` per resolved engagement; `bill_pay_run` → `_propose_bill_payment_batch` ("this week" → 7 days); new copilot tool `create_engagement` (risk `draft`) using `EngagementsService.prepare_engagement_draft_from_prompt`; Hermes `aethos.engagements.create_review` delegates to the same service. Tests: `tests/unit/test_atlas_deterministic_action_fallback.py` (three cases), `tests/unit/test_copilot_tools.py::test_create_engagement_routes_to_hitl`; Playwright `copilot-billing-run-live.spec.ts`, `copilot-create-engagement-live.spec.ts`. Depends on A3, B1a.

### B3 — Expense project resolution, then expense lifecycle (#518) — Karya + Rupa — M + M

The extractor emits `project_hint`; the worker resolves it through the entity resolver (plus the uploader's recent time entries) into `project_id` and a confidence, otherwise `requires_fields: [project_id]`; `_materialise_expense` raises 422 `project_required` instead of reporting success; the Inbox drawer adds a required project select for `create_expense_draft`. Second PR: migration `0124_project_expenses_lifecycle.sql` (`status`, `approved_by`, `journal_entry_id`), endpoints submit / approve / reject / reimburse, approve posts DR 5100 / CR 2100 through `post_journal`, billable approved expenses flow into invoice drafts, A4 lock on `expense_date`. Tests: `tests/unit/test_inbox_expense_materialization.py`, property `tests/property/test_expense_journal_balanced.py`; Playwright `expense-receipt-to-approval.spec.ts`. Depends on B1a, A7, B10(c).

### B4 — Materialisers for every HITL kind; alert cards; #499 — Karya + Rupa — M

Branches: `promote_autonomy` → level update (B5); `autonomy_demotion`, `finance_ops_escalation`, the four project-health kinds and six intelligence kinds → `_materialise_alert_acknowledgement` (records the decision; optional follow-up such as `OVERDUE_ESCALATION` → `draft_collection_reminders`); `cosec_instruction_review` → `cosec_compliance_obligations` row plus project work item. `intelligence_agent` reads `project_expenses` and the reminders table. Frontend `isIntelligenceKind()` over `ANOMALY_TYPES`. Guard test `test_every_written_kind_has_a_materialiser` introspects registry action types and worker kinds against `_materialise` branches. Playwright `inbox-alert-cards.spec.ts`.

### B6 — Billing Runs UI (#515) — Rupa — M

New `features/billing-runs/billing-runs.component.ts` (list, detail, Approve → `PATCH /billing-runs/{id}/approve`, loading / error / empty states); move Pay Bills to `/app/pay-bills`; rename the nav label. Playwright `billing-runs-ui.spec.ts`.

### B10 — Demo fixture generalisation — Karya + Aksha — S / M

`seed_demo_v2 --owner-email` for tenants created through the UI; link every seeded employee to a matching `tenant_users` row so chat time logging resolves the current user; deterministic receipt PDF asset containing "Project: Nexus CFO Advisory" plus a seed upload step; remove the Alderton / SGD / 18000 defaults (with B1a). Re-run `frontend/e2e/demo-v2-full-scenario.spec.ts` on a fresh tenant.

### B11 — Hermes verification (#530 residual) — Sthira + Rupa — S

`/health/ready` gains `checks.hermes` (`required=false` while fallback is on); the chat SSE stream emits a first frame `{runtime, fallback}` and the Nous UI shows "Nous · Hermes" or "Nous · Basic (fallback)" without tool names; `docs/infra/HOSTINGER_DEPLOYMENT.md` profile guidance changed to `COMPOSE_PROFILES=worker,hermes`. Tests: `tests/unit/test_ops_hardening.py::test_health_ready_reports_hermes`, a docs-versus-workflow contract test; Playwright `copilot-runtime-badge.spec.ts`.

**Minimum for a credible fresh-tenant demo:** B1a → B2 → B4 → B3 (project resolution only) → B10 → B11 → B6. B1b widens breadth.

## W3 — Completeness

| Item | Issue | Owner | Approach | Tests | Size |
| --- | --- | --- | --- | --- | --- |
| B5 autonomy loop | #497 #496 | Karya + Prahari (Tier 1) | Writer resolves level through `AgentToolPolicy`; replace the 17 hardcoded `autonomy_level=2` literals (accrual, FX remeasurement, revenue recognition × 4, prepaid, recurring, `graph.py:1849`, `atlas_tools.py:509`, `bill_payments.py:219`, project health, finance ops, time-entry reminder, collections, intelligence); money-out stays L2 through `max_auto_risk`; the eval runner writes `eval_passed_at` / `eval_score` on pack pass in a nightly live job; `promote_autonomy` approve raises the level with `promoted_by`; promoter dedup per agent and action; `AutoApplyExecutor` for an allowlist of low-risk kinds (`copilot_log_time_entry`, `send_time_entry_reminder`) | `tests/unit/test_autonomy_promoter.py::test_dedup_is_per_agent_action`, `tests/unit/test_agent_tool_policy.py::test_writer_resolves_autonomy_from_policy`, `tests/unit/test_auto_apply_executor.py`, a literal-forbidding contract test | L |
| B7 void and credit notes | #517 | Karya + Rupa (Tier 1, ADR-007) | `POST /invoices/{id}/void` (reversing journal through `post_journal`, `reverses_entry_id`, A4 lock, `PaymentLink.modify(active=False)` with idempotency key); `POST /invoices/{id}/credit-notes` (`credit_notes` table, DR Revenue / CR AR, applied balance); UI actions on invoice detail | `tests/property/test_void_reversal_balanced.py`, `tests/api/test_invoices.py::test_void_in_locked_period_rejected`, Playwright `invoice-void.spec.ts` | L |
| B8 onboarding and T&C | #519 | Rupa + Karya | `/app/onboarding` checklist from `GET /tenants/me/onboarding`; signup T&C checkbox → `accepted_terms_version` (422 if missing); migration `tenants.terms_accepted_at`, `terms_version` | `tests/api/test_signup_and_billing.py::test_signup_requires_terms`; Playwright `onboarding-checklist.spec.ts` | M |
| B9 dead code | — | Karya + Dhruva | Delete `automation_schedules_service.py` (note on table 0109) and `reporting_agent.py` with its registry rows and eval yaml; the eval gate iterates all `docs/test/agent_evals/*.yaml` in a nightly live job; demo filename shortcuts in `document_extraction.py:396-524` behind `demo_fixtures_enabled` (default false, refused in production) | `tests/unit/test_documents.py::test_demo_filename_shortcuts_disabled_by_default`, `tests/unit/test_eval_gate.py` | S |
| B12 docs | Review §2.1 | Dhruva | After W1 / W2 merge: user guide, Demo Guide v2, Hermes ops manual (memory, health check, badge), `backend/CLAUDE.md`, `frontend/CLAUDE.md` | Guides regeneration diff check from A1 | S–M |
| Roadmap (unchanged) | #520–#528, #404–#419, #533–#535 | — | Workspace switcher, CSV import, export and erasure, notifications, platform-admin plane, learning loop, bank rails, Xero / QBO | — | — |

## Critical files across waves

`backend/app/services/atlas_deterministic_responses.py`, `backend/app/api/v1/endpoints/atlas_tools.py`, `backend/app/agents/suggestion_writer.py`, `backend/app/services/inbox_service.py`, `backend/app/services/invoices_service.py`, `frontend/src/app/features/copilot/copilot.component.ts`, `frontend/scripts/generate-guides.mjs`, `docker-compose.hostinger.yml`, `.github/workflows/ci.yml`.
