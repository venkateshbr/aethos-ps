# Aethos PS Platform User Guide

This guide explains how a professional services firm uses Aethos PS as an
agent-first ERP. It is a living document: every enterprise-readiness slice must
update the relevant workflow, control, and testing notes.

Related docs:

- Aethos Atlas prompts: [`docs/copilot/prompt-library.md`](../copilot/prompt-library.md)
- Atlas/Hermes technical architecture: [`docs/architecture/atlas-hermes-ai-agent-architecture.md`](../architecture/atlas-hermes-ai-agent-architecture.md)
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
| Aethos Atlas | Ask AI to analyze, draft, upload, prepare, and coordinate finance work | AI tools are policy-classified; sensitive work routes to Inbox |
| Inbox | Review, approve, edit, reject, and route AI or workflow recommendations | Human-in-the-loop approval for money, accounting, external sends, and governance |
| ERP modules | Manage clients, vendors, engagements, projects, time, invoices, bills, journals, documents, and reports | Business records remain source-of-truth after approval |
| Settings and telemetry | Configure firm data, tax rates, tenant users, agent controls, run ledger, and workflow status | Admins inspect autonomy, access, agent activity, and operational evidence |

The intended user experience is one AI Finance Ops Manager coordinating work
across specialist workflows. Users should not need internal tool names. They
state the business outcome, review the proposed action when required, and rely
on the audit trail to explain what happened.

### Agent-first workflow loop

Aethos PS should feel like an AI-run finance department with human control
points. Most workflows follow the same loop:

1. Ask Aethos Atlas for a business outcome, such as draft invoices, review vendor
   invoices, prepare bill pay, prepare close, or explain operational blockers.
2. Aethos Atlas performs read-only analysis directly where safe.
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
| Aethos Atlas | `/app/copilot` | All finance users | Analyze, draft, upload, prepare, and explain work in business language | ENT-AIOPS-001, ENT-P2P-001, ENT-R2R-001 |
| Inbox | `/app/inbox` | Managers, AP/AR leads, Controller, Owner/Admin | Review AI proposals, approve with edits, reject, dispatch plan items, inspect decision history | ENT-CTRL-001, ENT-AUD-001, ENT-AUD-002 |
| Clients and vendors | `/app/clients` | Engagement managers, AP/AR leads | Create and inspect customers/vendors, link AR/AP history, support document intake | Launch scenarios 1-7 |
| People | `/app/people` | Admins, managers | Maintain staff, rates, targets, and delivery context for billing/reporting | Launch scenarios 1-4, 10 |
| Engagements and projects | `/app/engagements`, `/app/projects` | Engagement managers, project managers | Set billing terms, organize delivery, connect WIP to invoices and project health | Launch scenarios 1-4 |
| Invoices and public invoice | `/app/invoices`, `/p/:token` | AR lead, Controller, client recipient | Draft/review invoices, send/collect, inspect public invoice status | Engagement to Cash guide |
| Bills and pay bills | `/app/bills`, `/app/billing-runs` | AP lead, Controller, Owner/Admin | Review vendor invoice exceptions, create bills, prepare, approve, export, send, and settle guarded payment batches | ENT-P2P-001, ENT-P2P-002, ENT-P2P-003, ENT-P2P-005 |
| Accounting and close | `/app/accounting/journals` | Controller, Owner/Admin | Prepare close, review blockers, record overrides, generate statements | ENT-R2R-001, ENT-R2R-002, ENT-R2R-003 |
| Reports | `/app/reports` | Executives, managers, auditors | Explain AR/AP/WIP/revenue/project/accounting results and tie AI recommendations to source reports | Launch scenario 10 |
| Documents | `/app/documents` | AP, AR, engagement teams, auditors | Track uploaded source documents, extraction status, and resulting decisions | ENT-P2P-001, ENT-AUD-003 |
| Settings | `/app/settings` | Admins, Owner, operators, auditors where read-only | Configure services, tax, tenant users, autonomy, approval policy, personas, schedules, and inspect health/run ledgers | ENT-AIOPS-003, ENT-CTRL-003, ENT-RBAC-002, ENT-OPS-003 |

## 2. Roles And Responsibilities

Current implementation uses a Dynamics-style security catalog:

`Tenant user -> assigned security role(s) -> duties -> privileges`

