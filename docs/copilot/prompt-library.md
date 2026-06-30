# Aethos Atlas Prompt Library

Use these prompts as starting points for finance-operations workflows. They are
written in user language and intentionally avoid internal tool names.

Aethos Atlas should work from business intent. Users do not have to name an internal
tool or workflow function. Include the period, customer/vendor/project, desired
outcome, and approval boundary; Aethos Atlas should infer whether the request is
read-only, needs an Inbox task, or should be routed to an existing ERP module.
Engineers and QA authors may use tool names only for deterministic ledger
assertions.

For document intake, attach the document first and then send the matching
business prompt. Aethos Atlas should not extract the file or create Inbox work
until the prompt is submitted.

## Finance Ops Manager

| Goal | Prompt |
| --- | --- |
| Daily finance check | `Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.` |
| Read-only runtime smoke | `Run today's finance ops check. Use live Aethos data for AR, AP, WIP, and active engagements. Do not create any records.` |
| Create reviewed work plan | `Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.` |
| Configure scheduled manager | `Set the Finance Ops Manager to run every business morning at 07:00 UTC for the current month, create a reviewed action plan in Inbox, and escalate stale high-risk approvals without changing the original tasks.` |
| Check schedule settings | `Show me the current Finance Ops Manager schedule, escalation settings, latest scheduled run, and any open scheduled action plans waiting in Inbox.` |
| Finance Ops control room | `Show me the Finance Ops Manager control room. Include the current schedule, next run, latest scheduled run, failed or skipped workflows, open action plans, open Plan Items, stale approval escalations, and operational health. Do not show tool names, traces, logs, context IDs, or raw system details.` |
| Review scheduled output | `Show me the latest scheduled Finance Ops Manager run. Summarize the action plan, open Plan Items, stale approval escalations, and anything waiting on Owner or Admin review.` |
| Dispatch reviewed plan items | `After I approve the action plan, create the specialist follow-up tasks for the approved Plan Items. Keep final invoices, payments, journals, statements, and emails behind their own approvals.` |
| Explain blockers | `Explain the current finance ops blockers for June 2026. Group them by AR, AP, WIP, close, reporting, and approvals. Tell me what can run now and what needs human review.` |
| Review agent activity | `Summarize recent finance agent runs and workflow runs. Highlight failures, skipped actions, pending Inbox approvals, and anything that needs escalation.` |
| Review approval policy | `Show me which finance actions currently require Manager, Admin, or Owner approval. Explain the policy in business terms and flag any high-risk actions waiting in Inbox.` |
| Executive weekly brief | `Create a weekly finance operations brief for the leadership team. Summarize cash collection risk, vendor payment risk, close readiness, project margin risk, and any AI-recommended actions waiting for approval.` |

## Order To Cash

| Goal | Prompt |
| --- | --- |
| Draft customer invoice | `Draft an invoice for the Northstar Advisory engagement for June 2026. Use approved billable time, billable expenses, and billing terms. Send the draft to Inbox before creating an invoice.` |
| Review WIP | `Show me billable WIP for active engagements and recommend what should be invoiced this week. Do not create invoices without Inbox approval.` |
| Engagement structure | `Show me the Nexus Capital Partners engagement structure. List active projects, billing model for each workstream, linked rate card and source document state, and anything missing before billing.` |
| Resource delivery readback | `Show me Alice Chen's June delivery data for Nexus. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced.` |
| Log time | `Log 4.5 billable hours for Sarah Patel on the CFO Advisory project today for month-end close support. Send anything risky to Inbox.` |
| Capped tax engagement | `Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee 18,500 GBP, capped at 22,000 GBP if advisory hours overrun. Route the engagement draft to Inbox before creation.` |
| Update rates | `Update Sarah Patel's advisory billing rate to 425 USD per hour starting July 1, 2026. Route the rate change to Inbox for approval.` |
| Revenue tie-out | `Tie June 2026 revenue to approved invoices, billing terms, WIP movement, and posted journals. Flag any draft invoice or unposted journal that keeps the report from being final.` |
| Public invoice check | `Check whether the public invoice link for the latest Northstar invoice is safe to share. Confirm the amount, due date, customer name, and payment status before any external send.` |
| Multi-currency payment settlement | `Review the latest GBP customer payment. Confirm the transaction amount, USD base amount, realised FX gain or loss, and whether AR Aging and Cash Flow will update after settlement.` |

