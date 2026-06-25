# Aethos PS Platform User Guide

This guide explains how a professional services firm uses Aethos PS as an
agent-first ERP. It is a living document: every enterprise-readiness slice must
update the relevant workflow, control, and testing notes.

Related docs:

- Copilot prompts: [`docs/copilot/prompt-library.md`](../copilot/prompt-library.md)
- Launch QA runbook: [`docs/qa/launch-e2e-scenario-runbook-2026-06-24.md`](../qa/launch-e2e-scenario-runbook-2026-06-24.md)
- Enterprise E2E scenarios: [`docs/qa/enterprise-e2e-scenario-library.md`](../qa/enterprise-e2e-scenario-library.md)
- Engagement to Cash test guide: [`docs/test/e2e_engagement_to_cash.md`](../test/e2e_engagement_to_cash.md)
- Procure to Pay test guide: [`docs/test/e2e_procure_to_pay.md`](../test/e2e_procure_to_pay.md)
- Record to Report test guide: [`docs/test/e2e_record_to_report.md`](../test/e2e_record_to_report.md)
- Ops/Security test guide: [`docs/test/e2e_ops_security.md`](../test/e2e_ops_security.md)
- P2P PRD: [`docs/prd/advanced-p2p-v1.1.md`](../prd/advanced-p2p-v1.1.md)
- R2R PRD: [`docs/prd/r2r-financial-close-v1.1.md`](../prd/r2r-financial-close-v1.1.md)

## 1. Operating Model

Aethos PS is built around four surfaces:

| Surface | What users do there | Enterprise control point |
| --- | --- | --- |
| Copilot | Ask AI to analyze, draft, upload, prepare, and coordinate finance work | AI tools are policy-classified; sensitive work routes to Inbox |
| Inbox | Review, approve, edit, reject, and route AI or workflow recommendations | Human-in-the-loop approval for money, accounting, external sends, and governance |
| ERP modules | Manage clients, vendors, engagements, projects, time, invoices, bills, journals, documents, and reports | Business records remain source-of-truth after approval |
| Settings and telemetry | Configure firm data, tax rates, agent controls, run ledger, and workflow status | Admins inspect autonomy, agent activity, and operational evidence |

The intended user experience is one AI Finance Ops Manager coordinating work
across specialist workflows. Users should not need internal tool names. They
state the business outcome, review the proposed action when required, and rely
on the audit trail to explain what happened.

### Agent-first workflow loop

Aethos PS should feel like an AI-run finance department with human control
points. Most workflows follow the same loop:

1. Ask Copilot for a business outcome, such as draft invoices, review vendor
   invoices, prepare bill pay, prepare close, or explain operational blockers.
2. Copilot performs read-only analysis directly where safe.
3. Any sensitive write, money movement, accounting, external-send, or settings
   change becomes an Inbox review task.
4. The reviewer approves, edits, or rejects the task according to the approval
   policy and role mapping.
5. Approved work materializes into the ERP module of record.
6. Reports, operational health, run ledgers, and financial-event timelines give
   audit evidence for what happened.

This means users can ask for outcomes without naming tools. Tool names are an
engineering and QA fixture only; business users should describe the finance
result and the approval boundary.

### Module quick map