`tenant_users.role` still exists as a compatibility projection for legacy JWT,
UI, and API gates while the platform migrates fully to privilege checks. The
authoritative product model is now the security catalog under
Settings -> Security Roles and Settings -> Tenant Users.

| Enterprise role | Legacy projection | Primary duties | Restrictions |
| --- | --- | --- | --- |
| Tenant Owner | `owner` | Tenant administration, security administration, all finance duties, owner-threshold approvals | Tenant-scoped only |
| Tenant Admin | `admin` | Create users, create tenant roles, assign duties, manage settings, administer finance operations | Cannot grant Tenant Owner authority |
| CFO | `admin` | Executive finance review, performance, cash, controls, elevated approvals | Does not automatically own tenant/subscription controls |
| Finance Controller | `admin` | R2R, journals, close, financial statements, accounting approvals, audit evidence | Cannot bypass owner-threshold policy |
| Finance Ops Manager | `manager` | O2C/P2P operations, people/time, draft finance work, manager-threshold approvals | Cannot approve admin/owner-threshold work |
| Finance Approver | `approver` | Manager-threshold Inbox/procurement approval only | Cannot create operational records or approve admin/owner work |
| Procurement Manager | `manager` | Procurement, PO/service-order flow, AP matching, payment packet preparation | Cannot approve elevated spend unless another role grants it |
| AP Manager / AP Clerk | `manager` | Bills, AP evidence, payment preparation, AP exceptions | Payment approval/export remains gated by policy |
| AR Manager / Billing Specialist | `manager` | Draft invoices, WIP, collections, AR reporting | Send/post/payment gates still apply |
| GL Accountant / Close Manager | `admin` | Manual journals, close tasks, period locks, statement generation | Same-user high-value approval remains blocked |
| Engagement Manager / Resource Manager | `manager` | Clients, engagements, projects, WIP, people/time approvals | Cannot bypass finance posting/payment gates |
| Auditor | `auditor` | Read permitted records, reports, Inbox history, and audit evidence | No mutation, approval, posting, payment, send, lock, or settings authority |
| Executive Viewer | `viewer` | Read dashboards, reports, and operational summaries | Read-only |
| AI Operations Admin | `admin` | AI settings, agent autonomy, schedules, operational health | Cannot bypass finance approval policy |
| Timesheet Employee | `employee` | Timesheet portal only | No ERP access |

### Tenant user administration

Tenant Owners and Tenant Admins manage internal Aethos ERP users from
Settings -> Tenant Users. This is separate from the People module: People stores
staff, rates, utilization, managers, and timesheet context; Tenant Users stores
login access and ERP authorization for the main Aethos app.

Settings -> Security Roles shows the seeded master role catalog and each role's
duties/privileges. Tenant Admins can create tenant-specific roles by selecting
seeded duties. The system privilege catalog remains master/config data; tenant
admins create roles from permission sets, not ad-hoc ungoverned privileges.

Tenant user invite workflow:

1. Go to Settings -> Tenant Users.
2. Enter the user's email, display name, security role, and initial password.
   If the password is left blank, Aethos generates a temporary password.
3. Create the user. Aethos creates the login, assigns the security role, records
   the role audit event, and marks the account `must_change_password`.
4. Give the credential or set-password link to the user through a secure
   channel outside shared demo notes.
5. The invited user signs in and is sent to Account/Profile to change the
   initial password before normal app use.
6. After the password change, the user can use the main Aethos app within the
   assigned role's duties and privileges.
7. Tenant Owners/Admins can later update the display name, replace assigned
   roles, or deactivate access from the same Settings surface.

Server-side guardrails:

- `tenant.users.manage` is required for tenant-user administration.
- `security.roles.manage` is required for tenant role creation.
- Only Tenant Owners can grant Tenant Owner authority.
- Tenant Admins can create users, create tenant roles from seeded duties, assign
  non-owner roles, and set initial passwords.
- Users cannot change their own role or deactivate themselves.
- Admin-created users must change the initial password before normal app use.
- Deactivation preserves historical audit evidence while removing active
  access.
- Tenant-user and tenant-role audit events record invite, role update,
  assignment, deactivation, actor, target user, and role-code context.

For production validation tenants, generated credentials are stored locally in
`demo_credentials.json` under
`production_scenario_library_latest.tenants[]`. Each tenant entry contains
`owner`, `erp_manager`, and `timesheet_employee` credentials. Treat that file as
secret material and do not paste passwords into shared docs or screenshots.

