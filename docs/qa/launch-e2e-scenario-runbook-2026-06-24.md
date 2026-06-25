# Launch E2E Scenario Runbook - 2026-06-24

Purpose: validate Aethos PS as a launch-ready, browser-configurable professional-services ERP using realistic end-to-end scenarios. The script is written for manual execution by the launch team and for mapping to Playwright browser specs.

Scope rule: create and validate operational data through the browser UI. Do not seed business data directly through the backend for these scenarios. Existing authenticated test users and tenant access may be reused.

Launch bar: every feature must either pass through a browser workflow, be explicitly documented as already covered by a supplemental automated/API test, or be filed as a launch gap. A feature is not launch-verified if the only path is direct database/API setup and the browser cannot configure or inspect the result.

## Execution Rules

Use these rules for every scenario:

1. Start from a clean browser context or explicitly log out and back in between role changes.
2. Prefix all operational records with `Launch QA 20260624` so they can be filtered from existing demo data.
3. Enter customer, vendor, employee, service, tax, engagement, project, time, invoice, bill, journal, and close data through the UI only.
4. Do not use backend seeding for business records. If a required setup action is not possible in the browser, stop the specific step, capture the screen, and create a GitHub issue.
5. Validate the downstream result in at least one list page, one detail page where available, and one report or close/accounting surface.
6. For every negative test, verify the UI blocks invalid submission with a visible message or returns a non-500 failure that is shown to the user.
7. Record the exact route, role, expected result, actual result, and evidence path for every discrepancy.
8. Treat console errors, HTTP 500s, broken loading states, missing empty states, and silent failures as launch gaps.
9. When a scenario uses Copilot, write the prompt in business language first. Internal tool names may be used only in QA fixtures or ledger assertions.

## Test Roles And Access Coverage

The operational scenarios should be executed primarily as a tenant admin or owner. Role validation must then re-run the same key routes with restricted accounts.

| Role | Launch persona | Required browser checks |
| --- | --- | --- |
| Owner/Admin | Maya Rao | Can create settings, contacts, employees, engagements, projects, invoices, bills, journals, close tasks, and agent settings |
| Engagement Manager | Daniel Brooks | Can view client/project health, approve time if assigned, review WIP, but cannot change tenant-level autonomy/settings unless explicitly allowed |
| Project Manager | Priya Shah | Can view assigned projects, team, milestones, time, utilization/capacity, and relevant reports |
| Staff Consultant | Nina Patel | Can enter time/expenses where UI allows; cannot approve invoices, bills, journals, or tenant settings |
| AP Lead | Chris Moore | Can work vendor onboarding, bills, procurement, pay-bills, and AP Aging; cannot approve revenue actions unless explicitly allowed |
| Controller | Rachel Kim | Can post journals, work close tasks, review financial statements, and inspect statutory reports |
| Viewer/Auditor | Read-only QA user | Can view permitted data, Bills/AP mutation buttons are disabled, direct Inbox/Bills/Procurement/Financial Events mutations fail cleanly |

If role-auth users are not already available, create the initial auth accounts using the approved backend/admin path, then create all ERP employee/persona records through `/app/people`.

## Test Firm Context

Firm: Aster & Co Advisory

Operating model:
- 50-person professional-services firm.
- Service lines: CFO Advisory, ERP Implementation, Managed Accounting, Tax & Compliance, Payroll Operations, Audit Readiness.
- Roles used in scenarios: Owner/Admin, Engagement Manager, Project Manager, Senior Consultant, Staff Consultant, AP Lead, Controller.
- Base currency: USD.
- Launch test prefix: `Launch QA 20260624`.

Representative employees to create or verify in People:

| Name | Role | Department | Bill rate | Utilization target |
| --- | --- | --- | ---: | ---: |
| Maya Rao | Owner/Admin | Leadership | 350 | 65% |
| Daniel Brooks | Engagement Manager | CFO Advisory | 300 | 75% |
| Priya Shah | Project Manager | ERP Implementation | 260 | 80% |
| Elena Garcia | Senior Consultant | Managed Accounting | 210 | 82% |
| Omar Khan | Senior Consultant | Tax & Compliance | 225 | 78% |
| Nina Patel | Staff Consultant | Delivery | 145 | 85% |
| Chris Moore | AP Lead | Finance Ops | 160 | 70% |
| Rachel Kim | Controller | Record to Report | 240 | 70% |

The firm is modeled as a 50-person company; the runbook uses these named employees as the minimum browser-entered set. Capacity/reporting should be interpreted in that context.

## Master Data Setup

Run these once before the scenario pass.

1. Open `/app/settings`.
2. Open Services.
3. Add or verify these service catalogue entries:

| Service | Service line | Billing unit | Default rate |
| --- | --- | --- | ---: |
| Fractional CFO Advisory | Advisory | hour | 300 |
| ERP Implementation Program | Advisory | milestone | 25000 |
| Monthly Managed Accounting | Accounting | month | 12000 |
| Corporate Tax Compliance | Tax | fixed_fee | 18000 |
| Payroll Operations | Payroll | employee_month | 40 |
| Audit Readiness Review | Advisory | fixed_fee | 35000 |

4. Open `/app/people`.
5. Create or verify the representative employees above.
6. Open `/app/clients`.
7. Create the customer and vendor contacts listed in the scenarios below.

Expected result: services, employees, customer contacts, and vendor contacts are visible in their respective browser pages without backend seeding.

## Complete Platform Coverage Matrix

Every row below must be covered during the launch pass. If a UI route exists but the flow cannot complete from the browser, record a gap instead of compensating through the backend.

| Area | Browser route | Covered by scenarios | Required coverage |
| --- | --- | --- | --- |
| Landing and auth guard | `/`, `/login`, guarded `/app/*` | Access pass | Anonymous users are redirected away from app routes; valid users land in the shell; invalid credentials show a clear error |
| Signup wizard | `/signup` | Supplemental only | Do not use for scenario tenant setup in this pass; verify page renders and no regression is introduced |
| Copilot | `/app/copilot` | 8, 10 | New chat, prompt send, upload entry point, draft cards, approve/reject actions, low-confidence/HITL path, prompt-injection refusal |
| Documents | `/app/documents` | 1, 5, 6, 10 | Uploaded/extracted documents appear, source records can be found, empty and error states render |
| Inbox/HITL | `/app/inbox` | 3, 5, 6, 8, 10 | Approve, reject, edit payload, approve-all where safe, required-role chips, Open/Done/All status filters, decision-history cards, L3 promotion task handling, assigned owner/SLA chips |
| Contacts/customers/vendors | `/app/clients`, `/app/clients/:id` | Master, 1-7 | Customer/vendor/both creation, filters, details, vendor onboarding controls, AR/AP history visibility |
| People | `/app/people` | Master, 1-4, 10 | Employee creation, employment type/rates/targets, list filtering, invalid data validation |
| Engagements | `/app/engagements`, `/app/engagements/:id` | 1-4, 10 | Fixed fee, T&M, capped T&M, retainer, retainer draw, milestone, mixed billing where available |
| Projects | `/app/projects`, embedded detail panels | 1-4, 6, 10 | Project create, engagement linkage, project codes, team assignment, milestone/phase panel, delete/blocked delete checks |
| Time entries | `/app/time`, `/app/time-entries` | 1-4, 10 | Billable/non-billable time, project linkage, invalid hours/date, submitted/approved status visibility |
| Approvals | `/app/approvals` | 1-4, 10 | Manager review, approve/reject with reason, rejected entries can be corrected where supported |
| Expenses | `/app/expenses` | 5, 6, 10 | Manual expense create, extracted expense review, employee/vendor/project coding, invalid amount validation |
| Invoices | `/app/invoices`, `/app/invoices/:id` | 1-4, 7, 9 | Draft, approve, send, payment link, mark paid, duplicate/partial/overpayment behavior where exposed |
| Public invoice | `/p/:token` | 1-4 | Public unauthenticated invoice view, payment status, expired/rotated token behavior if exposed |
| Bills and procurement | `/app/bills`, `/app/bills/:id` | 5-7, 9 | PO, service order, vendor bill, match status, prepaid/service dates, approval, rejection, bill detail |
| Pay bills | `/app/billing-runs` | 7 | Select approved bills, create batch, export/send, settle, same-currency enforcement, status transitions |
| Accounting journals | `/app/accounting/journals` | 8, 9 | Manual balanced journal, imbalanced rejection, recurring template, close checklist, proposals, close package, period lock guard |
| Reports | `/app/reports` | 1-10 | All tabs render, data matches upstream transactions, no stale skeletons/errors |
| Settings - services | `/app/settings` | Master, 1-4 | Service catalogue create/edit, service line, unit, rates, active/inactive behavior |
| Settings - tax rates | `/app/settings` | Master, 4, 5, 9 | Add/disable tax rates, effective dates, jurisdictions, output/input tax reporting |
| Settings - autonomy | `/app/settings` | 8, 10 | Agent enable/disable, level change, promotion eligibility, confirmation modal |
| Settings - operational health | `/app/settings` | 9, 10 | Health status, table checks, rate-limit backend, request/background failures, agent/tool/workflow failures, routed alerts |
| Settings - agent runs | `/app/settings` | 8, 10 | Run ledger filters, run detail, tool invocations, replay preview/validation where data exists |
| Settings - workflow runs | `/app/settings` | 8, 10 | Workflow filters, status rows, step expansion, waiting-on-human state |
| Profile/change password | `/app/profile`, settings account controls | Access pass | Profile renders; change-password form validates current/new/confirm fields where exposed |
| Payments list | `/app/payments` | 1-4, 7 | Payments page renders and reflects recorded invoice payments where the product exposes payment list data |
| Multi-tenant isolation | Authenticated app routes | Access pass | Records created in one tenant do not appear in another tenant; direct URLs fail cleanly |
| Documentation and prompt library | `docs/user-guide/platform-user-guide.md`, `docs/copilot/prompt-library.md`, `docs/qa/enterprise-e2e-scenario-library.md` | ENT-DOC-002 | Guide covers every major product surface; prompts do not require tool names; #309, #310, #311, and #317 are automated |

