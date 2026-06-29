# Demo Guide v2 Production Browser Validation

Run ID: `2026-06-29T06-16-35-083Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-06-29T06:39:53.484Z`

This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.

Summary: PASS 53, WARN 0, FAIL 13, SKIP 0

Manual review adjustment: effective PASS 50, FAIL 16. The automated rubric
initially counted `1-6-capped-tax`, `5-6-reversal`, and
`7-5-config-telemetry` as PASS because they matched keywords, but manual review
found that the answers asked the user for information or said required platform
telemetry was not exposed. Treat those three as implementation gaps.

Additional stricter rerun note: `docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/`
is an interrupted partial rerun after tightening validation. It is not the
authoritative full run because Atlas stopped returning responses after the
first document prompt timed out, but it provides evidence for the document
upload recovery gap in #358.

## Follow-Up Issues

- [#358](https://github.com/venkateshbr/aethos-ps/issues/358) Atlas should read uploaded document extraction results before answering
- [#359](https://github.com/venkateshbr/aethos-ps/issues/359) Expose time-entry and resource delivery tools to Atlas/Hermes
- [#360](https://github.com/venkateshbr/aethos-ps/issues/360) Strengthen Atlas read-pack completeness for O2C, P2P, payroll, COSEC, and family office scenarios
- [#361](https://github.com/venkateshbr/aethos-ps/issues/361) Atlas accounting control answers need journal context, segregation checks, and decision audit trails
- [#362](https://github.com/venkateshbr/aethos-ps/issues/362) Provide operational health and observability read tools to Atlas
- [#363](https://github.com/venkateshbr/aethos-ps/issues/363) Atlas engagement creation/update prompts should use Aethos tools without asking for IDs

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
| 1-1-engagement-letter | 1.1 Engagement letter onboarding | Atlas prompt | FAIL | [screenshot](screenshots/1-1-engagement-letter-response.png) | Attachment banner before prompt: attach_file Attached: nexus_engagement_letter.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business validation failed: matched 7/7 required signals; forbidden hits 1.<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i |
| 1-2-engagement-structure | 1.2 Project structure | Atlas prompt | FAIL | [screenshot](screenshots/1-2-engagement-structure-response.png) | Business validation failed: matched 2/4 required signals; forbidden hits 0.<br>Missing required signals: /project/workstream/i, /missing/ready/before billing/setup/i |
| 1-3-log-time | 1.3 Time entry | Atlas prompt | FAIL | [screenshot](screenshots/1-3-log-time-response.png) | Business validation failed: matched 1/5 required signals; forbidden hits 1.<br>Missing required signals: /4\.5/4\.50/i, /Nexus/i, /CFO Advisory/board pack/cash flow/i, /logged/created/Inbox/approval/i<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i |
| 1-3a-delivery-data | 1.3A People and WIP | Atlas prompt | FAIL | [screenshot](screenshots/1-3a-delivery-data-response.png) | Business validation failed: matched 7/7 required signals; forbidden hits 2.<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i, /can you provide/can you confirm/do you want me to/i |
| 1-4-billing-run | 1.4 Mixed model invoice | Atlas prompt | PASS | [screenshot](screenshots/1-4-billing-run-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-5-revenue-recognition | 1.5 Revenue recognition | Atlas prompt | PASS | [screenshot](screenshots/1-5-revenue-recognition-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-6-capped-tax | 1.6 Capped tax engagement | Atlas prompt | PASS | [screenshot](screenshots/1-6-capped-tax-response.png) | Business-valid answer: matched 6/6 required signals. |
| 1-7-o2c-readiness | 1.7 O2C controls | Atlas prompt | PASS | [screenshot](screenshots/1-7-o2c-readiness-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-collections-read | 1.7 Collections read pack | Atlas prompt | FAIL | [screenshot](screenshots/1-7-collections-read-response.png) | Business validation failed: matched 5/8 required signals; forbidden hits 0.<br>Missing required signals: /reminder/i, /blocker/blocked/i, /next action/i |
| 1-7-invoice-drilldown | 1.7 Invoice drilldown | Atlas prompt | PASS | [screenshot](screenshots/1-7-invoice-drilldown-response.png) | Business-valid answer: matched 8/8 required signals. |
| 1-7-draft-reminders | 1.7 Collections controlled write | Atlas prompt | PASS | [screenshot](screenshots/1-7-draft-reminders-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-1-retainer | 2.1 Monthly retainer billing | Atlas prompt | FAIL | [screenshot](screenshots/2-1-retainer-response.png) | Business validation failed: matched 5/6 required signals; forbidden hits 0.<br>Missing required signals: /retainer/i |
| 2-2-milestone | 2.2 Annual accounts milestone | Atlas prompt | PASS | [screenshot](screenshots/2-2-milestone-response.png) | Business-valid answer: matched 6/6 required signals. |
| 2-3-payroll | 2.3 Payroll billing | Atlas prompt | FAIL | [screenshot](screenshots/2-3-payroll-response.png) | Business validation failed: matched 7/7 required signals; forbidden hits 1.<br>Invalid answer signals: /couldn'?t locate/not showing up/not found/no .* on file/need .* from you/i |
| 2-4-vendor-invoice | 2.4 Vendor invoice intake | Atlas prompt | PASS | [screenshot](screenshots/2-4-vendor-invoice-response.png) | Attachment banner before prompt: attach_file Attached: brightwater_subcontractor_invoice.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business-valid answer: matched 7/8 required signals.<br>Missing required signals: /project/i |
| 2-4-payment-risk-read | 2.4 P2P read pack | Atlas prompt | PASS | [screenshot](screenshots/2-4-payment-risk-read-response.png) | Business-valid answer: matched 9/9 required signals. |
| 2-4-single-bill | 2.4 Single bill drilldown | Atlas prompt | PASS | [screenshot](screenshots/2-4-single-bill-response.png) | Business-valid answer: matched 9/9 required signals. |
| 2-5-bill-pay | 2.5 Payment controls | Atlas prompt | PASS | [screenshot](screenshots/2-5-bill-pay-response.png) | Business-valid answer: matched 6/7 required signals.<br>Missing required signals: /rationale/reason/i |
| 2-5-payment-packet | 2.5 Payment approval packet | Atlas prompt | PASS | [screenshot](screenshots/2-5-payment-packet-response.png) | Business-valid answer: matched 7/7 required signals. |
| 3-1-family-office | 3.1 Family office structure | Atlas prompt | FAIL | [screenshot](screenshots/3-1-family-office-response.png) | Business validation failed: matched 6/7 required signals; forbidden hits 1.<br>Missing required signals: /project/i<br>Invalid answer signals: /couldn'?t locate/not showing up/not found/no .* on file/need .* from you/i |
| 3-2-scope-creep | 3.2 Scope creep risk | Atlas prompt | PASS | [screenshot](screenshots/3-2-scope-creep-response.png) | Business-valid answer: matched 7/7 required signals. |
| 3-3-sgd-journal | 3.3 Multi-currency trust accounts | Atlas prompt | PASS | [screenshot](screenshots/3-3-sgd-journal-response.png) | Business-valid answer: matched 8/8 required signals. |
| 3-4-cosec-reminders | 3.4 COSEC reminders | Atlas prompt | FAIL | [screenshot](screenshots/3-4-cosec-reminders-response.png) | Business validation failed: matched 5/7 required signals; forbidden hits 0.<br>Missing required signals: /evidence/missing/i, /billing impact/billing/i |
| 4-1-usd-engagement | 4.1 USD-billed engagement | Atlas prompt | PASS | [screenshot](screenshots/4-1-usd-engagement-response.png) | Business-valid answer: matched 7/8 required signals.<br>Missing required signals: /GBP/i |
| 4-2-series-a | 4.2 Series A milestone | Atlas prompt | PASS | [screenshot](screenshots/4-2-series-a-response.png) | Business-valid answer: matched 6/6 required signals. |
| 4-3-cosec-instruction | 4.3 COSEC instruction | Atlas prompt | FAIL | [screenshot](screenshots/4-3-cosec-instruction-response.png) | Attachment banner before prompt: attach_file Attached: thornton_cosec_instruction.pdf - add instructions and send to process. Documents<br>Attachment did not start extraction before prompt submission.<br>Business validation failed: matched 6/7 required signals; forbidden hits 1.<br>Missing required signals: /Thornton/i<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i |
| 5-1-close-readiness | 5.1 Pre-close checklist | Atlas prompt | PASS | [screenshot](screenshots/5-1-close-readiness-response.png) | Business-valid answer: matched 8/8 required signals. |
| 5-2-period-lock | 5.2 Period lock | Atlas prompt | PASS | [screenshot](screenshots/5-2-period-lock-response.png) | Business-valid answer: matched 6/6 required signals. |
| 5-3-trial-balance | 5.3 Trial Balance | Atlas prompt | PASS | [screenshot](screenshots/5-3-trial-balance-response.png) | Business-valid answer: matched 7/7 required signals. |
| 5-4-management-reporting | 5.4 Management reporting | Atlas prompt | PASS | [screenshot](screenshots/5-4-management-reporting-response.png) | Business-valid answer: matched 5/5 required signals. |
| 5-5-management-pack | 5.5 R2R management pack | Atlas prompt | PASS | [screenshot](screenshots/5-5-management-pack-response.png) | Business-valid answer: matched 9/10 required signals.<br>Missing required signals: /May 2026/i |
| 5-5-management-drilldown | 5.5 R2R blocker drilldown | Atlas prompt | PASS | [screenshot](screenshots/5-5-management-drilldown-response.png) | Business-valid answer: matched 5/5 required signals. |
| 5-5-statement-package | 5.5 Financial statement package | Atlas prompt | PASS | [screenshot](screenshots/5-5-statement-package-response.png) | Business-valid answer: matched 8/8 required signals. |
| 5-5-year-end | 5.5 Year-end close | Atlas prompt | PASS | [screenshot](screenshots/5-5-year-end-response.png) | Business-valid answer: matched 7/8 required signals.<br>Missing required signals: /P&L/profit and loss/i |
| 5-6-manual-journal | 5.6 Manual journal lifecycle | Atlas prompt | FAIL | [screenshot](screenshots/5-6-manual-journal-response.png) | Business validation failed: matched 7/8 required signals; forbidden hits 1.<br>Missing required signals: /approver.*submitter/different from submitter/segregation/i<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i |
| 5-6-reversal | 5.6 Manual journal reversal | Atlas prompt | PASS | [screenshot](screenshots/5-6-reversal-response.png) | Business-valid answer: matched 6/7 required signals.<br>Missing required signals: /new journal/not edit/rather than editing/i |
| 6-1-finance-ops-check | 6.1 Finance Ops Manager | Atlas prompt | PASS | [screenshot](screenshots/6-1-finance-ops-check-response.png) | Business-valid answer: matched 7/7 required signals. |
| 6-1-action-plan | 6.1 Finance Ops action plan | Atlas prompt | PASS | [screenshot](screenshots/6-1-action-plan-response.png) | Business-valid answer: matched 6/6 required signals. |
| 6-2-scheduled-control-room | 6.2 Scheduled Finance Ops Manager | Atlas prompt | PASS | [screenshot](screenshots/6-2-scheduled-control-room-response.png) | Business-valid answer: matched 6/6 required signals. |
| 7-1-approval-controls | 7.1 Approval policy and personas | Atlas prompt | PASS | [screenshot](screenshots/7-1-approval-controls-response.png) | Business-valid answer: matched 7/7 required signals. |
| 7-2-decision-trail | 7.2 Decision trail | Atlas prompt | FAIL | [screenshot](screenshots/7-2-decision-trail-response.png) | Business validation failed: matched 4/6 required signals; forbidden hits 0.<br>Missing required signals: /timestamp/time/i, /before\/after/before and after/review summary/i |
| 7-3-operational-health | 7.3 Operational Health | Atlas prompt | FAIL | [screenshot](screenshots/7-3-operational-health-response.png) | Business validation failed: matched 6/6 required signals; forbidden hits 1.<br>Invalid answer signals: /\bI (?:do not/don't) (?:have/see/find/locate/know/have direct access)\b/i |
| 7-4-documents-audit | 7.4 Documents and source evidence | Atlas prompt | PASS | [screenshot](screenshots/7-4-documents-audit-response.png) | Business-valid answer: matched 7/8 required signals.<br>Missing required signals: /journal/i |
| 7-5-config-telemetry | 7.5 Configuration and telemetry | Atlas prompt | PASS | [screenshot](screenshots/7-5-config-telemetry-response.png) | Business-valid answer: matched 7/7 required signals. |
| route-inbox-after-prompts | Route Coverage | Inbox after Atlas prompts | PASS | [screenshot](screenshots/route-inbox-after-prompts.png) | URL: https://aethos.ishirock.tech/app/inbox<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Inbox 13 All En |
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
 Perfect. I can see the Nexus engagement letter extraction is already queued in Inbox as a high-priority item (ID: 111be2f8-58be-4ffc-8838-cbc0ea60fc6a) awaiting manager review. The system has extracted the document and created a review task.

However, I don't have direct read access to the detailed extracted content from that Inbox item. To proceed properly, I need to work with the engagement data that was extracted. The engagement letter attachment shows an Inbox review already in progress.

Here's what I recommend:

1. **Review the Inbox item first** — The Nexus engagement letter extraction is waiting for your review at high priority. This extraction has already identified the client, engagement terms, and risks that need approval before I create the records.

2. **Once approved in Inbox**, I'll immediately create:
   - New client (if not already in system)
   - Engagement record with billing terms and rate card
   - First project/work item

The key reason to route through Inbox first is that engagement letters carry material risk: new client master data, billing terms, rate assumptions, and engagement scope all affect downstream invoicing and revenue recognition. Your approval locks the source document as audit evidence.

Would you like me to pull the details that are visible in the Inbox review task so you can assess them, or do you prefer to review it directly in Aethos first? Once you approve it, I can execute the full setup immediately.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 7/7 required signals; forbidden hits 1.
Criteria: Extracts the uploaded Nexus engagement letter instead of asking the user to retype it. | Creates or prepares client, engagement, billing terms, rate card, and first project. | Routes risky or incomplete items to Inbox.
Matched required signals: /Nexus/i, /client/i, /engagement/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i, /Inbox|review|risk/i
Missing required signals: none
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-1-engagement-letter-response.png](screenshots/1-1-engagement-letter-response.png)

## 1-2-engagement-structure - 1.2 Project structure

**Prompt**

```text
Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.
```

**Observed Atlas Response**

```text
 I found Nexus Capital Partners LP in the records. They have two active engagements:

**Nexus Capital Partners LP - Engagement Structure**

1. **Nexus Capital Partners - Group Accounting & Advisory** (ENG-0003)
   - Billing Model: Mixed
   - Value: GBP 156,000
   - Description: Mixed fixed-fee consolidation, monthly management accounts retainer, and CFO advisory T&M
   - Service Line: Accounting
   - Period: Jan 1 - Dec 31, 2026

2. **Nexus Corporation Tax Return FY2025** (ENG-0004)
   - Billing Model: Capped T&M (time and materials with cap)
   - Value: GBP 22,000
   - Description: Fixed-fee corporation tax return with advisory overrun capped
   - Service Line: Tax
   - Period: Jan 1 - Dec 31, 2026

**Total Contract Value: GBP 178,000**

I'm noting that both engagements show `billing_terms: null` and `source_document_id: null`. This typically means the engagement letter or billing schedule documentation hasn't been linked yet. Would you like me to check the current work-in-progress status or collections readiness for these engagements to see what's outstanding before invoicing?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 2/4 required signals; forbidden hits 0.
Criteria: Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.
Matched required signals: /Nexus/i, /billing model|fixed|retainer|T&M|time and materials/i
Missing required signals: /project|workstream/i, /missing|ready|before billing|setup/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-2-engagement-structure-response.png](screenshots/1-2-engagement-structure-response.png)

## 1-3-log-time - 1.3 Time entry

**Prompt**

```text
Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling
```

**Observed Atlas Response**

```text
 I don't have a time-logging tool available in my current Aethos toolkit. The tools I have access to cover finance operations (invoicing, payments, close procedures, collections) and engagement management, but not direct timesheet or hours entry.

To log your time, you'll likely need to:

1. Use your firm's timesheet system directly (if it's separate from Aethos)
2. Check if there's an Aethos portal or interface for time entry that I should route this through
3. Let me know the correct workflow, and I can help you set it up

Could you tell me which system you normally use to log project hours, or if this should be tracked within Aethos through a specific process?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 1/5 required signals; forbidden hits 1.
Criteria: Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.
Matched required signals: /time|hours/i
Missing required signals: /4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /logged|created|Inbox|approval/i
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-3-log-time-response.png](screenshots/1-3-log-time-response.png)

## 1-3a-delivery-data - 1.3A People and WIP

**Prompt**

```text
Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.
```

**Observed Atlas Response**

```text
 The data returned is tenant-wide, not specific to Alice Chen. Let me search for Alice Chen's time entries, approvals, and deliverables in June using a more targeted approach.

I need to clarify: the tools I have access to show portfolio-wide data rather than individual resource time entries. Based on what I've retrieved, here's what I can see about Nexus-related work in the system:

**Nexus Engagements Active:**
- Nexus CFO Advisory (T&M) — 9.0 unbilled hours at GBP 350/hr = GBP 3,150 WIP
- Nexus Group Consolidation FY2025 (no current WIP)
- Nexus Monthly Management Accounts (no current WIP)

**Nexus Invoice Status:**
- One invoice (INV-1001) issued 20 May, due 19 June: GBP 9,000 overdue by 10 days (unpaid)

**Ready to Invoice for Nexus:**
The 9 hours in CFO Advisory WIP can be billed once Alice's time entries are approved.

However, I don't have granular visibility into Alice Chen's individual time entries, approval status, expense claims, or utilization metrics through the current tools. To show her complete June delivery data, I would typically need:
- Her individual time logs with approval status (approved/pending)
- Billable expense claims for June
- Utilization rate for the month
- Which specific entries are bound to invoiceable engagements

Can you confirm: do you have access to a time tracking or resource management system where Alice Chen's individual June entries live, or should I draft an invoice for the 9 pending CFO Advisory hours to move that to billing?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 7/7 required signals; forbidden hits 2.
Criteria: Summarizes Alice Chen June delivery, utilization, WIP, expenses, and invoice readiness for Nexus.
Matched required signals: /Alice Chen|Alice/i, /June/i, /approved time|pending time|hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice|invoiced/i
Missing required signals: none
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i, /can you provide|can you confirm|do you want me to/i

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-3a-delivery-data-response.png](screenshots/1-3a-delivery-data-response.png)

## 1-4-billing-run - 1.4 Mixed model invoice

**Prompt**

```text
Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending.
```

**Observed Atlas Response**

```text
 Perfect. The June 2026 invoice for Nexus Capital Partners has been drafted and routed to Inbox for review. Here's what's been prepared:

**Nexus Capital Partners LP - June 2026 Billing Run**

The draft invoice includes:
- Monthly retainer: Nexus Capital Partners - Group Accounting & Advisory (June allocation)
- T&M advisory hours: Nexus CFO Advisory work (9.0 hours @ GBP 350/hr = GBP 3,150)
- Any approved expenses from the period
- Fixed fees and other billing components per the engagement terms

The invoice has been created as a draft and routed to Aethos Inbox under task ID 588221a3-f914-45a3-9828-84efce9566e4 for policy review and approval. Once reviewed and approved in Inbox, it will be ready for sending to the customer. The draft captures all four billing components you requested: fixed fees, monthly retainer, T&M advisory hours, and approved expenses.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Prepares Nexus June billing run with fixed fee, retainer, T&M hours, expenses, draft invoice lines, and Inbox routing.
Matched required signals: /Nexus/i, /June 2026|June/i, /fixed fee/i, /retainer/i, /T&M|time and materials|hour/i, /expense/i, /invoice line|draft invoice/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-4-billing-run-response.png](screenshots/1-4-billing-run-response.png)

## 1-5-revenue-recognition - 1.5 Revenue recognition

**Prompt**

```text
Explain how Nexus June revenue is recognized across fixed-fee milestone, retainer, T&M advisory WIP, and expenses. Tie the explanation to invoice-backed journals and Project P&L.
```

**Observed Atlas Response**

```text
 Excellent. Now I have the picture. Let me walk you through how Nexus Capital Partners LP's June revenue recognition works across its mixed billing model.

**NEXUS ENGAGEMENT STRUCTURE (ENG-0003)**
Nexus Capital Partners - Group Accounting & Advisory is a 156,000 GBP mixed-model engagement split into three service lines:
1. Fixed-fee group consolidation
2. Monthly management accounts retainer
3. CFO advisory time-and-materials

**JUNE REVENUE RECOGNITION FLOW**

**1. FIXED-FEE CONSOLIDATION (Recognition: Contract completion / monthly pro-rata)**
The fixed-fee component recognizes revenue when the consolidation milestone is delivered. If billed monthly on a pro-rata schedule (e.g., 12,000 GBP per month), June revenue records as earned when the June consolidation deliverable is complete and signed off. This typically maps to a fixed revenue line: Dr. AR, Cr. Revenue (Fixed-Fee Consolidation).

**2. RETAINER - MONTHLY MANAGEMENT ACCOUNTS (Recognition: Monthly billing)**
The retainer is earned monthly on a straight-line basis. Each month (June included), revenue is recognized at 1/12th of the annual amount. Assuming the retainer is billed, then the invoice backs a journal entry: Dr. AR, Cr. Revenue (Retainer). The WIP for Monthly Management Accounts shows 0.00 because the work is current and billed.

**3. T&M ADVISORY - CFO ADVISORY (Recognition: Time accrual + WIP)**
This is where unbilled hours pile up as work-in-progress. Currently, Nexus CFO Advisory shows 9.0 unbilled hours at 350/hour = 3,150 GBP in WIP. These hours have been logged but not yet invoiced. Revenue recognition here follows accrual accounting: as the hours are worked and logged in June, they are recorded as Dr. WIP Asset, Cr. Revenue (T&M Advisory). When those hours are later invoiced, the journal reverses to Dr. AR (invoice), Cr. WIP (relief).

**ACTUAL JUNE INVOICE (INV-1001)**
The system shows one invoice issued to Nexus on 2026-05-20 for 9,000 GBP:
- Due date: 2026-06-19
- Current status: Overdue (10 days past due as of June 29)
- Balance: 9,000 GBP unpaid

This invoice backs the actual billing cycle. The 9,000 GBP is likely composed of:
- Fixed consolidation June pro-rata
- Retainer June installment
- Potentially some previously accrued T&M hours billed in arrears

**PROJECT P&L LINKAGE**
The Project P&L tie-down works as:
- Revenue side: Sum of fixed-fee monthly allocations + retainer monthly allocations + T&M time-and-materials plus any hour-to-invoice conversion
- Expense side: Allocated staff costs, direct expenses (subcontractors, software, etc.) tagged to Nexus CFO Advisory, Nexus Group Consolidation, Nexus Monthly Management Accounts
- Margin: Revenue less expenses = contribution by project and billing model
- Gross margin variance analysis compares actual time-loaded costs vs. charged rates

**AR AGING & CASH IMPACT**
The 9,000 GBP invoice is now 10 days overdue. This creates a cash-flow gap: revenue was recognized (and likely booked to P&L) in May when the invoice iss
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Explains Nexus revenue recognition across milestone/fixed fee, retainer, T&M WIP, expenses, journals, and Project P&L.
Matched required signals: /Nexus/i, /revenue/i, /fixed fee|milestone/i, /retainer/i, /T&M|WIP|time and materials/i, /expense/i, /journal/i, /Project P&L|project/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-5-revenue-recognition-response.png](screenshots/1-5-revenue-recognition-response.png)

## 1-6-capped-tax - 1.6 Capped tax engagement

**Prompt**

```text
Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun
```

**Observed Atlas Response**

```text
 I'm hitting validation errors in the Aethos engagement tools. The available tools I have are designed for invoicing and collections workflows rather than direct engagement creation.

To properly set up this engagement for Nexus with the specifics you've outlined (fixed fee £18,500, capped at £22,000), I need more information:

1. **Client ID** — What is Nexus's client ID in Aethos?
2. **Service class** — Should this be classified as Tax or Advisory?
3. **Engagement ID** — Does one exist already, or should Aethos auto-generate it?
4. **Billing model** — Confirm this is fixed fee with a cap, not hourly?
5. **Period** — When does FY2025 close (e.g., 31 December 2025)?

Once you provide the client ID, I can route this through Aethos Inbox as an engagement review for approval, which will ensure the billing cap and advisory hour terms are recorded correctly. This keeps the engagement in the audit evidence system and triggers any necessary control reviews.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Creates or prepares Nexus capped tax engagement with fixed fee, cap, and Inbox approval if required.
Matched required signals: /Nexus/i, /Corporation Tax|Tax Return|FY2025/i, /18,?500|18500/i, /22,?000|22000|cap/i, /engagement/i, /Inbox|approval|created/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-6-capped-tax-response.png](screenshots/1-6-capped-tax-response.png)

## 1-7-o2c-readiness - 1.7 O2C controls

**Prompt**

```text
Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval.
```

**Observed Atlas Response**

```text
 Here's your Nexus Order-to-Cash readiness review for June 2026:

## Executive Summary

Nexus has partial O2C readiness with critical items pending action:

**Status: READINESS BLOCKED** — Engagement onboarding review is open and must be approved before invoice setup can proceed. One overdue invoice requires collection follow-up.

---

## Key Findings

**WIP (Work in Progress)**
Nexus CFO Advisory: 9 unbilled hours at 350/hr = 3150 GBP pending invoice
Nexus Group Consolidation and Monthly Management Accounts: Fully billed, no WIP
Ready to invoice once engagement letter and service mapping are approved.

**Invoices & Collections**
    One invoice issued (INV-1001):
    - Amount: 9,000 GBP, issued 20 May, due 19 June
    - Status: OVERDUE by 10 days (0-30 day bucket)
    - Payment: Unpaid, public invoice link available
    - Policy Stage: Firm (escalated collections reminder recommended)
    - No reminders sent yet
    - Blocker: None; ready for collections action

**Public Invoice Link**
Public invoice available for INV-1001; payment link shows "public_invoice_only" state (no direct payment acceptance). Customer can view but not pay directly online yet.

**Approval Queue (Inbox)**
Four high-risk items awaiting your approval:
    1. Nexus engagement letter extraction review (Draft) — blocks service setup
    2. Copilot-drafted invoice (57,185.50 GBP, Money-in) — requires manager approval
    3. June month-end close package (Accounting) — blocking close
    4. Vendor payment batch (3,389 GBP, Money-out) — unrelated to Nexus

**Service Catalogue, Rate Card & Tax**
The engagement review in Inbox indicates these are being extracted from Nexus's engagement letter. Cannot confirm mapping or tax setup until that draft is approved.

---

## Recommended Next Steps

1. Review the Nexus engagement letter draft in Inbox immediately — this unblocks service mapping and rate card configuration.
2. Once approved, the system will auto-link service catalogue to rate cards.
3. Address the overdue INV-1001 with a firm collections reminder (policy stage recommends escalation after 10 days).
4. Approve the pending 57,185.50 GBP invoice draft to activate it.

Would you like me to draft a firm collections reminder for INV-1001 for your Inbox review, or proceed with approving the engagement letter and invoice drafts?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Reviews Nexus O2C readiness across service catalogue, rate card, tax, invoices, payment links, WIP, and collections approvals.
Matched required signals: /Nexus/i, /service catalogue|catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link|public invoice/i, /WIP/i, /collections/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-7-o2c-readiness-response.png](screenshots/1-7-o2c-readiness-response.png)

## 1-7-collections-read - 1.7 Collections read pack

**Prompt**

```text
Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.
```

**Observed Atlas Response**

```text
 The collections data shows no overdue invoices at this time. I queried for all overdue invoices and got back an empty result set — zero customer count, zero invoice count, and zero overdue balance.

This means either:

1. Your customers are current on all payments.
2. There are no invoices issued yet.
3. All outstanding invoices are still within their payment terms.

Would you like me to:

- Check for invoices approaching due date (not yet overdue)?
- Look at your overall accounts receivable aging buckets to see if there are any aging trends?
- Review customer collections and invoice status for a specific customer or invoice?

Let me know what you'd like to investigate.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 5/8 required signals; forbidden hits 0.
Criteria: Shows collections customers with balances, invoices, due dates, aging, reminders, blockers, and next action without drafting.
Matched required signals: /customer/i, /balance/i, /invoice/i, /due date|due/i, /aging|overdue/i
Missing required signals: /reminder/i, /blocker|blocked/i, /next action/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-7-collections-read-response.png](screenshots/1-7-collections-read-response.png)

## 1-7-invoice-drilldown - 1.7 Invoice drilldown

**Prompt**

```text
Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action.
```

**Observed Atlas Response**

```text
 Here's the invoice review for INV-1001:

INVOICE DETAILS
Invoice Number: INV-1001
Customer: Nexus Capital Partners LP
Issue Date: 2026-05-20
Due Date: 2026-06-19
Status: Sent

PAYMENT STATE
Total Amount: GBP 9,000.00
Paid Amount: GBP 0
Balance Due: GBP 9,000.00
Payment Status: Unpaid

AGING
Days Overdue: 10 days
Aging Bucket: 0-30 days
Invoice State: Overdue

PUBLIC & PAYMENT ACCESS
Public Invoice Available: Yes
Payment Link State: Public invoice only (no direct payment link configured)

REMINDER HISTORY
Reminders Sent: 0
Last Reminder: None
Last Tone: None

COLLECTIONS POLICY STAGE
Stage: Firm

BLOCKERS
No blockers detected. Invoice is ready for collection action.

RECOMMENDED NEXT ACTION
Draft a firm collections reminder for Inbox review. This would be the first formal reminder to Nexus Capital Partners LP regarding the outstanding balance.

The invoice is cleanly overdue by 10 days with no payment received. There are no technical blockers, and the customer has already received the initial invoice. Moving to the firm reminder stage is the next appropriate step in your collections process.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Reviews INV-1001 with due date, aging, balance, paid status, payment link, reminders, blockers, and next action.
Matched required signals: /INV-1001/i, /due date|due/i, /aging|overdue/i, /balance/i, /paid|payment/i, /reminder/i, /blocker|blocked/i, /next action|recommend/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-7-invoice-drilldown-response.png](screenshots/1-7-invoice-drilldown-response.png)

## 1-7-draft-reminders - 1.7 Collections controlled write

**Prompt**

```text
Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.
```

**Observed Atlas Response**

```text
 The collections data shows no overdue invoices at the moment. There are currently zero invoices overdue in the system, so there are no 30+ day overdue invoices to draft reminders for.

To summarize:
- I queried the collections system for overdue invoices
- The query returned zero open overdue invoices and zero customers with overdue balances
- There are no reminders to draft at this time

If overdue invoices appear in the future, the workflow would be:
1. Pull overdue invoices from the collections pack (filtered by 30+ days overdue)
2. Generate customer-specific reminder copy tailored to each account
3. Route all reminder emails to Aethos Inbox for review and approval before sending

Would you like me to set up a recurring collections review or monitor this in the future?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Drafts customer-specific reminders for invoices over 30 days overdue and routes them to Inbox before sending.
Matched required signals: /reminder/i, /invoice/i, /30 days|overdue/i, /customer/i, /Inbox|approval/i, /draft/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/1-7-draft-reminders-response.png](screenshots/1-7-draft-reminders-response.png)

## 2-1-retainer - 2.1 Monthly retainer billing

**Prompt**

```text
Prepare Brightwater Manufacturing monthly retainer billing for June 2026. Show the draft invoice, any tax, and route it to Inbox before sending.
```

**Observed Atlas Response**

```text
 Perfect. Here's the summary of what I've prepared for your June 2026 billing:

**Draft Invoice for Brightwater Manufacturing Ltd**

Invoice Number: INV-1002
Period: June 1–30, 2026
Issue Date: June 25, 2026
Due Date: July 25, 2026

Amount: 4,500.00 GBP
Tax: Included in total (no separate tax line shown in current record)
Total Due: 4,500.00 GBP

Current Status: Unpaid
Aging Bucket: Current (not yet overdue)
Payment Notes: Public invoice link available for customer payment

**Inbox Status**

The invoice draft has been routed to Aethos Inbox for review before sending to the customer. This is the standard workflow for all customer invoices. Once the Inbox reviewer approves, the invoice will be ready to send or can be sent immediately depending on your approval process.

The invoice is currently held in draft review stage. No collections action is needed at this time since it hasn't reached the payment policy trigger stage yet.

Is there anything you'd like me to adjust before the invoice is approved and sent to Brightwater Manufacturing?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 5/6 required signals; forbidden hits 0.
Criteria: Prepares Brightwater monthly retainer billing with draft invoice, tax, and Inbox routing.
Matched required signals: /Brightwater/i, /June 2026|June/i, /invoice/i, /tax/i, /Inbox|approval/i
Missing required signals: /retainer/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/2-1-retainer-response.png](screenshots/2-1-retainer-response.png)

## 2-2-milestone - 2.2 Annual accounts milestone

**Prompt**

```text
Prepare the Brightwater Annual Accounts FY2025 milestone invoice. Include the milestone basis, tax treatment, and approval path before sending.
```

**Observed Atlas Response**

```text
 Based on the Aethos data, here's the summary for the Brightwater Annual Accounts FY2025 milestone invoice:

**MILESTONE ENGAGEMENT DETAILS**
- Engagement: Brightwater - Annual Statutory Accounts + CT600 FY2025 (ENG-0006)
- Client: Brightwater Manufacturing Ltd
- Billing Arrangement: Milestone-based
- Total engagement value: GBP 28,000
- Work-in-progress tracked: 16 unbilled hours at GBP 350/hour (GBP 5,600 WIP value)

**MILESTONE BASIS**
This is a fixed-fee milestone engagement for preparing the FY2025 statutory accounts and corporation tax return (CT600). Invoicing triggers on completion of defined milestones rather than time tracking. The service line is tax work for a UK manufacturing client.

**TAX TREATMENT**
- Currency: GBP (Sterling)
- Likely VAT scope: Standard-rated professional services (20% VAT applies unless the client is VAT-exempt or reverse-charged)
- This is advisory/outsourced accounting services, typically subject to UK VAT

**APPROVAL PATH**
Per policy, customer invoices require Manager-or-higher review before finalising. The approval workflow is:
1. Draft invoice prepared and routed to Aethos Inbox
2. Manager reviews milestone basis, amount, and tax treatment
3. Upon approval, invoice is generated
4. AR Lead can then prepare for sending to customer

**NEXT STEPS TO COMPLETE THIS INVOICE**
The system indicates no invoiceable lines were found. To proceed, you need to:
1. Record the approved billable work or milestone completion in the engagement (either time entries, expense items, or milestone billing terms)
2. Once invoiceable lines exist, I can draft the invoice through Inbox for Manager approval
3. After approval, the invoice will be ready to send

Would you like me to proceed once you've confirmed the milestone has been reached and the work is ready to bill, or do you need to add billing terms to the engagement first?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Prepares Brightwater Annual Accounts milestone invoice with basis, tax treatment, and approval path.
Matched required signals: /Brightwater/i, /Annual Accounts|FY2025/i, /milestone/i, /invoice/i, /tax/i, /approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/2-2-milestone-response.png](screenshots/2-2-milestone-response.png)

## 2-3-payroll - 2.3 Payroll billing

**Prompt**

```text
Prepare Brightwater payroll billing for June 2026 based on active employee count. Show per-employee billing, invoice total, and any approval needed.
```

**Observed Atlas Response**

```text
 I'm getting consistent HTTP 400 errors from Aethos, which suggests the context reference I've been provided may have expired or there's an authentication issue. To proceed with preparing Brightwater's payroll billing for June 2026, I need additional information from you:

1. What is the engagement ID or engagement name exactly as it appears in Aethos for Brightwater's payroll service?
2. How many active employees does Brightwater have for June 2026?
3. What is the per-employee billing rate for payroll services?
4. Are there any surcharges, discounts, or adjustments to apply?

Alternatively, if you have access to your Aethos dashboard or can provide the engagement details directly, I can structure the invoice with per-employee breakdown, total, and flag any approvals needed based on your approval thresholds.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 7/7 required signals; forbidden hits 1.
Criteria: Prepares Brightwater payroll billing from active employee count with total and approval need.
Matched required signals: /Brightwater/i, /payroll/i, /employee/i, /count/i, /invoice|billing/i, /total/i, /approval/i
Missing required signals: none
Invalid answer signals: /couldn'?t locate|not showing up|not found|no .* on file|need .* from you/i

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/2-3-payroll-response.png](screenshots/2-3-payroll-response.png)

## 2-4-vendor-invoice - 2.4 Vendor invoice intake

**Prompt**

```text
Process this vendor invoice for Brightwater. Match it to the right vendor and project, flag duplicate risk, code it to the right account, compare any PO or service-order evidence, and send exceptions to Inbox.
```

**Observed Atlas Response**

```text
 The Aethos backend is currently unreachable. This is blocking real-time access to vendor records, bill history, duplicate signals, PO matching, and account coding in the system of record.

Here's where we are:

The document extraction workflow has queued an Inbox review task for the Brightwater invoice (document_id: eaf2d50c-dccb-400b-a45e-c5c2861a94df). This is the right path — sensitive actions like vendor payment coding must route through Inbox with human review.

Once the Aethos system recovers, that Inbox task will contain:
- Vendor identity and master-data match
- Duplicate detection (same invoice already paid, partial duplicates, serial anomalies)
- PO or service-order attachment evidence
- Suggested GL account coding
- Amount, due date, and payment-term validation
- Any policy exceptions or risk flags

What you should do now:

1. Check your Aethos Inbox — the review task for this Brightwater invoice should appear there when the system recovers.
2. The Inbox interface will show you the extracted details, any PO or service-order links, suggested account, and flagged risks (duplicate, coding mismatch, vendor mismatch, etc.).
3. Approve or reject the coding and payment recommendation through Inbox. Your approval signals payment readiness to the batch.

I'll retry the Aethos connection in a moment to pull the data directly if needed. Would you like me to wait and retry, or do you want to proceed with manual Inbox review in the meantime?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/8 required signals.
Criteria: Extracts the uploaded Brightwater subcontractor invoice. | Matches vendor/project, codes account, checks duplicate and PO/service-order evidence, and routes exceptions to Inbox.
Matched required signals: /Brightwater/i, /vendor|subcontractor/i, /bill|invoice/i, /duplicate/i, /account|code/i, /PO|purchase order|service-order|service order/i, /Inbox|exception/i
Missing required signals: /project/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/2-4-vendor-invoice-response.png](screenshots/2-4-vendor-invoice-response.png)

## 2-4-payment-risk-read - 2.4 P2P read pack

**Prompt**

```text
Which vendor bills are due soon, which are blocked, and what evidence supports payment? Show vendor, bill number, amount, due date, status, coding evidence, source document, duplicate risk, PO/service-order match, payment-batch state, blockers, and next action. Do not create a payment batch yet.
```

**Observed Atlas Response**

```text
 Here's your vendor bill status summary. Both bills are due soon but blocked from payment due to missing evidence:

FORSTER & REID LTD
Vendor: Forster & Reid Ltd
Bill: BILL-1001
Vendor Invoice: FR-2026-0615
Amount: GBP 3,200.00
Due Date: 2026-07-05 (6 days remaining)
Status: Approved
Coding: Uncoded (0 of 1 lines coded)
Source Document: Missing (not attached)
Duplicate Risk: Low (no duplicate detected)
PO Match: Not linked
Payment Batches: None
Blockers: Incomplete bill coding + missing source document
Next Action: Complete bill coding and supply source document before payment release

BT BROADBAND
Vendor: BT Broadband
Bill: BILL-1002
Vendor Invoice: BT-2026-0620
Amount: GBP 189.00
Due Date: 2026-07-01 (2 days remaining)
Status: Approved
Coding: Uncoded (0 of 1 lines coded)
Source Document: Missing (not attached)
Duplicate Risk: Low (no duplicate detected)
PO Match: Not linked
Payment Batches: None
Blockers: Incomplete bill coding + missing source document
Next Action: Complete bill coding and supply source document before payment release

SUMMARY
Total due soon (next 30 days): GBP 3,389.00
Total blocked: 2 bills
Blocker pattern: Both bills need line coding and source document evidence before they can move to payment batch.

To clear these for payment, you'll need to: (1) code each bill's line items to the appropriate GL accounts, and (2) attach or reference the source documents (delivery receipts, contract scope documents, invoices from vendor). Once evidence is complete, both can be submitted for payment batch preparation.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 9/9 required signals.
Criteria: Shows due/blocked vendor bills with evidence, duplicate risk, PO match, payment state, blockers, and next action without batching.
Matched required signals: /vendor/i, /bill/i, /due date|due soon|overdue/i, /blocked|blocker/i, /evidence|source document/i, /duplicate/i, /PO|service order/i, /payment/i, /next action/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/2-4-payment-risk-read-response.png](screenshots/2-4-payment-risk-read-response.png)

## 2-4-single-bill - 2.4 Single bill drilldown

**Prompt**

```text
Review bill BILL-1001. Show due date, amount, vendor invoice number, coding status, source document, duplicate signals, PO/service-order match, approval state, payment readiness, existing batch status, and recommended next action.
```

**Observed Atlas Response**

```text
 Here's the bill review for BILL-1001:

BILL DETAILS
Vendor: Forster & Reid Ltd
Bill Number: BILL-1001
Vendor Invoice Number: FR-2026-0615
Amount: GBP 3,200.00
Issue Date: 15-Jun-2026
Due Date: 05-Jul-2026 (6 days remaining)

CODING STATUS
Status: Uncoded (0 of 1 line coded)
Lines: 1 line requiring allocation
Prepaid Lines: None
Service Period Exceptions: None

SOURCE DOCUMENT
Source Document Available: No
Document ID: Not linked
Blocker: Missing source document evidence

DUPLICATE SIGNALS
Duplicate Risk: No
Duplicate Review Required: No

PO/SERVICE-ORDER MATCH
PO Match Status: Not linked
No purchase order or service order currently associated with this bill

APPROVAL STATE
Current Status: Approved
Approval Stage: Approved for payment review
Bill State: Missing evidence

PAYMENT READINESS
Payment Status: Blocked
Blocking Issues:
- Coding incomplete (1 line needs allocation)
- Source document missing (invoice attachment or evidence required)

EXISTING BATCH STATUS
Payment Batches: None
Not yet included in any payment batch

RECOMMENDED NEXT ACTION
Complete bill coding and line evidence before payment approval. Obtain the missing invoice document and code the 1 uncoded line to the appropriate general ledger account. Once coding and evidence are complete, the bill can move to payment batch preparation.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 9/9 required signals.
Criteria: Reviews BILL-1001 with due date, vendor invoice number, coding, source, duplicate, approval, payment readiness, and next action.
Matched required signals: /BILL-1001/i, /due date|due/i, /vendor invoice/i, /coding|coded|account/i, /source document|source/i, /duplicate/i, /approval/i, /payment readiness|payment/i, /next action|recommend/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/2-4-single-bill-response.png](screenshots/2-4-single-bill-response.png)

## 2-5-bill-pay - 2.5 Payment controls

**Prompt**

```text
Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox.
```

**Observed Atlas Response**

```text
 I've reviewed the approved bills due this week. The issue is clear: both bills are blocked from payment. Here's my analysis:

**Bill Review Summary:**
- BILL-1001: Forster & Reid Ltd, GBP 3,200 (due 5 July) – Blocked
- BILL-1002: BT Broadband, GBP 189 (due 1 July) – Blocked

**Why These Cannot Be Paid This Week:**
Both bills are missing critical evidence and coding:
1. No bill coding completed (0 of 1 line items coded on each bill)
2. Source documents not attached to the system
3. No PO linkage for verification

These are not disputed bills—they're simply incomplete. Aethos is correctly preventing payment until financial audit evidence is in place. Paying uncoded bills violates control standards and creates month-end close delays.

**Recommendation:**
Rather than attempt a batch payment now, I recommend routing both bills back to the accounts team for completion:
- Obtain and attach the source documents
- Code the line items to the appropriate GL accounts
- Link to purchase orders if applicable
- Resubmit for payment review once evidence is complete

Once those steps are done, these bills will be payment-ready and eligible for next week's run.

Would you like me to create an action plan in Inbox to track the completion of this evidence, or escalate this to the finance operations team?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/7 required signals.
Criteria: Prepares a bill-pay run for due/overdue approved bills, excludes disputed items, explains rationale, and routes batch to Inbox.
Matched required signals: /bill-pay|payment/i, /due|overdue/i, /approved/i, /disputed|exclude/i, /batch/i, /Inbox|approval/i
Missing required signals: /rationale|reason/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/2-5-bill-pay-response.png](screenshots/2-5-bill-pay-response.png)

## 2-5-payment-packet - 2.5 Payment approval packet

**Prompt**

```text
Prepare a payment approval packet for bills due in the next 10 days. Include vendor, amount, due date, coding evidence, duplicate status, cash impact, and the approver role required for the batch.
```

**Observed Atlas Response**

```text
 PAYMENT APPROVAL PACKET — Bills due within 10 days

Generated: June 29, 2026 | Total bills: 2 | Batch amount: £3,389.00 | Currency: GBP

BILL DETAILS:

Bill 1: BILL-1001 (Forster & Reid Ltd)
  Vendor: Forster & Reid Ltd (FR-2026-0615)
  Amount: £3,200.00
  Due date: July 5, 2026 (6 days)
  Coding status: Uncoded — 0 of 1 lines coded
  Evidence: Missing source document
  Duplicate risk: No
  Payment blocker: Coding incomplete + source document missing

Bill 2: BILL-1002 (BT Broadband)
  Vendor: BT Broadband (BT-2026-0620)
  Amount: £189.00
  Due date: July 1, 2026 (2 days)
  Coding status: Uncoded — 0 of 1 lines coded
  Evidence: Missing source document
  Duplicate risk: No
  Payment blocker: Coding incomplete + source document missing

BATCH SUMMARY:

Total cash impact: £3,389.00 GBP outflow
Vendor count: 2
Duplicate review required: No (low risk across all bills)
PO linkage: Not linked (both bills)
Approval state: Approved for payment review
Payment readiness: BLOCKED

CRITICAL BLOCKERS FOR PAYMENT:

Both bills are currently blocked and cannot proceed to payment approval without remediation:

Bill BILL-1001: Complete line-item coding; attach source document (invoice)
Bill BILL-1002: Complete line-item coding; attach source document (invoice)

APPROVER ROLE REQUIRED:

Payment approval authority depends on batch amount. Both bills show approval_state as "approved_for_payment_review," meaning they have passed initial review gates. Complete the coding and evidence requirements, then route the cleaned packet to the designated payment approver per your delegation authority matrix (typically Finance Manager or Controller for batches > £1,000; Accounts Payable Manager for routine transactions under £1,000).

RECOMMENDATION:

Before proposing this batch for payment, coordinate with Accounts Payable to complete bill coding (assign GL accounts/cost centers to each line) and upload the vendor invoices as supporting evidence. Once blockers clear, I can prepare the formal payment proposal for Inbox review and approver routing.

Would you like me to draft a payment proposal once the coding and evidence are complete?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Prepares payment approval packet with vendor, amount, due date, coding evidence, duplicate status, cash impact, and approver role.
Matched required signals: /vendor/i, /amount/i, /due date|due/i, /coding evidence|coding/i, /duplicate/i, /cash impact|cash/i, /approver|approval role/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/2-5-payment-packet-response.png](screenshots/2-5-payment-packet-response.png)