## Collections

| Goal | Prompt |
| --- | --- |
| Draft reminders | `Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.` |
| Customer-specific sweep | `Find overdue invoices for Northstar and draft appropriate reminder emails. Use a firm tone only where the collections policy allows it. Do not send without approval.` |
| Collections follow-up read | `Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.` |
| Single invoice drilldown | `Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action.` |
| Collections status | `Summarize overdue invoices by customer, aging bucket, last reminder, and recommended next action. Flag any invoices that should not receive another reminder yet.` |

## Procure To Pay

| Goal | Prompt |
| --- | --- |
| Vendor invoice intake | `Process this vendor invoice, match it to the right vendor and project where possible, code exceptions for review, and send the bill draft to Inbox.` |
| Vendor invoice exception review | `Show me vendor match evidence, duplicate guard details, GL coding suggestions, project and customer hints, source document link, and required reviewer corrections for this invoice before I approve it.` |
| Duplicate invoice review | `Review this possible duplicate vendor invoice. Compare the vendor, invoice number, amount, date, source document, and coding evidence. If it is legitimate, add a duplicate-review reason before approval.` |
| Vendor payment risk read | `Which vendor bills are due soon, which are blocked, and what evidence supports payment? Show vendor, bill number, amount, due date, status, coding evidence, source document, duplicate risk, PO/service-order match, payment-batch state, blockers, and next action. Do not create a payment batch yet.` |
| Single bill drilldown | `Review bill BILL-1001. Show due date, amount, vendor invoice number, coding status, source document, duplicate signals, PO/service-order match, approval state, payment readiness, existing batch status, and recommended next action.` |
| Bill-pay run | `Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox.` |
| AP risk review | `Review AP Aging and tell me which vendors need payment attention this week. Separate safe recommendations from actions that need approval.` |
| Payment approval packet | `Prepare a payment approval packet for bills due in the next 10 days. Include vendor, amount, due date, coding evidence, duplicate status, cash impact, and the approver role required for the batch.` |
| Bill detail audit | `Explain how this bill was created. Include the source document, Inbox decision, reviewer edits, duplicate-review reason if any, GL coding evidence, and whether it is eligible for payment.` |

## Record To Report

| Goal | Prompt |
| --- | --- |
| Month-end close prep | `Prepare month-end close for June 2026. Summarize readiness blockers, missing approvals, unposted journals, open AR/AP, and proposed close tasks. Route the close preparation to Inbox before creating close tasks.` |
| Remaining close blockers | `What is still blocking June 2026 close? Show missing approvals, unposted journals, unreconciled balances, and the next owner for each item.` |
| Close override review | `Review the June 2026 close blockers and tell me which named blockers can be overridden. Include the business reason, supporting evidence, actor role needed, and warn me if the override would hide unresolved AR, AP, WIP, GL, or approval issues.` |
| Year-end close approval | `Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.` |
| Management pack readback | `Give me the June 2026 month-end management pack. Explain the major variances versus May 2026, show revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers. Do not post journals or lock the period.` |
| Comparative financial statements | `Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and evidence-backed management commentary. Compare it to May 2026 and show the variances.` |
| Variance explanation | `Explain material variances in June 2026 financial statements versus May 2026 and recommend next actions. Do not post journals or lock the period without approval.` |
| Close package tie-out | `Tie the June 2026 close package to AR Aging, AP Aging, WIP, Trial Balance, unposted journals, close tasks, and recorded override reasons. Show what is ready and what still needs review.` |
| Manual journal review | `Review this manual journal proposal for balance, account validity, period lock status, business reason, supporting evidence, approval role, and whether the approver is different from the submitter. Do not post it without Inbox approval.` |
| Manual journal evidence | `Prepare a manual journal packet for this adjustment. Include the business reason, supporting source records, debit and credit accounts, total debit amount, period-lock status, manual-journal approval threshold, required Accounting approver role, whether Inbox approval is required before posting, and the submitted/approved/rejected/posting evidence I should verify in the decision trail.` |
| Multi-currency manual journal | `Prepare a GBP 1,000 month-end payroll accrual journal for June 2026. Show the USD base-currency impact using the posting-date FX rate, route it to Inbox before posting, and verify the Trial Balance remains balanced after approval.` |
| Manual journal reversal | `Prepare a reversal packet for this posted manual journal. Explain why reversal is appropriate, propose an open-period reversal date, show the flipped debit and credit lines, and confirm the reversal will create a new journal rather than editing the original.` |

