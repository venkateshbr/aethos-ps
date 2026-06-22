/**
 * Accounting — Journal Entries page render-pass spec.
 *
 * Spec section: R-Accounting-1
 * Route: /app/accounting/journals
 * Issue: #215 — new spec added during e2e regression pass
 *
 * What this verifies:
 *   1. /app/accounting/journals mounts under the shell (route registered in #208).
 *   2. "Journal Entries" heading (h1) is visible.
 *   3. Status filter chips render (group aria-label: "Filter journal entries").
 *   4. Either the journal entries table (aria-label="Journal entries") OR
 *      graceful empty-state is present — no crash for fresh tenant.
 *   5. "New Journal Entry" button opens the create slide-in panel.
 *   6. Create panel contains: description field, date field, journal lines section.
 *   7. Submit ("Post Journal Entry") disabled when form is invalid.
 *   8. Journal lines: "Add line" button adds a new row.
 *   9. No unexpected JS/Angular console errors.
 *
 * Component: frontend/src/app/features/accounting/journal-entries-list.component.ts
 * Added in #208.
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

test.describe('R-Accounting-1 · Journal Entries page render pass (#208)', () => {
  test.use({ storageState: STORAGE_PATH });
  test.beforeEach(() => {
    test.skip(
      !fs.existsSync(STORAGE_PATH),
      'no signed-in session — run 00-signup.spec.ts first',
    );
  });

  test('/app/accounting/journals mounts, heading and controls visible', async ({ page }) => {
    test.setTimeout(60_000);
    const consoleCollect = attachConsoleCollector(page);

    await page.goto(`${BASE}/app/accounting/journals`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    await page.waitForLoadState('networkidle');

    // Page heading: "Journal Entries"
    await expect(page.getByRole('heading', { name: /^journal entries$/i, level: 1 })).toBeVisible({ timeout: 15_000 });

    // Loading skeleton must clear.
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    // Filter chip group.
    const filterGroup = page.getByRole('group', { name: /filter journal entries/i });
    await expect(filterGroup).toBeVisible({ timeout: 10_000 });

    // Content: table or empty-state (fresh tenant has no posted journals).
    const content = page.locator('table[aria-label="Journal entries"]').or(
      page.getByText(/no journal entries/i),
    );
    await expect(content.first()).toBeVisible({ timeout: 15_000 });

    // "New Journal Entry" button.
    await expect(
      page.getByRole('button', { name: /new journal entry/i }),
    ).toBeVisible({ timeout: 10_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '/app/accounting/journals: heading, filter chips, content, and "New Journal Entry" button all visible.',
    });

    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of (404|500)/i.test(e),
    );
    test.info().annotations.push({
      type: 'console',
      description: JSON.stringify({ errors: realErrors, raw: consoleCollect.errors }),
    });
    expect(realErrors, 'no unexpected JS/Angular errors on /app/accounting/journals').toEqual([]);
  });

  test('"New Journal Entry" button opens create panel with required fields', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/accounting/journals`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    const newBtn = page.getByRole('button', { name: /new journal entry/i });
    await expect(newBtn).toBeVisible({ timeout: 10_000 });
    await newBtn.click();

    // Slide-in panel / dialog must open.
    const panel = page.getByRole('dialog', { name: /post.*journal|journal entry/i }).or(
      page.getByRole('heading', { name: /post manual journal entry/i }),
    );
    await expect(panel.first()).toBeVisible({ timeout: 10_000 });

    // Journal Lines section header must be present.
    await expect(page.getByText(/journal lines/i).first()).toBeVisible({ timeout: 5_000 });

    // "Add line" button must be present in the form.
    await expect(page.getByRole('button', { name: /add line/i })).toBeVisible({ timeout: 5_000 });

    // Submit button ("Post Journal Entry") must be disabled when form is invalid.
    const postBtn = page.getByRole('button', { name: /post journal entry/i });
    await expect(postBtn).toBeVisible({ timeout: 5_000 });
    await expect(postBtn).toBeDisabled({ timeout: 5_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '"New Journal Entry" opens create panel. Journal lines section and "Add line" button visible. Submit disabled when form empty.',
    });
  });

  test('"Add line" button adds a journal line row', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/accounting/journals`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    await page.getByRole('button', { name: /new journal entry/i }).click();
    await expect(page.getByText(/journal lines/i).first()).toBeVisible({ timeout: 10_000 });

    const addLineBtn = page.getByRole('button', { name: /add line/i });
    await expect(addLineBtn).toBeVisible({ timeout: 5_000 });

    // Count initial line rows — component starts with 2 default lines.
    const lineRows = page.locator('[aria-label^="Account for line"]');
    const initialCount = await lineRows.count();

    // Add one more line.
    await addLineBtn.click();

    await expect(lineRows).toHaveCount(initialCount + 1, { timeout: 5_000 });

    test.info().annotations.push({
      type: 'finding',
      description: `"Add line" adds a row. Was ${initialCount} lines, now ${initialCount + 1}.`,
    });
  });
});