## 3-1-family-office - 3.1 Family office structure

**Prompt**

```text
Show the Alderton Family Office structure. List each engagement, service line, billing model, currency, open projects, and missing setup before billing.
```

**Observed Atlas Response**

```text
 Here's the Alderton Family Office engagement structure:

**Alderton Family Office - 3 Active Engagements**

1. ENG-0008: Alderton Family Office - Advisory Retainer
   Service Line: Advisory | Billing: Retainer | Currency: GBP
   Total Value: GBP 150,000 | Period: Jan 1 - Dec 31, 2026
   Description: Private wealth advisory retainer across family entities

2. ENG-0009: Alderton Trust (1985) - Trust Accounts & Tax
   Service Line: Tax | Billing: Fixed Fee | Currency: GBP
   Total Value: GBP 12,500 | Period: Jan 1 - Dec 31, 2026
   Description: Trust accounts and tax work, including SGD dividend income review

3. ENG-0010: Alderton COSEC Retainer - All Entities
   Service Line: Company Secretarial (COSEC) | Billing: Retainer | Currency: GBP
   Total Value: GBP 38,400 | Period: Jan 1 - Dec 31, 2026
   Description: COSEC retainer covering 12 Alderton entities

**Portfolio Total: GBP 200,900 annual revenue**

**Missing Setup for Billing:**
All three engagements show these gaps:
- Billing Terms not configured (null)
- Source Document ID missing (no engagement letter on file)
- Service Catalogue reference missing
- No rate card assignments visible for advisory/tax services

These items typically block invoice generation. You'll need source engagement letters uploaded and billing terms (e.g., net 30, net 60) confirmed in each engagement before the first invoices can be raised.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/7 required signals; forbidden hits 1.
Criteria: Shows Alderton family office engagements, service lines, billing models, currency, projects, and missing setup.
Matched required signals: /Alderton/i, /engagement/i, /service line|service/i, /billing model|fixed|retainer|T&M/i, /currency|GBP|SGD|USD/i, /missing|setup/i
Missing required signals: /project/i
Invalid answer signals: /couldn'?t locate|not showing up|not found|no .* on file|need .* from you/i

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/3-1-family-office-response.png](screenshots/3-1-family-office-response.png)

## 3-2-scope-creep - 3.2 Scope creep risk

**Prompt**

```text
Review Alderton bespoke tax return scope. Compare actual time, fixed fee, expected margin, open WIP, and recommend whether we need a fee adjustment before billing.
```

**Observed Atlas Response**

```text
 Perfect. Here's my review of the Alderton bespoke tax return engagement:

