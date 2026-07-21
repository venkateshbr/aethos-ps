# Ishantech Production End-to-End Runbook — 2026-07-11 (updated 2026-07-12)

Status: PREFLIGHT AND DEDICATED PLAYWRIGHT HARNESS COMPLETE; BRANCH RELEASE
VERIFICATION IS BLOCKED AT THE UNAPPLIED MIGRATION-0102 GATE; EXACT-SHA
DEPLOYMENT AND PRODUCTION EXECUTION PENDING. Production Ishantech mutation
remains NOT RUN and no Ishantech production tenant or business record has been
created. The run will use real Chromium UI automation in one recorded
BrowserContext for the tenant; an in-app Browser is not required.

Purpose: create a new fictional tenant through the public UI, exercise every
configured tenant-visible role, run engagement-to-cash, procure-to-pay, and
record-to-report through three monthly closes, and prove the Q2 financial
statements against deterministic accounting oracles.

This document is both the execution script and evidence index for issue #368.
A blank Actual, ID, or Evidence cell means the step has not been executed. Do
not convert an expected result into PASS without primary evidence.

## 1. Run control record

| Field | Required value | Actual |
| --- | --- | --- |
| Production URL | https://aethos.ishirock.tech/ | Confirmed canonical host |
| Run ID | ISH-E2E-20260711 | |
| Execution date/timezone | 2026-07-12 / Asia/Singapore | Preflight and branch verification only; production browser run not started |
| Test company | Ishantech Advisory Pte. Ltd. | |
| Country/base currency | Singapore / SGD | |
| Fiscal calendar | January–December | |
| Test period | 2026-04-01 through 2026-06-30 (Q2 2026) | |
| Branch | chore/368-launch-readiness-ishantech | |
| Commit SHA | <sha> | |
| Deployed build/version | <build ID and SHA> | |
| Tester | <name> | |
| Tenant ID | <production tenant UUID> | |
| Subscription/customer IDs | <redacted Stripe test-mode IDs> | |
| Email provider mode | Test/sandbox; owned ishirock.tech aliases only | |
| Stripe mode | Test mode only | |
| Worker/version health | <URL, timestamp, result> | Current deployment `/health/ready` 200 but does not expose SHA. The release branch adds exact `build_sha`, required-queue, DB, and secret-free Stripe-mode proof; production execution is gated on those values. |
| Evidence root | Redacted: docs/qa/ishantech-production-e2e-2026-07-11/; private recording: ishantech_e2e_private_evidence/ISH-E2E-20260711/ | |
| GitHub issue/PR | #368 / <PR URL> | |

Stop before signup if the browser origin differs from
`https://aethos.ishirock.tech/`, if TLS is invalid, or if Stripe is not visibly
in test mode.

### Supplemental branch verification completed

The results below validate the current branch and isolated test harness only.
They are not the production Ishantech run, do not populate any Actual/ID/Evidence
cell below, and cannot change a production workflow from NOT RUN to PASS.