The user who registers a new tenant receives the seeded Tenant Owner security
role. During the transition, this also projects to the legacy `owner` role so
existing owner-only gates continue to work.

The Bills/AP UI now disables read-only users from creating bills or procurement
documents, approving procurement, converting purchase requests, or opening Pay
Bills from the Bills page. Backend RBAC remains authoritative and returns 403
for direct read-only mutation attempts.

Settings -> Approval Controls -> Finance role personas remains a readable
business-language summary, while Settings -> Security Roles is the authoritative
role/duty/privilege catalog used for enterprise access control.

### Current approval policy matrix

The first enterprise controls slice adds a seeded approval matrix for Inbox
approvals:

| Task risk | Required approver |
| --- | --- |
| Draft or low-risk write | Manager by default; Finance Approver can decide manager-threshold review work, and tenants may configure Finance Approver for this category |
| Money-in action | Manager by default; Finance Approver can decide manager-threshold review work, and tenants may configure Finance Approver for this category |
| External send | Manager by default; Finance Approver can decide manager-threshold review work, and tenants may configure Finance Approver for this category |
| Money-out action | Admin or higher |
| Money-out action at or above 50,000 in task currency | Owner |
| Accounting action | Admin or higher |

Inbox shows the required approval role on review cards and lets users filter by
required role. The API enforces the same policy at approval time, including
approve-with-edits and rejection, so a corrected payload or rejection cannot
bypass a higher approval threshold.

Users can ask Aethos Atlas for the role-aware approval controls read pack:

> "What am I allowed to approve, what requires Owner approval, and which Inbox
> items are high risk? Include my finance personas, effective thresholds,
> pending high-risk tasks, and why each item needs review. Do not show tool
> names, policy reason codes, raw payloads, traces, logs, or context IDs."

The read pack resolves the caller's tenant role, maps it to finance personas,
summarizes effective approval thresholds, flags visible high-risk Inbox work,
and explains which pending items need a higher approver. It is read-only and
must not expose raw task payloads, internal reason codes, tool calls, traces,
logs, or context references.

## 3. Aethos Atlas And AI Finance Ops Manager

Use Aethos Atlas for chat-first finance operations:

- Upload engagement letters, SOWs, vendor invoices, receipts, and supporting documents.
- Ask for daily finance checks across AR, AP, WIP, close, approvals, and agent runs.
- Ask for reviewed work plans that route sensitive tasks to Inbox.
- Draft invoices, collections reminders, bill-pay proposals, month-end/year-end
  close preparation, and financial statement packages.
- Read uploaded document extraction results, engagement/project structure,
  resource delivery data, accounting decision trails, and operational health
  through Aethos-owned tools.

When attaching a document in Aethos Atlas, file selection only stages the source
document. Extraction and any Inbox task creation start after the user sends a
business prompt such as "process this vendor invoice" or "review this engagement
letter." The Documents page may show the staged file as `uploaded` until that
prompt is submitted.

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

Users do not need to specify tool names in chat. Aethos Atlas should infer the
correct internal capability from the business request. QA specs may still pin a
tool name when they need deterministic run-ledger assertions.

Engineering details for runtime selection, Hermes MCP wiring, tool broker
dispatch, database tables, and UI screen ownership are documented in
[`Atlas And Hermes AI Agent Architecture`](../architecture/atlas-hermes-ai-agent-architecture.md).

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
| Time logging | Uses the time-entry tool path and respects project/employee resolution |
| Engagement creation by prompt | Resolves client names and routes engagement drafts to Inbox rather than asking users for internal IDs |
| Operational health | Returns safe health, rate-limit, background failure, agent/tool/workflow failure, and observability status without logs or secrets |

### Scheduled Finance Ops Manager

Admins can configure the scheduled AI Finance Ops Manager through the Agents
API at `/api/v1/agents/finance-ops/schedule`. Tenants without an explicit row
use a seeded default: daily at 07:00 UTC, current-month review, 10-row lookback,
24-hour stale threshold, 4-hour high-risk threshold, and escalation enabled.

The scheduled worker runs hourly and only acts when the tenant cadence is due.
For each due tenant it:

1. runs the same read-only command-center analysis used by Aethos Atlas;
2. creates one `copilot_create_finance_ops_action_plan` Inbox task for manager review;
3. suppresses duplicate open scheduled plans for the same tenant/cadence window;
4. creates non-destructive `finance_ops_escalation` Inbox notices for stale or high-risk tasks; and
5. records a `scheduled_finance_ops_manager` workflow run visible in Settings telemetry.