| Module | Route | Primary users | How AI should help | Scenario anchors |
| --- | --- | --- | --- | --- |
| Copilot | `/app/copilot` | All finance users | Analyze, draft, upload, prepare, and explain work in business language | ENT-AIOPS-001, ENT-P2P-001, ENT-R2R-001 |
| Inbox | `/app/inbox` | Managers, AP/AR leads, Controller, Owner/Admin | Review AI proposals, approve with edits, reject, dispatch plan items, inspect decision history | ENT-CTRL-001, ENT-AUD-001, ENT-AUD-002 |
| Clients and vendors | `/app/clients` | Engagement managers, AP/AR leads | Create and inspect customers/vendors, link AR/AP history, support document intake | Launch scenarios 1-7 |
| People | `/app/people` | Admins, managers | Maintain staff, rates, targets, and delivery context for billing/reporting | Launch scenarios 1-4, 10 |
| Engagements and projects | `/app/engagements`, `/app/projects` | Engagement managers, project managers | Set billing terms, organize delivery, connect WIP to invoices and project health | Launch scenarios 1-4 |
| Invoices and public invoice | `/app/invoices`, `/p/:token` | AR lead, Controller, client recipient | Draft/review invoices, send/collect, inspect public invoice status | Engagement to Cash guide |
| Bills and pay bills | `/app/bills`, `/app/billing-runs` | AP lead, Controller, Owner/Admin | Review vendor invoice exceptions, create bills, prepare, approve, export, send, and settle guarded payment batches | ENT-P2P-001, ENT-P2P-002, ENT-P2P-003, ENT-P2P-005 |
| Accounting and close | `/app/accounting/journals` | Controller, Owner/Admin | Prepare close, review blockers, record overrides, generate statements | ENT-R2R-001, ENT-R2R-002, ENT-R2R-003 |
| Reports | `/app/reports` | Executives, managers, auditors | Explain AR/AP/WIP/revenue/project/accounting results and tie AI recommendations to source reports | Launch scenario 10 |
| Documents | `/app/documents` | AP, AR, engagement teams, auditors | Track uploaded source documents, extraction status, and resulting decisions | ENT-P2P-001, ENT-AUD-003 |
| Settings | `/app/settings` | Admins, Owner, operators, auditors where read-only | Configure services, tax, autonomy, approval policy, personas, schedules, and inspect health/run ledgers | ENT-AIOPS-003, ENT-CTRL-003, ENT-RBAC-002, ENT-OPS-003 |

## 2. Roles And Responsibilities

Current implementation uses the tenant role hierarchy
`owner > admin > manager > member > viewer > employee`. Enterprise finance
personas map onto that hierarchy for now; finer-grained named roles can be added
later without weakening the existing approval gates.

| Enterprise persona | Current role mapping | What they can do today | Current restrictions |
| --- | --- | --- | --- |
| Owner/Admin | `owner`, `admin` | Configure tenant and AI operations, inspect all finance records, and approve owner/admin-threshold Inbox work | Tenant-scoped only |
| Controller | `admin`, `owner` | Own close, journals, statements, accounting approvals, reports, and decision evidence | Cannot bypass owner-threshold policy or tenant boundaries |
| AP Lead | `manager`, `admin`, `owner` | Create/review bills and procurement documents, resolve vendor invoice exceptions, and prepare bill-pay batches | Cannot approve admin/owner-threshold money-out work unless mapped to admin/owner |
| AR Lead | `manager`, `admin`, `owner` | Draft/review invoices, collections work, WIP, revenue, and AR Aging | Cannot bypass send, payment, or admin-threshold approval gates unless mapped to admin/owner |
| Engagement Manager | `manager` | Maintain customers, engagements, projects, services, WIP, draft invoices, and team workflow | Cannot bypass admin approval for posting/sending/payment |
| Staff / Consultant | `member` or Timesheet `employee` | Participate in delivery workflows such as time/expense where exposed | Cannot approve finance, accounting, payment, settings, or agent-control actions |
| Auditor | `viewer` | Inspect permitted tenant records, reports, Inbox history, AP/AR records, and record-scoped decision evidence | Cannot create, approve, edit, reject, convert, post, pay, send, lock, change settings, or export admin-only audit events |
| Executive | `viewer` | Read dashboards, management reports, operational status, and AI Finance Ops Manager summaries | Same read-only mutation restrictions as auditor |

The Bills/AP UI now disables read-only users from creating bills or procurement
documents, approving procurement, converting purchase requests, or opening Pay
Bills from the Bills page. Backend RBAC remains authoritative and returns 403
for direct read-only mutation attempts.

Settings -> Approval Controls -> Finance role personas shows the live
product-facing persona catalog from `GET /api/v1/tenants/finance-personas`.
The card is readable by viewer users, highlights which personas match the
current enforced tenant role, and explains the actions that remain restricted.
This is a compatibility layer over the current role enum; dedicated finance-role
enum expansion remains future depth.

