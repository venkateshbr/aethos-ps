/**
 * Scheduled Finance Ops Manager browser proof for #317.
 *
 * The spec uses real Angular routes with mocked API contracts so it proves the
 * operator-facing schedule, Inbox, and workflow-ledger surfaces deterministically.
 */

import { expect, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

type MockRole = 'admin' | 'manager';

interface MockState {
  schedule: Record<string, unknown>;
  savedSchedules: Record<string, unknown>[];
}

function createState(): MockState {
  return {
    schedule: {
      tenant_id: 'tenant-aiops',
      is_enabled: true,
      cadence: 'daily',
      run_hour_utc: 7,
      run_weekday_utc: 0,
      timezone: 'UTC',
      period_mode: 'current_month',
      lookback_limit: 10,
      stale_after_hours: 24,
      high_risk_stale_after_hours: 4,
      escalation_enabled: true,
      is_seeded_default: true,
      created_at: null,
      updated_at: null,
    },
    savedSchedules: [],
  };
}

const scheduledPlanTask = {
  id: 'task-scheduled-plan-317',
  tenant_id: 'tenant-aiops',
  kind: 'copilot_create_finance_ops_action_plan',
  priority: 'high',
  title: 'Scheduled finance ops action plan for June 2026',
  agent_name: 'finance_ops_manager',
  confidence: '0.93',
  status: 'open',
  created_at: '2026-06-25T07:05:00Z',
  required_approval_role: 'manager',
  approval_policy_reason: 'finance_ops_action_plan_requires_manager_review',
  suggestion_payload: {
    preview: {
      period: '2026-06',
      status: 'waiting_on_human',
      action_count: 4,
      requires_inbox_approval_count: 4,
      domains: 'AR, AP, close, reporting',
    },
    source: 'scheduled_finance_ops_manager',
    cadence_window: '2026-06-25T07:00:00Z',
  },
};

const escalationTask = {
  id: 'task-finance-ops-escalation-317',
  tenant_id: 'tenant-aiops',
  kind: 'finance_ops_escalation',
  priority: 'critical',
  title: 'Escalate stale high-risk bill-pay approval',
  agent_name: 'finance_ops_manager',
  confidence: '0.91',
  status: 'open',
  created_at: '2026-06-25T07:06:00Z',
  required_approval_role: 'owner',
  approval_policy_reason: 'high_risk_stale_approval',
  suggestion_payload: {
    source_task_id: 'task-high-risk-payments',
    source_task_kind: 'create_bill_payment_batch',
    source_task_title: 'Approve high-value supplier payment batch',
    stale_hours: 9,
    high_risk_stale_after_hours: 4,
    recommended_action: 'Owner/Admin should review the original task.',
  },
};

const workflowRuns = {
  workflow_runs: [
    {
      id: 'workflow-scheduled-finance-ops-317',
      tenant_id: 'tenant-aiops',
      workflow_name: 'scheduled_finance_ops_manager',
      status: 'waiting_on_human',
      owner_agent_name: 'finance_ops_manager',
      user_id: null,
      current_step: 'hitl_review',
      goal_snapshot: {
        cadence: 'daily',
        period: '2026-06',
        creates_reviewed_action_plan: true,
      },
      state_snapshot: {
        action_plan_task_id: 'task-scheduled-plan-317',
        escalations_created: 1,
        work_items_created: 4,
      },
      trace_id: 'trace-scheduled-finance-ops-317',
      replay_pointer: 'agent_workflow_runs/workflow-scheduled-finance-ops-317',
      error_message: null,
      started_at: '2026-06-25T07:00:00Z',
      completed_at: null,
      created_at: '2026-06-25T07:00:00Z',
      updated_at: '2026-06-25T07:06:00Z',
    },
  ],
  total: 1,
};

async function authenticate(page: Page, role: MockRole): Promise<void> {
  await page.goto(`${BASE}/`);
  await page.evaluate(({ currentRole }) => {
    window.localStorage.setItem('aethos_token', `mock-token-${currentRole}`);
    window.localStorage.setItem('aethos_tenant_id', 'tenant-aiops');
    window.localStorage.setItem('aethos_role', currentRole);
  }, { currentRole: role });
}

async function installMocks(page: Page, state: MockState): Promise<void> {
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = request.url();
    const method = request.method();

    if (url.includes('/agents/finance-ops/schedule')) {
      if (method === 'PUT') {
        const body = request.postDataJSON() as Record<string, unknown>;
        state.savedSchedules.push(body);
        state.schedule = {
          ...state.schedule,
          ...body,
          is_seeded_default: false,
          updated_at: '2026-06-25T07:10:00Z',
        };
      }
      await route.fulfill({ json: state.schedule });
      return;
    }

    if (url.includes('/inbox/tasks')) {
      await route.fulfill({
        json: {
          items: [scheduledPlanTask, escalationTask],
          total: 2,
        },
      });
      return;
    }

    if (url.includes('/agents/workflow-runs')) {
      await route.fulfill({ json: workflowRuns });
      return;
    }

    if (method !== 'GET') {
      await route.fulfill({ status: 403, json: { detail: 'Mocked mutation blocked' } });
      return;
    }

    if (url.includes('/agents/runs')) {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }
    if (url.includes('/agents/autonomy-status')) {
      await route.fulfill({ json: { agents: [] } });
      return;
    }
    if (url.includes('/tenants/health')) {
      await route.fulfill({
        json: {
          status: 'ok',
          generated_at: '2026-06-25T07:00:00Z',
          runtime: {
            environment: 'test',
            debug: false,
            queue_configured: true,
            queue_required: false,
            extraction_mode: 'sync',
          },
          rate_limit: {
            enabled: true,
            backend: 'memory',
            distributed_configured: false,
            fallback_to_memory: true,
            window_seconds: 60,
          },
          checks: { tables: [{ name: 'agent_workflow_runs', status: 'ok' }] },
          telemetry: {
            request_failures: [],
            background_failures: [],
            failed_agent_runs_24h: 0,
            failed_tool_invocations_24h: 0,
            failed_workflow_runs_24h: 0,
            failed_tools_by_name_24h: [],
            window_start: '2026-06-24T07:00:00Z',
          },
          alerts: {
            route: { route_type: 'runbook_queue', channel: 'runbook', configured: false },
            items: [],
          },
        },
      });
      return;
    }
    if (url.includes('/approval-policy/effective')) {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-aiops',
          policy_source: 'system_default',
          money_out_default_role: 'manager',
          money_out_owner_threshold: '25000',
          money_out_owner_role: 'owner',
          accounting_role: 'admin',
          money_in_role: 'manager',
          draft_role: 'manager',
          external_send_role: 'admin',
          high_risk_role: 'owner',
          created_at: '2026-06-25T07:00:00Z',
          updated_at: '2026-06-25T07:00:00Z',
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
          tenant_id: 'tenant-aiops',
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

test.describe('Scheduled Finance Ops Manager proof (#317)', () => {
  test('admin configures schedule and sees scheduled output in Inbox and workflow ledger', async ({ page }) => {
    const state = createState();
    await installMocks(page, state);
    await authenticate(page, 'admin');

    await page.goto(`${BASE}/app/settings`, { waitUntil: 'domcontentloaded' });

    const schedulePanel = page.locator('app-finance-ops-schedule');
    await expect(schedulePanel.getByRole('heading', { name: 'Finance Ops Manager Schedule' })).toBeVisible();
    await expect(schedulePanel).toContainText('Default schedule');
    await schedulePanel.getByLabel('Cadence').selectOption('weekly');
    await schedulePanel.getByLabel('Run day').selectOption({ label: 'Wednesday' });
    await schedulePanel.getByLabel('Run hour UTC').fill('8');
    await schedulePanel.getByLabel('Timezone').fill('UTC');
    await schedulePanel.getByLabel('Period').selectOption('previous_month');
    await schedulePanel.getByLabel('Work item limit').fill('12');
    await schedulePanel.getByLabel('High-risk stale hours').fill('6');
    await schedulePanel.getByRole('spinbutton', { name: 'Stale hours', exact: true }).fill('48');
    await schedulePanel.getByRole('button', { name: 'Save Schedule' }).click();

    await expect(schedulePanel).toContainText('Finance Ops Manager schedule saved.');
    await expect(schedulePanel).toContainText('Tenant schedule');
    expect(state.savedSchedules).toEqual([
      {
        is_enabled: true,
        cadence: 'weekly',
        run_hour_utc: 8,
        run_weekday_utc: 2,
        timezone: 'UTC',
        period_mode: 'previous_month',
        lookback_limit: 12,
        stale_after_hours: 48,
        high_risk_stale_after_hours: 6,
        escalation_enabled: true,
      },
    ]);

    const workflowPanel = page.locator('app-agent-workflow-runs');
    await expect(workflowPanel).toContainText('Scheduled Finance Ops Manager');
    await expect(workflowPanel).toContainText('Waiting On Human');
    await expect(workflowPanel).toContainText('hitl_review');
    await workflowPanel.getByRole('row', { name: /Scheduled Finance Ops Manager/i }).click();
    await expect(workflowPanel).toContainText('creates_reviewed_action_plan');
    await expect(workflowPanel).toContainText('escalations_created');

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    const planCard = page.getByRole('article', { name: 'Scheduled finance ops action plan for June 2026' });
    await expect(planCard).toBeVisible();
    await expect(planCard).toContainText('Manager approval');
    await expect(planCard).toContainText('period:');
    await expect(planCard).toContainText('2026-06');
    await expect(planCard).toContainText('action count:');
    await expect(planCard).toContainText('4');
    await expect(planCard).toContainText('domains:');
    await expect(planCard).toContainText('AR, AP, close, reporting');

    const escalationCard = page.getByRole('article', { name: 'Escalate stale high-risk bill-pay approval' });
    await expect(escalationCard).toBeVisible();
    await expect(escalationCard).toContainText('Owner approval');
    await expect(escalationCard).toContainText('critical');
  });

  test('manager can inspect schedule but cannot save changes', async ({ page }) => {
    const state = createState();
    await installMocks(page, state);
    await authenticate(page, 'manager');

    await page.goto(`${BASE}/app/settings`, { waitUntil: 'domcontentloaded' });

    const schedulePanel = page.locator('app-finance-ops-schedule');
    await expect(schedulePanel).toContainText('Finance Ops Manager Schedule');
    await expect(schedulePanel).toContainText('Schedule changes require Admin or Owner.');
    await expect(schedulePanel.getByLabel('Run hour UTC')).toBeDisabled();
    await expect(schedulePanel.getByRole('button', { name: 'Save Schedule' })).toBeDisabled();
    expect(state.savedSchedules).toEqual([]);
  });
});
