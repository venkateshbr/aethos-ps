# Demo Guide v2 Production Browser Validation

Run ID: `2026-08-05T07-36-11-138Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-08-05T07:43:49.664Z`

This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.

Summary: PASS 58, WARN 0, FAIL 8, SKIP 0

## Evidence Table

| ID | Section | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| auth | Authentication | Logged into https://aethos.ishirock.tech | PASS | — | Tenant: Sterling Bridge Advisory Group<br>Tenant ID: retained production demo tenant<br>User: redacted — use the ignored local credential manifest |
| route-copilot | Route Coverage | Aethos Nous | PASS | [screenshot](screenshots/route-copilot.png) | URL: https://aethos.ishirock.tech/app/copilot<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-documents | Route Coverage | Documents | PASS | [screenshot](screenshots/route-documents.png) | URL: https://aethos.ishirock.tech/app/documents<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-inbox | Route Coverage | Inbox | PASS | [screenshot](screenshots/route-inbox.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-engagements | Route Coverage | Engagements | PASS | [screenshot](screenshots/route-engagements.png) | URL: https://aethos.ishirock.tech/app/engagements<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-projects | Route Coverage | Projects | PASS | [screenshot](screenshots/route-projects.png) | URL: https://aethos.ishirock.tech/app/projects<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-invoices | Route Coverage | Invoices | PASS | [screenshot](screenshots/route-invoices.png) | URL: https://aethos.ishirock.tech/app/invoices<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-clients | Route Coverage | Contacts | PASS | [screenshot](screenshots/route-clients.png) | URL: https://aethos.ishirock.tech/app/clients<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-expenses | Route Coverage | Expenses | PASS | [screenshot](screenshots/route-expenses.png) | URL: https://aethos.ishirock.tech/app/expenses<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-bills | Route Coverage | Bills | PASS | [screenshot](screenshots/route-bills.png) | URL: https://aethos.ishirock.tech/app/bills<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-billing-runs | Route Coverage | Billing Runs / Pay Bills | PASS | [screenshot](screenshots/route-billing-runs.png) | URL: https://aethos.ishirock.tech/app/billing-runs<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-time | Route Coverage | Time | PASS | [screenshot](screenshots/route-time.png) | URL: https://aethos.ishirock.tech/app/time<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-approvals | Route Coverage | Approvals | PASS | [screenshot](screenshots/route-approvals.png) | URL: https://aethos.ishirock.tech/app/approvals<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-payments | Route Coverage | Payments | PASS | [screenshot](screenshots/route-payments.png) | URL: https://aethos.ishirock.tech/app/payments<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-people | Route Coverage | People | PASS | [screenshot](screenshots/route-people.png) | URL: https://aethos.ishirock.tech/app/people<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-reports | Route Coverage | Reports | PASS | [screenshot](screenshots/route-reports.png) | URL: https://aethos.ishirock.tech/app/reports<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-journals | Route Coverage | Accounting / Journal Entries | PASS | [screenshot](screenshots/route-journals.png) | URL: https://aethos.ishirock.tech/app/accounting/journals<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-settings | Route Coverage | Settings | PASS | [screenshot](screenshots/route-settings.png) | URL: https://aethos.ishirock.tech/app/settings<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-timesheet | Route Coverage | Timesheet portal | PASS | [screenshot](screenshots/route-timesheet.png) | URL: https://timesheet.aethos.ishirock.tech<br>Body excerpt: Aethos Timesheets Sign in Log the hours you worked on your projects. EMAIL PASSWORD Sign in |
| 1-1-engagement-letter | 1.1 Engagement letter onboarding | Atlas prompt | PASS | [screenshot](screenshots/1-1-engagement-letter-response.png) | Attachment banner before prompt: attach_file Attached: nexus_engagement_letter.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business-valid answer: matched 7/7 required signals. |
| 1-2-engagement-structure | 1.2 Project structure | Atlas prompt | FAIL | [screenshot](screenshots/1-2-engagement-structure-response.png) | Business validation failed: matched 2/4 required signals; forbidden hits 0.<br>Missing required signals: /project/workstream/i, /billing model/fixed/retainer/T&M/time and materials/i |
| 1-3-log-time | 1.3 Time entry | Atlas prompt | FAIL | [screenshot](screenshots/1-3-log-time-response.png) | Business validation failed: matched 1/5 required signals; forbidden hits 0.<br>Missing required signals: /4\.5/4\.50/i, /Nexus/i, /CFO Advisory/board pack/cash flow/i, /logged/created/Inbox/approval/i |
| 1-3a-delivery-data | 1.3A People and WIP | Atlas prompt | PASS | [screenshot](screenshots/1-3a-delivery-data-response.png) | Business-valid answer: matched 7/7 required signals. |
| 1-4-billing-run | 1.4 Mixed model invoice | Atlas prompt | FAIL | [screenshot](screenshots/1-4-billing-run-response.png) | Business validation failed: matched 6/8 required signals; forbidden hits 2.<br>Missing required signals: /T&M/time and materials/hour/i, /invoice line/draft invoice/i<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i, /couldn'?t locate/not showing up/not found/no .* on file/need .* from you/need .* details/need more information/need some details/i |
| 1-5-revenue-recognition | 1.5 Revenue recognition | Atlas prompt | PASS | [screenshot](screenshots/1-5-revenue-recognition-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-6-capped-tax | 1.6 Capped tax engagement | Atlas prompt | PASS | [screenshot](screenshots/1-6-capped-tax-response.png) | Business-valid answer: matched 6/6 required signals. |
| 1-7-o2c-readiness | 1.7 O2C controls | Atlas prompt | PASS | [screenshot](screenshots/1-7-o2c-readiness-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-collections-read | 1.7 Collections read pack | Atlas prompt | PASS | [screenshot](screenshots/1-7-collections-read-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-invoice-drilldown | 1.7 Invoice drilldown | Atlas prompt | PASS | [screenshot](screenshots/1-7-invoice-drilldown-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-draft-reminders | 1.7 Collections controlled write | Atlas prompt | PASS | [screenshot](screenshots/1-7-draft-reminders-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-1-retainer | 2.1 Monthly retainer billing | Atlas prompt | PASS | [screenshot](screenshots/2-1-retainer-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-2-milestone | 2.2 Annual accounts milestone | Atlas prompt | PASS | [screenshot](screenshots/2-2-milestone-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-3-payroll | 2.3 Payroll billing | Atlas prompt | PASS | [screenshot](screenshots/2-3-payroll-response.png) | Business-valid answer: matched 7/7 required signals. |
| 2-4-vendor-invoice | 2.4 Vendor invoice intake | Atlas prompt | PASS | [screenshot](screenshots/2-4-vendor-invoice-response.png) | Attachment banner before prompt: attach_file Attached: brightwater_subcontractor_invoice.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business-valid answer: matched 8/8 required signals. |
| 2-4-payment-risk-read | 2.4 P2P read pack | Atlas prompt | PASS | [screenshot](screenshots/2-4-payment-risk-read-response.png) | Business-valid answer: matched 9/9 required signals. |
| 2-4-single-bill | 2.4 Single bill drilldown | Atlas prompt | FAIL | [screenshot](screenshots/2-4-single-bill-response.png) | Business validation failed: matched 5/9 required signals; forbidden hits 0.<br>Missing required signals: /BILL-1001/i, /due date/due/i, /payment readiness/payment/i, /next action/recommend/i |
| 2-5-bill-pay | 2.5 Payment controls | Atlas prompt | PASS | [screenshot](screenshots/2-5-bill-pay-response.png) | Business-valid answer: matched 7/7 required signals. |
| 2-5-payment-packet | 2.5 Payment approval packet | Atlas prompt | PASS | [screenshot](screenshots/2-5-payment-packet-response.png) | Business-valid answer: matched 7/7 required signals. |
| 3-1-family-office | 3.1 Family office structure | Atlas prompt | PASS | [screenshot](screenshots/3-1-family-office-response.png) | Business-valid answer: matched 7/7 required signals. |
| 3-2-scope-creep | 3.2 Scope creep risk | Atlas prompt | PASS | [screenshot](screenshots/3-2-scope-creep-response.png) | Business-valid answer: matched 7/7 required signals. |
| 3-3-sgd-journal | 3.3 Multi-currency trust accounts | Atlas prompt | PASS | [screenshot](screenshots/3-3-sgd-journal-response.png) | Business-valid answer: matched 8/8 required signals. |
| 3-4-cosec-reminders | 3.4 COSEC reminders | Atlas prompt | FAIL | [screenshot](screenshots/3-4-cosec-reminders-response.png) | Business validation failed: matched 5/7 required signals; forbidden hits 0.<br>Missing required signals: /Alderton/i, /billing impact/billing/i |
| 4-1-usd-engagement | 4.1 USD-billed engagement | Atlas prompt | PASS | [screenshot](screenshots/4-1-usd-engagement-response.png) | Business-valid answer: matched 8/8 required signals. |
| 4-2-series-a | 4.2 Series A milestone | Atlas prompt | PASS | [screenshot](screenshots/4-2-series-a-response.png) | Business-valid answer: matched 6/6 required signals. |
| 4-3-cosec-instruction | 4.3 COSEC instruction | Atlas prompt | PASS | [screenshot](screenshots/4-3-cosec-instruction-response.png) | Attachment banner before prompt: attach_file Attached: thornton_cosec_instruction.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business-valid answer: matched 7/7 required signals. |
| 5-1-close-readiness | 5.1 Pre-close checklist | Atlas prompt | PASS | [screenshot](screenshots/5-1-close-readiness-response.png) | Business-valid answer: matched 8/8 required signals. |
| 5-2-period-lock | 5.2 Period lock | Atlas prompt | PASS | [screenshot](screenshots/5-2-period-lock-response.png) | Business-valid answer: matched 6/6 required signals. |
| 5-3-trial-balance | 5.3 Trial Balance | Atlas prompt | PASS | [screenshot](screenshots/5-3-trial-balance-response.png) | Business-valid answer: matched 7/7 required signals. |
| 5-4-management-reporting | 5.4 Management reporting | Atlas prompt | PASS | [screenshot](screenshots/5-4-management-reporting-response.png) | Business-valid answer: matched 5/5 required signals. |
| 5-5-management-pack | 5.5 R2R management pack | Atlas prompt | FAIL | [screenshot](screenshots/5-5-management-pack-response.png) | Business validation failed: matched 5/10 required signals; forbidden hits 0.<br>Missing required signals: /June 2026/i, /variance/i, /revenue/i, /margin/i, /utili[sz]ation/i |
| 5-5-management-drilldown | 5.5 R2R blocker drilldown | Atlas prompt | FAIL | [screenshot](screenshots/5-5-management-drilldown-response.png) | Business validation failed: matched 2/5 required signals; forbidden hits 0.<br>Missing required signals: /close task/task/i, /owner/i, /next action/should happen/i |
| 5-5-statement-package | 5.5 Financial statement package | Atlas prompt | PASS | [screenshot](screenshots/5-5-statement-package-response.png) | Business-valid answer: matched 8/8 required signals. |
| 5-5-year-end | 5.5 Year-end close | Atlas prompt | PASS | [screenshot](screenshots/5-5-year-end-response.png) | Business-valid answer: matched 8/8 required signals. |
| 5-6-manual-journal | 5.6 Manual journal lifecycle | Atlas prompt | PASS | [screenshot](screenshots/5-6-manual-journal-response.png) | Business-valid answer: matched 8/8 required signals. |
| 5-6-reversal | 5.6 Manual journal reversal | Atlas prompt | PASS | [screenshot](screenshots/5-6-reversal-response.png) | Business-valid answer: matched 7/7 required signals. |
| 6-1-finance-ops-check | 6.1 Finance Ops Manager | Atlas prompt | PASS | [screenshot](screenshots/6-1-finance-ops-check-response.png) | Business-valid answer: matched 7/7 required signals. |
| 6-1-action-plan | 6.1 Finance Ops action plan | Atlas prompt | FAIL | [screenshot](screenshots/6-1-action-plan-response.png) | Tool-call cards visible to user: 1.<br>Business validation failed: matched 6/6 required signals; forbidden hits 1.<br>Invalid answer signals: Visible tool-call cards: 1 |
| 6-2-scheduled-control-room | 6.2 Scheduled Finance Ops Manager | Atlas prompt | PASS | [screenshot](screenshots/6-2-scheduled-control-room-response.png) | Business-valid answer: matched 6/6 required signals. |
| 7-1-approval-controls | 7.1 Approval policy and personas | Atlas prompt | PASS | [screenshot](screenshots/7-1-approval-controls-response.png) | Business-valid answer: matched 7/7 required signals. |
| 7-2-decision-trail | 7.2 Decision trail | Atlas prompt | PASS | [screenshot](screenshots/7-2-decision-trail-response.png) | Business-valid answer: matched 6/6 required signals. |
| 7-3-operational-health | 7.3 Operational Health | Atlas prompt | PASS | [screenshot](screenshots/7-3-operational-health-response.png) | Business-valid answer: matched 6/6 required signals. |
| 7-4-documents-audit | 7.4 Documents and source evidence | Atlas prompt | PASS | [screenshot](screenshots/7-4-documents-audit-response.png) | Business-valid answer: matched 8/8 required signals. |
| 7-5-config-telemetry | 7.5 Configuration and telemetry | Atlas prompt | PASS | [screenshot](screenshots/7-5-config-telemetry-response.png) | Business-valid answer: matched 6/7 required signals.<br>Missing required signals: /Atlas runtime/Atlas/i |
| route-inbox-after-prompts | Route Coverage | Inbox after Atlas prompts | PASS | [screenshot](screenshots/route-inbox-after-prompts.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-documents-after-prompts | Route Coverage | Documents after Atlas uploads | PASS | [screenshot](screenshots/route-documents-after-prompts.png) | URL: https://aethos.ishirock.tech/app/documents<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |
| route-workflow-runs-after-prompts | Route Coverage | Settings / workflow and observability surfaces | PASS | [screenshot](screenshots/route-workflow-runs-after-prompts.png) | URL: https://aethos.ishirock.tech/app/settings<br>Body excerpt: Aethos dashboard Dashboard auto_awesome Nous upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more schedule Tr |

## Prompt Transcript

## 1-1-engagement-letter - 1.1 Engagement letter onboarding

**Prompt**

```text
Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.
```

**Observed Atlas Response**

```text
 

The engagement letter has been extracted and an Inbox task has already been created for review. The document contains the following key terms:

**Client & Engagement:**
- Client: Nexus Capital Partners LP
- Engagement: Nexus Capital Partners - Group Accounting & Advisory
- Period: 1 January 2026 – 31 December 2026
- Currency: GBP

**Billing Structure (Mixed):**
- Fixed fee: GBP 42,000
- Monthly retainer: GBP 8,500
- Time-and-materials CFO advisory work
- Total engagement value: GBP 144,000

**Rate Card:**
- CFO Advisory Partner: GBP 350/hr
- Manager: GBP 240/hr
- Associate: GBP 145/hr

**First Project:**
- Name: Statutory Accounts - FY2025
- Scope: Preparation of FY2025 statutory group consolidation pack and supporting schedules

An Inbox task (priority: medium) has been created for you to review the extracted terms before they are applied. The agent confidence is 100%, but this still requires human sign-off before the client, engagement, billing terms, rate card, and project are created in Aethos.

**Next step:** Review the task in Inbox and approve to complete the onboarding. The extraction has flagged no injection risks, but please verify the engagement dates, fixed/retainer amounts, and rate card align with the original letter before confirming.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Extracts the uploaded Nexus engagement letter instead of asking the user to retype it. | Creates or prepares client, engagement, billing terms, rate card, and first project. | Routes risky or incomplete items to Inbox.
Matched required signals: /Nexus/i, /client/i, /engagement/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i, /Inbox|review|risk/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-1-engagement-letter-response.png](screenshots/1-1-engagement-letter-response.png)

## 1-2-engagement-structure - 1.2 Project structure

**Prompt**

```text
Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.
```

**Observed Atlas Response**

```text
 

Now I'll load the engagement structure tool to get the details for Nexus Capital Partners.

Now I'll call the engagement structure read pack for Nexus Capital Partners:

The search for "Nexus Capital Partners" returned no engagements. Let me search the full engagement list to see what's available and verify the client name:

I searched the engagement list and did not find an engagement for a client named "Nexus Capital Partners". The system contains engagements for six other clients, but none match that name.

The closest match I see is "SB Northwind Capital Partners" (ENG-0001), but that's a different client. 

Could you confirm:
- Is the client name "Nexus Capital Partners" exact, or could it be under a different name (perhaps with "SB" prefix or a variant)?
- Or did you mean "SB Northwind Capital Partners"?

If you'd like, I can pull the full engagement structure details for any of the existing clients listed above. All current engagements are in draft status and all are missing billing terms and rate cards, which would be required before billing can proceed.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 2/4 required signals; forbidden hits 0.
Criteria: Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.
Matched required signals: /Nexus/i, /missing|ready|before billing|setup/i
Missing required signals: /project|workstream/i, /billing model|fixed|retainer|T&M|time and materials/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-2-engagement-structure-response.png](screenshots/1-2-engagement-structure-response.png)

## 1-3-log-time - 1.3 Time entry

**Prompt**

```text
Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling
```

**Observed Atlas Response**

```text
 Unable to prepare the time entry.
- Status: failed; Project, hours, date, and exact description are required.
- No time entry was posted or approved.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 1/5 required signals; forbidden hits 0.
Criteria: Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.
Matched required signals: /time|hours/i
Missing required signals: /4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /logged|created|Inbox|approval/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-3-log-time-response.png](screenshots/1-3-log-time-response.png)

## 1-3a-delivery-data - 1.3A People and WIP

**Prompt**

```text
Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.
```

**Observed Atlas Response**

```text
 

Now I'll call the delivery read pack with Alice Chen's details for June:

Let me retry with a simpler request to fetch Alice Chen's delivery data:

I just pulled Alice Chen's delivery data from Aethos. The system queried August 2026 (the current month in the system) by default since June wasn't available in my initial filter. Here's what the data shows:

**Alice Chen — Delivery Summary (August 2026)**

Approved time: 0 hours
Pending time: 0 hours
Billable expenses: $0.00
Utilization: 0.00%
WIP value: $0.00
Invoice-ready entries: 0 time entries, 0 expenses

There are no active time entries, approved or pending, no billable expenses, and no work-in-progress recorded for Alice Chen in Aethos at this point. No entries are ready to invoice for Nexus or any other client.

If you're looking for June 2026 data specifically (rather than the current August period), or if Alice Chen should have billable activity recorded, please check:
- Whether time entries and expenses have been logged and submitted for approval
- Whether they're associated with a Nexus engagement in Aethos
- The approval workflow status for any pending submissions

Would you like me to check a different time period or verify Alice's engagement assignments with Nexus?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Summarizes Alice Chen June delivery, utilization, WIP, expenses, and invoice readiness for Nexus.
Matched required signals: /Alice Chen|Alice/i, /June/i, /approved time|pending time|hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice|invoiced/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-3a-delivery-data-response.png](screenshots/1-3a-delivery-data-response.png)

## 1-4-billing-run - 1.4 Mixed model invoice

**Prompt**

```text
Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending.
```

**Observed Atlas Response**

```text
 

I'll prepare the June 2026 billing run for Nexus. Let me fetch the engagement and WIP data, then draft the invoice for Inbox review.

I don't see a client named "Nexus" in the active engagements. The available engagements are for:
- SB Northwind Capital Partners (retainer)
- SB Belmont Industrial Group (time & materials)
- SB Cascade Health Systems (milestone)
- SB Ironwood Energy Corp (fixed fee)
- SB Sterling Retail Holdings (retainer)
- SB Vertex Semiconductor Inc (fixed fee)

WIP is currently zero across all projects, and there are no approved expenses or invoiceable time entries for June 2026.

Could you clarify which client the June 2026 billing run should cover? Alternatively, if Nexus is a new client or engagement not yet in the system, I'll need the client name and engagement details to proceed with the invoice draft.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/8 required signals; forbidden hits 2.
Criteria: Prepares Nexus June billing run with fixed fee, retainer, T&M hours, expenses, draft invoice lines, and Inbox routing.
Matched required signals: /Nexus/i, /June 2026|June/i, /fixed fee/i, /retainer/i, /expense/i, /Inbox|approval/i
Missing required signals: /T&M|time and materials|hour/i, /invoice line|draft invoice/i
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i, /couldn'?t locate|not showing up|not found|no .* on file|need .* from you|need .* details|need more information|need some details/i

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-4-billing-run-response.png](screenshots/1-4-billing-run-response.png)

## 1-5-revenue-recognition - 1.5 Revenue recognition

**Prompt**

```text
Explain how Nexus June revenue is recognized across fixed-fee milestone, retainer, T&M advisory WIP, and expenses. Tie the explanation to invoice-backed journals and Project P&L.
```

**Observed Atlas Response**

```text
 

Now let me pull the engagement structure and management pack to show you real Nexus June data:

Let me fetch the June management pack data:

## June Revenue Recognition: Breakdown by Billing Model & Invoice-Backed Journals

June delivered total revenue of **269,166 USD/GBP** across six engagements, split across fixed-fee, milestone, retainer, and time-and-materials models. Here's how each revenue stream was recognized into the general ledger and tied to customer invoices and Project P&L.

### Revenue by Billing Arrangement (June 2026)

**Fixed-Fee Engagements (2 total):**
- SB Ironwood Tech Transformation (USD): 42,500 invoiced; recognized to revenue on invoice issue date (June 15), posted to Delivery project PRJ-0009. Journal JE-INV-INV-0004.
- SB Vertex UK Advisory (GBP): 10,000 invoiced; recognized to revenue on invoice issue date (June 16), posted to Delivery project PRJ-0012. Journal JE-INV-INV-0007.
- Subtotal: 52,500 USD + 10,000 GBP

**Milestone Engagements (1 total):**
- SB Cascade Transaction Advisory (USD): 125,000 invoiced for first milestone achievement; recognized to revenue on invoice issue date (June 15), posted to Delivery project PRJ-0008. Journal JE-INV-INV-0003.
- Subtotal: 125,000 USD

**Retainer Engagements (2 total):**
- SB Northwind Risk Retainer (USD): 15,000 (June monthly billing); recognized to revenue on invoice issue date (June 15), posted to Delivery project PRJ-0006. Journal JE-INV-INV-0001.
- SB Sterling Retail FinOps (USD): 6,000 (June monthly billing); recognized to revenue on invoice issue date (June 15), posted to Delivery project PRJ-0010. Journal JE-INV-INV-0005.
- Subtotal: 21,000 USD

**Time & Materials (1 total):**
- SB Belmont Consulting (USD): 69,776 invoiced for cumulative T&M hours logged and reimbursable expenses; recognized to revenue on invoice issue date (June 15, 18), posted to Delivery project PRJ-0007. Journals JE-INV-INV-0002 and JE-INV-INV-0006.
- Subtotal: 69,776 USD

### Invoice-Backed Journal Flow

Each invoice created an automatic accounts receivable (AR) journal entry on the invoice issue date. All journals were posted by July 20–21, 2026:

1. **INV-0001 (Northwind retainer, 15,000 USD)** → JE-INV-INV-0001 → DR AR 1200, CR Revenue 4000
2. **INV-0002 (Belmont T&M, 48,000 USD, paid)** → JE-INV-INV-0002 → DR AR 1200, CR Revenue 4000; Payment received June 20 → JE-5284A950 → DR Bank, CR AR
3. **INV-0003 (Cascade milestone, 125,000 USD)** → JE-INV-INV-0003 → DR AR 1200, CR Revenue 4000
4. **INV-0004 (Ironwood fixed-fee, 42,500 USD)** → JE-INV-INV-0004 → DR AR 1200, CR Revenue 4000
5. **INV-0005 (Sterling retainer, 6,000 USD, paid)** → JE-INV-INV-0005 → DR AR 1200, CR Revenue 4000; Payment received June 20 → JE-4E27694F → DR Bank, CR AR
6. **INV-0006 (Belmont T&M, 21,776 USD)** → JE-INV-INV-0006 → DR AR 1200, CR Revenue 4000
7. **INV-0007 (Vertex fixed-fee, 10,000 GBP)** → JE-INV-INV-0007 → DR AR 1200, CR Revenue 4000

### Working Capital & Receivables Position

- Open AR total: **201,942 US
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Explains Nexus revenue recognition across milestone/fixed fee, retainer, T&M WIP, expenses, journals, and Project P&L.
Matched required signals: /Nexus/i, /revenue/i, /fixed fee|milestone/i, /retainer/i, /T&M|WIP|time and materials/i, /expense/i, /journal/i, /Project P&L|project/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-5-revenue-recognition-response.png](screenshots/1-5-revenue-recognition-response.png)

## 1-6-capped-tax - 1.6 Capped tax engagement

**Prompt**

```text
Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun
```

**Observed Atlas Response**

```text
 I'll help you create that engagement for Nexus. Let me first load the engagement workflow skill and then prepare the engagement for review.

Now I'll create the engagement with the billing structure you specified:

Done. I've created an engagement draft for Nexus and routed it to Aethos Inbox for approval.

**Engagement Details:**
- Client: Nexus
- Engagement: Corporation Tax Return FY2025
- Service line: Tax
- Currency: GBP
- Fixed fee: £18,500
- Cap: £22,000
- Billing arrangement: Capped (fixed fee with advisory hour cap)
- First project: FY2025 Corporate Tax Return

The engagement is now pending review in your Inbox. Once approved, the engagement and its initial project will be set up and ready for time logging and billing.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Creates or prepares Nexus capped tax engagement with fixed fee, cap, and Inbox approval if required.
Matched required signals: /Nexus/i, /Corporation Tax|Tax Return|FY2025/i, /18,?500|18500/i, /22,?000|22000|cap/i, /engagement/i, /Inbox|approval|created/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-6-capped-tax-response.png](screenshots/1-6-capped-tax-response.png)

## 1-7-o2c-readiness - 1.7 O2C controls

**Prompt**

```text
Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval.
```

**Observed Atlas Response**

```text
 Nexus order-to-cash readiness for June 2026:
- Service catalogue mapping: fixed fee statutory accounts, monthly retainer management accounts, T&M advisory, and approved expenses must map to active professional-services catalogue items before billing.
- Linked rate card: Nexus CFO Advisory uses the reviewed rate-card terms from the engagement letter; confirm hourly rates before final invoice approval.
- Tax setup: UK VAT/tax rate must be present before invoice posting; missing tax setup blocks posting and points the user to Settings / Tax Rates.
- Draft invoices/public invoice readiness: draft invoice lines remain in Inbox before send; payment link or public invoice link should be checked only after send approval.
- WIP: approved billable time and approved expenses are invoice-ready; unapproved or non-billable entries stay out of the draft invoice.
- Collections: any customer reminder or external collections email must route to Inbox approval before sending; disputed or hold invoices must not be chased.
- Approval boundary: invoice send, payment-link publication, collections email, voiding, and backdated posting remain controlled actions.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Reviews Nexus O2C readiness across service catalogue, rate card, tax, invoices, payment links, WIP, and collections approvals.
Matched required signals: /Nexus/i, /service catalogue|catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link|public invoice/i, /WIP/i, /collections/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-7-o2c-readiness-response.png](screenshots/1-7-o2c-readiness-response.png)

## 1-7-collections-read - 1.7 Collections read pack

**Prompt**

```text
Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.
```

**Observed Atlas Response**

```text
 Collections readout:
- Totals: 4 open invoices; 4 overdue; balances {'USD': '189276.0', 'GBP': '10000.0'}.
- SB Ironwood Energy Corp invoice INV-0004: due 2026-07-15; aging 0_30; balance USD 42500.0; payment status unpaid; reminder count 3; policy stage firm; blockers ['max_reminders_reached', 'cooldown_active']; next action Escalate to the finance manager; the configured reminder limit is reached..
- SB Belmont Industrial Group invoice INV-0002: due 2026-07-15; aging paid; balance USD 0.0; payment status paid; reminder count 0; policy stage none; blockers ['invoice_paid']; next action No collections action; the invoice is paid..
- SB Cascade Health Systems invoice INV-0003: due 2026-07-15; aging 0_30; balance USD 125000.0; payment status unpaid; reminder count 3; policy stage firm; blockers ['max_reminders_reached', 'cooldown_active']; next action Escalate to the finance manager; the configured reminder limit is reached..
- SB Northwind Capital Partners invoice INV-0001: due 2026-07-15; aging paid; balance USD 0.0; payment status paid; reminder count 0; policy stage none; blockers ['invoice_paid']; next action No collections action; the invoice is paid..
- SB Sterling Retail Holdings invoice INV-0005: due 2026-07-15; aging paid; balance USD 0.0; payment status paid; reminder count 0; policy stage none; blockers ['invoice_paid']; next action No collections action; the invoice is paid..
- SB Vertex Semiconductor Inc invoice INV-0007: due 2026-07-30; aging 0_30; balance GBP 10000.0; payment status unpaid; reminder count 1; policy stage gentle; blockers ['cooldown_active']; next action Wait for the collections cooldown before drafting another reminder..
- SB Belmont Industrial Group invoice INV-0006: due 2026-08-01; aging 0_30; balance USD 21776.0; payment status unpaid; reminder count 1; policy stage gentle; blockers ['cooldown_active']; next action Wait for the collections cooldown before drafting another reminder..
Any customer reminder email must be drafted to Inbox and approved before sending.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Shows collections customers with balances, invoices, due dates, aging, reminders, blockers, and next action without drafting.
Matched required signals: /customer/i, /balance/i, /invoice/i, /due date|due/i, /aging|overdue/i, /reminder/i, /blocker|blocked/i, /next action/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-7-collections-read-response.png](screenshots/1-7-collections-read-response.png)

## 1-7-invoice-drilldown - 1.7 Invoice drilldown

**Prompt**

```text
Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action.
```

**Observed Atlas Response**

```text
 Invoice INV-1001 drilldown:
- Due date: review against the invoice due date; aging is current/overdue based on that due date.
- Balance: show balance due, paid or partially paid amount, and remaining payment exposure.
- Public invoice/payment link: public invoice and payment-link state must be confirmed before customer follow-up.
- Reminder history: show last reminder, count, collections policy stage, and cooldown/max-reminder blockers.
- Recommended next action: if collectible, draft a customer-specific reminder to Inbox; if disputed/on hold, resolve blocker before sending.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Reviews INV-1001 with due date, aging, balance, paid status, payment link, reminders, blockers, and next action.
Matched required signals: /INV-1001/i, /due date|due/i, /aging|overdue/i, /balance/i, /paid|payment/i, /reminder/i, /blocker|blocked/i, /next action|recommend/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-7-invoice-drilldown-response.png](screenshots/1-7-invoice-drilldown-response.png)

## 1-7-draft-reminders - 1.7 Collections controlled write

**Prompt**

```text
Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.
```

**Observed Atlas Response**

```text
 

Now I'll read the collections data from Aethos and draft reminder emails routed to Inbox:

No collections reminders were routed to Inbox for approval.

Here's what Aethos found:

**Eligible invoices:** 0 drafts matched your 30+ days overdue criteria and passed collections policy.

**Skipped invoices (4 total):**

1. **SB Cascade Health Systems** — Invoice INV-0003 (21 days overdue)
   Reason: Maximum reminders already sent for this invoice; suppressed to avoid over-contact.

2. **SB Ironwood Energy Corp** — Invoice INV-0004 (21 days overdue)
   Reason: Maximum reminders already sent; suppressed.

3. **SB Vertex Semiconductor Inc** — Invoice INV-0007 (6 days overdue)
   Reason: Below 30-day threshold and cooldown active from recent reminder.

4. **SB Belmont Industrial Group** — Invoice INV-0006 (4 days overdue)
   Reason: Below 30-day threshold and cooldown active.

**Next actions:**
- Monitor Aethos collections aging to surface new invoices crossing 30 days.
- Review collections policy if you want to override reminder caps or shorten cooldown cycles for specific customers.
- If you need to manually draft reminders for customers already at max reminders, escalate through Aethos O2C to adjust customer escalation status.

No customer emails were created or sent.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Drafts customer-specific reminders for invoices over 30 days overdue and routes them to Inbox before sending.
Matched required signals: /reminder/i, /invoice/i, /30 days|overdue/i, /customer/i, /Inbox|approval/i, /draft/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/1-7-draft-reminders-response.png](screenshots/1-7-draft-reminders-response.png)

## 2-1-retainer - 2.1 Monthly retainer billing

**Prompt**

```text
Prepare Brightwater Manufacturing monthly retainer billing for June 2026. Show the draft invoice, any tax, and route it to Inbox before sending.
```

**Observed Atlas Response**

```text
 Brightwater monthly retainer billing for June 2026 is prepared as a draft invoice.
- Billing model: monthly retainer for management accounts.
- Draft invoice: retainer line plus applicable tax/VAT.
- Tax: confirm configured tax rate before posting.
- Approval: route the invoice to Inbox before sending; no customer invoice was sent directly.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Prepares Brightwater monthly retainer billing with draft invoice, tax, and Inbox routing.
Matched required signals: /Brightwater/i, /retainer/i, /June 2026|June/i, /invoice/i, /tax/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/2-1-retainer-response.png](screenshots/2-1-retainer-response.png)

## 2-2-milestone - 2.2 Annual accounts milestone

**Prompt**

```text
Prepare the Brightwater Annual Accounts FY2025 milestone invoice. Include the milestone basis, tax treatment, and approval path before sending.
```

**Observed Atlas Response**

```text
 Brightwater Annual Accounts FY2025 milestone invoice is prepared for approval.
- Basis: Annual Accounts FY2025 milestone achieved.
- Draft invoice: milestone billing line with tax treatment shown before posting.
- Approval path: partner/finance review in Inbox before sending to Brightwater.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Prepares Brightwater Annual Accounts milestone invoice with basis, tax treatment, and approval path.
Matched required signals: /Brightwater/i, /Annual Accounts|FY2025/i, /milestone/i, /invoice/i, /tax/i, /approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/2-2-milestone-response.png](screenshots/2-2-milestone-response.png)

## 2-3-payroll - 2.3 Payroll billing

**Prompt**

```text
Prepare Brightwater payroll billing for June 2026 based on active employee count. Show per-employee billing, invoice total, and any approval needed.
```

**Observed Atlas Response**

```text
 Brightwater payroll billing for June 2026 is ready for review.
- Basis: active employee count multiplied by the per-employee payroll service fee.
- Invoice: payroll billing line shows employee count, unit rate, subtotal, tax, and invoice total.
- Approval: route to Inbox before sending; reviewer confirms count and total.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Prepares Brightwater payroll billing from active employee count with total and approval need.
Matched required signals: /Brightwater/i, /payroll/i, /employee/i, /count/i, /invoice|billing/i, /total/i, /approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/2-3-payroll-response.png](screenshots/2-3-payroll-response.png)

## 2-4-vendor-invoice - 2.4 Vendor invoice intake

**Prompt**

```text
Process this vendor invoice for Brightwater. Match it to the right vendor and project, flag duplicate risk, code it to the right account, compare any PO or service-order evidence, and send exceptions to Inbox.
```

**Observed Atlas Response**

```text
 Brightwater vendor invoice intake review:
- Vendor/subcontractor: match Forster & Reid Ltd or the closest vendor record, with reviewer confirmation if confidence is amber.
- Bill/invoice: create a bill draft only after extraction review; keep exceptions in Inbox.
- Project: link to Brightwater Annual Accounts or the supported project/customer hint.
- Duplicate guard: compare vendor invoice number, amount, date, source document, and vendor before approval.
- Account/coding: suggest Project Costs - Subcontractors or the configured account code.
- PO/service-order evidence: show approved PO, service-order, or no-match exception.
- Inbox: route vendor, duplicate, coding, PO/service-order, and source-document exceptions to Inbox.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Extracts the uploaded Brightwater subcontractor invoice. | Matches vendor/project, codes account, checks duplicate and PO/service-order evidence, and routes exceptions to Inbox.
Matched required signals: /Brightwater/i, /vendor|subcontractor/i, /bill|invoice/i, /project/i, /duplicate/i, /account|code/i, /PO|purchase order|service-order|service order/i, /Inbox|exception/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/2-4-vendor-invoice-response.png](screenshots/2-4-vendor-invoice-response.png)

## 2-4-payment-risk-read - 2.4 P2P read pack

**Prompt**

```text
Which vendor bills are due soon, which are blocked, and what evidence supports payment? Show vendor, bill number, amount, due date, status, coding evidence, source document, duplicate risk, PO/service-order match, payment-batch state, blockers, and next action. Do not create a payment batch yet.
```

**Observed Atlas Response**

```text
 Vendor bill and payment-risk read pack:
- Vendor: show vendor name for each bill and due-soon total.
- Bill: show bill number, amount, due date, and status.
- Evidence/source document: show invoice source, coding evidence, duplicate status, and PO/service-order match.
- Blockers: duplicate risk, PO mismatch, missing bank details, approval gaps, or disputed status block payment.
- Payment state: show payment-batch state, cash impact, approver/approval role, and next action.
- Control: do not create a payment batch unless explicitly requested; payment batches route to Inbox before export/send/settlement.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 9/9 required signals.
Criteria: Shows due/blocked vendor bills with evidence, duplicate risk, PO match, payment state, blockers, and next action without batching.
Matched required signals: /vendor/i, /bill/i, /due date|due soon|overdue/i, /blocked|blocker/i, /evidence|source document/i, /duplicate/i, /PO|service order/i, /payment/i, /next action/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/2-4-payment-risk-read-response.png](screenshots/2-4-payment-risk-read-response.png)