ENGAGEMENT OVERVIEW
- Fixed fee: £12,500
- Service: Alderton Trust (1985) - Trust Accounts & Tax return (includes SGD dividend income review)
- Currency: GBP

KEY METRICS
- Open WIP: £1,750 (5.0 unbilled hours at £350 average rate)
- Actual time invested: 5 hours logged against the engagement
- Fixed fee: £12,500
- Gross margin target at FY close: approximately 86% (£10,750 cost absorption across full scope)

ANALYSIS & RECOMMENDATION

The engagement is tracking well:
• Unbilled hours are modest relative to the fixed fee
• The 5 hours of logged time represents only 14% of your implicit time budget (roughly 35-40 billable hours within £12,500)
• Work-in-progress is reasonable at £1,750

BEFORE BILLING: No fee adjustment recommended. The WIP position is healthy, and you have adequate cost absorption within the fixed fee to accommodate normal scope variance on trust tax returns. The 5 unbilled hours suggest efficient delivery.

However, flag for review during wrap-up:
- Confirm all SGD dividend income reconciliation and relief calculations are complete
- Verify the trust tax computation is finalized
- Once work is substantially complete, move these 5 hours into a draft invoice and route to Inbox for billing approval

Ready to draft and send the invoice when the work is complete?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Compares Alderton bespoke tax actual time, fixed fee, expected margin, WIP, and fee adjustment recommendation.
Matched required signals: /Alderton/i, /bespoke tax|tax return/i, /actual time|hours/i, /fixed fee/i, /margin/i, /WIP/i, /fee adjustment|recommend/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/3-2-scope-creep-response.png](screenshots/3-2-scope-creep-response.png)

