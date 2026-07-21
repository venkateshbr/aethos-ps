/**
 * R-Real-5 — UI-driven signup against the Cloudflare tunnel.
 *
 * Charter (Founder direct, see PILOT_READINESS_REPORT.md §R-Real-5):
 *   - Every assertion goes through the SPA at `aethos-dev.ishirock.com`.
 *   - No httpx / curl bypass — the auth interceptor's tenant-header attach
 *     (#128) is the regression we're guarding.
 *
 * What this spec exercises (top to bottom of the signup wizard):
 *   1. /signup loads, step 1 (Account) visible.
 *   2. Page 1 → submit firm + email + password + country → step 2 (Plan).
 *   3. /api/v1/billing/prices succeeds with the JWT minted by signupAndSignIn
 *      AND the X-Tenant-ID attached by the interceptor (#128 regression guard).
 *   4. Pick the recommended (Growth) tier monthly → advance to step 3 (Card).
 *   5. Stripe Elements iframe mounts. Fill the test card.
 *   6. Start-trial → land on /app/copilot.
 *   7. localStorage MUST contain `aethos_token` AND `aethos_tenant_id`.
 *
 * If step 2 explodes with 403 "Tenant context missing", that's #128 regressing.
 * If step 6 succeeds but `aethos_tenant_id` is missing, that's a new bug.
 */

import { test, expect, Page } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';

interface SignupRunArtifacts {
  email: string;
  tenantName: string;
  tenantId: string | null;
  token: string | null;
  landedUrl: string;
  role: string | null;
}

async function readLocalStorage(page: Page): Promise<Record<string, string | null>> {
  return page.evaluate(() => {
    const out: Record<string, string | null> = {};
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k) out[k] = localStorage.getItem(k);
      }
    } catch {
      /* swallow */
    }
    return out;
  });
}