### Current approval policy matrix

The first enterprise controls slice adds a seeded approval matrix for Inbox
approvals:

| Task risk | Required approver |
| --- | --- |
| Draft or low-risk write | Manager or higher |
| Money-in action | Manager or higher |
| Money-out action | Admin or higher |
| Money-out action at or above 50,000 in task currency | Owner |
| Accounting action | Admin or higher |

Inbox shows the required approval role on review cards and lets users filter by
required role. The API enforces the same policy at approval time, including
approve-with-edits, so a corrected payload cannot bypass a higher approval
threshold.

## 3. Copilot And AI Finance Ops Manager

Use Copilot for chat-first finance operations:

- Upload engagement letters, SOWs, vendor invoices, receipts, and supporting documents.
- Ask for daily finance checks across AR, AP, WIP, close, approvals, and agent runs.
- Ask for reviewed work plans that route sensitive tasks to Inbox.
- Draft invoices, collections reminders, bill-pay proposals, month-end/year-end
  close preparation, and financial statement packages.

Good prompts include the business period, customer/vendor/engagement name,
desired outcome, and approval boundary. See the prompt library for examples.

Recommended prompt pattern:

1. State the finance outcome: "prepare June bill pay" or "draft invoices for
   approved June WIP."
2. Name the scope: period, customer, vendor, engagement, project, or report.
3. State the safety boundary: "route to Inbox before paying, sending, posting,
   locking, or changing settings."
4. Ask for evidence: "show source records, blockers, and why each action is
   safe or needs review."

Users do not need to specify tool names in chat. Copilot should infer the
correct internal capability from the business request. QA specs may still pin a
tool name when they need deterministic run-ledger assertions.

### Current AI approval boundary

| AI activity | Current behavior |
| --- | --- |
| Read-only analysis | Can run directly and records tool activity |
| Draft invoice | Routes to Inbox, then materializes as draft invoice after approval |
| Collections reminders | Creates Inbox email-review tasks; approval is required before send path |
| Bill-pay proposal | Routes to Inbox, then creates a draft payment batch after approval |
| Month-end close preparation | Routes to Inbox, then creates close tasks after approval |
| Finance ops action plan | Routes manager plan to Inbox; approval creates Plan Items; Plan Item approval dispatches specialist workflows |
| Scheduled Finance Ops Manager | Runs on configured tenant cadence, creates a reviewed action-plan Inbox task, and creates separate escalation notices for stale/high-risk Inbox work |
| Financial statement package | Generates read-only summary from report/journal data |
| Vendor invoice upload | Extracts to Inbox review, then creates bill after approval |
| Engagement-letter upload | Extracts to Inbox review, then creates client, engagement, first project, and reviewed rate card after approval |

### Scheduled Finance Ops Manager

Admins can configure the scheduled AI Finance Ops Manager through the Agents
API at `/api/v1/agents/finance-ops/schedule`. Tenants without an explicit row
use a seeded default: daily at 07:00 UTC, current-month review, 10-row lookback,
24-hour stale threshold, 4-hour high-risk threshold, and escalation enabled.

The scheduled worker runs hourly and only acts when the tenant cadence is due.
For each due tenant it:

1. runs the same read-only command-center analysis used by Copilot;
2. creates one `copilot_create_finance_ops_action_plan` Inbox task for manager review;
3. suppresses duplicate open scheduled plans for the same tenant/cadence window;
4. creates non-destructive `finance_ops_escalation` Inbox notices for stale or high-risk tasks; and
5. records a `scheduled_finance_ops_manager` workflow run visible in Settings telemetry.

Approval boundary: approving the scheduled action plan only fans out reviewed
Plan Items. Approving an escalation notice acknowledges the escalation; the
source Inbox task still requires its own approval, rejection, or correction.

Browser proof command: `cd frontend && npx playwright test e2e/enterprise-scheduled-finance-ops.spec.ts --project=chromium`

### Recommended daily operating rhythm