## 3-3-sgd-journal - 3.3 Multi-currency trust accounts

**Prompt**

```text
Prepare an SGD 18,000 dividend income journal for Alderton Trust for June 2026. Show the GBP base-currency impact, FX rate provenance, required approval role, and route it to Inbox before posting.
```

**Observed Atlas Response**

```text
 Perfect. The draft Alderton Trust SGD dividend journal has been routed to Inbox for Admin approval review. Here's the full picture:

**Journal Preparation Complete**

Entry: DEMO-JE-ALDERTON-SGD
Customer: Alderton Trust
Period: June 2026
Amount: SGD 18,000 (dividend income)
Entry Date: 2026-06-21

GBP Base Currency Impact:
The SGD dividend is recorded in Aethos with conversion to GBP base currency for the tenant's consolidated reporting. The FX rate provenance is tracked through the journal's referenced date and source data.

Approval Requirements:
- Required Role: Admin (accounting approver)
- Risk Class: High-value manual journal (above 10,000 threshold)
- Routing: Inbox review task created for Admin approval
- Status: Now pending Admin review before posting

The journal is ready for review through Aethos Inbox, where the Admin reviewer can inspect the SGD-to-GBP conversion, verify the dividend income classification, and approve posting to the June 2026 period. Once approved and posted, it will clear the close blocker and allow the month-end close to proceed.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Prepares SGD dividend income journal with GBP impact, FX provenance, approval role, and Inbox routing before posting.
Matched required signals: /SGD/i, /18,?000|18000/i, /dividend/i, /journal/i, /GBP/i, /FX|exchange rate/i, /approval role|approval/i, /Inbox/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/3-3-sgd-journal-response.png](screenshots/3-3-sgd-journal-response.png)

## 3-4-cosec-reminders - 3.4 COSEC reminders

**Prompt**

```text
Review COSEC filing reminders for Alderton entities. Show upcoming filing dates, missing evidence, billing impact, and which reminders need approval before sending.
```

**Observed Atlas Response**

```text
 Based on the data pulled, I need to clarify what I found: the collections reminders search did not return any matching records for "Alderton" entities specifically. The system shows no eligible invoices for Alderton in the collections pipeline. However, I can see the approval framework that would apply to any filing reminders.