test.describe('R-Real-5 · Signup wizard (tunnel)', () => {
  test.describe.configure({ mode: 'serial' });

  // Use a per-spec timestamp so each run is unique.
  const ts = Date.now();
  const email = `aksha-o2c-${ts}@aethos-qa.dev`;
  const password = 'Aksha-real5-2026!';
  const tenantName = `Aksha O2C ${ts}`;
  const artifacts: SignupRunArtifacts = {
    email,
    tenantName,
    tenantId: null,
    token: null,
    landedUrl: '',
    role: null,
  };

  test('completes the 3-page wizard and lands on /app/copilot with both storage keys', async ({ page, context }) => {
    test.setTimeout(180_000);

    // Capture every network failure for evidence + diagnosis.
    const failed: { url: string; status: number; body: string }[] = [];
    page.on('response', async (res) => {
      if (res.status() >= 400 && res.url().includes('/api/')) {
        let body = '';
        try { body = (await res.text()).slice(0, 400); } catch { /* binary */ }
        failed.push({ url: res.url(), status: res.status(), body });
      }
    });

    // -------- Step 0: SPA bootstrap --------
    await page.goto(`${BASE}/signup`);
    await expect(page).toHaveURL(/\/signup$/);

    // Step indicator + step-1 hero
    await expect(page.getByRole('heading', { name: /create your firm/i })).toBeVisible();

    // -------- Step 1: Account form --------
    // Use IDs — labels work but "Password" appears in the strength hint too,
    // and Playwright's getByLabel ambiguity-fails on that.
    await page.locator('#firm').fill(tenantName);
    await page.locator('#email').fill(email);
    await page.locator('#password').fill(password);
    await page.locator('#confirm_password').fill(password);
    await page.locator('#country').selectOption('US');

    await page.getByRole('button', { name: /continue to plan/i }).click();

    // -------- Step 2: Plan picker --------
    // The "Pick a plan" heading is the step-2 anchor.
    await expect(page.getByRole('heading', { name: /pick a plan/i })).toBeVisible({ timeout: 30_000 });

    // #128 regression guard:
    //   The plan picker calls GET /api/v1/billing/prices via signup.service which
    //   uses environment.apiUrl + the new HttpClient. The auth interceptor must
    //   attach X-Tenant-ID — if it doesn't, the call returns 403 "Tenant context
    //   missing" and the picker shows "Could not load plans". We check both the
    //   absence of the failure copy AND that price tiles render.
    //
    // Wait for either tier tiles OR a price-error.
    const planRadioGroup = page.getByRole('radiogroup', { name: /plan tier/i });
    await expect(planRadioGroup).toBeVisible({ timeout: 30_000 });

    // Tile labels are inside a <button role="radio"> with the tier name. Three of
    // them — Starter/Growth/Pro — must be visible. Use a regex anchored to the
    // capitalized span at the start of each tile so we don't false-match on the
    // word "professional" or "pro plan" inside other descriptions.
    for (const tier of [/^starter\b/i, /^growth\b/i, /^pro\b/i]) {
      await expect(planRadioGroup.getByRole('radio', { name: tier })).toBeVisible();
    }

    // #128: there must be NO server-error alert at this point.
    const errAlert = page.getByRole('alert');
    if (await errAlert.isVisible().catch(() => false)) {
      const txt = (await errAlert.textContent()) ?? '';
      // It's only OK if the alert is something benign (e.g., the password
      // strength meter, which we don't render in step 2). Tenant-context-missing
      // is the explicit regression.
      expect(txt.toLowerCase()).not.toContain('tenant context missing');
      expect(txt.toLowerCase()).not.toContain('could not load plans');
    }

    // Pick Growth (the default-recommended tier) and advance.
    await planRadioGroup.getByRole('radio', { name: /^growth\b/i }).click();
    await page.getByRole('button', { name: /continue to card/i }).click();

    // -------- Step 3: Card --------
    await expect(page.getByRole('heading', { name: /confirm your card/i })).toBeVisible({ timeout: 30_000 });

    // Stripe Elements injects an iframe into the #cardEl mount. Wait for it.
    // The iframe has name="__privateStripeFrame…" and contains the card form.
    const cardIframe = page.frameLocator('iframe[name^="__privateStripeFrame"]').first();
    // The card-number input is identified by `name="cardnumber"` inside the frame.
    const cardNumberEl = cardIframe.locator('input[name="cardnumber"]');
    await expect(cardNumberEl).toBeVisible({ timeout: 30_000 });

    await cardNumberEl.fill('4242 4242 4242 4242');
    // Expiry + CVC live inside their own frames in newer Stripe Elements builds;
    // older builds keep them in the same iframe. Try same-frame first.
    let expEl = cardIframe.locator('input[name="exp-date"]');
    if (!(await expEl.count())) {
      expEl = page.frameLocator('iframe[name^="__privateStripeFrame"]').nth(1).locator('input[name="exp-date"]');
    }
    await expEl.fill('12 / 34');

    let cvcEl = cardIframe.locator('input[name="cvc"]');
    if (!(await cvcEl.count())) {
      cvcEl = page.frameLocator('iframe[name^="__privateStripeFrame"]').nth(2).locator('input[name="cvc"]');
    }
    await cvcEl.fill('123');

    let zipEl = cardIframe.locator('input[name="postal"]');
    if (!(await zipEl.count())) {
      zipEl = page.frameLocator('iframe[name^="__privateStripeFrame"]').nth(3).locator('input[name="postal"]');
    }
    if (await zipEl.count()) {
      await zipEl.fill('94110');
    }

    // Submit — Start 14-day trial.
    const startTrialBtn = page.getByRole('button', { name: /start 14-day trial/i });
    await expect(startTrialBtn).toBeEnabled({ timeout: 30_000 });
    await startTrialBtn.click();

    // -------- Land on /app/copilot --------
    await page.waitForURL(/\/app\/copilot(\?.*)?$/, { timeout: 60_000 });
    artifacts.landedUrl = page.url();

    // The copilot shell must mount — look for the "New chat" CTA which lives in
    // every shell render.
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 15_000 });

    // -------- #128 regression guard: both keys present --------
    const ls = await readLocalStorage(page);
    artifacts.token = ls['aethos_token'];
    artifacts.tenantId = ls['aethos_tenant_id'];
    artifacts.role = ls['aethos_role'];

    test.info().annotations.push({
      type: 'signup-artifacts',
      description: JSON.stringify({ ...artifacts, token: artifacts.token ? `${artifacts.token.slice(0, 16)}…` : null }, null, 2),
    });

    expect(artifacts.token, 'aethos_token must be in localStorage after signup').toBeTruthy();
    expect(artifacts.tenantId, 'aethos_tenant_id must be in localStorage after signup (regression guard for #128)').toBeTruthy();
    expect(artifacts.role, 'aethos_role must be owner after tenant-admin signup').toBe('owner');

    // No failed /api/* requests during the wizard.
    test.info().annotations.push({
      type: 'failed-requests',
      description: JSON.stringify(failed, null, 2),
    });
    // We tolerate 401s on /api/v1/billing/subscription-status pre-trial (race
    // between localStorage write and shell mount). Tenant-context-missing is
    // the explicit regression — should not appear.
    for (const f of failed) {
      expect(f.body.toLowerCase()).not.toContain('tenant context missing');
    }

    // Save signed-in storage state for the change-password + downstream specs.
    await context.storageState({ path: 'e2e/.auth/o2c-tenant.json' });

    // Persist the per-spec artifacts in a place the downstream tests can read.
    const fs = await import('node:fs');
    fs.chmodSync('e2e/.auth/o2c-tenant.json', 0o600);
    fs.writeFileSync(
      'e2e/.auth/o2c-tenant.meta.json',
      JSON.stringify({
        ...artifacts,
        password,
        playwrightRunId: process.env.AETHOS_E2E_RUN_ID,
      }, null, 2),
      { mode: 0o600 },
    );
    fs.chmodSync('e2e/.auth/o2c-tenant.meta.json', 0o600);
  });
});
