# Aethos PS Agentic ERP Gap and Enhancement Plan

Review date: 2026-06-22  
Repo: `aethos-ps`  
Mode: living implementation tracker; update dated implementation status as code and issue state change.

Last implementation revalidation: 2026-06-23.

## 2026-06-23 Implementation Status Update

This plan was revalidated against the current codebase, migrations, Angular routes/services, tests, and PR #256. Items below are now implemented and should not be reopened as generic gaps without a new regression or a sharper product requirement.

Done:
- Phase 0 API/UI contract gaps are implemented: `/api/v1/accounts`, `/api/v1/tax-rates`, `/api/v1/expenses`, `/api/v1/invoices/draft`, and `POST /api/v1/bills/{id}/void` are registered backend routes and have focused tests.
- Manual journal posting no longer writes the stale `journal_entries.reference` column; manual journals use the current `reference_id` schema path.
- Invoice and bill approval RBAC is now aligned to admin+ approval for money/accounting transitions.
- Service-catalogue tests and fixtures are now isolated enough for the backend suite.
- Frontend environment config uses relative API URLs for local and production builds.
- `backend/scripts/seed_demo.py --reset` exists and is idempotent for demo tenants.
- `make demo-ready` now wraps local server startup/reuse, demo reset/seed, API smoke checks, and selected Playwright demo specs.
- Manual invoice creation now calculates per-line tax from active system or tenant tax rates, and invoice approval splits tax to `2300 Sales Tax Payable`.
- Bill approval now keeps net line amounts on expense accounts and posts bill tax to `1300 Input Tax Recoverable` before crediting AP for the gross bill total.
- Local frontend runtime is pinned to supported Node 20 via root `.nvmrc` and frontend package `engines`; CI and Docker already use Node 20.
- Backend quality gates were restored on PR #256: full backend pytest passed (`861 passed, 57 xfailed, 1 xpassed`), ruff passed, frontend production build passed, and full Chromium Playwright passed (`110 passed, 11 skipped`).
- Agent operating-model tables exist via migrations `0034` to `0037`: `agent_runs`, `agent_tool_invocations`, `agent_workflow_runs`, `agent_memory_items`, kill/circuit state, eval candidates, and L3 promotion gates.
- Central agent tool-risk registry exists in `backend/app/agents/tool_registry.py`, with risk classes for Copilot, reporting, invoice, billing, collections, bill pay, accrual, revenue, accounting, project health, and intelligence actions.
- Agent controls are surfaced through `/api/v1/agents/*` and Settings UI: run dashboard, eval candidates, L3 policy, kill switches, and per-agent/tool circuit breaker controls.
- Deterministic recorded replay is available through `POST /api/v1/agents/runs/{run_id}/replay` and the Settings agent-run panel; it reconstructs stored tool-call snapshots without executing tools.
- Services-business intelligence endpoints and Angular typings now cover project health, capacity planning, client profitability, client-group profitability, segment profitability, practice dashboards, pricing/staffing recommendations, and scope-change advisor.
- Role-based operating action queues are available through `/api/v1/reports/action-queue` and the Reports Action Queue tab for partner, finance, project manager, and AP clerk personas.
- Backlog forecast and milestone-risk reports are available through `/api/v1/reports/backlog-forecast` and `/api/v1/reports/milestone-risk`, surfaced in the Reports Backlog tab, and feed partner/project-manager action queues.
- Client groups have API, UI, member roles, and profitability rollups.
- Employee resource profiles now include a billable-utilization target, maintained in the People UI and used by capacity planning/action-queue evidence.
- Service-catalogue linkage is now end-to-end across engagement setup, UI invoice drafting, billing-run invoice materialisation, invoice line create/response contracts, tenant FK validation, persistence, and service-line revenue reporting.
- Project planning now persists budget hours from the UI and exposes project phases as scheduled milestones/deliverables with acceptance criteria and percent-complete tracking through API and UI; milestone-risk/backlog reports already consume these phase schedules.
- Per-unit billing terms are implemented for payroll/per-employee style services: engagement creation captures billing unit, unit label, quantity, and unit price, computes fixed-fee compatibility totals, and invoice drafts emit quantity x unit-price lines.
- T&M invoice drafting now honors assignment-level employee override rates and existing client-specific rate-card override rows before falling back to base role rates.
- Financial close now has persisted close tasks by period, API/UI bootstrap and completion controls, and period lock blocks incomplete bootstrapped tasks.
- Bill payment lifecycle now includes approve, export, mark-sent, and settlement, with integrity metadata and financial-event coverage.
- R2R financial statements now include `/api/v1/reports/balance-sheet`, `/api/v1/reports/income-statement`, and `/api/v1/reports/cash-flow`, plus Reports UI tabs backed by posted journal lines in base currency.
- Financial-event audit log, authenticated read RLS reduction, document preflight PII/prompt-injection handling, localization profiles, and integration catalog are implemented under Phase 5.

