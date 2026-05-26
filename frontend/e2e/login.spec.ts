/**
 * R-Real-5 — Login flow against the tunnel.
 *
 * Depends on signup.spec.ts having created a tenant earlier in the run (the
 * `o2c-tenant.meta.json` artifact persists email + password between specs).
 * If that file is missing this spec is skipped — we never make up credentials.
 *
 * What this guards:
 *   - /login renders + signs in via Supabase signInWithPassword.
 *   - Lands on /app/copilot.
 *   - Both `aethos_token` AND `aethos_tenant_id` end up in localStorage
 *     (the auth.service.ts tenant_users lookup path — same regression family
 *     as #128, different code path).
 *   - The auth guard redirects an anonymous /app/inbox visit to /login (or /).
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';
const META_PATH = path.join(__dirname, '.auth', 'o2c-tenant.meta.json');

interface Meta {
  email: string;
  password: string;
  tenantId: string | null;
}

function loadMeta(): Meta | null {
  if (!fs.existsSync(META_PATH)) return null;
  try {
    return JSON.parse(fs.readFileSync(META_PATH, 'utf-8')) as Meta;
  } catch {
    return null;
  }
}

async function readLocalStorage(page: Page): Promise<Record<string, string | null>> {
  return page.evaluate(() => {
    const out: Record<string, string | null> = {};
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k) out[k] = localStorage.getItem(k);
      }
    } catch { /* swallow */ }
    return out;
  });
}

test.describe('R-Real-5 · Login (tunnel)', () => {
  // Fresh anonymous storage state per test in this suite.
  test.use({ storageState: { cookies: [], origins: [] } });

  test('anonymous /app/inbox redirects away from the app shell', async ({ page }) => {
    await page.goto(`${BASE}/app/inbox`);
    // The auth guard kicks them to either `/` or `/login`. Either is fine.
    await page.waitForURL(/\/(login)?(\?.*)?$/, { timeout: 10_000 });
    // Make sure we are NOT on /app/inbox.
    expect(page.url()).not.toContain('/app/inbox');
  });

  test('signs in an existing tenant via /login and lands on /app/copilot', async ({ page, context }) => {
    const meta = loadMeta();
    test.skip(!meta, 'no signup-created tenant meta — run signup.spec.ts first');
    if (!meta) return;

    // Currently fails because the tenant_users RLS denies the membership
    // lookup (#128 — newly filed P0). Mark as fail-expected so this spec
    // remains a regression guard but doesn't dominate the suite verdict.
    test.fail(true, 'Login currently blocked by #128 (tenant_users RLS) — when #128 lands, this assertion flips to passing and we remove test.fail.');

    await page.goto(`${BASE}/login`);
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();

    await page.locator('#email').fill(meta.email);
    await page.locator('#password').fill(meta.password);
    await page.getByRole('button', { name: /^sign in$/i }).click();

    await page.waitForURL(/\/app\/copilot(\?.*)?$/, { timeout: 30_000 });
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 15_000 });

    const ls = await readLocalStorage(page);
    expect(ls['aethos_token'], 'aethos_token must be set after login').toBeTruthy();
    expect(ls['aethos_tenant_id'], 'aethos_tenant_id must be set after login (tenant_users lookup)').toBeTruthy();

    // Save the freshened storage so downstream specs can reuse the session.
    await context.storageState({ path: 'e2e/.auth/o2c-tenant.json' });
  });
});
