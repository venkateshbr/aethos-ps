/**
 * Enterprise operational health proof for #311.
 *
 * The spec drives the real Settings route with mocked API contracts so it
 * verifies the browser-visible operator dashboard without requiring a live
 * Supabase tenant or outbound alert sink.
 */

import { expect, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

const hiddenSecrets = [
  'https://hooks.example.test/ops-secret-token',
  'ops-secret-token',
  'token_1234567890abcdef',
  'eyJhbGciOiJIUzI1NiJ9.secret.payload',
  'sk_live_ops_secret',
  'Confidential acquisition payroll document text',
  '{"public_invoice_token":"token_1234567890abcdef"}',
];

const tenantHealth = {
  status: 'degraded',
  tenant_id: 'tenant-ops',
  generated_at: '2026-06-25T02:00:00Z',
  runtime: {
    environment: 'production',
    debug: false,
    queue_configured: true,
    queue_required: true,
    extraction_mode: 'async',
  },
  rate_limit: {
    enabled: true,
    backend: 'supabase',
    distributed_configured: true,
    fallback_to_memory: true,
    window_seconds: 60,
  },
  checks: {
    tables: [
      { name: 'tenants', status: 'ok' },
      { name: 'rate_limit_events', status: 'ok' },
      { name: '0089_distributed_rate_limit_events', status: 'ok' },
      { name: 'agent_runs', status: 'ok' },
      { name: 'agent_tool_invocations', status: 'ok' },
      { name: 'agent_workflow_runs', status: 'ok' },
    ],
  },
  telemetry: {
    request_failures: [
      {
        method: 'GET',
        path: '/api/v1/public/invoices/{token}',
        status_code: 429,
        count: 12,
      },
    ],
    background_failures: [
      { worker_name: 'rate_limit_distributed_backend', count: 2 },
      { worker_name: 'close_scheduler_worker', count: 1 },
    ],
    failed_agent_runs_24h: 1,
    failed_tool_invocations_24h: 1,
    failed_workflow_runs_24h: 1,
    failed_tools_by_name_24h: [
      { tool_name: 'generate_financial_statement_package', count: 1 },
    ],
    window_start: '2026-06-24T02:00:00Z',
  },
  alerts: {
    route: {
      route_type: 'webhook',
      channel: 'secops',
      configured: true,
    },
    items: [
      {
        code: 'tenant_health_degraded',
        severity: 'warning',
        message: 'Tenant health is degraded.',
        count: 3,
        route_type: 'webhook',
        channel: 'secops',
        runbook: 'docs/test/e2e_ops_security.md#ops-alerts',
        metadata: { failed_tables: [] },
      },
      {
        code: 'public_endpoint_abuse',
        severity: 'warning',
        message: 'Repeated rate-limit denials crossed the alert threshold.',
        count: 12,
        route_type: 'webhook',
        channel: 'secops',
        runbook: 'docs/test/e2e_ops_security.md#ops-alerts',
        metadata: { paths: [{ path: '/api/v1/public/invoices/{token}', count: 12 }] },
      },
      {
        code: 'background_failure_spike',
        severity: 'warning',
        message: 'Background failures crossed the alert threshold.',
        count: 3,
        route_type: 'webhook',
        channel: 'secops',
        runbook: 'docs/test/e2e_ops_security.md#ops-alerts',
        metadata: { workers: [{ worker_name: 'rate_limit_distributed_backend', count: 2 }] },
      },
      {
        code: 'agent_failure_spike',
        severity: 'warning',
        message: 'Agent, tool, or workflow failures crossed the alert threshold.',
        count: 3,
        route_type: 'webhook',
        channel: 'secops',
        runbook: 'docs/test/e2e_ops_security.md#ops-alerts',
        metadata: {
          failed_tools_by_name: [
            { tool_name: 'generate_financial_statement_package', count: 1 },
          ],
        },
      },
    ],
  },
} as const;

async function authenticate(page: Page): Promise<void> {
  await page.goto(`${BASE}/`);
  await page.evaluate(() => {
    window.localStorage.setItem('aethos_token', 'mock-token-admin');
    window.localStorage.setItem('aethos_tenant_id', 'tenant-ops');
    window.localStorage.setItem('aethos_role', 'admin');
  });
}

async function installSettingsMocks(page: Page): Promise<void> {
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = request.url();

    if (request.method() !== 'GET') {
      await route.fulfill({ json: { ok: true } });
      return;
    }

    if (url.includes('/tenants/health')) {
      await route.fulfill({ json: tenantHealth });
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
    if (url.includes('/approval-policy/effective')) {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-ops',
          policy_source: 'system_default',
          money_out_default_role: 'manager',
          money_out_owner_threshold: '25000',
          money_out_owner_role: 'owner',
          accounting_role: 'admin',
          money_in_role: 'manager',
          draft_role: 'manager',
          external_send_role: 'admin',
          high_risk_role: 'owner',
          created_at: '2026-06-24T20:00:00Z',
          updated_at: '2026-06-24T20:00:00Z',
        },
      });
      return;
    }
    if (url.includes('/tenants/finance-personas')) {
      await route.fulfill({ json: { items: [] } });
      return;
    }
    if (url.includes('/collections/policies/effective')) {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-ops',
          policy_source: 'system_default',
          gentle_after_days: 7,
          firm_after_days: 30,
          pause_after_reminder_count: 3,
          updated_at: null,
        },
      });
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
    if (url.includes('/services')) {
      await route.fulfill({ json: { items: [] } });
      return;
    }
    if (url.includes('/tax-rates')) {
      await route.fulfill({ json: [] });
      return;
    }

    await route.fulfill({ json: { items: [], total: 0 } });
  });
}

test.describe('Enterprise operational health proof (#311)', () => {
  test('Settings Operational Health renders limiter, failure, and alert signals without secrets', async ({ page }) => {
    await installSettingsMocks(page);
    await authenticate(page);

    await page.goto(`${BASE}/app/settings`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible();
    const healthPanel = page.locator('app-tenant-health');
    await expect(healthPanel.getByRole('heading', { name: 'Operational Health' })).toBeVisible();
    await expect(healthPanel).toContainText('Degraded');
    await expect(healthPanel).toContainText('production');
    await expect(healthPanel).toContainText('Queue configured');
    await expect(healthPanel).toContainText('supabase');
    await expect(healthPanel).toContainText('Distributed');
    await expect(healthPanel).toContainText('fallback on');
    await expect(healthPanel).toContainText('tenants');
    await expect(healthPanel).toContainText('rate_limit_events');
    await expect(healthPanel).toContainText('0089_distributed_rate_limit_events');
    await expect(healthPanel).toContainText('/api/v1/public/invoices/{token} / 429');
    await expect(healthPanel).toContainText('rate_limit_distributed_backend');
    await expect(healthPanel).toContainText('Agent runs');
    await expect(healthPanel).toContainText('Tool invocations');
    await expect(healthPanel).toContainText('Workflow runs');
    await expect(healthPanel).toContainText('generate_financial_statement_package');
    await expect(healthPanel).toContainText('Webhook');
    await expect(healthPanel).toContainText('secops');
    await expect(healthPanel).toContainText('Tenant Health Degraded');
    await expect(healthPanel).toContainText('Public Endpoint Abuse');
    await expect(healthPanel).toContainText('Background Failure Spike');
    await expect(healthPanel).toContainText('Agent Failure Spike');

    for (const secret of hiddenSecrets) {
      await expect(page.locator('body')).not.toContainText(secret);
    }
  });
});
