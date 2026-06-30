/**
 * Enterprise controls/audit/RBAC proof for #309.
 *
 * The spec uses browser-visible routes with mocked API contracts so it proves
 * the Angular surfaces without requiring a live Supabase tenant. Backend API
 * assertions are covered by the contract tests referenced in the docs.
 */

import { expect, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

type MockRole = 'owner' | 'manager' | 'auditor' | 'viewer';

const approvalPolicy = {
  tenant_id: 'tenant-ctrl',
  policy_source: 'tenant_default',
  money_out_default_role: 'owner',
  money_out_owner_threshold: '25000',
  money_out_owner_role: 'owner',
  accounting_role: 'admin',
  money_in_role: 'manager',
  draft_role: 'manager',
  external_send_role: 'admin',
  high_risk_role: 'owner',
  created_at: '2026-06-24T20:00:00Z',
  updated_at: '2026-06-24T20:00:00Z',
};

const personas = [
  {
    id: 'owner_admin',
    label: 'Owner/Admin',
    mapped_roles: ['owner', 'admin'],
    description: 'Final finance control and tenant administration.',
    areas: ['Settings', 'Approvals', 'Payments'],
    allowed_actions: ['Configure tenant controls', 'Approve owner-threshold work'],
    restricted_actions: ['Tenant-scoped only'],
    read_only: false,
  },
  {
    id: 'controller',
    label: 'Controller',
    mapped_roles: ['admin', 'owner'],
    description: 'Owns close, accounting review, and statements.',
    areas: ['R2R', 'Reports', 'Audit'],
    allowed_actions: ['Review close and accounting evidence'],
    restricted_actions: ['Cannot bypass owner threshold'],
    read_only: false,
  },
  {
    id: 'auditor',
    label: 'Auditor',
    mapped_roles: ['auditor'],
    description: 'Read-only audit reviewer.',
    areas: ['Reports', 'Inbox history', 'Decision evidence'],
    allowed_actions: ['Inspect permitted records and decisions'],
    restricted_actions: ['Cannot create, approve, post, pay, send, lock, or change settings'],
    read_only: true,
  },
  {
    id: 'executive',
    label: 'Executive',
    mapped_roles: ['viewer'],
    description: 'Read-only management reviewer.',
    areas: ['Reports', 'Operational health'],
    allowed_actions: ['Inspect dashboards and summaries'],
    restricted_actions: ['Cannot mutate finance records'],
    read_only: true,
  },
];

const inboxTasks = [
  {
    id: 'task-owner-pay',
    tenant_id: 'tenant-ctrl',
    kind: 'create_bill_payment_batch',
    priority: 'high',
    title: 'Review high-value bill-pay batch',
    agent_name: 'finance_ops_manager',
    confidence: '0.92',
    status: 'open',
    created_at: '2026-06-24T20:00:00Z',
    suggestion_payload: {
      total_amount: '75000.00',
      currency: 'USD',
      proposed_bill_ids: ['bill-1'],
    },
    required_approval_role: 'owner',
    approval_policy_reason: 'money_out_above_owner_review_threshold',
    approval_policy: {
      required_role: 'owner',
      reason: 'money_out_above_owner_review_threshold',
      threshold: '25000',
    },
  },
  {
    id: 'task-approved-bill',
    tenant_id: 'tenant-ctrl',
    kind: 'create_bill',
    priority: 'normal',
    title: 'Reviewed vendor invoice bill',
    agent_name: 'vendor_invoice_agent',
    confidence: '0.88',
    status: 'done',
    created_at: '2026-06-23T20:00:00Z',
    suggestion_payload: {
      vendor_name: 'Aster Cloud Services',
      total_amount: '1200.00',
      currency: 'USD',
    },
    required_approval_role: 'manager',
    decision_history: [
      {
        id: 'event-task-approved',
        event_type: 'hitl_task.approved_with_edits',
        action: 'approved_with_edits',
        actor_user_id: 'controller-1',
        actor_role: 'admin',
        source_type: 'agent_suggestion',
        source_id: 'suggestion-1',
        before_state: {
          payload: { vendor_name: 'Aster Cloud', total_amount: '1200.00' },
          payload_hash: 'hash-before-reviewed-payload',
        },
        after_state: {
          payload: { vendor_name: 'Aster Cloud Services', total_amount: '1200.00' },
          payload_hash: 'hash-after-reviewed-payload',
          materialisation: { entity_type: 'bill', entity_id: 'bill-1' },
        },
        metadata: { decision_result: 'approved', source_hitl_task_id: 'task-approved-bill' },
        event_hash: 'hash-event-task-approved',
        created_at: '2026-06-24T20:15:00Z',
      },
    ],
  },
];

const billDetail = {
  id: 'bill-1',
  bill_number: 'BILL-309',
  vendor_name: 'Aster Cloud Services',
  currency: 'USD',
  subtotal: '1200.00',
  tax_total: '0.00',
  total: '1200.00',
  status: 'approved',
  issue_date: '2026-06-20',
  due_date: '2026-06-30',
  confidence: '0.88',
  vendor_invoice_review: {
    duplicate_review: { approved_duplicate: true, reason: 'Separate service period' },
  },
  lines: [
    {
      id: 'line-1',
      description: 'Cloud services',
      quantity: '1',
      unit_price: '1200.00',
      amount: '1200.00',
      tax_amount: '0.00',
    },
  ],
};

const billDecisionEvents = [
  {
    id: 'event-bill-approved',
    event_type: 'hitl_task.approved_with_edits',
    entity_type: 'bill',
    entity_id: 'bill-1',
    source_type: 'hitl_task',
    source_id: 'task-approved-bill',
    actor_user_id: 'controller-1',
    actor_role: 'admin',
    action: 'approved_with_edits',
    before_state: {
      task: { title: 'Reviewed vendor invoice bill', kind: 'create_bill' },
      payload: { vendor_name: 'Aster Cloud' },
      payload_hash: 'hash-before-reviewed-payload',
    },
    after_state: {
      task: { title: 'Reviewed vendor invoice bill', kind: 'create_bill' },
      payload: { vendor_name: 'Aster Cloud Services' },
      payload_hash: 'hash-after-reviewed-payload',
      materialisation: { entity_type: 'bill', entity_id: 'bill-1' },
    },
    metadata: { source_hitl_task_id: 'task-approved-bill' },
    event_hash: 'hash-event-bill-projection',
    created_at: '2026-06-24T20:15:00Z',
  },
];

async function authenticate(page: Page, role: MockRole): Promise<void> {
  await page.goto(`${BASE}/`);
  await page.evaluate(({ currentRole }) => {
    window.localStorage.setItem('aethos_token', `mock-token-${currentRole}`);
    window.localStorage.setItem('aethos_tenant_id', 'tenant-ctrl');
    window.localStorage.setItem('aethos_role', currentRole);
  }, { currentRole: role });
}

async function installEnterpriseMocks(page: Page): Promise<{ deniedApprovals: string[] }> {
  const deniedApprovals: string[] = [];

  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    if (request.method() !== 'GET') {
      await route.fulfill({ status: 403, json: { detail: 'Mocked RBAC denial for enterprise proof' } });
      return;
    }

    const url = request.url();
    if (
      url.includes('/approval-policy/')
      || url.includes('/tenants/finance-personas')
      || url.includes('/inbox/tasks')
      || url.includes('/bills/bill-1')
      || url.includes('/financial-events/business-records/bill/bill-1/decisions')
      || url.includes('/procurement/documents')
    ) {
      await route.fallback();
      return;
    }

    if (url.includes('/agents/runs')) {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }
    if (url.includes('/agents/workflow-runs')) {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }
    if (url.includes('/agents/autonomy-status')) {
      await route.fulfill({ json: { agents: [] } });
      return;
    }
    if (url.includes('/agents/finance-ops/schedule')) {
      await route.fulfill({
        json: {
          enabled: true,
          cadence: 'daily',
          run_hour_utc: 7,
          run_day_of_week: null,
          period_mode: 'current_month',
          max_work_items: 5,
          stale_after_hours: 24,
          high_risk_stale_after_hours: 4,
          escalation_enabled: true,
          updated_at: '2026-06-24T20:00:00Z',
          last_run_at: null,
        },
      });
      return;
    }
    if (url.includes('/tenants/health')) {
      await route.fulfill({
        json: {
          status: 'ok',
          generated_at: '2026-06-24T20:00:00Z',
          runtime: {
            environment: 'test',
            debug: false,
            queue_configured: true,
            queue_required: false,
            extraction_mode: 'sync',
          },
          rate_limit: {
            enabled: true,
            backend: 'supabase',
            distributed_configured: true,
            fallback_to_memory: true,
            window_seconds: 60,
          },
          checks: { tables: [{ name: 'financial_events', status: 'ok' }] },
          telemetry: {
            request_failures: [],
            background_failures: [],
            failed_agent_runs_24h: 0,
            failed_tool_invocations_24h: 0,
            failed_workflow_runs_24h: 0,
            failed_tools_by_name_24h: [],
            window_start: '2026-06-24T00:00:00Z',
          },
          alerts: { route: { route_type: 'runbook_queue', channel: 'runbook', configured: false }, items: [] },
        },
      });
      return;
    }
    if (url.includes('/services')) {
      await route.fulfill({ json: { items: [] } });
      return;
    }
    if (url.includes('/tax-rates')) {
      await route.fulfill({ json: [] });
      return;
    }
    if (url.includes('/integrations/catalog')) {
      await route.fulfill({ json: { integrations: [], total: 0 } });
      return;
    }
    if (url.includes('/stripe/connect/status')) {
      await route.fulfill({ json: { connected: false } });
      return;
    }
    if (url.includes('/collections/policies/effective')) {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-ctrl',
          policy_source: 'system_default',
          gentle_after_days: 7,
          firm_after_days: 30,
          pause_after_reminder_count: 3,
          updated_at: null,
        },
      });
      return;
    }

    await route.fulfill({ json: { items: [], total: 0 } });
  });

  await page.route('**/api/v1/approval-policy/effective', async route => {
    await route.fulfill({ json: approvalPolicy });
  });
  await page.route('**/api/v1/approval-policy/default', async route => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({ json: { ...approvalPolicy, policy_source: 'tenant_default' } });
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/v1/tenants/finance-personas', async route => {
    await route.fulfill({ json: { items: personas } });
  });
  await page.route('**/api/v1/inbox/tasks?**', async route => {
    const url = new URL(route.request().url());
    const status = url.searchParams.get('status') ?? 'open';
    const items = status === 'done'
      ? inboxTasks.filter(task => task.status === 'done')
      : inboxTasks.filter(task => task.status === 'open');
    await route.fulfill({ json: { items, total: items.length } });
  });
  await page.route('**/api/v1/inbox/tasks/task-owner-pay/approve', async route => {
    deniedApprovals.push(route.request().postData() ?? '');
    await route.fulfill({
      status: 403,
      json: {
        detail: 'Approval requires owner or higher',
      },
    });
  });
  await page.route('**/api/v1/bills/bill-1', async route => {
    await route.fulfill({ json: billDetail });
  });
  await page.route('**/api/v1/financial-events/business-records/bill/bill-1/decisions', async route => {
    await route.fulfill({ json: { items: billDecisionEvents, total: billDecisionEvents.length } });
  });
  await page.route('**/api/v1/bills?**', async route => {
    await route.fulfill({ json: { items: [billDetail], total: 1 } });
  });
  await page.route('**/api/v1/procurement/documents**', async route => {
    await route.fulfill({ json: { items: [], total: 0 } });
  });

  return { deniedApprovals };
}