## Reports Coverage Checklist

Open `/app/reports` after Scenarios 1-9 and verify every tab below. The tester should record whether each tab is data-backed, empty-but-valid, or failing.

| Report tab | Data expected from scenarios | Pass criteria |
| --- | --- | --- |
| AR Aging | Unpaid and paid invoices from Scenarios 1-4 | Open invoices age correctly; paid invoices drop out or show paid according to product design |
| AP Aging | Vendor bills from Scenarios 5-7 | Approved unpaid bills age; settled bills no longer appear as payable |
| Project P&L | Time, employee cost, vendor cost, invoices | Revenue, labor cost, vendor cost, gross margin, and project status are coherent |
| Project Health | Budget, cap, WIP, margin, milestone dates | Risk score and drivers explain underperforming/over-cap projects |
| Capacity | People availability, assignments, time | Overloaded/under-utilized employees receive sensible status and actions |
| Backlog | Multi-year retainer and milestone program | Contracted value, recognized backlog, unbilled WIP, and due milestones render |
| Profitability | Customer and service-line revenue/cost | Client, group, and service-line margins tie directionally to scenario economics |
| Practice | 50-person firm service-line view | Practice health, utilization, margin, and recommendations render |
| Recommendations | Risk and improvement opportunities | Recommendations are explainable and linkable/actionable where supported |
| Action Queue | Close tasks, HITL, overdue work | All-work and assigned-to-me views have owner, SLA, status, and route context |
| Scope Advisor | Capped T&M, milestones, change/risk | Scope warnings and suggested actions appear for cap/milestone stress cases |
| Utilization | Employee time entries | Billable/non-billable mix and utilization percent are reasonable |
| WIP | Unbilled approved time and expenses | WIP increases before invoicing and decreases after billing |
| Revenue | Approved/sent/paid invoices | Revenue totals align to billed service scenarios |
| Balance Sheet | Posted invoice/payment/bill/journal entries | Assets equal liabilities plus equity; imbalance warning never appears for valid data |
| Income Statement | Revenue and expense journals | Revenue, payroll, vendor, tax, and net income are directionally correct |
| Cash Flow | Paid invoices and settled bills | Operating cash increases/decreases after payment activity |
| Statutory Pack | Tax and statements | Tax buckets, statements, and compliance summaries render |
| Trial Balance | All posted journals | Debits equal credits; period selector works |

## Edge Case Catalogue

Run these edge cases across the scenarios rather than as isolated smoke tests.

| Edge area | Required cases |
| --- | --- |
| Required fields | Submit blank create forms for contact, person, engagement, project, time, invoice/bill line, journal line, and service; verify disabled submit or visible validation |
| Duplicate/naming | Create records with similar names and verify list search/filtering distinguishes them; exact duplicates should either be allowed intentionally or rejected clearly |
| Dates | End date before start date; due date before invoice date; service period outside contract; period-locked journal date; DST/timezone boundary time entry |
| Amount precision | Zero amount, negative amount, extra decimal precision, very large amount, tax rounding residual, invoice/bill total recomputation |
| Currency | USD base plus at least one GBP/SGD/INR/AUD scenario; unsupported currency rejection if a free-text field exists; same-currency payment batch guard |
| Billing models | T&M, fixed fee, retainer, retainer draw/floor, milestone, capped T&M, mixed fixed plus T&M, per-unit payroll if UI exposes it |
| Caps and budgets | Capped T&M over cap, budget hours overrun, low-margin project, missing rate, inactive service |
| Approvals | Submitted/approved/rejected lifecycle; reject with blank reason; double-click approval; stale page approval after another user acted |
| Role access | Owner allowed, manager partially allowed, staff/viewer blocked; direct URL access fails without exposing data |
| Tenant isolation | Two tenants with similarly named customers; no cross-tenant list/detail visibility |
| Public access | Public invoice works without auth; authenticated app remains guarded; invalid public token shows a controlled error |
| Documents and AI | Valid upload, unsupported file type, extracted draft edit, low confidence, prompt injection, reject correction logged |
| P2P matching | Exact PO match, quantity mismatch, price mismatch, missing PO, duplicate vendor invoice number, prepaid/service-period bill |
| Payments | Partial payment, overpayment, duplicate payment attempt, settlement reversal if exposed, paid item excluded from aging |
| Journals/R2R | Balanced manual journal with business reason accepted, imbalanced blocked, recurring template generated, close task waived with reason, close package loads, period lock readiness guard, journal audit event visible |
| Reports | Empty state, data state, refresh, period selector, tab switch, no stale skeletons, no console/API 500s |
| Resilience | Browser refresh on detail pages, back/forward navigation, long names, long notes, narrow/mobile viewport for primary forms |

## Scenario 1 - Multi-Year Managed Accounting Retainer

Customer: Northstar Robotics Inc.

Commercial model:
- Service line: Managed Accounting.
- Contract: 24-month retainer.
- Billing: monthly base retainer, $12,000/month.
- Delivery team: Elena Garcia, Nina Patel.

Browser steps:
1. `/app/clients`: create customer `Launch QA 20260624 - Northstar Robotics Inc.`.
2. `/app/engagements`: create engagement `Northstar - Managed Accounting FY26-FY27`.
3. Select billing arrangement `retainer` or closest available monthly recurring option.
4. Set currency USD, value 288000, start date 2026-07-01, end date 2028-06-30 if the fields are available.
5. `/app/projects`: create project `Northstar - Monthly Close Operations`.
6. Assign/verify staff if assignment UI is available; otherwise note the UI gap.
7. `/app/time`: log 8.0 billable hours for Elena and 6.0 billable hours for Nina.
8. `/app/billing-runs`: run billing for the engagement.
9. `/app/invoices`: approve, send, and mark paid where the UI supports it.
10. `/app/reports`: verify Revenue, WIP, Project P&L, AR Aging, and Cash Flow reflect the activity.

Expected result:
- Engagement and project are visible.
- Time entries are visible and unbilled before billing.
- Billing creates a draft invoice or an actionable billing run.
- Invoice lifecycle can move through approval/send/payment.
- Reports refresh without console or API errors.

Additional checks:
- Retainer configuration: verify monthly amount, start/end dates, currency, service line, and customer are visible after save and after browser refresh.
- WIP behavior: before the billing run, verify logged time appears in Time Entries and WIP but the retainer invoice amount remains the contracted retainer amount.
- Billing recurrence: if the UI exposes billing period/month selection, run only July 2026 and confirm a second run for the same period is blocked or idempotent.
- Non-billable time: add a 1.0 hour internal admin entry to the project and verify it does not increase invoice total.
- Role check: log in as Staff Consultant and verify invoice approval/send controls are unavailable.
- Edge case: attempt a retainer with zero monthly amount or end date before start date; submit must be blocked or show a clear error.
- Evidence: contact detail, engagement detail, project list/detail, time entry row, billing run/invoice detail, AR Aging before payment, AR Aging after payment, WIP after billing.

## Scenario 2 - Multi-Year ERP Implementation With Milestones

Customer: BluePeak Manufacturing Group.

Commercial model:
- Service line: ERP Implementation.
- Contract: 18-month program.
- Billing: milestone based.
- Total value: $450,000.
- Milestones: Design $90,000, Build $180,000, UAT $90,000, Go-live $90,000.
- Delivery team: Priya Shah, Daniel Brooks, Nina Patel.

