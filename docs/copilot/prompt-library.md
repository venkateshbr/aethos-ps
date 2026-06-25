# Copilot Prompt Library

Use these prompts as starting points for finance-operations workflows. They are
written in user language and intentionally avoid internal tool names.

Copilot should work from business intent. Users do not have to name an internal
tool or workflow function. Include the period, customer/vendor/project, desired
outcome, and approval boundary; Copilot should infer whether the request is
read-only, needs an Inbox task, or should be routed to an existing ERP module.
Engineers and QA authors may use tool names only for deterministic ledger
assertions.

## Finance Ops Manager

| Goal | Prompt |
| --- | --- |
| Daily finance check | `Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.` |
| Create reviewed work plan | `Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.` |
| Configure scheduled manager | `Set the Finance Ops Manager to run every business morning at 07:00 UTC for the current month, create a reviewed action plan in Inbox, and escalate stale high-risk approvals without changing the original tasks.` |
| Check schedule settings | `Show me the current Finance Ops Manager schedule, escalation settings, latest scheduled run, and any open scheduled action plans waiting in Inbox.` |
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
| Log time | `Log 4.5 billable hours for Sarah Patel on the CFO Advisory project today for month-end close support. Send anything risky to Inbox.` |
| Update rates | `Update Sarah Patel's advisory billing rate to 425 USD per hour starting July 1, 2026. Route the rate change to Inbox for approval.` |
| Revenue tie-out | `Tie June 2026 revenue to approved invoices, billing terms, WIP movement, and posted journals. Flag any draft invoice or unposted journal that keeps the report from being final.` |
| Public invoice check | `Check whether the public invoice link for the latest Northstar invoice is safe to share. Confirm the amount, due date, customer name, and payment status before any external send.` |

## Collections

| Goal | Prompt |
| --- | --- |
| Draft reminders | `Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.` |
| Customer-specific sweep | `Find overdue invoices for Northstar and draft appropriate reminder emails. Use a firm tone only where the collections policy allows it. Do not send without approval.` |
| Collections status | `Summarize overdue invoices by customer, aging bucket, last reminder, and recommended next action. Flag any invoices that should not receive another reminder yet.` |

## Procure To Pay

| Goal | Prompt |
| --- | --- |
| Vendor invoice intake | `Process this vendor invoice, match it to the right vendor and project where possible, code exceptions for review, and send the bill draft to Inbox.` |
| Vendor invoice exception review | `Show me vendor match evidence, duplicate guard details, GL coding suggestions, project and customer hints, source document link, and required reviewer corrections for this invoice before I approve it.` |
| Duplicate invoice review | `Review this possible duplicate vendor invoice. Compare the vendor, invoice number, amount, date, source document, and coding evidence. If it is legitimate, add a duplicate-review reason before approval.` |
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
| Comparative financial statements | `Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and evidence-backed management commentary. Compare it to May 2026 and show the variances.` |
| Variance explanation | `Explain material variances in June 2026 financial statements versus May 2026 and recommend next actions. Do not post journals or lock the period without approval.` |
| Close package tie-out | `Tie the June 2026 close package to AR Aging, AP Aging, WIP, Trial Balance, unposted journals, close tasks, and recorded override reasons. Show what is ready and what still needs review.` |
| Manual journal review | `Review this manual journal proposal for balance, account validity, period lock status, business reason, supporting evidence, approval role, and whether the approver is different from the submitter. Do not post it without Inbox approval.` |
| Manual journal evidence | `Prepare a manual journal packet for this adjustment. Include the business reason, supporting source records, debit and credit accounts, total debit amount, period-lock status, manual-journal approval threshold, required Accounting approver role, whether Inbox approval is required before posting, and the submitted/approved/rejected/posting evidence I should verify in the decision trail.` |
| Manual journal reversal | `Prepare a reversal packet for this posted manual journal. Explain why reversal is appropriate, propose an open-period reversal date, show the flipped debit and credit lines, and confirm the reversal will create a new journal rather than editing the original.` |

## Audit And Controls

| Goal | Prompt |
| --- | --- |
| Record decision trail | `Show the decision trail for this bill, invoice, payment batch, journal, or close record. Include the related Inbox task, actor role, decision type, timestamp, and before/after review summary.` |
| Audit sample | `Prepare an audit sample of AI-assisted finance decisions this week. Separate approvals, approve-with-edits, rejections, and approval denials. Flag records where the reviewed payload changed materially.` |
| Review finance access | `Show me which finance personas my current role maps to. Summarize what I can do in Inbox, Bills/AP, Invoices/AR, Reports, Accounting, and Settings, and which actions still need another approver.` |
| Read-only audit walkthrough | `As a read-only auditor, show me the records I can inspect for this bill-payment batch and which actions are intentionally blocked for my role.` |
| Approval policy impact | `If we raise high-value bill-pay approvals to Owner, explain which open Inbox tasks would be affected and which users could still approve them.` |

## Client And Engagement Onboarding

| Goal | Prompt |
| --- | --- |
| Engagement letter intake | `Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.` |
| SOW review | `Review this SOW and summarize scope, pricing, dates, billing terms, rate hints, and first project setup. Route the proposed records to Inbox before creation.` |
| Vendor onboarding | `Review this new vendor setup request. Summarize tax details, payment terms, banking risk if present, required approvals, and any missing source documents before creating or updating the vendor record.` |
| Project setup review | `Create a project setup checklist for this new engagement. Include billing model, service line, milestones, staffing, linked rate card, WIP risk, and any fields that need manager approval.` |

## Reports And Documents

| Goal | Prompt |
| --- | --- |
| Report pack review | `Prepare a management report pack for June 2026. Summarize AR, AP, WIP, revenue, project margin, utilization, Trial Balance, Balance Sheet, Income Statement, Cash Flow, and action queue exceptions.` |
| Source document search | `Find source documents connected to this bill, invoice, engagement, or close task. Summarize extraction status, Inbox decision outcome, and the materialized record it supports.` |
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
| AI finance workflow proof (#310) | `Process this vendor invoice for Aster Cloud Services. Match it to the right vendor and project, flag any duplicate risk, code it to software subscriptions, send exceptions to Inbox for review, and prepare a bill-pay proposal after the bill is reviewed.` `Run month-end close readiness for June 2026. Prepare the close review package, capture any controller override evidence, and generate financial statement commentary for the management pack.` | AP exception evidence, corrected bill, payment batch review, close evidence, statement commentary, agent/tool ledger evidence |
| AI year-end close proof (#329) | `Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.` | `copilot_prepare_year_end_close` Inbox task, preview blockers, retained-earnings amount/direction, comparative commentary, posted `YE-YYYY` journal after approval |
| Comparative statement proof (#331) | `Generate the financial statement package for Q2 2026 and compare it to Q2 2025. Include Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, close-readiness warnings, and evidence-backed variance commentary.` | Current/comparison periods, deterministic variances, management commentary, no record mutation |
| Ops proof (#311) | Review operational health; show alert readiness; review agent activity | Rate-limit backend, sanitized failure signals, routed alerts, no exposed secrets |
| Documentation proof (#312) | Run daily finance ops check; explain blockers; prepare executive weekly brief | Guide/prompt examples map to business tasks without internal tool names |

## Prompting Pattern

Good Copilot prompts usually include:

- the business period or customer/vendor/engagement name;
- the desired outcome;
- whether to summarize, draft, or prepare;
- the approval boundary, such as `route to Inbox before sending/posting/paying`;
- a request to separate read-only findings from actions.

Avoid asking for internal tool names. Copilot should infer the right tool from
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
