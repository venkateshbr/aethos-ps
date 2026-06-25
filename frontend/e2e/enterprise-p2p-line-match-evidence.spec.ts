/**
 * Enterprise P2P line-level match evidence proof for #323.
 *
 * This spec proves the browser-visible AP surfaces for linked PO/SO line
 * exceptions. Backend match semantics are covered by the bills API contract
 * tests in backend/tests/unit/test_bills_api_contract.py.
 */

import { expect, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

const bill = {
  id: 'bill-p2p-323',
  bill_number: 'BILL-323',
  vendor_name: 'Aster Cloud Services',
  vendor_id: 'vendor-aster',
  client_id: 'vendor-aster',
  purchase_order_id: 'so-323',
  po_match_status: 'line_mismatch',
  po_match_summary: {
    status: 'line_mismatch',
    purchase_order_id: 'so-323',
    purchase_order_number: 'SO-0323',
    purchase_order_type: 'service_order',
    order_status: 'approved',
    order_total: '110.00',
    matched_bill_total: '0.00',
    remaining_before_bill: '110.00',
    bill_total: '110.00',
    tolerance: '0.01',
    line_match_status: 'mismatch',
    line_matches: [
      {
        bill_line_description: 'Implementation tooling',
        order_line_description: 'Implementation tooling',
        match_basis: 'description_exact',
        quantity: { bill: '2', order: '1', status: 'mismatch' },
        unit_price: { bill: '100.00', order: '100.00', status: 'matched' },
        amount: { bill: '100.00', order: '100.00', status: 'matched' },
        service_period: {
          bill_start: '2026-07-01',
          bill_end: '2026-07-31',
          order_start: '2026-06-01',
          order_end: '2026-06-30',
          status: 'mismatch',
        },
      },
    ],
    line_exceptions: [
      {
        code: 'quantity_mismatch',
        message: 'Bill line quantity differs from the linked PO/SO line',
        bill_line_description: 'Implementation tooling',
        order_line_description: 'Implementation tooling',
        bill_quantity: '2',
        order_quantity: '1',
      },
      {
        code: 'service_period_mismatch',
        message: 'Bill line service period falls outside the linked service order period',
        bill_line_description: 'Implementation tooling',
        order_line_description: 'Implementation tooling',
        service_period: {
          bill_start: '2026-07-01',
          bill_end: '2026-07-31',
          order_start: '2026-06-01',
          order_end: '2026-06-30',
          status: 'mismatch',
        },
      },
    ],
  },
  currency: 'USD',
  subtotal: '100.00',
  tax_total: '10.00',
  total: '110.00',
  amount: '110.00',
  status: 'draft',
  issue_date: '2026-07-01',
  due_date: '2026-07-31',
  vendor_invoice_number: 'ASTER-323',
  source_document_id: 'doc-p2p-323',
  vendor_invoice_review: {},
  lines: [
    {
      id: 'bill-line-p2p-323',
      description: 'Implementation tooling',
      quantity: '2',
      unit_price: '100.00',
      amount: '100.00',
      tax_amount: '10.00',
      service_start_date: '2026-07-01',
      service_end_date: '2026-07-31',
    },
  ],
};

const procurementDocuments = [
  {
    id: 'so-323',
    document_type: 'service_order',
    document_number: 'SO-0323',
    client_id: 'vendor-aster',
    status: 'approved',
    currency: 'USD',
    total: '110.00',
    remaining_total: '110.00',
  },
];

async function authenticate(page: Page): Promise<void> {
  await page.goto(`${BASE}/`);
  await page.evaluate(() => {
    window.localStorage.setItem('aethos_token', 'mock-token-p2p-323');
    window.localStorage.setItem('aethos_tenant_id', 'tenant-p2p-323');
    window.localStorage.setItem('aethos_role', 'admin');
  });
}

async function installMocks(page: Page): Promise<void> {
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (method !== 'GET') {
      await route.fulfill({ status: 403, json: { detail: 'Mutation blocked in #323 proof' } });
      return;
    }

    if (path === '/api/v1/bills/bill-p2p-323') {
      await route.fulfill({ json: bill });
      return;
    }
    if (path === '/api/v1/bills') {
      await route.fulfill({ json: { items: [bill], total: 1 } });
      return;
    }
    if (path === '/api/v1/procurement/documents') {
      await route.fulfill({ json: { items: procurementDocuments, total: procurementDocuments.length } });
      return;
    }
    if (path === '/api/v1/clients') {
      await route.fulfill({
        json: {
          items: [{ id: 'vendor-aster', name: 'Aster Cloud Services', kind: 'vendor' }],
          total: 1,
        },
      });
      return;
    }
    if (path.includes('/financial-events/business-records/bill/bill-p2p-323/decisions')) {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }
    if (path === '/api/v1/agents/runs' || path === '/api/v1/agents/workflow-runs') {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }

    await route.fulfill({ json: { items: [], total: 0 } });
  });
}

test.describe('Enterprise P2P line-level match evidence (#323)', () => {
  test('bills list and detail expose PO/SO line exceptions', async ({ page }) => {
    await installMocks(page);
    await authenticate(page);

    await page.goto(`${BASE}/app/bills`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: /^bills$/i })).toBeVisible();
    const billRow = page.getByRole('row').filter({ hasText: 'BILL-323' });
    await expect(billRow).toBeVisible();
    await expect(billRow.getByText('SO-0323')).toBeVisible();
    await expect(billRow.getByText('Line mismatch')).toBeVisible();
    await expect(billRow.getByText('Quantity mismatch +1 more')).toBeVisible();

    await billRow.click();
    await expect(page).toHaveURL(/\/app\/bills\/bill-p2p-323/);
    await expect(page.getByRole('heading', { name: 'BILL-323' })).toBeVisible();
    const evidence = page.getByLabel('PO / SO match evidence');
    await expect(evidence.getByRole('heading', { name: 'PO / SO match evidence' })).toBeVisible();
    await expect(evidence.getByText('Line evidence exception')).toBeVisible();
    await expect(evidence.getByText('Quantity mismatch', { exact: true })).toBeVisible();
    await expect(evidence.getByText('Service period mismatch', { exact: true })).toBeVisible();
    await expect(evidence.getByText('Order line: Implementation tooling')).toBeVisible();
    await expect(
      evidence.getByText('Qty mismatch, unit price matched, amount matched, service period mismatch'),
    ).toBeVisible();
  });
});