| Time | User | Action | Evidence to inspect |
| --- | --- | --- | --- |
| Morning | Owner/Admin or Controller | Ask Copilot for the daily finance ops check or inspect the scheduled Finance Ops Manager output | Inbox action plan, Settings workflow runs, agent run ledger |
| Midday | AP/AR leads | Review vendor invoice exceptions, collections reminders, bill-pay proposals, and draft invoices | Inbox required-role chips, AP/AR records, decision history |
| Afternoon | Engagement managers | Review WIP, project health, utilization, and billing recommendations | Reports, engagement/project detail, draft invoice tasks |
| Close cycle | Controller | Prepare close, review blockers, record permitted overrides, and generate statement commentary | Close package, journals, financial statements, audit timeline |
| Weekly | Owner/Admin | Review approval policy, finance personas, operational health, rate limits, and alert routing | Settings approval controls, Operational Health, run ledger |

## 4. Inbox

Inbox is the control center for human review.

Users should use Inbox when:

- AI proposes a draft invoice, bill, journal, payment batch, email, or action plan.
- A document extraction has enough structure to review but should not directly create records.
- A workflow needs approval, rejection, or correction.
- A finance-ops Plan Item should be dispatched to its specialist workflow.

Common Inbox actions:

| Action | Meaning |
| --- | --- |
| Approve | Accept the proposed payload and materialize the next safe step |
| Approve with edits | Correct the payload before materialization |
| Reject | Stop the recommendation and record feedback |
| Filter by task type | Focus on invoices, payments, emails, documents, close, or Plan Items |
| Filter by required role | Focus on tasks needing Owner, Admin, or Manager approval |
| Filter by status | Review Open work or inspect Done/All tasks with decision history |

Inbox decision history now uses the immutable `financial_events` ledger for
approval, approve-with-edits, rejection, and approval-denial events. Done and
All status views show the recent decision timeline on task cards, including the
actor role, action, timestamp, source suggestion link, policy metadata, safe
before/after payload summaries, payload hashes, and materialized entity
references where available.

When an Inbox decision materializes a business record, the same immutable
decision is projected onto that record. Bill, invoice, engagement, payment
batch, journal, close-period, and source-document surfaces can show a
record-scoped decision timeline with the actor role, decision type, timestamp,
related Inbox task, safe before/after review summary, and event hash.
Viewer/auditor personas can inspect this record-scoped metadata without gaining
mutation access.

Admins can also inspect or export the full financial event ledger through the
`/api/v1/financial-events` API. This is useful for audit sampling and for
cross-checking task decisions against posted journal, period-lock, and
bill-payment lifecycle events that are already database-triggered.

## 5. Order To Cash

Order to Cash covers customer setup through cash receipt.

Typical workflow:

1. Create or import a client.
2. Create an engagement with billing terms: time and materials, fixed fee, milestone, retainer, capped, or mixed.
3. Create projects and assign work.
4. Log time and billable expenses manually or through Copilot.
5. Ask Copilot to draft an invoice or use the invoice UI.
6. Review AI-created invoice drafts in Inbox.
7. Approve, send, and collect payment through the normal invoice lifecycle.
8. Review AR Aging, WIP, revenue, project P&L, and financial statements.

Current safeguards:

- Drafting and approval are separate.
- Invoice approval and send/payment remain explicit lifecycle steps.
- Journal posting is guarded by accounting validation.
- Reports should tie back to posted business records.

Scenario anchors: launch scenarios 1-4, `docs/test/e2e_engagement_to_cash.md`,
ENT-CTRL-001, ENT-AUD-003, and #309 for automated control/audit/RBAC proof.

## 6. Procure To Pay

Procure to Pay covers vendors, bills, approvals, and payment batches.

Typical workflow:

1. Create or import a vendor.
2. Upload a vendor invoice through Copilot or create a bill manually.
3. Review extracted vendor, invoice number, lines, tax, project/account coding, and source document.
4. Approve the bill when ready.
5. Ask Copilot to prepare a bill-pay run or use the Pay Bills UI.
6. Review and approve the proposed payment batch.
7. Export the approved batch, mark it sent to bank, and confirm settlement.
8. Review AP Aging and Cash Flow impact.