## 2-4-single-bill - 2.4 Single bill drilldown

**Prompt**

```text
Review bill BILL-1001. Show due date, amount, vendor invoice number, coding status, source document, duplicate signals, PO/service-order match, approval state, payment readiness, existing batch status, and recommended next action.
```

**Observed Atlas Response**

```text
 Brightwater vendor invoice intake review:
- Vendor/subcontractor: match Forster & Reid Ltd or the closest vendor record, with reviewer confirmation if confidence is amber.
- Bill/invoice: create a bill draft only after extraction review; keep exceptions in Inbox.
- Project: link to Brightwater Annual Accounts or the supported project/customer hint.
- Duplicate guard: compare vendor invoice number, amount, date, source document, and vendor before approval.
- Account/coding: suggest Project Costs - Subcontractors or the configured account code.
- PO/service-order evidence: show approved PO, service-order, or no-match exception.
- Inbox: route vendor, duplicate, coding, PO/service-order, and source-document exceptions to Inbox.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 5/9 required signals; forbidden hits 0.
Criteria: Reviews BILL-1001 with due date, vendor invoice number, coding, source, duplicate, approval, payment readiness, and next action.
Matched required signals: /vendor invoice/i, /coding|coded|account/i, /source document|source/i, /duplicate/i, /approval/i
Missing required signals: /BILL-1001/i, /due date|due/i, /payment readiness|payment/i, /next action|recommend/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/2-4-single-bill-response.png](screenshots/2-4-single-bill-response.png)

## 2-5-bill-pay - 2.5 Payment controls

**Prompt**

```text
Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox.
```

**Observed Atlas Response**

```text
 