| Check | Verified branch result | Remaining limit |
| --- | --- | --- |
| Backend unit/property and lint | `1226 passed, 2 expected xfails` ([#103](https://github.com/venkateshbr/aethos-ps/issues/103)); 79.56% exact coverage; Ruff clean | One Starlette/httpx deprecation warning; reporting agent and FX refresh worker have 0% unit coverage; branch-only, not deployed production evidence |
| Real-stack API | Latest full run: `209 passed, 5 failed, 1 expected xfail` in 268.12 seconds; refreshed focused close-package and exact-denial checks passed afterward | Three approval tests intentionally return HTTP 503 until migration 0102 is deployed; 98 dependency warnings; API evidence is not production browser E2E |
| Frontend unit/typecheck/build | Clean `npm ci`; `71/71` tests; app, spec, and timesheet TypeScript typechecks; both production builds passed | Main bundle is 671.50 kB and triggers its budget warning; optional-chain and Sass warnings remain |
| Current full local Chromium release run | `128 passed, 18 failed, 3 skipped, 4 did not run` in 13.6 minutes; teardown verified two run-scoped tenants deleted | Twelve failures stop at migration 0102. Six deterministic mocks/labels were repaired and the affected enterprise suites passed `11/11`; full clean rerun requires the deployment migration. |
| Prior clean local Chromium history | `151 passed, 2 production-only specs skipped, 0 failed, 0 flaky` in 13.5 minutes | Historical 2026-07-11 result predates the current document-FX and exact-privilege changes |
| Full local Chromium release run (older pre-repair history) | `126 passed, 11 failed, 1 flaky, 3 skipped, 12 did not run` in 21.1 minutes | Historical failure/repair evidence only |
| Focused R2R/period/P2P/operations | Period-lock reason, AI chat mocks/selectors, and operational-health harness were repaired; focused R2R, period, P2P, and ops checks passed | Targeted branch evidence only; AI chat mocks are supplemental |
| Signup plus action-plan | Isolated flow passed `3/3` | Targeted branch evidence, not production E2E |
| Signup plus bill-pay | Isolated flow passed `3/3` | Targeted branch evidence, not production E2E |
| Remaining isolated workflows and log-time repair | Initial batch passed `8/9`, with log-time failing. After the UI consumed `tool_start` and `tool_result` stream events, the unchanged signup plus log-time flow passed `3/3` in 22.3 seconds | Targeted historical repair evidence; current full release gate remains migration-blocked |
| Daily finance | Isolated flow passed `3/3` | Targeted branch evidence, not production E2E |
| Signup plus timesheet | First run exposed the missing standalone forced-password-change flow and a dev-server overlay. After the branch product fix, the unchanged rerun passed `21/21` in 1.3 minutes with browser-driven temporary-password rotation, Bob and Carol time, approval/rejection, and the billing gate; teardown cleaned one owned tenant | The completion endpoint still trusts the client's changed-password claim; production security retest remains open |
| Signup plus S0 password proof | Typecheck passed; focused flow passed `5/5` in 28.4 seconds; browser proof rejects old temporary passwords and accepts unique replacement passwords; teardown cleaned one run-scoped tenant | Positive/negative visible behavior passes, but the completion endpoint trust boundary remains open in [#375](https://github.com/venkateshbr/aethos-ps/issues/375) |
| Meridian soft coverage | Latest artifact: `16 PASS / 0 FAIL / 27 SKIP`, then incorrect `Verdict: PASS`; branch reporter now emits `INCOMPLETE` for any skip and labels master data as reference-only | Deterministic fixtures and a clean rerun are still missing, so this remains non-gating soft coverage |
| Invoice-list inspection | Invoice records render | No visible Client column; client-level review gap remains ([#387](https://github.com/venkateshbr/aethos-ps/issues/387)) |
| Playwright isolation and teardown ([#386](https://github.com/venkateshbr/aethos-ps/issues/386)) | Exclusive-lock contention fails before signup/mutation; run ownership, mode-0600 state, positive cleanup, and owned-tenant teardown were verified | Full release rerun remains required |
| Provider/transport log suppression ([#374](https://github.com/venkateshbr/aethos-ps/issues/374)) | Focused regression covers `uvicorn.access`, `httpx`, `httpcore`, `hpack`, `stripe`, and `urllib3` | Partial privacy fix only; classified-field, document/OCR, model-context, trace/artifact, and provider-retention gaps remain open |

The current full local run verified two run-scoped Playwright tenants deleted.
Nine historical `acme/bravo-aksha-*` API-fixture tenants remain active pending
explicit cleanup approval; future API fixture cleanup now uses verified soft
deletion and raises on failure. The queue also contains 372 unattempted `cron`
jobs pending separately approved maintenance. Meridian's skipped cases do not
add coverage or cleanup evidence. No production Ishantech credentials were
consumed and no production Ishantech business record was mutated. Start SU-01
only after the exact reviewed SHA is deployed and the dedicated production
Playwright preflight passes on
`https://aethos.ishirock.tech/`.

## 2. Safety, evidence, and execution rules

1. Use only fictional data. Never use a real customer, vendor, employee, bank
   account, tax identifier, or payment instrument.
2. Use Stripe test instruments only. Do not submit a payment to a bank or other
   live payment rail.
3. Send mail only to owned ishirock.tech aliases. Verify suppression/sandbox
   behavior before any bulk invite or reminder action.
4. Perform **every** signup, configuration, user/role, master-data,
   transaction, approval, payment, close, lock, and report action through the
   visible production browser UI exactly as an end user would. Browser
   automation may click and type, but it must not use Playwright request APIs,
   service-role calls, SQL, backend scripts, or direct storage writes to create,
   change, approve, or seed state.
5. API or database access is allowed only as a read-only reconciliation after a
   successful browser action. Record the query and result; it may corroborate
   the UI but cannot create a prerequisite or turn a browser failure into PASS.
   If a required action has no visible UI, mark that step **BLOCKED — NO UI**,
   capture the missing surface, and file an issue. Do not bypass it.
6. API-seeded, route-intercepted, or direct-callback Playwright tests are
   supplemental contract evidence only. They do not count as this real E2E.
7. For each write, capture the resulting record ID, status, journal/event IDs,
   and downstream report effect. A page render or an Atlas response containing
   keywords is not proof that a transaction occurred.
8. Use one continuous browser context per tenant so the complete journey is a
   single recording. Log out through the visible UI between roles, sign in
   sequentially with each independent account, and never inject or reuse a
   different user's storage state.
9. Record HTTP 4xx/5xx, console errors, worker failures, timeouts, and retries.
   A controlled expected 4xx can pass; an unexplained 5xx cannot.
10. Prefix all names, references, invoice descriptions, and journal reasons with
   ISH-E2E-20260711 so retained test data is searchable.
11. Preserve the tenant and all tagged records after the run, as approved by the
   requester. Do not delete or anonymize them unless separately instructed.
12. Never commit passwords, session state, bearer tokens, payment secrets,
    complete auth responses, or unredacted screenshots.

### Evidence convention

Use evidence filenames of the form STEP-ID-short-description.png or
STEP-ID-response-redacted.json. The continuous video and trace are the primary
before/during/after evidence; the runner also writes a masked post-step
screenshot and a private transaction checkpoint. For every business
transaction preserve:

- the input/form and submission action in the continuous trace/video;
- the success/detail page with the record ID or reference;
- the corresponding journal, financial event, or webhook record;
- the affected aging/report/close surface;
- browser console and network status when an error or unexpected retry occurs.

The primary evidence must show the visible browser action and visible result.
A read-only API/DB reconciliation is labeled SUPPLEMENTAL and linked after the
browser evidence. Any record created by API/DB setup invalidates that workflow
as a browser-only E2E result and requires a fresh browser-created record.

Redact tokens, passwords, Stripe secrets, complete email addresses, cookies,
authorization headers, and private document contents. Keep timestamps, tenant
ID, record IDs, amounts, currency, status, and actor role visible.

### Continuous recording and replay artifacts

Run only `frontend/e2e/ishantech-production-ui.spec.ts` with
`frontend/playwright.production-ui.config.ts`. The dedicated config has no
global setup or teardown, one worker, zero retries, one test, video and trace
always on, an exact-host/SHA/run-ID gate, and explicit production-mutation
consent. It retains the tenant and refuses to run under the ordinary Playwright
configuration.

The private ignored directory contains the complete video, Playwright trace,
HTML report, JUnit/JSON results, per-step masked screenshots, persisted source
identifiers/statuses, and a timestamped execution ledger. Keep it mode 0700
(files 0600 where practical). The Tenant Users and People invite secrets are
visually blurred before their success surfaces appear; the raw trace still
remains private because DOM snapshots may contain sensitive values. Only
redacted screenshots and the redacted execution summary may be copied into Git
or GitHub.

From `frontend/`, execute the retained run only after the exact SHA is live:

~~~bash
AETHOS_RUN_ISHANTECH_PRODUCTION_UI=I_UNDERSTAND_THIS_MUTATES_PRODUCTION \
AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
AETHOS_EXPECTED_DEPLOY_SHA=<40-character deployed Git SHA> \
AETHOS_ISHANTECH_RUN_ID=ISH-E2E-20260711 \
npx playwright test \
  --config=playwright.production-ui.config.ts \
  --project=chromium \
  --workers=1 \
  --retries=0
~~~

The runner itself sets headed Chromium, a 1440x900 viewport, and slow motion so
the recording remains human-reviewable. Do not add the ordinary config, setup,
or teardown to this command.

The mutation run is intentionally non-resumable: one tenant must correspond to
one continuous BrowserContext and recording. If Chromium or the runner exits,
preserve the partial tenant, credentials, trace, and checkpoint; do not replay
irreversible actions. Create a fresh run ID, credentials manifest, and tenant
for the clean retest. The manifest writes `pending_password` before each
rotation and promotes it only after visible success, so either the prior or
pending credential remains available for controlled recovery after a crash.

## 3. Credential handling

Store exact credentials only in the dedicated repository-root ignored file
ishantech_e2e_credentials.json. The planned 22-account manifest and unique
passwords are already present; fill IDs and statuses as browser steps complete.
Before use, verify that the file remains ignored and owner-readable only:

~~~text
git check-ignore ishantech_e2e_credentials.json
chmod 600 ishantech_e2e_credentials.json
stat -f '%Sp %N' ishantech_e2e_credentials.json
~~~

The local object has one entry per role and no credentials from another tenant:

~~~json
{
  "production_url": "https://aethos.ishirock.tech/",
  "tenant_id": null,
  "accounts": [
    {
      "code": "tenant_owner",
      "email": "<exact local value>",
      "password": "<generated local value>",
      "user_id": null,
      "status": "planned"
    }
  ]
}
~~~

Generate unique high-entropy passwords, require first-login password change if
the product supports it, and never reuse a password across roles. Auth storage
under frontend/e2e/.auth must also be mode 0600 and must not be committed.
Committed manifests and evidence use only the redacted aliases below.

## 4. Tenant-visible role and account manifest

Create one independent user per configured system role. The legacy projection
is included because some routes still authorize against it. Record both the
assigned role code and the effective privileges shown by the UI/API.

| Role code | Legacy projection | Redacted deterministic alias | Required positive surface | User ID | Login / denial / evidence |
| --- | --- | --- | --- | --- | --- |
| tenant_owner | owner | admin-is***@ishirock.tech | Tenant/security administration and owner approvals | | |
| tenant_admin | admin | tenant-admin-ish***@ishirock.tech | Tenant users, configuration, admin approvals | | |
| cfo | admin | cfo-ish***@ishirock.tech | Finance reports, cash, controls, elevated approvals | | |
| finance_controller | admin | finance-ish***@ishirock.tech | Journals, statements, close controls | | |
| finance_ops_manager | manager | finance-ops-ish***@ishirock.tech | O2C, P2P, close readiness, Inbox | | |
| finance_approver | approver | finance-approver-ish***@ishirock.tech | Manager-threshold approve/reject only | | |
| finance_operator | member | finance-operator-ish***@ishirock.tech | Permitted finance drafts and operations | | |
| procurement_manager | manager | procurement-manager-ish***@ishirock.tech | Requests, orders, vendors, matching | | |
| buyer_requester | member | buyer-ish***@ishirock.tech | Procurement request and source evidence | | |
| ap_manager | manager | ap-manager-ish***@ishirock.tech | Bills, payment preparation/approval | | |
| ap_clerk | manager | ap-clerk-ish***@ishirock.tech | Bill intake and evidence review | | |
| ar_manager | manager | ar-manager-ish***@ishirock.tech | Billing, collections, receipts | | |
| billing_specialist | manager | billing-ish***@ishirock.tech | Draft invoices and WIP review | | |
| collections_specialist | manager | collections-ish***@ishirock.tech | Reminder preparation and follow-up | | |
| gl_accountant | admin | gl-accountant-ish***@ishirock.tech | Journal preparation and review | | |
| close_manager | admin | close-manager-ish***@ishirock.tech | Close blockers, locks, statement packages | | |
| engagement_manager | manager | engagement-manager-ish***@ishirock.tech | Clients, engagements, projects, WIP | | |
| resource_manager | manager | resource-manager-ish***@ishirock.tech | People, utilization, time approvals | | |
| auditor | auditor | auditor-ish***@ishirock.tech | Read-only records, reports, audit evidence | | |
| executive_viewer | viewer | executive-ish***@ishirock.tech | Read-only dashboards and reports | | |
| ai_ops_admin | admin | ai-ops-ish***@ishirock.tech | AI settings, autonomy, operational health | | |
| timesheet_employee | employee | timesheet-ish***@ishirock.tech | Narrow timesheet portal entry | | |

Platform administrator is not a configured tenant-visible role in the current
security catalogue. Do not simulate it by assigning tenant_owner. Record the
absence, inspect any separate control-plane mechanism only if explicitly
available, and file a product/security issue describing the intended platform
administrator lifecycle and least-privilege boundary.

For every role, test: invitation, first login, shell/navigation, one allowed
read, one allowed write where applicable, one forbidden mutation, direct URL
access to the forbidden surface, logout, and disabled/deactivated-user denial.
Test same-user creator/approver separation on money and journal actions.

## 5. Deterministic company and master data

### Company configuration

| Field | Value | Actual ID/evidence |
| --- | --- | --- |
| Legal name | Ishantech Advisory Pte. Ltd. | |
| Trading name | Ishantech | |
| Country | Singapore | |
| Base/reporting currency | SGD | |
| Fiscal year | 1 January–31 December | |
| Timezone | Asia/Singapore | |
| Output tax | Singapore GST 9% | |
| Input tax | Singapore GST 9% | |
| Zero tax | Zero-rated / 0% | |
| Invoice prefix | ISH-E2E-20260711-INV | |
| Payment terms | Net 30 | |

### Customers, engagements, and services

| Type | Deterministic record | Configuration | Actual ID |
| --- | --- | --- | --- |
| Customer | ISH-E2E-20260711 Merlion Health Pte. Ltd. | SGD, Singapore GST | |
| Customer | ISH-E2E-20260711 Pacific Vector LLC | USD, zero tax | |
| Service | Monthly Finance Operations | Retainer, SGD 12,000/month | |
| Service | Transformation Advisory | T&M, SGD | |
| Service | Implementation Milestone | Fixed milestone, SGD | |
| Engagement | Merlion Finance Operations | Monthly retainer, active 2026-04-01 | |
| Engagement | Merlion Transformation Advisory | T&M, active 2026-05-01 | |
| Engagement | Merlion Implementation | Milestone, active 2026-06-01 | |
| Engagement | Pacific Vector Advisory | Fixed fee, USD | |
| Project | Merlion Monthly Close | Linked to retainer | |
| Project | Merlion Transformation | Linked to T&M | |
| Project | Merlion Implementation Phase 1 | Linked to milestone | |

### Vendors and procurement controls

| Vendor | Currency/tax | Purpose | Actual ID |
| --- | --- | --- | --- |
| ISH-E2E-20260711 Cloud Harbor SG | SGD / GST 9% | April cloud expense | |
| ISH-E2E-20260711 Kinetic Contractors SG | SGD / GST 9% | May contractor PO/SO | |
| ISH-E2E-20260711 LedgerCloud SG | SGD / GST 9% | June annual prepaid software | |
| ISH-E2E-20260711 Vector Data Inc. | USD / zero tax | May foreign vendor bill | |

Create an approved PO or service order for the Kinetic Contractors bill with
quantity and price that match exactly. Configure test-only remittance details;
never enter a real bank account.

### Accounting and FX mapping

Before posting, map the actual chart-of-accounts IDs for: Cash, Accounts
Receivable, Accounts Payable, Service Revenue, Operating Expense, Prepaid
Software, Input GST, Output GST, Payroll Accrual, Owner Capital, Accumulated
Depreciation, Depreciation Expense, and Realised FX Gain/Loss.

Use the read-only Historical FX provenance panel in Settings to verify the
immutable rows used by the transaction engine. The runner derives two-decimal
USD document amounts that round exactly to the stated SGD approval bases; it
never writes or replaces a global FX row.

| Requested date | Pair | Required match | Purpose | Actual rate / matched date / FX row ID / source |
| --- | --- | --- | --- | --- |
| 2026-05-20 | USD to SGD | most recent immutable row no more than 3 days old | Derive TX-08 and TX-16 USD amounts that post SGD 6,750 and SGD 1,350 respectively | |
| 2026-07-12 | USD to SGD | exact-date row from the controlled current FX refresh | TX-12 receipt and realised FX gain/loss | |

Stop before approving a foreign document if either provenance lookup is absent,
the historical lag exceeds three days, the current row is not dated 2026-07-12,
or the immutable IDs are missing. A direct API/DB insert from the browser test
is prohibited. The current row comes from one separately audited operational FX
refresh after stale queue maintenance; the end-user journey itself remains UI-only.

## 6. Transaction ledger and posting oracles

All amounts below are exact. GST is 9% where stated. Actual IDs and evidence
must be completed during execution.

| Tx | Date | Browser transaction | Expected base posting (DR / CR) | Actual record/journal IDs | Result/evidence |
| --- | --- | --- | --- | --- | --- |
| TX-01 | Apr 1 | Opening capital journal SGD 100,000 | DR Cash 100,000 / CR Owner Capital 100,000 | | |
| TX-02 | Apr 5 | Retainer invoice: net 12,000; GST 1,080; total 13,080 | DR AR 13,080 / CR Revenue 12,000 / CR Output GST 1,080 | | |
| TX-03 | Apr 25 | Full receipt for TX-02 | DR Cash 13,080 / CR AR 13,080 | | |
| TX-04 | Apr 8 | Cloud bill: expense 3,000; GST 270; total 3,270 | DR Expense 3,000 / DR Input GST 270 / CR AP 3,270 | | |
| TX-05 | Apr 28 | Settle TX-04 | DR AP 3,270 / CR Cash 3,270 | | |
| TX-06 | May 31 | T&M invoice for approved May 4–15 time: net 18,000; GST 1,620; total 19,620 | DR AR 19,620 / CR Revenue 18,000 / CR Output GST 1,620 | | |
| TX-07 | May 31 | Partial receipt against TX-06: 10,000 | DR Cash 10,000 / CR AR 10,000 | | |
| TX-08 | May 20 | USD amount calculated from the captured historical rate; zero tax; frozen base 6,750 | DR AR 6,750 / CR Revenue 6,750; all lines retain the matched FX row ID | | |
| TX-09 | May 10 | Matched contractor bill: expense 8,000; GST 720; total 8,720 | DR Expense 8,000 / DR Input GST 720 / CR AP 8,720 | | |
| TX-10 | Jun 5 | Settle TX-09 | DR AP 8,720 / CR Cash 8,720 | | |
| TX-11 | Jun 15 | Remaining receipt against TX-06: 9,620 | DR Cash 9,620 / CR AR 9,620 | | |
| TX-12 | Jul 12 | Settle the TX-08 USD amount using the exact-date current row | DR Cash `<captured payment base>` plus realised FX gain/loss versus 6,750 / CR AR 6,750; July posting is excluded from Q2 statements | | |
| TX-13 | Jun 10 | Milestone invoice: net 25,000; GST 2,250; total 27,250; leave unpaid | DR AR 27,250 / CR Revenue 25,000 / CR Output GST 2,250 | | |
| TX-14 | Jun 1 | Annual software bill: prepaid 12,000; GST 1,080; total 13,080 | DR Prepaid Software 12,000 / DR Input GST 1,080 / CR AP 13,080 | | |
| TX-15 | Jun 2 | Settle TX-14 | DR AP 13,080 / CR Cash 13,080 | | |
| TX-16 | May 20 | USD amount calculated from the captured historical rate; zero tax; frozen base 1,350; leave unpaid | DR Expense 1,350 / CR AP 1,350; all lines retain the matched FX row ID | | |
| TX-16A | Jun 1 | Fictional equipment contributed in kind, fair value 600 | DR Equipment 600 / CR Owner Capital 600; disclose as non-cash financing | | |
| TX-17 | Jun 30 | Payroll accrual journal 15,000 | DR Payroll Expense 15,000 / CR Payroll Accrual 15,000 | | |
| TX-18 | Jun 30 | Depreciation journal 600 | DR Depreciation Expense 600 / CR Accumulated Depreciation 600 | | |
| TX-19 | Jun 30 | One month prepaid amortization 1,000 | DR Software Expense 1,000 / CR Prepaid Software 1,000 | | |

### Line-level journal evidence gate

TX-08, TX-16, TX-12, and the retained manual journals pass only when the
recorded browser expands the corresponding journal and visibly proves every
line's account code, DR/CR direction, transaction amount and ISO currency,
base amount and immutable FX rate row ID where conversion applies. The
Playwright journey uses the stable journal row/line evidence attributes only
to locate those visible values; it does not inspect an API response or query
the database.

TX-08 and TX-16 must show their USD transaction amounts, exact frozen SGD base
amounts, and the same `FX_APPROVAL_RATE_ID` captured in MD-07B on both sides of
each balanced journal. TX-12 requires both the receipt journal and the realised
FX journal: the receipt lines must show the USD amount, receipt-date SGD base,
and `FX_PAYMENT_RATE_ID`; the realised gain/loss lines must show the expected
SGD delta and account directions, with no second FX conversion.

TX-01, TX-16A, TX-17, TX-18, and TX-19 must visibly show the stated SGD
transaction and base amounts on their dedicated account codes, with no FX rate
ID. A USD default, converted base, missing account code, absent FX provenance,
or unmatched amount is a blocking discrepancy rather than acceptable
rounding. A journal summary row or total alone is not PASS evidence.

For each successful proof, retain the visible journal UUID and entry number in
the private checkpoint/report using the transaction-specific
`*_JOURNAL_ID` and `*_JOURNAL_ENTRY_NUMBER` keys. These identifiers link the
continuous trace/video and masked screenshot to the transaction ledger without
storing credentials or tokens.

### Monthly and quarter-end expected results

| Oracle | April | May | June | Q2 / Jun 30 ending |
| --- | ---: | ---: | ---: | ---: |
| Net income | 9,000 | 15,400 | 8,400 | 32,800 |
| Ending cash | 109,810 | 119,810 | 107,630 | 107,630 |
| Ending AR | 0 | 16,370 | 34,000 | 34,000 |
| Ending AP | 0 | 10,070 | 1,350 | 1,350 |

### Close-package period-end evidence gate

Before completing each monthly checklist, open the close package and preserve
the visible Period-end AR/AP card in the continuous recording and step
screenshot. Its base-currency AR and AP values must equal the monthly oracle
for April, May, and June, and the displayed as-of date must be April 30, May 31,
and June 30 respectively. A current-date subledger total cannot substitute for
the historical period-end values, and a close-package network response without
the corresponding visible card is not PASS evidence.

The evidence card must identify the reporting unit explicitly as
`SGD base-currency GL · as of YYYY-MM-DD`; a bare or USD-labelled amount does
not prove the Ishantech tenant's SGD close.

### Current aging evidence gate

After the final July transactions, use the visible Reports tabs to preserve
the current AR and AP aging cards in the continuous recording. The reporting
currency badge and each total must say `SGD base currency`: AR must visibly
equal SGD 27,250.00 after TX-12 clears TX-08 and TX-13 remains open, while AP
must visibly equal SGD 1,350.00 for the unpaid TX-16 bill. For each report, the
unallocated GL amount must be SGD 0.00 so the aging buckets reconcile to the
base-currency control account.

A numeric match with a USD or missing currency label is not PASS. These are
current-date controls after all retained transactions; they complement, but do
not replace, the April 30, May 31, and June 30 close-package evidence above.

Quarter statement oracle:

| Measure | Expected SGD |
| --- | ---: |
| Trial Balance debits | 184,250 |
| Trial Balance credits | 184,250 |
| Revenue | 61,750 |
| Realised FX gain/loss | 0 in Q2; TX-12 is a July event recorded separately |
| Expenses | 28,950 |
| Net income | 32,800 |
| Cash | 107,630 |
| Accounts receivable | 34,000 |
| Accounts payable | 1,350 |
| Prepaid asset, net | 11,000 |
| Input GST | 2,070 |
| Output GST | 4,950 |
| Net GST payable | 2,880 |
| Equipment, gross | 600 |
| Accumulated depreciation | (600) |
| Equipment, net | 0 |
| Total assets, gross GST presentation and net of accumulated depreciation | 154,700 |
| Liabilities, gross GST presentation | 21,300 |
| Contributed capital | 100,600 |
| Current earnings | 32,800 |
| Equity including current earnings | 133,400 |
| Operating cash flow | 7,630 |
| Financing cash flow | 100,000 |
| Ending cash flow balance | 107,630 |

If the statement offsets recoverable input GST against output GST, the equally
valid presentation is total assets 152,630 and liabilities 19,230, with net GST
payable 2,880 and equity unchanged at 133,400. Record the presentation used;
the underlying Input GST 2,070 and Output GST 4,950 ledgers must still reconcile.
The SGD 600 equipment contribution is a non-cash financing disclosure and does
not change the SGD 100,000 financing cash flow.

Sub-ledger controls:

- Invoice gross base value: 66,700.
- Q2 AR settlements at invoice base: 32,700.
- Q2 cash receipts: 32,700; TX-12 cash and realised FX are dated in July.
- Ending Q2 AR: 34,000; TX-12 subsequently clears the remaining 6,750 base balance.
- Bill gross base value: 26,420.
- AP settlements: 25,070.
- Ending AP: 1,350.

## 7. Full execution and evidence matrix

Fill every Actual, IDs/evidence, and Issue cell. PASS requires the expected
side effect, not only a success message.

| Step | Actor | Route/surface | Action and expected result | Actual | IDs/evidence | Issue |
| --- | --- | --- | --- | --- | --- | --- |
| PF-01 | Tester | DNS/TLS | Resolve canonical URL; canonical host, valid TLS, no redirect loop | PASS — A `76.13.208.106`; Let's Encrypt certificate valid through 2026-09-23; public origin 200 | [launch audit](launch-readiness-audit-2026-07-11.md) | |
| PF-02 | Tester | Public site/health | Record public build SHA, API health, worker health, migration version, time | PARTIAL — `/`, `/signup`, `/health`, `/health/ready`, `/api/v1/ping` returned 200; queue `ok`/`required:false`; SHA and migration version unavailable | [launch audit](launch-readiness-audit-2026-07-11.md) | #369 |
| PF-03 | Tester | Billing/email controls | Prove Stripe test mode and owned-alias mail sandbox before writes | | | |
| PF-04 | Tester | Browser devtools | Start clean context; capture baseline console/network; no unexplained error | | | |
| SU-01 | Anonymous | /signup | Register owner and Ishantech tenant using the public form | | | |
| SU-02 | Anonymous | /signup | Complete test-mode card/trial; one tenant/customer/subscription only | | | |
| SU-03 | Owner | First login | Verify email if required, change password, accept terms, land in tenant shell | | | |
| SU-04 | Owner | Settings/Billing | Trial status, plan, dates, currency, and Stripe IDs agree after refresh | | | |
| RB-01 | Owner | Settings/Tenant Users | Invite one independent account for each of 21 remaining roles | | | |
| RB-02 | Each role | Login | Complete first login; record user ID, assigned/effective role and nav | | | |
| RB-03 | Each role | Positive surface | Perform the allowed read/write specified in the role manifest | | | |
| RB-04 | Each role | Forbidden surface/direct URL | Controlled 403/404 or hidden action; no data leak or mutation | | | |
| RB-05 | Owner | Tenant Users | Deactivate a disposable restricted user; existing session and new login denied | | | |
| RB-06 | Owner | Security | Attempt creator self-approval where separation is required; deny and audit | | | |
| RB-07 | Tester | Platform administration | Record that no platform-admin role/control plane is discoverable; do not simulate | | | |
| MD-01 | Owner/Admin | Settings | Configure legal entity, fiscal year, SGD, timezone, GST, invoice settings | | | |
| MD-02 | Owner/Admin | Settings/Services | Create all deterministic services; refresh and verify persisted fields | | | |
| MD-03 | Engagement Manager | Contacts | Create two customers and four vendors with test-only details | | | |
| MD-04 | Resource Manager | People | Create/link staff records needed for timesheets and approvals | | | |
| MD-05 | Engagement Manager | Engagements/Projects | Create four engagements and three projects with correct billing models | | | |
| MD-06 | Procurement Manager + Finance Approver | Procurement | Procurement Manager creates the exact-match Kinetic PO/SO and is denied self-approval; Finance Approver approves with `procurement.approve` | | | |
| MD-07 | Controller | Accounting/Settings | Map account IDs and GST codes; visibly capture immutable historical/current FX provenance | | | |
| O2C-01 | Owner/Controller | Journals | Post TX-01; balanced journal and audit event exist | | | |
| O2C-02 | Billing Specialist + Finance Approver negative | Billing/Invoices | Produce TX-02; Finance Approver without `invoices.post` is visibly denied, then Billing Specialist posts/sends with catalogue privileges | | | |
| O2C-03 | AR Manager | Invoices/Payments | Post TX-03 with `invoices.mark_paid`; paid status and receipt journal update | | | |
| P2P-01 | AP Clerk + AP Manager | Bills/Pay Bills | AP Clerk creates; AP Manager approves with `bills.approve` and performs prepare/approve/export/mark-sent/settle with the matching `bill_payments.*` privileges; TX-04/TX-05 AP and GL agree | | | |
| CL-APR-01 | Close Manager | Close/Reports | Reconcile April, complete tasks, export statements, lock April | | | |
| CL-APR-02 | GL Accountant | Journals | Try Apr posting after lock; controlled rejection and no journal | | | |
| CL-APR-03 | Owner | Journals/Close | Unlock April through the audited visible control, prove Open, then relock and prove Locked | | | |
| O2C-04 | Timesheet/Resource/Billing roles | Time/Approvals/Billing | Log/approve T&M delivery and create TX-06 | | | |
| O2C-05 | AR Manager | Payments | Post TX-07 partial receipt; invoice remains partially paid at 9,620 | | | |
| O2C-06 | Billing Specialist/Controller | Invoices/FX | Create TX-08 in USD; stored transaction/base values and FX ID match | | | |
| P2P-02 | AP Clerk + AP Manager | Procurement/Bills | AP Clerk creates TX-09 against the approved PO/SO; AP Manager verifies exact match and approves the AP journal | | | |
| CL-MAY-01 | Close Manager | Close/Reports | Reconcile May, export statements, lock May with open AR/AP visible | | | |
| CL-MAY-02 | Billing/AP actors | Invoices/Bills | Try May-dated writes after lock; controlled rejection and no posting | | | |
| P2P-03 | AP Manager | Pay Bills | Prepare, approve, export, mark sent, and settle TX-09 as TX-10; payment lifecycle and bank/AP journals agree | | | |
| O2C-07 | AR Manager | Payments | Post TX-11; TX-06 becomes fully paid and leaves AR aging | | | |
| O2C-08 | AR Manager/Controller | Payments/FX | Post July TX-12; captured payment-base and realised gain/loss journal clear the 6,750 base AR exactly | | | |
| O2C-09 | Billing/Approver | Billing/Invoices | Produce TX-13 from milestone; approve/send and leave unpaid | | | |
| P2P-04 | AP Clerk + AP Manager | Bills/Pay Bills | AP Clerk creates TX-14; AP Manager approves and completes TX-15 settlement; classify prepaid, not current expense | | | |
| P2P-05 | AP Clerk + AP Manager | Bills/FX | AP Clerk creates TX-16 USD bill; AP Manager approves, proves 1,350 base and immutable FX ID, and leaves it unpaid | | | |
| R2R-00 | GL Accountant/Approver | Journals | Post TX-16A equipment contribution; gross asset and non-cash capital evidence exist | | | |
| R2R-01 | GL Accountant/Approver | Journals/Inbox | Submit TX-17 with reason; threshold approval by different user; post once | | | |
| R2R-02 | GL Accountant | Journals | Post TX-18 with reason and evidence | | | |
| R2R-03 | GL Accountant | Journals/Prepaids | Post/generate TX-19; prepaid roll-forward equals 11,000 | | | |
| R2R-04 | Controller | Reports | Current AR aging visibly equals SGD 27,250.00 and AP aging SGD 1,350.00 with SGD labels and zero unallocated GL; GST, FX, prepaid, payroll, and fixed-asset schedules tie to GL | | | |
| R2R-05 | Close Manager | Close | Complete June checklist, resolve/waive only with evidence and reason | | | |
| R2R-06 | Close Manager | Reports | Generate June P&L, balance sheet, cash flow, TB; match oracle | | | |
| R2R-07 | Close Manager | Close | Lock June; subsequent June posting and re-date attempts denied | | | |
| R2R-08 | CFO/Controller | Reports | Generate Q2 Apr–Jun statements; every quarter oracle matches | | | |
| R2R-09 | Auditor/Executive Viewer | Reports/Audit | Read/export permitted package; all mutation controls absent/denied | | | |
| R2R-10 | Controller | Statements | Drill every statement total to journals and source IDs | | | |
| FIN-01 | Tester | Console/network/health | Review full-run console, 5xx, worker failures, duplicate requests, timeouts | | | |
| FIN-02 | Controller | Reconciliation | Complete all monthly, Q2, AR/AP/GL, GST, FX, cash and equity tie-outs | | | |
| FIN-03 | Owner | Retention | Record tenant ID and searchable tag; preserve tenant; restrict credentials | | | |
| FIN-04 | Tester | GitHub/evidence | File each discrepancy, link evidence, classify severity and retest SHA | | | |

## 8. Edge-case matrix

Run each case on the same tenant without corrupting the deterministic ledger.
Use disposable draft records prefixed ISH-E2E-20260711-EDGE. Negative cases
must prove that no source record, payment, journal, or event was created.

| Area | Required cases | Expected evidence/result | Actual / issue |
| --- | --- | --- | --- |
| Signup | Invalid fields; duplicate email/company; card decline; double submit; refresh; rate limit | Clear non-500 error; no duplicate tenant/subscription | |
| Authentication | Wrong password; expired/reset link; disabled user; stale session | Controlled denial; no tenant data | |
| Role security | All role negatives; direct URLs; changed tenant header/ID; same-user approval; custom-role boundary | 403/404/hidden action; no cross-tenant row/mutation | |
| Tenant isolation | Optional second control tenant with same record names and direct IDs | No list/detail/report/storage leak in either direction | |
| Contacts/people | Blank/invalid/duplicate data; long Unicode names; inactive record | Visible validation and stable filtering/refresh | |
| Engagements/projects | Invalid dates; missing service/rate; inactive service; over-cap; blocked delete with WIP | Controlled validation; no orphan business records | |
| Time/expenses | Zero/negative/excess precision; future/locked date; DST boundary; duplicate submit; non-billable | Correct validation/status/WIP and no duplicate | |
| O2C | Blank line; due date before invoice; zero/negative/precision; duplicate approval; partial/overpayment; invalid/rotated public token; missing FX; locked period | Correct status, one journal, AR/report tie-out, controlled token error | |
| FX | Read-only historical/current provenance lookup; stale or absent rate; rate administration/write UI | Immutable rate/date/ID visible; missing write surface remains a product gap | |
| Collections | Paid invoice excluded; reminder draft vs send authority; duplicate reminder | No reminder for paid item; approval/audit boundary | |
| Procurement | Blank request; inactive vendor; self-approval; duplicate submit; threshold approval | Correct separation, status and audit | |
| Bills/matching | Duplicate vendor invoice; no PO; quantity mismatch; price mismatch; missing bank; service-period mismatch; prepaid coding | Match status and approval block are explicit | |
| Pay bills | High value; cross-currency batch; double submit; paid/voided item; export retry; settlement retry | No live bank send; idempotent status/journal | |
| Journals | Missing/short reason; imbalanced; extra precision; missing FX; threshold; self-approval; rejection; reversal; duplicate reversal | Only valid approved journals post once with audit chain | |
| Close | Open sub-ledger blocker; unapproved journal; override/waive reason; no-activity period; Owner unlock/relock; concurrent lock/write race | Readiness guard, visible open-to-locked audit, and correct authorization; concurrent race remains open | |
| Reporting | Empty/data states; April/May/June; true Apr–Jun quarter range; refresh/export/drilldown; balance warning | Period is honored; totals trace to source and tie | |
| Documents/AI | Unsupported type/size; low confidence; prompt injection; LLM/provider unavailable; keyword-only success response | Safe degradation; no unapproved side effects; source provenance | |
| Public invoice | Anonymous valid link; malformed/expired/rotated token; back/refresh; payment retry | No auth leak; controlled errors; one receipt | |
| Resilience/UI | Back/forward; hard refresh; two tabs/stale action; narrow viewport; long notes; timeout/retry | No silent loss, double write, broken layout, or unexplained console/500 | |
| Audit/export | Actor, timestamp, old/new state, reason, source and tenant; CSV/PDF contents | Complete tenant-scoped evidence with secrets redacted | |

Ordinary period locking, locked-period journal rejection, and Owner-only April
unlock followed by relock are executable in the visible UI and must be tested;
do not report a generic period-lock or reopen gap. The remaining close-control
gap is the concurrent lock/write race. Historical and current FX provenance is
also visible through the read-only inspector; the missing FX surface is rate
administration/write UI, not rate lookup.

Quarterly reporting is a launch blocker if the UI can select only one month or
if the service sends the same month as both range boundaries. Do not label three
separate monthly screenshots a quarterly-statement PASS.
Issue #370 adds From/To controls and automated range-forwarding proof on this
branch; this run must still prove the deployed controls and Q2 numbers through
the visible browser.

## 9. Retention and cleanup

The requester approved retaining this fictional tenant. At completion:

- record tenant UUID, owner user UUID, run ID, deployed SHA, and test-mode
  subscription/customer IDs in the local credential file and redacted report;
- leave all deterministic and edge records tagged with ISH-E2E-20260711;
- do not delete the tenant, users, source documents, journals, events, reports,
  or close evidence;
- verify ishantech_e2e_credentials.json and any auth-state files are 0600 and ignored;
- retain only redacted evidence in Git; never attach secrets to GitHub;
- document any test emails and Stripe objects so a later operator can identify
  and safely expire them without changing accounting history.

## 10. Exit criteria and sign-off

Launch sign-off requires all of the following:

- signup creates exactly one tenant and test-mode subscription;
- all 22 configured roles can log in and their positive/negative boundaries
  match effective privileges;
- platform-administrator ownership is either implemented and tested or accepted
  explicitly as a documented launch gap;
- every TX-01 through TX-19 record, including TX-16A, and its downstream
  journal/event exists exactly once and was created through visible browser
  actions;
- AR, AP, GST, FX, prepaid, payroll, fixed-asset, cash, and GL controls tie;
- April, May, and June close successfully and locked-period writes are denied;
- monthly statements and a true Apr–Jun Q2 range match the exact oracles;
- Trial Balance debits equal credits at 184,250 and the balance sheet ties at
  either documented GST presentation (154,700 gross or 152,630 net);
- no unresolved P0/P1 defect, unexplained 5xx, cross-tenant exposure, live
  payment, secret leak, or unapproved money-moving side effect remains;
- all discrepancies have issues, fix SHAs, deployment evidence, and production
  retest results.

No required **BLOCKED — NO UI** step may be counted as PASS. It remains a launch
blocker until a visible end-user flow is implemented, deployed, and rerun.

| Sign-off | Name | Date/time | Verdict | Evidence/notes |
| --- | --- | --- | --- | --- |
| QA executor | | | NOT RUN | |
| Finance/controller reviewer | | | NOT RUN | |
| Security/RBAC reviewer | | | NOT RUN | |
| Product owner | | | NOT RUN | |
| Launch authority | | | NOT READY / NO-GO | Production mutation NOT RUN; exact-SHA deployment and recorded Playwright run pending |
