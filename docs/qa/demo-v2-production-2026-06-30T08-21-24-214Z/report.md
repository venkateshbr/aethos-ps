# Demo Guide v2 Production Browser Validation

Run ID: `2026-06-30T08-21-24-214Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-06-30T08:58:50.201Z`

This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.

Summary: PASS 49, WARN 0, FAIL 17, SKIP 0

## Evidence Table

| ID | Section | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| auth | Authentication | Logged into https://aethos.ishirock.tech | PASS | [screenshot](screenshots/auth-login-filled.png) | Tenant: Meridian Demo v2 20260630063630<br>Tenant ID: a0267012-73a9-416c-bba2-81d86e2bbba4<br>User: prod-demo-v2-20260630063630@aethos-qa.dev |
| route-copilot | Route Coverage | Aethos Atlas | PASS | [screenshot](screenshots/route-copilot.png) | URL: https://aethos.ishirock.tech/app/copilot<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat Ne |
| route-documents | Route Coverage | Documents | PASS | [screenshot](screenshots/route-documents.png) | URL: https://aethos.ishirock.tech/app/documents<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Documents Docum |
| route-inbox | Route Coverage | Inbox | PASS | [screenshot](screenshots/route-inbox.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Inbox 5 All Eng |
| route-engagements | Route Coverage | Engagements | PASS | [screenshot](screenshots/route-engagements.png) | URL: https://aethos.ishirock.tech/app/engagements<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| route-projects | Route Coverage | Projects | PASS | [screenshot](screenshots/route-projects.png) | URL: https://aethos.ishirock.tech/app/projects<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| route-invoices | Route Coverage | Invoices | PASS | [screenshot](screenshots/route-invoices.png) | URL: https://aethos.ishirock.tech/app/invoices<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Invoices Review |
| route-clients | Route Coverage | Contacts | PASS | [screenshot](screenshots/route-clients.png) | URL: https://aethos.ishirock.tech/app/clients<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| route-expenses | Route Coverage | Expenses | PASS | [screenshot](screenshots/route-expenses.png) | URL: https://aethos.ishirock.tech/app/expenses<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Expenses Track  |
| route-bills | Route Coverage | Bills | PASS | [screenshot](screenshots/route-bills.png) | URL: https://aethos.ishirock.tech/app/bills<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Bills Manage ve |
| route-billing-runs | Route Coverage | Billing Runs / Pay Bills | PASS | [screenshot](screenshots/route-billing-runs.png) | URL: https://aethos.ishirock.tech/app/billing-runs<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Billing Run Bil |
| route-time | Route Coverage | Time | PASS | [screenshot](screenshots/route-time.png) | URL: https://aethos.ishirock.tech/app/time<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Time Entries Lo |
| route-approvals | Route Coverage | Approvals | PASS | [screenshot](screenshots/route-approvals.png) | URL: https://aethos.ishirock.tech/app/approvals<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Timesheet appro |
| route-payments | Route Coverage | Payments | PASS | [screenshot](screenshots/route-payments.png) | URL: https://aethos.ishirock.tech/app/payments<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Payments AR rec |
| route-people | Route Coverage | People | PASS | [screenshot](screenshots/route-people.png) | URL: https://aethos.ishirock.tech/app/people<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| route-reports | Route Coverage | Reports | PASS | [screenshot](screenshots/route-reports.png) | URL: https://aethos.ishirock.tech/app/reports<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| route-journals | Route Coverage | Accounting / Journal Entries | PASS | [screenshot](screenshots/route-journals.png) | URL: https://aethos.ishirock.tech/app/accounting/journals<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Journal Entries |
| route-settings | Route Coverage | Settings | PASS | [screenshot](screenshots/route-settings.png) | URL: https://aethos.ishirock.tech/app/settings<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Settings Manage |
| route-timesheet | Route Coverage | Timesheet portal | PASS | [screenshot](screenshots/route-timesheet.png) | URL: https://timesheet.aethos.ishirock.tech<br>Body excerpt: Aethos Timesheets Sign in Log the hours you worked on your projects. EMAIL PASSWORD Sign in |
| 1-1-engagement-letter | 1.1 Engagement letter onboarding | Atlas prompt | PASS | [screenshot](screenshots/1-1-engagement-letter-response.png) | Attachment banner before prompt: attach_file Attached: nexus_engagement_letter.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business-valid answer: matched 7/7 required signals. |
| 1-2-engagement-structure | 1.2 Project structure | Atlas prompt | PASS | [screenshot](screenshots/1-2-engagement-structure-response.png) | Business-valid answer: matched 4/4 required signals. |
| 1-3-log-time | 1.3 Time entry | Atlas prompt | PASS | [screenshot](screenshots/1-3-log-time-response.png) | Business-valid answer: matched 5/5 required signals. |
| 1-3a-delivery-data | 1.3A People and WIP | Atlas prompt | PASS | [screenshot](screenshots/1-3a-delivery-data-response.png) | Business-valid answer: matched 7/7 required signals. |
| 1-4-billing-run | 1.4 Mixed model invoice | Atlas prompt | FAIL | [screenshot](screenshots/1-4-billing-run-response.png) | Business validation failed: matched 6/8 required signals; forbidden hits 0.<br>Missing required signals: /fixed fee/i, /expense/i |
| 1-5-revenue-recognition | 1.5 Revenue recognition | Atlas prompt | FAIL | [screenshot](screenshots/1-5-revenue-recognition-response.png) | Business validation failed: matched 6/8 required signals; forbidden hits 0.<br>Missing required signals: /fixed fee/milestone/i, /journal/i |
| 1-6-capped-tax | 1.6 Capped tax engagement | Atlas prompt | PASS | [screenshot](screenshots/1-6-capped-tax-response.png) | Business-valid answer: matched 6/6 required signals. |
| 1-7-o2c-readiness | 1.7 O2C controls | Atlas prompt | PASS | [screenshot](screenshots/1-7-o2c-readiness-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-collections-read | 1.7 Collections read pack | Atlas prompt | PASS | [screenshot](screenshots/1-7-collections-read-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-invoice-drilldown | 1.7 Invoice drilldown | Atlas prompt | PASS | [screenshot](screenshots/1-7-invoice-drilldown-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-draft-reminders | 1.7 Collections controlled write | Atlas prompt | FAIL | [screenshot](screenshots/1-7-draft-reminders-response.png) | Business validation failed: matched 4/6 required signals; forbidden hits 0.<br>Missing required signals: /customer/i, /Inbox/approval/i |
| 2-1-retainer | 2.1 Monthly retainer billing | Atlas prompt | PASS | [screenshot](screenshots/2-1-retainer-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-2-milestone | 2.2 Annual accounts milestone | Atlas prompt | PASS | [screenshot](screenshots/2-2-milestone-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-3-payroll | 2.3 Payroll billing | Atlas prompt | PASS | [screenshot](screenshots/2-3-payroll-response.png) | Business-valid answer: matched 6/7 required signals.<br>Missing required signals: /count/i |
| 2-4-vendor-invoice | 2.4 Vendor invoice intake | Atlas prompt | FAIL | [screenshot](screenshots/2-4-vendor-invoice-response.png) | Attachment banner before prompt: attach_file Attached: brightwater_subcontractor_invoice.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business validation failed: matched 5/8 required signals; forbidden hits 0.<br>Missing required signals: /project/i, /duplicate/i, /PO/purchase order/service-order/service order/i |
| 2-4-payment-risk-read | 2.4 P2P read pack | Atlas prompt | PASS | [screenshot](screenshots/2-4-payment-risk-read-response.png) | Business-valid answer: matched 8/9 required signals.<br>Missing required signals: /vendor/i |
| 2-4-single-bill | 2.4 Single bill drilldown | Atlas prompt | PASS | [screenshot](screenshots/2-4-single-bill-response.png) | Business-valid answer: matched 9/9 required signals. |
| 2-5-bill-pay | 2.5 Payment controls | Atlas prompt | PASS | [screenshot](screenshots/2-5-bill-pay-response.png) | Business-valid answer: matched 6/7 required signals.<br>Missing required signals: /rationale/reason/i |
| 2-5-payment-packet | 2.5 Payment approval packet | Atlas prompt | FAIL | [screenshot](screenshots/2-5-payment-packet-response.png) | Business validation failed: matched 6/7 required signals; forbidden hits 0.<br>Missing required signals: /vendor/i |
| 3-1-family-office | 3.1 Family office structure | Atlas prompt | PASS | [screenshot](screenshots/3-1-family-office-response.png) | Business-valid answer: matched 6/7 required signals.<br>Missing required signals: /engagement/i |
| 3-2-scope-creep | 3.2 Scope creep risk | Atlas prompt | PASS | [screenshot](screenshots/3-2-scope-creep-response.png) | Business-valid answer: matched 7/7 required signals. |
| 3-3-sgd-journal | 3.3 Multi-currency trust accounts | Atlas prompt | FAIL | [screenshot](screenshots/3-3-sgd-journal-response.png) | Business validation failed: matched 4/8 required signals; forbidden hits 1.<br>Missing required signals: /SGD/i, /18,?000/18000/i, /GBP/i, /FX/exchange rate/i<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i |
| 3-4-cosec-reminders | 3.4 COSEC reminders | Atlas prompt | FAIL | [screenshot](screenshots/3-4-cosec-reminders-response.png) | Business validation failed: matched 5/7 required signals; forbidden hits 1.<br>Missing required signals: /evidence/missing/i, /approval/before sending/i<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i |
| 4-1-usd-engagement | 4.1 USD-billed engagement | Atlas prompt | PASS | [screenshot](screenshots/4-1-usd-engagement-response.png) | Business-valid answer: matched 8/8 required signals. |
| 4-2-series-a | 4.2 Series A milestone | Atlas prompt | FAIL | [screenshot](screenshots/4-2-series-a-response.png) | Tool-call cards visible to user: 1.<br>Business validation failed: matched 6/6 required signals; forbidden hits 1.<br>Invalid answer signals: Visible tool-call cards: 1 |
| 4-3-cosec-instruction | 4.3 COSEC instruction | Atlas prompt | PASS | [screenshot](screenshots/4-3-cosec-instruction-response.png) | Attachment banner before prompt: attach_file Attached: thornton_cosec_instruction.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business-valid answer: matched 7/7 required signals. |
| 5-1-close-readiness | 5.1 Pre-close checklist | Atlas prompt | PASS | [screenshot](screenshots/5-1-close-readiness-response.png) | Business-valid answer: matched 8/8 required signals. |
| 5-2-period-lock | 5.2 Period lock | Atlas prompt | PASS | [screenshot](screenshots/5-2-period-lock-response.png) | Business-valid answer: matched 6/6 required signals. |
| 5-3-trial-balance | 5.3 Trial Balance | Atlas prompt | PASS | [screenshot](screenshots/5-3-trial-balance-response.png) | Business-valid answer: matched 7/7 required signals. |
| 5-4-management-reporting | 5.4 Management reporting | Atlas prompt | FAIL | [screenshot](screenshots/5-4-management-reporting-response.png) | Business validation failed: matched 4/5 required signals; forbidden hits 0.<br>Missing required signals: /64%/64 percent/utili[sz]ation/i |
| 5-5-management-pack | 5.5 R2R management pack | Atlas prompt | FAIL | [screenshot](screenshots/5-5-management-pack-response.png) | Business validation failed: matched 7/10 required signals; forbidden hits 0.<br>Missing required signals: /utili[sz]ation/i, /journal/i, /blocker/i |
| 5-5-management-drilldown | 5.5 R2R blocker drilldown | Atlas prompt | FAIL | [screenshot](screenshots/5-5-management-drilldown-response.png) | Business validation failed: matched 4/5 required signals; forbidden hits 0.<br>Missing required signals: /owner/i |
| 5-5-statement-package | 5.5 Financial statement package | Atlas prompt | PASS | [screenshot](screenshots/5-5-statement-package-response.png) | Business-valid answer: matched 7/8 required signals.<br>Missing required signals: /Statutory Pack/i |
| 5-5-year-end | 5.5 Year-end close | Atlas prompt | PASS | [screenshot](screenshots/5-5-year-end-response.png) | Business-valid answer: matched 8/8 required signals. |
| 5-6-manual-journal | 5.6 Manual journal lifecycle | Atlas prompt | FAIL | [screenshot](screenshots/5-6-manual-journal-response.png) | Business validation failed: matched 2/8 required signals; forbidden hits 0.<br>Missing required signals: /balance/balanced/i, /period lock/locked period/i, /business reason/reason/i, /evidence/support/i, /approval role/approval/i, /approver.*submitter/different from submitter/segregation/i |
| 5-6-reversal | 5.6 Manual journal reversal | Atlas prompt | PASS | [screenshot](screenshots/5-6-reversal-response.png) | Business-valid answer: matched 6/7 required signals.<br>Missing required signals: /new journal/not edit/rather than editing/i |
| 6-1-finance-ops-check | 6.1 Finance Ops Manager | Atlas prompt | PASS | [screenshot](screenshots/6-1-finance-ops-check-response.png) | Business-valid answer: matched 7/7 required signals. |
| 6-1-action-plan | 6.1 Finance Ops action plan | Atlas prompt | FAIL | [screenshot](screenshots/6-1-action-plan-response.png) | Tool-call cards visible to user: 1.<br>Business validation failed: matched 4/6 required signals; forbidden hits 1.<br>Missing required signals: /five/5/at most/i, /invoice/payment/journal/email/i<br>Invalid answer signals: Visible tool-call cards: 1 |
| 6-2-scheduled-control-room | 6.2 Scheduled Finance Ops Manager | Atlas prompt | FAIL | [screenshot](screenshots/6-2-scheduled-control-room-response.png) | Business validation failed: matched 4/6 required signals; forbidden hits 0.<br>Missing required signals: /last run/i, /open .*plan/scheduled plan/i |
| 7-1-approval-controls | 7.1 Approval policy and personas | Atlas prompt | FAIL | [screenshot](screenshots/7-1-approval-controls-response.png) | Business validation failed: matched 4/7 required signals; forbidden hits 0.<br>Missing required signals: /Owner/i, /threshold/i, /review/i |
| 7-2-decision-trail | 7.2 Decision trail | Atlas prompt | PASS | [screenshot](screenshots/7-2-decision-trail-response.png) | Business-valid answer: matched 6/6 required signals. |
| 7-3-operational-health | 7.3 Operational Health | Atlas prompt | PASS | [screenshot](screenshots/7-3-operational-health-response.png) | Business-valid answer: matched 6/6 required signals. |
| 7-4-documents-audit | 7.4 Documents and source evidence | Atlas prompt | FAIL | [screenshot](screenshots/7-4-documents-audit-response.png) | Business validation failed: matched 2/8 required signals; forbidden hits 0.<br>Missing required signals: /engagement/i, /bill/i, /invoice/i, /journal/i, /Inbox/i, /review next/next review/what .* review/i |
| 7-5-config-telemetry | 7.5 Configuration and telemetry | Atlas prompt | FAIL | [screenshot](screenshots/7-5-config-telemetry-response.png) | Business validation failed: matched 3/7 required signals; forbidden hits 0.<br>Missing required signals: /Atlas runtime/Atlas/i, /Langfuse/i, /alert/i, /abuse/public/i |
| route-inbox-after-prompts | Route Coverage | Inbox after Atlas prompts | PASS | [screenshot](screenshots/route-inbox-after-prompts.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Inbox 16 All En |
| route-documents-after-prompts | Route Coverage | Documents after Atlas uploads | PASS | [screenshot](screenshots/route-documents-after-prompts.png) | URL: https://aethos.ishirock.tech/app/documents<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Documents Docum |
| route-workflow-runs-after-prompts | Route Coverage | Settings / workflow and observability surfaces | PASS | [screenshot](screenshots/route-workflow-runs-after-prompts.png) | URL: https://aethos.ishirock.tech/app/settings<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Settings Manage |

## Prompt Transcript

## 1-1-engagement-letter - 1.1 Engagement letter onboarding

**Prompt**

```text
Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.
```

**Observed Atlas Response**

```text
 I have reviewed the engagement letter for Nexus Capital Partners LP.

I have prepared a draft for the client, engagement, billing terms, and the first project (Statutory Accounts - FY2025) based on the following extracted terms:
- Total Value: GBP 144,000.00
- Fixed Fee: GBP 42,000.00
- Monthly Retainer: GBP 8,500.00
- Period: 2026-01-01 to 2026-12-31
- Rates: CFO Advisory Partner (350/hr), Manager (240/hr), Associate (145/hr)

Because this involves new client setup and financial commitments, the entire package has been routed to your Inbox for review and approval. Please visit /app/inbox to finalize the setup.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Extracts the uploaded Nexus engagement letter instead of asking the user to retype it. | Creates or prepares client, engagement, billing terms, rate card, and first project. | Routes risky or incomplete items to Inbox.
Matched required signals: /Nexus/i, /client/i, /engagement/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i, /Inbox|review|risk/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-1-engagement-letter-response.png](screenshots/1-1-engagement-letter-response.png)

## 1-2-engagement-structure - 1.2 Project structure

**Prompt**

```text
Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.
```

**Observed Atlas Response**

```text
 Nexus Capital Partners LP has two active engagements.

1. Group Accounting & Advisory
This engagement is ready for billing.
Active Projects & Billing:
- Nexus CFO Advisory: Time & Materials (GBP 350/hr)
- Nexus Group Consolidation FY2025: Fixed Fee (part of GBP 48,000 total)
- Nexus Monthly Management Accounts: Monthly Retainer (GBP 9,000/month)

2. Corporation Tax Return FY2025
This engagement needs a setup review before it can be billed.
Billing Model: Capped T&M (Fixed fee of GBP 18,500 with a cap of GBP 22,000; advisory overrun at GBP 280/hr).
Missing Items:
- No active projects or workstreams have been defined.
- Source documents (engagement letter) are missing.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 4/4 required signals.
Criteria: Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.
Matched required signals: /Nexus/i, /project|workstream/i, /billing model|fixed|retainer|T&M|time and materials/i, /missing|ready|before billing|setup/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-2-engagement-structure-response.png](screenshots/1-2-engagement-structure-response.png)

## 1-3-log-time - 1.3 Time entry

**Prompt**

```text
Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling
```

**Observed Atlas Response**

```text
 I have logged 4.5 hours to the Nexus CFO Advisory project for today. This entry is currently pending review in your Aethos Inbox.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 5/5 required signals.
Criteria: Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.
Matched required signals: /4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /time|hours/i, /logged|created|Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-3-log-time-response.png](screenshots/1-3-log-time-response.png)

## 1-3a-delivery-data - 1.3A People and WIP

**Prompt**

```text
Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.
```

**Observed Atlas Response**

```text
 For Alice Chen in June 2026:

Approved Time: 0 hours
Pending Time: 24.0 hours
Billable Expenses: 185.50 GBP
Utilization: 0.00%
WIP: 0.00

Nexus Invoicing:
No time entries are currently ready for invoicing as they are all in draft status. However, one travel expense of 185.50 GBP is ready to be invoiced for Nexus Capital Partners LP.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Summarizes Alice Chen June delivery, utilization, WIP, expenses, and invoice readiness for Nexus.
Matched required signals: /Alice Chen|Alice/i, /June/i, /approved time|pending time|hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice|invoiced/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-3a-delivery-data-response.png](screenshots/1-3a-delivery-data-response.png)

## 1-4-billing-run - 1.4 Mixed model invoice

**Prompt**

```text
Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending.
```

**Observed Atlas Response**

```text
 I have prepared the June 2026 billing run for Nexus Capital Partners LP based on the Group Accounting & Advisory engagement.

Draft Invoice Lines (GBP):
- Monthly Management Accounts Retainer: 9,000.00
- CFO Advisory (T&M): 3,150.00 (9.0 hours @ 350.00/hr)
- Group Consolidation: No unbilled WIP for this period.

Total Draft Amount: 12,150.00 GBP

The invoice has been routed to the Aethos Inbox for final review and approval before being sent to the client.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/8 required signals; forbidden hits 0.
Criteria: Prepares Nexus June billing run with fixed fee, retainer, T&M hours, expenses, draft invoice lines, and Inbox routing.
Matched required signals: /Nexus/i, /June 2026|June/i, /retainer/i, /T&M|time and materials|hour/i, /invoice line|draft invoice/i, /Inbox|approval/i
Missing required signals: /fixed fee/i, /expense/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-4-billing-run-response.png](screenshots/1-4-billing-run-response.png)

## 1-5-revenue-recognition - 1.5 Revenue recognition

**Prompt**

```text
Explain how Nexus June revenue is recognized across fixed-fee milestone, retainer, T&M advisory WIP, and expenses. Tie the explanation to invoice-backed journals and Project P&L.
```

**Observed Atlas Response**

```text
 For Nexus Capital Partners in June, revenue recognition is split across three distinct mechanisms within the Group Accounting & Advisory engagement.

Fixed-Fee & Retainer Revenue
The monthly management accounts retainer is recognized as revenue upon the issuance of the monthly invoice. This creates a debit to Accounts Receivable and a credit to Revenue. In the Project P&L, this appears as a steady monthly revenue stream with a high margin, as it is not tied to hourly WIP.

T&M Advisory WIP
CFO Advisory work is tracked as Work-in-Progress (WIP). For June, there are 9 unbilled hours at an average rate of 350.00, totaling 3,150.00 in WIP. This is not yet recognized as revenue on the Income Statement; it remains an asset on the Balance Sheet until the associated invoice is generated, at which point the WIP is cleared and revenue is recognized.

Expenses
Direct project costs (e.g., travel or software) are recognized as expenses in the period they are incurred. For the Nexus CFO Advisory project, 185.50 in direct costs was recorded in June. This reduces the Project P&L gross margin directly, creating a current gross margin of -185.50 for that specific project since the associated revenue is still sitting in WIP.

Summary Tie-in
The June Project P&L for Nexus currently shows no recognized revenue for the Advisory or Consolidation work because those are either in WIP or not yet invoiced. The global Revenue account (4000) reflects 9,000.00 for the period, which is primarily driven by other client retainers (like Brightwater) rather than Nexus, as Nexus's most recent activity is still awaiting billing.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/8 required signals; forbidden hits 0.
Criteria: Explains Nexus revenue recognition across milestone/fixed fee, retainer, T&M WIP, expenses, journals, and Project P&L.
Matched required signals: /Nexus/i, /revenue/i, /retainer/i, /T&M|WIP|time and materials/i, /expense/i, /Project P&L|project/i
Missing required signals: /fixed fee|milestone/i, /journal/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-5-revenue-recognition-response.png](screenshots/1-5-revenue-recognition-response.png)

## 1-6-capped-tax - 1.6 Capped tax engagement

**Prompt**

```text
Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun
```

**Observed Atlas Response**

```text
 I have prepared the engagement draft for Nexus Capital Partners LP: Corporation Tax Return FY2025 with a fixed fee of £18,500 and a cap of £22,000. This has been routed to the Aethos Inbox for approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Creates or prepares Nexus capped tax engagement with fixed fee, cap, and Inbox approval if required.
Matched required signals: /Nexus/i, /Corporation Tax|Tax Return|FY2025/i, /18,?500|18500/i, /22,?000|22000|cap/i, /engagement/i, /Inbox|approval|created/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-6-capped-tax-response.png](screenshots/1-6-capped-tax-response.png)

## 1-7-o2c-readiness - 1.7 O2C controls

**Prompt**

```text
Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval.
```

**Observed Atlas Response**

```text
 Nexus Order-to-Cash readiness for June 2026 is partially complete, with a critical setup gap in the Tax Return engagement and an overdue balance requiring attention.

Engagement & Setup Readiness
Group Accounting & Advisory: Ready. Service catalogue mapping is complete with three active projects (CFO Advisory, Group Consolidation, and Monthly Management Accounts) linked to the Meridian 2026 GBP Rate Card.
Corporation Tax Return FY2025: Not Ready. This engagement requires a setup review. It is currently missing active projects/workstreams and source documentation, which are blocking billing readiness.
Tax Rates: Setup is not explicitly detailed in the structure pack, but the Corporation Tax engagement is marked as needing review, which typically includes tax rate verification.

Invoicing & WIP
WIP: There is 3,150.00 GBP in unbilled WIP specifically for Nexus CFO Advisory (9.0 hours).
Draft Invoices: There is a pending high-risk Inbox item (ID: 99f75a63...) for a draft invoice amounting to 57,185.50 GBP awaiting manager approval.
Public Links: Public invoice links are active and ready; INV-1001 currently uses the public invoice path for payment.

Collections & Approvals
Overdue Balance: INV-1001 (9,000.00 GBP) is 11 days overdue.
Pending Actions: A firm collections reminder for INV-1001 is recommended. While not yet a formal Inbox item, the system identifies this as the immediate next action.
Other Approvals: An engagement letter extraction for Nexus is currently pending review in the Inbox (ID: fcae5b4a...).

Next Actions
1. Resolve the setup gaps for the Corporation Tax Return engagement (link projects and upload source documents).
2. Approve the pending 57,185.50 GBP draft invoice in the Inbox.
3. Draft and approve the firm collections reminder for INV-1001.
4. Review and approve the Nexus engagement letter extraction.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Reviews Nexus O2C readiness across service catalogue, rate card, tax, invoices, payment links, WIP, and collections approvals.
Matched required signals: /Nexus/i, /service catalogue|catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link|public invoice/i, /WIP/i, /collections/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-7-o2c-readiness-response.png](screenshots/1-7-o2c-readiness-response.png)

## 1-7-collections-read - 1.7 Collections read pack

**Prompt**

```text
Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.
```

**Observed Atlas Response**

```text
 Only Nexus Capital Partners LP requires a collections follow-up.

Customer: Nexus Capital Partners LP
Balance: 9,000.00 GBP
Invoice Number: INV-1001
Due Date: 2026-06-19
Aging Bucket: 0-30 days (11 days overdue)
Payment Status: Unpaid
Reminder History: No reminders sent
Collections Policy Stage: Firm
Blockers: None
Next Action: Draft a firm collections reminder for Inbox review.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Shows collections customers with balances, invoices, due dates, aging, reminders, blockers, and next action without drafting.
Matched required signals: /customer/i, /balance/i, /invoice/i, /due date|due/i, /aging|overdue/i, /reminder/i, /blocker|blocked/i, /next action/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-7-collections-read-response.png](screenshots/1-7-collections-read-response.png)

## 1-7-invoice-drilldown - 1.7 Invoice drilldown

**Prompt**

```text
Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action.
```

**Observed Atlas Response**

```text
 Invoice INV-1001 for Nexus Capital Partners LP is currently overdue.

Due Date: 2026-06-19
Aging: 11 days overdue (0-30 day bucket)
Balance Due: 9,000.00 GBP
Paid Amount: 0.00 GBP (Unpaid)
Public Invoice: Available
Payment Link State: Public invoice only
Reminder History: No reminders sent to date
Collections Policy Stage: Firm
Blockers: None
Recommended Next Action: Draft a firm collections reminder for Inbox review.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Reviews INV-1001 with due date, aging, balance, paid status, payment link, reminders, blockers, and next action.
Matched required signals: /INV-1001/i, /due date|due/i, /aging|overdue/i, /balance/i, /paid|payment/i, /reminder/i, /blocker|blocked/i, /next action|recommend/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-7-invoice-drilldown-response.png](screenshots/1-7-invoice-drilldown-response.png)

## 1-7-draft-reminders - 1.7 Collections controlled write

**Prompt**

```text
Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.
```

**Observed Atlas Response**

```text
 No invoices are currently more than 30 days overdue, so no reminders were drafted. One invoice for Nexus Capital Partners LP (INV-1001) was identified, but it is only 11 days overdue.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/6 required signals; forbidden hits 0.
Criteria: Drafts customer-specific reminders for invoices over 30 days overdue and routes them to Inbox before sending.
Matched required signals: /reminder/i, /invoice/i, /30 days|overdue/i, /draft/i
Missing required signals: /customer/i, /Inbox|approval/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/1-7-draft-reminders-response.png](screenshots/1-7-draft-reminders-response.png)

## 2-1-retainer - 2.1 Monthly retainer billing

**Prompt**

```text
Prepare Brightwater Manufacturing monthly retainer billing for June 2026. Show the draft invoice, any tax, and route it to Inbox before sending.
```

**Observed Atlas Response**

```text
 I have prepared the June 2026 monthly retainer billing for Brightwater Manufacturing Ltd.

The draft invoice for the Monthly Management Accounts engagement is as follows:
Net Amount: GBP 4,500.00
Tax: GBP 900.00 (VAT 20%)
Total Amount: GBP 5,400.00

This has been routed to the Aethos Inbox for review and approval before it is sent to the client.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Prepares Brightwater monthly retainer billing with draft invoice, tax, and Inbox routing.
Matched required signals: /Brightwater/i, /retainer/i, /June 2026|June/i, /invoice/i, /tax/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/2-1-retainer-response.png](screenshots/2-1-retainer-response.png)

## 2-2-milestone - 2.2 Annual accounts milestone

**Prompt**

```text
Prepare the Brightwater Annual Accounts FY2025 milestone invoice. Include the milestone basis, tax treatment, and approval path before sending.
```

**Observed Atlas Response**

```text
 I have prepared the draft invoice for the Brightwater Annual Accounts FY2025 milestone.

Details:
Milestone Basis: Statutory accounts milestone (Unit price: GBP 7,000.00)
Tax Treatment: Standard UK VAT applied as per the Meridian 2026 GBP Rate Card
Approval Path: The invoice has been routed to the Aethos Inbox for final review and approval by the Engagement Manager before it is sent to Brightwater Manufacturing Ltd.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Prepares Brightwater Annual Accounts milestone invoice with basis, tax treatment, and approval path.
Matched required signals: /Brightwater/i, /Annual Accounts|FY2025/i, /milestone/i, /invoice/i, /tax/i, /approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/2-2-milestone-response.png](screenshots/2-2-milestone-response.png)

## 2-3-payroll - 2.3 Payroll billing

**Prompt**

```text
Prepare Brightwater payroll billing for June 2026 based on active employee count. Show per-employee billing, invoice total, and any approval needed.
```

**Observed Atlas Response**

```text
 The payroll billing for Brightwater Manufacturing Ltd for June 2026 is calculated as follows:

Billing Detail:
180 active employees at GBP 8.50 per employee

Invoice Total:
GBP 1,530.00

Approval Needed:
The Payroll Bureau engagement is currently flagged as needing a setup review because it is missing an active project or workstream and source documentation. This must be resolved before the invoice can be finalized.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/7 required signals.
Criteria: Prepares Brightwater payroll billing from active employee count with total and approval need.
Matched required signals: /Brightwater/i, /payroll/i, /employee/i, /invoice|billing/i, /total/i, /approval/i
Missing required signals: /count/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/2-3-payroll-response.png](screenshots/2-3-payroll-response.png)

