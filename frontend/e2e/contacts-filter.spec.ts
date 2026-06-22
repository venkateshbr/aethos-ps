/**
 * Contacts filter chips — render and filter pass spec.
 *
 * Spec section: R-Contacts-1
 * Route: /app/clients
 * Issue: #215 — new spec added during e2e regression pass
 *
 * What this verifies:
 *   1. /app/clients mounts and shows the "Contacts" heading (#201 rename guard).
 *   2. Filter chip group "Filter by contact type" is visible.
 *   3. Three chips are present: All, Customers, Vendors.
 *   4. Each chip is clickable and the page does not crash after clicking.
 *   5. "New contact" button opens the create-contact slide-in panel (#130 fix, #201 rename).
 *   6. Create form fields: name, kind select.
 *   7. No unexpected JS/Angular console errors.
 *
 * Component: frontend/src/app/features/clients/clients-list.component.ts
 * Renamed from Clients → Contacts in #201.
 * Filter chips added in #201: { All, Customers, Vendors }.
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

test.describe('R-Contacts-1 · Contacts list and filter chips (#201 rename)', () => {
  test.use({ storageState: STORAGE_PATH });
  test.beforeEach(() => {
    test.skip(
      !fs.existsSync(STORAGE_PATH),
      'no signed-in session — run 00-signup.spec.ts first',
    );
  });

  test('/app/clients shows "Contacts" heading — #201 rename regression guard', async ({ page }) => {
    test.setTimeout(30_000);
    const consoleCollect = attachConsoleCollector(page);

    await page.goto(`${BASE}/app/clients`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');

    // #201: heading MUST be "Contacts", not "Clients".
    // If this fails, the rename was reverted — that is a regression.
    await expect(page.getByRole('heading', { name: /^contacts$/i, level: 1 })).toBeVisible({ timeout: 10_000 });
    // Inverse guard: old heading must NOT appear.
    await expect(page.getByRole('heading', { name: /^clients$/i, level: 1 })).toHaveCount(0);

    test.info().annotations.push({
      type: 'finding',
      description: '#201 rename verified: /app/clients displays "Contacts" heading.',
    });

    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of (404|500)/i.test(e),
    );
    expect(realErrors, 'no unexpected JS/Angular errors on /app/clients').toEqual([]);
  });

  test('filter chips All / Customers / Vendors are visible and clickable', async ({ page }) => {
    test.setTimeout(60_000);
    const consoleCollect = attachConsoleCollector(page);

    await page.goto(`${BASE}/app/clients`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    // Filter chip group.
    const filterGroup = page.getByRole('group', { name: /filter by contact type/i });
    await expect(filterGroup).toBeVisible({ timeout: 10_000 });

    // All three chips defined by filterChips in the component.
    const chips = ['All', 'Customers', 'Vendors'];
    for (const chip of chips) {
      await expect(filterGroup.getByRole('button', { name: new RegExp(`^${chip}$`, 'i') }))
        .toBeVisible({ timeout: 5_000 });
    }

    test.info().annotations.push({
      type: 'finding',
      description: `Filter chips visible: ${chips.join(', ')}.`,
    });

    // Click each chip — the page must survive without crashing.
    for (const chip of chips) {
      await filterGroup.getByRole('button', { name: new RegExp(`^${chip}$`, 'i') }).click();
      // After click: either the contacts list or an empty-state is visible — no crash.
      const content = page.locator('[aria-label^="View "]').or(
        page.getByText(/no contacts/i),
      );
      // At minimum the filter group should still be there (no full crash / redirect).
      await expect(filterGroup).toBeVisible({ timeout: 5_000 });
      test.info().annotations.push({
        type: 'chip-click',
        description: `"${chip}" chip clicked — page still mounted.`,
      });
    }

    // aria-pressed state: after clicking "Customers", that chip is aria-pressed=true.
    await filterGroup.getByRole('button', { name: /^customers$/i }).click();
    const customersChip = filterGroup.getByRole('button', { name: /^customers$/i });
    await expect(customersChip).toHaveAttribute('aria-pressed', 'true');

    // Clicking "All" resets to aria-pressed=true on All.
    await filterGroup.getByRole('button', { name: /^all$/i }).click();
    await expect(filterGroup.getByRole('button', { name: /^all$/i })).toHaveAttribute('aria-pressed', 'true');

    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of (404|500)/i.test(e),
    );
    expect(realErrors, 'no unexpected JS/Angular errors while using filter chips').toEqual([]);
  });

  test('"New contact" button opens create panel with name and kind fields', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/clients`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    // #201 rename: button is "New contact" (was "New client").
    const newBtn = page.getByRole('button', { name: /new contact/i });
    await expect(newBtn).toBeVisible({ timeout: 10_000 });
    await newBtn.click();

    // Slide-in panel / dialog must open.
    const panel = page.getByRole('dialog', { name: /new contact|create contact/i }).or(
      page.getByRole('heading', { name: /new contact/i }),
    );
    await expect(panel.first()).toBeVisible({ timeout: 10_000 });

    // Form fields: name and kind.
    await expect(page.locator('#client-name')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('#client-kind')).toBeVisible({ timeout: 5_000 });

    // Submit button must be disabled when the form is empty (name is required).
    await expect(page.getByRole('button', { name: /create contact/i })).toBeDisabled({ timeout: 5_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '"New contact" opens panel with required name field and kind select. Submit disabled when empty.',
    });
  });
});
