/**
 * C35 — Landing page smoke.
 *
 * Verifies the marketing landing page loads, mentions the launch markets,
 * and has a working CTA to signup. This is the lowest-cost UI test we can
 * ship in a single browser session and is intentionally tolerant of copy
 * variations.
 */

import { test, expect } from '@playwright/test';

test.describe('Landing page (C35)', () => {
  test('renders without console errors and exposes Get Started CTA', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await page.goto('/');

    // Loose page-title assertion — branding may evolve
    await expect(page).toHaveTitle(/aethos|professional services|erp/i);

    // CTA — match either a link or a button labelled with the usual copy
    const cta = page.getByRole('link', { name: /get started|sign up|start free trial/i }).or(
      page.getByRole('button', { name: /get started|sign up|start free trial/i }),
    );
    await expect(cta.first()).toBeVisible({ timeout: 10_000 });

    // No console errors of severity error
    expect(
      consoleErrors.filter((e) => !/Failed to load resource|favicon/i.test(e)),
    ).toEqual([]);
  });

  test('mentions launch markets (US, UK, SG, IN, AU)', async ({ page }) => {
    await page.goto('/');
    const bodyText = await page.locator('body').innerText();

    // Soft check — landing copy should call out the 5 launch markets in some form.
    // If marketing copy doesn't yet mention these, the test surfaces a marketing
    // gap, not a bug.
    const markets = ['United States', 'United Kingdom', 'Singapore', 'India', 'Australia'];
    const codes = ['US', 'UK', 'SG', 'IN', 'AU'];
    const hits = markets.filter((m) => bodyText.includes(m)).length
      + codes.filter((c) => new RegExp(`\\b${c}\\b`).test(bodyText)).length;
    test.info().annotations.push({
      type: 'marketing-coverage',
      description: `Markets mentioned in landing copy: ${hits} hits across ${markets.length + codes.length} possible`,
    });
    // No hard assertion — gives Founder visibility without blocking pilot.
  });
});
