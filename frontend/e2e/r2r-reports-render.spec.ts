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

    await page.goto(`${BASE}/app/reports`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });

    // Reload once to give the backend's just-created tenant_users row a beat
    // to be visible to the service-role read (#132 race). Without this the
    // first /api/v1/reports/* round-trip 404s and the page shows error states.
    await page.reload({ waitUntil: 'domcontentloaded' });

    // Filter out expected noise:
    //   - favicon 404s (browser default behavior)
    //   - 404s from #132 race (membership lookup, now fixed but still transitional)
    //   - 500s from /api/v1/reports/* on empty tenant — backend bug filed as
    //     #134 (reports endpoints 500 instead of returning empty results for
    //     fresh tenants). This is a known backend issue, separate from the
    //     UI render we're checking here.
    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of (404|500)/i.test(e),
    );

    // Separately capture and annotate 500s so the bug is visible in the report.
    const backendErrors500 = consoleCollect.errors.filter((e) =>
      /Failed to load resource: the server responded with a status of 500/i.test(e),
    );
    if (backendErrors500.length > 0) {
      test.info().annotations.push({
        type: 'bug',
        description: `Backend 500 on /app/reports for fresh tenant — reports endpoint(s) crash instead of returning empty data. Filed as #134. Errors: ${JSON.stringify(backendErrors500)}`,
      });
    }

    test.info().annotations.push({
      type: 'console',
      description: JSON.stringify({ errors: realErrors, warnings: consoleCollect.warnings.length, full: consoleCollect.errors }, null, 2),
    });

    // The page itself must still mount cleanly (no JS errors, no Angular crash).
    expect(realErrors, 'no unexpected JS/Angular console errors on /app/reports').toEqual([]);
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
        // Use domcontentloaded to avoid hanging on SSE / long-poll from backend 500s.
        await page.waitForLoadState('domcontentloaded');
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

    // Filter 404s (#132 transitional) and 500s (#134 backend bug — reports 500 on empty tenant).
    const realErrors = consoleCollect.errors.filter((e) =>
      !/favicon|net::ERR_|Failed to load resource: the server responded with a status of (404|500)/i.test(e),
    );
    expect(realErrors, 'no unexpected JS/Angular console errors tabbing through reports').toEqual([]);
  });
});
