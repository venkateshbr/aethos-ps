# Full Demo Guide v2 Browser Rerun — Post Prompt Fixes

- Date: 2026-09-30
- Orchestrator: Vishwa
- QA discipline: Aksha / browser QA
- Live app: https://aethos.ishirock.tech
- Timesheet: https://timesheet.aethos.ishirock.tech
- Backend deployed SHA verified before run: `aebba539d127253e28e8b9f5145cc897037c456b`
- Branch/PR: `feat/issue-585-aethos-nous-role-subprofiles` / PR #586

## Command

```bash
CI=1 AETHOS_E2E_RUN_ID=vishwa-full-browser-postfix-20260930 AETHOS_RUN_PRODUCTION_VALIDATION=true AETHOS_DEMO_STATEFUL_VALIDATION=true AETHOS_PS_WEB_URL=https://aethos.ishirock.tech AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech npx playwright test e2e/demo-v2-production-validation.spec.ts --project=chromium --reporter=list
```

## Verdict

**Not a full green pass yet.** The two previously failing prompts are fixed in the full suite (`1-6-capped-tax` and `1-7-draft-reminders` both passed), but the rerun exposed remaining failures in `1-3a-delivery-data` and `1-4-billing-run`.

## Run 1: `demo-v2-production-2026-09-30T02-24-58-511Z`

- Report: `/root/dev/aethos-ps/docs/qa/demo-v2-production-2026-09-30T02-24-58-511Z/report.md`
- Results JSON: `/root/dev/aethos-ps/docs/qa/demo-v2-production-2026-09-30T02-24-58-511Z/results.json`
- Counts: PASS 65 / WARN 0 / FAIL 3 / SKIP 0
- Previously failing `1-6-capped-tax`: PASS
- Previously failing `1-7-draft-reminders`: PASS

### Failures

#### `1-1-engagement-letter` — 1.1 Engagement letter onboarding

- Action: Atlas prompt
- Summary: Business validation failed: matched 2/7 required signals; forbidden hits 0.
- Missing: /Nexus/i, /client/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i
- Forbidden: none

Observed response excerpt:

```text
The engagement letter has been processed, and an Inbox review task has been created. Please review your Inbox for the next steps and any actions required.
```

#### `1-3a-delivery-data` — 1.3A People and WIP

- Action: Atlas prompt
- Summary: Business validation failed: matched 5/7 required signals; forbidden hits 0.
- Missing: /expense/i, /invoice|invoiced/i
- Forbidden: none

Observed response excerpt:

```text
I couldn't find any time entries recorded for Alice Chen on the Nexus projects for June 2026.

However, looking at the overall Work in Progress (WIP) for Nexus, there is unbilled effort on the **Nexus CFO Advisory** project:
*   **Unbilled Hours:** 13.5 hours
*   **WIP Value:** £4,725.00 (at an average rate of £350/hr)

Because there were no time entries found for Alice Chen specifically in June, I cannot provide her individual utilization or a breakdown of her approved vs. pending time. If she logged time under a different project name or if the entries are still in draft, please let me know!
```

#### `1-4-billing-run` — 1.4 Mixed model invoice

- Action: Atlas prompt
- Summary: Business validation failed: matched 2/8 required signals; forbidden hits 0.
- Missing: /fixed fee/i, /retainer/i, /T&M|time and materials|hour/i, /expense/i, /invoice line|draft invoice/i, /Inbox|approval/i
- Forbidden: none

Observed response excerpt:

```text
I attempted to prepare the June 2026 billing run for **Nexus Capital Partners - Group Accounting & Advisory**, but the request was denied due to a system policy restriction.

Please ensure that the necessary permissions are configured, or contact your system administrator to resolve the `tool_circuit_open` policy denial for invoicing.
```

## Run 2: `demo-v2-production-2026-09-30T02-33-07-397Z`

- Report: `/root/dev/aethos-ps/docs/qa/demo-v2-production-2026-09-30T02-33-07-397Z/report.md`
- Results JSON: `/root/dev/aethos-ps/docs/qa/demo-v2-production-2026-09-30T02-33-07-397Z/results.json`
- Counts: PASS 67 / WARN 0 / FAIL 2 / SKIP 0
- Previously failing `1-6-capped-tax`: PASS
- Previously failing `1-7-draft-reminders`: PASS

### Failures

#### `1-3a-delivery-data` — 1.3A People and WIP

- Action: Atlas prompt
- Summary: Business validation failed: matched 2/7 required signals; forbidden hits 0.
- Missing: /approved time|pending time|hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice|invoiced/i
- Forbidden: none

Observed response excerpt:

```text
I'll gather Alice Chen's June delivery data for Nexus. Let me query the time entries for both Nexus engagements during June 2026.
```

#### `1-4-billing-run` — 1.4 Mixed model invoice

- Action: Atlas prompt
- Summary: Business validation failed: matched 2/8 required signals; forbidden hits 0.
- Missing: /fixed fee/i, /retainer/i, /T&M|time and materials|hour/i, /expense/i, /invoice line|draft invoice/i, /Inbox|approval/i
- Forbidden: none

Observed response excerpt:

```text
I attempted to draft the June 2026 billing run for Nexus, but the action was denied due to system security policies. Please ensure you have the necessary manager-level permissions or contact your system administrator to resolve this.
```

## Notes

- Demo tenant was reset immediately before this run with `seed_demo_v2 --reset --require-tenant-name` for `Meridian Advisory QA 1790714645482`.
- `1-6-capped-tax` now passes with all 6/6 signals.
- `1-7-draft-reminders` now passes with all 6/6 signals.
- The suite exit code remained non-zero because `1-3a-delivery-data` and `1-4-billing-run` failed on the retry report.
