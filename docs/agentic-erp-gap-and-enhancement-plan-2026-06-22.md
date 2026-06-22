# Aethos PS Agentic ERP Gap and Enhancement Plan

Review date: 2026-06-22  
Repo: `aethos-ps`  
Mode: planning/review only; no application implementation changes in this pass.

## Executive Verdict

Aethos PS already has the shape of a professional-services ERP: tenant auth, contacts, employees, engagements, projects, time, invoices, bills, journals, reports, documents, HITL, and several agents are present. The strongest architectural choices are the tenant-scoped FastAPI/Supabase spine, the `agent_suggestions` + `hitl_tasks` review substrate, and the use of a canonical accounting guardian before journal posting.

The platform is not yet a reliable autonomous ERP. The current system behaves more like an AI-assisted PSA/ERP MVP with manual and semi-automated workflows. The main gap is not just missing screens; it is the missing agent operating model: durable workflow plans, per-tool authorization, agent run telemetry, eval-driven promotion, deterministic replay, and scheduled autonomous execution across engagement-to-cash, procure-to-pay, and record-to-report.

The immediate priority before new feature work is demo and contract stabilization. Today, the selected live API subset failed, and selected Playwright demo scenarios did not reproduce the 2026-06-21 demo pass report.

## Evidence Gathered

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

Live verification:
- Backend health on `127.0.0.1:8012`: `/health` returned ok.
- Backend readiness: DB reachable, queue reported `not_configured`.
- Backend unit tests: `448 passed`.
- Backend property suite: not runnable because local venv is missing `hypothesis`.
- Backend lint: `ruff check backend/app backend/tests` failed with 61 lint issues.
- Live API subset: `53 passed, 5 failed, 5 errors`.
- Selected Playwright suite: 1 setup test passed, 14 scenario tests failed.
- Angular dev server compiled, but reported Angular template warnings and Sass deprecation warnings.
- Local Node is `24.14.0`, which Angular 19 reports as unsupported.

Key live API failures:
- `test_manager_cannot_approve_invoice_admin_can`: manager can approve invoice, but test expects admin-only.
- Manual journal post tests return 500.
- `test_service_catalogue.py` setup collides with existing cloud data due duplicate account code `4000`.

Key E2E failures:
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

Gaps:
- Billing terms and rate-card UX are incomplete or workaround-driven.
- Tax calculation is not wired end to end; invoice creation currently does not materially apply tax rates.
- Revenue recognition is simple invoice posting, not full deferred revenue, WIP accrual, milestone, retainer drawdown, or percentage-of-completion accounting.
- No robust client group / multi-entity model for family office and portfolio-client scenarios.
- No client portal workflow beyond public invoice payment.
- Copilot can perform some writes without consistently using the same HITL/autonomy policy used by document agents.
- Time logging via live LLM is still open for verification.

### Procure To Pay

Present:
- Vendor contact kind.
- Vendor invoice extraction agent with duplicate checks, vendor matching, tax ID warnings, and GL suggestions.
- Bills and bill lines.
- Bill approval posts AP journal through the accounting guardian.
- AP aging.
- Bill payment batches, approval, export, and mark-sent.
- Bill-pay agent that proposes batches as HITL.

Gaps:
- No purchase requests, purchase orders, service orders, or PO matching.
- Vendor onboarding lacks bank-account verification, sanctions/tax validation, remittance controls, and approval workflow.
- Bill approval posts to a generic expense account path too often; line-level GL from the extraction suggestion is not yet strong enough as a closed loop.
- Payment export is a placeholder; NACHA/CSV needs bank-specific validation, controls, and audit.
- `mark-sent` does not complete a settlement/accounting lifecycle.
- Money-out controls should remain stricter than money-in controls.

### Record To Report

Present:
- Chart of accounts schema.
- Journal entries and journal lines.
- Period locks.
- Accounting guardian validates journal balance, period lock, and accounts.
- Trial balance, aging, utilization, WIP, project P&L, revenue and service-line reports.
- Manual journal UI exists.
- R2R close PRD exists: `docs/prd/r2r-financial-close-v1.1.md`.