Current implementation supports vendor invoice upload, AI-assisted exception
evidence, bill creation after Inbox approval, bill-pay proposals, and
payment-batch UI visibility. Pay Bills now carries the batch through explicit
approval, CSV/NACHA export state, sent-to-bank state, and settlement
confirmation with returned journal evidence.

Vendor invoice review now carries AI evidence into Inbox:

- vendor match status and matched vendor candidate;
- GL/account coding suggestions per invoice line;
- duplicate, anomaly, tax-id, prompt-injection, vendor-match, and coding review exceptions;
- source document linkage; and
- project/customer hints for project-cost attribution; and
- reviewed evidence persisted on the created bill and visible from Bill detail.

Duplicate invoice drafts cannot be approved as-is. A reviewer must use
approve-with-edits and add a duplicate review reason before the bill can be
materialized. Inbox exposes that reason field for vendor invoice duplicates and
blocks one-click approval until a reviewer explains why the duplicate should be
accepted. Approved vendor invoice drafts now create bill lines through the same
Bills service path used by manual bill creation, so account coding and PO match
validation are preserved. Linked bills also record line-level PO/service-order
match evidence: matched lines and exceptions are stored in `po_match_summary`
and shown from Bills list/detail. Quantity, unit-price, unmatched-line, and
service-period exceptions keep the bill in draft and block approval until the
linked order or bill evidence is corrected.

Invoice intake/coding approval and payment approval are separate guarded steps:
approving the vendor invoice creates the reviewed bill, while payment still
requires a bill-pay proposal and payment-batch approval. Payment file export,
bank-send acknowledgement, and settlement confirmation remain explicit operator
steps. Remaining enterprise P2P depth is planned under later advanced P2P work:
AI semantic PO selection from source documents, recurring bills, and native
bank-provider submission. Browser automation for the AP exception-review path
and separate bill-pay proposal review is implemented under #310; line-level
PO/SO match evidence is covered under #323; bill-pay lifecycle proof is covered
under #325.

Scenario anchors: launch scenarios 5-7 and 9,
`docs/test/e2e_procure_to_pay.md`, ENT-P2P-001, ENT-P2P-002, ENT-P2P-003,
ENT-P2P-004, ENT-P2P-005, #310 for automated AI finance workflow proof, #323
for line-level PO/SO match proof, and #325 for bill-pay lifecycle proof.

## 7. Record To Report

Record to Report covers accounting journals, close, and reporting.

Current workflows:

- Invoice and bill approvals post balanced journals through guarded paths.
- Manual journals can be created from the Accounting area. Each manual journal
  requires a business reason, stores that reason on the journal entry, and
  appends immutable `manual_journal.posted` evidence for audit review. Journals
  whose total debits meet or exceed the tenant manual-journal approval threshold
  route to Inbox, append `manual_journal.submitted_for_approval`, and post only
  after approval by a different user with the required Accounting role. If the
  submitter attempts to approve their own threshold journal, the task stays open
  and `manual_journal.approval_denied` evidence records the denial. If the Inbox
  task is rejected, the rejection reason is captured in `manual_journal.rejected`
  evidence without posting a journal. Posted manual journals can be reversed
  through Accounting by entering a reversal date and reason; the system creates
  a new reversal journal rather than editing history. For multi-currency manual
  journals, transaction amounts keep their entered currency while base amounts
  are converted to the tenant base currency at the posting-date FX rate before
  financial statements read the journal.
- Month-end close preparation can be requested through Copilot and routed to Inbox.
- Admin/Owner users can post year-end close from Accounting. The system closes
  posted revenue and expense balances to seeded account `3000 Retained
  Earnings` through a balanced `year_end_close` journal and blocks duplicate or
  locked-year attempts.
- Copilot can prepare year-end close through Inbox. The review task includes
  retained-earnings posting preview, readiness blockers, P&L activity, and
  current-vs-prior year statement commentary; approval posts through the same
  year-end close service used by Accounting.