I'll pull the payment-risk data to identify due and overdue approved bills, then prepare a payment batch excluding any disputed items.

Based on the payment-risk data, I can see that the only overdue approved bill (BILL-0002 from Vendor SB CloudScale Infrastructure) is blocked and cannot be included in this week's payment batch. Let me prepare and submit the payment batch.

**Bill-Pay Run Analysis**

Rationale for this week's batch:

1. BILL-0001 (Vendor: SB Apex Contractors LLC, USD 28,000.00) — Already paid on 2026-06-25. No payment action needed.

2. BILL-0002 (Vendor: SB CloudScale Infrastructure, USD 12,000.00) — Approved and overdue by 22 days (due 2026-07-14), but BLOCKED from payment because:
   - Bill coding incomplete (0 of 1 line coded)
   - Source document missing
   These blockers must be resolved before payment can proceed. No dispute is present, but evidence gaps prevent execution.

**Payment Batch Submission**

Since no bills are both approved and payable this week (the only approved bill is blocked by missing coding and evidence), I am submitting an empty/hold batch to Inbox for review and next-step direction:

**Bill-Pay Run Submitted to Inbox**

The weekly payment batch has been routed to Aethos Inbox for review:

**Batch Summary:**
- Batch ID: 962edf08-7aa9-4d7a-abd8-3640e7b0edc0
- Status: Pending Inbox review
- Payable bills this week: 0
- Total payment amount: USD 0.00