Here's what the review shows:

**Collections Status for Alderton:**
No active collections reminders drafted for Alderton entities at this time. The system recorded 0 eligible invoices and 0 review tasks created. One record for Nexus Capital Partners was skipped due to client filter mismatch (10 days overdue on INV-1001, but client name didn't match the Alderton filter).

**Approval Requirements for Filing Reminders (when applicable):**
All external communications—including COSEC filing reminders—route through Inbox and require approval before sending:
- External communications require Manager-or-higher approval
- Your role (Owner/Admin) has full approval authority across all risk categories
- Communications undergo review to prevent unauthorized external contact

**Current Inbox Status:**
You have 9 open items pending action, including month-end close work, invoice reviews, and payment batches. All are ready for your approval.

**Next Steps:**
To get a complete COSEC filing reminder review for Alderton entities, I'd need to search by specific entity name or look into your finance operational status. Would you like me to:
1. Run a broader search across all entities to find Alderton filings due?
2. Check the finance operations snapshot for upcoming close deadlines?
3. Pull AR aging or engagement details if Alderton is a customer/client engagement?

What's the specific scope you're looking for—is Alderton a customer, vendor, or internal subsidiary?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 5/7 required signals; forbidden hits 0.
Criteria: Reviews Alderton COSEC filing reminders, evidence gaps, billing impact, and approvals before sending.
Matched required signals: /Alderton/i, /COSEC/i, /filing/i, /date|deadline/i, /approval|before sending/i
Missing required signals: /evidence|missing/i, /billing impact|billing/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/3-4-cosec-reminders-response.png](screenshots/3-4-cosec-reminders-response.png)

## 4-1-usd-engagement - 4.1 USD-billed engagement

**Prompt**

```text
Explain Thornton June billing and cash position in USD and GBP. Show invoice amount, base-currency journal impact, FX rate provenance, AR status, and cash-flow effect after payment.
```

**Observed Atlas Response**

```text
 Based on Aethos data, here's Thornton Tech Solutions Ltd's June billing and cash position:

**Invoice Summary**

INV-1003: USD 4,500.00 issued 2026-06-10, due 2026-07-10

**Cash Position**

Status: Fully paid as of 2026-06-29

Payment received same day invoice was sent (2026-06-29)

Balance due: USD 0.00

**Base-Currency Journal Impact**

On invoice date (2026-06-10), Aethos posted:
- Accounts Receivable (1200) +USD 4,500
- Revenue (4000) +USD 4,500

On payment date (2026-06-29), Aethos posted:
- Bank (1100) +USD 4,500
- Accounts Receivable (1200) -USD 4,500

Net GL effect after payment cycle: Revenue recognized USD 4,500 with cash collected in full.

**FX Rate & Provenance**

Invoice currency: USD. The invoice and all journal entries are recorded in USD with no multi-currency conversion. Thornton USD Advisory project is natively denominated in USD, so no FX translation or revaluation occurred.

**AR Status & Aging**

Thornton's total open AR is USD 0 as of 2026-06-29. The invoice aged 0 days before payment. The company-wide AR aging shows USD 13,500 across 0-30 day bucket (other customers), but Thornton has no outstanding balance.

**Cash-Flow Effect After Payment**

Operating cash increased USD 4,500 from bank receipt on 2026-06-29. This is the full invoice amount, with no discounts or partial payments. Thornton is current.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/8 required signals.
Criteria: Explains Thornton June billing/cash in USD and GBP with invoice, FX provenance, AR status, and cash-flow effect.
Matched required signals: /Thornton/i, /June/i, /USD/i, /invoice/i, /FX|exchange rate/i, /AR|accounts receivable/i, /cash[- ]flow|cash flow/i
Missing required signals: /GBP/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/4-1-usd-engagement-response.png](screenshots/4-1-usd-engagement-response.png)

## 4-2-series-a - 4.2 Series A milestone

**Prompt**

```text
Thornton Series A closed at $14.2M. Update the milestone amount and invoice. Route any revenue or billing change to Inbox before sending.
```

**Observed Atlas Response**

```text
 Good. Now I have the complete picture:

**Summary:**

Thornton Tech's Series A closed at USD 14.2M. Their engagement "Thornton Tech - Series A Tax Structuring" (ENG-0012) is structured as a 0.75% success fee milestone, which calculates to **USD 106,500** on the raised amount.

The milestone amount and invoice have been queued for approval in Aethos Inbox. Here's what needs to happen:

1. **Milestone Update**: The engagement milestone needs confirmation at USD 106,500 (0.75% of USD 14.2M)
2. **Invoice Preparation**: A new invoice will be drafted for this milestone amount once approved
3. **Approval Gate**: The revenue and billing change routes through Aethos Inbox for policy review before any customer communication

An action plan has been created in Inbox (ID: e1fdd89d-42a5-4708-b3e3-407d03b4cdff) flagged for human review. Once approved there, the system will generate and send the invoice to Thornton Tech Solutions Ltd.

The current engagement shows all other Thornton engagements are active (retainer, time-and-materials, and milestone arrangements), so this Series A success fee invoice will consolidate with their regular billing.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Updates or prepares Thornton Series A milestone invoice for $14.2M and routes revenue/billing changes to Inbox.
Matched required signals: /Thornton/i, /Series A/i, /14\.2M|14,?200,?000|\$14\.2/i, /milestone/i, /invoice/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/4-2-series-a-response.png](screenshots/4-2-series-a-response.png)

## 4-3-cosec-instruction - 4.3 COSEC instruction

**Prompt**

```text
Review this COSEC instruction for Thornton. Identify the company change, create the required filing/project work item, identify billing impact, and route any external filing or invoice action to Inbox.
```

**Observed Atlas Response**

```text
 I don't have access to the document content itself—the system has processed it and created an Inbox task, but I'd need the extracted information to perform the analysis you're asking for.

Here's what I recommend:

1. Check your Inbox immediately. The document extraction workflow has already queued a task there with the extracted COSEC details, company changes, and any filing/billing information identified.

2. Once you review that Inbox item, you'll have:
   - The specific company change identified
   - Any filing requirements flagged
   - Billing impact assessment

3. If you need me to help once you have the details, I can:
   - Draft the project work item for filing (and route to Inbox for approval if needed)
   - Route any invoice/external filing action to Inbox for controlled delivery
   - Create an engagement-linked action plan

Could you share the extracted details from the Inbox task, or forward the key facts from the COSEC instruction (company name, change type, filing deadline, engagement info)? That way I can help you structure the filing/project work and route actions appropriately.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/7 required signals; forbidden hits 1.
Criteria: Extracts Thornton COSEC instruction, identifies company change, creates filing/project work item, billing impact, and Inbox routing.
Matched required signals: /COSEC/i, /company change|change/i, /filing/i, /project|work item/i, /billing impact|billing/i, /Inbox|approval/i
Missing required signals: /Thornton/i
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/4-3-cosec-instruction-response.png](screenshots/4-3-cosec-instruction-response.png)

## 5-1-close-readiness - 5.1 Pre-close checklist

**Prompt**

```text
Run June 2026 pre-close checks. Show AR, AP, WIP, unposted journals, close tasks, missing approvals, and what needs to happen before the period can be locked.
```

**Observed Atlas Response**

```text
 Here's your comprehensive June 2026 pre-close status:

**CLOSE STATUS: BLOCKED**
Period is locked: No | Ready to lock: No | As of: June 29, 2026

**CRITICAL BLOCKERS (Must resolve before lock)**

1. Unposted journals: 1
   - DEMO-JE-ALDERTON-SGD (June 21): Alderton Trust SGD dividend income accrual, GBP base currency
   - Status: Draft, must be posted or rejected

2. Incomplete close tasks: 5 of 6
   - Reconcile AR/AP subledgers: DONE
   - Review accruals: BLOCKED (Finance Manager due 7/5)
   - Review deferred revenue release: OPEN (Finance Manager due 7/5)
   - Review recurring journals: OPEN (Finance Manager due 7/5)
   - Review trial balance and close package: OPEN (Controller due 7/5)
   - Lock accounting period: BLOCKED until above tasks complete

**ACCOUNTS RECEIVABLE**
Total open: 13,500.00 (all current, 0-30 days)
Period activity: 9,000.00 revenue invoiced
Health: Strong; no aged balances beyond 30 days

**ACCOUNTS PAYABLE**
Total open: 3,389.00 (all current, 0-30 days)
Period activity: 3,389.00 bills received
No aged liabilities

**WORK IN PROGRESS**
Total WIP: 16,800.00 across 7 active projects
Top projects:
- Brightwater Annual Accounts FY2025: 5,600.00 (16 unbilled hours)
- Alderton COSEC Filings: 3,500.00 (10 unbilled hours)
- Nexus CFO Advisory: 3,150.00 (9 unbilled hours)

**FINANCIAL SNAPSHOT**
- Trial balance: BALANCED (26,639.00 debit/credit)
- Revenue: 9,000.00 (flat vs May)
- Expenses: 4,139.00 (new in June)
- Net income: 4,861.00 (down 46% vs May due to expenses)
- Total assets: 18,000.00 | Liabilities: 4,139.00 | Equity: 13,861.00

**JOURNALS**
Total in period: 7 | Posted: 6 | Draft: 1
All posted entries are AR/AP-driven or payment-related. One manual dividend accrual is pending.

**MISSING APPROVALS (Inbox items requiring action)**
10 high-priority items waiting (you have approval authority as Owner):
- Month-end close package review (Accounting level): 4,861.00 net income
- Two customer invoice drafts (Money-in level): 1,530.00 and 57,185.50
- Two vendor bill drafts (Draft level)
- Finance ops action plan
- Engagement letter review
- Plus 2 additional copilot-driven close review items

**NEXT STEPS TO UNLOCK**

1. Post or reject DEMO-JE-ALDERTON-SGD
2. Complete the 3 open Finance Manager tasks (accruals, deferred revenue, recurring journals)
3. Controller completes trial balance and close package review
4. Approve the month-end close package from Inbox
5. After all close tasks mark done, you can lock the period

Accounting and close work routes through Inbox for controlled approval. The system is operationally healthy, trial balance balances, and subledgers reconcile to GL—core fundamentals are ready. Execution moves forward once the 5 task steps complete.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Runs June pre-close checks across AR, AP, WIP, unposted journals, close tasks, approvals, and period-lock blockers.
Matched required signals: /June 2026|June/i, /AR|accounts receivable/i, /AP|accounts payable/i, /WIP/i, /unposted journal|journal/i, /close task|close/i, /approval/i, /lock|period/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-1-close-readiness-response.png](screenshots/5-1-close-readiness-response.png)

## 5-2-period-lock - 5.2 Period lock

**Prompt**

```text
Can we lock June 2026? Show the period-lock readiness result, blockers, overrides if any, and what a Controller or Owner must review before locking.
```

**Observed Atlas Response**

```text
 June 2026 is NOT ready to lock. Here's the readiness summary:

**LOCK STATUS: BLOCKED**

Two critical blockers must be resolved:

1. **Unposted journals (1)**
   - Entry: DEMO-JE-ALDERTON-SGD
   - Description: Alderton Trust SGD dividend income accrual, GBP base currency
   - Date: 2026-06-21
   - Action: Must be posted, rejected, or formally documented before lock.

2. **Incomplete close tasks (5 of 6)**
   - Review accruals (blocked, Finance Manager)
   - Review deferred revenue release (open, Finance Manager)
   - Review recurring journals (open, Finance Manager)
   - Review trial balance and close package (open, Controller)
   - Lock accounting period (blocked, Admin)

**WHAT'S COMPLETE:**
- Sub-ledger reconciliation ✓ (AR/AP reconcile to GL)
- Trial balance ✓ (balanced at 26,639.00 both sides)
- Close review queue ✓ (no pending HITL reviews)

**FINANCIAL STATUS:**
Trial balance is clean, net income 4,861 (54% margin on 9,000 revenue). Net income is down 46% vs. May due to 4,139 in new expenses.

**WHAT THE CONTROLLER & OWNER MUST REVIEW BEFORE LOCKING:**
- The draft Alderton SGD journal: determine if it should post or be reversed
- Close task completion checklist: sign off on all five incomplete reviews
- Working capital: open AR at 13,500 and WIP at 16,800 across engaged projects
- Statement variances: 100% asset growth and margin compression vs. prior month warrant narrative

**NEXT STEPS:**
1. Resolve the unposted journal
2. Complete all open close tasks
3. Once blockers clear, the lock task becomes executable

Worth noting—no overrides are currently in place. Once these tasks finish, the period will be ready to lock.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Assesses June 2026 period-lock readiness with blockers, overrides, and Controller/Owner review.
Matched required signals: /June 2026/i, /lock|period/i, /readiness|ready/i, /blocker/i, /override/i, /Controller|Owner/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-2-period-lock-response.png](screenshots/5-2-period-lock-response.png)

## 5-3-trial-balance - 5.3 Trial Balance

**Prompt**

```text
Show the June 2026 Trial Balance. Confirm whether debits equal credits, summarize the largest account movements, and flag suspense or unbalanced items.
```

**Observed Atlas Response**

```text
 Good news first: the June 2026 Trial Balance is balanced. Debits equal credits. Assets, liabilities, and equity reconcile cleanly with no unbalanced items or suspense accounts flagged.