- Reports include operational and accounting views such as AR Aging, AP Aging, Project P&L, Utilization, WIP, Revenue, Trial Balance, Balance Sheet, Income Statement, Cash Flow, and Statutory Pack where supported by the current build.
- Copilot can generate a financial statement package summary from report data,
  close readiness, management commentary, and current-vs-comparison period
  variance commentary. If the user does not name a comparison period, Copilot
  compares against the immediately preceding period window.

Close evidence now includes:

- AR, AP, WIP, GL, and approval readiness evidence from real records.
- Subledger, trial-balance, unposted-journal, close-review, and close-task lock blockers.
- Supporting record references where the system can identify the source row.
- Recorded close overrides with blocker code, reason, actor, role, timestamp,
  and blocker evidence.

Period lock remains blocked while required gates fail unless the matching close
override has been recorded. Overrides require a reason of at least 10 characters
and are included in the close package for controller/CPA review. Copilot close
preparation surfaces blocker counts, override counts, and readiness evidence
before creating close tasks through Inbox.
The Accounting close package panel also lets Admin/Owner users record named
override reasons for supported blockers and immediately shows those overrides
in the period evidence.

Remaining enterprise R2R depth after the #285/#300 first slices, #310 browser
proof, #327 year-end close posting, #329 AI-routed year-end approval, #331
comparative statement packages, #333 manual-journal audit evidence, #335
manual-journal threshold approval, and #337 manual-journal reversal:

- Richer workpaper orchestration.

Scenario anchors: launch scenarios 8-10,
`docs/test/e2e_record_to_report.md`, ENT-R2R-001, ENT-R2R-002, ENT-R2R-003,
ENT-R2R-004, ENT-R2R-005, #310 for automated AI finance workflow proof, #327
for year-end retained-earnings posting proof, and #329 for AI-routed year-end
close approval proof.

## 8. Documents

Documents are part of the audit trail for AI-assisted work.

Users can:

- Upload documents through Copilot.
- Track extraction status from document cards.
- Review extracted payloads in Inbox.
- Preserve source-document linkage into materialized bills or engagements where supported.

Recommended practice:

- Treat extracted values as proposals, not facts, until reviewed.
- Use approve-with-edits when document data is structurally correct but needs correction.
- Keep source documents attached for audit evidence.
- Ask Copilot to summarize document evidence, but approve the reviewed business
  record from Inbox before relying on it in AP, AR, engagement, or close flows.

Scenario anchors: ENT-P2P-001, ENT-P2P-003, ENT-AUD-002, ENT-AUD-003, and the
document rows in the launch runbook coverage matrix.

## 9. Reports And Management Cockpit

Reports help owners and controllers inspect operations and financial outcomes.

Core report families:

| Area | Examples |
| --- | --- |
| AR | AR Aging, revenue by engagement, invoices |
| AP | AP Aging, bills, payment batches |
| Delivery | Project P&L, utilization, WIP |
| Accounting | Trial Balance, Balance Sheet, Income Statement, Cash Flow, Statutory Pack |
| Operations | Action Queue, agent run ledger, workflow run visibility |

Users should cross-check AI summaries against report tabs when reviewing close,
payment, or statement packages. AI should explain numbers sourced from tools and
reports, not invent finance totals.

Recommended report review prompts:

- "Explain why AR Aging changed since last week and link the invoices driving
  the change."
- "Compare AP Aging to the proposed bill-pay batch and flag bills excluded from
  payment."
- "Tie Project P&L margin movement to time, expense, vendor cost, and invoice
  records."
- "Explain Balance Sheet and Cash Flow movement after the June close package."

Scenario anchors: launch scenario 10, ENT-R2R-003, ENT-OPS-002, ENT-OPS-003,
and #311 for automated ops/health-dashboard proof.

## 10. Settings, Agents, And Controls

Settings are used for:

- Firm and tenant configuration.
- Tax rates and market setup.
- Agent autonomy configuration.
- Scheduled Finance Ops Manager cadence through Settings and the Agents API.
- Approval policy thresholds for AI-created finance actions.
- Finance role persona mapping for RBAC compatibility and user education.
- Agent run ledger and workflow telemetry.
- Operational Health dashboard for safe internal operator review.
- Platform controls as enterprise slices land.

