/**
 * Playwright e2e suite for the engagement-to-cash workflow.
 *
 * Source spec: docs/test/e2e_engagement_to_cash.md
 * Every test corresponds to a section ID in the spec. Drift between this file
 * and the spec is a QA gate failure.
 *
 * All tests are `test.fixme()` until the underlying feature ships. When a
 * feature lands, replace `test.fixme(...)` with `test(...)` and the test must
 * pass against the real product for the right reason.
 *
 * Pattern follows agent-harness/core/e2e-workflow-standard.md:
 *   - Single browser instance per run, storage state reused.
 *   - Role-based locators (`getByRole`, `getByLabel`).
 *   - Web-first assertions (`expect(...).toBeVisible()`).
 *   - Sandbox Stripe credentials; provider-supplied test card.
 */

import { test, expect } from '@playwright/test';

const SPEC = 'docs/test/e2e_engagement_to_cash.md';

test.describe('engagement-to-cash — §1 Happy Path (TM, single-currency)', () => {

  test.fixme('§1.1 step 1 — drop engagement letter into chat', async ({ page }) => {
    // 1. login (Alice, owner)
    // 2. navigate to /copilot
    // 3. drop fixtures/engagement_letters/acme_tm.pdf onto the chat composer
    // 4. expect "extracting" toast visible
    // 5. expect document row in /documents/recent with status=uploaded
    expect(SPEC).toBeTruthy();
  });

  test.fixme('§1.1 step 3 — approve extracted engagement', async ({ page }) => {
    // expect inline EngagementDraftCard with confidence chip
    // click "Approve"
    // expect chat confirmation with link to /engagements/{id}
    // verify via API: engagement row + client row exist with currency=USD
  });

  test.fixme('§1.2 step 4 — log time from chat (3.5h on Acme yesterday)', async ({ page }) => { });
  test.fixme('§1.2 step 5 — receipt extraction auto-applies at conf > 0.9', async ({ page }) => { });
  test.fixme('§1.3 step 7 — invoice_drafter_agent produces InvoiceDraftCard', async ({ page }) => { });
  test.fixme('§1.3 step 8 — approve invoice posts balanced DR AR / CR Revenue journal', async ({ page }) => { });
  test.fixme('§1.4 step 9 — send invoice creates Stripe Payment Link', async ({ page }) => { });
  test.fixme('§1.4 step 10 — public /p/{token} renders branded invoice without auth', async ({ page }) => { });
  test.fixme('§1.5 step 11 — Stripe webhook marks invoice paid; DR Bank / CR AR journal posts', async ({ page }) => { });
  test.fixme('§1.5 step 13 — paid invoice drops out of AR aging', async ({ page }) => { });
});

test.describe('engagement-to-cash — §2 Variants', () => {
  test.fixme('§2.1 fixed-fee engagement — single milestone invoice', async ({ page }) => { });
  test.fixme('§2.2 milestone billing — one invoice per milestone', async ({ page }) => { });
  test.fixme('§2.3 monthly retainer — billing_run_agent batch', async ({ page }) => { });
  test.fixme('§2.4 retainer-draw floor alert', async ({ page }) => { });
  test.fixme('§2.5 capped T&M caps invoice and marks overflow non-billable', async ({ page }) => { });
  test.fixme('§2.6 mixed model invoice — fixed + T&M lines', async ({ page }) => { });
  test.fixme('§2.7 multi-currency — tenant USD, engagement GBP', async ({ page }) => { });
  test.fixme('§2.8 no Stripe Connect — PDF-only path', async ({ page }) => { });
});

test.describe('engagement-to-cash — §3 Unhappy Paths', () => {
  test.fixme('§3.1 extraction missing client → hitl', async ({ page }) => { });
  test.fixme('§3.2 invoice missing tax rate → blocked post', async ({ page }) => { });
  test.fixme('§3.3 webhook delayed → nightly reconciliation', async ({ page }) => { });
  test.fixme('§3.4 invalid webhook signature → 400', async ({ page }) => { });
  test.fixme('§3.5 LLM unavailable → graceful manual invoice form', async ({ page }) => { });
  test.fixme('§3.6 viewer cannot approve invoice → 403', async ({ page }) => { });
  test.fixme('§3.7 cross-tenant invoice access → 404', async ({ page }) => { });
  test.fixme('§3.8 concurrent approve → race-loser 409', async ({ page }) => { });
  test.fixme('§3.9 concurrent invoice creation → distinct numbers, no gap', async ({ page }) => { });
  test.fixme('§3.10 imbalanced journal rejected', async ({ page }) => { });
  test.fixme('§3.11 period-locked post rejected with code period_locked', async ({ page }) => { });
  test.fixme('§3.12 stale FX rate warns user on draft', async ({ page }) => { });
  test.fixme('§3.13 agent low confidence routes to HITL', async ({ page }) => { });
  test.fixme('§3.14 prompt injection in PDF → no compliance', async ({ page }) => { });
  test.fixme('§3.15 autonomy demoted on bad streak', async ({ page }) => { });
  test.fixme('§3.16 Stripe webhook idempotent on replay', async ({ page }) => { });
  test.fixme('§3.17 posted journal edit blocked at API', async ({ page }) => { });
});

test.describe('engagement-to-cash — §4 Edge Cases', () => {
  test.fixme('E1 zero-amount invoice → status=void, no journal', async ({ page }) => { });
  test.fixme('E2 negative invoice → credit note flow', async ({ page }) => { });
  test.fixme('E3 unsupported currency refused with clear message', async ({ page }) => { });
  test.fixme('E4 time-entry tz: stored in tenant tz, displayed in user tz', async ({ page }) => { });
  test.fixme('E5 FX moved between send and pay → realised FX gain/loss', async ({ page }) => { });
  test.fixme('E6 public token rotated mid-payment → old 410, new works', async ({ page }) => { });
  test.fixme('E7 delete project with unbilled effort → blocked', async ({ page }) => { });
  test.fixme('E8 max precision overflow → reject with clear message', async ({ page }) => { });
  test.fixme('E9 currency roundtrip residual → FX gain/loss', async ({ page }) => { });
  test.fixme('E10 DST transition → no lost or duplicate time entries', async ({ page }) => { });
});

test.describe('engagement-to-cash — §5 RBAC matrix', () => {
  test.fixme('owner can send invoice', async ({ page }) => { });
  test.fixme('manager can approve but cannot send invoice (UI hidden + API 403)', async ({ page }) => { });
  test.fixme('viewer sees data but cannot mutate (UI disabled + API 403)', async ({ page }) => { });
  test.fixme('other-tenant user gets 404 on direct URL', async ({ page }) => { });
});

test.describe('engagement-to-cash — §6 Audit Trail', () => {
  test.fixme('after happy path: all expected events + agent_suggestions + webhook_events present', async ({ page }) => { });
});

test.describe('engagement-to-cash — §8 Cleanup', () => {
  test.fixme('admin "Delete tenant" removes all test artifacts and cancels Stripe subscription', async ({ page }) => { });
});