**Excluded Bills & Rationale:**

1. **BILL-0002 (Vendor: SB CloudScale Infrastructure)** — USD 12,000.00, overdue 22 days
   - Approval Status: Approved for payment review ✓
   - Dispute Status: No disputes ✓
   - Blockers: Bill coding incomplete + source document missing
   - Action: Hold until complete bill coding (P&L account) and attach vendor invoice. This prevents duplicate payment risk and ensures full audit evidence.

2. **BILL-0001 (Vendor: SB Apex Contractors LLC)** — USD 28,000.00, paid 25 days ago
   - Already settled in batch 2a56e505-c5ae-4049-8800-87267758e09f

**Next Steps:**
1. Finance team to complete bill coding on BILL-0002
2. Upload source invoice document to BILL-0002
3. Resubmit for payment in next run once blockers cleared

Inbox task created for your review and approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Prepares a bill-pay run for due/overdue approved bills, excludes disputed items, explains rationale, and routes batch to Inbox.
Matched required signals: /bill-pay|payment/i, /due|overdue/i, /approved/i, /disputed|exclude/i, /rationale|reason/i, /batch/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/2-5-bill-pay-response.png](screenshots/2-5-bill-pay-response.png)

## 2-5-payment-packet - 2.5 Payment approval packet

**Prompt**

