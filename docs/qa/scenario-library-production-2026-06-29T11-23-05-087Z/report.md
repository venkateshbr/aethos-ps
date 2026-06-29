# Aethos PS Test Scenario Library Production Run

Run ID: `2026-06-29T11-23-05-087Z`
Base URL: `https://aethos.ishirock.tech`
Timesheet URL: `https://timesheet.aethos.ishirock.tech`
Generated: `2026-06-29T11:27:07.156Z`

Summary: PASS 116, WARN 0, FAIL 10, SKIP 0

## Scope

- Created all 10 scenario-library tenants through the deployed signup API.
- Created one signature client, engagement, active project, invited timesheet employee, and project assignment per tenant through authenticated product APIs.
- Created one ERP manager user per tenant through the tenant-user administration API.
- Validated live owner login, ERP manager login, key app routes, one Atlas business prompt per tenant, and independent timesheet login/time submission per tenant.
- This run does not direct-write to the database and does not use backend seed scripts.

## Known Blocked Coverage

- Tenant-user invite exists and is used for one ERP manager per tenant.
- Employee invite exists and was used for independent timesheet portal validation.
- Auditor-specific persona remains mapped to the read-only viewer role until a distinct auditor role is added.

## Evidence Table

| Tenant | ID | Action | Status | Screenshot | Notes |
| --- | --- | --- | --- | --- | --- |
| Cobalt Consulting Co. | T1-signup | Created tenant through production signup API | PASS |  | tenant_id=cc5a95c9-a4ba-4542-8573-fceca3ace26f<br>owner=prod-t1-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Cobalt Consulting Co. | T1-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Riverbend Foods<br>project=Riverbend Discovery Project<br>erp_user=prod-t1-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t1-2026-06-29t11-23-05-employee@aethos-qa.dev |
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
| Cobalt Consulting Co. | T1-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T1-atlas-response.png) | Prompt: Show me the Riverbend Foods engagement structure. List active projects, billing model, linked source data, and anything missing before billing.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Riverbend, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Cobalt Consulting Co. | T1-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T1-erp-manager-login.png) | Manager prod-t1-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Cobalt Consulting Co. | T1-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T1-timesheet-submitted.png) | Employee prod-t1-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Pixel & Pulp Studio | T2-signup | Created tenant through production signup API | PASS |  | tenant_id=72e4346c-adfd-46b2-a89f-1322e7f918e6<br>owner=prod-t2-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Pixel & Pulp Studio | T2-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Aurora Cosmetics<br>project=Aurora Milestone 1 Build<br>erp_user=prod-t2-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t2-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Pixel & Pulp Studio | T2-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T2-owner-login.png) |  |
| Pixel & Pulp Studio | T2-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T2-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Pixel & Pulp Studio | T2-clients | Live route /app/clients | PASS | [screenshot](screenshots/T2-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Pixel & Pulp Studio | T2-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T2-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Pixel & Pulp Studio | T2-projects | Live route /app/projects | PASS | [screenshot](screenshots/T2-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Pixel & Pulp Studio | T2-people | Live route /app/people | PASS | [screenshot](screenshots/T2-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Pixel & Pulp Studio | T2-reports | Live route /app/reports | PASS | [screenshot](screenshots/T2-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Pixel & Pulp Studio | T2-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T2-atlas-response.png) | Prompt: Show me the Aurora Cosmetics milestone engagement. Include projects, milestone billing model, WIP readiness, and missing setup before invoicing.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Aurora, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Pixel & Pulp Studio | T2-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T2-erp-manager-login.png) | Manager prod-t2-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Pixel & Pulp Studio | T2-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T2-timesheet-submitted.png) | Employee prod-t2-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Harborstone Accountants | T3-signup | Created tenant through production signup API | PASS |  | tenant_id=014909ad-505e-4ea0-af83-3e9aac4b661a<br>owner=prod-t3-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Harborstone Accountants | T3-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Delmont Holdings<br>project=Delmont Accounts Drafting<br>erp_user=prod-t3-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t3-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Harborstone Accountants | T3-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T3-owner-login.png) |  |
| Harborstone Accountants | T3-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T3-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Harborstone Accountants | T3-clients | Live route /app/clients | PASS | [screenshot](screenshots/T3-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Harborstone Accountants | T3-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T3-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Harborstone Accountants | T3-projects | Live route /app/projects | PASS | [screenshot](screenshots/T3-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Harborstone Accountants | T3-people | Live route /app/people | PASS | [screenshot](screenshots/T3-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Harborstone Accountants | T3-reports | Live route /app/reports | PASS | [screenshot](screenshots/T3-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Harborstone Accountants | T3-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T3-atlas-response.png) | Prompt: Show me the Delmont Holdings annual accounts engagement. Include service line, billing terms, projects, and year-end reporting readiness.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Delmont, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Harborstone Accountants | T3-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T3-erp-manager-login.png) | Manager prod-t3-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Harborstone Accountants | T3-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T3-timesheet-submitted.png) | Employee prod-t3-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Vantage Tax Partners | T4-signup | Created tenant through production signup API | PASS |  | tenant_id=ad66506d-fc37-45f5-93ab-a98b8188076a<br>owner=prod-t4-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Vantage Tax Partners | T4-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Pacific Rim Holdings<br>project=Pacific Rim FX Advisory<br>erp_user=prod-t4-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t4-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Vantage Tax Partners | T4-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T4-owner-login.png) |  |
| Vantage Tax Partners | T4-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T4-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Vantage Tax Partners | T4-clients | Live route /app/clients | PASS | [screenshot](screenshots/T4-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Vantage Tax Partners | T4-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T4-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Vantage Tax Partners | T4-projects | Live route /app/projects | PASS | [screenshot](screenshots/T4-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Vantage Tax Partners | T4-people | Live route /app/people | PASS | [screenshot](screenshots/T4-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Vantage Tax Partners | T4-reports | Live route /app/reports | PASS | [screenshot](screenshots/T4-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Vantage Tax Partners | T4-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T4-atlas-response.png) | Prompt: Review Pacific Rim cross-border tax readiness. Include FX provenance needs, capped T&M terms, project setup, and missing evidence before billing.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Pacific, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Vantage Tax Partners | T4-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T4-erp-manager-login.png) | Manager prod-t4-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Vantage Tax Partners | T4-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T4-timesheet-submitted.png) | Employee prod-t4-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Indus Engineering Advisory | T5-signup | Created tenant through production signup API | PASS |  | tenant_id=f6802da4-db0d-4592-bd21-d795af8ee401<br>owner=prod-t5-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Indus Engineering Advisory | T5-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Deccan Metro Authority<br>project=Deccan Metro Phase 1 PMO<br>erp_user=prod-t5-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t5-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Indus Engineering Advisory | T5-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T5-owner-login.png) |  |
| Indus Engineering Advisory | T5-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T5-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Indus Engineering Advisory | T5-clients | Live route /app/clients | PASS | [screenshot](screenshots/T5-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Indus Engineering Advisory | T5-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T5-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Indus Engineering Advisory | T5-projects | Live route /app/projects | PASS | [screenshot](screenshots/T5-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Indus Engineering Advisory | T5-people | Live route /app/people | PASS | [screenshot](screenshots/T5-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Indus Engineering Advisory | T5-reports | Live route /app/reports | PASS | [screenshot](screenshots/T5-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Indus Engineering Advisory | T5-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T5-atlas-response.png) | Prompt: Show me Deccan Metro PMO delivery and billing readiness. Include milestone program setup, procurement risks, WIP, and AP controls to verify.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Deccan, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Indus Engineering Advisory | T5-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T5-erp-manager-login.png) | Manager prod-t5-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Indus Engineering Advisory | T5-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T5-timesheet-submitted.png) | Employee prod-t5-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Southern Cross Legal | T6-signup | Created tenant through production signup API | PASS |  | tenant_id=9d76adfa-cfe5-4a14-8ec5-2e564ecbc17f<br>owner=prod-t6-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Southern Cross Legal | T6-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Brindabella Ventures<br>project=Brindabella Matter Support<br>erp_user=prod-t6-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t6-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Southern Cross Legal | T6-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T6-owner-login.png) |  |
| Southern Cross Legal | T6-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T6-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Southern Cross Legal | T6-clients | Live route /app/clients | PASS | [screenshot](screenshots/T6-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Southern Cross Legal | T6-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T6-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Southern Cross Legal | T6-projects | Live route /app/projects | PASS | [screenshot](screenshots/T6-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Southern Cross Legal | T6-people | Live route /app/people | PASS | [screenshot](screenshots/T6-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Southern Cross Legal | T6-reports | Live route /app/reports | PASS | [screenshot](screenshots/T6-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Southern Cross Legal | T6-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T6-atlas-response.png) | Prompt: Show me Brindabella retainer-draw status. Include project setup, retainer floor risk, invoice readiness, and any collection hold considerations.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Brindabella, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Southern Cross Legal | T6-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T6-erp-manager-login.png) | Manager prod-t6-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Southern Cross Legal | T6-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T6-timesheet-submitted.png) | Employee prod-t6-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Atlas Capital Advisors | T7-signup | Created tenant through production signup API | PASS |  | tenant_id=bac8461d-04e8-4022-82ac-62fd460c2dfc<br>owner=prod-t7-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Atlas Capital Advisors | T7-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Redwood Industrials<br>project=Redwood Deal Execution<br>erp_user=prod-t7-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t7-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Atlas Capital Advisors | T7-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T7-owner-login.png) |  |
| Atlas Capital Advisors | T7-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T7-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Atlas Capital Advisors | T7-clients | Live route /app/clients | PASS | [screenshot](screenshots/T7-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Atlas Capital Advisors | T7-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T7-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Atlas Capital Advisors | T7-projects | Live route /app/projects | PASS | [screenshot](screenshots/T7-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Atlas Capital Advisors | T7-people | Live route /app/people | PASS | [screenshot](screenshots/T7-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Atlas Capital Advisors | T7-reports | Live route /app/reports | PASS | [screenshot](screenshots/T7-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Atlas Capital Advisors | T7-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T7-atlas-response.png) | Prompt: Review Redwood sell-side M&A billing readiness. Include success-fee milestone logic, approval boundary, FX considerations, and evidence needed before invoicing.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Redwood, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Atlas Capital Advisors | T7-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T7-erp-manager-login.png) | Manager prod-t7-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Atlas Capital Advisors | T7-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T7-timesheet-submitted.png) | Employee prod-t7-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Helix Talent Group | T8-signup | Created tenant through production signup API | PASS |  | tenant_id=f1f078bb-4f0f-492c-b3d7-86654aeaf701<br>owner=prod-t8-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Helix Talent Group | T8-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Halcyon Retail<br>project=Halcyon Monthly Talent Ops<br>erp_user=prod-t8-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t8-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Helix Talent Group | T8-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T8-owner-login.png) |  |
| Helix Talent Group | T8-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T8-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Helix Talent Group | T8-clients | Live route /app/clients | PASS | [screenshot](screenshots/T8-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Helix Talent Group | T8-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T8-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Helix Talent Group | T8-projects | Live route /app/projects | PASS | [screenshot](screenshots/T8-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Helix Talent Group | T8-people | Live route /app/people | PASS | [screenshot](screenshots/T8-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Helix Talent Group | T8-reports | Live route /app/reports | PASS | [screenshot](screenshots/T8-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Helix Talent Group | T8-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T8-atlas-response.png) | Prompt: Show me Halcyon RPO retainer readiness. Include per-period billing, project staffing, utilization, and month-end reporting implications.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Halcyon, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Helix Talent Group | T8-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T8-erp-manager-login.png) | Manager prod-t8-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Helix Talent Group | T8-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T8-timesheet-submitted.png) | Employee prod-t8-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Brightline Wealth Office | T9-signup | Created tenant through production signup API | PASS |  | tenant_id=72156db1-7c77-494f-b0fe-ccd368526536<br>owner=prod-t9-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Brightline Wealth Office | T9-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Ashford Family Office<br>project=Ashford COSEC and Tax Coordination<br>erp_user=prod-t9-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t9-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Brightline Wealth Office | T9-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T9-owner-login.png) |  |
| Brightline Wealth Office | T9-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T9-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Brightline Wealth Office | T9-clients | Live route /app/clients | PASS | [screenshot](screenshots/T9-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Brightline Wealth Office | T9-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T9-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Brightline Wealth Office | T9-projects | Live route /app/projects | PASS | [screenshot](screenshots/T9-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Brightline Wealth Office | T9-people | Live route /app/people | PASS | [screenshot](screenshots/T9-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Brightline Wealth Office | T9-reports | Live route /app/reports | PASS | [screenshot](screenshots/T9-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Brightline Wealth Office | T9-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T9-atlas-response.png) | Prompt: Show me the Ashford Family Office structure. Include engagements, service lines, billing models, currencies, open projects, privacy risks, and missing setup before billing.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Ashford, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Brightline Wealth Office | T9-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T9-erp-manager-login.png) | Manager prod-t9-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Brightline Wealth Office | T9-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T9-timesheet-submitted.png) | Employee prod-t9-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |
| Quantum Systems Integration | T10-signup | Created tenant through production signup API | PASS |  | tenant_id=5cdd8b50-e257-40df-85cd-d8d5ec3902b9<br>owner=prod-t10-2026-06-29t11-23-05-owner@aethos-qa.dev |
| Quantum Systems Integration | T10-master-data | Created signature client, engagement, project, employee login, and project assignment | PASS |  | client=Continental Insurance Group<br>project=Continental Workstream A<br>erp_user=prod-t10-2026-06-29t11-23-05-manager@aethos-qa.dev<br>employee=prod-t10-2026-06-29t11-23-05-employee@aethos-qa.dev |
| Quantum Systems Integration | T10-owner-login | Owner login to live app | PASS | [screenshot](screenshots/T10-owner-login.png) |  |
| Quantum Systems Integration | T10-copilot | Live route /app/copilot | PASS | [screenshot](screenshots/T10-copilot.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle add New chat No |
| Quantum Systems Integration | T10-clients | Live route /app/clients | PASS | [screenshot](screenshots/T10-clients.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Contacts Compan |
| Quantum Systems Integration | T10-engagements | Live route /app/engagements | PASS | [screenshot](screenshots/T10-engagements.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Engagements All |
| Quantum Systems Integration | T10-projects | Live route /app/projects | PASS | [screenshot](screenshots/T10-projects.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Projects All pr |
| Quantum Systems Integration | T10-people | Live route /app/people | PASS | [screenshot](screenshots/T10-people.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle People Your tea |
| Quantum Systems Integration | T10-reports | Live route /app/reports | PASS | [screenshot](screenshots/T10-reports.png) | Body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Quantum Systems Integration | T10-atlas | Atlas scenario-library prompt | FAIL | [screenshot](screenshots/T10-atlas-response.png) | Prompt: Run today's finance ops check for Continental and Quantum. Separate read-only findings from actions that need Inbox approval. Include AR, AP, WIP, close, controls, and operational health.<br>Response excerpt:  Atlas is temporarily unavailable. Please try again.<br>Missing required response signals: Continental, engagement/project/billing/finance/WIP/readiness<br>No internal tool terminology detected. |
| Quantum Systems Integration | T10-erp-manager-login | ERP manager login to live Aethos app | PASS | [screenshot](screenshots/T10-erp-manager-login.png) | Manager prod-t10-2026-06-29t11-23-05-manager@aethos-qa.dev logged in independently.<br>Reports body excerpt: Aethos auto_awesome Atlas upload_file Documents inbox Inbox work Engagements folder_open Projects receipt Invoices bar_chart Reports More expand_more account_circle Reports AR Agin |
| Quantum Systems Integration | T10-timesheet | Timesheet employee login and time entry | PASS | [screenshot](screenshots/T10-timesheet-submitted.png) | Employee prod-t10-2026-06-29t11-23-05-employee@aethos-qa.dev logged in independently and submitted 2.5 hours. |

## Atlas Response Excerpts

## T1-atlas - Cobalt Consulting Co.

```text
 Atlas is temporarily unavailable. Please try again.
```

## T2-atlas - Pixel & Pulp Studio

```text
 Atlas is temporarily unavailable. Please try again.
```

## T3-atlas - Harborstone Accountants

```text
 Atlas is temporarily unavailable. Please try again.
```

## T4-atlas - Vantage Tax Partners

```text
 Atlas is temporarily unavailable. Please try again.
```

## T5-atlas - Indus Engineering Advisory

```text
 Atlas is temporarily unavailable. Please try again.
```

## T6-atlas - Southern Cross Legal

```text
 Atlas is temporarily unavailable. Please try again.
```

## T7-atlas - Atlas Capital Advisors

```text
 Atlas is temporarily unavailable. Please try again.
```

## T8-atlas - Helix Talent Group

```text
 Atlas is temporarily unavailable. Please try again.
```

## T9-atlas - Brightline Wealth Office

```text
 Atlas is temporarily unavailable. Please try again.
```

## T10-atlas - Quantum Systems Integration

```text
 Atlas is temporarily unavailable. Please try again.
```