## 2-4-vendor-invoice - 2.4 Vendor invoice intake

**Prompt**

```text
Process this vendor invoice for Brightwater. Match it to the right vendor and project, flag duplicate risk, code it to the right account, compare any PO or service-order evidence, and send exceptions to Inbox.
```

**Observed Atlas Response**

```text
 The invoice processing for Brightwater encountered several critical issues during automated extraction:

1.  Security Alert: The system detected suspected prompt injection within the source document, which has triggered a critical security flag.
2.  Extraction Failures: Due to the security alert, the extraction agent's confidence is 0%, and no vendor, amount, or coding data could be safely extracted.
3.  Review Required: As a result, the bill could not be automatically matched or coded.

A critical review task has been routed to the Aethos Inbox. Please review the document manually in the Inbox to resolve the security flag and complete the vendor matching and coding.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 5/8 required signals; forbidden hits 0.
Criteria: Extracts the uploaded Brightwater subcontractor invoice. | Matches vendor/project, codes account, checks duplicate and PO/service-order evidence, and routes exceptions to Inbox.
Matched required signals: /Brightwater/i, /vendor|subcontractor/i, /bill|invoice/i, /account|code/i, /Inbox|exception/i
Missing required signals: /project/i, /duplicate/i, /PO|purchase order|service-order|service order/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/2-4-vendor-invoice-response.png](screenshots/2-4-vendor-invoice-response.png)

## 2-4-payment-risk-read - 2.4 P2P read pack

**Prompt**

```text
Which vendor bills are due soon, which are blocked, and what evidence supports payment? Show vendor, bill number, amount, due date, status, coding evidence, source document, duplicate risk, PO/service-order match, payment-batch state, blockers, and next action. Do not create a payment batch yet.
```

**Observed Atlas Response**

```text
 BT Broadband
