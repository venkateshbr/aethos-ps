# Full Browser End-to-End QA — Aethos Demo Guide v2

Date: 2026-09-29  
Orchestrator/reviewer: Vishwa  
QA owner discipline: Aksha / browser QA  
Live app: `https://aethos.ishirock.tech`  
Timesheet app: `https://timesheet.aethos.ishirock.tech`  
Issue/PR context: Issue #585 / PR #586

## Verdict

**DO NOT CLAIM A FULL GREEN USER-GUIDE PASS YET.**

The full docs-led browser E2E was continued end-to-end against the live production URLs using a newly created disposable Meridian tenant seeded with the Demo Guide v2 fixture. The run covered signup/auth, all major application routes, guide prompt execution, document upload scenarios, and stateful Inbox materialization.

Result: **67 PASS, 0 WARN, 2 FAIL, 0 SKIP** on the primary run. Playwright retried once and reproduced the same failure count.

## What was executed

### 1. Created disposable production QA tenant through browser signup

A robust browser signup/auth script was used because the existing `00-signup.spec.ts` still expects the stale post-signup `You're in` page, while current production lands directly in `/app/copilot`.

Outcome:

- Signup reached authenticated `/app/copilot`.
- Tenant ID was captured locally in ignored auth metadata.
- No failed `/api/*` responses were observed during signup.
- Credentials/session artifacts remain local-only under `frontend/e2e/.auth/` and are not included here.

### 2. Seeded Demo Guide v2 Meridian fixture into the disposable tenant

Command class executed from `backend/`:

```bash
set -a; source ../.env; set +a; \
uv run python -m scripts.seed_demo_v2 \
  --tenant-id <disposable-tenant-id> \
  --reset \
  --require-tenant-name '<exact disposable Meridian tenant name>'
```

Seed result:

- 6 contacts and 5 Meridian employees
- 10 engagements
- 9 projects with assignments, WIP, and one billable expense
- 3 invoices including `INV-1001`
- 2 approved vendor bills including `BILL-1001`
- Source document records, Inbox review tasks, June close tasks, and manual journals

### 3. Ran full docs-led browser E2E with stateful validation enabled

Command:

```bash
CI=1 \
AETHOS_E2E_RUN_ID=vishwa-full-browser-20260929 \
AETHOS_RUN_PRODUCTION_VALIDATION=true \
AETHOS_DEMO_STATEFUL_VALIDATION=true \
AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech \
npx playwright test e2e/demo-v2-production-validation.spec.ts --project=chromium --reporter=list
```

Playwright exit code: `1` because the business-validation gate detected 2 failed guide checks.

## Evidence artifacts

Primary run:

- Report: `docs/qa/demo-v2-production-2026-09-29T20-45-33-667Z/report.md`
- Results JSON: `docs/qa/demo-v2-production-2026-09-29T20-45-33-667Z/results.json`
- Screenshots: `docs/qa/demo-v2-production-2026-09-29T20-45-33-667Z/screenshots/`

Retry run:

- Report: `docs/qa/demo-v2-production-2026-09-29T20-54-48-465Z/report.md`
- Results JSON: `docs/qa/demo-v2-production-2026-09-29T20-54-48-465Z/results.json`
- Screenshots: `docs/qa/demo-v2-production-2026-09-29T20-54-48-465Z/screenshots/`

Failure artifacts from Playwright retry:

- Screenshot: `frontend/test-results/artifacts/demo-v2-production-validat-0c850-e-v2-behavior-on-production-chromium-retry1/test-failed-1.png`
- Video: `frontend/test-results/artifacts/demo-v2-production-validat-0c850-e-v2-behavior-on-production-chromium-retry1/video.webm`
- Trace: `frontend/test-results/artifacts/demo-v2-production-validat-0c850-e-v2-behavior-on-production-chromium-retry1/trace.zip`
- Error context: `frontend/test-results/artifacts/demo-v2-production-validat-0c850-e-v2-behavior-on-production-chromium-retry1/error-context.md`

## Primary run summary

- PASS: 67
- WARN: 0
- FAIL: 2
- SKIP: 0
- Console errors: 0
- Network failures: 2 navigation/page-teardown aborts

## Retry run summary

- PASS: 67
- WARN: 0
- FAIL: 2
- SKIP: 0
- Console errors: 0
- Network failures: 2 navigation/page-teardown aborts

## Failing guide checks

### 1. `1-6-capped-tax` — 1.6 Capped tax engagement

Primary run failure:

- Matched 3/6 required signals.
- Missing required signals:
  - fixed fee amount `18,500`
  - capped amount `22,000`
  - Inbox / approval / created signal
- Invalid answer signal:
  - response used an “I do not have…” style pattern instead of completing the user-guide action.

Retry failure:

- Reproduced with weaker match: 1/6 required signals.
- Missing Nexus / Tax Return FY2025 / fee / cap / Inbox signals.
- Same invalid-answer pattern class.

Classification: **Product / prompt-behavior defect** — the seeded fixture exists, but the guide action is not answered with the expected created/approval-ready capped engagement outcome.

### 2. `1-7-draft-reminders` — 1.7 Collections controlled write

Primary run failure:

- Matched 5/6 required signals.
- Missing required signal: customer-specific reminder signal.

Retry failure:

- Matched 4/6 required signals.
- Missing required signals:
  - customer-specific reminder signal
  - Inbox / approval signal

Classification: **Product / prompt-behavior defect** — route coverage and collections data are present, but the controlled-write response does not consistently satisfy the guide’s customer-specific + Inbox-gated reminder expectation.

## Passing coverage highlights

The run passed:

- Browser signup/auth into `/app/copilot`.
- Stateful Inbox approval/materialization for engagement onboarding.
- Stateful Inbox approval/materialization for time entry.
- Stateful Inbox approval/materialization for vendor invoice / bill creation.
- Major route coverage:
  - Aethos Nous
  - Documents
  - Inbox
  - Engagements
  - Projects
  - Invoices
  - Contacts
  - Expenses
  - Bills
  - Billing Runs / Pay Bills
  - Time
  - Approvals
  - Payments
  - People
  - Reports
  - Accounting / Journals
  - Settings
  - Timesheet portal
- Most Demo Guide v2 read/write prompt validations across O2C, P2P, R2R, Finance Ops, controls, documents, and telemetry.

## Drift / fixed-observation notes

- Existing `00-signup.spec.ts` remains stale because it expects the old post-trial `You're in` success page and `Open Nous` CTA. Current production can land directly in `/app/copilot`; the robust auth step accepted that current behavior.
- This run used a disposable Meridian tenant and exact-name guarded fixture reset, so the previous “Sterling vs Meridian fixture mismatch” blocker is not the cause of the remaining failures.
- The full test command has Playwright retry enabled via config; the retry produced a second report and reproduced the same two failing areas.

## Recommended next actions

1. **Karya + Nethra**: fix the `1-6-capped-tax` prompt/tool path so it produces or proposes the Nexus Corporation Tax FY2025 capped engagement with the fixed fee, cap, and Inbox/approval boundary.
2. **Karya + Nethra**: fix the `1-7-draft-reminders` collections controlled-write path so it drafts customer-specific reminders and routes every email through Inbox before sending.
3. **Rupa/Aksha**: update `00-signup.spec.ts` to accept current `/app/copilot` post-signup success behavior.
4. **Aksha**: rerun the same full browser E2E after fixes; acceptance is 0 FAIL with stateful validation enabled.