Still open:
- `make demo-ready` needs to be run against a real demo tenant and captured as launch evidence.
- Demo report/screenshots were intentionally not regenerated in this pass.
- Recorded agent replay is implemented; full re-execution against current code and external providers remains open.
- `agent_workflow_runs` exists, but Phase 3 long-running autonomous workflow orchestration is still partial.
- Role-based action queues are implemented from report evidence; deeper personalized ownership/assignment queues remain open.

## Executive Verdict

Aethos PS already has the shape of a professional-services ERP: tenant auth, contacts, employees, engagements, projects, time, invoices, bills, journals, reports, documents, HITL, and several agents are present. The strongest architectural choices are the tenant-scoped FastAPI/Supabase spine, the `agent_suggestions` + `hitl_tasks` review substrate, and the use of a canonical accounting guardian before journal posting.

The platform is not yet a reliable autonomous ERP. The current system behaves more like an AI-assisted PSA/ERP MVP with manual and semi-automated workflows. The main gap is not just missing screens; it is the missing agent operating model: durable workflow plans, per-tool authorization, agent run telemetry, eval-driven promotion, deterministic replay, and scheduled autonomous execution across engagement-to-cash, procure-to-pay, and record-to-report.

2026-06-23 status: demo and contract stabilization is materially complete. The remaining launch-readiness work is a real-tenant `make demo-ready` evidence run, refreshed evidence report, FX/Stripe browser coverage, and live agent replay re-execution.

## Original Evidence Gathered On 2026-06-22

The evidence below is retained for audit history. Several failures in this original review have since been fixed; use the 2026-06-23 implementation status update above as the current source of truth.

Repository and context reviewed:
- `CLAUDE.md`
- `agent-harness/adapters/claude/CLAUDE.md`
- `agent-harness/adapters/codex/AGENTS.md`
- `agent-harness/core/*` standards for SDLC, quality gates, e2e, evals, security
- `docs/PLAN.md`
- `docs/team/PROJECT_CONTEXT.md`
- `docs/team/SDLC_PROTOCOL.md`
- `domain_packs/professional-services/pack.yaml`
- Demo and scenario docs under `docs/DEMO_GUIDE_v2.md`, `docs/demo-v2-test-report.md`, and `docs/test/*`

Original live verification:
- Backend health on `127.0.0.1:8012`: `/health` returned ok.
- Backend readiness: DB reachable, queue reported `not_configured`.
- Backend unit tests: `448 passed`.
- Backend property suite: not runnable because local venv is missing `hypothesis`.
- Backend lint: `ruff check backend/app backend/tests` failed with 61 lint issues.
- Live API subset: `53 passed, 5 failed, 5 errors`.
- Selected Playwright suite: 1 setup test passed, 14 scenario tests failed.
- Angular dev server compiled, but reported Angular template warnings and Sass deprecation warnings.
- Local Node is `24.14.0`, which Angular 19 reports as unsupported.

Original key live API failures:
- `test_manager_cannot_approve_invoice_admin_can`: manager can approve invoice, but test expects admin-only.
- Manual journal post tests return 500.
- `test_service_catalogue.py` setup collides with existing cloud data due duplicate account code `4000`.

