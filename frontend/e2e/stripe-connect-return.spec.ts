/**
 * #403 — Stripe Connect OAuth return route.
 *
 * Verifies the callback route `/settings/billing/connect/return` is wired to the
 * StripeConnectReturnComponent. Previously no route matched, so Stripe's redirect
 * fell through to the `**` wildcard and landed on the marketing page, losing the
 * OAuth code/state. Hitting the route with no params must render the component's
 * own error state (not the landing page) — proving the linkage exists. Full
 * OAuth-success verification requires live Stripe Connect and is out of scope
 * for a single browser session.
 */

import { test, expect } from '@playwright/test';

test.describe('Stripe Connect OAuth return route (#403)', () => {
  test('callback route is wired and handles a missing/invalid OAuth return', async ({ page }) => {
    await page.goto('/settings/billing/connect/return');

    // The callback component renders its own error state for missing code/state.
    await expect(
      page.getByText(/couldn't complete stripe setup|missing authorization details/i),
    ).toBeVisible({ timeout: 10_000 });

    // It is the callback page (has a Back-to-Settings link), NOT the landing page.
    await expect(page.getByRole('link', { name: /back to settings/i })).toBeVisible();
  });
});
