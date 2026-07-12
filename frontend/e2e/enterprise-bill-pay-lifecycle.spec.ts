/**
 * Enterprise bill-pay lifecycle proof for #325.
 *
 * Uses mocked API contracts to prove the browser path from selected approved
 * bills through approval, export, bank-send, and settlement confirmation.
 */

import { expect, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

async function authenticate(page: Page): Promise<void> {
  await page.goto(`${BASE}/`);
  await page.evaluate(() => {
    window.localStorage.setItem('aethos_token', 'mock-token-bill-pay-325');
    window.localStorage.setItem('aethos_tenant_id', 'tenant-bill-pay-325');
    window.localStorage.setItem('aethos_role', 'admin');
  });
}

async function installMocks(page: Page): Promise<void> {
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (path === '/api/v1/security/me/permissions' && method === 'GET') {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-bill-pay-325',
          user_id: 'user-bill-pay-325',
          legacy_role: 'admin',
          role_codes: ['tenant_admin'],
          role_labels: ['Tenant Admin'],
          privilege_codes: [
            'bill_payments.read',
            'bill_payments.prepare',
            'bill_payments.approve',
            'bill_payments.export',
            'bill_payments.settle',
          ],
          must_change_password: false,
        },
      });
      return;
    }

    if (path === '/api/v1/bills' && method === 'GET') {
      await route.fulfill({
        json: {
          items: [
            {
              id: 'bill-325',
              bill_number: 'BILL-325',
              client_id: 'Aster Cloud Services',
              total: '125.00',
              currency: 'USD',
              due_date: '2026-06-30',
              status: 'approved',
            },
          ],
          total: 1,
        },
      });
      return;
    }

    if (path === '/api/v1/engagements' && method === 'GET') {
      await route.fulfill({ json: [] });
      return;
    }

    if (path === '/api/v1/bill-payments/batches' && method === 'POST') {
      await route.fulfill({
        status: 201,
        json: {
          id: 'batch-325',
          status: 'draft',
          total: '125.00',
          total_amount: '125.00',
          currency: 'USD',
          pay_date: '2026-06-30',
          bank_account_label: 'Operating Account',
          bill_ids: ['bill-325'],
        },
      });
      return;
    }

    if (path === '/api/v1/bill-payments/batches/batch-325/approve' && method === 'POST') {
      await route.fulfill({
        json: {
          id: 'batch-325',
          status: 'approved',
          total: '125.00',
          total_amount: '125.00',
          currency: 'USD',
          pay_date: '2026-06-30',
          bank_account_label: 'Operating Account',
          bill_ids: ['bill-325'],
        },
      });
      return;
    }

    if (path === '/api/v1/bill-payments/batches/batch-325/export' && method === 'GET') {
      await route.fulfill({
        contentType: 'text/csv',
        headers: {
          'Content-Disposition': 'attachment; filename=batch-batch-325.csv',
        },
        body: 'Vendor Name,Routing Number,Account Number,Amount,Currency,Pay Date,Reference,Vendor Invoice Number\nAster Cloud Services,,,125.00,USD,2026-06-30,BATCH-batch-325,ASTER-325\n',
      });
      return;
    }

    if (path === '/api/v1/bill-payments/batches/batch-325/mark-sent' && method === 'PATCH') {
      await route.fulfill({
        json: {
          id: 'batch-325',
          status: 'sent_to_bank',
          total: '125.00',
          total_amount: '125.00',
          currency: 'USD',
          pay_date: '2026-06-30',
          bank_account_label: 'Operating Account',
          bill_ids: ['bill-325'],
        },
      });
      return;
    }

    if (path === '/api/v1/bill-payments/batches/batch-325/settle' && method === 'POST') {
      await route.fulfill({
        json: {
          batch_id: 'batch-325',
          status: 'settled',
          settled_count: 1,
          journal_entry_ids: ['je-325'],
        },
      });
      return;
    }

    if (path.includes('/financial-events/business-records/bill_payment_batch/batch-325/decisions')) {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }

    await route.fulfill({ json: { items: [], total: 0 } });
  });
}

test.describe('Enterprise bill-pay lifecycle (#325)', () => {
  test('Pay Bills requires approval, export, send, and settlement in order', async ({ page }) => {
    await installMocks(page);
    await authenticate(page);

    await page.goto(`${BASE}/app/billing-runs`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: 'Pay Bills' })).toBeVisible();
    await page.getByRole('tab', { name: /Select Bills/i }).click();
    await expect(page.getByText('BILL-325')).toBeVisible();
    await page.getByLabel('Select bill BILL-325').click();
    await expect(page.getByText('1 bills selected')).toBeVisible();
    await page.getByRole('button', { name: 'Next: Batch Details' }).click();

    await page.locator('#pay-date').fill('2026-06-30');
    await page.locator('#bank-label').fill('Operating Account');
    await page.getByRole('button', { name: 'Create Batch' }).click();

    await expect(page.getByText('Draft - approval required')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Download CSV' })).toBeDisabled();

    await page.getByRole('button', { name: 'Approve Batch' }).click();
    await expect(page.getByText('Approved - ready to export')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Download CSV' })).toBeEnabled();

    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download CSV' }).click();
    await download;
    await expect(page.getByText('CSV export downloaded and recorded.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Mark as Sent to Bank' })).toBeEnabled();

    await page.getByRole('button', { name: 'Mark as Sent to Bank' }).click();
    await expect(page.getByRole('heading', { name: 'Batch sent to bank' })).toBeVisible();
    await page.getByRole('button', { name: 'Confirm Settlement' }).click();

    await expect(page.getByRole('heading', { name: 'Batch settled' })).toBeVisible();
    await expect(page.getByText('1 bills settled.')).toBeVisible();
    await expect(page.getByText('Journals: je-325')).toBeVisible();
  });
});