Gaps:
- Manual journal post currently returns 500 in live API due a stale `reference` column update against a schema that uses `reference_id`.
- No balance sheet, income statement, cash flow, retained earnings roll-forward, or statutory reporting pack.
- No close calendar, close tasks, reconciliations, variance explanations, or evidence package implemented.
- No automated accruals, prepaid amortization, deferred revenue release, or recurring journals.
- FX is partially implemented but not consistently surfaced in reports as transaction currency plus base currency.
- Period close is not yet a guided autonomous workflow.

### Agent Platform

Present:
- Agents: engagement letter, expense extractor, vendor invoice, invoice drafter, reporting, project health, collections, bill pay, intelligence, Copilot, accounting guardian.
- `agent_suggestions`, `hitl_tasks`, and `agent_corrections`.
- Autonomy settings and autonomy promoter worker.
- Agent eval pack files exist in `docs/test/agent_evals`.
- PII masking helper exists and text prompts use it in several agents.

Gaps:
- No complete agent run ledger: `agent_runs`, `tool_invocations`, input hashes, output hashes, model/prompt versions, token/cost, status, and replay IDs.
- No single tool registry with per-agent capability scopes and per-tool risk class.
- No durable workflow engine for long-running business goals.
- Queue is `not_configured` in the live readiness check, so scheduled autonomy is not operational in this local/live run.
- Binary PDF/image content is sent to LLMs without the same PII masking guarantee as decoded text.
- Agent evals are documented, but the runnable eval gate and drift dashboard are not mature.
- Copilot can hang the UI in a disabled-running state.

### Frontend And Contract Surface

Present:
- App shell with feature routes for Copilot, inbox, clients, engagements, projects, invoices, bills, billing runs/pay bills, reports, accounting, documents, settings, people, time, expenses.
- Manual backup surfaces exist for several workflows.
- Settings include autonomy, tax rates, services, and Stripe Connect.

Contract gaps found:
- UI calls `/api/v1/accounts`; router does not register an accounts endpoint.
- UI calls `/api/v1/tax-rates`; router does not register a tax-rates endpoint.
- UI calls `/api/v1/expenses`; router does not register an expenses endpoint.
- UI calls `/api/v1/invoices/draft`; backend draft invoice route is engagement-scoped, not this path.
- Bill detail calls `POST /api/v1/bills/{id}/void`; backend route is missing.
- `environment.ts` hardcodes an external API URL for signup/billing while most app code uses relative `/api`, which hurts local/proxy consistency.
- Playwright storage state is brittle and can silently redirect protected-route specs to the landing page.

## Critical Blockers Before Feature Expansion

1. Stabilize auth/test-state for Playwright.
   - Make global setup produce a valid reusable storage state or require login once per run.
   - Fail fast if a protected-route spec lands on the landing page.
   - Align all specs with `AETHOS_PS_WEB_URL` and `AETHOS_PS_API_URL`; remove hardcoded `localhost:8011`.

2. Fix live API regressions.
   - Manual journal 500: stop writing `journal_entries.reference`, or add the intended schema column with migration and model updates.
   - Invoice approval RBAC: decide whether managers may approve invoices. Code and tests disagree.
   - Service catalogue tests: isolate tenant/account fixtures or use idempotent upserts with cleanup.

3. Close frontend/backend contract gaps.
   - Add or remove `/accounts`, `/tax-rates`, `/expenses`, `/invoices/draft`, `/bills/{id}/void`.
   - Prefer API routes that match existing UI expectations only when the product contract makes sense.

4. Make the demo reproducible.
   - Seed a deterministic Meridian tenant.
   - Run the demo from a clean auth state.
   - Capture screenshots and trace IDs.
   - Update `docs/demo-v2-test-report.md` only after a fresh passing run.