## Audit And Controls

| Goal | Prompt |
| --- | --- |
| Record decision trail | `Show the decision trail for this bill, invoice, payment batch, journal, or close record. Include the related Inbox task, actor role, decision type, timestamp, and before/after review summary.` |
| Audit sample | `Prepare an audit sample of AI-assisted finance decisions this week. Separate approvals, approve-with-edits, rejections, and approval denials. Flag records where the reviewed payload changed materially.` |
| Approval controls read pack | `What am I allowed to approve, what requires Owner approval, and which Inbox items are high risk? Include my finance personas, effective thresholds, pending high-risk tasks, and why each item needs review. Do not show tool names, policy reason codes, raw payloads, traces, logs, or context IDs.` |
| Review finance access | `Show me which finance personas my current role maps to. Summarize what I can do in Inbox, Bills/AP, Invoices/AR, Reports, Accounting, and Settings, and which actions still need another approver.` |
| Read-only audit walkthrough | `As a read-only auditor, show me the records I can inspect for this bill-payment batch and which actions are intentionally blocked for my role.` |
| Approval policy impact | `If we raise high-value bill-pay approvals to Owner, explain which open Inbox tasks would be affected and which users could still approve them.` |

## Client And Engagement Onboarding

| Goal | Prompt |
| --- | --- |
| Engagement letter intake | `Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.` |
| Engagement extraction readback | `Read the extraction results and linked Inbox review for this engagement letter. Summarize client, billing model, commercial terms, rate hints, first project, confidence, and what needs approval.` |
| SOW review | `Review this SOW and summarize scope, pricing, dates, billing terms, rate hints, and first project setup. Route the proposed records to Inbox before creation.` |
| Vendor onboarding | `Review this new vendor setup request. Summarize tax details, payment terms, banking risk if present, required approvals, and any missing source documents before creating or updating the vendor record.` |
| Project setup review | `Create a project setup checklist for this new engagement. Include billing model, service line, milestones, staffing, linked rate card, WIP risk, and any fields that need manager approval.` |

## Reports And Documents

| Goal | Prompt |
| --- | --- |
| Report pack review | `Prepare a management report pack for June 2026. Summarize AR, AP, WIP, revenue, project margin, utilization, Trial Balance, Balance Sheet, Income Statement, Cash Flow, and action queue exceptions.` |
| Source document search | `Find source documents connected to this bill, invoice, engagement, or close task. Summarize extraction status, Inbox decision outcome, and the materialized record it supports.` |
| Document intake readback | `Read the document intake context for nexus_engagement_letter.pdf. Show source filename, extraction state, extracted payload, linked Inbox task, and the business record it supports.` |
| Project margin investigation | `Explain why this project margin changed this month. Tie the explanation to time entries, expenses, vendor bills, invoices, WIP, and any pending approvals.` |
| Collections and cash view | `Show expected cash movement for the next 30 days from overdue invoices, expected payments, approved bills, and proposed bill-pay batches. Separate forecasts from approved transactions.` |

## Settings And Operations

| Goal | Prompt |
| --- | --- |
| Operational health | `Review operational health for this tenant. Summarize runtime status, table checks, rate-limit backend, request failures, background failures, agent/tool/workflow failures, and routed alerts without exposing secrets or tokens.` |
| Alert readiness | `Show which operational alerts would route to the runbook or webhook today. Include degraded health, public endpoint abuse, background failure spikes, and agent/tool/workflow failure spikes.` |
| Schedule readiness | `Before enabling a scheduled Finance Ops Manager run, show the current cadence, escalation windows, last run, open scheduled plans, and approval boundary for resulting work.` |
| Persona education | `Explain my finance role persona mapping and the top five actions I can do directly, the top five actions I can review, and the actions that require a higher approver.` |