Bill Number: BILL-1002 (Invoice BT-2026-0620)
Amount: 189.00 GBP
Due Date: 2026-07-01
Status: Approved (Blocked)
Coding Evidence: Uncoded
Source Document: Missing
Duplicate Risk: No
PO/Service-Order Match: Not linked
Payment-batch state: None
Blockers: Incomplete coding, missing source document
Next Action: Complete bill coding and line evidence before payment approval.

Forster & Reid Ltd
Bill Number: BILL-1001 (Invoice FR-2026-0615)
Amount: 3,200.00 GBP
Due Date: 2026-07-05
Status: Approved (Blocked)
Coding Evidence: Uncoded
Source Document: Missing
Duplicate Risk: No
PO/Service-Order Match: Not linked
Payment-batch state: None
Blockers: Incomplete coding, missing source document
Next Action: Complete bill coding and line evidence before payment approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/9 required signals.
Criteria: Shows due/blocked vendor bills with evidence, duplicate risk, PO match, payment state, blockers, and next action without batching.
Matched required signals: /bill/i, /due date|due soon|overdue/i, /blocked|blocker/i, /evidence|source document/i, /duplicate/i, /PO|service order/i, /payment/i, /next action/i
Missing required signals: /vendor/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/2-4-payment-risk-read-response.png](screenshots/2-4-payment-risk-read-response.png)

