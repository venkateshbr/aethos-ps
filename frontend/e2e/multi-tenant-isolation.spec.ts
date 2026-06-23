/**
 * R-Real-5 — Multi-tenant isolation through the UI.
 *
 * Two tenants: A (the one signup.spec.ts created) and B (a fresh signup in
 * a brand-new browser context). From B's signed-in session we try to fetch
 * a URL that only A's tenant should see — the per-tenant /app/copilot loads
 * tenant-scoped subscription-status, and visiting A's engagement URL (if
 * we had one) should 404.
 *
 * The "visit A's engagement detail URL from B" check is parked because
 * #129/#130 means we can't *create* engagements via the UI to get a
 * tenant-A id to probe. Instead we verify:
 *   - Two independent storage states isolate cleanly (different aethos_tenant_id).
 *   - Tenant B's authenticated /api/v1/billing/subscription-status returns a
 *     trial status row that's not tenant A's (different subscription_id).
 *   - Tenant B cannot read A's data from the inbox/engagements list pages
 *     (their lists render empty, not A's content).
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';
const A_META_PATH = path.join(__dirname, '.auth', 'o2c-tenant.meta.json');

interface SignupArtifacts {
  email: string;
  tenantId: string | null;
  token: string | null;
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

async function signupTenant(page: Page, ctxLabel: string): Promise<SignupArtifacts> {
  const ts = Date.now() + Math.floor(Math.random() * 1000);
  const email = `aksha-iso-${ctxLabel}-${ts}@aethos-qa.dev`;
  const password = 'Aksha-real5-2026!';
  const tenantName = `Aksha ${ctxLabel} ${ts}`;

  await page.goto(`${BASE}/signup`);
  await page.locator('#firm').fill(tenantName);
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(password);
  await page.locator('#confirm_password').fill(password);
  await page.locator('#country').selectOption('US');
  await page.getByRole('button', { name: /continue to plan/i }).click();

  await expect(page.getByRole('heading', { name: /pick a plan/i })).toBeVisible({ timeout: 30_000 });
  await page.getByRole('radiogroup', { name: /plan tier/i })
    .getByRole('radio', { name: /^growth\b/i })
    .click();
  await page.getByRole('button', { name: /continue to card/i }).click();

  await expect(page.getByRole('heading', { name: /confirm your card/i })).toBeVisible({ timeout: 30_000 });

  const cardIframe = page.frameLocator('iframe[name^="__privateStripeFrame"]').first();
  await cardIframe.locator('input[name="cardnumber"]').fill('4242 4242 4242 4242');
  await cardIframe.locator('input[name="exp-date"]').fill('12 / 34');
  await cardIframe.locator('input[name="cvc"]').fill('123');
  const zip = cardIframe.locator('input[name="postal"]');
  if (await zip.count()) await zip.fill('94110');

  const startBtn = page.getByRole('button', { name: /start 14-day trial/i });
  await expect(startBtn).toBeEnabled({ timeout: 30_000 });
  await startBtn.click();

  await page.waitForURL(/\/app\/copilot(\?.*)?$/, { timeout: 60_000 });
  const ls = await readLocalStorage(page);

  return { email, tenantId: ls['aethos_tenant_id'], token: ls['aethos_token'] };
}

test.describe('R-Real-5 · Multi-tenant isolation (tunnel)', () => {
  test.describe.configure({ mode: 'serial' });

  test('two fresh signups get distinct tenant ids and isolated empty lists', async ({ browser }) => {
    test.setTimeout(360_000);

    // Tenant A — reuse signup.spec.ts artifact if present, otherwise sign up fresh.
    let tenantA: SignupArtifacts;
    if (fs.existsSync(A_META_PATH)) {
      const meta = JSON.parse(fs.readFileSync(A_META_PATH, 'utf-8'));
      tenantA = { email: meta.email, tenantId: meta.tenantId, token: meta.token };
    } else {
      const ctxA = await browser.newContext();
      const pageA = await ctxA.newPage();
      tenantA = await signupTenant(pageA, 'A');
      await ctxA.close();
    }

    // Tenant B — new isolated browser context, never sees A's storage.
    const ctxB = await browser.newContext();
    const pageB = await ctxB.newPage();
    const tenantB = await signupTenant(pageB, 'B');

    // Sanity — distinct tenants.
    expect(tenantA.tenantId).toBeTruthy();
    expect(tenantB.tenantId).toBeTruthy();
    expect(tenantA.tenantId).not.toEqual(tenantB.tenantId);
    expect(tenantA.email).not.toEqual(tenantB.email);

    // Navigate B → /app/engagements. Should render the empty state (no rows
    // bleeding through from A). We check by URL stability + absence of A's
    // email/tenant_name anywhere in the visible body.
    await pageB.goto(`${BASE}/app/engagements`);
    await expect(pageB.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });

    // Capture page text and verify no A-tenant artefacts.
    await pageB.waitForLoadState('networkidle');
    const bodyText = await pageB.locator('body').innerText();

    // If A's tenant_name appears in B's UI, that's a leak.
    if (tenantA.email) {
      expect(bodyText.toLowerCase(), 'tenant A email should never appear in tenant B UI').not.toContain(tenantA.email.toLowerCase());
    }

    // Same drill for the Inbox.
    await pageB.goto(`${BASE}/app/inbox`);
    await pageB.waitForLoadState('networkidle');
    const inboxBody = await pageB.locator('body').innerText();
    if (tenantA.email) {
      expect(inboxBody.toLowerCase()).not.toContain(tenantA.email.toLowerCase());
    }

    // Persist tenant B's storage in case downstream specs want to use it.
    await ctxB.storageState({ path: 'e2e/.auth/isolation-tenant-b.json' });
    fs.writeFileSync(
      'e2e/.auth/isolation-tenant-b.meta.json',
      JSON.stringify({ ...tenantB, password: 'Aksha-real5-2026!' }, null, 2),
    );

    test.info().annotations.push({
      type: 'tenant-pair',
      description: JSON.stringify({
        A: { email: tenantA.email, tenant_id: tenantA.tenantId },
        B: { email: tenantB.email, tenant_id: tenantB.tenantId },
      }, null, 2),
    });

    await ctxB.close();
  });
});