Browser steps:
1. `/app/clients`: create customer `Launch QA 20260624 - BluePeak Manufacturing Group`.
2. `/app/engagements`: create `BluePeak - ERP Transformation Program`.
3. Select billing arrangement `milestone` or closest available milestone/fixed arrangement.
4. Enter total value 450000 and dates if supported.
5. `/app/projects`: create `BluePeak - ERP Phase 1 Design` and `BluePeak - ERP Phase 2 Build`.
6. If project phase/deliverable controls are visible, create the four milestones and mark Design complete.
7. `/app/time`: log design/build time for Priya, Daniel, and Nina.
8. `/app/billing-runs` or engagement detail: draft an invoice for the completed Design milestone.
9. Approve and send the invoice.
10. `/app/reports`: verify project health, capacity planning, revenue, and project P&L show BluePeak.

Expected result:
- Milestone or fixed-fee billing can be configured from the UI.
- Completed milestone can be billed without backend setup.
- Reports expose the project and revenue impact.

Additional checks:
- Milestone detail: verify each milestone has name, amount, due date, status, and engagement/project linkage after refresh.
- Partial completion: mark Design complete and leave Build/UAT/Go-live open; only Design should be billable.
- Backlog: confirm remaining milestone value appears in Backlog and does not appear as invoiced revenue until billed.
- Capacity stress: assign Priya and Nina enough planned/logged hours to trigger a capacity or project-health warning if thresholds support it.
- Edge case: try to bill an incomplete milestone; UI should block it or require explicit override.
- Edge case: create a milestone total that does not equal the engagement contract value; product should either reconcile visibly or warn.
- Evidence: milestone panel, draft invoice lines, sent invoice detail, Project Health risk drivers, Capacity row for assigned staff, Backlog tab.

## Scenario 3 - One-Time CFO Advisory Capped T&M

Customer: Greenfield Health Partners.

Commercial model:
- Service line: CFO Advisory.
- Contract: 12-week board reporting advisory.
- Billing: capped T&M.
- Cap: $75,000.
- Rates: Daniel $300/hr, Nina $145/hr.

Browser steps:
1. Create customer `Launch QA 20260624 - Greenfield Health Partners`.
2. Create engagement `Greenfield - Board Reporting Advisory`.
3. Select capped T&M if available; otherwise use T&M and record a gap for cap configuration.
4. Create project `Greenfield - KPI Dashboard Build`.
5. Log time for Daniel and Nina.
6. Draft invoice from engagement detail or billing runs.
7. Verify invoice includes time lines and cap adjustment if the cap is exceeded.
8. Approve/send invoice.
9. `/app/reports`: verify WIP, utilization, and project P&L.

Expected result:
- Capped T&M terms can be entered or an explicit UI gap is recorded.
- Invoice does not exceed the configured cap when cap configuration is available.

Additional checks:
- Cap enforcement: log enough hours to exceed $75,000 and verify the invoice caps, discounts, or warns according to product design.
- Scope advisor: verify Scope Advisor or Project Health explains over-cap exposure and recommended action.
- Rate source: verify Daniel and Nina rates are pulled from People/service/project setup or can be overridden visibly.
- Approval gate: submit time for approval, reject one line with a reason, correct/resubmit it, and confirm only approved time enters billing if the UI supports approval status.
- Edge case: attempt a negative or >24 hour time entry; UI must block it.
- Edge case: missing project or customer on time/invoice must be blocked before billing.
- Evidence: time entries before approval, approval queue, capped invoice lines, WIP before/after invoice, Scope Advisor/Project Health warning.

## Scenario 4 - One-Time Tax Compliance Fixed Fee

Customer: Harbor Foods LLC.

Commercial model:
- Service line: Tax & Compliance.
- Contract: one-time corporate tax compliance.
- Billing: fixed fee, $18,000.
- Delivery team: Omar Khan, Nina Patel.

Browser steps:
1. Create customer `Launch QA 20260624 - Harbor Foods LLC`.
2. Create engagement `Harbor Foods - 2026 Corporate Tax Compliance`.
3. Select fixed fee and total value 18000.
4. Create project `Harbor Foods - Tax Workpapers`.
5. Log non-billable internal review time and billable preparation time.
6. Draft fixed-fee invoice.
7. Approve/send/mark paid.
8. Verify Revenue, AR Aging, Cash Flow, and Income Statement.

Expected result:
- Fixed-fee billing works without time-line dependency.
- Non-billable time remains visible but does not invoice.

Additional checks:
- Tax rate: apply a configured tax rate if the invoice UI exposes it; verify tax amount, invoice total, and statutory tax bucket.
- Fixed-fee independence: create the fixed-fee invoice before logging time, then log workpapers time and verify invoice amount does not change unexpectedly.
- Margin: verify Project P&L reflects labor cost even when billing is fixed-fee.
- Edge case: attempt a fixed-fee invoice with zero/negative line or invalid tax rate; UI must reject or show controlled error.
- Edge case: mark invoice paid twice or enter an overpayment if the UI exposes manual payment amount; duplicate/overpayment must be blocked or explicitly accounted for.
- Evidence: fixed-fee engagement setup, invoice detail with tax, payment state, Revenue, AR Aging, Cash Flow, Income Statement, Statutory Pack tax controls.

## Scenario 5 - IT Infrastructure Procurement

Vendor: CloudCore Systems.

Procurement need:
- 20 laptops and network equipment for consultants.
- Purchase order: $42,000 plus tax.
- Buyer: AP Lead.

Browser steps:
1. `/app/clients`: create vendor `Launch QA 20260624 - CloudCore Systems`.
2. Open the vendor detail page and complete vendor onboarding controls where available.
3. `/app/bills`: click New Procurement.
4. Create a purchase order for `Consultant laptops and network equipment`.
5. Add line 1: 20 laptops at 1800 each.
6. Add line 2: network equipment at 6000.
7. Approve the procurement document from the Bills page if approval controls are visible.
8. Create a vendor bill linked to the approved purchase order.
9. Verify PO match status is matched.
10. Approve the bill.

Expected result:
- Vendor onboarding can be completed from the browser.
- Purchase order, approval, bill linkage, and PO match are visible.
- Over-tolerance or mismatch blocks AP approval if tested with a mismatched bill.

Additional checks:
- Vendor controls: verify bank account, tax validation, sanctions/remittance, onboarding status, and vendor filter where those controls are visible.
- Purchase order lifecycle: draft, approve, bill-link, and matched status must be visible from the Bills list and bill/procurement detail.
- Match exception: create or attempt a bill for 21 laptops or a different unit price; the UI must flag quantity/price mismatch before approval.
- Tax and capitalization: apply input tax if supported; code one line as equipment/capital asset or IT expense where account coding is exposed.
- Duplicate vendor invoice: attempt a second bill with the same vendor invoice number; product should block or warn.
- Role check: AP Lead can work bill queue; Staff Consultant and Viewer cannot approve.
- Evidence: vendor detail onboarding, PO/service document, matched bill detail, mismatch error, AP Aging before payment, audit/status history if exposed.

## Scenario 6 - Contractor Resource Service Order

Vendor: Apex Contractor Network.

Procurement need:
- Two ERP contractors for BluePeak implementation.
- Service order: 320 hours at $115/hr, $36,800.
- Service period: 2026-07-01 to 2026-09-30.

Browser steps:
1. Create vendor `Launch QA 20260624 - Apex Contractor Network`.
2. Complete vendor onboarding controls.
3. `/app/bills`: click New Procurement.
4. Choose service order.
5. Set service dates and line: `ERP implementation contractors`, quantity 320, unit price 115.
6. Approve the service order.
7. Create a vendor bill linked to the service order.
8. Approve the bill.
9. `/app/reports`: verify AP Aging and Project P&L include contractor cost where coding is available.

Expected result:
- Service-order setup is browser-configurable.
- Service-period metadata is captured.
- Vendor bill can link to the service order.

Additional checks:
- Project coding: code contractor cost to the BluePeak ERP project where available; verify Project P&L margin includes vendor cost.
- Service period: verify start/end service dates persist after refresh and appear on bill detail or reports if exposed.
- Accrual/prepaid logic: if service dates cross month end, verify close proposals detect expense accrual or prepaid amortization as appropriate.
- Match exception: bill 400 hours against a 320-hour service order; approval should be blocked or show an over-tolerance warning.
- Edge case: service end date before start date must be blocked.
- Evidence: service order detail, linked bill, AP Aging, Project P&L vendor-cost row, close proposal result.

## Scenario 7 - Bill Payment Batch And Settlement

Vendors: CloudCore Systems and Apex Contractor Network.

Browser steps:
1. Ensure Scenarios 5 and 6 have approved bills.
2. `/app/billing-runs`: open Pay Bills.
3. Select both approved bills.
4. Enter pay date and payment method/export option.
5. Create payment batch.
6. Approve or send/export the batch as the UI allows.
7. Mark payment sent/settled where available.
8. `/app/bills`: verify bill statuses update.
9. `/app/reports`: verify AP Aging no longer shows settled bills.

Expected result:
- Approved bills can be batched from the browser.
- Payment controls show appropriate review/export/send/settlement state.
- AP Aging changes after settlement.