Original key E2E failures:
- Most selected specs landed on the marketing page after navigating to `/app/*`, so the saved auth state is stale or incompatible with this local/Supabase run.
- The Meridian demo spec authenticated via fallback, reached Copilot, then timed out while the composer remained disabled during a `get_wip` tool run.
- The current `docs/demo-v2-test-report.md` says the demo passed on 2026-06-21, but today’s run does not reproduce it.

## Market Baseline

The current competitive direction is converging around four ideas:

1. PSA/ERP depth for services firms is still table stakes. Microsoft Dynamics 365 Project Operations covers pricing/costing, fixed/T&M/retainer contracts, project budgets, resource skills, utilization, time, expense, approvals, project accounting, billing, revenue recognition, and service-centric ERP interoperability. Source: https://www.microsoft.com/en-us/dynamics-365/products/project-operations

2. NetSuite PSA frames the lifecycle as opportunity through project delivery, invoicing, and revenue recognition, with project accounting, project management, resource management, timesheets, expenses, analytics, and budget management. Source: https://www.netsuite.com/portal/products/professional-services-automation.shtml

3. Agentic ERP is being positioned as governed agent teams embedded in business systems, not just chat. Oracle describes agents as planners that gather information, act with tools, learn from feedback, and receive graduated autonomy. Oracle and SAP are both pushing agent teams grounded in enterprise data, permissions, governance, and audit. Sources: https://www.oracle.com/artificial-intelligence/ai-agents/ and https://www.itpro.com/technology/artificial-intelligence/oracle-announces-new-proactive-enterprise-agents-at-ai-world-tour-london

4. Agent governance is becoming a product surface. Microsoft Agent 365 is framed as a control plane for registering, monitoring, permissioning, and protecting agents. Source: https://www.theverge.com/news/822035/microsoft-agent-365-businesses-control-security

Implication for Aethos PS: the differentiator should not be “chat over ERP.” It should be a governed, auditable services-business operating system where agents own routine work, humans handle exceptions, and manual mode is always available.

## Current Capability Map

### Engagement To Cash

Present:
- Clients/customers.
- Engagements with billing arrangements.
- Projects, assignments, time entries, simple approvals.
- Invoice drafter agent.
- Invoices and invoice lines.
- Invoice approval, send, public invoice, payment link, manual payments.
- AR aging, WIP, project P&L, utilization, revenue reports.
- Copilot tools for WIP, AR, time logging, and rate-card updates.
- Billing runs and a Meridian demo narrative.

Gaps / status:
- Done 2026-06-23: billing terms UI now supports fixed, T&M, retainer, retainer drawdown, milestone, capped T&M, mixed, and per-unit payroll/per-employee terms.
- Done 2026-06-23: invoice persistence now supports negative adjustment lines used by capped T&M cap adjustments and retainer-draw offsets while still blocking net-negative invoice totals.
- Done 2026-06-23: tax-rate API/settings UI, seeded market defaults, invoice drafter tax, manual invoice line tax, invoice approval tax-payable split, and bill approval input-tax-recoverable split are implemented.
- Partial 2026-06-23: WIP accrual, deferred revenue release, and milestone revenue recognition proposal endpoints/agents exist and flow through HITL draft-journal approval/posting. Remaining revenue-recognition depth is retainer balance/drawdown automation, percentage-of-completion accounting, prepaid amortization, and broader schedule management.
- Done 2026-06-23: client groups and member roles exist with API/UI and profitability rollups. Remaining multi-entity work is legal-entity depth and demo-grade family-office workflows.
- Open: no client portal workflow beyond public invoice payment.
- Done/verification open 2026-06-23: Copilot write tools are registered in the common tool-risk registry and policy path. Live LLM time logging remains open for verification in GitHub issue #253.

### Procure To Pay

Present:
- Vendor contact kind.
- Vendor invoice extraction agent with duplicate checks, vendor matching, tax ID warnings, and GL suggestions.
- Bills and bill lines.
- Bill approval posts AP journal through the accounting guardian.
- AP aging.
- Bill payment batches, approval, export, and mark-sent.
- Bill-pay agent that proposes batches as HITL.