Approval boundary: approving the scheduled action plan only fans out reviewed
Plan Items. Approving an escalation notice acknowledges the escalation; the
source Inbox task still requires its own approval, rejection, or correction.

Managers and above can ask Aethos Atlas for a consolidated control-room readback:

> "Show me the Finance Ops Manager control room. Include the current schedule,
> next run, latest scheduled run, failed or skipped workflows, open action
> plans, open Plan Items, stale approval escalations, and operational health.
> Do not show tool names, traces, logs, context IDs, or raw system details."

The control-room response is read-only. It combines the tenant schedule,
scheduled workflow status, open Finance Ops Inbox work, and redacted operational
health. It should not expose raw tool calls, traces, logs, stack traces, or
internal context references to business users.

Browser proof command: `cd frontend && npx playwright test e2e/enterprise-scheduled-finance-ops.spec.ts --project=chromium`

### Recommended daily operating rhythm

| Time | User | Action | Evidence to inspect |
| --- | --- | --- | --- |
| Morning | Owner/Admin or Controller | Ask Aethos Atlas for the daily finance ops check or Finance Ops Manager control room | Inbox action plan, Settings workflow runs, Operational Health, agent run ledger |
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
| Filter by required role | Focus on tasks needing Owner, Admin, Manager, or Finance Approver review |
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
Viewer/auditor roles can inspect this record-scoped metadata without gaining
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
4. Log time and billable expenses manually or through Aethos Atlas.
5. Ask Aethos Atlas to draft an invoice or use the invoice UI.
6. Review AI-created invoice drafts in Inbox.
7. Approve, send, and collect payment through the normal invoice lifecycle.
8. Review AR Aging, WIP, revenue, project P&L, and financial statements.

Current safeguards:

- Drafting and approval are separate.
- Invoice approval and send/payment remain explicit lifecycle steps.
- Journal posting is guarded by accounting validation.
- Reports should tie back to posted business records.

Current implementation details to document in demos and tests:

- Engagement-letter or SOW approval can create a customer, engagement, first
  project, and linked rate card when reviewed rate hints are present.
- Service catalogue, tax rates, people, rate cards, time entries, and expenses
  are source records for billing and project economics.
- Time and billable expenses should be approved or clearly eligible before they
  become invoice lines; non-billable work remains visible for margin/utilization
  but is excluded from invoice drafting.
- Public invoice pages expose only customer-safe invoice data. Internal
  comments, source documents, Inbox history, agent runs, and approval evidence
  remain authenticated.
- Stripe payment links are generated when Stripe Connect is available. If a
  tenant is not connected, operators can still send the invoice without a
  payment link and settle through the manual record-payment path.
- AR payments store transaction amount, currency, tenant-base amount, FX rate
  provenance, and realised FX adjustment when payment-date base value differs
  from invoice-date base value.
- Aethos Atlas can answer O2C collections read prompts before drafting any
  reminder: customer balances, invoice status, due dates, aging buckets,
  payment status, public invoice/payment-link state, reminder history,
  collections policy stage, blockers, and recommended next action.
- Collections reminders are drafted into Inbox with invoice, customer,
  recipient, tone, subject, body, confidence, and eligibility rationale. Email
  is not sent before approval.

O2C edge cases and controls:

| Edge case | Expected behavior |
| --- | --- |
| Missing tax setup | Invoice draft or posting is blocked with a clear path to Settings -> Tax Rates |
| Locked accounting period | Backdated invoice posting is rejected; user must date the invoice in an open period or reopen through permitted controls |
| Read-only user attempts mutation | Viewer/auditor can inspect permitted records but cannot approve, send, void, or record payment |
| Public invoice abuse | Public invoice token endpoint is rate-limited and telemetry stores sanitized paths, not raw tokens |
| Disputed or collections-hold invoice | Atlas flags the blocker and recommends no reminder until the dispute/hold is resolved |
| Partially paid invoice | Atlas reports paid amount, balance due, and recommends collecting only the remaining balance |
| Draft, paid, or voided invoice | Atlas explains why collections follow-up is not appropriate |
| LLM unavailable for drafting | User can continue through ERP invoice forms and source records; AI is not the only path |
| FX rate missing for non-base currency | Posting is refused until a valid FX rate exists rather than guessing |