Additional checks:
- Eligibility: draft/unapproved bills must not be selectable for payment.
- Currency guard: attempt to select bills in different currencies if data exists; UI must block mixed-currency batch or split it clearly.
- Partial selection: pay CloudCore only, verify Apex remains open in AP Aging, then pay Apex.
- Duplicate settlement: refresh after settlement and verify the same bill cannot be paid again.
- Export/send artifact: if a payment file or send/export action exists, verify it produces success state and no console/API failure.
- Evidence: pay-bills selection grid, batch confirmation, settled statuses on bills, AP Aging before/after, Cash Flow operating outflow.

## Scenario 8 - Month-End Close

Period: the current month shown in the Accounting Close panel.

Transactions sourced from:
- Customer invoices and payments from Scenarios 1-4.
- Vendor bills and payments from Scenarios 5-7.
- Manual journals for payroll accrual or depreciation if needed.

Browser steps:
1. `/app/accounting/journals`: verify Journal Entries page loads.
2. Post a balanced manual journal:
   - DR Payroll Expense 15000
   - CR Accrued Payroll 15000
   - Business reason: "Accrue approved payroll register for current-month close."
3. Bootstrap close tasks for the period.
4. Request WIP accrual, deferred revenue, prepaid amortization, and recurring journal proposals if buttons are available.
5. `/app/inbox`: approve generated review tasks that are appropriate.
6. Return to `/app/accounting/journals`.
7. Mark close tasks done or waived with reasons where applicable.
8. Load close package.
9. Attempt period lock only after readiness is green.

Expected result:
- Manual journal posts only when balanced and a business reason of at least 10 characters is provided.
- Posted manual journal detail shows the business reason and the immutable event log contains `manual_journal.posted` metadata with the same reason, actor, line count, and debit total.
- Close tasks can be bootstrapped and updated from the browser.
- Agent proposals route through Inbox review before posting.
- Close package renders and period lock is guarded by readiness checks.

Additional checks:
- Imbalanced rejection: attempt DR 15000 / CR 14000; UI must block or API error must be user-visible and non-500.
- Missing reason rejection: attempt to post a balanced manual journal without a business reason; UI or API must reject it with a clear validation message.
- Recurring template: create a monthly depreciation or rent accrual template, request recurring-journal proposal, and verify generated task/proposal.
- Close proposals: run WIP accrual, expense accrual, deferred revenue release, milestone recognition, percentage-completion recognition, prepaid amortization, and recurring journals where buttons are available.
- HITL path: approve one generated proposal, reject one generated proposal, and verify Inbox/action queue status changes.
- Waiver governance: waive a close task with a reason and verify the reason persists after refresh.
- Period lock guard: attempt to lock or finalize before all required tasks are done; product should block with readiness explanation.
- Evidence: balanced posted journal, imbalanced error, recurring template, close checklist, proposal task in Inbox, close package, Action Queue close items.

## Scenario 9 - Quarter Close And Financial Statements

Period: quarter ending 2026-09.

Browser steps:
1. Run the Month-End Close script for each month in the quarter where practical.
2. `/app/reports`: set statement period to the quarter or latest available period.
3. Open these tabs:
   - Trial Balance
   - Balance Sheet
   - Income Statement
   - Cash Flow
   - Retained Earnings
   - Statutory Pack
4. Verify Balance Sheet balances.
5. Verify Cash Flow changes after paid invoices and paid vendor bills.
6. Verify Income Statement includes revenue, labor/vendor expenses, and net income.
7. Verify tax buckets/statutory pack render.

Expected result:
- All statement tabs load from the browser without backend intervention.
- Statements are based on posted journal lines.
- Trial Balance and Balance Sheet balance.

Additional checks:
- Tie-out: Trial Balance total debits equal credits; Balance Sheet total assets equal liabilities plus equity.
- Statement logic: invoice revenue appears in Income Statement; paid invoices and settled vendor bills affect Cash Flow; unpaid AR/AP stays on Balance Sheet.
- Retained earnings: current period net income flows to retained earnings view.
- Tax: output tax from customer invoice and input tax from vendor bill appear in Statutory Pack if tax was configured.
- Period selector: change period/month/quarter if controls exist and confirm data refreshes instead of showing stale values.
- Edge case: open statements before any activity in a fresh tenant; all tabs must show controlled empty states.
- Evidence: Trial Balance, Balance Sheet balanced status, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, period selector state.

## Scenario 10 - Management Reporting And Action Queues

Audience: owner, engagement manager, AP lead, controller.

Browser steps:
1. `/app/reports`: open Management Summary if visible; otherwise use Revenue, Project P&L, Project Health, Capacity Planning, Action Queue, AR Aging, AP Aging, WIP, and Utilization tabs.
2. Review each customer:
   - Northstar: recurring revenue and close operations.
   - BluePeak: multi-year implementation margin and capacity.
   - Greenfield: capped T&M margin and WIP exposure.
   - Harbor Foods: fixed-fee profitability.
3. Open Action Queue as all work.
4. Toggle Assigned to me.
5. Verify overdue/due-soon SLA chips and owners where tasks exist.
6. `/app/settings`: open Agent Run Ledger and Workflow Runs.
7. Verify recent workflow runs show success/skipped/waiting-on-human states.

Expected result:
- Role-oriented report tabs are visible and stable.
- Action queues distinguish all work from assigned-to-me work.
- Workflow run telemetry is visible without backend lookup.

Additional checks:
- Recommendation quality: every recommendation/risk driver should name the project/client/metric causing it and give an action a user can take.
- Action Queue scope: verify all-work vs assigned-to-me counts change by role and do not expose unauthorized work to restricted users.
- Agent controls: disable an agent, change its autonomy level, cancel the confirmation modal, then perform a real change and verify persistence after refresh.
- Agent run ledger: filter by agent/status, open a run, inspect tool invocations, run replay preview/validation where data exists.
- Workflow runs: filter by workflow/status, expand a waiting-on-human workflow, and verify the linked Inbox task or route context.
- Empty state: in a new tenant or filtered view with no records, dashboards must show clear empty states rather than failed tables.
- Evidence: management/recommendation tabs, Action Queue all/me, autonomy table before/after, agent run detail, workflow run expansion, no-console-error log.

## AI Finance Ops Manager Scenarios

These scenarios extend the launch pass for the intended agentic operating model:
an AI Finance Ops Manager coordinates finance work across billing, AP, close,
reporting, collections, document intake, and controls. Human users approve
financially sensitive transitions through Inbox when the action changes money,
accounting, external communications, or governance state.

Recommended product language: use `AI Finance Ops Manager` for the consolidated
role. The product can still expose specialist agents internally, but the user
experience should feel like one finance-operations manager assigning work to
AI specialists and routing approvals to the right human.

Prompt examples: see `docs/copilot/prompt-library.md` for user-facing Copilot
prompts. The examples intentionally avoid internal tool names; Copilot should
infer the right tool from the business request.

User and QA guides:

- Platform guide: `docs/user-guide/platform-user-guide.md`
- Enterprise E2E scenario library: `docs/qa/enterprise-e2e-scenario-library.md`

Current implementation assessment:

