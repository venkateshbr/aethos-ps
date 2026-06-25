/**
 * Enterprise R2R year-end close proof for #327.
 *
 * Uses mocked API contracts to prove the Accounting close panel can post the
 * retained-earnings closing journal and refresh the journal list evidence.
 */

import { expect, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

interface MockState {
  yearEndJournal: null | {
    id: string;
    entry_number: string;
    description: string;
    entry_date: string;
    reference_type: string;
    posted_by: string;
    total_dr: string;
  };
}

async function authenticate(page: Page): Promise<void> {
  await page.goto(`${BASE}/`);
  await page.evaluate(() => {
    window.localStorage.setItem('aethos_token', 'mock-token-r2r-327');
    window.localStorage.setItem('aethos_tenant_id', 'tenant-r2r-327');
    window.localStorage.setItem('aethos_role', 'admin');
  });
}

async function installMocks(page: Page, state: MockState): Promise<void> {
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (path === '/api/v1/accounting/journal-entries' && method === 'GET') {
      await route.fulfill({
        json: [
          {
            id: 'journal-month-close-327',
            entry_number: 'JE-327',
            description: 'Month-end accrual',
            entry_date: '2026-06-30',
            reference_type: 'manual',
            posted_by: 'controller-327',
            total_dr: '300.00',
          },
          ...(state.yearEndJournal ? [state.yearEndJournal] : []),
        ],
      });
      return;
    }

    if (path.match(/^\/api\/v1\/accounting\/periods\/\d{4}-\d{2}\/close-tasks$/)) {
      await route.fulfill({ json: { tasks: [] } });
      return;
    }

    if (path.match(/^\/api\/v1\/accounting\/periods\/\d{4}-\d{2}\/close-package$/)) {
      await route.fulfill({
        json: {
          period: '2026-06',
          previous_period: '2026-05',
          generated_at: '2026-06-30T23:59:00+00:00',
          close_status: {
            status: 'ready',
            ready_to_lock: true,
            locked: false,
            checklist: [],
            lock_blockers: [],
          },
          gl_summary: { net_income: '900.00' },
          previous_gl_summary: { net_income: '500.00' },
          working_capital: {
            ar_open_total: '0.00',
            ap_open_total: '0.00',
            wip_total: '0.00',
          },
          readiness_evidence: {},
          close_overrides: [],
          variance_commentary: [
            {
              code: 'net_income_variance',
              severity: 'medium',
              summary: 'Net income increased versus the prior period.',
              delta: '400.00',
              delta_pct: 80,
            },
          ],
          trial_balance: {},
          ar_aging: {},
          ap_aging: {},
          wip: [],
          service_line_margins: [],
        },
      });
      return;
    }

    if (path === '/api/v1/accounting/recurring-journal-templates' && method === 'GET') {
      await route.fulfill({ json: { templates: [] } });
      return;
    }

    const yearEndMatch = path.match(/^\/api\/v1\/accounting\/years\/(\d{4})\/year-end-close$/);
    if (yearEndMatch && method === 'POST') {
      const year = Number(yearEndMatch[1]);
      state.yearEndJournal = {
        id: `journal-year-end-${year}`,
        entry_number: `YE-${year}`,
        description: `Year-end close ${year}: roll P&L to retained earnings`,
        entry_date: `${year}-12-31`,
        reference_type: 'year_end_close',
        posted_by: 'controller-327',
        total_dr: '1200.00',
      };
      await route.fulfill({
        json: {
          year,
          period: `${year}-12`,
          entry_date: `${year}-12-31`,
          journal_entry_id: state.yearEndJournal.id,
          entry_number: state.yearEndJournal.entry_number,
          posted_at: `${year}-12-31T23:59:00+00:00`,
          net_income: '900.00',
          retained_earnings_direction: 'CR',
          retained_earnings_amount: '900.00',
          retained_earnings_account: {
            id: 'acct-3000',
            code: '3000',
            name: 'Retained Earnings',
          },
          revenue_closed: '1200.00',
          expenses_closed: '300.00',
          line_count: 3,
        },
      });
      return;
    }

    await route.fulfill({ json: { items: [], total: 0 } });
  });
}

test.describe('Enterprise R2R year-end close (#327)', () => {
  test('Accounting panel posts retained-earnings close and refreshes journal evidence', async ({ page }) => {
    const state: MockState = { yearEndJournal: null };
    await installMocks(page, state);
    await authenticate(page);

    await page.goto(`${BASE}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: /^Month-end close$/i })).toBeVisible();
    await expect(page.getByText('Year-end close', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Post year-end close' }).click();

    await expect(page.getByText(/Year-end close YE-\d{4} posted to retained earnings\./)).toBeVisible();
    await expect(page.getByText('Net income', { exact: true })).toBeVisible();
    await expect(page.getByText('$900.00', { exact: true })).toBeVisible();
    await expect(page.getByText(/CR\s+\$900\.00/)).toBeVisible();
    const yearEndRow = page
      .getByRole('row')
      .filter({ hasText: /YE-\d{4}/ })
      .filter({ hasText: /Year-end close \d{4}: roll P&L to retained earnings/ });
    await expect(yearEndRow).toBeVisible();
  });
});