Scenario anchors: launch scenarios 1-4, `docs/test/e2e_engagement_to_cash.md`,
ENT-CTRL-001, ENT-AUD-003, and #309 for automated control/audit/RBAC proof.

## 6. Procure To Pay

Procure to Pay covers vendors, bills, approvals, and payment batches.

Typical workflow:

1. Create or import a vendor.
2. Upload a vendor invoice through Aethos Atlas or create a bill manually.
3. Review extracted vendor, invoice number, lines, tax, project/account coding, and source document.
4. Approve the bill when ready.
5. Ask Aethos Atlas to prepare a bill-pay run or use the Pay Bills UI.
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

Aethos Atlas can answer read-only P2P payment-risk prompts before creating a
payment proposal: vendor balances, bill status, due dates, coding status,
source-document availability, duplicate signals, PO/service-order match state,
payment readiness, existing safe batch state, blockers, and recommended next
action. The read pack does not expose raw bank details, export hashes, raw
payloads, traces, logs, or context references.

P2P edge cases and controls:

| Edge case | Expected behavior |
| --- | --- |
| Duplicate vendor invoice | Draft cannot be approved as-is; reviewer must approve with edits and provide a duplicate-review reason |
| PO/service-order mismatch | Line-level match summary is persisted; quantity, price, unmatched-line, or service-period exceptions keep the bill in draft until corrected or justified |
| Missing source or coding evidence | Atlas flags payment readiness as blocked until source document and coding evidence are resolved |
| Existing payment batch | Atlas shows draft/approved/sent/settled batch state without raw bank details or export hashes |
| Paid or voided bill | Atlas explains that no payment action is appropriate |
| High-value payment batch | Approval policy routes money-out work to Admin or Owner based on configured threshold |
| Missing vendor bank details | Bill can remain in AP, but payment execution is blocked until bank/payment details are resolved |
| Viewer attempts AP mutation | UI hides or disables mutation controls and API returns 403 for create/approve/export/send/settle attempts |
| Payment file already exported | Export/send/settle lifecycle is explicit so operators can see whether a file has already been generated or sent |
| Payment settlement | Settlement confirmation posts DR Accounts Payable / CR Bank and updates AP Aging and Cash Flow |

P2P demo proof should always show four separate gates:

1. source invoice extraction and exception review;
2. bill approval and AP journal evidence;
3. payment batch approval and required role;
4. export/send/settle lifecycle and settlement journal.

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
- Month-end close preparation can be requested through Aethos Atlas and routed to Inbox.
- Admin/Owner users can post year-end close from Accounting. The system closes
  posted revenue and expense balances to seeded account `3000 Retained
  Earnings` through a balanced `year_end_close` journal and blocks duplicate or
  locked-year attempts.
- Aethos Atlas can prepare year-end close through Inbox. The review task includes
  retained-earnings posting preview, readiness blockers, P&L activity, and
  current-vs-prior year statement commentary; approval posts through the same
  year-end close service used by Accounting.
- Reports include operational and accounting views such as AR Aging, AP Aging, Project P&L, Utilization, WIP, Revenue, Trial Balance, Balance Sheet, Income Statement, Cash Flow, and Statutory Pack where supported by the current build.
- Aethos Atlas can produce a read-only R2R management pack for a named period.
  The pack normalizes prompts such as `June 2026` or `2026-06-30` to the same
  accounting period, compares to a named or previous period, and explains major
  revenue, expense, net income, cash, project margin, utilization, AR/AP movement,
  journal, close-task, and close-blocker signals from Aethos records. This
  readback does not create Inbox tasks, post journals, or lock periods.
- Aethos Atlas can generate a financial statement package summary from report data,
  close readiness, management commentary, and current-vs-comparison period
  variance commentary. If the user does not name a comparison period, Aethos Atlas
  compares against the immediately preceding period window.

Close evidence now includes:

- AR, AP, WIP, GL, and approval readiness evidence from real records.
- Subledger, trial-balance, unposted-journal, close-review, and close-task lock blockers.
- Supporting record references where the system can identify the source row.
- Recorded close overrides with blocker code, reason, actor, role, timestamp,
  and blocker evidence.

R2R management-pack edge cases:

- If the period has no posted GL, project margin, or utilization activity, Atlas
  labels the response as no activity rather than inventing commentary.