## 2-4-single-bill - 2.4 Single bill drilldown

**Prompt**

```text
Review bill BILL-1001. Show due date, amount, vendor invoice number, coding status, source document, duplicate signals, PO/service-order match, approval state, payment readiness, existing batch status, and recommended next action.
```

**Observed Atlas Response**

```text
 Review for BILL-1001 (Forster & Reid Ltd):

Due Date: 2026-07-05
Amount: 3,200.00 GBP
Vendor Invoice Number: FR-2026-0615
Coding Status: Uncoded (1 line pending)
Source Document: Missing
Duplicate Signals: None (No risk detected)
PO/Service-Order Match: Not linked
Approval State: Approved for payment review
Payment Readiness: Blocked (Blockers: incomplete coding, missing source document)
Existing Batch Status: Not assigned to any batch
Recommended Next Action: Complete bill coding and provide line evidence before payment approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 9/9 required signals.
Criteria: Reviews BILL-1001 with due date, vendor invoice number, coding, source, duplicate, approval, payment readiness, and next action.
Matched required signals: /BILL-1001/i, /due date|due/i, /vendor invoice/i, /coding|coded|account/i, /source document|source/i, /duplicate/i, /approval/i, /payment readiness|payment/i, /next action|recommend/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/2-4-single-bill-response.png](screenshots/2-4-single-bill-response.png)

## 2-5-bill-pay - 2.5 Payment controls

**Prompt**

```text
Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox.
```

**Observed Atlas Response**

```text
 I have prepared this week's bill-pay run. I identified all approved bills due or overdue within the next 7 days and excluded any disputed items.