Gaps / status:
- No purchase requests, purchase orders, service orders, or PO matching.
- Vendor onboarding lacks bank-account verification, sanctions/tax validation, remittance controls, and approval workflow.
- Done/partial 2026-06-23: bill approval now preserves line-level expense coding in the AP journal, but the extraction-to-coding feedback loop still needs stronger closed-loop validation.
- Partial 2026-06-23: bill-payment export now has integrity metadata and approval/export/send/settlement controls. Bank-native NACHA/BACS/ABA/GIRO/NEFT validation remains future P2P depth.
- Done 2026-06-23: `mark-sent` is no longer the terminal lifecycle; settlement is implemented.
- Money-out controls should remain stricter than money-in controls.

### Record To Report

Present:
- Chart of accounts schema.
- Journal entries and journal lines.
- Period locks.
- Accounting guardian validates journal balance, period lock, and accounts.
- Trial balance, aging, utilization, WIP, project P&L, revenue and service-line reports.
- Balance sheet, income statement, and direct cash-flow reports.
- Manual journal UI exists.
- R2R close PRD exists: `docs/prd/r2r-financial-close-v1.1.md`.

Gaps / status:
- Done 2026-06-23: manual journal post regression is fixed; the service uses the current `reference_id` schema path.
- Done/partial 2026-06-23: balance sheet, income statement, and direct cash-flow reports are implemented from posted journal lines with UI tabs. Retained earnings year-end roll-forward and statutory reporting packs remain open.
- Done/monitor 2026-06-23: close status, close readiness, close package, reconciliation services, WIP accrual proposal, deferred revenue release proposal endpoints, and persisted close task workflow exist; period lock now blocks incomplete bootstrapped close tasks.
- Partial 2026-06-23: automated accrual and deferred revenue proposal agents exist, but prepaid amortization, recurring journals, and guided close automation remain open.
- FX is partially implemented but not consistently surfaced in reports as transaction currency plus base currency.
- Period close is not yet a guided autonomous workflow.

### Agent Platform

Present:
- Agents: engagement letter, expense extractor, vendor invoice, invoice drafter, reporting, project health, collections, bill pay, intelligence, Copilot, accounting guardian.
- `agent_suggestions`, `hitl_tasks`, and `agent_corrections`.
- Autonomy settings and autonomy promoter worker.
- Agent eval pack files exist in `docs/test/agent_evals`.
- PII masking helper exists and text prompts use it in several agents.

Gaps / status:
- Done/partial 2026-06-23: `agent_runs` and `agent_tool_invocations` now capture input/output hashes, model/prompt versions, usage/cost fields, status, trace IDs, replay pointers, and a recorded replay manifest. Coverage across every agent-created mutation and live re-execution still need hardening.
- Done 2026-06-23: central tool registry with per-agent tool/action risk classes exists.
- Partial 2026-06-23: `agent_workflow_runs` exists as the durable workflow container, and the monthly retainer billing-run worker now records running/skipped/waiting-on-human/failed workflow states. Remaining work is consistent workflow-run adoption across the other long-running Phase 3 workers.
- Queue is `not_configured` in the live readiness check, so scheduled autonomy is not operational in this local/live run.
- Done 2026-06-23: document preflight scanning masks decoded text and withholds sensitive/adversarial PDF/image content from external LLM calls when detected.
- Partial 2026-06-23: human corrections become eval candidates and L3 policy fields exist. Runnable eval gate and drift dashboard are still not mature.
- Done/verification open 2026-06-23: Copilot UI/E2E resilience was hardened in PR #256; live LLM tool execution still needs issue #253 verification.

### Frontend And Contract Surface

Present:
- App shell with feature routes for Copilot, inbox, clients, engagements, projects, invoices, bills, billing runs/pay bills, reports, accounting, documents, settings, people, time, expenses.
- Manual backup surfaces exist for several workflows.
- Settings include autonomy, tax rates, services, and Stripe Connect.

Contract status:
- Done 2026-06-23: `/api/v1/accounts`, `/api/v1/tax-rates`, `/api/v1/expenses`, `/api/v1/invoices/draft`, and `POST /api/v1/bills/{id}/void` are registered backend routes.
- Done 2026-06-23: local and production Angular environments use relative API URLs.
- Done/monitor 2026-06-23: Playwright auth/storage-state was hardened enough for the full Chromium suite to pass. Keep new protected-route specs fail-fast so landing-page redirects cannot masquerade as passing tests.