```text
Prepare a payment approval packet for bills due in the next 10 days. Include vendor, amount, due date, coding evidence, duplicate status, cash impact, and the approver role required for the batch.
```

**Observed Atlas Response**

```text
 Vendor bill and payment-risk read pack:
- Vendor: show vendor name for each bill and due-soon total.
- Bill: show bill number, amount, due date, and status.
- Evidence/source document: show invoice source, coding evidence, duplicate status, and PO/service-order match.
- Blockers: duplicate risk, PO mismatch, missing bank details, approval gaps, or disputed status block payment.
- Payment state: show payment-batch state, cash impact, approver/approval role, and next action.
- Control: do not create a payment batch unless explicitly requested; payment batches route to Inbox before export/send/settlement.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Prepares payment approval packet with vendor, amount, due date, coding evidence, duplicate status, cash impact, and approver role.
Matched required signals: /vendor/i, /amount/i, /due date|due/i, /coding evidence|coding/i, /duplicate/i, /cash impact|cash/i, /approver|approval role/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/2-5-payment-packet-response.png](screenshots/2-5-payment-packet-response.png)

## 3-1-family-office - 3.1 Family office structure

**Prompt**

```text
Show the Alderton Family Office structure. List each engagement, service line, billing model, currency, open projects, and missing setup before billing.
```

**Observed Atlas Response**

```text
 Alderton Family Office structure:
- Engagements: family investment company accounts, trading group management accounts, trust accounts and tax, personal tax returns, and COSEC retainer.
- Service lines: accounting, trust/tax, personal tax, and COSEC.
- Billing models: fixed fee, monthly retainer, T&M/advisory where scoped, and per-event COSEC where applicable.
- Currency: GBP base with SGD trust activity where foreign income applies.
- Projects: open projects sit under each engagement; missing setup before billing includes rate/card terms, tax setup, approval state, and source evidence.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Shows Alderton family office engagements, service lines, billing models, currency, projects, and missing setup.
Matched required signals: /Alderton/i, /engagement/i, /service line|service/i, /billing model|fixed|retainer|T&M/i, /currency|GBP|SGD|USD/i, /project/i, /missing|setup/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/3-1-family-office-response.png](screenshots/3-1-family-office-response.png)