Here's the summary:

**Trial Balance Status:**
- Trial balance is balanced: TRUE
- Balance sheet balanced: TRUE (Assets 18,000.00 = Liabilities 4,139.00 + Equity 13,861.00)

**Largest Account Movements (vs May):**

1. **Expenses (4,139.00)** — This is the dominant swing. May had zero expenses; June recorded 4,139.00, reducing net income by 46%.

2. **Cash flow impact (4,500.00)** — Ending cash position moved from 0.00 in May to 4,500.00 in June.

3. **Revenue flat (9,000.00)** — Held even with May at 9,000.00 (Accounting service line is the primary driver with 77.3% margin).

4. **Working capital exposure (26.9M net)** — AR open at 13.5M, WIP at 16.8M, AP at 3.4M. Largest WIP projects are Brightwater Annual Accounts (5.6M) and Alderton COSEC Filings (3.5M).

**Red Flags & Blockers:**

- **1 unposted journal** — DEMO-JE-ALDERTON-SGD (dividend income accrual, dated June 21) is sitting in draft and blocking period close.
- **5 incomplete close checklist tasks**, including WIP accrual review (currently blocked) and trial balance sign-off (open).
- **Period is locked for writes** until these blockers clear.

**Next steps:** Post the pending journal, then clear the close checklist tasks in Inbox. Once those are done, the period can lock and the variance commentary (net margin down from 100% to 54%) will be formally approved.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Shows June 2026 Trial Balance, debit/credit balance, largest movements, and suspense/unbalanced items.
Matched required signals: /June 2026/i, /Trial Balance/i, /debit/i, /credit/i, /balance|balanced/i, /movement|largest/i, /suspense|unbalanced/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-3-trial-balance-response.png](screenshots/5-3-trial-balance-response.png)

## 5-4-management-reporting - 5.4 Management reporting

**Prompt**

```text
Alice is at 64% utilisation in June. Which clients have unbilled WIP tied to Alice?
```

**Observed Atlas Response**

```text
 Alice has unbilled work-in-progress (WIP) tied to the following five clients:

1. Nexus — 9 hours, $3,150 WIP (CFO Advisory)
2. Brightwater — 24 hours, $8,400 WIP combined (Monthly Management Accounts + Annual Accounts FY2025)
3. Alderton — 15 hours, $5,250 WIP combined (Trust 1985 Accounts & Tax + COSEC Filings)

The unbilled balance totals 48 hours valued at $18,800 across these three clients. Given her 64% utilization in June, releasing some of this WIP through invoicing would help bridge capacity and cash.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 5/5 required signals.
Criteria: Identifies clients with unbilled WIP tied to Alice at 64 percent utilization.
Matched required signals: /Alice/i, /64%|64 percent|utili[sz]ation/i, /unbilled/i, /WIP/i, /client/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-4-management-reporting-response.png](screenshots/5-4-management-reporting-response.png)

## 5-5-management-pack - 5.5 R2R management pack

**Prompt**

```text
Give me the June 2026 month-end management pack. Explain the major variances versus May 2026, show revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers. Do not post journals or lock the period.
```

**Observed Atlas Response**

```text
 Here is your June 2026 month-end management pack:

**FINANCIAL OVERVIEW**

Revenue was flat at 9,000 versus May. The key change is 4,139 in new expenses posted in June, driving net income down 46% (from 9,000 to 4,861). Net margin contracted from 100% to 54%. Your balance sheet expanded: total assets grew from 9,000 to 18,000 (a 100% increase), driven by 4,500 in new bank cash collected and working capital activity.

**MAJOR VARIANCES vs MAY**

- Expenses jumped 4,139 (first expenses recorded this month). Nexus CFO Advisory absorbed 185.50 in direct costs; the remainder is operational spend captured in your GL.
- Net cash improved by 4,500 month-over-month, reflecting invoices converted to cash.
- AR remained stable at 13,500 all unpaid within 30 days; AP grew to 3,389 (first payables), also all current.

**REVENUE & EXPENSES**

June revenue: 9,000 across two projects (Brightwater Monthly Management Accounts and Thornton USD Advisory, each at 4,500). No revenue change from May, but both projects are hitting 100% project margin with zero direct costs. Accounting service line drove 77.3% gross margin overall (6,960 margin on 9,000 revenue).

Expenses: 4,139 total. First month with operating spend visible; reserve for timing differences in vendor bill posting.

**PROJECT MARGIN & UTILIZATION**

Two projects are healthy: Brightwater Monthly and Thornton USD Advisory each at 100% margin. Seven other engagements show zero revenue with 16,800 in accumulated WIP. Alterton COSEC Filings, Alterton Trust 1985, and Brightwater Annual Accounts FY2025 are the largest WIP holders (5,600 + 3,500 + 3,500).

Utilization is tight: two employees at 100% (over-utilized risk), one at 91.7% (healthy). No slack for scope creep or unplanned work.

**AR/AP MOVEMENT**

AR aging: 13,500 current (0-30 days), no overdue. AP aging: 3,389 current. Working capital position stable. WIP balance unchanged at 16,800 (staged projects waiting for billing).

**JOURNALS**

7 total journals posted in June; 6 posted, 1 draft. Draft journal (DEMO-JE-ALDERTON-SGD) is an Alderton Trust SGD dividend accrual awaiting review. Posted journals include AR/AP captures for two invoices, two bills, one manual accrual, and one payment reversal.

**CLOSE BLOCKERS**

You have TWO blocking issues preventing period lock:

1. Unposted journal: The Alderton SGD accrual (DEMO-JE-ALDERTON-SGD) must be posted, rejected, or formally documented for exclusion before close.
2. Five incomplete close tasks:
   - Review accruals (blocked)
   - Review deferred revenue release (open)
   - Review recurring journals (open)
   - Review trial balance and close package (open)
   - Lock period (blocked until the above clear)

Subledger reconciliation and trial balance are complete—your books are balanced.

**REMAINING NEXT STEPS**

Post or reject the draft journal. Complete or waive the five open close tasks. Once both blocking issues resolve, the period can be locked. Trial balance is balanced; no accounting overrides need
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 9/10 required signals.
Criteria: Produces June management pack comparing May with variances, revenue, expenses, margins, utilization, AR/AP, journals, and blockers without posting.
Matched required signals: /June 2026/i, /variance/i, /revenue/i, /expense/i, /margin/i, /utili[sz]ation/i, /AR|AP/i, /journal/i, /blocker/i
Missing required signals: /May 2026/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-5-management-pack-response.png](screenshots/5-5-management-pack-response.png)

## 5-5-management-drilldown - 5.5 R2R blocker drilldown

**Prompt**

```text
Drill into the draft journals and close task blockers for June 2026. Which ones block close, who owns them, and what should happen next?
```

**Observed Atlas Response**

```text
 Here's what's blocking close for June 2026:

**Two Primary Close Blockers:**

1. **Unposted Journal (1 item)**
   - Entry: DEMO-JE-ALDERTON-SGD
   - Description: Alderton Trust SGD dividend income accrual, GBP base currency
   - Date: June 21, 2026
   - This manual journal must be either posted, rejected, or documented before close

2. **Incomplete Close Tasks (5 of 6 items pending)**
   - Review accruals — Status: BLOCKED, Owner: Finance Manager
   - Review deferred revenue release — Status: OPEN, Owner: Finance Manager
   - Review recurring journals — Status: OPEN, Owner: Finance Manager
   - Review trial balance and close package — Status: OPEN, Owner: Controller
   - Lock accounting period — Status: BLOCKED (depends on above items), Owner: Admin

**Task Ownership & Dependencies:**

The Finance Manager owns three open review tasks (accruals, deferred revenue, recurring journals) all due July 5. One of these—accruals review—is marked blocked, likely waiting on the unposted journal decision.

The Controller owns the trial balance review, which is also open and due July 5.

The Admin owns the final period lock action, which cannot proceed until the Finance Manager and Controller complete their reviews.

**What Should Happen Next:**

1. Finance Manager should decide on DEMO-JE-ALDERTON-SGD: post it if it's correct, reject it if it shouldn't be recorded, or document why it's pending.

2. Once that's resolved, the accruals review task can move from blocked to complete.

3. Finance Manager then completes the other two open reviews (deferred revenue, recurring journals).

4. Controller reviews trial balance and close package.

5. Admin locks the period.

The underlying GL is balanced and sub-ledgers reconcile, so the only friction is these accounting reviews and the one unposted manual entry. Trial balance shows revenues at 9000 and expenses at 4139, net income 4861.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 5/5 required signals.
Criteria: Drills into draft journals and close task blockers with owner, close impact, and next action.
Matched required signals: /draft journal|journal/i, /close task|task/i, /block|blocker/i, /owner/i, /next action|should happen/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-5-management-drilldown-response.png](screenshots/5-5-management-drilldown-response.png)

## 5-5-statement-package - 5.5 Financial statement package

**Prompt**

```text
Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and evidence-backed management commentary. Compare it to May 2026 and show the variances.
```

**Observed Atlas Response**

```text
 I've generated your complete financial statement package for June 2026 with comparison to May 2026. Here's the executive summary:

FINANCIAL STATEMENTS SUMMARY

Trial Balance (June 2026): Balanced
- Debit/Credit totals: 26,639.00 each
- 5 line items spanning assets, revenue, expenses, liabilities

Balance Sheet
- Total Assets: 18,000.00
- Total Liabilities: 4,139.00
- Total Equity: 13,861.00
- Status: Balanced

Income Statement
- Revenue: 9,000.00
- Expenses: 4,139.00
- Net Income: 4,861.00
- Net Margin: 54.0%

Cash Flow Statement
- Operating cash inflow: 4,500.00
- Net change in cash: 4,500.00
- Ending cash balance: 4,500.00

Retained Earnings: 4,861.00

KEY VARIANCES vs MAY 2026

Revenue: Flat at 9,000.00 (no change, 0.0%)
Expenses: Increased 4,139.00 (from 0 to 4,139.00)
Net Income: Down 4,139.00 or -46.0% (from 9,000 down to 4,861)
Net Margin: Declined 46 percentage points (from 100% to 54%)
Total Assets: Up 9,000.00 or +100% (doubled from 9,000 to 18,000)
Cash Position: Improved 4,500.00 (from 0 to 4,500)

WORKING CAPITAL SNAPSHOT

Accounts Receivable (open): 13,500.00 - all within 0-30 days
Accounts Payable (open): 3,389.00 - all within 0-30 days
Work in Progress: 16,800.00 across 9 projects
Net working capital exposure: 26,911.00

Top WIP Projects:
1. Brightwater Annual Accounts FY2025: 5,600.00
2. Alderton COSEC Filings: 3,500.00
3. Nexus CFO Advisory: 3,150.00
4. Brightwater Monthly Mgmt Accounts: 2,800.00
5. Alderton Trust 1985 Accounts & Tax: 1,750.00

CLOSE READINESS WARNINGS

Period Status: BLOCKED - Cannot lock June 2026
Critical Blockers:
- 1 unposted journal (Alderton Trust SGD dividend income accrual, entry dated 2026-06-21)
- 5 incomplete close tasks

Incomplete Close Tasks (all due 2026-07-05):
1. Review accruals (blocked) - Finance Manager
2. Review deferred revenue release (open) - Finance Manager
3. Review recurring journals (open) - Finance Manager
4. Review trial balance and close package (open) - Controller
5. Lock accounting period (blocked) - Admin

Completed Checklist Items:
- Sub-ledger reconciliation: Complete (AR/AP reconcile to GL)
- Trial balance: Balanced
- Close review queue: No pending reviews
- No accounting overrides

EVIDENCE-BACKED MANAGEMENT COMMENTARY

Operating Performance: Revenue held steady while expenses increased significantly. June saw the introduction of 4,139 in period costs (likely accruals), reducing net margin by 46 points. This was offset partially by the collection of 4,500 in cash during the period, improving balance sheet liquidity.

Service Line Mix: Accounting service line dominates with 9,000 revenue and 77.3% gross margin. Two key projects (Brightwater Monthly Mgmt Accounts and Thornton USD Advisory) each generated 4,500 with 100% margins, indicating healthy project economics in billable service lines.

Project & Resource Health: Nine active projects show 16,800 in WIP value. Several projects with no revenue yet (Alderton COSEC, Alderton Trust, Brightwater Annual Accounts, Nexus offer
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 8/8 required signals.
Criteria: Generates financial statement package with TB, BS, IS, cash flow, retained earnings, statutory pack, warnings, commentary, and May variance.
Matched required signals: /Trial Balance/i, /Balance Sheet/i, /Income Statement/i, /Cash Flow/i, /Retained Earnings/i, /Statutory Pack/i, /warning|close-readiness/i, /variance|May 2026/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-5-statement-package-response.png](screenshots/5-5-statement-package-response.png)

## 5-5-year-end - 5.5 Year-end close

**Prompt**

```text
Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.
```

**Observed Atlas Response**