Current guidance:

- Keep money-out, accounting, and external communication workflows review-gated.
- Promote autonomy only after enough successful reviewed outcomes.
- Use Settings -> Agent Autonomy -> Finance Ops Manager Schedule to enable,
  pause, or tune scheduled action-plan cadence and stale-approval escalation.
- Use Settings -> Approval Controls -> Approval Policy Matrix to raise review
  roles for money-out, accounting, money-in, draft, external-send, and
  high-risk AI actions.
- Use Settings -> Approval Controls -> Finance role personas to explain which
  product-facing finance personas map to the current tenant role and what each
  persona can or cannot do through existing approval gates.
- Use run ledger details to inspect tool execution and risk class.
- Use Settings -> Operational Health for support-safe runtime, table/migration,
  rate-limit backend, request-failure, background-failure, agent failure, tool
  failure, workflow failure, and routed-alert signals.
- Keep production provider credentials and mail/payment setup validated outside demo-only environments.

Ops/Security slices under #286, #301, and #311:

- `POST /api/v1/auth/signup` and `GET /api/v1/public/invoices/{token}` are
  protected by app-level rate limits with safe `429` responses and retry
  headers.
- Rate limiting can run in local in-process mode or Supabase/Postgres-backed
  distributed mode through `RATE_LIMIT_BACKEND=supabase`. Distributed mode
  stores hashed subjects only and falls back to in-memory limiting by default
  if the RPC is unavailable.
- Request failures are counted by sanitized method/path/status, without raw
  tokens or request payloads.
- Tenant health exposes runtime config shape, table/migration checks, recent
  request/background failure counters, and agent/tool/workflow failure counts.
- Tenant health now includes routed alert items for degraded health, repeated
  public-endpoint abuse, background failure spikes, and agent/tool/workflow
  failure spikes. If no webhook channel is configured, alerts route to the
  runbook queue in the health output.
- #311 adds deterministic backend proof for shared distributed limiter state
  across simulated app instances, fallback/deny-safe modes, and routed alert
  classes, plus browser proof for Settings -> Operational Health redaction.
- Proof commands: `cd backend && uv run pytest tests/unit/test_ops_hardening.py -q`
  and `cd frontend && npx playwright test e2e/enterprise-ops-health.spec.ts --project=chromium`.
- Health output is intended for internal operators and admins; it must not
  expose secrets, raw credentials, tokens, or customer document payloads.

Scenario anchors: `docs/test/e2e_ops_security.md`, ENT-OPS-001, ENT-OPS-002,
ENT-OPS-003, and #311 for distributed/live-alert proof.

## 11. Enterprise Readiness Roadmap

The following work is tracked under parent issue #278:

| Issue | Area | Outcome |
| --- | --- | --- |
| #279 | Docs and QA | Platform user guide and enterprise E2E scenario library |
| #280 | Controls | Approval policy matrix and role-aware Inbox routing, first slice implemented |
| #281 | Controls | Immutable Inbox decision audit trail, first slice implemented |
| #282 | RBAC | Finance role mapping and read-only permission proof, first slice implemented |
| #283 | AI Ops | Scheduled Finance Ops Manager runs and escalations, first slice implemented |
| #284 | P2P | Vendor invoice matching and coding exceptions, first slice implemented |
| #285 | R2R | Close evidence package and reconciliation gates, first slice implemented |
| #286 | Ops/Security | Rate limiting, telemetry, and tenant health, first slice implemented |
| #295 | AI Ops | Settings UI for scheduled Finance Ops Manager cadence, first slice implemented |
| #296 | Controls | Tenant-configurable approval policy UI, first slice implemented |
| #297 | Audit | Business-record decision timeline and browser proof, first slice implemented |
| #298 | RBAC | Finance-role taxonomy compatibility catalog, Settings visibility, and API/unit permission proof, first slice implemented |
| #299 | P2P | Vendor invoice exception review UX and staged payment approval, first slice implemented |
| #300 | R2R | Close override wizard and statement commentary, first slice implemented |
| #301 | Ops/Security | Distributed rate limiting, Operational Health dashboard, and safe alert routing, first slice implemented |
| #309 | QA proof | Browser E2E implemented for controls, audit, and RBAC proof |
| #310 | QA proof | Browser E2E implemented for AI finance workflows across P2P and R2R |
| #311 | Ops proof | Browser/API proof implemented for distributed limiter, alert, and Operational Health dashboard |
| #312 | Docs and prompts | Full platform guide and prompt-library proof |
| #317 | QA proof | Browser E2E implemented for scheduled Finance Ops Manager schedule, Inbox output, escalation, and workflow telemetry |
| #321 | RBAC proof | Browser E2E implemented for the full finance persona matrix |
| #323 | P2P proof | Line-level PO/service-order match evidence and approval blocking implemented |
| #325 | P2P proof | Pay Bills approve/export/send/settle lifecycle implemented |
| #327 | R2R proof | Year-end close retained-earnings posting implemented |
| #329 | R2R proof | AI-routed year-end close approval implemented |
| #331 | Reporting proof | Comparative AI financial statement package commentary implemented |

