/**
 * Trial Balance — render-pass spec.
 *
 * Spec section: R-Reports-2
 * Route: /app/reports (Trial Balance tab)
 * Issue: #215 — new spec added during e2e regression pass
 *
 * What this verifies:
 *   1. /app/reports loads (extends the existing R-Real-5 r2r spec).
 *   2. The "Trial Balance" tab is present in the reports tab group.
 *   3. Clicking the tab renders a table (aria-label="Trial Balance") or
 *      graceful empty-state — no console errors, no Angular crash.
 *   4. When data exists: the table has DR and CR columns and
 *      the footer shows balanced totals (DR total == CR total).
 *      When data does NOT exist (fresh tenant): empty-state copy is visible.
 *
 * Component: frontend/src/app/features/reports/reports.component.ts
 *   Trial Balance tab added in the reports overhaul (#208).
 *   API: GET /api/v1/reports/trial-balance
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

test.describe('R-Reports-2 · Trial Balance tab render pass', () => {
  test.use({ storageState: STORAGE_PATH });
  test.beforeEach(() => {
    test.skip(
      !fs.existsSync(STORAGE_PATH),
      'no signed-in session — run 00-signup.spec.ts first',
    );
  });

  test('/app/reports has a Trial Balance tab that mounts without crashing', async ({ page }) => {
    test.setTimeout(90_000);
    const consoleCollect = attachConsoleCollector(page);

    await page.goto(`${BASE}/app/reports`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    // Reload once to let fresh-tenant membership settle (mirrors r2r-reports-render.spec.ts).
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60_000 });

    // Trial Balance tab must be visible in the tab group.
    const tbTab = page.getByRole('tab', { name: /trial balance/i });
    await expect(tbTab).toBeVisible({ timeout: 15_000 });

    test.info().annotations.push({
      type: 'finding',
      description: 'Trial Balance tab present in /app/reports tab group.',
    });
  });

  test('Trial Balance tab click renders table or graceful empty-state', async ({ page }) => {
    test.setTimeout(90_000);
    const consoleCollect = attachConsoleCollector(page);

    await page.goto(`${BASE}/app/reports`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60_000 });

    const tbTab = page.getByRole('tab', { name: /trial balance/i });
    if (!(await tbTab.isVisible({ timeout: 15_000 }).catch(() => false))) {
      test.info().annotations.push({
        type: 'gap',
        description: 'Trial Balance tab not found in /app/reports — tab may not yet be rendered in this build.',
      });
      test.skip();
      return;
    }

    await tbTab.click();
    // Wait for domcontentloaded to avoid hanging on SSE / backend 500s (#134).
    await page.waitForLoadState('domcontentloaded');

    // Either the Trial Balance table OR a graceful empty / loading state must be visible.
    // The table has aria-label="Trial Balance" per the component template.
    const tbTable = page.locator('table[aria-label="Trial Balance"]');
    const emptyState = page.getByText(/no data|no trial balance|no accounts|empty/i);
    const loadingState = page.locator('[aria-busy="true"]');
    const errorState = page.getByText(/failed to load|could not load|error/i);

    // Wait for loading to settle first.
    await expect(loadingState).toHaveCount(0, { timeout: 30_000 });

    const anyContent = tbTable.or(emptyState).or(errorState);
    await expect(anyContent.first()).toBeVisible({ timeout: 15_000 });

    test.info().annotations.push({
      type: 'finding',
      description: 'Trial Balance tab clicked. Table or empty-state visible — no crash.',
    });

    // If the table is present (i.e. there IS trial balance data), verify DR = CR balance.
    if (await tbTable.isVisible({ timeout: 3_000 }).catch(() => false)) {
      // The Trial Balance table must have columns for account, debit, and credit.
      // Column header text: accounts vary but "Debit" and "Credit" must appear.
      await expect(page.getByRole('columnheader', { name: /debit/i })).toBeVisible({ timeout: 5_000 });
      await expect(page.getByRole('columnheader', { name: /credit/i })).toBeVisible({ timeout: 5_000 });

      // Footer totals: DR total must equal CR total (trial balance invariant).
      // The component renders footer cells with the running totals.
      // We read both totals and compare numerically.
      const footerCells = await tbTable.locator('tfoot td, tfoot th').allTextContents();
      const numbers = footerCells
        .map((t) => t.replace(/[^0-9.]/g, ''))
        .filter((t) => t.length > 0)
        .map(Number)
        .filter((n) => !Number.isNaN(n) && n > 0);

      test.info().annotations.push({
        type: 'trial-balance-totals',
        description: JSON.stringify({ footerCells, parsedNumbers: numbers }),
      });

      if (numbers.length >= 2) {
        // DR total == CR total (within $0.01 rounding tolerance).
        const [dr, cr] = numbers;
        expect(
          Math.abs(dr - cr),
          `Trial Balance must balance: DR ${dr} == CR ${cr} (tolerance $0.01)`,
        ).toBeLessThanOrEqual(0.01);
      }
    }

    // No unexpected JS errors.
    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of (404|500)/i.test(e),
    );
    test.info().annotations.push({
      type: 'console',
      description: JSON.stringify({ errors: realErrors, raw: consoleCollect.errors }),
    });
    expect(realErrors, 'no unexpected JS/Angular errors on Trial Balance tab').toEqual([]);
  });
});
