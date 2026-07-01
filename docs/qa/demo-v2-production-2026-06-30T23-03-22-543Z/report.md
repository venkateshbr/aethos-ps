# Demo Guide v2 Production Browser Validation

Run ID: `2026-06-30T23-03-22-543Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-07-01T00:28:13.412Z`

This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.

Summary: PASS 23, WARN 0, FAIL 8, SKIP 0

## Evidence Table

| ID | Section | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| auth | Authentication | Logged into https://aethos.ishirock.tech | PASS | [screenshot](screenshots/auth-login-filled.png) | Tenant: Meridian Demo v2 20260630063630<br>Tenant ID: a0267012-73a9-416c-bba2-81d86e2bbba4<br>User: prod-demo-v2-20260630063630@aethos-qa.dev |
| route-copilot | Route Coverage | Aethos Atlas | PASS | [screenshot](screenshots/route-copilot.png) | URL: https://aethos.ishirock.tech/app/copilot<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat Pr |
| route-documents | Route Coverage | Documents | PASS | [screenshot](screenshots/route-documents.png) | URL: https://aethos.ishirock.tech/app/documents<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Documents Docum |
| route-inbox | Route Coverage | Inbox | PASS | [screenshot](screenshots/route-inbox.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Inbox 43 All En |
| route-engagements | Route Coverage | Engagements | PASS | [screenshot](screenshots/route-engagements.png) | URL: https://aethos.ishirock.tech/app/engagements<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| route-projects | Route Coverage | Projects | PASS | [screenshot](screenshots/route-projects.png) | URL: https://aethos.ishirock.tech/app/projects<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| route-invoices | Route Coverage | Invoices | PASS | [screenshot](screenshots/route-invoices.png) | URL: https://aethos.ishirock.tech/app/invoices<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Invoices Review |
| route-clients | Route Coverage | Contacts | PASS | [screenshot](screenshots/route-clients.png) | URL: https://aethos.ishirock.tech/app/clients<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| route-expenses | Route Coverage | Expenses | PASS | [screenshot](screenshots/route-expenses.png) | URL: https://aethos.ishirock.tech/app/expenses<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Expenses Track  |
| route-bills | Route Coverage | Bills | PASS | [screenshot](screenshots/route-bills.png) | URL: https://aethos.ishirock.tech/app/bills<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Bills Manage ve |
| route-billing-runs | Route Coverage | Billing Runs / Pay Bills | PASS | [screenshot](screenshots/route-billing-runs.png) | URL: https://aethos.ishirock.tech/app/billing-runs<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Billing Run Bil |
| route-time | Route Coverage | Time | FAIL |  | URL: https://aethos.ishirock.tech/app/time<br>TimeoutError: page.goto: Timeout 60000ms exceeded.
Call log:
[2m  - navigating to "https://aethos.ishirock.tech/app/time", waiting until "domcontentloaded"[22m
 |
| route-approvals | Route Coverage | Approvals | FAIL |  | URL: https://aethos.ishirock.tech/app/approvals<br>TimeoutError: page.goto: Timeout 60000ms exceeded.
Call log:
[2m  - navigating to "https://aethos.ishirock.tech/app/approvals", waiting until "domcontentloaded"[22m
 |
| route-payments | Route Coverage | Payments | FAIL |  | URL: https://aethos.ishirock.tech/app/payments<br>Error: page.goto: net::ERR_TIMED_OUT at https://aethos.ishirock.tech/app/payments
Call log:
[2m  - navigating to "https://aethos.ishirock.tech/app/payments", waiting until "domcontentloaded"[22m
 |
| route-people | Route Coverage | People | PASS | [screenshot](screenshots/route-people.png) | URL: https://aethos.ishirock.tech/app/people<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| route-reports | Route Coverage | Reports | FAIL |  | URL: https://aethos.ishirock.tech/app/reports<br>TimeoutError: page.goto: Timeout 60000ms exceeded.
Call log:
[2m  - navigating to "https://aethos.ishirock.tech/app/reports", waiting until "domcontentloaded"[22m
 |
| route-journals | Route Coverage | Accounting / Journal Entries | FAIL |  | URL: https://aethos.ishirock.tech/app/accounting/journals<br>Error: page.goto: net::ERR_TIMED_OUT at https://aethos.ishirock.tech/app/accounting/journals
Call log:
[2m  - navigating to "https://aethos.ishirock.tech/app/accounting/journals", waiting until "domcontentloaded"[22m
 |
| route-settings | Route Coverage | Settings | PASS | [screenshot](screenshots/route-settings.png) | URL: https://aethos.ishirock.tech/app/settings<br>Body excerpt: Sign in Now in private beta · US · UK · SG · IN · AU Engagement to cash. Without the forms. Drop your engagement letter. Aethos extracts, proposes, and posts — you approve. GAAP do |
| route-timesheet | Route Coverage | Timesheet portal | FAIL |  | URL: https://timesheet.aethos.ishirock.tech<br>TimeoutError: page.goto: Timeout 60000ms exceeded.
Call log:
[2m  - navigating to "https://timesheet.aethos.ishirock.tech/", waiting until "domcontentloaded"[22m
 |
| 1-1-engagement-letter | 1.1 Engagement letter onboarding | Atlas prompt | FAIL | [screenshot](screenshots/1-1-engagement-letter-response.png) | Attachment banner before prompt: attach_file Attached: nexus_engagement_letter.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Expected response signals matched 0/1.<br>Business validation failed: matched 0/7 required signals; forbidden hits 1.<br>Missing required signals: /Nexus/i, /client/i, /engagement/i, /billing/fixed/retainer/T&M/time and materials/mixed/i, /rate card/rate/i, /project/i, /Inbox/review/risk/i<br>Invalid answer signals: No Atlas response captured. |
| 1-2-engagement-structure | 1.2 Project structure | Atlas prompt | PASS | [screenshot](screenshots/1-2-engagement-structure-response.png) | Business-valid answer: matched 4/4 required signals. |
| 1-3-log-time | 1.3 Time entry | Atlas prompt | PASS | [screenshot](screenshots/1-3-log-time-response.png) | Business-valid answer: matched 5/5 required signals. |
| 1-3a-delivery-data | 1.3A People and WIP | Atlas prompt | PASS | [screenshot](screenshots/1-3a-delivery-data-response.png) | Business-valid answer: matched 7/7 required signals. |
| 1-4-billing-run | 1.4 Mixed model invoice | Atlas prompt | PASS | [screenshot](screenshots/1-4-billing-run-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-5-revenue-recognition | 1.5 Revenue recognition | Atlas prompt | PASS | [screenshot](screenshots/1-5-revenue-recognition-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-6-capped-tax | 1.6 Capped tax engagement | Atlas prompt | PASS | [screenshot](screenshots/1-6-capped-tax-response.png) | Business-valid answer: matched 6/6 required signals. |
| 1-7-o2c-readiness | 1.7 O2C controls | Atlas prompt | PASS | [screenshot](screenshots/1-7-o2c-readiness-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-collections-read | 1.7 Collections read pack | Atlas prompt | PASS | [screenshot](screenshots/1-7-collections-read-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-invoice-drilldown | 1.7 Invoice drilldown | Atlas prompt | PASS | [screenshot](screenshots/1-7-invoice-drilldown-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-draft-reminders | 1.7 Collections controlled write | Atlas prompt | PASS | [screenshot](screenshots/1-7-draft-reminders-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-1-retainer | 2.1 Monthly retainer billing | Atlas prompt | FAIL | [screenshot](screenshots/2-1-retainer-failed.png) | Error: locator.click: Target page, context or browser has been closed |

## Prompt Transcript

## 1-1-engagement-letter - 1.1 Engagement letter onboarding

**Prompt**

```text
Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.
```

**Observed Atlas Response**

```text

```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/7 required signals; forbidden hits 1.
Criteria: Extracts the uploaded Nexus engagement letter instead of asking the user to retype it. | Creates or prepares client, engagement, billing terms, rate card, and first project. | Routes risky or incomplete items to Inbox.
Matched required signals: none
Missing required signals: /Nexus/i, /client/i, /engagement/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i, /Inbox|review|risk/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-1-engagement-letter-response.png](screenshots/1-1-engagement-letter-response.png)

## 1-2-engagement-structure - 1.2 Project structure

**Prompt**

```text
Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.
```

**Observed Atlas Response**

```text
 Nexus Capital Partners has two active engagements:

Nexus Capital Partners - Group Accounting & Advisory
This engagement is ready for billing and uses a mixed model:
- Nexus CFO Advisory: T&M (Advisory hour at GBP 350.00)
- Nexus Group Consolidation FY2025: Fixed Fee (Part of the GBP 48,000.00 total fixed fee)
- Nexus Monthly Management Accounts: Monthly Retainer (GBP 9,000.00 per month)

Nexus Corporation Tax Return FY2025
This engagement is not yet ready for billing. It uses a capped T&M model (Fixed fee of GBP 18,500.00 with a cap of GBP 22,000.00).
Missing items before billing:
- No active project or workstream defined
- Source document missing
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 4/4 required signals.
Criteria: Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.
Matched required signals: /Nexus/i, /project|workstream/i, /billing model|fixed|retainer|T&M|time and materials/i, /missing|ready|before billing|setup/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-2-engagement-structure-response.png](screenshots/1-2-engagement-structure-response.png)

## 1-3-log-time - 1.3 Time entry

**Prompt**

```text
Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling
```

**Observed Atlas Response**

```text
 Prepared the Nexus CFO Advisory time entry for review.
- Time: 4.5 hours today on Nexus CFO Advisory.
- Narrative: board pack review and cash flow modelling.
- Billing: billable advisory time; expected rate is the reviewed CFO Advisory rate-card rate.
- Status: logged/prepared for the authenticated employee if employee resolution is available; otherwise route the time-entry action to Inbox/manager approval for employee mapping.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 5/5 required signals.
Criteria: Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.
Matched required signals: /4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /time|hours/i, /logged|created|Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-3-log-time-response.png](screenshots/1-3-log-time-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-3a-delivery-data-response.png](screenshots/1-3a-delivery-data-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-4-billing-run-response.png](screenshots/1-4-billing-run-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-5-revenue-recognition-response.png](screenshots/1-5-revenue-recognition-response.png)

## 1-6-capped-tax - 1.6 Capped tax engagement

**Prompt**

```text
Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun
```

**Observed Atlas Response**

```text
 Prepared a Nexus Corporation Tax Return FY2025 engagement draft.
- Client: Nexus Capital Partners.
- Service: Corporation Tax Return FY2025.
- Billing: fixed fee GBP 18,500 with a cap at GBP 22,000 if advisory hours overrun.
- Control: capped-fee scope and advisory overrun risk require Inbox approval before the engagement is created/sent.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Creates or prepares Nexus capped tax engagement with fixed fee, cap, and Inbox approval if required.
Matched required signals: /Nexus/i, /Corporation Tax|Tax Return|FY2025/i, /18,?500|18500/i, /22,?000|22000|cap/i, /engagement/i, /Inbox|approval|created/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-6-capped-tax-response.png](screenshots/1-6-capped-tax-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-7-o2c-readiness-response.png](screenshots/1-7-o2c-readiness-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-7-collections-read-response.png](screenshots/1-7-collections-read-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-7-invoice-drilldown-response.png](screenshots/1-7-invoice-drilldown-response.png)

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/1-7-draft-reminders-response.png](screenshots/1-7-draft-reminders-response.png)

## 2-1-retainer - 2.1 Monthly retainer billing

**Prompt**

```text
Prepare Brightwater Manufacturing monthly retainer billing for June 2026. Show the draft invoice, any tax, and route it to Inbox before sending.
```

**Observed Atlas Response**

```text
(no response captured)
```

**Business Validation**

No business validation was recorded for this entry.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T23-03-22-543Z/screenshots/2-1-retainer-failed.png](screenshots/2-1-retainer-failed.png)

## Browser Console Errors

- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 401 ()`
- `Failed to load resource: the server responded with a status of 403 ()`
- `Failed to load resource: the server responded with a status of 403 ()`
- `Failed to load Atlas threads: Error: HTTP 403
    at n.<anonymous> (https://aethos.ishirock.tech/chunk-QX67KEZI.js:1:19984)
    at Generator.next (<anonymous>)
    at i (https://aethos.ishirock.tech/chunk-EMJ45C2U.js:1:7`
- `Failed to load resource: net::ERR_HTTP2_PING_FAILED`
- `Atlas send error: network error`

## Network Failures And 5xx Responses

- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20`
- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status`
- `net::ERR_ABORTED https://aethos.ishirock.tech/app/time`
- `net::ERR_ABORTED https://aethos.ishirock.tech/app/approvals`
- `net::ERR_TIMED_OUT https://aethos.ishirock.tech/app/payments`
- `net::ERR_ABORTED https://aethos.ishirock.tech/app/reports`
- `net::ERR_TIMED_OUT https://aethos.ishirock.tech/app/accounting/journals`
- `net::ERR_HTTP2_PING_FAILED https://aethos.ishirock.tech/api/v1/chat/threads/8f9d7020-0537-474b-ae75-b18171750210/messages`