| Capability | Current implementation | Product gap | Tracking |
| --- | --- | --- | --- |
| Copilot reads finance data and logs time | Implemented with read tools, time logging, rate updates, policy/HITL, and #265 command-center synthesis/live E2E coverage | Manager-level action planning is covered separately by #272; specialist execution remains approval-gated | #265 |
| AI command-center action plan | Implemented in #272, #274, and #276: Copilot turns the daily finance-ops check into a reviewable Inbox action plan; approval fans out child Inbox work items, and Plan Item approval dispatches mapped specialist workflows such as collections, bill-pay, and close prep through their existing HITL gates | Invoices, payments, journals, statements, and emails still require specialist approvals before final execution | #272, #274, #276 |
| Scheduled AI Finance Ops Manager | Implemented first slices in #283 and #295, then automated in #317: tenant cadence can be configured through Settings or the Agents API, the hourly worker creates a traceable `scheduled_finance_ops_manager` workflow run, routes a scheduled action plan to Inbox, suppresses duplicate open plans for the same cadence window, and creates separate escalation notices for stale/high-risk Inbox work | Scheduled execution still stops at reviewed plans/escalation notices; live worker cadence smoke remains environment evidence | #283, #295, #317 |
| AI invoice drafting from Copilot | Implemented and browser-verified: Copilot drafts invoice lines, creates an Inbox review task, and materialises the reviewed payload as a draft invoice | Keep invoice approval, send, and payment as separate guarded flows | #263 |
| AI bill-pay run | Implemented and browser-verified: Copilot proposes approved-bill payment batches through Inbox, then approval materialises a draft payment batch. #325 exposes the downstream Pay Bills lifecycle: draft batch approval, CSV/NACHA export state, mark-sent, and settlement confirmation with returned journal evidence | Native bank-provider submission remains future payment depth; current export uses operator-controlled files and explicit settlement confirmation | #262, #325 |
| AI month-end/year-end close controller | Implemented and browser-verified in #260, then hardened in #285/#300 and automated in #310: Copilot routes close preparation to Inbox, approval runs the close workflow and bootstraps close tasks, close packages include AR/AP/WIP/GL/approval readiness evidence, period lock can only bypass blockers through recorded reasoned overrides, and the Accounting close panel can record named override reasons. #327 adds the controller-facing year-end close posting action, #329 adds Copilot `prepare_year_end_close` routing through Inbox before any retained-earnings journal is posted, and #333 adds manual-journal business reasons plus immutable `manual_journal.posted` evidence | Direct close locking and journal posting remain approval-gated; manual-journal threshold approval and native close calendar/workpaper orchestration remain future depth | #260, #285, #300, #310, #327, #329, #333 |
| AI financial statement package | Implemented and browser-verified in #261, then enriched in #300 and automated in #310: Copilot generates a read-only statement package summary from posted journal/report services with close-readiness warnings and evidence-backed management commentary, and browser proof ties the package to Reports tabs plus Agent Run Ledger evidence. #327 adds retained-earnings posting evidence for year-end statement tie-out, #329 adds current-vs-prior year commentary to the year-end close approval payload, and #331 adds comparative statement package variance commentary for default prior-period and explicit comparison windows | Board-pack export/PDF generation remains future reporting depth | #261, #300, #310, #327, #329, #331 |
| AI document intake | Implemented and browser-verified for vendor invoice upload to Inbox approval to bill creation with source-document linkage | AI semantic PO selection and project coding from source documents remain broader P2P coverage | #264 |
| AI vendor invoice exceptions | Implemented first slices in #284/#299 and automated in #310: extraction payloads include vendor match status, GL coding suggestions, review exceptions, duplicate guard metadata, project/customer hints, and source document linkage; Inbox and Bill detail surface AP review evidence, duplicate invoice approval requires a reviewer-entered reason, and approval uses the Bills service path to create reviewed bill lines with `vendor_invoice_review` evidence. #323 adds line-level PO/service-order match evidence: linked bills compare bill lines to approved PO/SO lines for description, quantity, unit price, amount, and service period where applicable; mismatches record `line_exceptions`, show in Bills list/detail, and block approval through the existing AP gate | Payment remains a separate bill-pay approval flow; fuzzy/semantic AI PO selection remains future P2P depth | #284, #299, #310, #323 |
| AI engagement-letter onboarding | Implemented and browser-verified in #267: Copilot upload classifies engagement letters/SOWs, creates `create_engagement_draft` Inbox tasks with client, engagement, billing terms, rates, dates, and first project, then approval materialises customer, draft engagement, and first project records | Automatic rate-card creation from extracted hints remains future depth; reviewed commercial terms are preserved in the Inbox payload | #267 |
| AI collections | Implemented and browser-verified in #266: Copilot drafts overdue-invoice reminder payloads, routes `collections_agent/send_email` tasks to Inbox, approval materialises through the email path, and rejection records audit feedback | Production email-provider credentials remain an environment validation outside the non-deliverable QA recipient domain | #266 |
| Enterprise approval policy | Implemented first slices in #280 and #296, then automated in #309: Inbox exposes required Owner/Admin/Manager approval role, the API enforces the same policy including approve-with-edits re-evaluation, Settings lets Admin/Owner users raise tenant approval roles, and browser proof verifies owner-threshold routing plus disabled under-privileged approval | Deeper finance-role taxonomy remains future enterprise controls | #280, #296, #309 |
| Enterprise decision audit | Implemented first slices in #281 and #297, then automated in #309: Inbox approve, approve-with-edits, reject, and approval-denial paths append immutable `financial_events`; Inbox Done/All status views show recent decision history; materialized business records and source documents expose record-scoped decision timelines; browser proof verifies Inbox Done history and Bill detail decision evidence | Rejection/document timeline browser depth remains future coverage | #281, #297, #309 |
| Enterprise RBAC permission proof | Implemented first slices in #282 and #298, automated in #309, then expanded in #321: current enterprise personas map to owner/admin/manager/member/viewer/employee, Settings exposes a viewer-readable Finance role personas catalog, API/unit tests prove the catalog does not add permissions, browser proof verifies Owner/Admin, Manager, and Viewer paths across Settings, Inbox, and Bill detail, and the full persona matrix verifies Owner/Admin, Controller, AP Lead, AR Lead, Auditor, and Executive route/action expectations | Dedicated finance-role enum assignment remains future enterprise controls depth | #282, #298, #309, #321 |
| Enterprise ops hardening | Implemented first slices in #286 and #301, then automated in #311: signup and public invoice token reads have app-level rate limits with safe 429 responses, request failures are counted by sanitized path/status, tenant health exposes runtime/table/agent/tool/workflow failure signals without secrets, Supabase-backed distributed limiting is available with hashed subjects and fallback/deny-safe behavior, Settings exposes Operational Health, and tenant health routes degraded/abuse/background/agent failure alerts to webhook metadata or the runbook queue | Deployed Supabase smoke validation remains environment evidence; deterministic browser/API proof is automated | #286, #301, #311 |

## Scenario 11 - AI Finance Department Command Center

Persona: Maya Rao, Owner/Admin. AI role: Finance Ops Manager.

Browser steps:
1. `/app/copilot`: start a new chat.
2. Ask: `Run today's finance ops check for Launch QA 20260624. Tell me what needs billing, payment, collections, close, and review.`
3. Verify Copilot uses live data, not invented values, for AR, AP, WIP, action queue, close readiness, and agent run status where available.
4. Ask Copilot to create the next recommended work items.
5. `/app/inbox`: verify sensitive actions appear as review tasks instead of silently changing invoices, bills, journals, emails, or payments.
6. `/app/settings`: open Agent Run Ledger and verify Copilot tool invocations are recorded with risk class, status, duration, and payload summary.

Expected result:
- Copilot behaves as the consolidated finance-ops manager, not a passive Q&A bot.
- Read-only analysis can execute directly.
- Money/accounting/external-send actions route to Inbox.
- The run ledger proves which tools ran and why review was required.

Implementation status:
- Implemented under #265, #272, #274, #276, and #283, with scheduled-manager browser proof automated in #317. The read-only daily command-center synthesis covers AR, AP, WIP, close readiness, action queue, and agent/workflow status. The follow-up action-plan workflow turns those findings into a `copilot_create_finance_ops_action_plan` Inbox task. Approval creates `finance_ops_action_item` child Inbox tasks for each review-required recommendation, and Plan Item approval dispatches the mapped specialist workflow without directly approving invoices, payments, journals, statements, or emails. Scheduled runs now create the same reviewed parent plan through the hourly Finance Ops Manager worker and record `scheduled_finance_ops_manager` workflow telemetry.

Automation:
```bash
cd frontend && npx playwright test e2e/enterprise-scheduled-finance-ops.spec.ts --project=chromium
```

Evidence: Copilot response, Inbox tasks, Agent Run Ledger detail, no console/API errors.

## Scenario 12 - AI Client Onboarding From Engagement Letter

Persona: Engagement Manager. AI role: Finance Ops Manager with engagement-letter specialist.

Browser steps:
1. `/app/copilot`: upload a new SOW or engagement letter for `Launch QA 20260624 - AI Onboarding`.
2. Ask Copilot: `Review this SOW, create the client, engagement, billing terms, and first project. Send anything risky to Inbox.`
3. `/app/inbox`: review the extracted customer, engagement, billing arrangement, dates, rates, and project proposal.
4. Approve with edits where required.
5. `/app/clients`, `/app/engagements`, `/app/projects`: verify records were created from the reviewed payload.
6. `/app/documents`: verify the source document links back to the created records where supported.

Expected result:
- AI extracts the engagement structure from the document.
- Humans review extracted commercial terms before records are created.
- The source document remains traceable.

Implementation status:
- Implemented and browser-verified under #267. Copilot upload classifies SOW/engagement-letter documents separately from vendor invoices, the extraction worker creates a `create_engagement_draft` Inbox task with the proposed client, engagement, billing arrangement, dates, rates/fees, and first project, and Inbox approval or approve-with-edits materialises customer, draft engagement, and first project records. The engagement stores source-document linkage where supported.

Evidence: upload state, Inbox detail, created engagement/project, document source linkage.

## Scenario 13 - AI Drafts Customer Invoice

Persona: Controller or Owner/Admin. AI role: Finance Ops Manager with invoice drafter.

Browser steps:
1. Ensure a customer engagement has billing terms plus invoiceable time, expenses, retainers, milestones, or fixed-fee terms.
2. `/app/copilot`: ask `Draft the June invoice for Launch QA 20260624 - Northstar Managed Accounting.`
3. Verify Copilot creates an Inbox review task instead of directly creating an approved/sent invoice.
4. `/app/inbox`: open the task and verify engagement, period, line count, subtotal, tax, total, and supporting line details.
5. Approve the task.
6. `/app/invoices`: verify a draft invoice exists with matching lines and totals.
7. Continue the normal invoice approval/send/payment flow from the invoice page.