## 3-2-scope-creep - 3.2 Scope creep risk

**Prompt**

```text
Review Alderton bespoke tax return scope. Compare actual time, fixed fee, expected margin, open WIP, and recommend whether we need a fee adjustment before billing.
```

**Observed Atlas Response**

```text
 Alderton bespoke tax return scope review:
- Actual time/hours should be compared with the fixed fee and expected margin.
- Open WIP and additional CGT/trust complexity create scope-creep risk.
- Margin: if actual time erodes expected margin, recommend a fee adjustment before billing.
- Recommendation: prepare a supplemental fee quote and route engagement/billing changes to Inbox approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Compares Alderton bespoke tax actual time, fixed fee, expected margin, WIP, and fee adjustment recommendation.
Matched required signals: /Alderton/i, /bespoke tax|tax return/i, /actual time|hours/i, /fixed fee/i, /margin/i, /WIP/i, /fee adjustment|recommend/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/3-2-scope-creep-response.png](screenshots/3-2-scope-creep-response.png)

## 3-3-sgd-journal - 3.3 Multi-currency trust accounts

**Prompt**

```text
Prepare an SGD 18,000 dividend income journal for Alderton Trust for June 2026. Show the GBP base-currency impact, FX rate provenance, required approval role, and route it to Inbox before posting.
```

**Observed Atlas Response**

```text
 Prepared the manual journal review packet and routed it to Inbox before posting.
Requested transaction: SGD 18000.00 with GBP base-currency impact 10533.60. FX provenance: SGD->GBP rate 0.5852 from fx_rates dated 2026-05-19..
Review path: /app/inbox; task id: 2290ce96-7aab-4fbe-b4f0-2b447d1c8d1a; approval boundary: Do not post without Inbox approval.
Journal lines:
- DR 1100 Bank: SGD 18000.00 (base GBP 10533.60).
- CR 4000 Revenue: SGD 18000.00 (base GBP 10533.60).
Control checks: balanced yes; debits 18000.00; credits 18000.00; account validity valid; period lock status open.
Business reason: Record foreign dividend income for trust accounts before month-end close.. Supporting evidence: Dividend notice or bank/source document must be attached in Inbox before approval..
Required approval role: finance_controller; segregation of duties: Approver must be different from the submitter before posting.
Do not post without Inbox approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Prepares SGD dividend income journal with GBP impact, FX provenance, approval role, and Inbox routing before posting.
Matched required signals: /SGD/i, /18,?000|18000/i, /dividend/i, /journal/i, /GBP/i, /FX|exchange rate/i, /approval role|approval/i, /Inbox/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/3-3-sgd-journal-response.png](screenshots/3-3-sgd-journal-response.png)

## 3-4-cosec-reminders - 3.4 COSEC reminders

**Prompt**

```text
Review COSEC filing reminders for Alderton entities. Show upcoming filing dates, missing evidence, billing impact, and which reminders need approval before sending.
```

**Observed Atlas Response**

```text
 COSEC filing reminders are ready for review. No reminder has been sent; client communications require Inbox approval before sending.
Summary: 0 reminder(s), 0 with missing evidence, 0 requiring approval.
- No COSEC compliance-calendar rows matched this query. Check engagement setup before promising a filing deadline.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 5/7 required signals; forbidden hits 0.
Criteria: Reviews Alderton COSEC filing reminders, evidence gaps, billing impact, and approvals before sending.
Matched required signals: /COSEC/i, /filing/i, /date|deadline/i, /evidence|missing/i, /approval|before sending/i
Missing required signals: /Alderton/i, /billing impact|billing/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/3-4-cosec-reminders-response.png](screenshots/3-4-cosec-reminders-response.png)

## 4-1-usd-engagement - 4.1 USD-billed engagement

**Prompt**

```text
Explain Thornton June billing and cash position in USD and GBP. Show invoice amount, base-currency journal impact, FX rate provenance, AR status, and cash-flow effect after payment.
```

**Observed Atlas Response**

```text
 Thornton June billing and cash position:
- Invoice: show USD invoice amount and GBP base-currency journal impact.
- FX provenance: use the stored exchange rate/fx_rates row for USD to GBP conversion.
- AR status: invoice remains in AR/accounts receivable until payment clears.
- Cash-flow effect: after payment, cash increases and AR reduces; realized FX is recorded if settlement rate differs.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Explains Thornton June billing/cash in USD and GBP with invoice, FX provenance, AR status, and cash-flow effect.
Matched required signals: /Thornton/i, /June/i, /USD/i, /GBP/i, /invoice/i, /FX|exchange rate/i, /AR|accounts receivable/i, /cash[- ]flow|cash flow/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/4-1-usd-engagement-response.png](screenshots/4-1-usd-engagement-response.png)

## 4-2-series-a - 4.2 Series A milestone

**Prompt**

```text
Thornton Series A closed at $14.2M. Update the milestone amount and invoice. Route any revenue or billing change to Inbox before sending.
```

**Observed Atlas Response**

```text
 Thornton Series A milestone update prepared for review.
- Event: Series A close at USD 14.2M.
- Success-fee billing model: 0.75% milestone payable on closing.
- Draft milestone invoice amount: USD 106,500.00.
- Revenue/billing change: route to Inbox before sending; do not send the invoice or post revenue without approval.
- Evidence to review: engagement milestone terms, closing confirmation, project P&L, and invoice draft.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Updates or prepares Thornton Series A milestone invoice for $14.2M and routes revenue/billing changes to Inbox.
Matched required signals: /Thornton/i, /Series A/i, /14\.2M|14,?200,?000|\$14\.2/i, /milestone/i, /invoice/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/4-2-series-a-response.png](screenshots/4-2-series-a-response.png)

## 4-3-cosec-instruction - 4.3 COSEC instruction

**Prompt**

```text
Review this COSEC instruction for Thornton. Identify the company change, create the required filing/project work item, identify billing impact, and route any external filing or invoice action to Inbox.
```

**Observed Atlas Response**

```text
 Thornton COSEC instruction review:
- Company change: identify the statutory company change from the instruction.
- Filing/project work item: create the required COSEC filing task and project work item for review.
- Billing impact: show whether the filing is included, per-event, or out-of-scope billing.
- Control: route any external filing or invoice action to Inbox approval before sending/submitting.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Extracts Thornton COSEC instruction, identifies company change, creates filing/project work item, billing impact, and Inbox routing.
Matched required signals: /Thornton/i, /COSEC/i, /company change|change/i, /filing/i, /project|work item/i, /billing impact|billing/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/4-3-cosec-instruction-response.png](screenshots/4-3-cosec-instruction-response.png)

## 5-1-close-readiness - 5.1 Pre-close checklist

**Prompt**

```text
Run June 2026 pre-close checks. Show AR, AP, WIP, unposted journals, close tasks, missing approvals, and what needs to happen before the period can be locked.
```

**Observed Atlas Response**

```text
 Pre-close checks for June 2026:
- AR/accounts receivable: review aging, unapplied receipts, and invoice approvals.
- AP/accounts payable: review due/blocked vendor bills and payment batches.
- WIP: resolve unbilled approved time and expenses.
- Unposted journals: draft/unposted journals block close until approved, posted, rejected, or waived.
- Close tasks and approvals: incomplete close tasks, missing approvals, and lock blockers must be cleared before period lock.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Runs June pre-close checks across AR, AP, WIP, unposted journals, close tasks, approvals, and period-lock blockers.
Matched required signals: /June 2026|June/i, /AR|accounts receivable/i, /AP|accounts payable/i, /WIP/i, /unposted journal|journal/i, /close task|close/i, /approval/i, /lock|period/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-1-close-readiness-response.png](screenshots/5-1-close-readiness-response.png)

## 5-2-period-lock - 5.2 Period lock

**Prompt**

```text
Can we lock June 2026? Show the period-lock readiness result, blockers, overrides if any, and what a Controller or Owner must review before locking.
```

**Observed Atlas Response**

```text
 June 2026 period-lock readiness:
- Readiness: not ready until AR, AP, WIP, unposted journal, and close-task blockers are resolved.
- Blockers: incomplete close tasks, draft journals, pending approvals, or missing reconciliations.
- Overrides: Controller or Owner must review and document any override reason.
- Lock control: locking the period is an Inbox/role-controlled action; I did not lock the period.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Assesses June 2026 period-lock readiness with blockers, overrides, and Controller/Owner review.
Matched required signals: /June 2026/i, /lock|period/i, /readiness|ready/i, /blocker/i, /override/i, /Controller|Owner/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-2-period-lock-response.png](screenshots/5-2-period-lock-response.png)

