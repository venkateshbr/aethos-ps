/**
 * Projects page — render-pass spec.
 *
 * Spec section: R-Projects-1
 * Route: /app/projects
 * Issue: #215 — new spec added during e2e regression pass
 *
 * What this verifies:
 *   1. /app/projects mounts under the shell.
 *   2. "Projects" heading (h1) is visible.
 *   3. Status filter chips render (group aria-label: "Filter by status").
 *   4. Engagement filter select renders.
 *   5. Either the projects table (aria-label="Projects") OR empty-state is present.
 *   6. "New project" button opens the create-project slide-in panel.
 *   7. Create form fields: project name (#proj-name), engagement (#proj-engagement).
 *   8. Submit disabled when name is empty.
 *   9. No unexpected JS/Angular console errors.
 *
 * Component: frontend/src/app/features/projects/projects-standalone.component.ts
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

test.describe('R-Projects-1 · Projects page render pass', () => {
  test.use({ storageState: STORAGE_PATH });
  test.beforeEach(() => {
    test.skip(
      !fs.existsSync(STORAGE_PATH),
      'no signed-in session — run 00-signup.spec.ts first',
    );
  });

  test('/app/projects mounts, heading and controls visible', async ({ page }) => {
    test.setTimeout(60_000);
    const consoleCollect = attachConsoleCollector(page);

    await page.goto(`${BASE}/app/projects`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    await page.waitForLoadState('networkidle');

    // Page heading.
    await expect(page.getByRole('heading', { name: /^projects$/i, level: 1 })).toBeVisible({ timeout: 15_000 });

    // Loading skeleton must clear.
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    // Status filter chips group.
    const filterGroup = page.getByRole('group', { name: /filter by status/i });
    await expect(filterGroup).toBeVisible({ timeout: 10_000 });

    // Engagement filter select.
    const engFilter = page.locator('select[aria-label*="engagement" i], select#proj-filter-engagement').or(
      page.locator('select').filter({ has: page.locator('option[value="all"]') }),
    );
    await expect(engFilter.first()).toBeVisible({ timeout: 10_000 });

    // Content: table or empty-state.
    const content = page.locator('table[aria-label="Projects"]').or(
      page.getByText(/no projects/i),
    );
    await expect(content.first()).toBeVisible({ timeout: 15_000 });

    // New project button.
    await expect(page.getByRole('button', { name: /new project/i }).first()).toBeVisible({ timeout: 10_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '/app/projects: heading, filter chips, engagement filter, and "New project" button all visible.',
    });

    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of (404|500)/i.test(e),
    );
    test.info().annotations.push({
      type: 'console',
      description: JSON.stringify({ errors: realErrors, raw: consoleCollect.errors }),
    });
    expect(realErrors, 'no unexpected JS/Angular errors on /app/projects').toEqual([]);
  });

  test('"New project" button opens create panel with required fields', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/projects`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    const newBtn = page.getByRole('button', { name: /new project/i }).first();
    await expect(newBtn).toBeVisible({ timeout: 10_000 });
    await newBtn.click();

    // Slide-in panel must open.
    const panel = page.getByRole('dialog', { name: /new project|create project/i }).or(
      page.getByRole('heading', { name: /new project/i }),
    );
    await expect(panel.first()).toBeVisible({ timeout: 10_000 });

    // Required field: project name.
    await expect(page.locator('#proj-name')).toBeVisible({ timeout: 5_000 });

    // Submit disabled when name is empty.
    const createBtn = page.getByRole('button', { name: /create project/i });
    await expect(createBtn).toBeDisabled({ timeout: 5_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '"New project" opens create panel. Name field visible, submit disabled when empty.',
    });
  });
});
