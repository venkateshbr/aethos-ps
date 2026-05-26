/**
 * R-Real-5 — Auth guard regression.
 *
 * #111 — anonymous visit to any /app/* route must redirect to /.
 * No saved storage state for this spec; we use a fresh anonymous context.
 */

import { test, expect } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';

test.describe('R-Real-5 · Auth guard (tunnel)', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  const guardedRoutes = [
    '/app/copilot',
    '/app/inbox',
    '/app/engagements',
    '/app/invoices',
    '/app/reports',
    '/app/settings',
  ];

  for (const route of guardedRoutes) {
    test(`anonymous ${route} is redirected to landing`, async ({ page }) => {
      await page.goto(`${BASE}${route}`);
      // The guard sends them to / (with optional ?returnUrl=) or /login.
      await page.waitForURL(/^https?:\/\/[^/]+\/(login)?(\?.*)?$/, { timeout: 10_000 });
      expect(page.url(), `${route} should not be reachable without auth`).not.toContain('/app/');
    });
  }
});