5. Restore quality gates.
   - Fix `ruff`.
   - Install or sync dev deps so property tests run.
   - Pin supported Node for Angular 19.
   - Make `/health/ready` queue status green when workers are required for the demo.

## Enhancement Plan

### Phase 0: Demo And Quality Stabilization

Goal: make the existing platform trustworthy enough to demo and build on.

Work items:
- Repair Playwright auth and selected E2E suites.
- Fix manual journal, invoice RBAC, and service-catalogue fixture isolation.
- Implement or remove broken UI contracts.
- Normalize frontend environment configuration.
- Fix lint and dev dependency drift.
- Make `seed_demo.py --reset` idempotent against Supabase cloud data.
- Add a “demo readiness” command that starts backend/frontend, seeds tenant, runs smoke API, then runs selected E2E specs.

Acceptance:
- Backend unit + property tests pass.
- Focused live API suite passes.
- Selected Meridian demo suite passes from clean state.
- `ruff check backend/app backend/tests` passes.
- Demo report regenerated with current date and evidence.

### Phase 1: Complete The Professional-Services ERP Spine

Goal: close baseline PSA/ERP gaps versus NetSuite and Dynamics Project Operations.

Work items:
- Accounts API and account picker across accounting/service catalogue/bills.
- Tax-rates API, tax defaults, line tax, invoice/bill journal tax postings.
- Expenses API and UI completion.
- Billing terms UI: fixed, T&M, capped T&M, retainer, milestone, per-unit payroll.
- Rate card UI and role/employee/service-line rates.
- Service catalogue integration across engagements, invoice lines, reports, and settings.
- Client groups and legal entities for portfolio/family-office clients.
- Project milestones, deliverables, budgets, and percent-complete.
- Resource profile: role, cost rate, skills, availability, capacity, utilization target.

Acceptance:
- Engagement-to-cash scenario covers fixed, T&M, retainer, milestone, capped T&M, and multi-currency.
- Reports show revenue, labor cost, vendor cost, margin, WIP, and utilization by client, engagement, project, service line, and employee.

### Phase 2: Build The Agent Operating Model

Goal: make “agentic ERP” auditable and controllable.

Work items:
- Add `agent_runs`, `agent_tool_invocations`, `agent_workflow_runs`, and `agent_memory_items` or equivalent tables.
- Create a tool registry with risk class: read-only, draft, write-low-risk, write-money-in, write-money-out, accounting.
- Enforce tool authorization by agent, autonomy level, role, tenant, and risk class.
- Move Copilot write tools through the same HITL/autonomy path as document agents.
- Store prompt version, model version, source-document hash, input hash, output hash, cost, trace ID, and replay pointer.
- Add agent run dashboard in Settings or Admin.
- Add kill switch and per-agent/tool circuit breakers.
- Make human corrections automatically candidates for eval cases.

Acceptance:
- Every agent-created mutation is traceable from source input to tool call to DB write to HITL decision.
- A failed agent run can be replayed deterministically against current code.
- L3 promotion cannot happen without eval pass, approval history, admin opt-in, and tool-risk permission.

### Phase 3: Autonomous Workflow Loops

Goal: agents perform routine ERP work with humans handling exceptions.

Engagement-to-cash loops:
- Engagement intake agent creates engagement/project/rate-card drafts from documents.
- Time-entry agent drafts and reminds based on calendar/email/project context.
- Billing-run agent prepares invoices by schedule and billing terms.
- Collections agent sends reminders based on client payment behavior and policy.
- Revenue agent posts deferred revenue release, WIP accruals, and milestone recognition.

Procure-to-pay loops:
- Vendor invoice agent extracts, matches, detects duplicates, and suggests GL/service-line/project coding.
- Vendor onboarding agent validates tax IDs, bank details, and approvals.
- AP payment agent proposes payment batches by due date, discount, cash, and risk.
- Payment settlement agent posts journals only after bank/payment confirmation.

