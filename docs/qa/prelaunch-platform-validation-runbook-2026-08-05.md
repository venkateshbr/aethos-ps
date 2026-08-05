# Pre-Launch Platform Validation Runbook — 2026-08-05

## Decision

Production is reachable and every authenticated product route exercised by the
Demo Guide v2 rendered successfully. The current retained tenant is useful for
platform exploration, but the published Meridian Demo Guide v2 is **not ready
to present verbatim** against that tenant.

The first production browser pass recorded 58 passes and 8 failures across 66
checks. The automatic retry recorded 57 passes and 9 failures. The failures are
concentrated in scenario-data mismatch, time-entry handling, R2R prompt
sequencing, and one visible internal tool-call card.

Do not represent a failing guide step as shipped behavior. Use the Sterling
Bridge records that exist, or provision a disposable tenant with the complete
Meridian fixture before a customer demo.

## Production tenant inventory

Inventory was read directly from the production `tenants` table with the
service role on 2026-08-05. No tenant or user was created during inventory.

| Item | Observed state |
| --- | --- |
| Active tenants | 1 |
| Retained tenant | Sterling Bridge Advisory Group |
| Tenant status / tier | active / starter |
| Subscription state | Database says `trialing`; trial ended 2026-08-03 and the UI displays **Trial ended** |
| Stripe Connect | not connected; charges and payouts disabled |
| Created | 2026-07-20 |
| Active ERP users | 2: one owner and one viewer |

The old Meridian and multi-scenario tenants listed in local historical
credential manifests are not present in the current production tenant table.