Expected result:
- AI does the invoice calculation and line preparation.
- Inbox approval materialises only a draft invoice.
- Invoice approval/send/payment stay separate.

Implementation status:
- Implemented and browser-verified under #263. Live evidence covers Copilot prompt, Inbox approval, and draft invoice visibility.

Evidence: Copilot chat, Inbox review payload, draft invoice detail, AR/WIP report effect.

## Scenario 14 - AI Vendor Invoice Processing

Persona: AP Lead. AI role: Finance Ops Manager with vendor invoice specialist.

Browser steps:
1. `/app/copilot`: upload a vendor invoice PDF for a known vendor and project.
2. Ask: `Process this vendor invoice, match it to the right PO or service order, code it to the project, and send exceptions to Inbox.`
3. `/app/inbox`: verify extracted vendor, invoice number, service period, amount, tax, project/account coding, and match status.
4. Approve a clean bill and reject or edit a mismatch.
5. `/app/bills`: verify approved payload created a bill and duplicate invoice numbers are blocked or warned.
6. `/app/reports`: verify AP Aging and Project P&L update.

Expected result:
- AI extracts and codes the bill.
- Match exceptions require human approval or correction.
- Approved bills are visible for payment selection.

Implementation status:
- Exception-review and line-match slices implemented. Vendor invoice extraction, bill materialisation, Inbox AP review evidence, duplicate reason capture, Bill detail review evidence, and line-level PO/service-order match evidence exist.
- Browser-verified under #264 for Copilot upload, extraction status, Inbox approval, and bill creation with source-document traceability.
- Browser automation added under #310 for business-language Copilot prompting,
  duplicate/mismatch edit approval, Bill detail evidence, and separate bill-pay
  proposal review. #323 adds API/browser proof for line-level PO/SO match
  exceptions and approval blocking.

Automation:
```bash
cd frontend && npx playwright test e2e/enterprise-ai-finance-workflows.spec.ts --project=chromium
cd frontend && npx playwright test e2e/enterprise-p2p-line-match-evidence.spec.ts --project=chromium
```

Evidence: upload, Inbox review, bill detail, AP Aging/Project P&L.

## Scenario 15 - AI Bill-Pay Run

Persona: Controller or AP Lead. AI role: Finance Ops Manager with bill-pay specialist.

Browser steps:
1. Ensure multiple approved unpaid bills exist.
2. `/app/copilot`: ask `Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, and send the batch to Inbox.`
3. Verify Copilot proposes the payment batch, pay date, eligible bills, excluded bills, total, currency, and rationale.
4. `/app/inbox`: approve the proposed batch.
5. `/app/billing-runs` or Pay Bills route: verify the batch exists and can follow export/send/settlement controls.
6. `/app/reports`: verify AP Aging and Cash Flow after settlement.

Expected result:
- AI prepares the batch and explains eligibility.
- Human approval creates the batch.
- Export/send/settlement remain explicit downstream state changes.

Implementation status:
- Implemented and browser-verified under #262. Live evidence covers Copilot proposal, Inbox approval, draft payment batch creation, and Pay Bills UI visibility.
- Browser automation under #310 covers an AI bill-pay proposal as a separate
  reviewed Inbox decision after vendor invoice bill creation.
- #325 adds Pay Bills lifecycle proof for approved-bill response normalization,
  explicit batch approval, CSV/NACHA export state, mark-sent, and settlement
  confirmation with journal evidence.

Automation:
```bash
cd frontend && npx playwright test e2e/enterprise-bill-pay-lifecycle.spec.ts --project=chromium
```

Evidence: Copilot proposal, Inbox task, payment batch approval, export state,
sent-to-bank state, settlement result, AP Aging before/after.

## Scenario 16 - AI Month-End Close Controller

Persona: Controller. AI role: Finance Ops Manager with accounting specialists.

Browser steps:
1. `/app/copilot`: ask `Run month-end close readiness for the current period. Prepare WIP, expense accrual, deferred revenue, prepaid amortization, recurring journal, and revenue recognition proposals where needed.`
2. Verify Copilot summarizes readiness blockers, missing approvals, unposted journals, open AR/AP, and proposed journals.
3. `/app/inbox`: approve one generated journal proposal, reject one, and edit one if available.
4. `/app/accounting/journals`: verify approved proposals post balanced journals only.
5. Return to Copilot and ask for the remaining close blockers.
6. Load the close package and attempt period lock only when readiness is green.

Expected result:
- AI coordinates close tasks and proposals.
- All accounting postings remain balanced and review-gated.
- Close readiness updates after approvals/rejections.

Implementation status:
- Implemented and browser-verified under #260. Live evidence covers Copilot close-prep request, Inbox approval, close-task bootstrap, and Accounting Journals close panel visibility.
- Browser automation under #310 covers business-language close preparation,
  close Inbox approval, close package evidence, override reason capture, and
  close approval timeline visibility.

Evidence: Copilot readiness summary, Inbox tasks, posted journal, close package, readiness/lock state.

## Scenario 17 - AI Collections Agent

Persona: Owner/Admin or Controller. AI role: Finance Ops Manager with collections specialist.

Browser steps:
1. Ensure at least one sent unpaid invoice is overdue.
2. `/app/copilot`: ask `Draft collections reminders for invoices more than 30 days overdue. Do not send without review.`
3. Verify Copilot identifies overdue invoices from AR Aging and drafts customer-specific reminder copy.
4. `/app/inbox`: approve one reminder and reject one reminder.
5. Verify approved reminders use the configured send-email materialisation path and rejected reminders do not send.
6. `/app/settings`: verify agent run/tool invocation status and any workflow waiting-on-human state.

Expected result:
- AI identifies overdue invoices and drafts reminders.
- Human approval gates external communications.
- Rejections are logged for learning/audit.

Implementation status:
- Implemented and browser-verified under #266. Copilot uses `draft_collection_reminders` to discover eligible overdue invoices, create one Inbox `send_email` task per reminder, and record collections-agent read/draft/send ledger steps. Approval materialises through the existing collections email path, with non-deliverable QA recipients recorded as skipped sends; rejection records the correction/audit signal.

Evidence: AR Aging, Inbox reminder, send status, ledger/workflow detail.

## Scenario 18 - AI Financial Statement Package

Persona: Owner/Admin and Controller. AI role: Finance Ops Manager with reporting specialist.

Browser steps:
1. Complete invoice, bill, payment, and close activity for the period.
2. `/app/copilot`: ask `Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and management commentary. Compare it to May 2026 and show the variances.`
3. Verify Copilot uses posted journal/report data and flags any missing close prerequisites.
4. For fiscal-year close validation, `/app/copilot`: ask `Prepare year-end close for fiscal year 2026. Check retained earnings setup, duplicate close risk, locked periods, P&L activity, and comparative statement movement. Route the posting to Inbox for approval.`
5. `/app/inbox`: inspect the `copilot_prepare_year_end_close` task and approve it as Admin/Owner.
6. `/app/accounting/journals`: verify a `YE-YYYY` retained-earnings journal appears.
7. `/app/reports`: cross-check each statement tab against Copilot's package summary.
8. Ask Copilot to explain material variances, open risks, and next actions.
9. Verify the package does not claim final/locked status unless the period is actually ready or locked.

Expected result:
- AI assembles and explains statements from real accounting data.
- The package is traceable to report tabs and posted journals.
- Year-end close posts a balanced retained-earnings journal when fiscal-year activity is ready.
- Missing close work is surfaced as blockers, not hidden.

Implementation status:
- Implemented and browser-verified under #261. Live evidence covers Copilot statement-package generation and Reports UI cross-checks for Balance Sheet, Income Statement, and Statutory Pack.
- Browser automation under #310 covers business-language statement commentary
  generation, Reports tab tie-out, and Agent Run Ledger tool evidence without
  requiring tool names in the user prompt.
- #327 adds year-end close retained-earnings posting through Accounting, with
  backend guardrails and browser proof in
  `frontend/e2e/enterprise-r2r-year-end-close.spec.ts`.
- #329 adds Copilot `prepare_year_end_close`, Inbox approval materialisation,
  Finance Ops Plan Item dispatch, and current-vs-prior year commentary in the
  year-end close review payload.
- #331 adds structured comparative statement package commentary for default
  prior-period and explicit comparison windows.

Evidence: Copilot package, report tabs, variance commentary, close readiness status.

## Scenario 19 - Finance Role Persona And Permission Proof

Persona: Owner/Admin, AP Lead, AR Lead, Controller, Auditor, and Executive.
AI role: Finance Ops Manager as access explainer only.

Browser steps:
1. `/app/settings`: open Approval Controls and verify the Finance role personas card shows the current enforced role.
2. As Owner/Admin, Manager, and Viewer sessions, verify compatible persona chips:
   Owner/Admin should include Owner/Admin, Controller, AP Lead, and AR Lead;
   Manager should include AP Lead and AR Lead; Viewer should include Auditor
   and Executive.
