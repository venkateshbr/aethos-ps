# Demo Guide v2 Production Browser Validation

Run ID: `2026-06-29T06-44-39-272Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-06-29T06:50:26.176Z`

This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.

Summary: PASS 19, WARN 0, FAIL 11, SKIP 0

## Evidence Table

| ID | Section | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| auth | Authentication | Logged into https://aethos.ishirock.tech | PASS | [screenshot](screenshots/auth-login-filled.png) | Tenant: Meridian Hermes Demo 1782477159363<br>Tenant ID: f3fe988f-bade-4037-b709-efb077faee67<br>User: prod-hermes-demo-1782477159363@aethos-qa.dev |
| route-copilot | Route Coverage | Aethos Atlas | PASS | [screenshot](screenshots/route-copilot.png) | URL: https://aethos.ishirock.tech/app/copilot<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat Ne |
| route-documents | Route Coverage | Documents | PASS | [screenshot](screenshots/route-documents.png) | URL: https://aethos.ishirock.tech/app/documents<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Documents Docum |
| route-inbox | Route Coverage | Inbox | PASS | [screenshot](screenshots/route-inbox.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Inbox 4 All Eng |
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
| 1-1-engagement-letter | 1.1 Engagement letter onboarding | Atlas prompt | FAIL | [screenshot](screenshots/1-1-engagement-letter-response.png) | Attachment banner before prompt: attach_file Attached: nexus_engagement_letter.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Expected response signals matched 0/1.<br>Business validation failed: matched 0/7 required signals; forbidden hits 1.<br>Missing required signals: /Nexus/i, /client/i, /engagement/i, /billing/fixed/retainer/T&M/time and materials/mixed/i, /rate card/rate/i, /project/i, /Inbox/review/risk/i<br>Invalid answer signals: No Atlas response captured. |
| 1-2-engagement-structure | 1.2 Project structure | Atlas prompt | FAIL | [screenshot](screenshots/1-2-engagement-structure-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/4 required signals; forbidden hits 0.<br>Missing required signals: /Nexus/i, /project/workstream/i, /billing model/fixed/retainer/T&M/time and materials/i, /missing/ready/before billing/setup/i |
| 1-3-log-time | 1.3 Time entry | Atlas prompt | FAIL | [screenshot](screenshots/1-3-log-time-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/5 required signals; forbidden hits 0.<br>Missing required signals: /4\.5/4\.50/i, /Nexus/i, /CFO Advisory/board pack/cash flow/i, /time/hours/i, /logged/created/Inbox/approval/i |
| 1-3a-delivery-data | 1.3A People and WIP | Atlas prompt | FAIL | [screenshot](screenshots/1-3a-delivery-data-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/7 required signals; forbidden hits 0.<br>Missing required signals: /Alice Chen/Alice/i, /June/i, /approved time/pending time/hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice/invoiced/i |
| 1-4-billing-run | 1.4 Mixed model invoice | Atlas prompt | FAIL | [screenshot](screenshots/1-4-billing-run-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/8 required signals; forbidden hits 0.<br>Missing required signals: /Nexus/i, /June 2026/June/i, /fixed fee/i, /retainer/i, /T&M/time and materials/hour/i, /expense/i, /invoice line/draft invoice/i, /Inbox/approval/i |
| 1-5-revenue-recognition | 1.5 Revenue recognition | Atlas prompt | FAIL | [screenshot](screenshots/1-5-revenue-recognition-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/8 required signals; forbidden hits 0.<br>Missing required signals: /Nexus/i, /revenue/i, /fixed fee/milestone/i, /retainer/i, /T&M/WIP/time and materials/i, /expense/i, /journal/i, /Project P&L/project/i |
| 1-6-capped-tax | 1.6 Capped tax engagement | Atlas prompt | FAIL | [screenshot](screenshots/1-6-capped-tax-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/6 required signals; forbidden hits 0.<br>Missing required signals: /Nexus/i, /Corporation Tax/Tax Return/FY2025/i, /18,?500/18500/i, /22,?000/22000/cap/i, /engagement/i, /Inbox/approval/created/i |
| 1-7-o2c-readiness | 1.7 O2C controls | Atlas prompt | FAIL | [screenshot](screenshots/1-7-o2c-readiness-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/8 required signals; forbidden hits 0.<br>Missing required signals: /Nexus/i, /service catalogue/catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link/public invoice/i, /WIP/i, /collections/i |
| 1-7-collections-read | 1.7 Collections read pack | Atlas prompt | FAIL | [screenshot](screenshots/1-7-collections-read-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/8 required signals; forbidden hits 0.<br>Missing required signals: /customer/i, /balance/i, /invoice/i, /due date/due/i, /aging/overdue/i, /reminder/i, /blocker/blocked/i, /next action/i |
| 1-7-invoice-drilldown | 1.7 Invoice drilldown | Atlas prompt | FAIL | [screenshot](screenshots/1-7-invoice-drilldown-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/8 required signals; forbidden hits 0.<br>Missing required signals: /INV-1001/i, /due date/due/i, /aging/overdue/i, /balance/i, /paid/payment/i, /reminder/i, /blocker/blocked/i, /next action/recommend/i |
| 1-7-draft-reminders | 1.7 Collections controlled write | Atlas prompt | FAIL | [screenshot](screenshots/1-7-draft-reminders-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/6 required signals; forbidden hits 0.<br>Missing required signals: /reminder/i, /invoice/i, /30 days/overdue/i, /customer/i, /Inbox/approval/i, /draft/i |

## Prompt Transcript

## 1-1-engagement-letter - 1.1 Engagement letter onboarding

**Prompt**

```text
Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.
```

**Observed Atlas Response**

```text
(no response captured)
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/7 required signals; forbidden hits 1.
Criteria: Extracts the uploaded Nexus engagement letter instead of asking the user to retype it. | Creates or prepares client, engagement, billing terms, rate card, and first project. | Routes risky or incomplete items to Inbox.
Matched required signals: none
Missing required signals: /Nexus/i, /client/i, /engagement/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i, /Inbox|review|risk/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-1-engagement-letter-response.png](screenshots/1-1-engagement-letter-response.png)

## 1-2-engagement-structure - 1.2 Project structure

**Prompt**

```text
Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/4 required signals; forbidden hits 0.
Criteria: Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.
Matched required signals: none
Missing required signals: /Nexus/i, /project|workstream/i, /billing model|fixed|retainer|T&M|time and materials/i, /missing|ready|before billing|setup/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-2-engagement-structure-response.png](screenshots/1-2-engagement-structure-response.png)

## 1-3-log-time - 1.3 Time entry

**Prompt**

```text
Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/5 required signals; forbidden hits 0.
Criteria: Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.
Matched required signals: none
Missing required signals: /4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /time|hours/i, /logged|created|Inbox|approval/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-3-log-time-response.png](screenshots/1-3-log-time-response.png)

## 1-3a-delivery-data - 1.3A People and WIP

**Prompt**

```text
Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/7 required signals; forbidden hits 0.
Criteria: Summarizes Alice Chen June delivery, utilization, WIP, expenses, and invoice readiness for Nexus.
Matched required signals: none
Missing required signals: /Alice Chen|Alice/i, /June/i, /approved time|pending time|hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice|invoiced/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-3a-delivery-data-response.png](screenshots/1-3a-delivery-data-response.png)

## 1-4-billing-run - 1.4 Mixed model invoice

**Prompt**

```text
Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending.
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/8 required signals; forbidden hits 0.
Criteria: Prepares Nexus June billing run with fixed fee, retainer, T&M hours, expenses, draft invoice lines, and Inbox routing.
Matched required signals: none
Missing required signals: /Nexus/i, /June 2026|June/i, /fixed fee/i, /retainer/i, /T&M|time and materials|hour/i, /expense/i, /invoice line|draft invoice/i, /Inbox|approval/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-4-billing-run-response.png](screenshots/1-4-billing-run-response.png)

## 1-5-revenue-recognition - 1.5 Revenue recognition

**Prompt**

```text
Explain how Nexus June revenue is recognized across fixed-fee milestone, retainer, T&M advisory WIP, and expenses. Tie the explanation to invoice-backed journals and Project P&L.
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/8 required signals; forbidden hits 0.
Criteria: Explains Nexus revenue recognition across milestone/fixed fee, retainer, T&M WIP, expenses, journals, and Project P&L.
Matched required signals: none
Missing required signals: /Nexus/i, /revenue/i, /fixed fee|milestone/i, /retainer/i, /T&M|WIP|time and materials/i, /expense/i, /journal/i, /Project P&L|project/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-5-revenue-recognition-response.png](screenshots/1-5-revenue-recognition-response.png)

## 1-6-capped-tax - 1.6 Capped tax engagement

**Prompt**

```text
Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/6 required signals; forbidden hits 0.
Criteria: Creates or prepares Nexus capped tax engagement with fixed fee, cap, and Inbox approval if required.
Matched required signals: none
Missing required signals: /Nexus/i, /Corporation Tax|Tax Return|FY2025/i, /18,?500|18500/i, /22,?000|22000|cap/i, /engagement/i, /Inbox|approval|created/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-6-capped-tax-response.png](screenshots/1-6-capped-tax-response.png)

## 1-7-o2c-readiness - 1.7 O2C controls

**Prompt**

```text
Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval.
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/8 required signals; forbidden hits 0.
Criteria: Reviews Nexus O2C readiness across service catalogue, rate card, tax, invoices, payment links, WIP, and collections approvals.
Matched required signals: none
Missing required signals: /Nexus/i, /service catalogue|catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link|public invoice/i, /WIP/i, /collections/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-7-o2c-readiness-response.png](screenshots/1-7-o2c-readiness-response.png)

## 1-7-collections-read - 1.7 Collections read pack

**Prompt**

```text
Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/8 required signals; forbidden hits 0.
Criteria: Shows collections customers with balances, invoices, due dates, aging, reminders, blockers, and next action without drafting.
Matched required signals: none
Missing required signals: /customer/i, /balance/i, /invoice/i, /due date|due/i, /aging|overdue/i, /reminder/i, /blocker|blocked/i, /next action/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-7-collections-read-response.png](screenshots/1-7-collections-read-response.png)

## 1-7-invoice-drilldown - 1.7 Invoice drilldown

**Prompt**

```text
Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action.
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/8 required signals; forbidden hits 0.
Criteria: Reviews INV-1001 with due date, aging, balance, paid status, payment link, reminders, blockers, and next action.
Matched required signals: none
Missing required signals: /INV-1001/i, /due date|due/i, /aging|overdue/i, /balance/i, /paid|payment/i, /reminder/i, /blocker|blocked/i, /next action|recommend/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-7-invoice-drilldown-response.png](screenshots/1-7-invoice-drilldown-response.png)

## 1-7-draft-reminders - 1.7 Collections controlled write

**Prompt**

```text
Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.
```

**Observed Atlas Response**

```text
 HTTP 402: This request requires more credits, or fewer max_tokens. You requested up to 64000 tokens, but can only afford 61844. To increase, visit https://openrouter.ai/workspaces/default/keys/1fb1b36469ecf7478e264cf5e2da63bdf7a79d42793fb4d3ca71efd4dbc73486 and adjust the key's total limit
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/6 required signals; forbidden hits 0.
Criteria: Drafts customer-specific reminders for invoices over 30 days overdue and routes them to Inbox before sending.
Matched required signals: none
Missing required signals: /reminder/i, /invoice/i, /30 days|overdue/i, /customer/i, /Inbox|approval/i, /draft/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/screenshots/1-7-draft-reminders-response.png](screenshots/1-7-draft-reminders-response.png)

## Browser Console Errors

- `Failed to load Atlas threads: TypeError: Failed to fetch
    at https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:2:3143
    at t.<computed> (https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:1:13713)
    at n.<anonymo`
- `Document processing failed: Error: Document extraction failed
    at n.<anonymous> (https://aethos.ishirock.tech/chunk-L2SXWXOM.js:6:2419)
    at Generator.next (<anonymous>)
    at i (https://aethos.ishirock.tech/chunk-`

## Network Failures And 5xx Responses

- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20`
- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status`
