# Demo Guide v2 Production Browser Validation

Run ID: `2026-06-30T14-08-52-793Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-06-30T14:43:20.520Z`

This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.

Summary: PASS 27, WARN 0, FAIL 6, SKIP 0

## Evidence Table

| ID | Section | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| auth | Authentication | Logged into https://aethos.ishirock.tech | PASS | [screenshot](screenshots/auth-login-filled.png) | Tenant: Meridian Demo v2 20260630063630<br>Tenant ID: a0267012-73a9-416c-bba2-81d86e2bbba4<br>User: prod-demo-v2-20260630063630@aethos-qa.dev |
| route-copilot | Route Coverage | Aethos Atlas | PASS | [screenshot](screenshots/route-copilot.png) | URL: https://aethos.ishirock.tech/app/copilot<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat Re |
| route-documents | Route Coverage | Documents | PASS | [screenshot](screenshots/route-documents.png) | URL: https://aethos.ishirock.tech/app/documents<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Documents Docum |
| route-inbox | Route Coverage | Inbox | PASS | [screenshot](screenshots/route-inbox.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Inbox 24 All En |
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
| 1-3-log-time | 1.3 Time entry | Atlas prompt | FAIL | [screenshot](screenshots/1-3-log-time-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/5 required signals; forbidden hits 1.<br>Missing required signals: /4\.5/4\.50/i, /Nexus/i, /CFO Advisory/board pack/cash flow/i, /time/hours/i, /logged/created/Inbox/approval/i<br>Invalid answer signals: No Atlas response captured. |
| 1-3a-delivery-data | 1.3A People and WIP | Atlas prompt | PASS | [screenshot](screenshots/1-3a-delivery-data-response.png) | Business-valid answer: matched 7/7 required signals. |
| 1-4-billing-run | 1.4 Mixed model invoice | Atlas prompt | PASS | [screenshot](screenshots/1-4-billing-run-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-5-revenue-recognition | 1.5 Revenue recognition | Atlas prompt | PASS | [screenshot](screenshots/1-5-revenue-recognition-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-6-capped-tax | 1.6 Capped tax engagement | Atlas prompt | FAIL | [screenshot](screenshots/1-6-capped-tax-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/6 required signals; forbidden hits 1.<br>Missing required signals: /Nexus/i, /Corporation Tax/Tax Return/FY2025/i, /18,?500/18500/i, /22,?000/22000/cap/i, /engagement/i, /Inbox/approval/created/i<br>Invalid answer signals: No Atlas response captured. |
| 1-7-o2c-readiness | 1.7 O2C controls | Atlas prompt | PASS | [screenshot](screenshots/1-7-o2c-readiness-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-collections-read | 1.7 Collections read pack | Atlas prompt | PASS | [screenshot](screenshots/1-7-collections-read-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-invoice-drilldown | 1.7 Invoice drilldown | Atlas prompt | FAIL | [screenshot](screenshots/1-7-invoice-drilldown-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/8 required signals; forbidden hits 1.<br>Missing required signals: /INV-1001/i, /due date/due/i, /aging/overdue/i, /balance/i, /paid/payment/i, /reminder/i, /blocker/blocked/i, /next action/recommend/i<br>Invalid answer signals: No Atlas response captured. |
| 1-7-draft-reminders | 1.7 Collections controlled write | Atlas prompt | PASS | [screenshot](screenshots/1-7-draft-reminders-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-1-retainer | 2.1 Monthly retainer billing | Atlas prompt | FAIL | [screenshot](screenshots/2-1-retainer-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/6 required signals; forbidden hits 1.<br>Missing required signals: /Brightwater/i, /retainer/i, /June 2026/June/i, /invoice/i, /tax/i, /Inbox/approval/i<br>Invalid answer signals: No Atlas response captured. |
| 2-2-milestone | 2.2 Annual accounts milestone | Atlas prompt | FAIL | [screenshot](screenshots/2-2-milestone-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/6 required signals; forbidden hits 1.<br>Missing required signals: /Brightwater/i, /Annual Accounts/FY2025/i, /milestone/i, /invoice/i, /tax/i, /approval/i<br>Invalid answer signals: No Atlas response captured. |
| 2-3-payroll | 2.3 Payroll billing | Atlas prompt | FAIL | [screenshot](screenshots/2-3-payroll-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/7 required signals; forbidden hits 1.<br>Missing required signals: /Brightwater/i, /payroll/i, /employee/i, /count/i, /invoice/billing/i, /total/i, /approval/i<br>Invalid answer signals: No Atlas response captured. |

## Prompt Transcript

## 1-1-engagement-letter - 1.1 Engagement letter onboarding

**Prompt**

```text
Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.
```

**Observed Atlas Response**

```text
 I have reviewed the engagement letter for Nexus Capital Partners LP.

Based on the document, I have prepared the client and engagement draft, including the billing terms (mixed: GBP 8,500 monthly retainer and GBP 42,000 fixed fee), the first project (Statutory Accounts - FY2025), and the associated rate card (CFO Advisory Partner: GBP 350/hr, Manager: GBP 240/hr, Associate: GBP 145/hr).

Because this involves creating new financial terms and engagement structures, the complete package has been routed to your Inbox for review and approval. Please check your Inbox to finalize these entries.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Extracts the uploaded Nexus engagement letter instead of asking the user to retype it. | Creates or prepares client, engagement, billing terms, rate card, and first project. | Routes risky or incomplete items to Inbox.
Matched required signals: /Nexus/i, /client/i, /engagement/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i, /Inbox|review|risk/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-1-engagement-letter-response.png](screenshots/1-1-engagement-letter-response.png)

## 1-2-engagement-structure - 1.2 Project structure

**Prompt**

```text
Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.
```

**Observed Atlas Response**

```text
 Nexus Capital Partners has two active engagements:

Nexus Capital Partners - Group Accounting & Advisory
This engagement is billing-ready.
Active Projects:
- Nexus CFO Advisory: T&M (Advisory hour at 350 GBP)
- Nexus Group Consolidation FY2025: Fixed Fee (Part of 48,000 GBP total fixed fee)
- Nexus Monthly Management Accounts: Monthly Retainer (9,000 GBP per month)

Nexus Corporation Tax Return FY2025
This engagement requires a setup review before billing can occur.
Active Projects: None
Billing Model: Capped T&M (18,500 GBP fixed fee, capped at 22,000 GBP with advisory hours at 280 GBP)
Missing before billing:
- Project or workstream setup
- Source documents (Engagement Letter)
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 4/4 required signals.
Criteria: Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.
Matched required signals: /Nexus/i, /project|workstream/i, /billing model|fixed|retainer|T&M|time and materials/i, /missing|ready|before billing|setup/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-2-engagement-structure-response.png](screenshots/1-2-engagement-structure-response.png)

## 1-3-log-time - 1.3 Time entry

**Prompt**

```text
Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling
```

**Observed Atlas Response**

```text

```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/5 required signals; forbidden hits 1.
Criteria: Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.
Matched required signals: none
Missing required signals: /4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /time|hours/i, /logged|created|Inbox|approval/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-3-log-time-response.png](screenshots/1-3-log-time-response.png)

## 1-3a-delivery-data - 1.3A People and WIP

**Prompt**

```text
Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.
```

**Observed Atlas Response**

```text
 Delivery and utilization context for Alice in June 2026:
- Approved hours 0; pending hours 24.0; utilization 0.00%; WIP 0.00; billable expenses 185.50.
- Invoice-ready billable expenses: 1 item(s), total 185.50.
Use the WIP and Project P&L reports for invoice-ready detail; I did not create an invoice.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Summarizes Alice Chen June delivery, utilization, WIP, expenses, and invoice readiness for Nexus.
Matched required signals: /Alice Chen|Alice/i, /June/i, /approved time|pending time|hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice|invoiced/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-3a-delivery-data-response.png](screenshots/1-3a-delivery-data-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-4-billing-run-response.png](screenshots/1-4-billing-run-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-5-revenue-recognition-response.png](screenshots/1-5-revenue-recognition-response.png)

## 1-6-capped-tax - 1.6 Capped tax engagement

**Prompt**

```text
Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun
```

**Observed Atlas Response**

```text

```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/6 required signals; forbidden hits 1.
Criteria: Creates or prepares Nexus capped tax engagement with fixed fee, cap, and Inbox approval if required.
Matched required signals: none
Missing required signals: /Nexus/i, /Corporation Tax|Tax Return|FY2025/i, /18,?500|18500/i, /22,?000|22000|cap/i, /engagement/i, /Inbox|approval|created/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-6-capped-tax-response.png](screenshots/1-6-capped-tax-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-7-o2c-readiness-response.png](screenshots/1-7-o2c-readiness-response.png)

## 1-7-collections-read - 1.7 Collections read pack

**Prompt**

```text
Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.
```

**Observed Atlas Response**

```text
 Collections readout:
- Totals: 2 open invoices; 1 overdue; balances {'GBP': '13500.0', 'USD': '0.0'}.
- Nexus Capital Partners LP invoice INV-1001: due 2026-06-19; aging 0_30; balance GBP 9000.0; payment status unpaid; reminder count 0; policy stage firm; blockers none; next action draft a firm collections reminder for Inbox review..
- Thornton Tech Solutions Ltd invoice INV-1003: due 2026-07-10; aging paid; balance USD 0.0; payment status paid; reminder count 0; policy stage none; blockers ['invoice_paid']; next action No collections action; the invoice is paid..
- Brightwater Manufacturing Ltd invoice INV-1002: due 2026-07-25; aging current; balance GBP 4500.0; payment status unpaid; reminder count 0; policy stage none; blockers ['policy_stage_not_reached']; next action No reminder yet; monitor until the invoice reaches the policy stage..
Any customer reminder email must be drafted to Inbox and approved before sending.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Shows collections customers with balances, invoices, due dates, aging, reminders, blockers, and next action without drafting.
Matched required signals: /customer/i, /balance/i, /invoice/i, /due date|due/i, /aging|overdue/i, /reminder/i, /blocker|blocked/i, /next action/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-7-collections-read-response.png](screenshots/1-7-collections-read-response.png)

## 1-7-invoice-drilldown - 1.7 Invoice drilldown

**Prompt**

```text
Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action.
```

**Observed Atlas Response**

```text

```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/8 required signals; forbidden hits 1.
Criteria: Reviews INV-1001 with due date, aging, balance, paid status, payment link, reminders, blockers, and next action.
Matched required signals: none
Missing required signals: /INV-1001/i, /due date|due/i, /aging|overdue/i, /balance/i, /paid|payment/i, /reminder/i, /blocker|blocked/i, /next action|recommend/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-7-invoice-drilldown-response.png](screenshots/1-7-invoice-drilldown-response.png)

## 1-7-draft-reminders - 1.7 Collections controlled write

**Prompt**

```text
Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.
```

**Observed Atlas Response**

```text
 Collections readout:
- Totals: 2 open invoices; 1 overdue; balances {'GBP': '13500.0', 'USD': '0.0'}.
- Nexus Capital Partners LP invoice INV-1001: due 2026-06-19; aging 0_30; balance GBP 9000.0; payment status unpaid; reminder count 0; policy stage firm; blockers none; next action draft a firm collections reminder for Inbox review..
- Thornton Tech Solutions Ltd invoice INV-1003: due 2026-07-10; aging paid; balance USD 0.0; payment status paid; reminder count 0; policy stage none; blockers ['invoice_paid']; next action No collections action; the invoice is paid..
- Brightwater Manufacturing Ltd invoice INV-1002: due 2026-07-25; aging current; balance GBP 4500.0; payment status unpaid; reminder count 0; policy stage none; blockers ['policy_stage_not_reached']; next action No reminder yet; monitor until the invoice reaches the policy stage..
Any customer reminder email must be drafted to Inbox and approved before sending.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Drafts customer-specific reminders for invoices over 30 days overdue and routes them to Inbox before sending.
Matched required signals: /reminder/i, /invoice/i, /30 days|overdue/i, /customer/i, /Inbox|approval/i, /draft/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/1-7-draft-reminders-response.png](screenshots/1-7-draft-reminders-response.png)

## 2-1-retainer - 2.1 Monthly retainer billing

**Prompt**

```text
Prepare Brightwater Manufacturing monthly retainer billing for June 2026. Show the draft invoice, any tax, and route it to Inbox before sending.
```

**Observed Atlas Response**

```text

```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/6 required signals; forbidden hits 1.
Criteria: Prepares Brightwater monthly retainer billing with draft invoice, tax, and Inbox routing.
Matched required signals: none
Missing required signals: /Brightwater/i, /retainer/i, /June 2026|June/i, /invoice/i, /tax/i, /Inbox|approval/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/2-1-retainer-response.png](screenshots/2-1-retainer-response.png)

## 2-2-milestone - 2.2 Annual accounts milestone

**Prompt**

```text
Prepare the Brightwater Annual Accounts FY2025 milestone invoice. Include the milestone basis, tax treatment, and approval path before sending.
```

**Observed Atlas Response**

```text

```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/6 required signals; forbidden hits 1.
Criteria: Prepares Brightwater Annual Accounts milestone invoice with basis, tax treatment, and approval path.
Matched required signals: none
Missing required signals: /Brightwater/i, /Annual Accounts|FY2025/i, /milestone/i, /invoice/i, /tax/i, /approval/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/2-2-milestone-response.png](screenshots/2-2-milestone-response.png)

## 2-3-payroll - 2.3 Payroll billing

**Prompt**

```text
Prepare Brightwater payroll billing for June 2026 based on active employee count. Show per-employee billing, invoice total, and any approval needed.
```

**Observed Atlas Response**

```text

```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/7 required signals; forbidden hits 1.
Criteria: Prepares Brightwater payroll billing from active employee count with total and approval need.
Matched required signals: none
Missing required signals: /Brightwater/i, /payroll/i, /employee/i, /count/i, /invoice|billing/i, /total/i, /approval/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T14-08-52-793Z/screenshots/2-3-payroll-response.png](screenshots/2-3-payroll-response.png)

## Browser Console Errors

- `Failed to load Atlas threads: TypeError: Failed to fetch
    at https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:2:3143
    at t.<computed> (https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:1:13713)
    at n.<anonymo`
- `Failed to load resource: net::ERR_HTTP2_PING_FAILED`
- `Atlas send error: network error`
- `Failed to load resource: net::ERR_HTTP2_PING_FAILED`
- `Atlas send error: network error`
- `Failed to load resource: net::ERR_HTTP2_PING_FAILED`
- `Atlas send error: network error`
- `Failed to load resource: net::ERR_CONNECTION_RESET`
- `Atlas send error: network error`
- `Failed to load resource: net::ERR_HTTP2_PING_FAILED`
- `Atlas send error: network error`

## Network Failures And 5xx Responses

- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status`
- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20`
- `net::ERR_HTTP2_PING_FAILED https://aethos.ishirock.tech/api/v1/chat/threads/11b09f71-a388-4869-b7b9-91ec346b626a/messages`
- `net::ERR_HTTP2_PING_FAILED https://aethos.ishirock.tech/api/v1/chat/threads/8045edaf-1766-482e-adaf-71c92440b0ad/messages`
- `net::ERR_HTTP2_PING_FAILED https://aethos.ishirock.tech/api/v1/chat/threads/aa65cf4c-d892-43c9-bb05-29f98a52c4cf/messages`
- `net::ERR_CONNECTION_RESET https://aethos.ishirock.tech/api/v1/chat/threads/4a2cac14-812a-4b8c-b246-00c06b14af32/messages`
- `net::ERR_HTTP2_PING_FAILED https://aethos.ishirock.tech/api/v1/chat/threads/bba0a74b-e170-4f94-b3cd-84bb0e91775a/messages`