The expired-trial state is internally inconsistent and unsuitable for an
unqualified customer demo. It is tracked in
[#481 — Reconcile expired trial status and demo-tenant access state](https://github.com/venkateshbr/aethos-ps/issues/481).

### Retained tenant data profile

| Record | Count before this validation |
| --- | ---: |
| Clients | 14 |
| Employees | 0 |
| Engagements | 6 |
| Projects | 12 |
| Time entries | 0 |
| Project expenses | 0 |
| Invoices | 7 |
| Bills | 2 |
| Payments | 3 |
| Journal entries | 15 |
| Tax rates | 3 |

The absence of employees, time entries, project expenses, and Meridian-named
records explains several guide failures. Nous correctly found Sterling records
instead of inventing Nexus records, but the guide acceptance assertions still
failed because the required fixture was absent.

## Guide review

### Platform User Guide

The route map and current product-boundary wording match the Angular route
table. The guide correctly identifies `/app/*` authenticated routes and warns
that standalone routes such as `/copilot`, `/payments`, `/reports/ar-aging`,
and `/settings/stripe` are not current routes.

The guide should remain the product operating reference. It is not a guarantee
that a particular demo fixture exists.

### Demo Guide v1

`docs/DEMO_GUIDE.md` is already marked as archived. It contains historical
routes, seed data, prices, and workflow claims and must not be used for a live
production demo.

### Demo Guide v2

`docs/DEMO_GUIDE_v2.md` is the maintained scenario script, but its named firm
and fixture are Meridian Advisory Group. Production currently retains Sterling
Bridge Advisory Group. The guide's Nexus, Brightwater, Alderton, Thornton,
Alice Chen, and `BILL-1001` steps therefore cannot be validated literally
without provisioning the matching fixture.

Tracking issue: [#479 — Align production demo fixture with Demo Guide v2](https://github.com/venkateshbr/aethos-ps/issues/479).

## Browser evidence

Canonical evidence from the first complete pass:

- [Human-readable report](demo-v2-production-2026-08-05T07-36-11-138Z/report.md)
- [Machine-readable results](demo-v2-production-2026-08-05T07-36-11-138Z/results.json)
- Screenshots are stored beside the report under `screenshots/`.

The run authenticated through the public login form, visited every guide
surface, sent the real guide prompts, uploaded the three real demo PDFs, and
checked the resulting Inbox, Documents, and Settings surfaces.

### Route coverage

All 18 checked surfaces passed without visible load failures:

1. Nous
2. Documents
3. Inbox
4. Engagements
5. Projects
6. Invoices
7. Contacts
8. Expenses
9. Bills
10. Pay Bills / Billing Runs
11. Time
12. Approvals
13. Payments
14. People
15. Reports
16. Accounting / Journals
17. Settings
18. Timesheet portal

There were no browser console errors. Three aborted requests were captured on
the first pass: subscription status, chat-thread list, and a Google font. They
occurred during navigation and did not produce a visible route failure.

### Prompt failures

| Prompt | Result | Interpretation / tracking |
| --- | --- | --- |
| 1-2 engagement structure | Failed twice | Nexus is absent from Sterling; read-pack completeness remains tracked in #360. |
| 1-3 log time | Failed twice | The supplied prompt fields were rejected as missing; tracked in #359. |
| 1-3A delivery data | Passed, then failed retry | No Alice/Nexus fixture and nondeterministic resource lookup; tracked in #359 and #479. |
| 1-4 billing run | Failed twice | Nexus and its billable time/expenses are absent; tracked in #479. |
| 2-4 single-bill drilldown | Failed twice | `BILL-1001` is absent and the response fell back to generic intake guidance; tracked in #360/#479. |
| 3-4 COSEC reminders | Failed twice | Alderton calendar data is absent; tracked in #360/#479. |
| 5-5 management pack | Failed twice | Returned a pre-close checklist instead of the requested comparative pack; tracked in #357. |
| 5-5 blocker drilldown | Failed twice | Returned the prior management-pack result instead of owners/actions; tracked in #357. |
| 6-1 action plan | Failed twice | Business answer and Inbox task were correct, but an internal tool card was visible; tracked in #480. |

Tracking issue: [#480 — Hide internal tool-call cards from end users](https://github.com/venkateshbr/aethos-ps/issues/480).

## Credentials and secure handoff

The active Sterling Bridge credentials are already present in the workspace at
the repository root:

`sterlingbridge_e2e_credentials.json`

This file is ignored by Git through `*_credentials.json` and must remain mode
`0600`. It contains two active accounts:

- Managing Partner / Tenant Owner
- Executive Viewer

Do not copy the email addresses or passwords into this runbook, a GitHub issue,
chat, screenshots, commits, or a shared deck. Open the local manifest directly
or import its values into an approved password manager. To inspect the account
labels without exposing credentials:

```bash
jq '.accounts | map({code, label, status})' sterlingbridge_e2e_credentials.json
```

For Playwright, the owner login is mirrored in the ignored file
`frontend/e2e/.auth/o2c-tenant.meta.json`; the tenant ID matches the retained
Sterling Bridge tenant. The storage-state files under `frontend/e2e/.auth/` are
also local-only session artifacts.

After the founder validates, rotate both passwords and update the ignored
manifest. Never reuse these credentials for a real customer tenant.

## Founder validation walkthrough

1. Confirm the credential manifest is local and protected:

   ```bash
   git check-ignore -v sterlingbridge_e2e_credentials.json
   stat -f '%Sp %N' sterlingbridge_e2e_credentials.json
   ```

2. Open `https://aethos.ishirock.tech/login` and sign in as the Tenant Owner
   using the local manifest.
3. Visit each route in the route-coverage list. Confirm the firm is Sterling
   Bridge and no visible loading error appears. Record the **Trial ended** badge;
   do not describe the subscription as active until #481 is resolved.
4. In Reports, verify June 2026 figures and journal drilldowns against the
   source modules. Do not use Meridian client names.
5. In Nous, start a new chat and ask for the active engagement list. Use one of
   the returned Sterling client names for follow-up prompts.
6. Upload one approved fictional demo PDF. Confirm it remains attached until
   the business prompt is sent, then verify its Document and Inbox evidence.
7. Ask for a read-only finance-ops check. Confirm the response uses business
   language and displays no internal tool cards, tool names, payloads, context
   references, or provider errors.
8. Explicitly sign out. Sign in as Executive Viewer and verify reporting reads
   work while mutation and approval controls are unavailable or denied.
9. Sign out and record the date, account role, observed result, and screenshot
   in a new dated QA report. Do not record credentials.

## Automated rerun

Run from `frontend/`:

```bash
AETHOS_RUN_PRODUCTION_VALIDATION=true \
AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech \
CI=1 \
npx playwright test e2e/demo-v2-production-validation.spec.ts --project=chromium
```

Expected release gate: both the initial run and retry complete with zero
critical failures. Until #479 is resolved, this exact test is expected to fail
against Sterling because it asserts the Meridian fixture.

## Production-state note

The two-pass validation uploaded the three fictional demo PDFs twice and
created reviewed Finance Ops action-plan Inbox tasks. These are intentional QA
artifacts in the retained demo tenant. Do not delete them until the founder has
reviewed the evidence. Afterwards, remove them through the product's governed
UI or the documented tenant cleanup procedure, never through an ad-hoc database
delete.
