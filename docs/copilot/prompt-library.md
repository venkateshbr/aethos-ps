# Copilot Prompt Library

Use these prompts as starting points for finance-operations workflows. They are
written in user language and intentionally avoid internal tool names.

## Finance Ops Manager

| Goal | Prompt |
| --- | --- |
| Daily finance check | `Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.` |
| Create reviewed work plan | `Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.` |
| Configure scheduled manager | `Set the Finance Ops Manager to run every business morning at 07:00 UTC for the current month, create a reviewed action plan in Inbox, and escalate stale high-risk approvals without changing the original tasks.` |
| Review scheduled output | `Show me the latest scheduled Finance Ops Manager run. Summarize the action plan, open Plan Items, stale approval escalations, and anything waiting on Owner or Admin review.` |
| Dispatch reviewed plan items | `After I approve the action plan, create the specialist follow-up tasks for the approved Plan Items. Keep final invoices, payments, journals, statements, and emails behind their own approvals.` |
| Explain blockers | `Explain the current finance ops blockers for June 2026. Group them by AR, AP, WIP, close, reporting, and approvals. Tell me what can run now and what needs human review.` |
| Review agent activity | `Summarize recent finance agent runs and workflow runs. Highlight failures, skipped actions, pending Inbox approvals, and anything that needs escalation.` |

## Order To Cash

| Goal | Prompt |
| --- | --- |
| Draft customer invoice | `Draft an invoice for the Northstar Advisory engagement for June 2026. Use approved billable time, billable expenses, and billing terms. Send the draft to Inbox before creating an invoice.` |
| Review WIP | `Show me billable WIP for active engagements and recommend what should be invoiced this week. Do not create invoices without Inbox approval.` |
| Log time | `Log 4.5 billable hours for Sarah Patel on the CFO Advisory project today for month-end close support. Send anything risky to Inbox.` |
| Update rates | `Update Sarah Patel's advisory billing rate to 425 USD per hour starting July 1, 2026. Route the rate change to Inbox for approval.` |

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
| Bill-pay run | `Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox.` |
| AP risk review | `Review AP Aging and tell me which vendors need payment attention this week. Separate safe recommendations from actions that need approval.` |

## Record To Report

| Goal | Prompt |
| --- | --- |
| Month-end close prep | `Prepare month-end close for June 2026. Summarize readiness blockers, missing approvals, unposted journals, open AR/AP, and proposed close tasks. Route the close preparation to Inbox before creating close tasks.` |
| Remaining close blockers | `What is still blocking June 2026 close? Show missing approvals, unposted journals, unreconciled balances, and the next owner for each item.` |
| Financial statements | `Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, and management commentary. Flag missing close prerequisites.` |
| Variance explanation | `Explain material variances in June 2026 financial statements and recommend next actions. Do not post journals or lock the period without approval.` |

## Client And Engagement Onboarding

| Goal | Prompt |
| --- | --- |
| Engagement letter intake | `Review this engagement letter, create the client, engagement, billing terms, and first project. Send anything risky to Inbox.` |
| SOW review | `Review this SOW and summarize scope, pricing, dates, billing terms, rate hints, and first project setup. Route the proposed records to Inbox before creation.` |

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