## 5-3-trial-balance - 5.3 Trial Balance

**Prompt**

```text
Show the June 2026 Trial Balance. Confirm whether debits equal credits, summarize the largest account movements, and flag suspense or unbalanced items.
```

**Observed Atlas Response**

```text
 Trial Balance for June 2026:
- Debits and credits must balance; any difference is an unbalanced item.
- Largest account movements should be summarized by account with debit/credit movement.
- Suspense account and unbalanced items must be flagged before close.
- Use the Reports / Trial Balance view for the full account listing.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Shows June 2026 Trial Balance, debit/credit balance, largest movements, and suspense/unbalanced items.
Matched required signals: /June 2026/i, /Trial Balance/i, /debit/i, /credit/i, /balance|balanced/i, /movement|largest/i, /suspense|unbalanced/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-3-trial-balance-response.png](screenshots/5-3-trial-balance-response.png)

## 5-4-management-reporting - 5.4 Management reporting

**Prompt**

```text
Alice is at 64% utilisation in June. Which clients have unbilled WIP tied to Alice?
```

**Observed Atlas Response**

```text
 Delivery and utilization context for Alice in June 2026:
- Utilization: Alice is at 64% utilisation in June, below the target benchmark for her role.
- Client with unbilled WIP: Nexus Capital Partners; Alice has unbilled CFO Advisory WIP tied to the Nexus engagement.
- Invoice-ready work: include approved billable time, approved billable expenses, and any WIP that passed approval controls.
- Not invoice-ready: pending time, rejected time, non-billable internal work, and expenses missing approval or evidence.
- Management action: review Alice's allocation, clear pending approvals, and route any invoice draft to Inbox before sending.
Use WIP and Project P&L reports for the full client detail; I did not create an invoice.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 5/5 required signals.
Criteria: Identifies clients with unbilled WIP tied to Alice at 64 percent utilization.
Matched required signals: /Alice/i, /64%|64 percent|utili[sz]ation/i, /unbilled/i, /WIP/i, /client/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-4-management-reporting-response.png](screenshots/5-4-management-reporting-response.png)

## 5-5-management-pack - 5.5 R2R management pack

**Prompt**

```text
Give me the June 2026 month-end management pack. Explain the major variances versus May 2026, show revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers. Do not post journals or lock the period.
```

**Observed Atlas Response**

```text
 Pre-close checks for May 2026:
- AR/accounts receivable: review aging, unapplied receipts, and invoice approvals.
- AP/accounts payable: review due/blocked vendor bills and payment batches.
- WIP: resolve unbilled approved time and expenses.
- Unposted journals: draft/unposted journals block close until approved, posted, rejected, or waived.
- Close tasks and approvals: incomplete close tasks, missing approvals, and lock blockers must be cleared before period lock.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 5/10 required signals; forbidden hits 0.
Criteria: Produces June management pack comparing May with variances, revenue, expenses, margins, utilization, AR/AP, journals, and blockers without posting.
Matched required signals: /May 2026/i, /expense/i, /AR|AP/i, /journal/i, /blocker/i
Missing required signals: /June 2026/i, /variance/i, /revenue/i, /margin/i, /utili[sz]ation/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-5-management-pack-response.png](screenshots/5-5-management-pack-response.png)

## 5-5-management-drilldown - 5.5 R2R blocker drilldown

**Prompt**

```text
Drill into the draft journals and close task blockers for June 2026. Which ones block close, who owns them, and what should happen next?
```

**Observed Atlas Response**

```text
 Month-end management pack for 2026-06 versus 2026-05:
- Revenue 269166.00; expenses 41500.00; net income 227666.00.
- Project margin highlights: 8; utilization highlights: 0.
- AR/AP movement: AR activity 268276.00; AP activity 40000.00; WIP 0.00.
- Journals: 0 draft journal(s) and 14 posted journal(s) for 2026-06.; draft journals 0.
- Close status ready; remaining close blockers 2.
I did not post journals or lock the period.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 2/5 required signals; forbidden hits 0.
Criteria: Drills into draft journals and close task blockers with owner, close impact, and next action.
Matched required signals: /draft journal|journal/i, /block|blocker/i
Missing required signals: /close task|task/i, /owner/i, /next action|should happen/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-5-management-drilldown-response.png](screenshots/5-5-management-drilldown-response.png)

## 5-5-statement-package - 5.5 Financial statement package

**Prompt**

```text
Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and evidence-backed management commentary. Compare it to May 2026 and show the variances.
```

**Observed Atlas Response**

```text
 Financial statement package for May 2026 compared to May 2026:
- Trial Balance: debit/credit balance and suspense warnings.
- Balance Sheet: assets, liabilities, equity, and balance check.
- Income Statement: revenue, expenses, and net income variance.
- Cash Flow: operating, investing, financing, and net cash movement.
- Retained Earnings and Statutory Pack: close-readiness warnings and evidence-backed management commentary.
- Variance: compare June 2026 to May 2026 and keep journals/period lock approval-gated.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Generates financial statement package with TB, BS, IS, cash flow, retained earnings, statutory pack, warnings, commentary, and May variance.
Matched required signals: /Trial Balance/i, /Balance Sheet/i, /Income Statement/i, /Cash Flow/i, /Retained Earnings/i, /Statutory Pack/i, /warning|close-readiness/i, /variance|May 2026/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-5-statement-package-response.png](screenshots/5-5-statement-package-response.png)

## 5-5-year-end - 5.5 Year-end close

**Prompt**

```text
Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.
```

**Observed Atlas Response**

```text
 FY2026 year-end close preparation:
- Retained earnings setup must be present before the retained-earnings journal.
- Posted P&L/profit and loss activity must be complete for fiscal year 2026.
- Locked periods and duplicate close risk must be checked before any posting.
- Current-vs-prior year statement movement should be reviewed.
- Route the retained-earnings posting to Inbox approval before any journal is posted.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Prepares FY2026 year-end close with retained earnings, P&L activity, locked periods, duplicate risk, statement movement, and Inbox routing.
Matched required signals: /2026|FY2026/i, /year-end|year end/i, /retained earnings/i, /P&L|profit and loss/i, /locked period|period/i, /duplicate/i, /statement movement|prior year/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-5-year-end-response.png](screenshots/5-5-year-end-response.png)

## 5-6-manual-journal - 5.6 Manual journal lifecycle

**Prompt**

```text
Review this manual journal proposal for balance, account validity, period lock status, business reason, supporting evidence, approval role, and whether the approver is different from the submitter. Do not post it without Inbox approval.
```

**Observed Atlas Response**

```text
 Manual journal review should stay in Inbox until approval.
Balance: verify debits equal credits; account validity: verify active GL accounts; period lock status: check close calendar.
Business reason: required before approval. Supporting evidence: [{'document_id': None, 'filename': None, 'document_type': 'journal_support', 'status': 'missing', 'review_next': 'Attach supporting evidence before posting.'}].
Approval role and segregation: controller/admin approval may be required, and the approver must be different from the submitter for threshold or Nous-prepared journals. Do not post without Inbox approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Reviews manual journal proposal for balance, account validity, period lock, reason, evidence, approval role, and segregation of duties.
Matched required signals: /journal/i, /balance|balanced/i, /account/i, /period lock|locked period/i, /business reason|reason/i, /evidence|support/i, /approval role|approval/i, /approver.*submitter|different from submitter|segregation/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-6-manual-journal-response.png](screenshots/5-6-manual-journal-response.png)

## 5-6-reversal - 5.6 Manual journal reversal

**Prompt**

```text
Prepare a reversal packet for this posted manual journal. Explain why reversal is appropriate, propose an open-period reversal date, show the flipped debit and credit lines, and confirm the reversal will create a new journal rather than editing the original.
```

**Observed Atlas Response**

```text
 Manual journal reversal packet:
- Reason: document why reversal is appropriate before approval.
- Open-period date: propose a reversal date in an open period.
- Lines: flip the original debit and credit lines.
- Control: create a new reversal journal rather than editing the original posted journal.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Prepares reversal packet with reason, open-period date, flipped debit/credit lines, and new journal rather than editing original.
Matched required signals: /reversal/i, /journal/i, /reason|appropriate/i, /open period|date/i, /debit/i, /credit/i, /new journal|not edit|rather than editing/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/5-6-reversal-response.png](screenshots/5-6-reversal-response.png)

## 6-1-finance-ops-check - 6.1 Finance Ops Manager

**Prompt**

```text
Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.
```

**Observed Atlas Response**

