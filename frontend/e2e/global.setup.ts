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
 * does not attempt signup. It can, however, refresh the saved O2C tenant
 * session from e2e/.auth/o2c-tenant.meta.json so authenticated render specs
 * do not start with an expired bearer token.
 */

import { test as setup, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const AUTH_DIR = path.join(__dirname, '.auth');
const STORAGE_STATE_PATH = path.join(AUTH_DIR, 'storage-state.json');
const O2C_STORAGE_STATE_PATH = path.join(AUTH_DIR, 'o2c-tenant.json');
const O2C_META_PATH = path.join(AUTH_DIR, 'o2c-tenant.meta.json');

interface O2CMeta {
  email?: string;
  password?: string;
}

function loadO2CMeta(): O2CMeta | null {
  if (!fs.existsSync(O2C_META_PATH)) return null;
  try {
    return JSON.parse(fs.readFileSync(O2C_META_PATH, 'utf-8')) as O2CMeta;
  } catch {
    return null;
  }
}

setup('frontend reachable + empty storage state', async ({ page }) => {
  setup.setTimeout(120_000);
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
  await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await expect(page).toHaveURL(/\/(login|signup|)?$/);

  const meta = loadO2CMeta();
  if (!meta?.email || !meta?.password) return;

  await page.goto('/login', { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
  await page.locator('#email').fill(meta.email);
  await page.locator('#password').fill(meta.password);
  await page.getByRole('button', { name: /^sign in$/i }).click();

  await page.waitForURL(/\/app\/copilot(\?.*)?$/, { timeout: 90_000 });
  await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });

  const storage = await page.evaluate(() => ({
    token: localStorage.getItem('aethos_token'),
    tenantId: localStorage.getItem('aethos_tenant_id'),
  }));
  expect(storage.token, 'aethos_token must be set by global auth refresh').toBeTruthy();
  expect(storage.tenantId, 'aethos_tenant_id must be set by global auth refresh').toBeTruthy();

  await page.context().storageState({ path: O2C_STORAGE_STATE_PATH });
});