## 12. Scenario Crosswalk

| Guide area | User-facing proof | Automation/proof backlog |
| --- | --- | --- |
| Operating model, Copilot, and Inbox | ENT-DOC-001, ENT-DOC-002, ENT-AIOPS-001, ENT-AIOPS-002 | #310 automated for P2P/R2R AI finance workflows; #317 automated for scheduled Finance Ops Manager; #312 docs proof |
| Approval policy and decision evidence | ENT-CTRL-001, ENT-CTRL-002, ENT-CTRL-003, ENT-AUD-001, ENT-AUD-002, ENT-AUD-003 | #309 automated |
| Roles and read-only personas | ENT-RBAC-001, ENT-RBAC-002 | #309 automated; full persona matrix automated in #321 |
| Order to Cash | Launch scenarios 1-4, Engagement to Cash guide | Future depth beyond #310 |
| Procure to Pay | ENT-P2P-001, ENT-P2P-002, ENT-P2P-003, ENT-P2P-004, ENT-P2P-005, launch scenarios 5-7 | #310 automated; #323 automated for line-level PO/SO match evidence; #325 automated for bill-pay lifecycle |
| Record to Report | ENT-R2R-001, ENT-R2R-002, ENT-R2R-003, ENT-R2R-004, ENT-R2R-005, ENT-R2R-006, launch scenarios 8-10 | #310 automated; #327 automated for year-end retained-earnings posting; #329 automated for AI-routed year-end close approval; #331 automated for comparative statement package commentary |
| Reports, management cockpit, and documents | Launch scenario 10, ENT-AUD-003, ENT-OPS-002 | #310 automated for statement tabs and ledger evidence; #311 automated for ops-health evidence |
| Settings, agent schedule, approval controls, personas, and health | ENT-AIOPS-003, ENT-CTRL-003, ENT-RBAC-002, ENT-OPS-003 | #309 automated for approval/persona controls; #321 automated for full finance persona matrix; #311 automated for Operational Health; #317 automated for scheduled manager |

## 13. Documentation And Test Definition Of Done

Every enterprise implementation slice should update:

1. This user guide if user behavior, roles, controls, or workflows change.
2. The enterprise E2E scenario library with the browser/API behavior that should
   be automated later.
3. The relevant domain test doc when it touches O2C, P2P, R2R, onboarding, or Copilot.
4. The launch runbook when evidence or implementation status changes.
5. The prompt library when user-facing Copilot behavior changes.

Do not document internal tool names as required user behavior unless the target
reader is an engineer or QA author. Business users should describe the finance
outcome and approval boundary.

Static verification for this documentation set:

- Confirm local markdown links resolve for `docs/user-guide/platform-user-guide.md`,
  `docs/copilot/prompt-library.md`, and
  `docs/qa/enterprise-e2e-scenario-library.md`.
- Confirm issue IDs #309, #310, #311, and #312 are referenced where the
  residual automation/proof backlog is described.
- Confirm prompt examples remain business-language prompts and do not require
  users to name internal tools.
