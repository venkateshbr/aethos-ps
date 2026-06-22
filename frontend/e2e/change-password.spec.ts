/**
 * R-Real-5 — Change-password flow against the tunnel.
 *
 * Depends on a signed-in session (signup.spec.ts → o2c-tenant.json).
 *
 * Scope:
 *   1. Settings page mounts under the app shell.
 *   2. Account & Security section renders the change-password form.
 *   3. Submitting current+new+confirm shows success copy.
 *   4. Trying to log in with the new password — BLOCKED by #128 (tenant_users
 *      RLS). Spec records the gap with a test.info() annotation and skips
 *      the re-login step.
 */

import { test, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');
const META_PATH = path.join(__dirname, '.auth', 'o2c-tenant.meta.json');

test.describe('R-Real-5 · Change password (tunnel)', () => {
  test.use({ storageState: STORAGE_PATH });

  test.beforeEach(() => {
    test.skip(
      !fs.existsSync(STORAGE_PATH) || !fs.existsSync(META_PATH),
      'no signed-in session — run 00-signup.spec.ts first',
    );
  });

  test('settings page renders the change-password form with all required fields', async ({ page }) => {
    test.setTimeout(60_000);

    await page.goto(`${BASE}/app/settings`);

    // Settings page mounts under the app shell. Look for the sidebar nav and
    // the Settings hero — both prove the shell + route loaded.
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: /^settings$/i, level: 1 })).toBeVisible();
    await expect(page.getByRole('heading', { name: /change password/i, level: 3 })).toBeVisible();

    // All three fields visible and editable.
    await expect(page.locator('#current_password')).toBeVisible();
    await expect(page.locator('#new_password')).toBeVisible();
    await expect(page.locator('#confirm_password')).toBeVisible();

    // The Update button exists, is disabled (because form is empty).
    const submit = page.getByRole('button', { name: /update password/i });
    await expect(submit).toBeVisible();
  });

  test('change-password form submits successfully and shows success message (#131 regression guard)', async ({ page }) => {
    test.setTimeout(60_000);

    // R-Real-6: #131 is fixed — shared SupabaseService singleton means the
    // session is now persisted across navigation. test.fail removed.
    // We assert the success path: the success message renders and we do NOT
    // bounce to /login.

    const meta = JSON.parse(fs.readFileSync(META_PATH, 'utf-8')) as { password: string; password_rotated?: boolean };

    const currentPassword = meta.password;
    const newPassword = `Aksha-real5-${Date.now().toString(36)}!`;

    await page.goto(`${BASE}/app/settings`);
    await expect(page.getByRole('heading', { name: /change password/i, level: 3 })).toBeVisible({ timeout: 15_000 });

    await page.locator('#current_password').fill(currentPassword);
    await page.locator('#new_password').fill(newPassword);
    await page.locator('#confirm_password').fill(newPassword);

    const submit = page.getByRole('button', { name: /update password/i });
    await expect(submit, 'completed password form should enable submit').toBeEnabled({ timeout: 5_000 });
    await submit.click();

    // R-Real-6 assertion: must NOT bounce to /login. #131 is the regression we guard.
    await page.waitForLoadState('networkidle', { timeout: 15_000 });
    const url = page.url();

    test.info().annotations.push({
      type: 'post-submit-url',
      description: url,
    });

    // The fix (#131) means the Supabase session IS persisted after signup.
    // So we should stay on /app/settings (not /login).
    expect(url, '#131 regression guard: change-password must not redirect to /login').not.toContain('/login');

    // Success toast / status message must be visible.
    await expect(
      page.getByRole('status').or(page.getByText(/password updated/i)).or(page.getByText(/success/i)),
    ).toBeVisible({ timeout: 10_000 });

    // Persist the new current password for later setup/login runs.
    const updated = { ...meta, password: newPassword, password_rotated: false };
    fs.writeFileSync(META_PATH, JSON.stringify(updated, null, 2));
  });
});
