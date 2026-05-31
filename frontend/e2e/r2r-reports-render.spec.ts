/**
 * R-Real-5 — R2R (record-to-report) UI render pass.
 *
 * The Founder's R2R cycle calls for verifying AR aging, AP aging, Project P&L,
 * Utilization, WIP, Revenue, and a Period-close lock. We cannot drive any of
 * those to "real numbers" because #129/#130 mean there's no way to create the
 * underlying data via the UI. What we CAN do is verify the reports page
 * mounts and each tab renders cleanly for an empty tenant (no console errors,
 * graceful empty-state copy).
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');

interface ConsoleCollect {
  errors: string[];
  warnings: string[];
}

function attachConsoleCollector(page: Page): ConsoleCollect {
  const collect: ConsoleCollect = { errors: [], warnings: [] };
  page.on('console', (msg) => {
    if (msg.type() === 'error') collect.errors.push(msg.text());
    if (msg.type() === 'warning') collect.warnings.push(msg.text());
  });
  page.on('pageerror', (err) => collect.errors.push(`pageerror: ${err.message}`));
  return collect;
}

test.describe('R-Real-5 · R2R — reports surface render check', () => {
  test.use({ storageState: STORAGE_PATH });
  test.beforeEach(() => {
    test.skip(!fs.existsSync(STORAGE_PATH), 'no signed-in session — run 00-signup.spec.ts first');
  });

  test('/app/reports mounts under the shell without console errors', async ({ page }) => {
    const consoleCollect = attachConsoleCollector(page);

    await page.goto(`${BASE}/app/reports`);
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');

    // Reload once to give the backend's just-created tenant_users row a beat
    // to be visible to the service-role read (#132 race). Without this the
    // first /api/v1/reports/* round-trip 404s and the page shows error states.
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Filter out the noise we expect (favicon, transient 404s tracked as
    // #132 race, third-party 401s before tenant context resolves) but flag
    // anything else.
    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of 404/i.test(e),
    );
    test.info().annotations.push({
      type: 'console',
      description: JSON.stringify({ errors: realErrors, warnings: consoleCollect.warnings.length, full: consoleCollect.errors }, null, 2),
    });

    // Empty body is fine — we're verifying the page can mount for a tenant
    // with no data without crashing.
    expect(realErrors, 'no unexpected console errors on /app/reports (404s tracked as #132)').toEqual([]);
  });

  test('each reports tab renders without throwing', async ({ page }) => {
    test.setTimeout(120_000);

    const consoleCollect = attachConsoleCollector(page);
    await page.goto(`${BASE}/app/reports`);
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });

    // The reports page may render tabs as buttons, links, or a tablist.
    const tabsByName = ['AR Aging', 'AP Aging', 'Project P&L', 'Utilization', 'WIP', 'Revenue'];
    const found: string[] = [];
    const missing: string[] = [];

    for (const name of tabsByName) {
      const tab = page.getByRole('tab', { name: new RegExp(name, 'i') }).or(
        page.getByRole('button', { name: new RegExp(name, 'i') }),
      ).or(
        page.getByRole('link', { name: new RegExp(name, 'i') }),
      );
      if (await tab.first().isVisible().catch(() => false)) {
        found.push(name);
        await tab.first().click();
        await page.waitForLoadState('networkidle');
      } else {
        missing.push(name);
      }
    }

    test.info().annotations.push({
      type: 'reports-coverage',
      description: JSON.stringify({ found, missing }, null, 2),
    });

    // Soft assertion — at least one of the six tabs should be visible. If none
    // are, the reports page is hollow and we flag that as a UI gap.
    expect(found.length, 'at least one reports tab should render').toBeGreaterThan(0);

    // No console errors as we tabbed through (404 tolerated due to #132).
    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of 404/i.test(e),
    );
    expect(realErrors, 'no unexpected console errors tabbing through reports (404s tracked as #132)').toEqual([]);
  });
});
