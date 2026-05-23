/**
 * Global Playwright setup — runs before every spec via the `setup` project
 * dependency declared in playwright.config.ts.
 *
 * Purpose:
 *   1. Verify the frontend is reachable.
 *   2. Write an empty storage-state file so the chromium project's
 *      `storageState: 'e2e/.auth/storage-state.json'` resolution does
 *      not throw "ENOENT". Real per-tenant login is added incrementally
 *      as the QA harness lands more tenant-aware tests (see
 *      docs/qa/MASTER_TEST_PLAN.md §5).
 *
 * Until a real signup flow ships (#94/#95/#97 still open), this setup
 * deliberately does NOT attempt a real login — it would fail on bug #97
 * (signup AuthApiError → 500). Specs that need auth must short-circuit
 * via API JWT minting, mirroring the pytest tests in backend/tests/api/.
 */

import { test as setup, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const AUTH_DIR = path.join(__dirname, '.auth');
const STORAGE_STATE_PATH = path.join(AUTH_DIR, 'storage-state.json');

setup('frontend reachable + empty storage state', async ({ page }) => {
  // Ensure the .auth directory exists
  fs.mkdirSync(AUTH_DIR, { recursive: true });

  // Empty storage state is valid — Playwright treats absent cookies/localStorage
  // as a fresh anonymous browser. Specs that need auth set headers via
  // page.setExtraHTTPHeaders() per-test.
  const emptyState = { cookies: [], origins: [] };
  fs.writeFileSync(STORAGE_STATE_PATH, JSON.stringify(emptyState, null, 2));

  // Smoke check: the landing page must be reachable. This also serves as
  // a fail-fast — if the frontend isn't running, every spec is going to
  // ENETUNREACH; better to surface that here with a clear error.
  await page.goto('/');
  await expect(page).toHaveURL(/\/(login|signup|)?$/);
});