- If no close task checklist has been bootstrapped, Atlas calls that out as a
  close-task setup blocker even if other close gates look ready.
- If the period is locked, Atlas treats the pack as review-only and recommends a
  controlled unlock path for any changes.
- Draft journals are shown as blockers until posted, rejected, or documented.
- Cross-tenant rows are not included in the pack even if an ID from another
  tenant is mentioned in the prompt.

Period lock remains blocked while required gates fail unless the matching close
override has been recorded. Overrides require a reason of at least 10 characters
and are included in the close package for controller/CPA review. Aethos Atlas close
preparation surfaces blocker counts, override counts, and readiness evidence
before creating close tasks through Inbox.
The Accounting close package panel also lets Admin/Owner users record named
override reasons for supported blockers and immediately shows those overrides
in the period evidence.

R2R edge cases and controls:

| Edge case | Expected behavior |
| --- | --- |
| Manual journal without business reason | Rejected with validation error; no journal or audit event is posted |
| Imbalanced manual journal | Rejected by accounting validation; no partial posting |
| High-value manual journal | Routes to Inbox, records submitted-for-approval evidence, and posts only after approval by a different permitted accounting approver |
| Same-user high-value approval | Denied, task remains open, and approval-denial evidence is recorded |
| Rejected journal task | Captures rejection reason and posts no journal |
| Posted manual journal reversal | Creates a new reversal journal with flipped lines and reason; original remains immutable |
| Duplicate manual reversal | Blocked with a clear conflict; first reversal remains the correction record |
| Non-manual reversal through manual path | Rejected; user must use the relevant sub-ledger correction path |
| Close blocker without override | Period lock remains blocked until resolved or a named reasoned override is recorded |
| Statement package generation | Read-only; numbers come from report/journal services and do not mutate records |
| Missing FX rate for foreign-currency posting | Posting is refused rather than silently estimating base amounts |

Remaining enterprise R2R depth after the #285/#300 first slices, #310 browser
proof, #327 year-end close posting, #329 AI-routed year-end approval, #331
comparative statement packages, #333 manual-journal audit evidence, #335
manual-journal threshold approval, #337 manual-journal reversal, #339
submitted/rejected lifecycle evidence, #341 same-user approval denial, #347
multi-currency base amounts, and #351 FX provenance:

- Richer workpaper orchestration.

Scenario anchors: launch scenarios 8-10,
`docs/test/e2e_record_to_report.md`, ENT-R2R-001, ENT-R2R-002, ENT-R2R-003,
ENT-R2R-004, ENT-R2R-005, ENT-R2R-006, ENT-R2R-007, ENT-R2R-008,
ENT-R2R-009, ENT-R2R-010, #310 for automated AI finance workflow proof, #327
for year-end retained-earnings posting proof, #329 for AI-routed year-end close
approval proof, #333/#335/#337/#339/#341 for manual-journal lifecycle proof,
and #347/#351 for multi-currency journal proof.

## 8. Documents

Documents are part of the audit trail for AI-assisted work.

Users can:

- Upload documents through Aethos Atlas.
- Track extraction status from document cards.
- Review extracted payloads in Inbox.
- Preserve source-document linkage into materialized bills or engagements where supported.
- Ask Atlas to read document intake context after upload: source filename,
  extraction status, extracted payload, linked Inbox task, and materialized
  business record.

Recommended practice:

- Treat extracted values as proposals, not facts, until reviewed.
- Use approve-with-edits when document data is structurally correct but needs correction.
- Keep source documents attached for audit evidence.
- Ask Aethos Atlas to summarize document evidence, but approve the reviewed business
  record from Inbox before relying on it in AP, AR, engagement, or close flows.

Document evidence should be visible across the workflow:

| Source document | Expected lineage |
| --- | --- |
| Engagement letter or SOW | Document attach -> prompt-triggered extraction -> engagement draft -> Inbox approval -> client, engagement, first project, and linked rate card where rate hints exist |
| Vendor invoice | Document attach -> prompt-triggered extraction -> bill draft with vendor/coding/duplicate/PO evidence -> Inbox approval -> bill and bill-line review evidence |
| Receipt or project expense | Document attach -> prompt-triggered extraction -> project expense with billable/non-billable treatment and source link |
| Dividend notice or accounting support | Document attach -> prompt-triggered extraction -> journal packet or manual journal support -> Inbox/accounting approval -> posted journal evidence |
| COSEC instruction | Document attach -> prompt-triggered extraction -> project milestone, billing event, or engagement support record where configured |

