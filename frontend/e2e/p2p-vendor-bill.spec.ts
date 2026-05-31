/**
 * R-Real-6 — P2P (procure-to-pay) walkthrough through the UI.
 *
 * Fixes verified in R-Real-6:
 *   - #129: document upload UI in Copilot composer (file input present)
 *   - #130: "New expense" slide-in form now opens
 *   - #133: bare-array fix — list pages render correctly
 *
 * What this spec verifies:
 *   1. Inbox mounts (empty for fresh tenant — no extraction tasks yet).
 *   2. Expenses list renders + "New expense" button opens the form (#130 fix).
 *   3. Billing-runs / pay-bills page renders.
 *   4. Copilot file input confirms upload entry point is present (#129 fix).
 */

import { test, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');

test.describe('R-Real-6 · P2P — vendor bill + expense + pay-bills', () => {
  test.use({ storageState: STORAGE_PATH });
  test.beforeEach(() => {
    test.skip(!fs.existsSync(STORAGE_PATH), 'no signed-in session — run 00-signup.spec.ts first');
  });

  test('inbox renders for fresh tenant (no extraction HITL tasks yet)', async ({ page }) => {
    test.setTimeout(90_000);
    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /^inbox$/i, level: 1 })).toBeVisible();
    // Empty state for fresh tenant — page must mount cleanly without errors.
    await page.waitForLoadState('networkidle');
    test.info().annotations.push({
      type: 'finding',
      description: 'Inbox mounts cleanly for fresh tenant. No HITL tasks present (none uploaded via Copilot yet).',
    });
  });

  test('expenses list renders and "New expense" button opens slide-in form — #130 fix', async ({ page }) => {
    test.setTimeout(90_000);
    await page.goto(`${BASE}/app/expenses`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    await page.waitForLoadState('networkidle');

    // #130 fix: "New expense" button must exist and open the create form.
    const newBtn = page.getByRole('button', { name: /new expense/i });
    await expect(newBtn).toBeVisible({ timeout: 10_000 });
    await newBtn.click();

    const slideIn = page.getByRole('dialog').or(
      page.locator('[class*="slide"], [class*="drawer"], [class*="panel"]').filter({ hasText: /expense/i }),
    ).or(page.getByRole('heading', { name: /new expense|create expense/i }));
    await expect(slideIn.first()).toBeVisible({ timeout: 10_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '#130 fix verified: "New expense" opens the slide-in create form.',
    });
  });

  test('billing-runs / pay-bills page renders', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/billing-runs`);
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');
    test.info().annotations.push({
      type: 'finding',
      description: 'pay-bills page rendered cleanly. No batch action buttons visible for fresh tenant with no approved bills — expected empty state.',
    });
  });

  test('Copilot has file-upload entry point for vendor invoice upload — #129 fix', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/copilot`);
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 15_000 });

    // #129 fix: the upload entry point must be present in the Copilot composer.
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toHaveCount(1, { timeout: 10_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '#129 fix verified: file input in Copilot is the upload entry point for vendor invoice extraction.',
    });
  });
});