The payment batch has been sent to your Inbox for review and final approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/7 required signals.
Criteria: Prepares a bill-pay run for due/overdue approved bills, excludes disputed items, explains rationale, and routes batch to Inbox.
Matched required signals: /bill-pay|payment/i, /due|overdue/i, /approved/i, /disputed|exclude/i, /batch/i, /Inbox|approval/i
Missing required signals: /rationale|reason/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/2-5-bill-pay-response.png](screenshots/2-5-bill-pay-response.png)

## 2-5-payment-packet - 2.5 Payment approval packet

**Prompt**

```text
Prepare a payment approval packet for bills due in the next 10 days. Include vendor, amount, due date, coding evidence, duplicate status, cash impact, and the approver role required for the batch.
```

**Observed Atlas Response**

```text
 Payment Approval Packet: Bills Due Within 10 Days

Total Cash Impact: 3,389.00 GBP
Required Approver Role: Admin (Money-out policy)

Bill Details:

1. BT Broadband
Amount: 189.00 GBP
Due Date: 2026-07-01
Coding Evidence: Uncoded (Blocked: Coding incomplete, Source document missing)
Duplicate Status: No risk detected

2. Forster & Reid Ltd
Amount: 3,200.00 GBP
Due Date: 2026-07-05
Coding Evidence: Uncoded (Blocked: Coding incomplete, Source document missing)
Duplicate Status: No risk detected

Note: Both bills are currently blocked from payment due to missing source documents and incomplete coding. These must be resolved before the payment batch can be finalized.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/7 required signals; forbidden hits 0.
Criteria: Prepares payment approval packet with vendor, amount, due date, coding evidence, duplicate status, cash impact, and approver role.
Matched required signals: /amount/i, /due date|due/i, /coding evidence|coding/i, /duplicate/i, /cash impact|cash/i, /approver|approval role/i
Missing required signals: /vendor/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/2-5-payment-packet-response.png](screenshots/2-5-payment-packet-response.png)

## 3-1-family-office - 3.1 Family office structure

**Prompt**

```text
Show the Alderton Family Office structure. List each engagement, service line, billing model, currency, open projects, and missing setup before billing.
```

**Observed Atlas Response**

```text
 Alderton Family Office Structure:

Alderton COSEC Retainer - All Entities
Service Line: cosec
Billing Model: retainer
Currency: GBP
Open Projects: Alderton COSEC Filings (PRJ-0007)
Missing Setup: Source document missing

Alderton Trust (1985) - Trust Accounts & Tax
Service Line: tax
Billing Model: fixed_fee
Currency: GBP
Open Projects: Alderton Trust 1985 Accounts & Tax (PRJ-0006)
Missing Setup: Source document missing

Alderton Family Office - Advisory Retainer
Service Line: advisory
Billing Model: retainer
Currency: GBP
Open Projects: None
Missing Setup: Project or workstream missing, source document missing
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/7 required signals.
Criteria: Shows Alderton family office engagements, service lines, billing models, currency, projects, and missing setup.
Matched required signals: /Alderton/i, /service line|service/i, /billing model|fixed|retainer|T&M/i, /currency|GBP|SGD|USD/i, /project/i, /missing|setup/i
Missing required signals: /engagement/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/3-1-family-office-response.png](screenshots/3-1-family-office-response.png)

## 3-2-scope-creep - 3.2 Scope creep risk

**Prompt**

```text
Review Alderton bespoke tax return scope. Compare actual time, fixed fee, expected margin, open WIP, and recommend whether we need a fee adjustment before billing.
```

**Observed Atlas Response**

```text
 For the Alderton Trust (1985) tax return scope:

Actual Time: 5 hours (currently in draft/WIP)
Fixed Fee: 12,500 GBP
Open WIP: 1,750 GBP (based on an average rate of 350 GBP/hr)
Expected Margin: High. With only 5 hours logged against a 12,500 GBP fee, the current cost of delivery is very low relative to the fee.

Recommendation: No fee adjustment is needed. The engagement is currently significantly under-budget on time, meaning the margin is well-protected. You can proceed with billing as planned.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Compares Alderton bespoke tax actual time, fixed fee, expected margin, WIP, and fee adjustment recommendation.
Matched required signals: /Alderton/i, /bespoke tax|tax return/i, /actual time|hours/i, /fixed fee/i, /margin/i, /WIP/i, /fee adjustment|recommend/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/3-2-scope-creep-response.png](screenshots/3-2-scope-creep-response.png)

## 3-3-sgd-journal - 3.3 Multi-currency trust accounts

**Prompt**

```text
Prepare an SGD 18,000 dividend income journal for Alderton Trust for June 2026. Show the GBP base-currency impact, FX rate provenance, required approval role, and route it to Inbox before posting.
```

**Observed Atlas Response**

```text
 I do not have a tool to directly create or propose specific journal entries for revenue or dividends. However, I can help you manage the month-end close process or generate financial statements for June 2026.

If this dividend income is part of your month-end close requirements, I can run the `prepare_month_end_close` tool for June 2026, which will bootstrap the necessary close tasks and journal review proposals for your team's approval in the Inbox.

Would you like me to prepare the June 2026 month-end close?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/8 required signals; forbidden hits 1.
Criteria: Prepares SGD dividend income journal with GBP impact, FX provenance, approval role, and Inbox routing before posting.
Matched required signals: /dividend/i, /journal/i, /approval role|approval/i, /Inbox/i
Missing required signals: /SGD/i, /18,?000|18000/i, /GBP/i, /FX|exchange rate/i
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/3-3-sgd-journal-response.png](screenshots/3-3-sgd-journal-response.png)

## 3-4-cosec-reminders - 3.4 COSEC reminders

**Prompt**

```text
Review COSEC filing reminders for Alderton entities. Show upcoming filing dates, missing evidence, billing impact, and which reminders need approval before sending.
```

**Observed Atlas Response**

```text
 I do not have a specific tool to review "COSEC filing reminders" or "entity compliance dates." However, I can check for any related billing impact by reviewing the **Work in Progress (WIP)** for Alderton projects or checking for outstanding invoices.

Would you like me to:
1.  **Check WIP** for Alderton entities to see if there is unbilled effort related to filings?
2.  **Run a Finance Ops Check** to see if there are any pending compliance-related action items in the queue?
3.  **List all Alderton engagements** to identify the specific projects involved?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 5/7 required signals; forbidden hits 1.
Criteria: Reviews Alderton COSEC filing reminders, evidence gaps, billing impact, and approvals before sending.
Matched required signals: /Alderton/i, /COSEC/i, /filing/i, /date|deadline/i, /billing impact|billing/i
Missing required signals: /evidence|missing/i, /approval|before sending/i
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/3-4-cosec-reminders-response.png](screenshots/3-4-cosec-reminders-response.png)

## 4-1-usd-engagement - 4.1 USD-billed engagement

**Prompt**

```text
Explain Thornton June billing and cash position in USD and GBP. Show invoice amount, base-currency journal impact, FX rate provenance, AR status, and cash-flow effect after payment.
```

**Observed Atlas Response**

```text
 For the June billing period, Thornton Tech Solutions Ltd has a settled position.

Invoice Details
Invoice INV-1003 was issued for 4,500.00 USD.

Cash Position and Impact
The invoice has been fully paid as of June 30, 2026.

USD Position:
Invoice Amount: 4,500.00 USD
AR Status: Paid (Balance Due: 0.00 USD)
Cash-Flow Effect: +4,500.00 USD

GBP Position:
While the billing was USD-denominated, the base-currency journal impact is recognized in GBP. Based on the current finance snapshot, the transaction is fully settled, meaning the AR balance is zero and the corresponding cash increase has been realized in the base currency.

FX Rate Provenance:
The FX rate used for the base-currency journal was derived from the Aethos system rate at the time of invoice posting (June 10) and the payment date (June 30).

Summary:
Thornton is currently up-to-date with no outstanding AR. The June billing has converted from a receivable to a cash asset.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Explains Thornton June billing/cash in USD and GBP with invoice, FX provenance, AR status, and cash-flow effect.
Matched required signals: /Thornton/i, /June/i, /USD/i, /GBP/i, /invoice/i, /FX|exchange rate/i, /AR|accounts receivable/i, /cash[- ]flow|cash flow/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/4-1-usd-engagement-response.png](screenshots/4-1-usd-engagement-response.png)

## 4-2-series-a - 4.2 Series A milestone

**Prompt**

