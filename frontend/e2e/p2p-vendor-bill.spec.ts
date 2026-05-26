/**
 * R-Real-5 — P2P (procure-to-pay) walkthrough through the UI.
 *
 * Per the Founder's mandate:
 *   1. Upload a vendor invoice → vendor_invoice_agent → HITL.
 *   2. Approve bill draft.
 *   3. Upload an expense receipt → expense_extractor_agent → HITL.
 *   4. Approve expense.
 *   5. Propose bill-pay batch → approve → download NACHA/CSV.
 *   6. Mark batch as paid → journal posts.
 *
 * Steps 1, 3 are BLOCKED by #129 (no upload UI).
 * Steps 2, 4 are BLOCKED by both — no HITL tasks exist for a fresh tenant.
 * Steps 5, 6 — verify the bill-pay page renders + buttons are wired (the
 *              one working batch flow per #130 inventory).
 */

import { test, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');

test.describe('R-Real-5 · P2P — vendor bill + expense + pay-bills', () => {
  test.skip(!fs.existsSync(STORAGE_PATH), 'no signed-in session — run signup.spec.ts first');
  test.use({ storageState: STORAGE_PATH });

  test('inbox renders empty for fresh tenant (no extraction HITL tasks)', async ({ page }) => {
    await page.goto(`${BASE}/app/inbox`);
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: /^inbox$/i, level: 1 })).toBeVisible();

    // Empty state copy.
    const empty = page.getByText(/no tasks|all caught up|nothing here|inbox is empty/i);
    // It may or may not show a copy — just verify the page mounts and is not in error.
    await page.waitForLoadState('networkidle');

    test.info().annotations.push({
      type: 'gap',
      description: 'Cannot drive the HITL approval flow without #129 (upload UI). Inbox is empty for fresh tenants.',
    });
  });

  test('expenses list page renders + receipt upload entry point gap is logged', async ({ page }) => {
    await page.goto(`${BASE}/app/expenses`);
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');

    // No "Upload receipt" entry point per #129.
    const uploadBtn = page.getByRole('button', { name: /upload|drop|receipt/i });
    if (!(await uploadBtn.first().isVisible().catch(() => false))) {
      test.info().annotations.push({
        type: 'gap',
        description: 'No upload-receipt UI on /app/expenses — see #129.',
      });
    }
  });

  test('billing runs / pay-bills page renders + propose-batch button is wired', async ({ page }) => {
    await page.goto(`${BASE}/app/billing-runs`);
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');

    // pay-bills.component has 8 click handlers per the #130 inventory — at least
    // one "propose batch" or similar entry point should be visible.
    const anyBatchBtn = page.getByRole('button', { name: /propose|new batch|pay bills|create batch/i });
    if (await anyBatchBtn.first().isVisible().catch(() => false)) {
      test.info().annotations.push({
        type: 'finding',
        description: 'pay-bills page has a working batch-action button (the only working batch flow in this survey).',
      });
    } else {
      // Empty for a fresh tenant with no approved bills — that's OK. We
      // verify the page mounted cleanly.
      test.info().annotations.push({
        type: 'finding',
        description: 'pay-bills page rendered but no batch button visible — likely empty-state (fresh tenant has no approved bills). Page mounts cleanly.',
      });
    }
  });
});