```text
 Perfect. Here's the year-end close readiness summary for FY 2026:

---

**YEAR-END CLOSE READINESS: FY 2026 (Dec 31)**

**Close Status: READY TO PROCEED**

All core audit checklist items are complete:
- Trial balance is balanced (26,639.00 debit / credit)
- Sub-ledger reconciliation complete for AR and AP
- No unposted journals pending
- No close-related reviews outstanding
- Period is unlocked and ready to lock

**Financial Summary (FY 2026 vs FY 2025)**

Income Statement:
- Revenue: 18,000.00 (vs 0.00 prior year, +18,000.00)
- Expenses: 4,139.00 (vs 0.00 prior year, +4,139.00)
- Net Income: 13,861.00 (vs 0.00 prior year)

Balance Sheet:
- Total Assets: 18,000.00 (Bank 4,500 + AR 13,500)
- Total Liabilities: 4,139.00 (AP 3,389 + Sales tax)
- Total Equity: 13,861.00 (unchanged MoM)
- Statement is in balance

**Retained Earnings Setup**

Current retained earnings balance: 0.00
FY 2026 net income to post: 13,861.00
No duplicate close risk detected; trial balances match month-over-month.

**Working Capital Movement**
- AR aging: All 13,500 is current (0-30 days); no outstanding collections issues
- AP aging: All 3,389 is current (0-30 days)
- WIP balance: 16,800.00 across 9 projects (largest: Brightwater Annual Accounts at 5,600)

**CRITICAL: RETAINED EARNINGS POSTING ROUTED TO INBOX**

The year-end close adjustment to post FY 2026 net income (13,861.00) to retained earnings has been submitted for Inbox review and approval. This posting will not be applied to the general ledger until explicitly approved through the review workflow.

Action required: Review and approve the retained-earnings posting in Inbox before the period lock is finalized. Once approved, the journal entry will be posted and the period can be locked.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/8 required signals.
Criteria: Prepares FY2026 year-end close with retained earnings, P&L activity, locked periods, duplicate risk, statement movement, and Inbox routing.
Matched required signals: /2026|FY2026/i, /year-end|year end/i, /retained earnings/i, /locked period|period/i, /duplicate/i, /statement movement|prior year/i, /Inbox|approval/i
Missing required signals: /P&L|profit and loss/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-5-year-end-response.png](screenshots/5-5-year-end-response.png)

## 5-6-manual-journal - 5.6 Manual journal lifecycle

**Prompt**

```text
Review this manual journal proposal for balance, account validity, period lock status, business reason, supporting evidence, approval role, and whether the approver is different from the submitter. Do not post it without Inbox approval.
```

**Observed Atlas Response**

```text
 I'm ready to review the manual journal proposal, but I don't see it attached or referenced in your message. Please provide the proposal details, and I'll check:

- Balance (debits equal credits)
- Account validity and GL mapping
- Period lock status and posting date appropriateness
- Business reason and narrative
- Supporting evidence (attachments, backing documents)
- Approval role and authority level
- Submitter vs. approver (must be different)

Once you share the proposal, I'll route it through Aethos Inbox for controlled review and approval before any posting.
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 7/8 required signals; forbidden hits 1.
Criteria: Reviews manual journal proposal for balance, account validity, period lock, reason, evidence, approval role, and segregation of duties.
Matched required signals: /journal/i, /balance|balanced/i, /account/i, /period lock|locked period/i, /business reason|reason/i, /evidence|support/i, /approval role|approval/i
Missing required signals: /approver.*submitter|different from submitter|segregation/i
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-6-manual-journal-response.png](screenshots/5-6-manual-journal-response.png)

## 5-6-reversal - 5.6 Manual journal reversal

**Prompt**

```text
Prepare a reversal packet for this posted manual journal. Explain why reversal is appropriate, propose an open-period reversal date, show the flipped debit and credit lines, and confirm the reversal will create a new journal rather than editing the original.
```

**Observed Atlas Response**

```text
 I need some details to prepare the reversal packet. Please provide:

1. **Journal identifier** — What's the journal ID, reference number, or posting date of the manual journal you want to reverse?

2. **Journal details** — What accounts and amounts were in the original entry? (Or I can look it up if you give me the reference.)

3. **Business reason** — Why is the reversal appropriate? (e.g., duplicate entry, posting error, reversing a transaction, accounting correction)

4. **Proposed reversal date** — What date do you want the reversal to post? (I'll validate it's in an open period and suggest alternatives if needed.)

Once you provide these, I'll load the relevant Aethos tools to build the reversal packet with:
- Explanation of why reversal is appropriate for this case
- Recommended open-period reversal date
- The flipped debit/credit lines (original credits become debits and vice versa)
- Confirmation that this creates a new reversing journal per accounting standards, leaving the original posted entry intact
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/7 required signals.
Criteria: Prepares reversal packet with reason, open-period date, flipped debit/credit lines, and new journal rather than editing original.
Matched required signals: /reversal/i, /journal/i, /reason|appropriate/i, /open period|date/i, /debit/i, /credit/i
Missing required signals: /new journal|not edit|rather than editing/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/5-6-reversal-response.png](screenshots/5-6-reversal-response.png)

## 6-1-finance-ops-check - 6.1 Finance Ops Manager

**Prompt**

```text
Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.
```

**Observed Atlas Response**

```text
 Perfect. Here's your June 2026 finance ops check. I've split out read-only findings from actions that need your approval.

## READ-ONLY FINDINGS

Customer Receivables: GBP 13,500 outstanding, all within 0-30 days. One invoice (INV-1001 to Nexus Capital Partners LP) is now 10 days overdue for GBP 9,000. All other invoicing is current.

Vendor Payables: GBP 3,389 due within 30 days. All payables are current with no aging concerns.

Work in Progress (Unbilled Hours): Six active projects have billable hours pending invoicing totaling GBP 22,400 in WIP value. The largest items: Brightwater Annual Accounts (GBP 5,600 on 16 hours), Alderton COSEC Filings (GBP 3,500 on 10 hours), Nexus CFO Advisory (GBP 3,150 on 9 hours), and Brightwater Monthly Management Accounts (GBP 2,800 on 8 hours).

Finance Ops Status: Operations are running normally. The daily check ran this morning as scheduled. No runtime failures or escalations.

You're matched to four finance personas: Owner/Admin, Controller, AP Lead, and AR Lead—so you can approve any policy-level work across all finance functions.

## ACTIONS REQUIRING YOUR INBOX APPROVAL (10 OPEN ITEMS)

Three categories need your review before they proceed:

INVOICING (Money-In) – 2 draft invoices pending your approval:
- Draft invoice for GBP 57,185.50 (likely retainer billing to a large client)
- Draft invoice for GBP 1,530.00 (smaller transaction)

Both are created but not yet posted. Manager-level review required.

BILLS & PROCUREMENT – 2 vendor bill drafts pending review:
- Two bill drafts from the Vendor Invoice Agent (amounts pending details)

Manager-level review required before posting.

CLOSE & ACCOUNTING – 3 close packages pending admin-level approval:
- June 2026 month-end close package (with GBP 4,861 in close adjustments)
- Year-end 2026 close package (with GBP 13,861 in close-related entries)
- Finance ops action plan for June (high priority, 4 action items)

Admin-level approval required to proceed.

COLLECTIONS – 1 overdue-invoice reminder ready for review:
- Firm-tone payment reminder to Nexus Capital Partners LP for INV-1001 (10 days overdue, GBP 9,000)

Manager-level review required before sending. The collections system has drafted this and is waiting for your sign-off in Inbox.

All 10 items are visible to you as Owner. You can approve them individually through the Inbox or, if preferred, I can help you prioritize or batch-review them.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Runs finance ops check separating read-only findings from Inbox-gated actions across billing, payment, collections, close, and review.
Matched required signals: /billing/i, /payment/i, /collections/i, /close/i, /review/i, /read-only|read only/i, /Inbox|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/6-1-finance-ops-check-response.png](screenshots/6-1-finance-ops-check-response.png)

## 6-1-action-plan - 6.1 Finance Ops action plan

**Prompt**

```text
Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.
```

**Observed Atlas Response**

```text
 Based on the financial operations snapshot I've reviewed, here's the recommended action plan for June 2026. I've identified five priority work items for manager review:

**Finance Ops Action Plan - June 2026**

1. **Invoice Brightwater Annual Accounts FY2025** — Complete milestone engagement with GBP 28,000 total value. 16 unbilled hours at 350/hour (GBP 5,600 WIP) ready to bill. This fixed-milestone work is ripe for invoicing.

2. **Finalize Alderton COSEC Filings** — 10 unbilled hours across event-based company secretarial filings (GBP 3,500 WIP). Clear for customer delivery and billing given retainer structure.

3. **Bill Alderton Trust 1985 Accounts & Tax** — Time-and-materials work with 5 unbilled hours (GBP 1,750 WIP). Trust accounts and tax work cycle appears complete in June.

4. **Collect Brightwater Monthly Management Accounts** — Retainer engagement with 8 unbilled hours (GBP 2,800 WIP). June month-end retainer invoicing and AR follow-up for GBP 13,500 current aging (0-30 days).

5. **Process Current Payables** — GBP 3,389 in AP due within 30 days requires payment processing and reconciliation. No overdue items present.

All five items require manager approval before invoicing or payment movement. The action plan is ready for Inbox review and will route through standard approval workflows. No invoices, payments, or journals have been directly executed — all actions remain in draft pending your review and authorization.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Creates at most five manager-reviewed finance ops work items and routes action plan to Inbox without approving sensitive actions.
Matched required signals: /finance ops/i, /work item|action plan/i, /five|5|at most/i, /manager-reviewed|review/i, /Inbox|approval/i, /invoice|payment|journal|email/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/6-1-action-plan-response.png](screenshots/6-1-action-plan-response.png)

## 6-2-scheduled-control-room - 6.2 Scheduled Finance Ops Manager

**Prompt**

```text
Before enabling a scheduled Finance Ops Manager run, show the current cadence, escalation windows, last run, open scheduled plans, and approval boundary for resulting work.
```

**Observed Atlas Response**

```text
 Here's the Finance Ops Manager readiness status before enabling a scheduled run:

**Schedule & Cadence**
The Manager is currently enabled and runs daily at 7 AM UTC. The next run is scheduled for today (June 29) at 7:00 AM UTC. It analyzes the current month with a 10-day lookback limit.

**Escalation Windows**
Escalation is active. Standard data is considered stale after 24 hours; high-risk items escalate after 4 hours. This means urgent financial issues surface quickly through Inbox routing.

**Last Run**
No scheduled runs have completed yet—this is the first cadence. The system is freshly initialized with default settings.

**Open Scheduled Plans**
One action plan is open: a draft Finance Ops plan from today (created 06:29 UTC), high priority, containing 4 recommended actions for June. This is awaiting Manager review before the next automated run processes further work.

**Approval Boundary for Resulting Work**
All work generated by the Manager routes through Inbox with role-based approval gates:

- Draft and low-risk work: Manager approval required
- Money-in actions (invoices, revenue): Manager approval required
- External communications: Manager approval required
- Money-out actions: Admin approval required; Owner approval for payments ≥ $50,000
- Accounting and close work: Admin approval required; Owner approval for manual journals ≥ $10,000

You currently hold Owner role, so you can approve all work at any threshold. There are 10 open Inbox items awaiting your review, spanning invoices, collections emails, vendor bills, and close preparations.

**Operational Health**
Status is green. No failures in the last 24 hours. Rate limiting is configured and the system is ready for production automation.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 6/6 required signals.
Criteria: Shows scheduled Finance Ops cadence, escalation windows, last run, open plans, and approval boundary before enablement.
Matched required signals: /scheduled|cadence/i, /Finance Ops/i, /escalation/i, /last run/i, /open .*plan|scheduled plan/i, /approval boundary|approval/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/6-2-scheduled-control-room-response.png](screenshots/6-2-scheduled-control-room-response.png)

## 7-1-approval-controls - 7.1 Approval policy and personas

**Prompt**

```text
What am I allowed to approve, what requires Owner approval, and which Inbox items are high risk? Include my finance personas, effective thresholds, pending high-risk tasks, and why each item needs review. Do not show tool names, policy reason codes, raw payloads, traces, logs, or context IDs.
```

**Observed Atlas Response**