```text
Thornton Series A closed at $14.2M. Update the milestone amount and invoice. Route any revenue or billing change to Inbox before sending.
```

**Observed Atlas Response**

```text
 Ifound the "Thornton Tech - Series A Tax Structuring" engagement (ID: `0d6c7986-254b-479f-a5dd-ce21e09153ec`), which is a **milestone** engagement currently valued at **$106,500 USD**.

However, the `draft_invoice` tool failed because there are **no invoiceable lines** (approved time, billable expenses, or billing terms) on this engagement yet. The tool only drafts invoices from existing billable data — it doesn't create or update milestone amounts directly.

**To update the milestone amount to $14.2M and invoice it:**
1. The engagement's `total_value` / milestone amount must be updated in the system first (this isn't exposed via the available tools).
2. Once the milestone is recorded, you can use `draft_invoice` to generate the invoice draft, which will route to **Inbox for review** before any invoice is created or sent.

Would you like me to:
- Check if there's any WIP (unbilled time/expenses) on this engagement that could be invoiced now?
- Or confirm that the milestone update needs to be done in the engagement record first, after which I can draft the invoice for Inbox review?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/6 required signals; forbidden hits 1.
Criteria: Updates or prepares Thornton Series A milestone invoice for $14.2M and routes revenue/billing changes to Inbox.
Matched required signals: /Thornton/i, /Series A/i, /14\.2M|14,?200,?000|\$14\.2/i, /milestone/i, /invoice/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: Visible tool-call cards: 1

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/4-2-series-a-response.png](screenshots/4-2-series-a-response.png)

## 4-3-cosec-instruction - 4.3 COSEC instruction

**Prompt**

```text
Review this COSEC instruction for Thornton. Identify the company change, create the required filing/project work item, identify billing impact, and route any external filing or invoice action to Inbox.
```

**Observed Atlas Response**

```text
 I have reviewed the COSEC instruction for Thornton.

**1. Company Change Identified:**
The instruction specifies a change of Registered Office address for Thornton.

**2. Required Filing/Project Work Item:**
A project work item for the Registered Office change filing has been created.

**3. Billing Impact:**
The filing of this change will trigger a standard COSEC administrative fee. I have queued a draft invoice for this service.

**Next Steps:**
The external filing action and the draft invoice have been routed to your **Inbox** for review and approval. Please check your Inbox to finalize these actions.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Extracts Thornton COSEC instruction, identifies company change, creates filing/project work item, billing impact, and Inbox routing.
Matched required signals: /Thornton/i, /COSEC/i, /company change|change/i, /filing/i, /project|work item/i, /billing impact|billing/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/4-3-cosec-instruction-response.png](screenshots/4-3-cosec-instruction-response.png)

## 5-1-close-readiness - 5.1 Pre-close checklist

**Prompt**

```text
Run June 2026 pre-close checks. Show AR, AP, WIP, unposted journals, close tasks, missing approvals, and what needs to happen before the period can be locked.
```

**Observed Atlas Response**

```text
 June 2026 pre-close checks are complete. Here is the current state of the ledger:

Financial Position
AR Aging: 13,500.00 (all current 0-30 days)
AP Aging: 3,389.00 (all current 0-30 days)
WIP: 16,700.00 total unbilled value across 5 projects, including Brightwater Annual Accounts (5,600.00) and Alderton COSEC Filings (3,500.00).

Close Readiness
Unposted Journals: One manual journal (DEMO-JE-ALDERTON-SGD) for 10,440.00 (Dividend income accrual) remains unposted.
Close Tasks: No open action plans or pending human workflows are currently listed in the control room, though operational health is flagged as degraded due to recent tool failures.
Missing Approvals: There are 10 open items in the Inbox, including:
- 2 draft invoices (totaling 61,685.50)
- 1 bill payment batch (3,389.00)
- 2 bill drafts and 1 time entry log
- 3 engagement letter drafts

Requirements Before Period Lock
To lock the June 2026 period, the following must be resolved:
1. Post the unposted dividend income journal (DEMO-JE-ALDERTON-SGD).
2. Clear the Inbox queue, specifically the high-priority draft invoices and the payment batch.
3. Ensure all June WIP is either billed or accrued.
4. Resolve the degraded operational health alerts to ensure data integrity before the final lock.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Runs June pre-close checks across AR, AP, WIP, unposted journals, close tasks, approvals, and period-lock blockers.
Matched required signals: /June 2026|June/i, /AR|accounts receivable/i, /AP|accounts payable/i, /WIP/i, /unposted journal|journal/i, /close task|close/i, /approval/i, /lock|period/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-1-close-readiness-response.png](screenshots/5-1-close-readiness-response.png)

## 5-2-period-lock - 5.2 Period lock

**Prompt**

```text
Can we lock June 2026? Show the period-lock readiness result, blockers, overrides if any, and what a Controller or Owner must review before locking.
```

**Observed Atlas Response**

```text
 June 2026 cannot be locked at this time.

Readiness Result: Blocked

Blockers:
1. Unposted Journals: There is 1 unposted journal (DEMO-JE-ALDERTON-SGD: Alderton Trust SGD dividend income accrual).
2. Incomplete Close Tasks: 5 tasks are still pending or blocked, including:
- Review accruals (Blocked)
- Review deferred revenue release (Open)
- Review recurring journals (Open)
- Review trial balance and close package (Open)
- Lock accounting period (Blocked)

Overrides: None (Override count is 0).

Review Requirements:
- Finance Manager: Must resolve the unposted journal and complete the reviews for accruals, deferred revenue, and recurring journals.
- Controller: Must review the trial balance and the final close package.
- Owner/Admin: Final authorization to lock the period once all blocking tasks are cleared.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Assesses June 2026 period-lock readiness with blockers, overrides, and Controller/Owner review.
Matched required signals: /June 2026/i, /lock|period/i, /readiness|ready/i, /blocker/i, /override/i, /Controller|Owner/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-2-period-lock-response.png](screenshots/5-2-period-lock-response.png)

## 5-3-trial-balance - 5.3 Trial Balance

**Prompt**

```text
Show the June 2026 Trial Balance. Confirm whether debits equal credits, summarize the largest account movements, and flag suspense or unbalanced items.
```

**Observed Atlas Response**

```text
 The Trial Balance for June 2026 is balanced, with total debits equaling total credits.

Summary of Key Movements (vs May 2026):
- Revenue: Stable at 9,000.00.
- Expenses: Increased by 4,139.00 (from 0.00 in May), leading to a net income decrease of 46%.
- Cash Position: Ending cash is 4,500.00.
- Working Capital: Significant exposure with 13,500.00 in open AR, 16,800.00 in WIP, and 3,389.00 in open AP.

Flags:
- No suspense or unbalanced items were found.
- Period Lock Blocked: The month cannot be locked due to one unposted journal (Alderton Trust SGD dividend income accrual) and five incomplete close tasks.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Shows June 2026 Trial Balance, debit/credit balance, largest movements, and suspense/unbalanced items.
Matched required signals: /June 2026/i, /Trial Balance/i, /debit/i, /credit/i, /balance|balanced/i, /movement|largest/i, /suspense|unbalanced/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-3-trial-balance-response.png](screenshots/5-3-trial-balance-response.png)

## 5-4-management-reporting - 5.4 Management reporting

**Prompt**

```text
Alice is at 64% utilisation in June. Which clients have unbilled WIP tied to Alice?
```

**Observed Atlas Response**

```text
 The clients with unbilled WIP tied to Alice are Nexus, Brightwater, and Alderton.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/5 required signals; forbidden hits 0.
Criteria: Identifies clients with unbilled WIP tied to Alice at 64 percent utilization.
Matched required signals: /Alice/i, /unbilled/i, /WIP/i, /client/i
Missing required signals: /64%|64 percent|utili[sz]ation/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-4-management-reporting-response.png](screenshots/5-4-management-reporting-response.png)

## 5-5-management-pack - 5.5 R2R management pack

**Prompt**

```text
Give me the June 2026 month-end management pack. Explain the major variances versus May 2026, show revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers. Do not post journals or lock the period.
```

**Observed Atlas Response**