test.describe('Enterprise controls, audit, and RBAC proof (#309)', () => {
  test('approval policy and finance personas are browser-visible controls', async ({ page }) => {
    await installEnterpriseMocks(page);
    await authenticate(page, 'owner');

    await page.goto(`${BASE}/app/settings`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Approval Controls' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Finance role personas' })).toBeVisible();
    await expect(page.getByText('Current enforced role')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Owner/Admin' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Controller' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Auditor' })).toBeVisible();
    await expect(page.getByText('Approval Policy Matrix')).toBeVisible();
    await expect(page.getByLabel('Money-out default')).toHaveValue('owner');
    await expect(page.getByLabel('Owner threshold')).toHaveValue('25000');
    await expect(page.getByLabel('External send')).toHaveValue('admin');
  });

  test('manager sees owner-required Inbox work but cannot approve it', async ({ page }) => {
    const mocks = await installEnterpriseMocks(page);
    await authenticate(page, 'manager');

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });

    const card = page.getByRole('article', { name: 'Review high-value bill-pay batch' });
    await expect(card).toBeVisible();
    await expect(card.getByText('Owner approval')).toBeVisible();
    await expect(card.getByText('total amount:')).toBeVisible();
    await expect(card.getByRole('button', { name: /Approval requires Owner/i })).toBeDisabled();
    await expect(page.getByText('Review high-value bill-pay batch')).toBeVisible();
    expect(mocks.deniedApprovals).toEqual([]);
  });

  test('Inbox done view and bill detail expose immutable decision evidence', async ({ page }) => {
    await installEnterpriseMocks(page);
    await authenticate(page, 'owner');

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: /^Done$/i }).click();

    const doneCard = page.getByRole('article', { name: 'Reviewed vendor invoice bill' });
    await expect(doneCard).toBeVisible();
    await expect(doneCard.getByText('Decision history')).toBeVisible();
    await expect(doneCard.getByText('Approved With Edits')).toBeVisible();
    await expect(doneCard.getByText('Admin')).toBeVisible();
    await expect(doneCard.getByText('bill: bill-1')).toBeVisible();

    await page.goto(`${BASE}/app/bills/bill-1`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'BILL-309' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Decision timeline' })).toBeVisible();
    await expect(page.getByText('Immutable approval and review events for this record.')).toBeVisible();
    await expect(page.getByText('Approved With Edits')).toBeVisible();
    await expect(page.getByText('payload changed hash-before- -> hash-after-r')).toBeVisible();
    await expect(page.getByText('hash hash-event-b')).toBeVisible();
    await expect(page.getByText('mock-token')).toHaveCount(0);
  });

  test('auditor persona can inspect but mutation controls stay blocked', async ({ page }) => {
    await installEnterpriseMocks(page);
    await authenticate(page, 'auditor');

    await page.goto(`${BASE}/app/settings`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByText('Current enforced role')).toBeVisible();
    await expect(
      page.getByText('Current enforced role').locator('..').locator('p.text-sm.font-medium'),
    ).toHaveText('Auditor');
    await expect(page.getByText('Read-only audit reviewer.')).toBeVisible();
    await expect(page.getByText('Cannot create, approve, post, pay, send, lock, or change settings')).toBeVisible();
    await expect(page.getByText('Approval policy changes require Admin or Owner.')).toBeVisible();
    await expect(page.getByLabel('Approval Controls').getByRole('button', { name: /Save Policy/i })).toBeDisabled();

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    const card = page.getByRole('article', { name: 'Review high-value bill-pay batch' });
    await expect(card.getByRole('button', { name: /Approval requires Owner/i })).toBeDisabled();

    await page.goto(`${BASE}/app/bills/bill-1`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'BILL-309' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Decision timeline' })).toBeVisible();
  });
});
