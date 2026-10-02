# Issue #585 — Aethos Nous ERP Role Subprofiles Browser E2E QA

Date: 2026-09-21T00:02:07Z  
Owner: Aksha QA profile  
Reviewer/orchestrator: Vishwa  
Live app: `https://aethos.ishirock.tech`  
Timesheet app: `https://timesheet.aethos.ishirock.tech`  
PR: #586

## Verdict

**SHIP WITH FIXES / not a full user-guide pass yet.**

Aksha verified the live browser path far enough to prove:

- signup can create a disposable trial tenant and land in authenticated Aethos Nous;
- authenticated navigation renders the major Aethos ERP surfaces;
- the Aethos Nous / Hermes runtime path is active and visible in run evidence;
- ERP role-subprofile prompt behavior mostly works and does not expose raw tool names in the captured responses.

However, the docs-led guide run still has business-validation failures, so issue #585 / PR #586 should **not** claim a complete green browser E2E.

## Commands executed by Aksha

```bash
CI=1 \
AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech \
npx playwright test e2e/00-signup.spec.ts --project=chromium --reporter=list
```

Result: failed before browser binary install; Aksha installed Chromium.

```bash
npx playwright install chromium
```

Result: succeeded.

```bash
CI=1 \
AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech \
npx playwright test e2e/00-signup.spec.ts --project=chromium --reporter=list
```

Result: failed due stale signup spec expectation after reaching authenticated `/app/copilot`.

```bash
CI=1 \
AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech \
npx playwright test e2e/aksha-live-signup-preserve-auth.spec.ts --project=chromium --reporter=list
```

Result: failed at the temporary verifier level, but preserved usable auth state and captured authenticated Aethos Nous screenshot.

```bash
CI=1 \
AETHOS_E2E_RUN_ID=aksha-downstream-20260920 \
AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech \
npx playwright test e2e/demo-v2-full-scenario.spec.ts --project=chromium --reporter=list
```

Result: command completed in Aksha’s transcript; no failure artifact was found for this spec.

```bash
CI=1 \
AETHOS_E2E_RUN_ID=aksha-prodval-20260920 \
AETHOS_RUN_PRODUCTION_VALIDATION=true \
AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech \
npx playwright test e2e/demo-v2-production-validation.spec.ts --project=chromium --reporter=list
```

Result: produced docs-led QA reports with failures; long run was interrupted by Aksha profile quota before a final narrative summary.

## Evidence artifacts

Local artifact folders retained on the VPS:

- `docs/qa/demo-v2-production-2026-09-20T15-21-16-234Z/`
- `docs/qa/demo-v2-production-2026-09-20T15-30-25-163Z/`
- `frontend/test-results/aksha-live-signup-copilot.png`
- `frontend/test-results/artifacts/demo-v2-production-validat-0c850-e-v2-behavior-on-production-chromium-retry1/`

These contain screenshots, Playwright videos/traces, generated report markdown, and JSON results. Bulky screenshot/video artifacts are intentionally not committed.

## Result summaries

### Long docs-led production run

Report: `docs/qa/demo-v2-production-2026-09-20T15-21-16-234Z/report.md`

- PASS: 59
- WARN: 0
- FAIL: 7
- SKIP: 3
- Console errors: 0
- Network failures: 3 `ERR_ABORTED` requests during navigation/page teardown.

Failures:

- `1-2-engagement-structure` — missing project/workstream and missing/ready/setup signals.
- `1-4-billing-run` — missing June, billing model, expense, invoice line, and Inbox approval signals.
- `1-6-capped-tax` — missing fixed/cap amount and Inbox/creation signals; response included an invalid “I do not have access” pattern.
- `1-7-draft-reminders` — missing customer and Inbox approval signals.
- `2-4-single-bill` — missing bill detail/payment readiness/action signals.
- `2-5-bill-pay` — missing disputed/exclude and rationale signals.
- `3-4-cosec-reminders` — missing Alderton and billing-impact signals.

### Short rerun

Report: `docs/qa/demo-v2-production-2026-09-20T15-30-25-163Z/report.md`

