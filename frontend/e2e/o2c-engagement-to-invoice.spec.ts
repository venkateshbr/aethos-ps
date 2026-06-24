/**
 * R-Real-6 — O2C (engagement-to-cash) walkthrough through the UI.
 *
 * Fixes verified in R-Real-6:
 *   - #133: bare-array API fix — empty-state now renders (test.fail removed)
 *   - #130: "New X" slide-in forms on engagements, clients, invoices
 *   - #129: document upload UI in Copilot composer + Documents list page
 *
 * What this spec verifies through the SPA at aethos-dev.ishirock.com:
 *   1. /app/copilot loads, chat sidebar + composer render.
 *   2. Copilot file-upload input exists (#129 fix).
 *   3. /app/engagements renders the empty-state (#133 fix).
 *   4. "New engagement" button opens the slide-in form (#130 fix).
 *   5. /app/invoices renders + "New invoice" button opens the form (#130 fix).
 *   6. /app/clients renders + "New client" button opens the form (#130 fix).
 *   7. /app/documents list page mounts (#129 fix).
 *   8. /app/payments renders.
 */

import { test, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos-dev.ishirock.com';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');

test.describe('R-Real-6 · O2C — engagement-to-invoice through the UI', () => {
  test.use({ storageState: STORAGE_PATH });
  test.beforeEach(() => {
    test.skip(!fs.existsSync(STORAGE_PATH), 'no signed-in session — run 00-signup.spec.ts first');
  });

  test('copilot mounts, chat composer accepts input, file-upload input is present (#129)', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/copilot`);
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 15_000 });

    const composer = page.getByRole('textbox', { name: /message input/i });
    await expect(composer).toBeVisible();
    await composer.fill('Show my active engagements');
    await expect(composer).toHaveValue('Show my active engagements');

    // #129 regression guard: file upload input must be present in the Copilot composer.
    // It may be a hidden <input type="file"> triggered by a button/icon.
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toHaveCount(1, { timeout: 10_000 });
    test.info().annotations.push({
      type: 'finding',
      description: '#129 fix verified: file input present in Copilot composer.',
    });
  });

  test('engagements list mounts with empty-state — #133 bare-array fix regression guard', async ({ page }) => {
    test.setTimeout(60_000);
    // Navigate then reload to let the tenant-membership settle (#132 race).
    // Use domcontentloaded to avoid hanging on SSE / long-poll connections.
    await page.goto(`${BASE}/app/engagements`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60_000 });

    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /^engagements$/i, level: 1 })).toBeVisible();

    // #133 fix: backend now returns bare array; FE services updated to accept it.
    // Reusable QA tenants may already contain engagements, so either the
    // engagement table/cards or the empty-state copy proves the page survived.
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });
    const content = page.locator('table[aria-label="Engagements"]').or(
      page.locator('[aria-label^="Engagement: "]'),
    ).or(
      page.getByText(/No engagements yet/i),
    );
    await expect(content.first()).toBeVisible({ timeout: 15_000 });
    test.info().annotations.push({
      type: 'finding',
      description: '#133 fix verified: engagements page renders with existing data or empty-state.',
    });
  });

  test('"New engagement" button opens slide-in form — #130 fix regression guard', async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto(`${BASE}/app/engagements`, { waitUntil: 'domcontentloaded' });
    await page.reload({ waitUntil: 'domcontentloaded' });
    // Wait for the loading skeleton to clear before clicking.
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 15_000 });

    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });

    // #130 fix: "New engagement" button must exist and open a slide-in form.
    const newBtn = page.getByRole('button', { name: /new engagement/i });
    await expect(newBtn).toBeVisible({ timeout: 10_000 });
    await newBtn.click();

    // The slide-in panel / dialog / drawer must appear with a form.
    // Look for a heading or panel that signals the create-form mounted.
    const slideIn = page.getByRole('dialog').or(
      page.locator('[class*="slide"], [class*="drawer"], [class*="panel"]').filter({ hasText: /engagement/i }),
    ).or(page.getByRole('heading', { name: /new engagement|create engagement/i }));
    await expect(slideIn.first()).toBeVisible({ timeout: 10_000 });

    await expect(page.locator('#eng-service')).toBeVisible();
    await expect(page.locator('#eng-service-line')).toBeVisible();
    await expect(page.locator('#eng-rate-card')).toBeVisible();
    await expect(page.locator('#eng-billing')).toContainText('Retainer Drawdown');
    await expect(page.locator('#eng-billing')).toContainText('Mixed');

    test.info().annotations.push({
      type: 'finding',
      description: '#130 + Phase 1 verified: "New engagement" opens with service catalogue, service line, rate card, and expanded billing arrangement controls.',
    });
  });

  test('invoices list mounts and "New invoice" button is wired — #130 fix', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/invoices`);
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: /^invoices$/i, level: 1 })).toBeVisible();

    // #130 fix: "New invoice" button must exist and be clickable.
    // NOTE: By design, this button navigates to /app/engagements (invoices are
    // generated from the engagement draft-invoice flow, not as standalone creates).
    // The important thing is the button is wired — not a dead no-op.
    const newBtn = page.getByRole('button', { name: /new invoice/i });
    await expect(newBtn).toBeVisible({ timeout: 10_000 });
    await newBtn.click();

    // After clicking, we should navigate to engagements (the correct flow).
    await page.waitForURL(/\/app\/engagements/, { timeout: 10_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '#130 fix verified: "New invoice" button is wired and navigates to /app/engagements for the draft-invoice flow.',
    });
  });

  test('contacts list mounts and "New contact" button opens form — #130 fix, #201 rename', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/clients`);
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });

    // #201: page heading is now "Contacts" (renamed from "Clients").
    await expect(page.getByRole('heading', { name: /^contacts$/i, level: 1 })).toBeVisible({ timeout: 10_000 });

    // #130 fix / #201: button is now "New contact" (was "New client").
    const newBtn = page.getByRole('button', { name: /new contact/i });
    await expect(newBtn).toBeVisible({ timeout: 10_000 });
    await newBtn.click();

    const slideIn = page.getByRole('dialog').or(
      page.locator('[class*="slide"], [class*="drawer"], [class*="panel"]').filter({ hasText: /contact/i }),
    ).or(page.getByRole('heading', { name: /new contact|create contact/i }));
    await expect(slideIn.first()).toBeVisible({ timeout: 10_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '#130 fix + #201 rename verified: /app/clients shows "Contacts" heading and "New contact" button opens the slide-in panel.',
    });
  });

  test('/app/documents list page mounts — #129 fix regression guard', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/documents`);
    await page.waitForLoadState('domcontentloaded');

    // #129 fix: Documents list page must exist in the nav and be reachable.
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });

    // The page should mount — either the documents list heading or an empty state.
    const documentPage = page.getByRole('heading', { name: /documents/i }).or(
      page.getByText(/no documents|upload a document|drop files/i),
    );
    await expect(documentPage.first()).toBeVisible({ timeout: 10_000 });

    test.info().annotations.push({
      type: 'finding',
      description: '#129 fix verified: /app/documents page is reachable and mounts correctly.',
    });
  });

  test('payments page renders', async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(`${BASE}/app/payments`);
    await expect(page.getByRole('navigation', { name: /main navigation/i })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('domcontentloaded');
  });
});
