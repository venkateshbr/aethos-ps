/**
 * Regression — copilot raw fetch() must carry X-Tenant-ID.
 *
 * Bug: copilot.component.ts uses raw fetch() (SSE streaming forces this) which
 * bypasses the auth interceptor, so POST /api/v1/chat/threads went out with a
 * bearer token but NO X-Tenant-ID header. The backend membership dependency
 * (#90) replies 403 "Tenant context missing", the component swallows it, and
 * the user sees "Could not start a conversation. Please try again." on every
 * send and upload attempt from the copilot surface.
 *
 * This spec signs in (same meta artifact as login.spec.ts), sends a message
 * from the copilot composer, and asserts:
 *   1. The thread-creation request includes X-Tenant-ID matching localStorage.
 *   2. The request succeeds (201), i.e. no "Could not start a conversation".
 */

import { test, expect } from '@playwright/test';
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

test.describe('Regression · copilot thread creation carries X-Tenant-ID', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('composer send creates a thread with the tenant header', async ({ page }) => {
    const meta = loadMeta();
    test.skip(!meta, 'no signup-created tenant meta — run signup.spec.ts first');
    if (!meta) return;

    await page.goto(`${BASE}/login`);
    await page.locator('#email').fill(meta.email);
    await page.locator('#password').fill(meta.password);
    await page.getByRole('button', { name: /^sign in$/i }).click();
    await page.waitForURL(/\/app\/copilot(\?.*)?$/, { timeout: 30_000 });

    const storedTenantId = await page.evaluate(() =>
      localStorage.getItem('aethos_tenant_id'),
    );
    expect(storedTenantId, 'login must persist aethos_tenant_id').toBeTruthy();

    // Arm the network assertion BEFORE sending.
    const threadRequest = page.waitForRequest(
      req => req.url().includes('/api/v1/chat/threads') && req.method() === 'POST',
      { timeout: 15_000 },
    );
    const threadResponse = page.waitForResponse(
      res => res.url().includes('/api/v1/chat/threads') && res.request().method() === 'POST',
      { timeout: 15_000 },
    );

    const composer = page.getByRole('textbox');
    await composer.fill('hello');
    await composer.press('Enter');

    const req = await threadRequest;
    expect(req.headers()['x-tenant-id'], 'raw fetch must attach X-Tenant-ID').toBe(storedTenantId);
    expect(req.headers()['authorization']).toMatch(/^Bearer /);

    const res = await threadResponse;
    expect(res.status(), 'thread creation must not 403').toBe(201);

    // And the user-facing failure banner must not appear.
    await expect(
      page.getByText('Could not start a conversation', { exact: false }),
    ).toHaveCount(0);
  });
});
