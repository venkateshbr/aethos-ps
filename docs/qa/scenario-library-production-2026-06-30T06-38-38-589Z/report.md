# Aethos PS Test Scenario Library Production Run

Run ID: `2026-06-30T06-38-38-589Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-06-30T07:23:15.096Z`

Summary: PASS 104, WARN 0, FAIL 22, SKIP 0

## Scope

- Created all 10 scenario-library tenants through the deployed signup API.
- Created one signature client, engagement, active project, invited timesheet employee, and project assignment per tenant through authenticated product APIs.
- Created one ERP manager user per tenant through the tenant-user administration API.
- Validated live owner login, ERP manager login, key app routes, one Atlas business prompt per tenant, and independent timesheet login/time submission per tenant.
- This run does not direct-write to the database and does not use backend seed scripts.

## Known Blocked Coverage

- Tenant-user invite exists and is used for one ERP manager per tenant.
- Employee invite exists and was used for independent timesheet portal validation.
- Auditor and Executive Viewer are distinct read-only ERP roles; Tenant Admin role/user administration is covered by the focused RBAC browser proof.

## Evidence Table

| Tenant | ID | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| Cobalt Consulting Co. | T1-signup | Created tenant through production signup API | PASS |  | tenant_id=ff918863-8ab6-4be2-9ce5-19a1d92b74a6<br>owner=prod-t1-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Cobalt Consulting Co. | T1-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Riverbend Foods<br>project=Riverbend Discovery Project<br>erp_user=prod-t1-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t1-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Cobalt Consulting Co. | T1-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T1-owner-login.png) |  |
| Cobalt Consulting Co. | T1-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T1-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Cobalt Consulting Co. | T1-clients | Live route /app/clients | PASS | [screenshot](screenshots/T1-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Cobalt Consulting Co. | T1-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T1-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Cobalt Consulting Co. | T1-projects | Live route /app/projects | PASS | [screenshot](screenshots/T1-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Cobalt Consulting Co. | T1-people | Live route /app/people | PASS | [screenshot](screenshots/T1-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Cobalt Consulting Co. | T1-time | Live route /app/time | PASS | [screenshot](screenshots/T1-time.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Time Entries Lo |
| Cobalt Consulting Co. | T1-inbox | Live route /app/inbox | PASS | [screenshot](screenshots/T1-inbox.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Inbox All Engag |
| Cobalt Consulting Co. | T1-invoices | Live route /app/invoices | PASS | [screenshot](screenshots/T1-invoices.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Invoices Review |
| Cobalt Consulting Co. | T1-bills | Live route /app/bills | PASS | [screenshot](screenshots/T1-bills.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Bills Manage ve |
| Cobalt Consulting Co. | T1-reports | Live route /app/reports | PASS | [screenshot](screenshots/T1-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Cobalt Consulting Co. | T1-journals | Live route /app/accounting/journals | PASS | [screenshot](screenshots/T1-journals.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Journal Entries |
| Cobalt Consulting Co. | T1-settings | Live route /app/settings | PASS | [screenshot](screenshots/T1-settings.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Settings Manage |
| Cobalt Consulting Co. | T1-atlas | Atlas scenario-library prompt | PASS | [screenshot](screenshots/T1-atlas-response.png) | Prompt: Show me the Riverbend Foods engagement structure. List active projects, billing model, linked source data, and anything missing before billing.<br>Response excerpt:  I see there are no active engagements in the system. Let me check for all engagements to get a complete picture: **Riverbend Foods Engagement Structure** / Field / Value / /-------/-------/ / **Engagement ID** / `e4bdd206-fb6d-4d9b-82b7-a9feba4725bd` / / **Engagement Name** / Ri<br>Required business signals present.<br>No internal tool terminology detected. |
| Cobalt Consulting Co. | T1-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Cobalt Consulting Co. | T1-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Pixel & Pulp Studio | T2-signup | Created tenant through production signup API | PASS |  | tenant_id=8f8abe81-c6fe-4099-ad5b-bd26180f43d1<br>owner=prod-t2-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Pixel & Pulp Studio | T2-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Aurora Cosmetics<br>project=Aurora Milestone 1 Build<br>erp_user=prod-t2-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t2-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Pixel & Pulp Studio | T2-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T2-owner-login.png) |  |
| Pixel & Pulp Studio | T2-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T2-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Pixel & Pulp Studio | T2-clients | Live route /app/clients | PASS | [screenshot](screenshots/T2-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Pixel & Pulp Studio | T2-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T2-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Pixel & Pulp Studio | T2-projects | Live route /app/projects | PASS | [screenshot](screenshots/T2-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Pixel & Pulp Studio | T2-people | Live route /app/people | PASS | [screenshot](screenshots/T2-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Pixel & Pulp Studio | T2-reports | Live route /app/reports | PASS | [screenshot](screenshots/T2-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Pixel & Pulp Studio | T2-atlas | Atlas scenario-library prompt | PASS | [screenshot](screenshots/T2-atlas-response.png) | Prompt: Show me the Aurora Cosmetics milestone engagement. Include projects, milestone billing model, WIP readiness, and missing setup before invoicing.<br>Response excerpt:  **Aurora Cosmetics Milestone Engagement** - **Name**: Aurora Web Build SOW - **Billing Model**: Milestone (GBP) - **Total Value**: £45,000.00 - **Status**: Draft **Projects**: 1. **General** (Project ID: ef59b556-0acb-44f5-983b-3a746d725c5e) 2. **Aurora Milestone 1 Build** (Proj<br>Required business signals present.<br>No internal tool terminology detected. |
| Pixel & Pulp Studio | T2-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Pixel & Pulp Studio | T2-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Harborstone Accountants | T3-signup | Created tenant through production signup API | PASS |  | tenant_id=95e11c31-563a-4b4e-8fe4-55800b39ea4e<br>owner=prod-t3-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Harborstone Accountants | T3-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Delmont Holdings<br>project=Delmont Accounts Drafting<br>erp_user=prod-t3-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t3-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Harborstone Accountants | T3-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T3-owner-login.png) |  |
| Harborstone Accountants | T3-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T3-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Harborstone Accountants | T3-clients | Live route /app/clients | PASS | [screenshot](screenshots/T3-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Harborstone Accountants | T3-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T3-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Harborstone Accountants | T3-projects | Live route /app/projects | PASS | [screenshot](screenshots/T3-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Harborstone Accountants | T3-people | Live route /app/people | PASS | [screenshot](screenshots/T3-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Harborstone Accountants | T3-reports | Live route /app/reports | PASS | [screenshot](screenshots/T3-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Harborstone Accountants | T3-atlas | Atlas scenario-library prompt | PASS | [screenshot](screenshots/T3-atlas-response.png) | Prompt: Show me the Delmont Holdings annual accounts engagement. Include service line, billing terms, projects, and year-end reporting readiness.<br>Response excerpt:  The engagement "Delmont Annual Accounts FY2026" (ID: 0c06d1ce-7779-40e4-9454-e81dfde1f92f) under Delmont Holdings shows: - **Billing Terms**: Fixed fee in USD ($18,500.00) - **Status**: Draft - **Service Line**: Not explicitly detailed in current data - **Projects**: No projects<br>Required business signals present.<br>No internal tool terminology detected. |
| Harborstone Accountants | T3-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Harborstone Accountants | T3-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Vantage Tax Partners | T4-signup | Created tenant through production signup API | PASS |  | tenant_id=a8a54ca2-3666-4c5b-a239-a8b10230184f<br>owner=prod-t4-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Vantage Tax Partners | T4-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Pacific Rim Holdings<br>project=Pacific Rim FX Advisory<br>erp_user=prod-t4-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t4-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Vantage Tax Partners | T4-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T4-owner-login.png) |  |
| Vantage Tax Partners | T4-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T4-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Vantage Tax Partners | T4-clients | Live route /app/clients | PASS | [screenshot](screenshots/T4-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Vantage Tax Partners | T4-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T4-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Vantage Tax Partners | T4-projects | Live route /app/projects | PASS | [screenshot](screenshots/T4-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Vantage Tax Partners | T4-people | Live route /app/people | PASS | [screenshot](screenshots/T4-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Vantage Tax Partners | T4-reports | Live route /app/reports | PASS | [screenshot](screenshots/T4-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Vantage Tax Partners | T4-atlas | Atlas scenario-library prompt | PASS | [screenshot](screenshots/T4-atlas-response.png) | Prompt: Review Pacific Rim cross-border tax readiness. Include FX provenance needs, capped T&M terms, project setup, and missing evidence before billing.<br>Response excerpt:  The Pacific Rim Cross-Border Tax engagement (ENG-0001) is currently in draft status and not yet ready for billing. Here is the readiness review: Project Setup & Terms The engagement is correctly configured for Capped T&M with a total value of 38,000 SGD. However, the billing ter<br>Required business signals present.<br>No internal tool terminology detected. |
| Vantage Tax Partners | T4-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Vantage Tax Partners | T4-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Indus Engineering Advisory | T5-signup | Created tenant through production signup API | PASS |  | tenant_id=99352d27-b332-413e-b34e-5033c7ab8d63<br>owner=prod-t5-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Indus Engineering Advisory | T5-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Deccan Metro Authority<br>project=Deccan Metro Phase 1 PMO<br>erp_user=prod-t5-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t5-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Indus Engineering Advisory | T5-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T5-owner-login.png) |  |
| Indus Engineering Advisory | T5-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T5-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Indus Engineering Advisory | T5-clients | Live route /app/clients | PASS | [screenshot](screenshots/T5-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Indus Engineering Advisory | T5-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T5-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Indus Engineering Advisory | T5-projects | Live route /app/projects | PASS | [screenshot](screenshots/T5-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Indus Engineering Advisory | T5-people | Live route /app/people | PASS | [screenshot](screenshots/T5-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Indus Engineering Advisory | T5-reports | Live route /app/reports | PASS | [screenshot](screenshots/T5-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Indus Engineering Advisory | T5-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T5-atlas-response.png) | Prompt: Show me Deccan Metro PMO delivery and billing readiness. Include milestone program setup, procurement risks, WIP, and AP controls to verify.<br>No Atlas response captured.<br>Missing required response signals: Deccan, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Indus Engineering Advisory | T5-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Indus Engineering Advisory | T5-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Southern Cross Legal | T6-signup | Created tenant through production signup API | PASS |  | tenant_id=d46626f7-a4ee-49d0-958b-ae4d74960128<br>owner=prod-t6-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Southern Cross Legal | T6-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Brindabella Ventures<br>project=Brindabella Matter Support<br>erp_user=prod-t6-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t6-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Southern Cross Legal | T6-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T6-owner-login.png) |  |
| Southern Cross Legal | T6-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T6-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Southern Cross Legal | T6-clients | Live route /app/clients | PASS | [screenshot](screenshots/T6-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Southern Cross Legal | T6-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T6-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Southern Cross Legal | T6-projects | Live route /app/projects | PASS | [screenshot](screenshots/T6-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Southern Cross Legal | T6-people | Live route /app/people | PASS | [screenshot](screenshots/T6-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Southern Cross Legal | T6-reports | Live route /app/reports | PASS | [screenshot](screenshots/T6-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Southern Cross Legal | T6-atlas | Atlas scenario-library prompt | PASS | [screenshot](screenshots/T6-atlas-response.png) | Prompt: Show me Brindabella retainer-draw status. Include project setup, retainer floor risk, invoice readiness, and any collection hold considerations.<br>Response excerpt:  The Brindabella Retainer Draw is currently in a draft state, meaning the project setup is not yet finalized. Project Setup: The engagement (ENG-0001) for Brindabella Ventures is listed as a draft with a total value of 60,000 AUD. It is configured as a retainer draw for advisory <br>Required business signals present.<br>No internal tool terminology detected. |
| Southern Cross Legal | T6-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Southern Cross Legal | T6-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Atlas Capital Advisors | T7-signup | Created tenant through production signup API | PASS |  | tenant_id=fb5926c5-4de3-4f38-b377-5919fdfcffea<br>owner=prod-t7-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Atlas Capital Advisors | T7-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Redwood Industrials<br>project=Redwood Deal Execution<br>erp_user=prod-t7-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t7-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Atlas Capital Advisors | T7-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T7-owner-login.png) |  |
| Atlas Capital Advisors | T7-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T7-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Atlas Capital Advisors | T7-clients | Live route /app/clients | PASS | [screenshot](screenshots/T7-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Atlas Capital Advisors | T7-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T7-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Atlas Capital Advisors | T7-projects | Live route /app/projects | PASS | [screenshot](screenshots/T7-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Atlas Capital Advisors | T7-people | Live route /app/people | PASS | [screenshot](screenshots/T7-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Atlas Capital Advisors | T7-reports | Live route /app/reports | PASS | [screenshot](screenshots/T7-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Atlas Capital Advisors | T7-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T7-atlas-response.png) | Prompt: Review Redwood sell-side M&A billing readiness. Include success-fee milestone logic, approval boundary, FX considerations, and evidence needed before invoicing.<br>Response excerpt:  <br>Missing required response signals: Redwood, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Atlas Capital Advisors | T7-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Atlas Capital Advisors | T7-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Helix Talent Group | T8-signup | Created tenant through production signup API | PASS |  | tenant_id=1c5cd22f-0671-46bb-8b58-940409440853<br>owner=prod-t8-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Helix Talent Group | T8-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Halcyon Retail<br>project=Halcyon Monthly Talent Ops<br>erp_user=prod-t8-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t8-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Helix Talent Group | T8-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T8-owner-login.png) |  |
| Helix Talent Group | T8-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T8-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Helix Talent Group | T8-clients | Live route /app/clients | PASS | [screenshot](screenshots/T8-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Helix Talent Group | T8-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T8-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Helix Talent Group | T8-projects | Live route /app/projects | PASS | [screenshot](screenshots/T8-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Helix Talent Group | T8-people | Live route /app/people | PASS | [screenshot](screenshots/T8-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Helix Talent Group | T8-reports | Live route /app/reports | PASS | [screenshot](screenshots/T8-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Helix Talent Group | T8-atlas | Atlas scenario-library prompt | PASS | [screenshot](screenshots/T8-atlas-response.png) | Prompt: Show me Halcyon RPO retainer readiness. Include per-period billing, project staffing, utilization, and month-end reporting implications.<br>Response excerpt:  I'll pull up the Halcyon RPO engagement details for you. Let me query the engagements and related data. <br>Required business signals present.<br>No internal tool terminology detected. |
| Helix Talent Group | T8-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Helix Talent Group | T8-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Brightline Wealth Office | T9-signup | Created tenant through production signup API | PASS |  | tenant_id=84516292-ea3f-4315-b56f-8b43c7bf241f<br>owner=prod-t9-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Brightline Wealth Office | T9-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Ashford Family Office<br>project=Ashford COSEC and Tax Coordination<br>erp_user=prod-t9-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t9-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Brightline Wealth Office | T9-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T9-owner-login.png) |  |
| Brightline Wealth Office | T9-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T9-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Brightline Wealth Office | T9-clients | Live route /app/clients | PASS | [screenshot](screenshots/T9-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Brightline Wealth Office | T9-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T9-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Brightline Wealth Office | T9-projects | Live route /app/projects | PASS | [screenshot](screenshots/T9-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Brightline Wealth Office | T9-people | Live route /app/people | PASS | [screenshot](screenshots/T9-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Brightline Wealth Office | T9-reports | Live route /app/reports | PASS | [screenshot](screenshots/T9-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Brightline Wealth Office | T9-atlas | Atlas scenario-library prompt | PASS | [screenshot](screenshots/T9-atlas-response.png) | Prompt: Show me the Ashford Family Office structure. Include engagements, service lines, billing models, currencies, open projects, privacy risks, and missing setup before billing.<br>Response excerpt:  The Ashford Family Office structure is as follows: Engagement: Ashford Family Office Advisory (ENG-0001) Service Line: COSEC Billing Model: Mixed Currency: GBP Open Projects: - General - Ashford COSEC and Tax Coordination Privacy Risks: No specific privacy risks identified in th<br>Required business signals present.<br>No internal tool terminology detected. |
| Brightline Wealth Office | T9-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Brightline Wealth Office | T9-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |
| Quantum Systems Integration | T10-signup | Created tenant through production signup API | PASS |  | tenant_id=bdfbb386-c900-4124-bd14-f9debb6c09df<br>owner=prod-t10-2026-06-30t06-38-38-owner@aethos-qa.dev |
| Quantum Systems Integration | T10-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Continental Insurance Group<br>project=Continental Workstream A<br>erp_user=prod-t10-2026-06-30t06-38-38-manager@aethos-qa.dev<br>employee=prod-t10-2026-06-30t06-38-38-employee@aethos-qa.dev |
| Quantum Systems Integration | T10-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T10-owner-login.png) |  |
| Quantum Systems Integration | T10-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T10-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Quantum Systems Integration | T10-clients | Live route /app/clients | PASS | [screenshot](screenshots/T10-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Quantum Systems Integration | T10-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T10-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Quantum Systems Integration | T10-projects | Live route /app/projects | PASS | [screenshot](screenshots/T10-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Quantum Systems Integration | T10-people | Live route /app/people | PASS | [screenshot](screenshots/T10-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Quantum Systems Integration | T10-reports | Live route /app/reports | PASS | [screenshot](screenshots/T10-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Quantum Systems Integration | T10-atlas | Atlas scenario-library prompt | PASS | [screenshot](screenshots/T10-atlas-response.png) | Prompt: Run today's finance ops check for Continental and Quantum. Separate read-only findings from actions that need Inbox approval. Include AR, AP, WIP, close, controls, and operational health.<br>Response excerpt:  ### Finance Ops Check Summary (2026-06-30) **Period:** 2026-06 #### **Read-Only Findings** **Financial Position** * **Accounts Receivable (AR):** $0.00 total outstanding. No overdue invoices. * **Accounts Payable (AP):** $0.00 total outstanding. * **Work in Progress (WIP):** $0.<br>Required business signals present.<br>No internal tool terminology detected. |
| Quantum Systems Integration | T10-erp-manager-login | ERP manager login to live Aethos app | FAIL |  | TimeoutError: page.waitForURL: Timeout 90000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
  navigated to "https://aethos.ishirock.tech/app/profile"
============================================================ |
| Quantum Systems Integration | T10-timesheet | Timesheet employee login and time entry | FAIL |  | Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed

Locator: locator('input[type="number"]').first()
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
[2m  - Expect "toBeVisible" with timeout 30000ms[22m
[2m  - waiting for locator('input[type="number"]').first()[22m
 |

## Atlas Response Excerpts

## T1-atlas - Cobalt Consulting Co.

```text
 
I see there are no active engagements in the system. Let me check for all engagements to get a complete picture:

**Riverbend Foods Engagement Structure**

| Field | Value |
|-------|-------|
| **Engagement ID** | `e4bdd206-fb6d-4d9b-82b7-a9feba4725bd` |
| **Engagement Name** | Riverbend Discovery Advisory |
| **Status** | **Draft** (not yet active) |
| **Billing Model** | Time & Materials |
| **Currency** | USD |
| **Total Contract Value** | $25,000.00 |

---

### Projects (2)

| Project ID | Project Name | Unbilled Hours | Avg Rate | WIP Value |
|------------|--------------|----------------|----------|-----------|
| `ae8749ad-5ea6-4aa8-a9fc-6de625962428` | General | 0 | $0/hr | $0.00 |
| `1c18f6e6-cfac-4b94-8b87-be07a2f352e0` | Riverbend Discovery Project | 0 | $0/hr | $0.00 |

---

### Missing Before Billing

1. **Engagement not activated** — Status is **Draft**. Must be moved to **Active** before any billing can occur.
2. **No time logged** — Both projects show 0 unbilled hours and $0 WIP value.
3. **No rate cards visible** — Average rate is $0/hr on both projects; employee billing rates may need to be set (default or engagement-specific).
4. **No billing period defined** — No period start/end dates have been set for invoicing.
5. **No retainers/milestones/expenses recorded** — Nothing to draw down against or invoice for.

---

### Recommended Next Steps
1. **Activate the engagement** (change status from Draft → Active).
2. **Set billing rates** for staff assigned to this engagement (or confirm default rates apply).
3. **Log time** against the "Riverbend Discovery Project" (and "General" if used for admin/overhead).
4. **Define a billing period** (e.g., monthly) and generate the first invoice draft via `draft_invoice`.

Would you like me to help with any of these — e.g., log time, set rates, or prepare a draft invoice once time is recorded?
```

## T2-atlas - Pixel & Pulp Studio

```text
 

**Aurora Cosmetics Milestone Engagement**  
- **Name**: Aurora Web Build SOW  
- **Billing Model**: Milestone (GBP)  
- **Total Value**: £45,000.00  
- **Status**: Draft  

**Projects**:  
1. **General** (Project ID: ef59b556-0acb-44f5-983b-3a746d725c5e)  
2. **Aurora Milestone 1 Build** (Project ID: 101c137f-9506-49a5-a205-8430e3926e12)  

**WIP Readiness**:  
- **Unbilled Hours**: 0.00 (no logged hours for either project)  
- **WIP Value**: £0.00 (no work-in-progress recorded)  

**Missing Setup Before Invoicing**:  
- Engagement status is **draft**, indicating it is not yet active or ready for invoicing.  
- No hours have been logged against the milestone projects, suggesting incomplete setup (e.g., time tracking, milestone approvals, or billing configuration).  
- To proceed with invoicing, ensure:  
  - Time entries are logged against the projects.  
  - Milestone criteria are met and approved.  
  - Engagement status is updated to "active" (if applicable).  

Let me know if you need further details!
```

## T3-atlas - Harborstone Accountants

```text
 

The engagement "Delmont Annual Accounts FY2026" (ID: 0c06d1ce-7779-40e4-9454-e81dfde1f92f) under Delmont Holdings shows:  
- **Billing Terms**: Fixed fee in USD ($18,500.00)  
- **Status**: Draft  
- **Service Line**: Not explicitly detailed in current data  
- **Projects**: No projects listed in current response  
- **Year-End Reporting**: No explicit readiness status provided  

Would you like to explore additional details about this engagement or check for supplementary documentation?
```

## T4-atlas - Vantage Tax Partners

```text
 The Pacific Rim Cross-Border Tax engagement (ENG-0001) is currently in draft status and not yet ready for billing. Here is the readiness review:

Project Setup & Terms
The engagement is correctly configured for Capped T&M with a total value of 38,000 SGD. However, the billing terms are currently empty in the system, which needs to be populated to formalize the cap and payment milestones.

FX Provenance
A specific project for FX Advisory has been created, but there is currently zero WIP or unbilled time logged against it. To ensure FX provenance for cross-border tax, we need to establish the source of the exchange rates being used and ensure time is tracked against this specific project.

Missing Evidence & Billing Blockers
Billing cannot proceed due to the following gaps:
1. Engagement Status: The engagement is still in draft. It must be moved to active status.
2. WIP: There is currently no unbilled value or hours recorded for either the General or FX Advisory projects.
3. Evidence: There is no source document linked to the engagement. We need the signed engagement letter or approved SOW uploaded as audit evidence before the first invoice can be generated.
```

## T6-atlas - Southern Cross Legal

```text
 The Brindabella Retainer Draw is currently in a draft state, meaning the project setup is not yet finalized.

Project Setup: The engagement (ENG-0001) for Brindabella Ventures is listed as a draft with a total value of 60,000 AUD. It is configured as a retainer draw for advisory services, running from June 1 to December 31, 2026.

Retainer Floor Risk: There is currently no WIP value or unbilled hours recorded across the associated projects (General and Brindabella Matter Support), so there is no immediate draw-down risk against the retainer floor.

Invoice Readiness: Because the engagement is still in draft status and there is no accumulated WIP, it is not yet ready for invoicing.

Collection Holds: There are no open or overdue invoices for Brindabella, and no collection hold considerations are present in the current record.
```

## T7-atlas - Atlas Capital Advisors

```text
 
```

## T8-atlas - Helix Talent Group

```text
 
I'll pull up the Halcyon RPO engagement details for you. Let me query the engagements and related data.




```

## T9-atlas - Brightline Wealth Office

```text
 The Ashford Family Office structure is as follows:

Engagement: Ashford Family Office Advisory (ENG-0001)
Service Line: COSEC
Billing Model: Mixed
Currency: GBP

Open Projects:
- General
- Ashford COSEC and Tax Coordination

Privacy Risks: No specific privacy risks identified in the current finance or approval context.

Missing Setup Before Billing:
- Engagement Status: The engagement is currently in draft status and must be finalized/activated before billing can occur.
- Billing Terms: Billing terms are currently null and need to be defined.
- Rate Card: No rate card is associated with the engagement.
```

## T10-atlas - Quantum Systems Integration

```text
 ### Finance Ops Check Summary (2026-06-30)
**Period:** 2026-06

#### **Read-Only Findings**

**Financial Position**
*   **Accounts Receivable (AR):** $0.00 total outstanding. No overdue invoices.
*   **Accounts Payable (AP):** $0.00 total outstanding.
*   **Work in Progress (WIP):** $0.00 unbilled value across 2 projects (Continental Workstream A, General).

**Close Readiness**
*   **Status:** **Ready to Lock**.
*   **Checklist:** All major reconciliations (AR/AP, Trial Balance) and journal reviews are complete. No pending blocking tasks.
*   **Note:** The period is ready for the final lock.

**Operational Health & Controls**
*   **Agent Workflows:** Healthy. Recent Copilot agent runs are active/running.
*   **Capacity:** Underutilization noted for **T10 Employee Tester**.

---

#### **Actions Requiring Inbox Approval**

**Action Queue (High/Medium Priority)**
*   **Practice Review (High):** Review the **Advisory** practice backlog and staffing balance. Recommended action: Run a partner review covering pricing, delivery risk, and staffing.
*   **Staffing Management (Medium):** Address underutilization for **T10 Employee Tester**. Recommended action: Review open work and assign additional billable tasks.
```
