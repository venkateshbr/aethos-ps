# Demo Guide v2 Production Browser Validation

Run ID: `2026-06-30T07-23-33-257Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-06-30T07:46:32.723Z`

This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.

Summary: PASS 19, WARN 0, FAIL 3, SKIP 0

## Evidence Table

| ID | Section | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| auth | Authentication | Logged into https://aethos.ishirock.tech | PASS | [screenshot](screenshots/auth-login-filled.png) | Tenant: Meridian Demo v2 20260630063630<br>Tenant ID: a0267012-73a9-416c-bba2-81d86e2bbba4<br>User: prod-demo-v2-20260630063630@aethos-qa.dev |
| route-copilot | Route Coverage | Aethos Atlas | PASS | [screenshot](screenshots/route-copilot.png) | URL: https://aethos.ishirock.tech/app/copilot<br>Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
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
| 1-2-engagement-structure | 1.2 Project structure | Atlas prompt | FAIL | [screenshot](screenshots/1-2-engagement-structure-response.png) | Business validation failed: matched 4/4 required signals; forbidden hits 1.<br>Invalid answer signals: /couldn'?t locate/not showing up/not found/no .* on file/need .* from you/need .* details/need more information/need some details/i |
| 1-3-log-time | 1.3 Time entry | Atlas prompt | FAIL | [screenshot](screenshots/1-3-log-time-response.png) | Expected response signals matched 0/1.<br>Business validation failed: matched 0/5 required signals; forbidden hits 1.<br>Missing required signals: /4\.5/4\.50/i, /Nexus/i, /CFO Advisory/board pack/cash flow/i, /time/hours/i, /logged/created/Inbox/approval/i<br>Invalid answer signals: No Atlas response captured. |

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

Screenshot: [docs/qa/demo-v2-production-2026-06-30T07-23-33-257Z/screenshots/1-1-engagement-letter-response.png](screenshots/1-1-engagement-letter-response.png)

## 1-2-engagement-structure - 1.2 Project structure

**Prompt**

```text
Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.
```

**Observed Atlas Response**

```text
 We need to respond to user request: "Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing."

We have to use the appropriate tool(s) to get the engagement structure. The system's tool for listing engagements is query_engagements, which can list engagements for the current tenant, with optional limit and status filter.

But the user wants details on "Nexus Capital Partners engagement structure". Potentially there is an engagement with a client named Nexus Capital Partners. They want active projects, billing model for each workstream, and anything missing before billing.

The system has a function to query engagements. But that only lists engagements; it doesn't provide detailed structure. However maybe we can get engagement ID and then use something else to get details like projects, billing model, etc. There's no direct tool for retrieving engagement details beyond query_engagements. But perhaps we can query time entries? Not relevant. There's a tool to get WIP, get_ar_aging etc. But the request is to show the engagement structure, listing active projects, billing model for each workstream, and anything missing before billing.

We might need to search for engagements with name containing "Nexus Capital Partners". The query_engagements tool can filter by status but not by name. There's no parameter for searching name. But maybe the system's query_engagements will return a list of engagements for the current tenant. The user wants "Nexus Capital Partners engagement structure". Maybe there's only one engagement with that client.

We can call query_engagements with status 'active' to list active engagements. Use default limit of 10. That may return the engagement.

But then the user also wants "billing model for each workstream". How can we get workstream details? There's no tool for retrieving workstream details directly. However perhaps the engagement structure includes projects (or workstreams) under the engagement. Possibly we can query "query_time_entries" for a project_id but that only lists time entries, not billing model.

The tool "get_wip" returns work in progress — unbilled effort and its estimated value per project. That might help identify missing billing items.

But the request is for "anything missing before billing." That might refer to unbilled time, unbilled expenses that need to be captured before invoicing. That could be derived from WIP.

Thus, we might need to retrieve engagement ID, then retrieve its projects (maybe using query_engagements to get engagement details? but only returns engagements, not projects). There's no direct function to fetch engagement details except perhaps query_engagements returns engagement ID, name, status, maybe some other fields.

Actually, the description of query_engagements: "List engagements for the current tenant. Use this when the user asks about their engagements, clients, or projects." So it m
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 4/4 required signals; forbidden hits 1.
Criteria: Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.
Matched required signals: /Nexus/i, /project|workstream/i, /billing model|fixed|retainer|T&M|time and materials/i, /missing|ready|before billing|setup/i
Missing required signals: none
Invalid answer signals: /couldn'?t locate|not showing up|not found|no .* on file|need .* from you|need .* details|need more information|need some details/i

Screenshot: [docs/qa/demo-v2-production-2026-06-30T07-23-33-257Z/screenshots/1-2-engagement-structure-response.png](screenshots/1-2-engagement-structure-response.png)

## 1-3-log-time - 1.3 Time entry

**Prompt**

```text
Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling
```

**Observed Atlas Response**

```text
(no response captured)
```

**Business Validation**

Verdict: FAIL
Summary: Business validation failed: matched 0/5 required signals; forbidden hits 1.
Criteria: Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.
Matched required signals: none
Missing required signals: /4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /time|hours/i, /logged|created|Inbox|approval/i
Invalid answer signals: No Atlas response captured.

Screenshot: [docs/qa/demo-v2-production-2026-06-30T07-23-33-257Z/screenshots/1-3-log-time-response.png](screenshots/1-3-log-time-response.png)

## Browser Console Errors

- `Failed to load Atlas threads: TypeError: Failed to fetch
    at https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:2:3143
    at t.<computed> (https://aethos.ishirock.tech/polyfills-OQVFUOR5.js:1:13713)
    at n.<anonymo`
- `Failed to load resource: net::ERR_HTTP2_PROTOCOL_ERROR`
- `Atlas send error: network error`
- `Failed to load resource: net::ERR_NETWORK_IO_SUSPENDED`
- `Atlas send error: network error`

## Network Failures And 5xx Responses

- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status`
- `net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20`
- `net::ERR_HTTP2_PROTOCOL_ERROR https://aethos.ishirock.tech/api/v1/chat/threads/fbd4315c-29f5-49f7-a168-eb8417de8142/messages`
- `net::ERR_NETWORK_IO_SUSPENDED https://aethos.ishirock.tech/api/v1/chat/threads/549783d9-795e-4fd3-bb75-9bd07e13bdc6/messages`