- PASS: 22
- WARN: 0
- FAIL: 2
- SKIP: 2
- Console errors: 0
- Network failures: 3 `ERR_ABORTED` requests during navigation/page teardown.

Failures:

- `1-3a-delivery-data` — missing approved/pending time, utilization, expense, and invoice readiness signals.
- `1-4-billing-run` — missing draft invoice-line signal and asked the user to provide/confirm missing input.

## User-guide coverage matrix

| Area | Status | Evidence |
| --- | --- | --- |
| Signup / trial creation | DRIFT / PARTIAL PASS | Live flow can land in authenticated `/app/copilot`; official `00-signup.spec.ts` still expects old `You're in` success copy. |
| Authenticated Nous shell | PASS | `frontend/test-results/aksha-live-signup-copilot.png`; route screenshots in both reports. |
| Documents | PASS route coverage | `route-documents` and `route-documents-after-prompts` screenshots. |
| Inbox | PASS route coverage, SKIP materialization | Inbox renders, but stateful approval/materialization steps were skipped unless `AETHOS_DEMO_STATEFUL_VALIDATION=true`. |
| Engagements / Projects | PASS route coverage, mixed prompt validation | Routes render; Nexus engagement/project prompts had failures in long run and partial pass in short run. |
| Invoices / O2C | PASS route coverage, FAIL selected prompt validation | Invoice route renders; billing-run prompt still failed. |
| Bills / Payments / P2P | PASS route coverage, mixed prompt validation | Bills/payments routes render; single-bill and bill-pay prompts failed in long run. |
| Reports | PASS route coverage | Reports route renders. |
| Journals / Settings | PASS route coverage | Journal and settings routes render. |
| Timesheet | PASS public route coverage | Timesheet login page renders. |

## Runtime evidence

Browser-captured operational rows show paired runtime records for the same chat traces:

- `Nous Hermes Runtime ... Succeeded ... nous:hermes_agent`
- Copilot agent rows around those traces using `google/gemma-4-31b-it:free` as tenant model metadata.

Host-level runtime health also verified:

- `aethos-nous-hermes.service` is active.
- `hermes -p aethos-nous mcp test aethos` discovers Aethos MCP tools.

Interpretation: the browser run exercised the configured Aethos Nous Hermes runtime path, not only the basic fallback. Some tenant AI setting rows still display the configured tenant model name (`google/gemma-4-31b-it:free`) for Copilot agent rows; the corresponding `Nous Hermes Runtime` rows provide the runtime-path evidence.

## Product defects / drift

1. **Signup spec drift**: `00-signup.spec.ts` expects old post-trial success copy (`You're in`, `Open Nous`). Current product/docs land directly in `/app/copilot`.
2. **Intermittent signup generic error**: earlier browser run showed `Something went wrong on our end. Please try again.` on Account step. Aksha later reached authenticated Nous, so this is intermittent but should remain tracked.
3. **Guide scenario data mismatch / incomplete seed**: several guide prompts ask for Nexus/Alice/Alderton/BILL data that the disposable tenant does not consistently contain.
4. **Prompt quality gaps**: specific ERP prompts still ask user for missing input or omit required business signals.
5. **Stateful materialization not covered**: Inbox approvals/materialization skipped because the run did not enable `AETHOS_DEMO_STATEFUL_VALIDATION=true` on a disposable Meridian tenant.

## Cleanup notes

Aksha created a temporary helper spec at `frontend/e2e/aksha-live-signup-preserve-auth.spec.ts` to preserve auth state. It is not intended for commit as-is.

## Recommendation

1. Rupa/Aksha: update `00-signup.spec.ts` to accept `/app/copilot` + authenticated shell/trial state as success.
2. Karya/Aksha: create or seed a disposable Meridian/Nexus demo tenant that matches the v2/v3 guide data, then rerun docs-led validation with `AETHOS_DEMO_STATEFUL_VALIDATION=true`.
3. Karya/Nethra: tighten responses for failed ERP prompts so they return draft/read-pack outputs instead of asking the user to provide data that should be in the guide seed.
4. Vishwa: keep PR #586 open with status **browser QA partially passed, full guide E2E not green** until rerun has 0 FAIL.
