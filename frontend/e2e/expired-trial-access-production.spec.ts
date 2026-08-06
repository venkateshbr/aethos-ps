import { expect, test } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const ORIGIN = 'https://aethos.ishirock.tech';
const EXPECTED_STATUS = process.env.AETHOS_EXPECTED_BILLING_STATUS;
const CREDENTIAL_PATH = path.resolve(__dirname, '..', '..', 'sterlingbridge_e2e_credentials.json');

interface CredentialManifest {
  company: string;
  production_url: string;
  accounts: Array<{ code: string; email: string; password: string }>;
}

test('expired trial has consistent status, CTA, and server-enforced access', async ({ page }) => {
  const manifest = JSON.parse(fs.readFileSync(CREDENTIAL_PATH, 'utf8')) as CredentialManifest;
  expect(manifest.company).toBe('Sterling Bridge Advisory Group');
  expect(manifest.production_url.replace(/\/$/, '')).toBe(ORIGIN);
  const owner = manifest.accounts.find(account => account.code === 'owner') ?? manifest.accounts[0];
  expect(owner).toBeTruthy();

  await page.goto('/login');
  await page.locator('#email').fill(owner.email);
  await page.locator('#password').fill(owner.password);
  const statusResponse = page.waitForResponse(response =>
    response.url().includes('/api/v1/billing/subscription-status') && response.status() === 200,
  );
  await page.getByRole('button', { name: /^sign in$/i }).click();
  await page.waitForURL(/\/app\/(?:copilot|profile)/);
  const billing = await (await statusResponse).json() as {
    status: string;
    provider_status: string;
    access_mode: string;
  };

  expect(billing.status).toBe(EXPECTED_STATUS);
  expect(billing.provider_status).toBe('trialing');

  if (EXPECTED_STATUS === 'trial_expired') {
    expect(billing.access_mode).toBe('read_only');
    await expect(page.getByRole('link', { name: /trial ended.*read-only/i })).toBeVisible();

    await page.getByRole('button', { name: 'Start new chat' }).click();
    await page.getByRole('textbox', { name: 'Message input' }).fill('Show my active engagements');
    const denied = page.waitForResponse(response =>
      response.url().includes('/api/v1/chat/threads') &&
      response.request().method() === 'POST' &&
      response.status() === 402,
    );
    await page.getByRole('button', { name: 'Send message' }).click();
    await denied;
    await expect(page.getByRole('alert')).toContainText(/workspace is read-only.*manage billing/i);
  } else {
    expect(billing.access_mode).toBe('full');
  }

  await page.goto('/app/settings');
  const billingCard = page.locator('app-subscription');
  if (EXPECTED_STATUS === 'trial_expired') {
    await expect(billingCard).toContainText('Trial ended');
    await expect(billingCard).toContainText('Workspace is read-only');
  } else {
    await expect(billingCard).toContainText('Access override');
  }
  await expect(billingCard.getByRole('button', { name: /manage plan and billing/i })).toBeVisible();
});