Atlas should not ask a user to retype fields already present in the extraction
payload or linked Inbox task. If the extracted payload is incomplete, Atlas
should say which field is missing and route the risk through Inbox or
approve-with-edits.

Document and audit edge cases:

- Low-confidence extraction routes to Inbox rather than silently creating records.
- Prompt-injection text inside a document is treated as untrusted document
  content and should be surfaced as risk evidence, not executed as instruction.
- Viewer/auditor users can inspect permitted source evidence and record-scoped
  decision timelines without create/edit/delete permissions.
- Deleted or unauthorized document access follows tenant/RBAC controls and
  should not leak whether another tenant's object exists.

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
- Tenant user invite, role update, deactivation, and access audit review.
- Tax rates and market setup.
- Agent autonomy configuration.
- Scheduled Finance Ops Manager cadence through Settings and the Agents API.
- AI inference runtime and OpenRouter model routing.
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
- Ask Aethos Atlas for the Finance Ops Manager control room to inspect schedule,
  next run, failed or skipped workflows, open Inbox work, and redacted
  operational health from one business prompt.
- Use Settings -> Agent Autonomy -> AI Inference Settings to choose the tenant
  Atlas runtime and model-routing order. The default OpenRouter chain is
  `google/gemma-4-31b-it:free` -> `openrouter/free` ->
  `anthropic/claude-haiku-4.5`.
- The AI settings chain applies to Aethos Basic, the built-in Atlas fallback,
  and tenant-scoped document/reporting agents. Hermes uses the mounted Atlas
  profile for its primary model until the Hermes runtime supports dynamic
  per-tenant model selection.
- Use Settings -> Approval Controls -> Approval Policy Matrix to raise review
  roles for money-out, accounting, money-in, draft, external-send, and
  high-risk AI actions.
- Use Settings -> Approval Controls -> Finance role personas to explain which
  product-facing finance personas map to the current tenant role and what each
  persona can or cannot do through existing approval gates.
- Use Settings -> Tenant Users to invite ERP users, assign owner/admin/manager/
  approver/member/auditor/viewer roles, test independent login, change roles, deactivate access,
  and inspect the tenant-user audit trail.
- Use run ledger details to inspect action evidence and risk class.
- Use Settings -> Operational Health for support-safe runtime, table/migration,
  rate-limit backend, request-failure, background-failure, agent failure, tool
  failure, workflow failure, and routed-alert signals.
- Keep production provider credentials and mail/payment setup validated outside demo-only environments.

Settings demo checklist:

| Settings surface | What to verify |
| --- | --- |
| Services | Active service catalogue maps to engagements, invoice lines, and reporting |
| Tax Rates | Market tax setup exists before invoice/bill posting |
| Collections Policy | Reminder cadence and tone are configured before email tasks are approved |
| Stripe Connect | Payment-link readiness or manual-payment fallback is clear |
| Tenant Users | Owner/admin can invite ERP users, assigned users can log into the main app, role changes/deactivation are audited, and self-demotion/self-deactivation is blocked |
| AI Inference Settings | Tenant Admin / Owner can choose Hermes vs Aethos Basic and verify the effective model chain: Gemma 4 31B free, OpenRouter free router, Claude Haiku fallback |
| Agent Autonomy | Scheduled Finance Ops Manager cadence, work-item limit, stale escalation windows, and Atlas control-room readback are visible |
| Approval Controls | Required roles and high-value thresholds are visible and enforced by Inbox/API |
| Finance Role Personas | Product-facing personas map to current tenant roles and explain allowed/blocked actions |
| Agent Runs | Prompt, actions, evidence snapshots, risk class, and replay-safe validation are inspectable |
| Workflow Runs | Scheduled manager, close, and specialist workflow status are visible |
| Operational Health | Runtime/table/limiter/failure/alert signals are redacted and safe for support |

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

Ops and abuse-path checks:

