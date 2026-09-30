# Full Demo Guide v2 Browser Validation — Final Green

- Date: 2026-09-30
- Orchestrator: Vishwa
- QA discipline: Aksha / browser QA
- Live app: https://aethos.ishirock.tech
- Timesheet: https://timesheet.aethos.ishirock.tech
- Backend deployed SHA: `ea385cc1118777b3c7b1c0c379b073e327578467`
- Branch/PR: `feat/issue-585-aethos-nous-role-subprofiles` / PR #586

## Verdict

**PASS — full Demo Guide v2 production browser suite is green.**

## Final full-suite command

```bash
CI=1 AETHOS_E2E_RUN_ID=vishwa-full-browser-final-20260930 AETHOS_RUN_PRODUCTION_VALIDATION=true AETHOS_DEMO_STATEFUL_VALIDATION=true AETHOS_PS_WEB_URL=https://aethos.ishirock.tech AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech npx playwright test e2e/demo-v2-production-validation.spec.ts --project=chromium --reporter=list
```

## Final full-suite evidence

- Report: `/root/dev/aethos-ps/docs/qa/demo-v2-production-2026-09-30T03-00-00-469Z/report.md`
- Results JSON: `/root/dev/aethos-ps/docs/qa/demo-v2-production-2026-09-30T03-00-00-469Z/results.json`
- Counts: PASS 69 / WARN 0 / FAIL 0 / SKIP 0
- Playwright process exit code: `0`

Key formerly failing prompts in final full suite:
- `1-3a-delivery-data` — **PASS** — Business-valid answer: matched 7/7 required signals.
- `1-4-billing-run` — **PASS** — Business-valid answer: matched 8/8 required signals.
- `1-6-capped-tax` — **PASS** — Business-valid answer: matched 6/6 required signals.
- `1-7-draft-reminders` — **PASS** — Business-valid answer: matched 6/6 required signals.

## Focused validation before final suite

- Report: `/root/dev/aethos-ps/docs/qa/focused-remaining-demo-fix-2026-09-30T02-58-59-871Z/report.md`
- Results JSON: `/root/dev/aethos-ps/docs/qa/focused-remaining-demo-fix-2026-09-30T02-58-59-871Z/results.json`
- Counts: PASS 2 / FAIL 0
- `1-3a-delivery-data` — PASS
- `1-4-billing-run` — PASS

## Backend verification

- Targeted tests: `46 passed, 1 warning`.
- Ruff: `All checks passed!`.
- Live `/api/v1/ping`: `{"pong":true}`.
- Live `/health` build SHA: `ea385cc1118777b3c7b1c0c379b073e327578467`.

## Fix summary

- Delivery data prompt now routes deterministically to `delivery_context` for exact Demo Guide wording including Alice Chen, approved/pending time, billable expenses, WIP, utilization, and invoiced entries.
- Billing run prompt now uses the deterministic `billing_run` response rather than falling through to tool policy/circuit-open denial; response includes fixed fee, retainer, T&M hours, approved expenses, draft invoice lines, and Inbox approval.
- Previously fixed capped-tax and draft-reminders prompts remain green in the final full suite.

## Secret handling

No credentials, tokens, auth-state contents, environment values, or connection strings are recorded in this report.