3. `/app/copilot`: ask `Show me which finance personas my current role maps to. Summarize what I can do in Inbox, Bills/AP, Invoices/AR, Reports, Accounting, and Settings, and which actions still need another approver.`
4. As Viewer, open Inbox, Bills/AP, Invoices/AR, Accounting, Reports, and Settings.
5. Attempt restricted finance actions: approve, edit, create, convert, post, pay,
   send, lock, and settings mutation.
6. Repeat direct API calls for the same restricted paths.

Expected result:
- Finance persona labels are understandable to users but remain mapped to the
  enforced backend role hierarchy.
- Viewer-backed Auditor and Executive personas can inspect permitted records and
  decision evidence but cannot mutate finance or settings state.
- Manager-backed AP/AR personas can prepare work and use manager-threshold flows
  without gaining admin/owner approval rights.
- Owner/Admin and Controller mappings keep final approval and settings authority
  behind the existing tenant role gates.

Implementation status:
- First slice implemented under #282 and #298, with browser/API proof added in
  #309 and full persona matrix browser proof added in #321. The backend exposes
  `GET /api/v1/tenants/finance-personas`, Settings renders the catalog under
  Approval Controls, component tests cover manager/viewer persona compatibility,
  backend tests prove viewer readability plus existing role mapping, and
  Playwright verifies Owner/Admin visibility, Manager owner-required approval
  denial, Viewer read-only Settings/Inbox/Bill-detail behavior, Inbox Done
  decision history, and Bill decision timeline evidence. The #321 matrix signs
  in as Owner/Admin, Controller, AP Lead, AR Lead, Auditor, and Executive through
  the current enforced-role compatibility model and verifies Settings, Inbox,
  Bills/AP, Invoices/AR, Accounting, Reports, and read-only mutation guards.

Automation:
```bash
cd frontend && npx playwright test e2e/enterprise-controls-audit-rbac.spec.ts --project=chromium
cd backend && uv run pytest tests/unit/test_approval_policy_api_contract.py tests/unit/test_inbox_api_contract.py tests/unit/test_financial_events_api_contract.py tests/unit/test_rbac.py -q
```

Evidence: Settings persona card, Copilot access explanation, disabled UI
controls, API 403 responses, no console/API errors.

## Enterprise Ops Automation - Distributed Limiter And Operational Health

Persona: Owner/Admin, Internal operator, Security reviewer.

Implementation status:
- Browser/API proof added under #311. Backend tests prove shared Supabase-style
  limiter state across simulated app instances, safe fallback telemetry, and
  deny-safe behavior when distributed fallback is disabled.
- Settings -> Operational Health browser automation verifies runtime, queue,
  table/migration, rate-limit, request/background failure,
  agent/tool/workflow failure, and routed-alert signals without exposing
  webhook URLs, raw invoice tokens, JWT-shaped values, API keys, document text,
  or request payloads.

Automation:
```bash
cd backend && uv run pytest tests/unit/test_ops_hardening.py -q
cd frontend && npx playwright test e2e/enterprise-ops-health.spec.ts --project=chromium
```

Evidence: safe 429/fallback contract, sanitized tenant health response, Settings
Operational Health panel, and routed alert rows.

## End-To-End Execution Schedule

Run the launch pass in this order so every scenario builds on earlier browser-entered data.

| Phase | Owner role | Work | Exit criteria |
| --- | --- | --- | --- |
| 0. Access baseline | Owner/Admin, Viewer | Login, auth guard, profile, guarded route redirects, empty-state scan | Valid users can enter app; anonymous users cannot; no broken shell routes |
| 1. Tenant configuration | Owner/Admin | Services, tax rates, autonomy baseline, people, contacts | All master data visible in list/detail pages after refresh |
| 2. O2C setup | Owner/Admin, Engagement Manager | Scenarios 1-4 customers, engagements, projects, time | Four customer contracts configured; time and approvals visible |
| 3. O2C billing | Owner/Admin, Controller | Scenarios 1-4 billing, invoice approval/send/payment/public invoice | Invoices lifecycle through paid or intentionally unpaid states |
| 4. P2P setup | AP Lead | Scenarios 5-6 vendors, onboarding, PO/service order, bills | Vendor controls and linked bills visible; mismatch cases logged |
| 5. P2P payments | AP Lead, Controller | Scenario 7 payment batches and settlement | AP Aging and Cash Flow reflect settlements |
| 6. R2R month close | Controller | Scenario 8 journals, proposals, Inbox, close package | Balanced journals and close tasks pass; imbalanced/early-lock cases blocked |
| 7. Quarter reporting | Controller, Owner/Admin | Scenario 9 statement tie-outs | Trial Balance and Balance Sheet balance; statements reflect O2C/P2P activity |
| 8. Management cockpit | Owner/Admin, Engagement Manager | Scenario 10 reports, action queue, agent telemetry | Reports explain risks; all/me queues and agent settings work |
| 9. RBAC and isolation | All roles | Scenario 19 finance persona catalog plus key create/approve/settings/report routes by role and tenant | Mutations allowed only by intended roles; no cross-tenant leakage |
| 10. Regression sweep | Owner/Admin | Refresh detail routes, narrow viewport, console/network review | No broken refresh, stuck loading state, console error, or API 500 remains |

## Browser Evidence Checklist

Capture evidence for the final launch packet:

- Route screenshots or Playwright traces for each scenario start, key action, and final report.
- Console/network log summary for each phase, including any ignored favicon/static-asset noise.
- Data tie-out notes for invoice totals, bill totals, payment status, WIP/revenue/AP/AR, and financial statements.
- Role matrix notes showing which buttons are hidden/disabled or which actions fail cleanly.
- GitHub issue URLs for every gap, with scenario number and route in the issue title.

## Existing Automated Coverage To Reuse

These tests can supplement the manual launch pass, but they do not replace browser-only scenario execution when they use API setup.

| Automated spec | Use in launch pass | Notes |
| --- | --- | --- |
| `frontend/e2e/demo-v2-full-scenario.spec.ts` | Primary browser walkthrough baseline | UI-driven engagement-to-cash demo; rerun after runbook updates |
| `frontend/e2e/timesheet-e2e.spec.ts` | Time, approvals, portal, billing gate supplement | Includes deeper time approval lifecycle; verify whether any API setup is used before counting as browser-only |
| `frontend/e2e/bills-list.spec.ts` | Bills render/filter supplement | Useful for P2P route regression |
| `frontend/e2e/p2p-vendor-bill.spec.ts` | P2P render supplement | Covers bills, expenses, pay-bills, Copilot upload entry points |
| `frontend/e2e/enterprise-scheduled-finance-ops.spec.ts` | #317 scheduled Finance Ops Manager proof | Covers Settings schedule save/read-only behavior, scheduled action-plan Inbox task, stale high-risk escalation notice, and `scheduled_finance_ops_manager` workflow telemetry |
| `frontend/e2e/enterprise-ai-finance-workflows.spec.ts` | #310 AI finance workflow proof | Covers business-language Copilot prompts, P2P AP exception review, duplicate reason approval, bill evidence, bill-pay proposal review, R2R close package/override, statement tabs, and Agent Run Ledger evidence |
| `frontend/e2e/enterprise-p2p-line-match-evidence.spec.ts` | #323 P2P line-match proof | Covers Bills list/detail PO/SO line exceptions for linked bills, including readable mismatch labels and line evidence |
| `frontend/e2e/enterprise-bill-pay-lifecycle.spec.ts` | #325 bill-pay lifecycle proof | Covers approved-bills response normalization, draft batch approval, CSV export, mark-sent, and settlement confirmation |
| `frontend/e2e/enterprise-r2r-year-end-close.spec.ts` | #327 R2R year-end close proof | Covers Accounting year-end close posting, retained-earnings evidence, and refreshed journal-list proof |
| Backend Copilot year-end close unit suite | #329 AI-routed year-end close proof | Covers `prepare_year_end_close` tool schema, accounting HITL routing, Inbox materialisation, Finance Ops Plan Item dispatch, preview blockers, and comparative statement commentary |
| Backend Copilot comparative statement unit suite | #331 comparative statement proof | Covers statement package comparison periods, default prior-window comparison, deterministic variances, and readable comparison input validation |
| `frontend/e2e/enterprise-ops-health.spec.ts` | #311 operational health proof | Covers Settings Operational Health runtime, table/migration, distributed limiter, request/background failure, agent/tool/workflow failure, routed alert, and secret-redaction evidence |
| `frontend/e2e/enterprise-finance-persona-matrix.spec.ts` | #321 full finance persona matrix proof | Covers Owner/Admin, Controller, AP Lead, AR Lead, Auditor, and Executive compatibility mappings plus Settings, Inbox, Bills/AP, Invoices/AR, Accounting, Reports, and viewer mutation guards |
| `frontend/e2e/accounting-journals.spec.ts` | Journal UI supplement | Covers page render and journal form basics |
| `frontend/e2e/r2r-reports-render.spec.ts` and `frontend/e2e/trial-balance.spec.ts` | Reports render supplement | Proves report tabs mount; business tie-outs still come from scenarios |
| `frontend/e2e/engagement-to-cash.spec.ts` | Deep API edge regression | Covers many edge cases, RBAC, FX, idempotency; mark as supplemental unless the step is browser-driven |
| `frontend/e2e/multi-tenant-isolation.spec.ts` | Isolation supplement | Use to confirm isolation in addition to manual tenant switch checks |
| `frontend/e2e/login.spec.ts`, `frontend/e2e/auth-guard.spec.ts`, `frontend/e2e/change-password.spec.ts` | Access supplement | Use for baseline auth/profile checks |
| `frontend/e2e/copilot-draft-invoice-live.spec.ts` | AI invoice drafting live proof | Uses Copilot chat, Inbox approval, and Invoices UI against the live QA tenant; supplemental to Scenario 13 browser evidence |
| `frontend/e2e/copilot-finance-ops-live.spec.ts` | AI finance-ops live proof | Uses Copilot chat/upload, Inbox approval, Plan Items fan-out, Pay Bills, Accounting Journals, Reports, Documents, Bills, Clients, Engagements, and Projects UI against the live QA tenant for Scenarios 11-18 |