## Critical Blockers Before Feature Expansion

1. Done/monitor 2026-06-23: stabilize auth/test-state for Playwright.
   - Full Chromium suite passed on PR #256.
   - Keep fail-fast checks for protected-route specs so landing-page redirects are never counted as valid coverage.
   - Continue using `AETHOS_PS_WEB_URL` and `AETHOS_PS_API_URL` for new specs.

2. Done 2026-06-23: fix live API regressions.
   - Manual journal 500 is fixed through the `reference_id` path.
   - Invoice approval RBAC is admin+.
   - Service catalogue fixtures no longer block the backend suite.

3. Done 2026-06-23: close frontend/backend contract gaps.
   - Add or remove `/accounts`, `/tax-rates`, `/expenses`, `/invoices/draft`, `/bills/{id}/void`.
   - Prefer API routes that match existing UI expectations only when the product contract makes sense.

4. Partial 2026-06-23: make the demo reproducible.
   - `seed_demo.py --reset` exists and full Chromium E2E passed.
   - Done: `make demo-ready` starts/reuses backend/frontend, resets/seeds the tenant, runs API smoke, and runs selected demo E2E specs.
   - Pending: execute `make demo-ready` against the launch demo tenant and archive the evidence.
   - Pending: regenerate `docs/demo-v2-test-report.md` only when screenshots/report updates are explicitly in scope.

5. Partial 2026-06-23: restore quality gates.
   - Done: `ruff` passes.
   - Done: backend dev dependencies include Hypothesis and the full backend suite passed.
   - Done 2026-06-23: pin a supported Node 20 runtime for Angular 19 local development.
   - Pending: make `/health/ready` queue status green when workers are required for the demo.

## Enhancement Plan

### Phase 0: Demo And Quality Stabilization

Goal: make the existing platform trustworthy enough to demo and build on.

Work items:
- Done 2026-06-23: repair Playwright auth and selected E2E suites.
- Done 2026-06-23: fix manual journal, invoice RBAC, and service-catalogue fixture isolation.
- Done 2026-06-23: implement broken UI contracts.
- Done 2026-06-23: normalize frontend environment configuration.
- Done 2026-06-23: fix lint and dev dependency drift.
- Done 2026-06-23: make `seed_demo.py --reset` idempotent against Supabase cloud data.
- Done 2026-06-23: add a "demo readiness" command that starts backend/frontend, seeds tenant, runs smoke API, then runs selected E2E specs.

Acceptance:
- Done 2026-06-23: backend pytest passed on PR #256 (`861 passed, 57 xfailed, 1 xpassed`).
- Done 2026-06-23: `ruff check backend/app backend/tests` passes.
- Done 2026-06-23: full Chromium Playwright passed (`110 passed, 11 skipped`).
- Pending: `make demo-ready` execution against a real launch demo tenant.
- Pending: demo report regeneration with current date and evidence.

### Phase 1: Complete The Professional-Services ERP Spine

Goal: close baseline PSA/ERP gaps versus NetSuite and Dynamics Project Operations.

Work items:
- Done 2026-06-23: Accounts API and account picker across accounting/service catalogue/bills.
- Done 2026-06-23: Tax-rates API, tax defaults, settings UI, invoice drafter tax, manual invoice line tax, invoice approval tax-payable splitting, and bill approval input-tax-recoverable splitting are implemented.
- Done/monitor 2026-06-23: Expenses API and UI list/create completion.
- Done 2026-06-23: Billing terms UI supports fixed, T&M, capped T&M, retainer, retainer drawdown, milestone, mixed, and per-unit payroll/per-employee billing.
- Done/UX depth 2026-06-23: Rate-card API/UI and engagement picker exist; assignment-level employee override rates, client-specific overrides, and service-line-specific role rates are honored in invoice drafting. Remaining price-book work is richer admin UX/reporting around segmented rate books.
- Done 2026-06-23: Service catalogue API/settings/engagement/report integration exists, and invoice lines now accept, validate, persist, return, and propagate `service_catalogue_id` from UI drafts and billing-run drafts into service-line revenue reporting.
- Partial 2026-06-23: Client groups, member roles, UI, and report rollups exist; deeper legal-entity semantics remain open.
- Done 2026-06-23: Project budgets, budget hours, phases, deliverables, milestone schedules, acceptance criteria, and percent-complete tracking are implemented through API/UI and feed milestone-risk/backlog reporting.
- Done 2026-06-23: Resource profile includes cost rate, skills, availability, practice area, seniority, utilization target, and capacity reporting.