```text
 Based on the management packs for **June 2026** and **May 2026**, here is the requested analysis:

### **1. Net Income Comparison**
*   **June 2026:** £4,861.00
*   **May 2026:** £9,000.00
*   **Variance:** **-£4,139.00 (-46.0%)**

### **2. Primary Driver of Variance**
The decrease in net income was driven entirely by the emergence of expenses in June. While May had **£0.00** in expenses, June recorded **£4,139.00** in expenses, which directly reduced the net income from £9,000.00 to £4,861.00 (given that revenue remained constant at £9,000.00 in both periods).

### **3. Net Margin Comparison**
*   **June 2026:** 54.0%
*   **May 2026:** 100.0%
*   **Variance:** **-46.0 percentage points**

### **4. Summary Table**

| Metric | May 2026 | June 2026 | Variance |
| :--- | :--- | :--- | :--- |
| **Revenue** | £9,000.00 | £9,000.00 | £0.00 (0%) |
| **Expenses** | £0.00 | £4,139.00 | +£4,139.00 |
| **Net Income** | **£9,000.00** | **£4,861.00** | **-£4,139.00 (-46%)** |
| **Net Margin** | **100.0%** | **54.0%** | **-46.0 pts** |
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 7/10 required signals; forbidden hits 0.
Criteria: Produces June management pack comparing May with variances, revenue, expenses, margins, utilization, AR/AP, journals, and blockers without posting.
Matched required signals: /June 2026/i, /May 2026/i, /variance/i, /revenue/i, /expense/i, /margin/i, /AR|AP/i
Missing required signals: /utili[sz]ation/i, /journal/i, /blocker/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-5-management-pack-response.png](screenshots/5-5-management-pack-response.png)

## 5-5-management-drilldown - 5.5 R2R blocker drilldown

**Prompt**

```text
Drill into the draft journals and close task blockers for June 2026. Which ones block close, who owns them, and what should happen next?
```

**Observed Atlas Response**

```text
 The June 2026 close is currently blocked by one draft journal and five incomplete tasks.

Draft Journal Blocker
The journal DEMO-JE-ALDERTON-SGD (Alderton Trust SGD dividend income accrual) is unposted and must be posted, rejected, or documented before the period can be locked.

Close Task Blockers
The following tasks are pending and block the final period lock:

Finance Manager
Review accruals (Status: Blocked)
Review deferred revenue release (Status: Open)
Review recurring journals (Status: Open)

Controller
Review trial balance and close package (Status: Open)

Admin
Lock accounting period (Status: Blocked)

Next Actions
1. Post or resolve the Alderton Trust SGD dividend accrual journal.
2. The Finance Manager needs to clear the accrual, deferred revenue, and recurring journal reviews.
3. Once those are complete, the Controller can perform the final trial balance review.
4. The Admin can then lock the period.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/5 required signals; forbidden hits 0.
Criteria: Drills into draft journals and close task blockers with owner, close impact, and next action.
Matched required signals: /draft journal|journal/i, /close task|task/i, /block|blocker/i, /next action|should happen/i
Missing required signals: /owner/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-5-management-drilldown-response.png](screenshots/5-5-management-drilldown-response.png)

## 5-5-statement-package - 5.5 Financial statement package

**Prompt**

```text
Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and evidence-backed management commentary. Compare it to May 2026 and show the variances.
```

**Observed Atlas Response**

```text
 The financial statement package for June 2026 has been generated and compared to May 2026.

Financial Summary (June 2026)
Trial Balance: Balanced (Total Dr/Cr: 26,639.00)
Balance Sheet: Balanced
Total Assets: 18,000.00
Total Liabilities: 4,139.00
Total Equity: 13,861.00
Income Statement:
Total Revenue: 9,000.00
Total Expenses: 4,139.00
Net Income: 4,861.00
Cash Flow:
Net Change in Cash: 4,500.00
Ending Cash: 4,500.00
Retained Earnings:
Ending Balance: 4,861.00

Comparative Variances (June vs May 2026)
Revenue: 9,000.00 (Unchanged)
Expenses: Increased by 4,139.00 (May was 0.00)
Net Income: Decreased by 4,139.00 (-46.0%)
Total Assets: Increased by 9,000.00 (+100.0%)
Ending Cash: Increased by 4,500.00

Management Commentary & Evidence
Close Blockers: The period cannot be locked due to one unposted journal (DEMO-JE-ALDERTON-SGD: Alderton Trust SGD dividend income accrual) and 5 incomplete close tasks.
Net Margin: Currently 54.0%, a decrease of 46.0 points compared to May.
Working Capital: Open AR is 13,500.00, AP is 3,389.00, and WIP is 16,800.00, resulting in a net exposure of 26,911.00.
Revenue Driver: Accounting is the primary service line, contributing 9,000.00 in revenue with a 77.3% margin.

Close-Readiness Warnings
Status: Blocked
Warnings:
- Close prerequisites are incomplete (unposted journals, close tasks).
- Checklist tasks remain incomplete or unwaived.
- The period is not ready to lock.

Next Actions
1. Post, reject, or document the draft journal for the Alderton Trust dividend accrual.
2. Complete or waive the 5 pending close tasks, including the WIP accrual and deferred revenue reviews.
3. Lock the accounting period once blockers are cleared.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/8 required signals.
Criteria: Generates financial statement package with TB, BS, IS, cash flow, retained earnings, statutory pack, warnings, commentary, and May variance.
Matched required signals: /Trial Balance/i, /Balance Sheet/i, /Income Statement/i, /Cash Flow/i, /Retained Earnings/i, /warning|close-readiness/i, /variance|May 2026/i
Missing required signals: /Statutory Pack/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-5-statement-package-response.png](screenshots/5-5-statement-package-response.png)

## 5-5-year-end - 5.5 Year-end close

**Prompt**

```text
Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.
```

**Observed Atlas Response**

```text
 The year-end close preparation for fiscal year 2026 has been initiated.

Review of close state for December 2026:
- Retained Earnings: A review task (ID: 73b8464f-78ae-4f9c-be8b-37a2ad279ab5) has been routed to the Inbox for approval. The retained earnings posting will only be executed once approved.
- P&L Activity: There is no posted P&L activity for the current period (Revenue: 0.00, Expenses: 0.00).
- Locked Periods: The period is currently unlocked and ready to lock, pending the completion of the close task checklist.
- Duplicate Close Risk: No duplicate close risk detected; no prior year-end journals have been posted for 2026.
- Statement Movement: There is zero variance between the current (2026-12) and prior (2026-11) periods. Total assets remain at 18,000.00 and total equity at 13,861.00.

Next actions:
- Approve the retained earnings posting in the Inbox.
- Bootstrap the close task checklist for December 2026.
- Lock the period once approvals and checklists are complete.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Prepares FY2026 year-end close with retained earnings, P&L activity, locked periods, duplicate risk, statement movement, and Inbox routing.
Matched required signals: /2026|FY2026/i, /year-end|year end/i, /retained earnings/i, /P&L|profit and loss/i, /locked period|period/i, /duplicate/i, /statement movement|prior year/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-5-year-end-response.png](screenshots/5-5-year-end-response.png)

## 5-6-manual-journal - 5.6 Manual journal lifecycle

**Prompt**

```text
Review this manual journal proposal for balance, account validity, period lock status, business reason, supporting evidence, approval role, and whether the approver is different from the submitter. Do not post it without Inbox approval.
```

**Observed Atlas Response**

```text
 Based on the provided data, there is a posted journal entry (`b23f5e1a-f307-49be-80f3-5213b03e3aea`) that was created specifically for a reversal demonstration.

**Journal Details:**
- **Entry Number:** DEMO-JE-MANUAL-001
- **Description:** Manual accrual posted for reversal demonstration
- **Date:** 2026-06-24
- **Status:** Posted
- **Total Value:** 750.00 GBP
- **Lines:**
    - **Debit:** 750.00 GBP to Expenses (Account 5000)
    - **Credit:** 750.00 GBP to Accounts Payable (Account 2000)

According to the control notes, reversing this entry would require creating a new reversing journal rather than editing the original posted entry.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 2/8 required signals; forbidden hits 0.
Criteria: Reviews manual journal proposal for balance, account validity, period lock, reason, evidence, approval role, and segregation of duties.
Matched required signals: /journal/i, /account/i
Missing required signals: /balance|balanced/i, /period lock|locked period/i, /business reason|reason/i, /evidence|support/i, /approval role|approval/i, /approver.*submitter|different from submitter|segregation/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-6-manual-journal-response.png](screenshots/5-6-manual-journal-response.png)

## 5-6-reversal - 5.6 Manual journal reversal

**Prompt**

```text
Prepare a reversal packet for this posted manual journal. Explain why reversal is appropriate, propose an open-period reversal date, show the flipped debit and credit lines, and confirm the reversal will create a new journal rather than editing the original.
```

**Observed Atlas Response**

```text
 Reversal Packet: DEMO-JE-MANUAL-001

Reason for Reversal
This is a manual accrual posted for professional expenses. Reversing the entry is appropriate to clear the temporary liability and expense recognition once the actual invoice is received or the obligation is settled, ensuring the accounts reflect the actual realized cost.

Proposed Reversal Date
2026-07-01 (Open Period)

Proposed Reversal Entry
Debit: Accounts Payable (2000) - 750.00 GBP
Credit: Expenses (5000) - 750.00 GBP

Audit Confirmation
In accordance with Aethos control policies, this reversal will create a new, separate reversing journal. The original posted journal (DEMO-JE-MANUAL-001) will remain unchanged to preserve the audit trail.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/7 required signals.
Criteria: Prepares reversal packet with reason, open-period date, flipped debit/credit lines, and new journal rather than editing original.
Matched required signals: /reversal/i, /journal/i, /reason|appropriate/i, /open period|date/i, /debit/i, /credit/i
Missing required signals: /new journal|not edit|rather than editing/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/5-6-reversal-response.png](screenshots/5-6-reversal-response.png)

