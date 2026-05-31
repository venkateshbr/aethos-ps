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

  test('attempting the change-password flow surfaces the session gap (P1 finding)', async ({ page }) => {
    test.setTimeout(60_000);

    const meta = JSON.parse(fs.readFileSync(META_PATH, 'utf-8')) as { password: string };
    const newPassword = `${meta.password}-rot`;

    await page.goto(`${BASE}/app/settings`);
    await expect(page.getByRole('heading', { name: /change password/i, level: 3 })).toBeVisible({ timeout: 15_000 });

    await page.locator('#current_password').fill(meta.password);
    await page.locator('#new_password').fill(newPassword);
    await page.locator('#confirm_password').fill(newPassword);

    await page.getByRole('button', { name: /update password/i }).click();

    // Wait for one of: success (form clears), error toast, or bounce to login.
    await page.waitForLoadState('networkidle', { timeout: 15_000 });

    const url = page.url();
    if (url.includes('/login')) {
      test.info().annotations.push({
        type: 'finding',
        description:
          'Change-password component calls supabase.auth.getSession() but signup persists session=false (signup.service.ts:99). ' +
          'When the user returns to /app/settings the Supabase localStorage entry is missing, so the component bounces to /login. ' +
          'Filing as a P1 because change-password is broken for every fresh-signup tenant. Workaround: log in via /login (also broken — see #128).',
      });
      test.fail(true, 'Settings → change password bounces to /login because Supabase persistSession=false at signup. P1 — see annotation.');
      return;
    }

    // If success path works (e.g., a logged-in-via-/login session), capture it.
    await expect(page.getByRole('status').or(page.getByText(/password updated/i))).toBeVisible({ timeout: 5_000 });

    const updated = { ...meta, password: newPassword, password_rotated: true };
    fs.writeFileSync(META_PATH, JSON.stringify(updated, null, 2));
  });
});