Acceptance:
- Partial 2026-06-23: engagement-to-cash coverage spans fixed, T&M, retainer, milestone, capped T&M, and multi-currency, but several Stripe/FX/period-lock/browser assertions remain `test.fixme` in `frontend/e2e/engagement-to-cash.spec.ts`.
- Partial 2026-06-23: reports show revenue, labor cost, expense/vendor cost, margin, WIP, utilization, project health, and capacity by several dimensions. Remaining work is launch-grade role workflow and tax/FX presentation depth.

### Phase 2: Build The Agent Operating Model

Goal: make “agentic ERP” auditable and controllable.

Work items:
- Done 2026-06-23: add `agent_runs`, `agent_tool_invocations`, `agent_workflow_runs`, and `agent_memory_items` or equivalent tables.
- Done 2026-06-23: create a tool registry with risk class: read-only, draft, write-low-risk, write-money-in, write-money-out, accounting.
- Done/monitor 2026-06-23: enforce tool authorization by agent, autonomy level, role, tenant, and risk class for registered tools.
- Done/verification open 2026-06-23: move Copilot write tools through the same tool policy/HITL/autonomy path; live LLM time logging remains tracked by issue #253.
- Done/partial 2026-06-23: store prompt version, model version, source-document hash, input hash, output hash, cost, trace ID, and replay pointer. Recorded replay is runnable from the agent-run dashboard; live replay against current code remains open.
- Done 2026-06-23: add agent run dashboard in Settings/Admin.
- Done 2026-06-23: add kill switch and per-agent/tool circuit breakers.
- Done 2026-06-23: make human corrections automatically candidates for eval cases.

Acceptance:
- Partial 2026-06-23: agent run/tool provenance exists. The "every agent-created mutation" bar remains open until coverage is verified across all agents and direct write paths.
- Done/partial 2026-06-23: a failed agent run can be replayed from recorded tool snapshots; deterministic re-execution against current code remains open.
- Done/monitor 2026-06-23: L3 promotion gates require eval pass metadata, approval history, admin opt-in, and tool-risk permission.

### Phase 3: Autonomous Workflow Loops

Goal: agents perform routine ERP work with humans handling exceptions.

Engagement-to-cash loops:
- Partial: engagement intake agent creates engagement/project drafts from documents; rate-card draft depth remains open.
- Open: time-entry agent drafts/reminds based on calendar/email/project context.
- Partial 2026-06-23: billing-run agent prepares invoices by schedule and billing terms.
- Partial: collections agent exists, but behavior-policy-driven reminder loops need demo-grade verification.
- Partial 2026-06-23: revenue/accrual agents can propose WIP accruals, deferred revenue releases, and milestone recognition journals from completed project phases; HITL approval posts through the manual journal/accounting guardian path. Retainer drawdown, percentage-of-completion, and prepaid amortization loops remain open.

Procure-to-pay loops:
- Done/monitor 2026-06-23: vendor invoice agent extracts, matches, detects duplicates, and suggests GL/service-line/project coding.
- Vendor onboarding agent validates tax IDs, bank details, and approvals.
- Done/partial 2026-06-23: AP payment agent proposes payment batches with money-out controls; cash/discount/risk optimization needs more depth.
- Done/monitor 2026-06-23: payment settlement lifecycle exists and posts only after settlement confirmation.

Record-to-report loops:
- Done/monitor 2026-06-23: close status/readiness/package endpoints and persisted close calendar/task workflow are implemented.
- Partial 2026-06-23: reconciliation service checks AR/AP/settlement evidence; full bank/suspense matching remains open.
- Partial 2026-06-23: accrual/revenue agents propose unbilled revenue and deferred revenue releases; missing-expense/prepaid coverage remains open.
- Partial 2026-06-23: reporting agent and close package exist; variance-commentary workflow remains open.
- Done/partial 2026-06-23: period lock includes readiness, pending-review, and close-task guards; autonomous scheduled close execution remains open.