```text
 Finance Ops check for June 2026:
- Billing read-only findings: review invoice drafts, billing runs, WIP, and missing setup before approval.
- Payment read-only findings: review due approved bills, blocked bills, payment-batch state, and cash impact.
- Collections read-only findings: review overdue invoices, reminder eligibility, blockers, and customer-specific next actions.
- Close read-only findings: review draft journals, close task blockers, AR/AP/WIP state, and period-lock readiness.
- Review actions: route action plans, invoices, payments, journals, and external emails to Inbox approval.
Read-only findings are separated from controlled actions. I did not approve invoices, payments, journals, close locks, or external emails.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Runs finance ops check separating read-only findings from Inbox-gated actions across billing, payment, collections, close, and review.
Matched required signals: /billing/i, /payment/i, /collections/i, /close/i, /review/i, /read-only|read only/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/6-1-finance-ops-check-response.png](screenshots/6-1-finance-ops-check-response.png)

## 6-1-action-plan - 6.1 Finance Ops action plan

**Prompt**

```text
Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.
```

**Observed Atlas Response**

```text
 Created the next recommended Finance Ops action plan for June 2026 and routed it to Inbox for review.
- Work-item limit: at most five manager-reviewed items.
- Inbox review reference: f4f66c59-0456-4099-84bb-f0ce10fa81b3.
- Status: Created an Inbox review task before applying this change.
- Approval boundary: Created at most the requested number of manager-reviewed work items for Inbox review; no invoice, payment, journal, or email was approved, posted, paid, or sent directly.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/6 required signals; forbidden hits 1.
Criteria: Creates at most five manager-reviewed finance ops work items and routes action plan to Inbox without approving sensitive actions.
Matched required signals: /finance ops/i, /work item|action plan/i, /five|5|at most/i, /manager-reviewed|review/i, /Inbox|approval/i, /invoice|payment|journal|email/i
Missing required signals: none
Invalid answer signals: Visible tool-call cards: 1

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/6-1-action-plan-response.png](screenshots/6-1-action-plan-response.png)

## 6-2-scheduled-control-room - 6.2 Scheduled Finance Ops Manager

**Prompt**

```text
Before enabling a scheduled Finance Ops Manager run, show the current cadence, escalation windows, last run, open scheduled plans, and approval boundary for resulting work.
```

**Observed Atlas Response**

```text
 Scheduled Finance Ops Manager control room:
- Current cadence: show enabled state, run hour, timezone, period mode, and lookback window.
- Escalation windows: show stale and high-risk stale thresholds plus escalation enabled state.
- Last run: show status, business summary, and whether any workflow is waiting on a human.
- Open scheduled plans: show action plans, plan items, and escalations still awaiting review.
- Approval boundary: scheduled runs may prepare work, but invoice approval, payment approval, journal posting, close locks, and external emails require Inbox approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Shows scheduled Finance Ops cadence, escalation windows, last run, open plans, and approval boundary before enablement.
Matched required signals: /scheduled|cadence/i, /Finance Ops/i, /escalation/i, /last run/i, /open .*plan|scheduled plan/i, /approval boundary|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/6-2-scheduled-control-room-response.png](screenshots/6-2-scheduled-control-room-response.png)

## 7-1-approval-controls - 7.1 Approval policy and personas

**Prompt**

```text
What am I allowed to approve, what requires Owner approval, and which Inbox items are high risk? Include my finance personas, effective thresholds, pending high-risk tasks, and why each item needs review. Do not show tool names, policy reason codes, raw payloads, traces, logs, or context IDs.
```

**Observed Atlas Response**

```text
 Approval controls summary:
- You can approve items permitted by your assigned role/persona and effective thresholds.
- Owner approval is required for configured high-value money-out, elevated-risk, and policy-threshold exceptions.
- Finance personas map the user to approval duties; high-risk Inbox items explain why review is required.
- Pending high-risk tasks stay in Inbox until the right approver acts.
- Internal identifiers and diagnostics are omitted from this user-facing answer.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Explains approval permissions, Owner approval thresholds, high-risk Inbox items, personas, and reasons without exposing internals.
Matched required signals: /approve|approval/i, /Owner/i, /threshold/i, /persona|role/i, /Inbox/i, /high risk|risk/i, /review/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/7-1-approval-controls-response.png](screenshots/7-1-approval-controls-response.png)

## 7-2-decision-trail - 7.2 Decision trail

**Prompt**

```text
Show the decision trail for the latest bill, invoice, payment batch, journal, or close record. Include the related Inbox task, actor role, decision type, timestamp, and before/after review summary.
```

**Observed Atlas Response**

```text
 Decision trail summary:
- Related Inbox task: include the bill, invoice, payment batch, journal, or close task review item.
- Actor role: show reviewer role and whether it met the approval policy.
- Decision type and timestamp: approved, rejected, approved with edits, waived, or posted with the decision time.
- Before/after review summary: show what changed; internal diagnostics are omitted from the user-facing answer.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Shows decision trail with related Inbox task, actor role, decision type, timestamp, and before/after summary.
Matched required signals: /decision/i, /Inbox/i, /actor role|role/i, /decision type|type/i, /timestamp|time/i, /before\/after|before and after|review summary/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/7-2-decision-trail-response.png](screenshots/7-2-decision-trail-response.png)

## 7-3-operational-health - 7.3 Operational Health

**Prompt**

```text
Show operational health for the platform today. Include degraded health, public endpoint abuse, background failure spikes, and agent/tool/workflow failure spikes. Do not expose secrets, traces, raw logs, or stack traces.
```

**Observed Atlas Response**

```text
 Operational health for the platform today:
- Health/status: show degraded health where applicable.
- Public endpoint abuse: show public abuse-path alerts and rate-limit state.
- Background failure spikes: summarize worker/job failures as business-safe counts and affected workflows.
- Agent/tool/workflow failure spikes: show alert counts and affected workflow areas.
- Safety: sensitive diagnostics are omitted from this user-facing summary.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Shows operational health with degraded status, public abuse, background failures, agent/tool/workflow failures, and no secrets/logs/traces.
Matched required signals: /health/i, /degraded|status/i, /public endpoint|abuse/i, /background/i, /agent|tool|workflow/i, /failure|spike|alert/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/7-3-operational-health-response.png](screenshots/7-3-operational-health-response.png)

## 7-4-documents-audit - 7.4 Documents and source evidence

**Prompt**

```text
Show documents that support recent engagements, bills, invoices, journals, and Inbox decisions. For each, show the linked business record, source filename, extraction state, and what I should review next.
```

**Observed Atlas Response**

```text
 Document source-evidence audit:
- Engagement document: source filename, linked engagement record, extraction state, and review next.
- Bill document: source filename, linked bill/vendor record, coding/extraction state, and review next.
- Invoice document: source filename, linked invoice/customer record, extraction state, and review next.
- Journal document: source filename, linked journal/manual support record, extraction state, and review next.
- Inbox decision evidence: linked Inbox task, decision status, and reviewer next step.
Internal storage details are omitted from this user-facing answer.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Shows source documents linked to engagements, bills, invoices, journals, and Inbox decisions with extraction state and next review.
Matched required signals: /document|source/i, /engagement/i, /bill/i, /invoice/i, /journal/i, /Inbox/i, /extraction state|extracted|processing/i, /review next|next review|what .* review/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/7-4-documents-audit-response.png](screenshots/7-4-documents-audit-response.png)

## 7-5-config-telemetry - 7.5 Configuration and telemetry

**Prompt**

```text
Review configuration and telemetry readiness. Show approval controls, scheduled Finance Ops Manager settings, Atlas runtime, Langfuse observability status, operational alerts, and any public abuse-path controls that need attention.
```

**Observed Atlas Response**

```text
 Configuration and telemetry readiness is summarized with user-safe status flags.
Approval controls: role and threshold policy are active; high-risk Inbox items require role review.
Scheduled Finance Ops Manager settings: cadence, escalation windows, last run, and open scheduled plans should be reviewed before enablement.
Nous runtime: configurable between Aethos basic AI and Hermes-powered Nous; fallback can route degraded Hermes turns to basic Nous.
Langfuse observability: configured state, base URL status, and sample rate are summarized as safe status flags; low-level diagnostics stay internal.
Operational alerts: show alert route and active alert items for background failures, workflow failures, and degraded health.
Public abuse-path controls: rate limits, abuse alerts, and sanitized public endpoint reporting protect public invoice/payment paths.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/7 required signals.
Criteria: Reviews approval controls, scheduled Finance Ops, Atlas runtime, Langfuse observability, operational alerts, and abuse controls.
Matched required signals: /approval controls|approval/i, /scheduled Finance Ops|Finance Ops/i, /Langfuse/i, /observability|telemetry/i, /alert/i, /abuse|public/i
Missing required signals: /Atlas runtime|Atlas/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-08-05T07-36-11-138Z/screenshots/7-5-config-telemetry-response.png](screenshots/7-5-config-telemetry-response.png)

## Browser Console Errors

_None captured_

## Network Failures And 5xx Responses

- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status`
- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20`
- `net::ERR_ABORTED https://fonts.gstatic.com/s/materialicons/v145/flUhRq6tzZclQEJ-Vdg-IuiaDsNc.woff2`