Record-to-report loops:
- Close agent builds close calendar and status.
- Reconciliation agent matches bank, AR, AP, and suspense accounts.
- Accrual agent proposes missing expenses, unbilled revenue, and deferred revenue releases.
- Reporting agent prepares variance commentary and close package.
- Period-lock agent locks only after reconciliations and review are complete.

Acceptance:
- Each loop has a happy path, low-confidence HITL path, provider failure path, period-locked path, and manual fallback path.
- Manual users can do every critical action without AI.

### Phase 4: Services-Business Intelligence

Goal: move beyond transaction automation into operating leverage.

Work items:
- Project health score: budget burn, margin erosion, utilization, unbilled WIP, cap/retainer drawdown, overdue milestones.
- Scope-change advisor using historical comparables.
- Pricing and staffing recommendation engine.
- Client profitability and segment profitability dashboards.
- Capacity planning and backlog forecast.
- Partner/practice dashboards for accounting, tax, COSEC, payroll, advisory.
- Multi-entity client group rollups.

Acceptance:
- The system can answer “what should I do today?” for partner, finance manager, project manager, and AP clerk with evidence-backed recommendations.

### Phase 5: Compliance And Enterprise Readiness

Goal: make the product credible for real finance operations.

Work items:
- Done 2026-06-22: added `financial_events` as an immutable, hash-chained event log with database-trigger coverage for posted journals and period lock/unlock actions, plus read-only `/api/v1/financial-events` admin API.
- In progress 2026-06-22: added authenticated anon/JWT Supabase client dependency and migrated `GET /api/v1/accounts`, `GET /api/v1/tax-rates`, read-only service catalogue routes, read-only client group routes, read-only client routes, read-only employee routes, read-only project and project-assignment routes, engagement list/detail/summary routes, read-only rate-card routes, expense list routes, time-entry list/detail routes, inbox list/detail routes, invoice list/detail routes, payments list route, bill list/detail/AP aging routes, billing-run list/detail routes, bill-payment batch list/detail routes, financial-event list/export routes, accounting period list, journal-entry list routes, FX-rate lookup routes, document metadata list routes, chat thread list route, read-only reports routes, employee identity lookup, read-only timesheet portal routes, and agent dashboard read routes off service-role; accounts, tax-rate, service-catalogue, clients, client-group, employee, project, project-assignment, engagement, engagement-billing-terms, rate-card, rate-card-line, project-expense, time-entry, HITL-task, agent-suggestion, invoice, invoice-line, payment, bill, bill-line, billing-run, bill-payment-batch, bill-payment-item, financial-event, period-lock, journal-entry, journal-line, document, FX-rate, chat-thread, agent-autonomy-setting, agent-run, agent-tool-invocation, and agent-eval-candidate RLS now admit authenticated readers through existing tenant membership checks, owner checks, or global authenticated-read policy while preserving internal service-role/app-context write paths.
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
- Fix Playwright auth/storage-state and demo reproducibility.
- Fix manual journal post regression.
- Resolve invoice approval RBAC decision.
- Add missing API contracts or remove UI paths.
- Make service-catalogue tests idempotent.
- Restore lint/property-test gate.

Priority 1:
- Accounts, tax-rates, and expenses APIs.
- Billing terms + rate card UI.
- Service catalogue end-to-end.
- Project milestones/deliverables/budgets.
- Revenue recognition and tax journals.

Priority 2:
- Agent run ledger and tool registry.
- Unified HITL/autonomy enforcement for Copilot tools.
- Eval runner and correction-to-eval loop.
- Agent dashboard and kill switches.

Priority 3:
- P2P workflow depth: vendor onboarding, PO/service orders, bank validation, settlement.
- R2R close management: reconciliations, accruals, financial statements.
- Advanced project health and scope-change intelligence.

## Approval Recommendation

Do not start broad feature implementation until Phase 0 is complete. The fastest path to an agentic ERP is to first make today’s workflow evidence reliable. Once the demo/test spine is stable, build the agent control plane and workflow loops in parallel with the PSA accounting depth.