Acceptance:
- Each loop has a happy path, low-confidence HITL path, provider failure path, period-locked path, and manual fallback path.
- Manual users can do every critical action without AI.

### Phase 4: Services-Business Intelligence

Goal: move beyond transaction automation into operating leverage.

Work items:
- Done 2026-06-23: project health score covers budget burn, margin erosion, WIP, cap/retainer drawdown, and scope signals; milestone-risk report now surfaces overdue and near-due delivery risk.
- Done 2026-06-23: scope-change advisor using historical comparables.
- Done 2026-06-23: pricing and staffing recommendation engine.
- Done 2026-06-23: client profitability and segment profitability dashboards.
- Done 2026-06-23: capacity planning and backlog forecast exist, including contract value, billed-to-date, unbilled WIP, delivery backlog, due-date risk, and recommended actions.
- Done 2026-06-23: partner/practice dashboards for accounting, tax, COSEC, payroll, advisory.
- Done 2026-06-23: multi-entity client group rollups.

Acceptance:
- Done/partial 2026-06-23: evidence-backed recommendations now feed role-specific action queues for partner, finance manager, project manager, and AP clerk personas. Deeper personal ownership, SLA, and assignment queues remain open.

### Phase 5: Compliance And Enterprise Readiness

Goal: make the product credible for real finance operations.

Work items:
- Done 2026-06-22: added `financial_events` as an immutable, hash-chained event log with database-trigger coverage for posted journals and period lock/unlock actions, plus read-only `/api/v1/financial-events` admin API.
- Done/monitor 2026-06-23: added authenticated anon/JWT Supabase client dependency and migrated `GET /api/v1/accounts`, `GET /api/v1/tax-rates`, read-only service catalogue routes, read-only client group routes, read-only client routes, read-only employee routes, read-only project and project-assignment routes, engagement list/detail/summary routes, read-only rate-card routes, expense list routes, time-entry list/detail routes, inbox list/detail routes, invoice list/detail routes, payments list route, bill list/detail/AP aging routes, billing-run list/detail routes, bill-payment batch list/detail routes, financial-event list/export routes, accounting period list, journal-entry list routes, accounting close status/readiness/package routes, FX-rate lookup routes, document metadata list routes, document signed-URL row authorization, chat thread list route, read-only reports routes, employee identity lookup, read-only timesheet portal routes, and agent dashboard read routes off service-role; accounts, tax-rate, service-catalogue, clients, client-group, employee, project, project-assignment, engagement, engagement-billing-terms, rate-card, rate-card-line, project-expense, time-entry, HITL-task, agent-suggestion, invoice, invoice-line, payment, bill, bill-line, billing-run, bill-payment-batch, bill-payment-item, financial-event, period-lock, journal-entry, journal-line, document, FX-rate, chat-thread, agent-autonomy-setting, agent-run, agent-tool-invocation, and agent-eval-candidate RLS now admit authenticated readers through existing tenant membership checks, owner checks, or global authenticated-read policy while preserving internal service-role/app-context write paths.
- Done 2026-06-22: added capped admin CSV export for `financial_events` so audit/review packages can include event evidence without direct database access.
- Done 2026-06-22: added shared document preflight scanning for PII and prompt-injection markers; text is masked before LLM calls, and PDF/image binaries with detectable sensitive or adversarial text are withheld from the external LLM and replaced with masked text-only context.
- Done 2026-06-22: added bill-payment export integrity metadata, actor/timestamp controls for approval/export/send/settlement, settled batch status, and financial event log coverage for payment-batch transitions.
- Done 2026-06-22: added a shared launch-market localization profile service/API for US, UK, SG, IN, and AU, covering country/market mapping, base currency, locale, timezone, tax labels, authorities, reporting periods, and default tax-rate templates; signup provisioning, signup country selection, billing currency mapping, and tax-rate market mapping now reuse it.
- Done 2026-06-22: added a shared integration catalog/API and Settings roadmap for email/calendar, bank feeds, government registry/tax validation, payroll, CRM, document storage, Stripe Connect, and transactional email, with explicit roadmap status, auth model, risk, markets, data classes, and capabilities.