```text
 You hold four active finance personas: Owner/Admin, Controller, AP Lead, and AR Lead. Here's your approval authority and what needs your review.

What You Can Approve:
- Any draft or low-risk work (invoices, records, engagement letters)
- Customer money-in changes (invoices, AR records)
- External communications before they're sent
- Vendor payments and payment batches
- Accounting, journals, and close preparation up to the thresholds
- High-risk AI-recommended finance actions

What Requires Owner Approval (Escalation):
- Vendor payments at or above $50,000
- High-value manual accounting journals at or above $10,000
- Any money-out work exceeding the standard admin threshold

Thresholds:
- Owner escalation for money-out: $50,000 and above
- Manual journal escalation: $10,000 and above

Your Current Inbox (13 open items):
11 of 12 flagged items are ready for your review and approval — you have the authority for all of them. No items are stuck waiting for higher approval.

High-Priority Tasks Requiring Review Now:

1. Collections email – $9,000 (Medium priority) — External communication sent by the collections agent; needs your review before the email goes to the customer.

2. Year-end close package – $13,861 (High priority) — Full year-end accounting close; requires controller-level review of all adjustments and financial statement readiness.

3. Month-end close package (June) – (High priority) — Standard month-end package with accruals and adjustments; controller review is required.

4. Two vendor bill drafts – (High priority each) — AI-reviewed vendor invoices ready for your processing approval.

5. Payment batch – $3,389 (High priority) — Forster & Reid and BT Broadband payments; requires admin-level approval before processing.

6. Two customer invoices – $1,530 and $57,185 (High priority each) — Money-in transactions; the larger one carries material exposure and needs your sign-off before it affects AR.

7. Finance operations action plan (High priority) — Strategic operational workflow proposal from the Finance Ops Manager; requires manager review.

8. Nexus engagement letter extraction (High priority) — Client engagement data onboarded from documentation; needs validation before it affects records.

The only reason each needs review is that these actions either affect financial records, move money, communicate externally to customers and vendors, or require a human approval gate as a control—none should be auto-processed by AI without your visibility.
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Explains approval permissions, Owner approval thresholds, high-risk Inbox items, personas, and reasons without exposing internals.
Matched required signals: /approve|approval/i, /Owner/i, /threshold/i, /persona|role/i, /Inbox/i, /high risk|risk/i, /review/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/7-1-approval-controls-response.png](screenshots/7-1-approval-controls-response.png)

## 7-2-decision-trail - 7.2 Decision trail

**Prompt**

```text
Show the decision trail for the latest bill, invoice, payment batch, journal, or close record. Include the related Inbox task, actor role, decision type, timestamp, and before/after review summary.
```

**Observed Atlas Response**

```text
 ## Decision Trail Summary

Based on the latest records across finance operations, here's the most recent decision trail:

**LATEST PENDING DECISIONS IN INBOX**

The most recent item awaiting approval is a collections reminder email (6:36 AM today):
- Task: Review collections email to Nexus Capital Partners LP
- Role Required: Manager (Current user can approve)
- Risk Category: External send
- Amount: GBP 9,000
- Status: Open
- Business Reason: External communications require human review before sending

This is tied to invoice INV-1001 (due 2026-06-19), which is now 10 days overdue. A firm-tone reminder was last sent to the customer at 6:36:11 AM today and is pending review in Inbox.

**SECOND: YEAR-END CLOSE PREPARATION**

Two accounting tasks are also pending immediate attention:

1. Year-End Close Review (6:35 AM)
   - Type: Accounting task requiring admin approval
   - Amount: GBP 13,861
   - Status: Open
   - Requirement: Accounting approver sign-off

2. Month-End Close Review (6:27 AM)
   - Type: Accounting task requiring admin approval
   - Amount: GBP 4,861
   - Status: Open
   - Requirement: Accounting approver sign-off

**CLOSE BLOCKERS FOR JUNE 2026**

The accounting period cannot lock because:
- 1 unposted journal: DEMO-JE-ALDERTON-SGD (Alderton Trust SGD dividend income accrual) created 6:15 AM today—must be posted, rejected, or documented.
- 5 incomplete close tasks: Review accruals, deferred revenue release, recurring journals, trial balance, and period lock.

**EARLIER BILLS AWAITING CODING**

Two vendor bills are approved but blocked from payment:
- BILL-1001 from Forster & Reid Ltd (GBP 3,200 due 2026-07-05)
- BILL-1002 from BT Broadband (GBP 189 due 2026-07-01)

Both lack evidence and are uncoded—they need line-by-line coding and supporting documents before payment can proceed.

**YOUR APPROVAL CAPACITY**

You are authorized as the Owner/Admin with approval rights across all risk categories: drafts, money-in (invoices), money-out (payments), external sends, accounting work, and high-value transactions.

Would you like me to drill into any specific decision trail, pending Inbox task, or close blocker?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/6 required signals; forbidden hits 0.
Criteria: Shows decision trail with related Inbox task, actor role, decision type, timestamp, and before/after summary.
Matched required signals: /decision/i, /Inbox/i, /actor role|role/i, /decision type|type/i
Missing required signals: /timestamp|time/i, /before\/after|before and after|review summary/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/7-2-decision-trail-response.png](screenshots/7-2-decision-trail-response.png)

## 7-3-operational-health - 7.3 Operational Health

**Prompt**

```text
Show operational health for the platform today. Include degraded health, public endpoint abuse, background failure spikes, and agent/tool/workflow failure spikes. Do not expose secrets, traces, raw logs, or stack traces.
```

**Observed Atlas Response**

```text
 I don't have access to operational health or infrastructure monitoring tools for the platform. The Aethos tools available to me are focused on business finance operations—O2C (Order-to-Cash), P2P (Procure-to-Pay), and R2R (Record-to-Report) workflows.

To get the operational health you're asking about—degraded health, endpoint abuse, background failure spikes, and agent/tool/workflow failures—you would need to query:

- A monitoring/observability platform (Datadog, New Relic, Prometheus, CloudWatch, etc.)
- Infrastructure dashboards (Kubernetes health, service mesh, load balancers)
- Application performance monitoring (APM) systems
- Log aggregation and alerting systems (ELK, Splunk, etc.)
- Rate-limiting and DDoS protection services
- Background job monitoring (Celery, Bull, etc.)
- Workflow orchestration dashboards (Temporal, Airflow, etc.)

Can you point me to where that operational data lives? Is there a dashboard URL, monitoring API, or alert system I should check?
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 6/6 required signals; forbidden hits 1.
Criteria: Shows operational health with degraded status, public abuse, background failures, agent/tool/workflow failures, and no secrets/logs/traces.
Matched required signals: /health/i, /degraded|status/i, /public endpoint|abuse/i, /background/i, /agent|tool|workflow/i, /failure|spike|alert/i
Missing required signals: none
Invalid answer signals: /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/7-3-operational-health-response.png](screenshots/7-3-operational-health-response.png)

## 7-4-documents-audit - 7.4 Documents and source evidence

**Prompt**

```text
Show documents that support recent engagements, bills, invoices, journals, and Inbox decisions. For each, show the linked business record, source filename, extraction state, and what I should review next.
```

**Observed Atlas Response**

```text
 Here's a comprehensive view of documents supporting your recent business activities. I've organized this by area with linked records, extraction state, and next steps:

=== ENGAGEMENTS (10 Active) ===

Thornton Tech Solutions Ltd
- ENG-0013: COSEC Filings (Time & Materials, GBP 3,500)
- ENG-0012: Series A Tax Structuring (Milestone, USD 106,500)
- ENG-0011: Accounting & Advisory FY2026 (Retainer, USD 54,000)

Alderton Family Office
- ENG-0010: COSEC Retainer - 12 entities (Retainer, GBP 38,400)
- ENG-0009: Trust (1985) Accounts & Tax (Fixed fee, GBP 12,500)
- ENG-0008: Advisory Retainer (Retainer, GBP 150,000)

Brightwater Manufacturing Ltd
- ENG-0007: Payroll Bureau (Fixed fee, GBP 18,360)
- ENG-0006: Annual Statutory Accounts + CT600 FY2025 (Milestone, GBP 28,000)
- ENG-0005: Monthly Management Accounts (Retainer, GBP 54,000)

Nexus Capital Partners LP
- ENG-0004: Corporation Tax Return FY2025 (Capped T&M, GBP 22,000)
- ENG-0003: Group Accounting & Advisory (Mixed, GBP 156,000)

Next: All engagements active and assigned. Review WIP reconciliation below.

=== INVOICES & AR (3 Recent Invoices) ===

INV-1001 | Nexus Capital Partners LP | GBP 9,000 | OVERDUE 10 days
- Status: Sent, unpaid, due 2026-06-19
- Reminder: 1 firm reminder sent today at 06:36; in cooldown (wait 24-48h before next)
- Review next: Check payment status before end of day; cool-down prevents immediate escalation

INV-1003 | Thornton Tech Solutions Ltd | USD 4,500 | PAID
- Status: Sent 29 Jun, paid same day
- Collections: No follow-up needed
- Review next: Record payment confirmation

INV-1002 | Brightwater Manufacturing Ltd | GBP 4,500 | CURRENT
- Status: Sent 29 Jun, due 2026-07-25
- Collections: No reminder yet; triggers policy at 14+ days overdue
- Review next: Monitor for escalation when due date approaches

Total AR balance: GBP 13,500 (GBP 9,000 overdue)

=== BILLS & AP (2 Recent Bills — Both Blocked) ===

BILL-1001 | Forster & Reid Ltd (FR-2026-0615) | GBP 3,200 | DUE 2026-07-05 (6 days)
- Status: Approved, missing evidence
- Blockers: Uncoded + no source document attached
- Extraction: 0 of 1 line coded; no PO link
- Review next: Upload invoice image, code expense line, then unblock for payment

BILL-1002 | BT Broadband (BT-2026-0620) | GBP 189 | DUE 2026-07-01 (2 days)
- Status: Approved, missing evidence
- Blockers: Uncoded + no source document attached
- Extraction: 0 of 1 line coded; no PO link
- Review next: Upload invoice image urgently, code line, unblock (due in 2 days)

Total AP blocked: GBP 3,389; total due soon (within 10 days): GBP 3,389

=== WORK IN PROGRESS (Unbilled) ===

Active WIP totaling GBP 22,350:
- Brightwater Annual Accounts FY2025: 16 hrs → GBP 5,600
- Nexus CFO Advisory: 9 hrs → GBP 3,150
- Alderton COSEC Filings: 10 hrs → GBP 3,500
- Brightwater Monthly Management Accounts: 8 hrs → GBP 2,800
- Alderton Trust 1985 Accounts & Tax: 5 hrs → GBP 1,750

Review next: 38 unbilled hours across 5 projects; prepare invoices for next billing cycle

=== IN
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/8 required signals.
Criteria: Shows source documents linked to engagements, bills, invoices, journals, and Inbox decisions with extraction state and next review.
Matched required signals: /document|source/i, /engagement/i, /bill/i, /invoice/i, /Inbox/i, /extraction state|extracted|processing/i, /review next|next review|what .* review/i
Missing required signals: /journal/i
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/7-4-documents-audit-response.png](screenshots/7-4-documents-audit-response.png)

## 7-5-config-telemetry - 7.5 Configuration and telemetry

**Prompt**

```text
Review configuration and telemetry readiness. Show approval controls, scheduled Finance Ops Manager settings, Atlas runtime, Langfuse observability status, operational alerts, and any public abuse-path controls that need attention.
```

**Observed Atlas Response**

```text
 Configuration and telemetry status report:

APPROVAL CONTROLS
Your role is Owner, which grants you all personas: Owner/Admin, Controller, AP Lead, and AR Lead. You can approve all action types without escalation. Policy thresholds in place are Owner approval required for money-out at $50,000+, and elevated approval for manual journals at $10,000+.

FINANCE OPS MANAGER SCHEDULING
Status: Enabled, running daily at 7:00 UTC. Period mode is current month with 10-day lookback. Stale-item escalation is active (24 hours for standard, 4 hours for high-risk). Next scheduled run is today at 7:00 UTC.

ATLAS RUNTIME
Environment is production with synchronous extraction. Queue is configured but not required. Rate limiting is enabled using in-memory backend with 60-second windows. No distributed rate-limit backend is configured; it falls back to memory. Health status is OK.

FAILURE TELEMETRY (24H)
Request failures: 2 (non-workflow). Background failures: 0. Failed agent runs: 0. Failed tool invocations: 0. Failed workflow runs: 0. All agents and workflows completed successfully.

ALERTS & ESCALATIONS
No active alerts. Alert routing is not configured (runbook queue channel is disabled). Escalation is enabled but no escalations are pending.

OPERATIONAL FINDINGS

13 open Inbox items awaiting approval. All are approvable by your role. Highest priority: 2 accounting/close packages (June month-end and year-end close prep), 2 draft vendor invoices, 2 money-in invoices totaling ~$58,715, 1 payment batch ($3,389), 1 collections email, and 1 engagement onboarding review.

One open action plan for June 2026 with 4 items (created at 06:29 UTC today) in draft status, awaiting your review.

LANGFUSE OBSERVABILITY & ABUSE-PATH CONTROLS

That information is not exposed through the current telemetry tools. Langfuse integration status, distributed tracing, and public abuse-path controls (CORS, rate-limit policies for external API consumers, API key rotation schedules) would require access to infrastructure observability or API gateway configuration outside the Aethos Inbox-focused toolset. If you need to audit:
- Langfuse tracing and spans integration, contact your infrastructure team
- External API controls and DDoS mitigation, check your API gateway console
- Rate-limit and auth policies on public endpoints, review the deployment manifest or gateway config

Is there a specific approval or action plan from Inbox you'd like me to summarize, or deeper dive into particular risk categories?
```

**Business Validation**

Verdict: PASS
Summary: Business-valid answer: matched 7/7 required signals.
Criteria: Reviews approval controls, scheduled Finance Ops, Atlas runtime, Langfuse observability, operational alerts, and abuse controls.
Matched required signals: /approval controls|approval/i, /scheduled Finance Ops|Finance Ops/i, /Atlas runtime|Atlas/i, /Langfuse/i, /observability|telemetry/i, /alert/i, /abuse|public/i
Missing required signals: none
Invalid answer signals: none

Screenshot: [docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/screenshots/7-5-config-telemetry-response.png](screenshots/7-5-config-telemetry-response.png)

## Browser Console Errors

- `Failed to load Atlas threads: TypeError: Failed to fetch
    at https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:2:3143
    at t.<computed> (https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:1:13713)
    at n.<anonymo`

## Network Failures And 5xx Responses

- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20`
- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status`
