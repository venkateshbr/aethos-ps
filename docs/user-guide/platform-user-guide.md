# Aethos PS Platform User Guide

This guide explains how a professional services firm uses Aethos PS as an
agent-first ERP. It is a living document: every enterprise-readiness slice must
update the relevant workflow, control, and testing notes.

Related docs:

- Copilot prompts: [`docs/copilot/prompt-library.md`](../copilot/prompt-library.md)
- Launch QA runbook: [`docs/qa/launch-e2e-scenario-runbook-2026-06-24.md`](../qa/launch-e2e-scenario-runbook-2026-06-24.md)
- Enterprise E2E scenarios: [`docs/qa/enterprise-e2e-scenario-library.md`](../qa/enterprise-e2e-scenario-library.md)
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

## 2. Roles And Responsibilities

Current implementation uses the tenant role hierarchy
`owner > admin > manager > member > viewer > employee`. Enterprise finance
personas map onto that hierarchy for now; finer-grained named roles can be added
later without weakening the existing approval gates.

| Enterprise persona | Current role mapping | What they can do today | Current restrictions |
| --- | --- | --- | --- |
| Owner | `owner` | Configure tenant, unlock high-risk accounting states, approve owner-threshold Inbox work | None inside tenant; still tenant-scoped |
| Admin / Controller | `admin` | Approve money-out, accounting, bills, invoice sends/payments, financial events, settings, and agent controls | Cannot cross tenants |
| Finance Manager / AP Lead | `manager` | Create bills, procurement documents, contacts, engagements, projects, employees, and review manager-threshold Inbox work | Cannot approve admin/owner-threshold money-out/accounting actions |
| Engagement Manager | `manager` | Maintain customers, engagements, projects, services, WIP, draft invoices, and team workflow | Cannot bypass admin approval for posting/sending/payment |
| Staff / Consultant | `member` or Timesheet `employee` | Participate in delivery workflows such as time/expense where exposed | Cannot approve finance, accounting, payment, settings, or agent-control actions |
| Auditor / External CPA | `viewer` | Inspect permitted tenant records, reports, Inbox history, AP/AR records, and read-only evidence | Cannot create, approve, edit, reject, convert, pay, send, or export admin-only audit events |
| Executive / Viewer | `viewer` | Read dashboards, management reports, and operational status | Same read-only mutation restrictions as auditor |

The Bills/AP UI now disables read-only users from creating bills or procurement
documents, approving procurement, converting purchase requests, or opening Pay
Bills from the Bills page. Backend RBAC remains authoritative and returns 403
for direct read-only mutation attempts.

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
- Draft invoices, collections reminders, bill-pay proposals, month-end close preparation, and financial statement packages.

Good prompts include the business period, customer/vendor/engagement name,
desired outcome, and approval boundary. See the prompt library for examples.

### Current AI approval boundary

| AI activity | Current behavior |
| --- | --- |
| Read-only analysis | Can run directly and records tool activity |
| Draft invoice | Routes to Inbox, then materializes as draft invoice after approval |
| Collections reminders | Creates Inbox email-review tasks; approval is required before send path |
| Bill-pay proposal | Routes to Inbox, then creates a draft payment batch after approval |
| Month-end close preparation | Routes to Inbox, then creates close tasks after approval |
| Finance ops action plan | Routes manager plan to Inbox; approval creates Plan Items; Plan Item approval dispatches specialist workflows |
| Financial statement package | Generates read-only summary from report/journal data |
| Vendor invoice upload | Extracts to Inbox review, then creates bill after approval |
| Engagement-letter upload | Extracts to Inbox review, then creates client, engagement, and first project after approval |

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

## 6. Procure To Pay

Procure to Pay covers vendors, bills, approvals, and payment batches.

Typical workflow:

1. Create or import a vendor.
2. Upload a vendor invoice through Copilot or create a bill manually.
3. Review extracted vendor, invoice number, lines, tax, project/account coding, and source document.
4. Approve the bill when ready.
5. Ask Copilot to prepare a bill-pay run or use the Pay Bills UI.
6. Review and approve the proposed payment batch.
7. Export or process the payment batch through the supported downstream path.
8. Review AP Aging and Cash Flow impact.

Current implementation supports vendor invoice upload, bill creation after Inbox
approval, bill-pay proposals, and payment-batch UI visibility. Enterprise P2P
depth is planned under #284: matching, coding exceptions, duplicate guards,
multi-step approvals, recurring bills, and native bank formats.

## 7. Record To Report

Record to Report covers accounting journals, close, and reporting.

Current workflows:

- Invoice and bill approvals post balanced journals through guarded paths.
- Manual journals can be created from the Accounting area.
- Month-end close preparation can be requested through Copilot and routed to Inbox.
- Reports include operational and accounting views such as AR Aging, AP Aging, Project P&L, Utilization, WIP, Revenue, Trial Balance, Balance Sheet, Income Statement, Cash Flow, and Statutory Pack where supported by the current build.
- Copilot can generate a financial statement package summary from report data.

Enterprise R2R depth is planned under #285:

- Close evidence package.
- AR/AP/WIP/subledger reconciliation gates.
- Override reason capture.
- Year-end close and retained earnings depth.
- Manual journal audit enhancements.

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

## 10. Settings, Agents, And Controls

Settings are used for:

- Firm and tenant configuration.
- Tax rates and market setup.
- Agent autonomy configuration.
- Agent run ledger and workflow telemetry.
- Platform controls as enterprise slices land.

Current guidance:

- Keep money-out, accounting, and external communication workflows review-gated.
- Promote autonomy only after enough successful reviewed outcomes.
- Use run ledger details to inspect tool execution and risk class.
- Keep production provider credentials and mail/payment setup validated outside demo-only environments.

## 11. Enterprise Readiness Roadmap

The following work is tracked under parent issue #278:

| Issue | Area | Outcome |
| --- | --- | --- |
| #279 | Docs and QA | Platform user guide and enterprise E2E scenario library |
| #280 | Controls | Approval policy matrix and role-aware Inbox routing, first slice implemented |
| #281 | Controls | Immutable Inbox decision audit trail, first slice implemented |
| #282 | RBAC | Finance role mapping and read-only permission proof, first slice implemented |
| #283 | AI Ops | Scheduled Finance Ops Manager runs and escalations |
| #284 | P2P | Vendor invoice matching and coding exceptions |
| #285 | R2R | Close evidence package and reconciliation gates |
| #286 | Ops/Security | Rate limiting, telemetry, and tenant health |

## 12. Documentation And Test Definition Of Done

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