## Verification Matrix

CI gate note for #319:

- If GitHub Actions jobs fail in 1-4 seconds with `steps: []`, no logs, and no
  runner assignment, follow
  [`docs/qa/github-actions-billing-runbook.md`](github-actions-billing-runbook.md).
  The observed #319 failure is a GitHub billing/spending-limit hold, not a
  workflow YAML failure. CI is not considered launch-trusted again until jobs
  produce normal checkout/setup/build/test logs.

Final verification on 2026-06-24:

- Primary UI launch walkthrough: `frontend/e2e/demo-v2-full-scenario.spec.ts` passed with `No gaps found` after fixes for contact profile fields, People classification fields, project budget/status entry, Copilot Log time quick action, manual journal account selection, and Trial Balance retry/active-tab checks.
- Full browser suite: `set -a && source ../.env && set +a && AETHOS_TS_WEB_URL=http://127.0.0.1:4202 npx playwright test --project=chromium --reporter=list` passed `122 passed (11.7m)`.
- Backend suite: `uv run pytest` passed `800 passed, 214 skipped, 56 xfailed`.
- Backend lint: `uv run ruff check .` passed.
- Main frontend production build: `npm run build` passed with existing Angular optional-chain, Sass deprecation, and bundle budget warnings.
- Timesheet production build: `npx ng build timesheet` passed with existing Sass deprecation warnings.
- Original launch-gap issue scan before the AI finance-ops expansion returned no open issues. The AI expansion added #258-#264 to track the new agentic finance-department scenarios, implementation slices, and browser QA.
- AI invoice live proof: `CI=1 AETHOS_PS_WEB_URL=http://localhost:4201 AETHOS_PS_API_URL=http://localhost:8011 npx playwright test e2e/copilot-draft-invoice-live.spec.ts --project=chromium --reporter=list` passed after the Copilot draft-invoice implementation.
- AI finance-ops live proof: `AETHOS_PS_WEB_URL=http://localhost:4201 AETHOS_PS_API_URL=http://localhost:8011 npx playwright test e2e/copilot-finance-ops-live.spec.ts --project=chromium --reporter=list` passed `9 passed (3.2m)`, including #272 command-center action-plan orchestration, #274 Plan Items fan-out, #276 Plan Item dispatch, and #267 engagement-letter onboarding. Focused #276 Plan Item dispatch proof also passed with `--grep "action plan"` (`2 passed`), verifying parent approval creates child Inbox tasks and AR Plan Item approval creates downstream collections `send_email` review tasks.
- QA database schema was brought current through Supabase migrations `0065`-`0083`; migrations `0068`, `0075`, and `0076` were aligned to the existing `public.is_tenant_member(auth.uid(), tenant_id)` RLS helper before push.

Implemented during this validation pass:

- Contact create/detail now supports browser-entered phone and website, with `email` mapped to the existing billing email storage and migration `0083_client_profile_fields.sql` adding `phone` and `website`.
- People create/edit now exposes `practice_area` and `seniority`, and the People list shows those classifications for reporting/capacity context.
- Standalone Projects create now exposes budget amount and budget hours, carries selected status through the API, and shows monetary budget in the project list.
- Copilot now has a persistent `Log time` quick action that pre-fills the natural-language time logging prompt.
- Reports Trial Balance reloads when its eager initial request fails before the tab is active, and the launch walkthrough verifies the visible active tab instead of hidden stale tab content.
- The launch walkthrough creates richer data through the UI: contact profile, employee classification, service line, engagement total value/dates, project budgets, time entries, invoice, bills surfaces, reports, and manual journal.
- Copilot finance-ops tools now cover bill-pay proposals, month-end close preparation, year-end close preparation, and financial statement package generation with tool policy/HITL routing.
- Copilot finance-ops command-center orchestration now covers manager action-plan creation through Inbox; approval fans out `finance_ops_action_item` child tasks, and child approval dispatches mapped specialist workflows while leaving downstream invoices, payments, journals, statements, and emails behind their existing specialist approvals.
- Copilot document upload status now has a document detail API path, actionable Documents/Inbox links, and source-document metadata preserved through HITL approval into created bills.
- Bill-pay Inbox approval now attributes draft payment batch creation to the approving user UUID instead of a non-UUID agent label.
- Month-end close preparation now fails loudly if close-task bootstrap returns no tasks, preventing a false successful close in a database missing migration `0068_accounting_close_tasks.sql`.

| Scenario | Browser-only setup | Browser validation | Current result | Notes |
| --- | --- | --- | --- | --- |
| 1. Multi-year managed accounting retainer | Browser-capable | Browser + automated equivalent | Passed | Retainer/billing-run behavior covered by full E2E §2.3 and reports route checks; manual business script remains for team demo rehearsal |
| 2. Multi-year ERP implementation milestones | Browser-capable | Browser + automated equivalent | Passed | Milestone billing covered by full E2E §2.2 and project phase UI coverage; manual script validates named BluePeak data |
| 3. One-time capped T&M CFO advisory | Browser-capable | Browser + automated equivalent | Passed | Capped T&M covered by full E2E §2.5, WIP/utilization/report tabs, and launch walkthrough T&M flow |
| 4. One-time fixed-fee tax compliance | Browser-capable | Browser + automated equivalent | Passed | Fixed-fee invoicing covered by full E2E §2.1, invoice lifecycle, paid state, and financial reports |
| 5. IT infrastructure procurement | Browser-capable entry points | Browser + automated equivalent | Passed | Vendor/bills/pay-bills routes render and #323 covers line-level PO match lifecycle; run manual script for launch-demo data entry |
| 6. Contractor service order | Browser-capable entry points | Browser + automated equivalent | Passed | Vendor bill/procurement, service-period PO/SO match evidence, project-cost, AP Aging, and close proposal paths covered by automated suite; manual script validates named contractor scenario |
| 7. Bill payment batch and settlement | Browser-capable | Browser + automated equivalent + Copilot live proof | Passed | Pay Bills route and AP Aging checks pass; Copilot live proof verifies AI proposal, Inbox approval, and draft batch creation; #325 browser proof covers approve/export/mark-sent/settle lifecycle; bill payment/service tests cover settlement semantics |
| 8. Month-end close | Browser-capable | Browser + automated equivalent + Copilot live proof | Passed | Manual journal UI, imbalanced rejection, period-lock guard, close package/service tests, and Copilot close-task bootstrap all passed |
| 9. Quarter close and statements | Browser-capable | Browser + automated equivalent + Copilot live proof | Passed | Trial Balance, Balance Sheet, Income Statement, Cash Flow, Statutory Pack, financial statement unit/report tests, Copilot statement-package live proof, and #327 year-end retained-earnings posting proof passed |
| 10. Management reports and action queues | Browser-capable | Browser + automated equivalent | Passed | Project Health, Capacity, Action Queue, report tabs, Inbox/HITL, agent run/workflow surfaces covered by full browser/backend suites |

## Gaps To Record As Issues

When a browser step cannot be completed because the UI lacks a required control, create a GitHub issue with:

- title: `[launch-e2e] <scenario> - <missing or failing capability>`
- labels: `type:task`, plus the relevant area label if available
- body:
  - `> *This was generated by AI during triage.*`
  - Scenario number and name.
  - Browser route.
  - Exact user action attempted.
  - Expected result.
  - Actual result.
  - Screenshot/video/trace path if available.
  - Whether the API/backend already supports the capability.

Do not close a gap issue until the browser workflow passes.
