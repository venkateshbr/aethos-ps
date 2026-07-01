# Demo Guide v2 Production Browser Validation

Run ID: `2026-06-30T12-09-20-781Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-06-30T12:20:39.724Z`

This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.

Summary: PASS 26, WARN 0, FAIL 1, SKIP 0

## Evidence Table

| ID | Section | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| auth | Authentication | Logged into https://aethos.ishirock.tech | PASS | [screenshot](screenshots/auth-login-filled.png) | Tenant: Meridian Demo v2 20260630063630<br>Tenant ID: a0267012-73a9-416c-bba2-81d86e2bbba4<br>User: prod-demo-v2-20260630063630@aethos-qa.dev |
| route-copilot | Route Coverage | Aethos Atlas | PASS | [screenshot](screenshots/route-copilot.png) | URL: https://aethos.ishirock.tech/app/copilot<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat Th |
| route-documents | Route Coverage | Documents | PASS | [screenshot](screenshots/route-documents.png) | URL: https://aethos.ishirock.tech/app/documents<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Documents Docum |
| route-inbox | Route Coverage | Inbox | PASS | [screenshot](screenshots/route-inbox.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Inbox 20 All En |
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
| 1-3a-delivery-data | 1.3A People and WIP | Atlas prompt | PASS | [screenshot](screenshots/1-3a-delivery-data-response.png) | Business-valid answer: matched 6/7 required signals.<br>Missing required signals: /June/i |
| 1-4-billing-run | 1.4 Mixed model invoice | Atlas prompt | PASS | [screenshot](screenshots/1-4-billing-run-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-5-revenue-recognition | 1.5 Revenue recognition | Atlas prompt | PASS | [screenshot](screenshots/1-5-revenue-recognition-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-6-capped-tax | 1.6 Capped tax engagement | Atlas prompt | PASS | [screenshot](screenshots/1-6-capped-tax-response.png) | Business-valid answer: matched 6/6 required signals. |
| 1-7-o2c-readiness | 1.7 O2C controls | Atlas prompt | FAIL | [screenshot](screenshots/1-7-o2c-readiness-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/8 required signals; forbidden hits 1.<br>Missing required signals: /Nexus/i, /service catalogue/catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link/public invoice/i, /WIP/i, /collections/i<br>Invalid answer signals: No Atlas response captured. |

## Prompt Transcript

## 1-1-engagement-letter - 1.1 Engagement letter onboarding

**Prompt**

```text
Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.
```

**Observed Atlas Response**

```text
 I have reviewed the engagement letter for Nexus Capital Partners LP.

I have prepared the client, engagement, billing terms, and the first project (Statutory Accounts - FY2025) based on the extracted terms:
- Total Value: GBP 144,000.00
- Fixed Fee: GBP 42,000.00
- Monthly Retainer: GBP 8,500.00
- Period: 2026-01-01 to 2026-12-31
- Rate Card: CFO Advisory Partner (GBP 350/hr), Manager (GBP 240/hr), and Associate (GBP 145/hr).

As these are material master-data changes, I have routed the complete engagement draft to the Inbox for your review and approval. Please check the Inbox to finalize the setup.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Extracts the uploaded Nexus engagement letter instead of asking the user to retype it. | Creates or prepares client, engagement, billing terms, rate card, and first project. | Routes risky or incomplete items to Inbox.
Matched required signals: /Nexus/i, /client/i, /engagement/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i, /Inbox|review|risk/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T12-09-20-781Z/screenshots/1-1-engagement-letter-response.png](screenshots/1-1-engagement-letter-response.png)

## 1-2-engagement-structure - 1.2 Project structure

**Prompt**

```text
Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.
```

**Observed Atlas Response**

```text
 Nexus Capital Partners has two active engagements:

Group Accounting & Advisory
This engagement is ready for billing.
Active Projects:
- Nexus CFO Advisory: T&M (Advisory hour at 350 GBP)
- Nexus Group Consolidation FY2025: Fixed Fee (Part of 48,000 GBP total fixed fee)
- Nexus Monthly Management Accounts: Retainer (9,000 GBP per month)

Corporation Tax Return FY2025
This engagement requires setup review before billing.
Active Projects:
None.
Missing Items:
- Project or workstream definition
- Source documents (engagement letter)

The total value across both engagements is 178,000 GBP.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 4/4 required signals.
Criteria: Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.
Matched required signals: /Nexus/i, /project|workstream/i, /billing model|fixed|retainer|T&M|time and materials/i, /missing|ready|before billing|setup/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T12-09-20-781Z/screenshots/1-2-engagement-structure-response.png](screenshots/1-2-engagement-structure-response.png)

## 1-3-log-time - 1.3 Time entry

**Prompt**

```text
Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling
```

**Observed Atlas Response**

```text
 I have logged 4.5 hours to the Nexus CFO Advisory project for board pack review and cash flow modelling. This entry has been sent to your Inbox for review and approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 5/5 required signals.
Criteria: Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.
Matched required signals: /4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /time|hours/i, /logged|created|Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T12-09-20-781Z/screenshots/1-3-log-time-response.png](screenshots/1-3-log-time-response.png)

## 1-3a-delivery-data - 1.3A People and WIP

**Prompt**

```text
Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.
```

**Observed Atlas Response**

```text
 Delivery and utilization context for Alice in 2026-06:
- Approved hours 0; pending hours 24.0; utilization 0.00%; WIP 0.00; billable expenses 185.50.
- Invoice-ready billable expenses: 1 item(s), total 185.50.
Use the WIP and Project P&L reports for invoice-ready detail; I did not create an invoice.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/7 required signals.
Criteria: Summarizes Alice Chen June delivery, utilization, WIP, expenses, and invoice readiness for Nexus.
Matched required signals: /Alice Chen|Alice/i, /approved time|pending time|hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice|invoiced/i
Missing required signals: /June/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T12-09-20-781Z/screenshots/1-3a-delivery-data-response.png](screenshots/1-3a-delivery-data-response.png)

## 1-4-billing-run - 1.4 Mixed model invoice

**Prompt**

```text
Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending.
```

**Observed Atlas Response**

```text
 Prepared the Nexus 2026-06 billing run draft and routed the invoice to Inbox before sending.
Draft invoice lines:
- Group Statutory Accounts: fixed fee milestone 1/2, GBP 21,000.00.
- Monthly Management Accounts: June retainer, GBP 8,500.00.
- CFO Advisory: T&M advisory hours, 12.5 hours x GBP 350 = GBP 4,375.00.
- Approved expenses: Travel & Subsistence, GBP 843.20.
- Journal impact after approval: DR Accounts Receivable for the gross invoice; CR Revenue for fixed fee, retainer, T&M, and expenses; CR VAT/tax payable where applicable.
No invoice was sent directly. Review the Inbox invoice draft before customer delivery.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Prepares Nexus June billing run with fixed fee, retainer, T&M hours, expenses, draft invoice lines, and Inbox routing.
Matched required signals: /Nexus/i, /June 2026|June/i, /fixed fee/i, /retainer/i, /T&M|time and materials|hour/i, /expense/i, /invoice line|draft invoice/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T12-09-20-781Z/screenshots/1-4-billing-run-response.png](screenshots/1-4-billing-run-response.png)

## 1-5-revenue-recognition - 1.5 Revenue recognition

**Prompt**

```text
Explain how Nexus June revenue is recognized across fixed-fee milestone, retainer, T&M advisory WIP, and expenses. Tie the explanation to invoice-backed journals and Project P&L.
```

**Observed Atlas Response**

```text
 Nexus 2026-06 revenue recognition uses each billing model separately:
- Fixed fee milestone: recognize the approved milestone amount when the milestone invoice is approved; no T&M WIP is needed for that fixed-fee line.
- Monthly retainer: recognize the June retainer in June revenue. If an annual retainer were paid upfront, it would be deferred and released monthly.
- T&M advisory WIP: approved billable hours are held as WIP until invoiced; the invoice-backed journal recognizes advisory revenue.
- Approved expenses: bill at cost or agreed markup according to the engagement terms and include the recoverable amount on the invoice.
- Journal impact: invoice approval posts DR Accounts Receivable, CR Revenue for fixed fee/retainer/T&M/expenses, and CR VAT/tax payable where applicable.
Project P&L ties the revenue to delivery cost and margin. Any invoice send or accounting-sensitive correction remains routed through Inbox approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Explains Nexus revenue recognition across milestone/fixed fee, retainer, T&M WIP, expenses, journals, and Project P&L.
Matched required signals: /Nexus/i, /revenue/i, /fixed fee|milestone/i, /retainer/i, /T&M|WIP|time and materials/i, /expense/i, /journal/i, /Project P&L|project/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T12-09-20-781Z/screenshots/1-5-revenue-recognition-response.png](screenshots/1-5-revenue-recognition-response.png)

## 1-6-capped-tax - 1.6 Capped tax engagement

**Prompt**

```text
Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun
```

**Observed Atlas Response**

```text
 I have prepared the engagement draft for Nexus Capital Partners LP for the Corporation Tax Return FY2025 with a fixed fee of £18,500 and a cap of £22,000. This has been routed to the Aethos Inbox for approval.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Creates or prepares Nexus capped tax engagement with fixed fee, cap, and Inbox approval if required.
Matched required signals: /Nexus/i, /Corporation Tax|Tax Return|FY2025/i, /18,?500|18500/i, /22,?000|22000|cap/i, /engagement/i, /Inbox|approval|created/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T12-09-20-781Z/screenshots/1-6-capped-tax-response.png](screenshots/1-6-capped-tax-response.png)

## 1-7-o2c-readiness - 1.7 O2C controls

**Prompt**

```text
Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval.
```

**Observed Atlas Response**

```text

```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/8 required signals; forbidden hits 1.
Criteria: Reviews Nexus O2C readiness across service catalogue, rate card, tax, invoices, payment links, WIP, and collections approvals.
Matched required signals: none
Missing required signals: /Nexus/i, /service catalogue|catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link|public invoice/i, /WIP/i, /collections/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T12-09-20-781Z/screenshots/1-7-o2c-readiness-response.png](screenshots/1-7-o2c-readiness-response.png)

## Browser Console Errors

- `Failed to load Atlas threads: TypeError: Failed to fetch
    at https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:2:3143
    at t.<computed> (https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:1:13713)
    at n.<anonymo`

## Network Failures And 5xx Responses

- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20`
- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status`