| Check | Expected behavior |
| --- | --- |
| Signup or public invoice endpoint exceeds limit | Safe 429 response with retry headers |
| Public invoice token abuse | Telemetry records sanitized method/path/status, not raw tokens |
| Tenant health without permission | RBAC denies access |
| Distributed limiter unavailable | Health shows fallback/deny-safe state without exposing credentials |
| Agent/tool/workflow failures | Counts and names are visible; payload snapshots and secrets are not |
| Alert routing | Output shows channel/runbook metadata only, never webhook URLs or secret values |

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
| #333 | R2R proof | Manual-journal business reason and immutable posting evidence implemented |
| #335 | R2R proof | High-value manual journals route through Inbox threshold approval |
| #337 | R2R proof | Posted manual journals reverse through controlled reversal journals |
| #339 | R2R proof | Manual-journal submitted/rejected lifecycle evidence implemented |
| #341 | R2R proof | Same-user high-value manual-journal approval denial implemented |
| #345 | Engagement proof | Engagement/SOW approval materializes linked rate cards from reviewed hints |
| #347 | R2R proof | Multi-currency manual journals store tenant-base amounts and remain balanced |
| #349 | O2C proof | Non-base-currency AR payments store base amounts and realised FX impact |
| #351 | O2C/R2R proof | FX rate provenance is stored on payments and journal lines |
| #353 | AI Ops proof | Finance Ops Manager control-room read pack implemented |
| #354 | Controls proof | Role-aware approval controls and Inbox-risk read pack implemented |
| #355 | O2C proof | Customer collections and invoice drilldown read pack implemented |
| #356 | P2P proof | Vendor bill and payment-risk drilldown read pack implemented |
| #357 | R2R proof | Management-pack reporting and close drilldown read pack implemented |
| #364 | RBAC/user admin proof | Tenant-user invite, role update, deactivation, audit events, Settings UI, and production ERP-manager login validation implemented as first slice |

## 12. Scenario Crosswalk

| Guide area | User-facing proof | Automation/proof backlog |
| --- | --- | --- |
| Operating model, Aethos Atlas, and Inbox | ENT-DOC-001, ENT-DOC-002, ENT-AIOPS-001, ENT-AIOPS-002 | #310 automated for P2P/R2R AI finance workflows; #317 automated for scheduled Finance Ops Manager; #312 docs proof |
| Approval policy and decision evidence | ENT-CTRL-001, ENT-CTRL-002, ENT-CTRL-003, ENT-AUD-001, ENT-AUD-002, ENT-AUD-003 | #309 automated |
| Roles, tenant users, and read-only personas | ENT-RBAC-001, ENT-RBAC-002 | #309 automated; full persona matrix automated in #321; tenant-user invite and production ERP-manager login validated in #364 |
| Order to Cash | Launch scenarios 1-4, Engagement to Cash guide, ENT-E2C-001, ENT-E2C-002 | #345 automated for linked rate cards; #349/#351 automated for AR payment base amounts, realised FX, and FX provenance |
| Procure to Pay | ENT-P2P-001, ENT-P2P-002, ENT-P2P-003, ENT-P2P-004, ENT-P2P-005, launch scenarios 5-7 | #310 automated; #323 automated for line-level PO/SO match evidence; #325 automated for bill-pay lifecycle |
| Record to Report | ENT-R2R-001 through ENT-R2R-010, launch scenarios 8-10 | #310 automated; #327 automated for year-end retained-earnings posting; #329 automated for AI-routed year-end close approval; #331 automated for comparative statement package commentary; #333/#335/#337/#339/#341 automated for manual-journal reason, approval, rejection, same-user denial, and reversal; #347/#351 automated for multi-currency base amounts and FX provenance |
| Reports, management cockpit, and documents | Launch scenario 10, ENT-AUD-003, ENT-OPS-002 | #310 automated for statement tabs and ledger evidence; #311 automated for ops-health evidence |
| Settings, tenant users, agent schedule, approval controls, personas, and health | ENT-AIOPS-003, ENT-CTRL-003, ENT-RBAC-002, ENT-OPS-003 | #309 automated for approval/persona controls; #321 automated for full finance persona matrix; #364 validates tenant-user invite/login; #311 automated for Operational Health; #317 automated for scheduled manager |

## 13. Documentation And Test Definition Of Done

Every enterprise implementation slice should update:

1. This user guide if user behavior, roles, controls, or workflows change.
2. The enterprise E2E scenario library with the browser/API behavior that should
   be automated later.
3. The relevant domain test doc when it touches O2C, P2P, R2R, onboarding, or Aethos Atlas.
4. The launch runbook when evidence or implementation status changes.
5. The prompt library when user-facing Aethos Atlas behavior changes.

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