## 6-1-finance-ops-check - 6.1 Finance Ops Manager

**Prompt**

```text
Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.
```

**Observed Atlas Response**

```text
 Read-Only Findings

Billing (WIP)
The following unbilled amounts are currently held in WIP:
- Brightwater Annual Accounts FY2025: 5,600.00
- Alderton COSEC Filings: 3,500.00
- Nexus CFO Advisory: 3,150.00
- Brightwater Monthly Management Accounts: 2,800.00
- Alderton Trust 1985 Accounts & Tax: 1,750.00

Payments (AP)
- Total AP Aging: 3,389.00 (all current 0-30 days).

Collections (AR)
- Total AR Aging: 13,500.00 (all current 0-30 days).

Close & Review
- Operational Health: The system status is currently Degraded. There are warnings regarding tenant health and a spike in background failures (atlas_provider_timeout).
- System Errors: One failed invocation of the draft_invoice tool was recorded in the last 24 hours.

Actions Requiring Inbox Approval

- Billing: Draft invoices for the WIP items listed above.
- Payments: Propose a payment batch for the current 3,389.00 AP balance.
- Review: Investigate the degraded system health and draft_invoice tool failure.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Runs finance ops check separating read-only findings from Inbox-gated actions across billing, payment, collections, close, and review.
Matched required signals: /billing/i, /payment/i, /collections/i, /close/i, /review/i, /read-only|read only/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/6-1-finance-ops-check-response.png](screenshots/6-1-finance-ops-check-response.png)

## 6-1-action-plan - 6.1 Finance Ops action plan

**Prompt**

```text
Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.
```

**Observed Atlas Response**

```text
 I have created the recommended finance ops action plan for June 2026. A manager-level work plan containing the next priority items has been routed to your Inbox for review.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/6 required signals; forbidden hits 1.
Criteria: Creates at most five manager-reviewed finance ops work items and routes action plan to Inbox without approving sensitive actions.
Matched required signals: /finance ops/i, /work item|action plan/i, /manager-reviewed|review/i, /Inbox|approval/i
Missing required signals: /five|5|at most/i, /invoice|payment|journal|email/i
Invalid answer signals: Visible tool-call cards: 1

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/6-1-action-plan-response.png](screenshots/6-1-action-plan-response.png)

## 6-2-scheduled-control-room - 6.2 Scheduled Finance Ops Manager

**Prompt**

```text
Before enabling a scheduled Finance Ops Manager run, show the current cadence, escalation windows, last run, open scheduled plans, and approval boundary for resulting work.
```

**Observed Atlas Response**

```text
 The Aethos system is currently unreachable, so I cannot retrieve the Finance Ops Manager cadence, escalation windows, or approval boundaries at this time. I will monitor the connection and can try again in a few minutes.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/6 required signals; forbidden hits 0.
Criteria: Shows scheduled Finance Ops cadence, escalation windows, last run, open plans, and approval boundary before enablement.
Matched required signals: /scheduled|cadence/i, /Finance Ops/i, /escalation/i, /approval boundary|approval/i
Missing required signals: /last run/i, /open .*plan|scheduled plan/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/6-2-scheduled-control-room-response.png](screenshots/6-2-scheduled-control-room-response.png)

## 7-1-approval-controls - 7.1 Approval policy and personas

**Prompt**

```text
What am I allowed to approve, what requires Owner approval, and which Inbox items are high risk? Include my finance personas, effective thresholds, pending high-risk tasks, and why each item needs review. Do not show tool names, policy reason codes, raw payloads, traces, logs, or context IDs.
```

**Observed Atlas Response**

```text
 I'm sorry, but the Aethos system is currently unreachable. I cannot retrieve your approval permissions, finance personas, or the current high-risk items in your Inbox at this time. Please let me know if you'd like me to try again in a few moments.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/7 required signals; forbidden hits 0.
Criteria: Explains approval permissions, Owner approval thresholds, high-risk Inbox items, personas, and reasons without exposing internals.
Matched required signals: /approve|approval/i, /persona|role/i, /Inbox/i, /high risk|risk/i
Missing required signals: /Owner/i, /threshold/i, /review/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/7-1-approval-controls-response.png](screenshots/7-1-approval-controls-response.png)

## 7-2-decision-trail - 7.2 Decision trail

**Prompt**

```text
Show the decision trail for the latest bill, invoice, payment batch, journal, or close record. Include the related Inbox task, actor role, decision type, timestamp, and before/after review summary.
```

**Observed Atlas Response**

```text
 The latest decision trail is for a Finance Ops Action Plan review.

Inbox Task: Review: Copilot Agent (ID: 286a39c7-b340-4d0d-a887-71f724fd75e0)
Actor Role: Not specified (Pending)
Decision Type: Open
Timestamp: 2026-06-30 08:55:16 UTC

Review Summary:
Before: Period 2026-06, Status: ready_for_review (Tool: create_finance_ops_action_plan)
After: Period 2026-06, Status: ready_for_review (Tool: create_finance_ops_action_plan)
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Shows decision trail with related Inbox task, actor role, decision type, timestamp, and before/after summary.
Matched required signals: /decision/i, /Inbox/i, /actor role|role/i, /decision type|type/i, /timestamp|time/i, /before\/after|before and after|review summary/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/7-2-decision-trail-response.png](screenshots/7-2-decision-trail-response.png)

## 7-3-operational-health - 7.3 Operational Health

**Prompt**

```text
Show operational health for the platform today. Include degraded health, public endpoint abuse, background failure spikes, and agent/tool/workflow failure spikes. Do not expose secrets, traces, raw logs, or stack traces.
```

**Observed Atlas Response**

```text
 Platform health is currently degraded.

Health Summary:
- Overall Status: Degraded
- Background Failures: Spike detected with 4 failures attributed to atlas_provider_timeout.
- Agent/Tool/Workflow Failures: Spike detected with 1 tool invocation failure for draft_invoice.
- Public Endpoint Abuse: No evidence of abuse; however, there was 1 request failure (400 Bad Request) on the tools execution endpoint.

All core data tables are reporting healthy status.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Shows operational health with degraded status, public abuse, background failures, agent/tool/workflow failures, and no secrets/logs/traces.
Matched required signals: /health/i, /degraded|status/i, /public endpoint|abuse/i, /background/i, /agent|tool|workflow/i, /failure|spike|alert/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/7-3-operational-health-response.png](screenshots/7-3-operational-health-response.png)

## 7-4-documents-audit - 7.4 Documents and source evidence

**Prompt**

```text
Show documents that support recent engagements, bills, invoices, journals, and Inbox decisions. For each, show the linked business record, source filename, extraction state, and what I should review next.
```

**Observed Atlas Response**

```text
 I'm currently unable to retrieve the audit and intake documents from Aethos due to a system error. I will alert the finance operations team to investigate the connection issue and let you know as soon as the document lineage and extraction states are available for review.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 2/8 required signals; forbidden hits 0.
Criteria: Shows source documents linked to engagements, bills, invoices, journals, and Inbox decisions with extraction state and next review.
Matched required signals: /document|source/i, /extraction state|extracted|processing/i
Missing required signals: /engagement/i, /bill/i, /invoice/i, /journal/i, /Inbox/i, /review next|next review|what .* review/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/7-4-documents-audit-response.png](screenshots/7-4-documents-audit-response.png)

## 7-5-config-telemetry - 7.5 Configuration and telemetry

**Prompt**

```text
Review configuration and telemetry readiness. Show approval controls, scheduled Finance Ops Manager settings, Atlas runtime, Langfuse observability status, operational alerts, and any public abuse-path controls that need attention.
```

**Observed Atlas Response**

```text
 The Aethos system is currently unreachable, which is preventing me from accessing the configuration and telemetry data. I am unable to retrieve the approval controls, Finance Ops Manager settings, runtime status, or observability metrics at this time. Please check the server status or let me know when I should try again.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 3/7 required signals; forbidden hits 0.
Criteria: Reviews approval controls, scheduled Finance Ops, Atlas runtime, Langfuse observability, operational alerts, and abuse controls.
Matched required signals: /approval controls|approval/i, /scheduled Finance Ops|Finance Ops/i, /observability|telemetry/i
Missing required signals: /Atlas runtime|Atlas/i, /Langfuse/i, /alert/i, /abuse|public/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T08-21-24-214Z/screenshots/7-5-config-telemetry-response.png](screenshots/7-5-config-telemetry-response.png)

## Browser Console Errors

- `Failed to load Atlas threads: TypeError: Failed to fetch
    at https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:2:3143
    at t.<computed> (https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:1:13713)
    at n.<anonymo`

## Network Failures And 5xx Responses

- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status`
- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20`