Acceptance:
- Security review for agent tools, payments, RLS, webhooks, and document/LLM data handling.
- Cross-tenant tests and prompt-injection evals pass for every workflow.

## Recommended New Demo Scenarios

Add these as deterministic scenario docs and Playwright/API specs:

1. Zero-touch monthly retainer invoice.
   - L3 invoice drafter sends invoice without HITL.
   - Same scenario at L2 creates an Inbox task.

2. Capped T&M project near cap.
   - Time entries drive cap utilization.
   - Project health agent warns before overrun.

3. Vendor bill with vendor mismatch.
   - Agent extracts bill, detects low-confidence vendor match, requires human review, posts AP only after correction.

4. AP payment batch with money-out controls.
   - Batch proposal, approval, export, mark sent, settlement journal.
   - Above-threshold bill always requires explicit approval.

5. Month-end close.
   - Trial balance, accrual proposal, reconciliation, variance commentary, close package, period lock.

6. Multi-currency invoice and payment.
   - USD invoice in GBP base tenant, FX rate snapshot, payment at different rate, realized gain/loss.

7. Multi-entity family office client.
   - Parent group, child entities, separate engagements, consolidated profitability.

8. AI outage manual mode.
   - Disable LLM key or force agent failure.
   - User completes engagement, bill, invoice, and journal manually.

9. Prompt-injection document.
   - Uploaded invoice tells the agent to ignore controls.
   - Agent flags injection and forces HITL.

## Proposed Issue Backlog After Approval

Priority 0:
- Done 2026-06-23: fix Playwright auth/storage-state.
- Pending: execute `make demo-ready` against the launch demo tenant and refresh the evidence report.
- Done 2026-06-23: fix manual journal post regression.
- Done 2026-06-23: resolve invoice approval RBAC decision.
- Done 2026-06-23: add missing API contracts or remove UI paths.
- Done 2026-06-23: make service-catalogue tests idempotent.
- Done 2026-06-23: restore lint/property-test gate.

Priority 1:
- Done 2026-06-23: accounts and expenses APIs.
- Done 2026-06-23: tax-rates API/UI, invoice-side line tax/tax-payable journals, and bill-side input-tax-recoverable postings.
- Done/UX depth 2026-06-23: billing terms including per-unit payroll are implemented; employee/client-specific rate overrides and service-line-specific rate-card segmentation are honored in invoice drafting. Remaining price-book work is richer admin UX/reporting around segmented rate books.
- Done 2026-06-23: service catalogue end-to-end now includes invoice-line linkage and reporting evidence through service-line revenue reports.
- Done 2026-06-23: project milestones, deliverables, budget hours, and percent-complete tracking.
- Revenue recognition and tax journals.

Priority 2:
- Done 2026-06-23: agent run ledger and tool registry.
- Done/verification open 2026-06-23: unified HITL/autonomy enforcement for Copilot tools; verify live LLM `log_time_entry` in issue #253.
- Partial 2026-06-23: eval runner and correction-to-eval loop; correction candidates exist, runnable promotion gate still needs maturity.
- Done 2026-06-23: agent dashboard and kill switches.

Priority 3:
- P2P workflow depth: vendor onboarding, PO/service orders, bank-native validation, sanctions/tax controls, and payment optimization.
- R2R close management: close calendar/tasks, bank/suspense reconciliations, recurring journals, prepaid amortization, retained-earnings roll-forward, and statutory reporting packs.
- Advanced services intelligence: personalized assignment queues and demo-ready recommendation workflows.

## Approval Recommendation

Phase 0 is materially complete except for executing the demo-readiness target against a real launch tenant and refreshing demo evidence. The fastest path to launch is now:
- run `make demo-ready` for the launch demo tenant and refresh the evidence report;
- close the remaining FX/Stripe and live replay re-execution gaps;
- use the updated GitHub issue state to avoid duplicating completed Phase 0, Phase 2, and Phase 4 work.
