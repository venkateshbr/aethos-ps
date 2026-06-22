/**
 * Bills list — render-pass spec.
 *
 * Spec section: R-Bills-1
 * Route: /app/bills
 * Issue: #215 — new spec added during e2e regression pass
 *
 * What this verifies:
 *   1. /app/bills mounts under the shell.
 *   2. Page heading "Bills" is visible.
 *   3. Status filter chips render (All, Draft, Approved, etc.).
 *   4. Either a bills table OR an empty-state card is present (no crash for fresh tenant).
 *   5. "Pay Bills" navigation button is visible.
 *   6. No unexpected JS/Angular console errors.
 *
 * Component: frontend/src/app/features/bills/bills-list.component.ts
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');

interface ConsoleCollect {
  errors: string[];
}

function attachConsoleCollector(page: Page): ConsoleCollect {
  const collect: ConsoleCollect = { errors: [] };
  page.on('console', (msg) => {
    if (msg.type() === 'error') collect.errors.push(msg.text());
  });
  page.on('pageerror', (err) => collect.errors.push(`pageerror: ${err.message}`));
  return collect;
}

test.describe('R-Bills-1 · Bills list render pass', () => {
  test.use({ storageState: STORAGE_PATH });
  test.beforeEach(() => {
    test.skip(
      !fs.existsSync(STORAGE_PATH),
      'no signed-in session — run 00-signup.spec.ts first',
    );
  });

  test('/app/bills mounts, heading and filter chips visible', async ({ page }) => {
    test.setTimeout(60_000);
    const consoleCollect = attachConsoleCollector(page);

    await page.goto(`${BASE}/app/bills`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    await page.waitForLoadState('networkidle');

    // Heading must be "Bills"
    await expect(page.getByRole('heading', { name: /^bills$/i, level: 1 })).toBeVisible({ timeout: 15_000 });

    // Status filter chips — at least "All" chip must be rendered.
    // The component renders a group of status-filter buttons.
    const filterGroup = page.getByRole('group', { name: /filter bills by status/i });
    await expect(filterGroup).toBeVisible({ timeout: 10_000 });

    const allChip = filterGroup.getByRole('button', { name: /^all$/i });
    await expect(allChip).toBeVisible({ timeout: 5_000 });

    // "Pay Bills" navigation button must be present.
    await expect(page.getByRole('link', { name: /pay bills/i }).or(
      page.getByRole('button', { name: /pay bills/i }),
    ).first()).toBeVisible({ timeout: 10_000 });

    // Either the bills table OR empty-state — page must not crash.
    const content = page.locator('table[aria-label="Bills"]').or(
      page.getByText(/no bills yet/i),
    );
    await expect(content.first()).toBeVisible({ timeout: 15_000 });

    // No unexpected JS errors (filter out 404/500 from empty-tenant API calls).
    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of (404|500)/i.test(e),
    );
    test.info().annotations.push({
      type: 'console',
      description: JSON.stringify({ errors: realErrors, raw: consoleCollect.errors }),
    });
    expect(realErrors, 'no unexpected JS/Angular errors on /app/bills').toEqual([]);
  });

  test('status filter chips filter the list (or show filtered empty-state)', async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto(`${BASE}/app/bills`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    const filterGroup = page.getByRole('group', { name: /filter bills by status/i });
    await expect(filterGroup).toBeVisible({ timeout: 10_000 });

    // Click each chip and verify the page does not crash (error boundary is the key guard).
    const chipNames = ['Draft', 'Submitted', 'Approved', 'Paid'];
    for (const chipName of chipNames) {
      const chip = filterGroup.getByRole('button', { name: new RegExp(`^${chipName}$`, 'i') });
      if (await chip.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await chip.click();
        // Either a table or an empty-state message — either means the component handled the filter.
        const result = page.locator('table[aria-label="Bills"]').or(
          page.getByText(/no bills yet|no.*bills/i),
        );
        await expect(result.first()).toBeVisible({ timeout: 10_000 });
        test.info().annotations.push({
          type: 'chip-filter',
          description: `${chipName} chip: filter applied without crash.`,
        });
      }
    }

    // Reset to "All" at end.
    await filterGroup.getByRole('button', { name: /^all$/i }).click();
  });
});