## E2E Scenario Prompt Sets

Use these prompt sets as the starting point for browser automation and manual
launch passes. The exact business names can be replaced with launch test data.

| Scenario | Prompts | Expected proof |
| --- | --- | --- |
| Controls/audit/RBAC proof (#309) | Review approval policy; draft high-value bill-pay run; show decision trail; review finance access | Required-role Inbox task, denied under-privileged action, immutable decision event, read-only UI/API denial |
| Multi-currency AR payment proof (#349/#351) | `Review the latest GBP customer payment. Confirm the transaction amount, USD base amount, realised FX gain or loss, and whether AR Aging and Cash Flow will update after settlement.` | Payment transaction/base amounts, FX rate id provenance, DR Bank/CR AR base amounts, realised FX delta, AR Aging and Cash Flow tie-out |
| AI finance workflow proof (#310) | `Process this vendor invoice for Aster Cloud Services. Match it to the right vendor and project, flag any duplicate risk, code it to software subscriptions, send exceptions to Inbox for review, and prepare a bill-pay proposal after the bill is reviewed.` `Run month-end close readiness for June 2026. Prepare the close review package, capture any controller override evidence, and generate financial statement commentary for the management pack.` | AP exception evidence, corrected bill, payment batch review, close evidence, statement commentary, agent/tool ledger evidence |
| AI year-end close proof (#329) | `Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.` | `copilot_prepare_year_end_close` Inbox task, preview blockers, retained-earnings amount/direction, comparative commentary, posted `YE-YYYY` journal after approval |
| Multi-currency R2R proof (#347/#351) | `Prepare a GBP 1,000 month-end payroll accrual journal for June 2026. Show the USD base-currency impact using the posting-date FX rate, route it to Inbox before posting, and verify the Trial Balance remains balanced after approval.` | GBP transaction amounts, USD base amounts, FX rate id provenance, no silent missing-rate post, balanced Trial Balance, manual-journal audit evidence |
| Comparative statement proof (#331) | `Generate the financial statement package for Q2 2026 and compare it to Q2 2025. Include Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, close-readiness warnings, and evidence-backed variance commentary.` | Current/comparison periods, deterministic variances, management commentary, no record mutation |
| R2R management-pack read proof (#357) | `Give me the June 2026 month-end management pack. Explain major variances versus May 2026 and list remaining close blockers. Then drill into revenue, expenses, project margin, utilization, AR/AP movement, journals, and close task blockers with source data. Do not post journals or lock the period.` | Normalized period, comparative statements, variance rows, project/utilization highlights, AR/AP period movement, draft journals, locked-period state, close-task blockers, no record mutation |
| Ops proof (#311) | Review operational health; show alert readiness; review agent activity | Rate-limit backend, sanitized failure signals, routed alerts, no exposed secrets |
| Documentation proof (#312) | Run daily finance ops check; explain blockers; prepare executive weekly brief | Guide/prompt examples map to business tasks without internal tool names |

## Prompting Pattern

Good Aethos Atlas prompts usually include:

- the business period or customer/vendor/engagement name;
- the desired outcome;
- whether to summarize, draft, or prepare;
- the approval boundary, such as `route to Inbox before sending/posting/paying`;
- a request to separate read-only findings from actions.

Avoid asking for internal tool names. Aethos Atlas should infer the right tool from
the business request. Test specs may name tools to reduce automation
nondeterminism, but users should not need to.

For persistent scheduled Finance Ops Manager changes, admins can also use
Settings -> Agent Autonomy -> Finance Ops Manager Schedule. Prompts remain
useful for reviewing schedule status and run output in context.
For persistent approval-threshold changes, admins should use Settings ->
Approval Controls -> Approval Policy Matrix.
For role mapping review, all users can use Settings -> Approval Controls ->
Finance role personas to see product-facing finance personas mapped to enforced
tenant roles.

## Demo Guide v2 Live Validation Prompt Set

These are the exact Aethos Atlas prompts used by
`frontend/e2e/demo-v2-production-validation.spec.ts`. Use them for manual
browser validation after seeding Demo Guide v2 data. For rows with attachments,
attach the named demo asset first and then submit the prompt.

| Step | Scenario | Prompt |
| --- | --- | --- |
| 1-1-engagement-letter | 1.1 Engagement letter onboarding | `Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.` |
| 1-2-engagement-structure | 1.2 Project structure | `Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.` |
| 1-3-log-time | 1.3 Time entry | `Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling` |
| 1-3a-delivery-data | 1.3A People and WIP | `Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.` |
| 1-4-billing-run | 1.4 Mixed model invoice | `Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending.` |
| 1-5-revenue-recognition | 1.5 Revenue recognition | `Explain how Nexus June revenue is recognized across fixed-fee milestone, retainer, T&M advisory WIP, and expenses. Tie the explanation to invoice-backed journals and Project P&L.` |
| 1-6-capped-tax | 1.6 Capped tax engagement | `Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun` |
| 1-7-o2c-readiness | 1.7 O2C controls | `Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval.` |
| 1-7-collections-read | 1.7 Collections read pack | `Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.` |
| 1-7-invoice-drilldown | 1.7 Invoice drilldown | `Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action.` |
| 1-7-draft-reminders | 1.7 Collections controlled write | `Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.` |
| 2-1-retainer | 2.1 Monthly retainer billing | `Prepare Brightwater Manufacturing monthly retainer billing for June 2026. Show the draft invoice, any tax, and route it to Inbox before sending.` |
| 2-2-milestone | 2.2 Annual accounts milestone | `Prepare the Brightwater Annual Accounts FY2025 milestone invoice. Include the milestone basis, tax treatment, and approval path before sending.` |
| 2-3-payroll | 2.3 Payroll billing | `Prepare Brightwater payroll billing for June 2026 based on active employee count. Show per-employee billing, invoice total, and any approval needed.` |
| 2-4-vendor-invoice | 2.4 Vendor invoice intake | `Process this vendor invoice for Brightwater. Match it to the right vendor and project, flag duplicate risk, code it to the right account, compare any PO or service-order evidence, and send exceptions to Inbox.` |
| 2-4-payment-risk-read | 2.4 P2P read pack | `Which vendor bills are due soon, which are blocked, and what evidence supports payment? Show vendor, bill number, amount, due date, status, coding evidence, source document, duplicate risk, PO/service-order match, payment-batch state, blockers, and next action. Do not create a payment batch yet.` |
| 2-4-single-bill | 2.4 Single bill drilldown | `Review bill BILL-1001. Show due date, amount, vendor invoice number, coding status, source document, duplicate signals, PO/service-order match, approval state, payment readiness, existing batch status, and recommended next action.` |
| 2-5-bill-pay | 2.5 Payment controls | `Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox.` |
| 2-5-payment-packet | 2.5 Payment approval packet | `Prepare a payment approval packet for bills due in the next 10 days. Include vendor, amount, due date, coding evidence, duplicate status, cash impact, and the approver role required for the batch.` |
| 3-1-family-office | 3.1 Family office structure | `Show the Alderton Family Office structure. List each engagement, service line, billing model, currency, open projects, and missing setup before billing.` |
| 3-2-scope-creep | 3.2 Scope creep risk | `Review Alderton bespoke tax return scope. Compare actual time, fixed fee, expected margin, open WIP, and recommend whether we need a fee adjustment before billing.` |
| 3-3-sgd-journal | 3.3 Multi-currency trust accounts | `Prepare an SGD 18,000 dividend income journal for Alderton Trust for June 2026. Show the GBP base-currency impact, FX rate provenance, required approval role, and route it to Inbox before posting.` |
| 3-4-cosec-reminders | 3.4 COSEC reminders | `Review COSEC filing reminders for Alderton entities. Show upcoming filing dates, missing evidence, billing impact, and which reminders need approval before sending.` |
| 4-1-usd-engagement | 4.1 USD-billed engagement | `Explain Thornton June billing and cash position in USD and GBP. Show invoice amount, base-currency journal impact, FX rate provenance, AR status, and cash-flow effect after payment.` |
| 4-2-series-a | 4.2 Series A milestone | `Thornton Series A closed at $14.2M. Update the milestone amount and invoice. Route any revenue or billing change to Inbox before sending.` |
| 4-3-cosec-instruction | 4.3 COSEC instruction | `Review this COSEC instruction for Thornton. Identify the company change, create the required filing/project work item, identify billing impact, and route any external filing or invoice action to Inbox.` |
| 5-1-close-readiness | 5.1 Pre-close checklist | `Run June 2026 pre-close checks. Show AR, AP, WIP, unposted journals, close tasks, missing approvals, and what needs to happen before the period can be locked.` |
| 5-2-period-lock | 5.2 Period lock | `Can we lock June 2026? Show the period-lock readiness result, blockers, overrides if any, and what a Controller or Owner must review before locking.` |
| 5-3-trial-balance | 5.3 Trial Balance | `Show the June 2026 Trial Balance. Confirm whether debits equal credits, summarize the largest account movements, and flag suspense or unbalanced items.` |
| 5-4-management-reporting | 5.4 Management reporting | `Alice is at 64% utilisation in June. Which clients have unbilled WIP tied to Alice?` |
| 5-5-management-pack | 5.5 R2R management pack | `Give me the June 2026 month-end management pack. Explain the major variances versus May 2026, show revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers. Do not post journals or lock the period.` |
| 5-5-management-drilldown | 5.5 R2R blocker drilldown | `Drill into the draft journals and close task blockers for June 2026. Which ones block close, who owns them, and what should happen next?` |
| 5-5-statement-package | 5.5 Financial statement package | `Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and evidence-backed management commentary. Compare it to May 2026 and show the variances.` |
| 5-5-year-end | 5.5 Year-end close | `Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.` |
| 5-6-manual-journal | 5.6 Manual journal lifecycle | `Review this manual journal proposal for balance, account validity, period lock status, business reason, supporting evidence, approval role, and whether the approver is different from the submitter. Do not post it without Inbox approval.` |
| 5-6-reversal | 5.6 Manual journal reversal | `Prepare a reversal packet for this posted manual journal. Explain why reversal is appropriate, propose an open-period reversal date, show the flipped debit and credit lines, and confirm the reversal will create a new journal rather than editing the original.` |
| 6-1-finance-ops-check | 6.1 Finance Ops Manager | `Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.` |
| 6-1-action-plan | 6.1 Finance Ops action plan | `Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.` |
| 6-2-scheduled-control-room | 6.2 Scheduled Finance Ops Manager | `Before enabling a scheduled Finance Ops Manager run, show the current cadence, escalation windows, last run, open scheduled plans, and approval boundary for resulting work.` |
| 7-1-approval-controls | 7.1 Approval policy and personas | `What am I allowed to approve, what requires Owner approval, and which Inbox items are high risk? Include my finance personas, effective thresholds, pending high-risk tasks, and why each item needs review. Do not show tool names, policy reason codes, raw payloads, traces, logs, or context IDs.` |
| 7-2-decision-trail | 7.2 Decision trail | `Show the decision trail for the latest bill, invoice, payment batch, journal, or close record. Include the related Inbox task, actor role, decision type, timestamp, and before/after review summary.` |
| 7-3-operational-health | 7.3 Operational Health | `Show operational health for the platform today. Include degraded health, public endpoint abuse, background failure spikes, and agent/tool/workflow failure spikes. Do not expose secrets, traces, raw logs, or stack traces.` |
| 7-4-documents-audit | 7.4 Documents and source evidence | `Show documents that support recent engagements, bills, invoices, journals, and Inbox decisions. For each, show the linked business record, source filename, extraction state, and what I should review next.` |
| 7-5-config-telemetry | 7.5 Configuration and telemetry | `Review configuration and telemetry readiness. Show approval controls, scheduled Finance Ops Manager settings, Atlas runtime, Langfuse observability status, operational alerts, and any public abuse-path controls that need attention.` |
