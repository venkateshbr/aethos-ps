/**
 * Enterprise AI finance workflow proof for #310.
 *
 * The spec drives browser routes with mocked public API contracts. The prompts
 * typed into Copilot are business-language prompts; internal tool names appear
 * only in ledger evidence rendered after the fact.
 */

import { expect, Page, test } from '@playwright/test';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';
const CLOSE_PERIOD = '2026-06';

type MockRole = 'owner' | 'admin' | 'manager' | 'viewer';

interface MockState {
  vendorTaskOpen: boolean;
  billCreated: boolean;
  paymentTaskOpen: boolean;
  paymentBatchCreated: boolean;
  closeTaskOpen: boolean;
  closeApproved: boolean;
  overrideCreated: boolean;
  prompts: string[];
  p2pEdits: Record<string, unknown>[];
}

const forbiddenPromptFragments = [
  'propose_bill_payment_batch',
  'prepare_month_end_close',
  'generate_financial_statement_package',
  'create_bill_draft',
  'tool_name',
  'Use the',
];

const p2pPrompt = [
  'Process this vendor invoice for Aster Cloud Services.',
  'Match it to the right vendor and project, flag any duplicate risk, code it to software subscriptions,',
  'send exceptions to Inbox for review, and prepare a bill-pay proposal after the bill is reviewed.',
].join(' ');

const r2rPrompt = [
  'Run month-end close readiness for June 2026.',
  'Prepare the close review package, capture any controller override evidence,',
  'and generate financial statement commentary for the management pack.',
].join(' ');

const baseVendorPayload = {
  vendor_name: 'Aster Cloud Services',
  vendor_invoice_number: 'AST-2026-0615',
  currency: 'USD',
  subtotal: '1180.00',
  tax_total: '0.00',
  total: '1180.00',
  issue_date: '2026-06-15',
  due_date: '2026-06-30',
  original_document_id: 'doc-ai-310',
  source_document_id: 'doc-ai-310',
  possible_duplicate: true,
  duplicate_review: {},
  vendor_match: {
    vendor_id: 'vendor-aster',
    confidence: 0.91,
    match_reason: 'Name and remittance domain match vendor master.',
  },
  match_status: 'matched',
  coding_status: 'needs_review',
  project_hints: [{ project_id: 'project-cloud', project_name: 'Cloud migration' }],
  customer_hints: [{ client_id: 'client-nexus', client_name: 'Nexus Advisory' }],
  gl_suggestions: [
    {
      account_code: '6000',
      account_name: 'Software Subscriptions',
      confidence: 0.84,
    },
  ],
  review_exceptions: [
    {
      code: 'possible_duplicate',
      message: 'Invoice number resembles prior vendor invoice AST-2026-0601.',
    },
  ],
};

const paymentPayload = {
  bill_count: 1,
  currency: 'USD',
  total_amount: '1180.00',
  proposed_pay_date: '2026-06-28',
  proposed_bill_ids: ['bill-ai-310'],
  flagged_for_review_count: 1,
};

const closePayload = {
  period: CLOSE_PERIOD,
  workflow: 'month_end_close',
  lock_blocker_count: 2,
  pending_review_count: 1,
  override_count: 0,
  net_income: '18250.00',
  variance_comment_count: 2,
};

const closeOverride = {
  id: 'override-ai-310',
  period: CLOSE_PERIOD,
  blocker_code: 'close_tasks',
  reason: 'Controller reviewed AP accrual evidence and approved temporary close-task override for board reporting.',
  created_by: 'controller-1',
  created_by_role: 'admin',
  created_at: '2026-06-24T20:45:00Z',
  blocker_ref: {
    source: 'accounting_close_panel',
    blocker_status: 'blocked',
    blocker_summary: 'One AP accrual review remains open.',
  },
};

function createState(): MockState {
  return {
    vendorTaskOpen: true,
    billCreated: false,
    paymentTaskOpen: true,
    paymentBatchCreated: false,
    closeTaskOpen: true,
    closeApproved: false,
    overrideCreated: false,
    prompts: [],
    p2pEdits: [],
  };
}

async function authenticate(page: Page, role: MockRole = 'admin'): Promise<void> {
  await page.goto(`${BASE}/`);
  await page.evaluate(({ currentRole }) => {
    window.localStorage.setItem('aethos_token', `mock-token-${currentRole}`);
    window.localStorage.setItem('aethos_tenant_id', 'tenant-ai-finance');
    window.localStorage.setItem('aethos_role', currentRole);
  }, { currentRole: role });
}

async function sendCopilotBusinessPrompt(page: Page, prompt: string): Promise<void> {
  await page.goto(`${BASE}/app/copilot`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: 'Aethos Atlas' })).toBeVisible();
  await page.getByLabel('Message input').fill(prompt);
  await page.getByRole('button', { name: 'Send message' }).click();
  await expect(page.getByLabel(`You: ${prompt}`)).toBeVisible();
}

function assertBusinessPrompt(prompt: string): void {
  for (const forbidden of forbiddenPromptFragments) {
    expect(prompt).not.toContain(forbidden);
  }
}

function taskBase(overrides: Record<string, unknown>): Record<string, unknown> {
  return {
    tenant_id: 'tenant-ai-finance',
    priority: 'high',
    confidence: '0.91',
    status: 'open',
    created_at: '2026-06-24T20:00:00Z',
    required_approval_role: 'manager',
    ...overrides,
  };
}

function vendorInvoiceTask(state: MockState): Record<string, unknown> {
  return taskBase({
    id: 'task-vendor-invoice-ai-310',
    kind: 'create_bill_draft',
    title: 'Review duplicate vendor invoice from Aster Cloud Services',
    agent_name: 'vendor_invoice_agent',
    suggestion_payload: {
      ...baseVendorPayload,
      ...(state.p2pEdits[0] ?? {}),
    },
  });
}

function paymentTask(): Record<string, unknown> {
  return taskBase({
    id: 'task-payment-ai-310',
    kind: 'create_bill_payment_batch',
    title: 'Review AI bill-pay run for Aster Cloud Services',
    agent_name: 'bill_pay_agent',
    required_approval_role: 'admin',
    suggestion_payload: paymentPayload,
  });
}

function closeTask(): Record<string, unknown> {
  return taskBase({
    id: 'task-close-ai-310',
    kind: 'copilot_prepare_month_end_close',
    title: 'Review June 2026 month-end close package',
    agent_name: 'accounting_close_agent',
    required_approval_role: 'admin',
    suggestion_payload: closePayload,
  });
}

function openTasks(state: MockState): Record<string, unknown>[] {
  const items: Record<string, unknown>[] = [];
  if (state.vendorTaskOpen) items.push(vendorInvoiceTask(state));
  if (state.billCreated && state.paymentTaskOpen) items.push(paymentTask());
  if (state.closeTaskOpen) items.push(closeTask());
  return items;
}

function doneTasks(state: MockState): Record<string, unknown>[] {
  const items: Record<string, unknown>[] = [];
  if (!state.vendorTaskOpen && state.billCreated) {
    items.push({
      ...vendorInvoiceTask(state),
      status: 'done',
      decision_history: [billDecisionEvent()],
    });
  }
  if (!state.paymentTaskOpen && state.paymentBatchCreated) {
    items.push({
      ...paymentTask(),
      status: 'done',
      decision_history: [paymentDecisionEvent()],
    });
  }
  if (!state.closeTaskOpen && state.closeApproved) {
    items.push({
      ...closeTask(),
      status: 'done',
      decision_history: [closeDecisionEvent()],
    });
  }
  return items;
}

function billDetail(state: MockState): Record<string, unknown> {
  const reviewedPayload = {
    ...baseVendorPayload,
    ...(state.p2pEdits[0] ?? {
      duplicate_review: {
        approved_duplicate: true,
        reason: 'Separate service period validated against the contract.',
      },
    }),
  };
  return {
    id: 'bill-ai-310',
    bill_number: 'BILL-AI-310',
    vendor_id: 'vendor-aster',
    vendor_name: 'Aster Cloud Services',
    source_document_id: 'doc-ai-310',
    currency: 'USD',
    subtotal: '1180.00',
    tax_total: '0.00',
    total: '1180.00',
    status: 'approved',
    issue_date: '2026-06-15',
    due_date: '2026-06-30',
    confidence: '0.91',
    vendor_invoice_review: reviewedPayload,
    lines: [
      {
        id: 'line-ai-310',
        description: 'Cloud platform subscription',
        quantity: '1',
        unit_price: '1180.00',
        amount: '1180.00',
        tax_amount: '0.00',
      },
    ],
  };
}

function billDecisionEvent(): Record<string, unknown> {
  return {
    id: 'event-bill-ai-310',
    event_type: 'hitl_task.approved_with_edits',
    entity_type: 'bill',
    entity_id: 'bill-ai-310',
    source_type: 'hitl_task',
    source_id: 'task-vendor-invoice-ai-310',
    actor_user_id: 'controller-1',
    actor_role: 'admin',
    action: 'approved_with_edits',
    before_state: {
      task: { title: 'Review duplicate vendor invoice from Aster Cloud Services', kind: 'create_bill_draft' },
      payload: { total: '1180.00', duplicate_review: {} },
      payload_hash: 'hash-before-vendor-invoice',
    },
    after_state: {
      task: { title: 'Review duplicate vendor invoice from Aster Cloud Services', kind: 'create_bill_draft' },
      payload: {
        total: '1180.00',
        duplicate_review: { approved_duplicate: true, reason: 'Separate service period validated.' },
      },
      payload_hash: 'hash-after-vendor-invoice-reviewed',
      materialisation: { entity_type: 'bill', entity_id: 'bill-ai-310' },
    },
    metadata: { source_hitl_task_id: 'task-vendor-invoice-ai-310' },
    event_hash: 'hash-event-bill-ai-310',
    created_at: '2026-06-24T20:15:00Z',
  };
}

function paymentDecisionEvent(): Record<string, unknown> {
  return {
    id: 'event-payment-ai-310',
    event_type: 'hitl_task.approved',
    entity_type: 'bill_payment_batch',
    entity_id: 'batch-ai-310',
    source_type: 'hitl_task',
    source_id: 'task-payment-ai-310',
    actor_user_id: 'controller-1',
    actor_role: 'admin',
    action: 'approved',
    before_state: {
      task: { title: 'Review AI bill-pay run for Aster Cloud Services', kind: 'create_bill_payment_batch' },
      payload_hash: 'hash-before-payment',
    },
    after_state: {
      task: { title: 'Review AI bill-pay run for Aster Cloud Services', kind: 'create_bill_payment_batch' },
      payload_hash: 'hash-after-payment',
      materialisation: { entity_type: 'bill_payment_batch', entity_id: 'batch-ai-310' },
    },
    metadata: { source_hitl_task_id: 'task-payment-ai-310' },
    event_hash: 'hash-event-payment-ai-310',
    created_at: '2026-06-24T20:25:00Z',
  };
}

function closeDecisionEvent(): Record<string, unknown> {
  return {
    id: 'event-close-ai-310',
    event_type: 'hitl_task.approved',
    entity_type: 'month_end_close',
    entity_id: CLOSE_PERIOD,
    source_type: 'hitl_task',
    source_id: 'task-close-ai-310',
    actor_user_id: 'controller-1',
    actor_role: 'admin',
    action: 'approved',
    before_state: {
      task: { title: 'Review June 2026 month-end close package', kind: 'copilot_prepare_month_end_close' },
      payload_hash: 'hash-before-close',
    },
    after_state: {
      task: { title: 'Review June 2026 month-end close package', kind: 'copilot_prepare_month_end_close' },
      payload_hash: 'hash-after-close',
      materialisation: { entity_type: 'month_end_close', entity_id: CLOSE_PERIOD },
    },
    metadata: { source_hitl_task_id: 'task-close-ai-310' },
    event_hash: 'hash-event-close-ai-310',
    created_at: '2026-06-24T20:35:00Z',
  };
}

function closePackage(state: MockState): Record<string, unknown> {
  return {
    period: CLOSE_PERIOD,
    generated_at: '2026-06-24T20:40:00Z',
    previous_period: '2026-05',
    close_status: {
      status: state.overrideCreated ? 'ready' : 'blocked',
      ready_to_lock: state.overrideCreated,
      locked: false,
      lock_blockers: state.overrideCreated ? [] : ['close_tasks', 'approvals'],
      checklist: [
        {
          code: 'close_tasks',
          label: 'Close tasks',
          status: state.overrideCreated ? 'overridden' : 'blocked',
          blocking: !state.overrideCreated,
          summary: 'One AP accrual review remains open.',
          count: 1,
          overridden: state.overrideCreated,
        },
        {
          code: 'approvals',
          label: 'Approvals',
          status: 'ready',
          blocking: false,
          summary: 'Inbox approvals reviewed.',
          count: 0,
        },
      ],
    },
    gl_summary: { net_income: '18250.00' },
    previous_gl_summary: { net_income: '14100.00' },
    working_capital: { ar_open_total: '4200.00', ap_open_total: '1180.00', wip_total: '9500.00' },
    readiness_evidence: {
      ar: { status: 'ready', open_total: '4200.00', blocker_count: 0 },
      ap: { status: state.overrideCreated ? 'overridden' : 'blocked', open_total: '1180.00', blocker_count: 1 },
      wip: { status: 'ready', open_total: '9500.00', project_count: 2 },
      gl: { status: 'ready', unposted_journal_count: 0, trial_balance_balanced: true },
      approvals: { status: 'ready', pending_review_count: 0, incomplete_task_count: 0 },
      overrides: { status: state.overrideCreated ? 'overridden' : 'info', count: state.overrideCreated ? 1 : 0 },
    },
    close_overrides: state.overrideCreated ? [closeOverride] : [],
    variance_commentary: [
      {
        code: 'net_income',
        severity: 'info',
        summary: 'Net income increased after reviewed AP accruals and WIP release.',
        delta: '4150.00',
        delta_pct: 29.4,
      },
      {
        code: 'ap_exposure',
        severity: 'watch',
        summary: 'AP exposure remains low after Aster Cloud bill review.',
        delta: '-820.00',
        delta_pct: -41,
      },
    ],
  };
}

const trialBalance = {
  as_of_period: CLOSE_PERIOD,
  lines: [
    { account_code: '1000', account_name: 'Cash', account_type: 'asset', total_dr: '50000.00', total_cr: '0.00', net: '50000.00' },
    { account_code: '2000', account_name: 'Accounts Payable', account_type: 'liability', total_dr: '0.00', total_cr: '1180.00', net: '-1180.00' },
    { account_code: '4000', account_name: 'Advisory Revenue', account_type: 'revenue', total_dr: '0.00', total_cr: '30000.00', net: '-30000.00' },
    { account_code: '6000', account_name: 'Software Subscriptions', account_type: 'expense', total_dr: '1180.00', total_cr: '0.00', net: '1180.00' },
  ],
  grand_total_dr: '51180.00',
  grand_total_cr: '51180.00',
  is_balanced: true,
  generated_at: '2026-06-24T20:45:00Z',
};

const balanceSheet = {
  as_of_period: CLOSE_PERIOD,
  asset_lines: [{ account_code: '1000', account_name: 'Cash', account_type: 'asset', amount: '50000.00' }],
  liability_lines: [{ account_code: '2000', account_name: 'Accounts Payable', account_type: 'liability', amount: '1180.00' }],
  equity_lines: [{ account_code: '3000', account_name: 'Retained Earnings', account_type: 'equity', amount: '48820.00' }],
  total_assets: '50000.00',
  total_liabilities: '1180.00',
  total_equity: '48820.00',
  liabilities_and_equity: '50000.00',
  is_balanced: true,
  generated_at: '2026-06-24T20:45:00Z',
};

const incomeStatement = {
  period_start: CLOSE_PERIOD,
  period_end: CLOSE_PERIOD,
  revenue_lines: [{ account_code: '4000', account_name: 'Advisory Revenue', account_type: 'revenue', amount: '30000.00' }],
  expense_lines: [{ account_code: '6000', account_name: 'Software Subscriptions', account_type: 'expense', amount: '1180.00' }],
  total_revenue: '30000.00',
  total_expenses: '11750.00',
  net_income: '18250.00',
  generated_at: '2026-06-24T20:45:00Z',
};

const cashFlow = {
  period_start: CLOSE_PERIOD,
  period_end: CLOSE_PERIOD,
  operating_lines: [{ section: 'operating', description: 'Net income', amount: '18250.00', period: CLOSE_PERIOD, journal_entry_id: null, reference_type: null }],
  investing_lines: [],
  financing_lines: [],
  net_cash_from_operating: '18250.00',
  net_cash_from_investing: '0.00',
  net_cash_from_financing: '0.00',
  net_change_in_cash: '18250.00',
  beginning_cash: '31750.00',
  ending_cash: '50000.00',
  generated_at: '2026-06-24T20:45:00Z',
};

const retainedEarnings = {
  period: CLOSE_PERIOD,
  previous_period: '2026-05',
  beginning_retained_earnings: '30570.00',
  current_period_net_income: '18250.00',
  retained_earnings_activity: '0.00',
  ending_retained_earnings: '48820.00',
  generated_at: '2026-06-24T20:45:00Z',
};

function statutoryPack(): Record<string, unknown> {
  return {
    period_start: CLOSE_PERIOD,
    period_end: CLOSE_PERIOD,
    as_of_period: CLOSE_PERIOD,
    country: 'US',
    market: 'USA',
    base_currency: 'USD',
    locale: 'en-US',
    timezone: 'America/New_York',
    tax_label: 'Sales Tax',
    tax_authority_label: 'State Tax Authority',
    tax_collection_model: 'sales_tax',
    reporting_periods: [CLOSE_PERIOD],
    trial_balance: trialBalance,
    balance_sheet: balanceSheet,
    income_statement: incomeStatement,
    cash_flow: cashFlow,
    retained_earnings_roll_forward: retainedEarnings,
    tax_summary: {
      tax_label: 'Sales Tax',
      tax_authority_label: 'State Tax Authority',
      base_currency: 'USD',
      transaction_currency_buckets: [],
      ledger_output_tax_payable_balance: '0.00',
      ledger_input_tax_recoverable_balance: '0.00',
      ledger_net_tax_payable: '0.00',
    },
    generated_at: '2026-06-24T20:45:00Z',
  };
}

function agentRuns() {
  return {
    runs: [
      {
        id: 'run-ai-finance-310',
        agent_name: 'finance_ops_manager',
        trigger_type: 'copilot',
        status: 'succeeded',
        user_id: 'controller-1',
        prompt_version: 'finance_ops_manager.v3',
        model_version: 'gpt-4.1',
        trace_id: 'trace-ai-finance-310',
        replay_pointer: 'ledger://run-ai-finance-310',
        input_hash: 'hash-input-ai-finance-310',
        output_hash: 'hash-output-ai-finance-310',
        source_document_hash: null,
        usage_input_tokens: 1800,
        usage_output_tokens: 640,
        cost_usd: '0.06',
        error_message: null,
        started_at: '2026-06-24T20:00:00Z',
        completed_at: '2026-06-24T20:03:00Z',
        created_at: '2026-06-24T20:00:00Z',
        tool_count: 4,
        failed_tool_count: 0,
      },
    ],
    total: 1,
  };
}

function agentRunDetail() {
  return {
    ...agentRuns().runs[0],
    tool_invocations: [
      {
        id: 'tool-vendor-ai-310',
        tool_name: 'process_vendor_invoice',
        risk_class: 'review_required',
        status: 'succeeded',
        external_tool_call_id: null,
        input_hash: 'hash-tool-in-vendor',
        output_hash: 'hash-tool-out-vendor',
        input_snapshot: { document_id: 'doc-ai-310' },
        output_snapshot: { hitl_task_id: 'task-vendor-invoice-ai-310' },
        duration_ms: 320,
        error_message: null,
        created_at: '2026-06-24T20:01:00Z',
      },
      {
        id: 'tool-pay-ai-310',
        tool_name: 'propose_bill_payment_batch',
        risk_class: 'review_required',
        status: 'succeeded',
        external_tool_call_id: null,
        input_hash: 'hash-tool-in-pay',
        output_hash: 'hash-tool-out-pay',
        input_snapshot: { due_within_days: 7 },
        output_snapshot: { hitl_task_id: 'task-payment-ai-310' },
        duration_ms: 280,
        error_message: null,
        created_at: '2026-06-24T20:02:00Z',
      },
      {
        id: 'tool-close-ai-310',
        tool_name: 'prepare_month_end_close',
        risk_class: 'review_required',
        status: 'succeeded',
        external_tool_call_id: null,
        input_hash: 'hash-tool-in-close',
        output_hash: 'hash-tool-out-close',
        input_snapshot: { period: CLOSE_PERIOD },
        output_snapshot: { hitl_task_id: 'task-close-ai-310' },
        duration_ms: 360,
        error_message: null,
        created_at: '2026-06-24T20:02:30Z',
      },
      {
        id: 'tool-statement-ai-310',
        tool_name: 'generate_financial_statement_package',
        risk_class: 'read_only',
        status: 'succeeded',
        external_tool_call_id: null,
        input_hash: 'hash-tool-in-statement',
        output_hash: 'hash-tool-out-statement',
        input_snapshot: { period_start: CLOSE_PERIOD },
        output_snapshot: { generated_statement_package: true },
        duration_ms: 410,
        error_message: null,
        created_at: '2026-06-24T20:03:00Z',
      },
    ],
  };
}

function sseResponse(message: string): string {
  return [
    `data: ${JSON.stringify({ delta: message })}`,
    'data: {"done":true}',
    '',
  ].join('\n');
}

async function installAiFinanceMocks(page: Page, state: MockState): Promise<void> {
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (path === '/api/v1/chat/threads' && method === 'POST') {
      await route.fulfill({
        json: { id: 'thread-ai-finance-310', title: 'AI finance workflow proof', created_at: '2026-06-24T20:00:00Z' },
      });
      return;
    }
    if (path.endsWith('/messages') && path.includes('/api/v1/chat/threads/') && method === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}') as { content?: string };
      state.prompts.push(body.content ?? '');
      const response = body.content?.includes('month-end')
        ? 'I prepared the June close review, captured override evidence in the close package, and generated statement commentary for management review.'
        : 'I routed the vendor invoice exception to Inbox and prepared a reviewed bill-pay proposal after bill creation.';
      await route.fulfill({
        headers: { 'content-type': 'text/event-stream' },
        body: sseResponse(response),
      });
      return;
    }

    if (path === '/api/v1/inbox/tasks' && method === 'GET') {
      const status = url.searchParams.get('status') ?? 'open';
      const items = status === 'done'
        ? doneTasks(state)
        : status === 'all'
          ? [...openTasks(state), ...doneTasks(state)]
          : openTasks(state);
      await route.fulfill({ json: { items, total: items.length } });
      return;
    }
    if (path === '/api/v1/inbox/tasks/task-vendor-invoice-ai-310/approve-with-edits' && method === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}') as { corrected_payload?: Record<string, unknown> };
      state.p2pEdits.push(body.corrected_payload ?? {});
      state.vendorTaskOpen = false;
      state.billCreated = true;
      await route.fulfill({ json: { materialized: { entity_type: 'bill', entity_id: 'bill-ai-310' } } });
      return;
    }
    if (path === '/api/v1/inbox/tasks/task-payment-ai-310/approve' && method === 'POST') {
      state.paymentTaskOpen = false;
      state.paymentBatchCreated = true;
      await route.fulfill({ json: { materialized: { entity_type: 'bill_payment_batch', entity_id: 'batch-ai-310' } } });
      return;
    }
    if (path === '/api/v1/inbox/tasks/task-close-ai-310/approve' && method === 'POST') {
      state.closeTaskOpen = false;
      state.closeApproved = true;
      await route.fulfill({ json: { materialized: { entity_type: 'month_end_close', entity_id: CLOSE_PERIOD } } });
      return;
    }

    if (path === '/api/v1/bills/bill-ai-310' && method === 'GET') {
      await route.fulfill({ json: billDetail(state) });
      return;
    }
    if (path === '/api/v1/bills' && method === 'GET') {
      const bill = billDetail(state);
      if (url.searchParams.get('status') === 'approved') {
        await route.fulfill({
          json: [
            {
              id: bill.id,
              bill_number: bill.bill_number,
              client_id: 'vendor-aster',
              amount: bill.total,
              currency: bill.currency,
              due_date: bill.due_date,
              status: bill.status,
              source_document_id: bill.source_document_id,
            },
          ],
        });
        return;
      }
      await route.fulfill({ json: { items: state.billCreated ? [bill] : [], total: state.billCreated ? 1 : 0 } });
      return;
    }
    if (path === '/api/v1/bill-payments/batches' && method === 'POST') {
      state.paymentBatchCreated = true;
      await route.fulfill({
        json: {
          id: 'batch-ai-310',
          status: 'draft',
          total_amount: '1180.00',
          currency: 'USD',
          pay_date: '2026-06-28',
          bank_account_label: 'Operating Account',
          bill_ids: ['bill-ai-310'],
        },
      });
      return;
    }
    if (path === '/api/v1/engagements' && method === 'GET') {
      await route.fulfill({ json: [] });
      return;
    }

    if (path === '/api/v1/accounting/journal-entries' && method === 'GET') {
      await route.fulfill({ json: { items: [], total: 0 } });
      return;
    }
    if (path === `/api/v1/accounting/periods/${CLOSE_PERIOD}/close-tasks` && method === 'GET') {
      await route.fulfill({
        json: {
          tasks: state.closeApproved
            ? [
                {
                  id: 'close-task-ai-310',
                  period: CLOSE_PERIOD,
                  code: 'ap_accrual_review',
                  title: 'Review AP accruals',
                  description: 'Confirm Aster Cloud accrual treatment.',
                  owner_role: 'controller',
                  status: state.overrideCreated ? 'waived' : 'open',
                  due_date: '2026-06-29',
                  completed_at: null,
                  completed_by: null,
                  evidence: { source: 'AI Finance Ops Manager' },
                  order_index: 1,
                },
              ]
            : [],
        },
      });
      return;
    }
    if (path === `/api/v1/accounting/periods/${CLOSE_PERIOD}/close-package` && method === 'GET') {
      await route.fulfill({ json: closePackage(state) });
      return;
    }
    if (path === `/api/v1/accounting/periods/${CLOSE_PERIOD}/close-overrides` && method === 'POST') {
      state.overrideCreated = true;
      await route.fulfill({ json: closeOverride });
      return;
    }
    if (path === '/api/v1/accounting/recurring-journal-templates' && method === 'GET') {
      await route.fulfill({ json: { templates: [] } });
      return;
    }

    if (path.includes('/api/v1/financial-events/business-records/bill/bill-ai-310/decisions')) {
      await route.fulfill({ json: { items: state.billCreated ? [billDecisionEvent()] : [], total: state.billCreated ? 1 : 0 } });
      return;
    }
    if (path.includes('/api/v1/financial-events/business-records/bill_payment_batch/batch-ai-310/decisions')) {
      await route.fulfill({ json: { items: state.paymentBatchCreated ? [paymentDecisionEvent()] : [], total: state.paymentBatchCreated ? 1 : 0 } });
      return;
    }
    if (path.includes(`/api/v1/financial-events/business-records/month_end_close/${CLOSE_PERIOD}/decisions`)) {
      await route.fulfill({ json: { items: state.closeApproved ? [closeDecisionEvent()] : [], total: state.closeApproved ? 1 : 0 } });
      return;
    }

    if (path === '/api/v1/reports/trial-balance') {
      await route.fulfill({ json: trialBalance });
      return;
    }
    if (path === '/api/v1/reports/balance-sheet') {
      await route.fulfill({ json: balanceSheet });
      return;
    }
    if (path === '/api/v1/reports/income-statement') {
      await route.fulfill({ json: incomeStatement });
      return;
    }
    if (path === '/api/v1/reports/cash-flow') {
      await route.fulfill({ json: cashFlow });
      return;
    }
    if (path === '/api/v1/reports/retained-earnings-roll-forward') {
      await route.fulfill({ json: retainedEarnings });
      return;
    }
    if (path === '/api/v1/reports/statutory-pack') {
      await route.fulfill({ json: statutoryPack() });
      return;
    }
    if (path.startsWith('/api/v1/reports/')) {
      await route.fulfill({
        json: path.includes('aging')
          ? { total: '0.00', current: '0.00', days_1_30: '0.00', days_31_60: '0.00', days_61_90: '0.00', days_over_90: '0.00', items: [] }
          : [],
      });
      return;
    }

    if (path === '/api/v1/agents/runs' && method === 'GET') {
      await route.fulfill({ json: agentRuns() });
      return;
    }
    if (path === '/api/v1/agents/runs/run-ai-finance-310' && method === 'GET') {
      await route.fulfill({ json: agentRunDetail() });
      return;
    }
    if (path === '/api/v1/agents/workflow-runs' && method === 'GET') {
      await route.fulfill({
        json: {
          items: [
            {
              id: 'workflow-ai-finance-310',
              workflow_type: 'ai_finance_ops_manager',
              status: 'succeeded',
              started_at: '2026-06-24T20:00:00Z',
              completed_at: '2026-06-24T20:03:00Z',
              step_count: 4,
              failed_step_count: 0,
            },
          ],
          total: 1,
        },
      });
      return;
    }

    if (path === '/api/v1/services') {
      await route.fulfill({ json: { items: [] } });
      return;
    }
    if (path === '/api/v1/tax-rates') {
      await route.fulfill({ json: [] });
      return;
    }
    if (path === '/api/v1/integrations/catalog') {
      await route.fulfill({ json: { integrations: [], total: 0 } });
      return;
    }
    if (path === '/api/v1/agents/autonomy-status') {
      await route.fulfill({ json: { agents: [] } });
      return;
    }
    if (path === '/api/v1/agents/finance-ops/schedule') {
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
    if (path === '/api/v1/tenants/health') {
      await route.fulfill({
        json: {
          status: 'ok',
          generated_at: '2026-06-24T20:00:00Z',
          runtime: { environment: 'test', debug: false, queue_configured: true, queue_required: false, extraction_mode: 'sync' },
          rate_limit: { enabled: true, backend: 'supabase', distributed_configured: true, fallback_to_memory: true, window_seconds: 60 },
          checks: { tables: [] },
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
    if (path === '/api/v1/stripe/connect/status') {
      await route.fulfill({ json: { connected: false } });
      return;
    }
    if (path === '/api/v1/collections/policies/effective') {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-ai-finance',
          policy_source: 'system_default',
          gentle_after_days: 7,
          firm_after_days: 30,
          pause_after_reminder_count: 3,
          updated_at: null,
        },
      });
      return;
    }
    if (path === '/api/v1/approval-policy/effective') {
      await route.fulfill({
        json: {
          tenant_id: 'tenant-ai-finance',
          policy_source: 'tenant_default',
          money_out_default_role: 'admin',
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
    if (path === '/api/v1/tenants/finance-personas') {
      await route.fulfill({ json: { items: [] } });
      return;
    }

    if (method !== 'GET') {
      await route.fulfill({ status: 403, json: { detail: 'Unhandled mutating mock route' } });
      return;
    }
    await route.fulfill({ json: { items: [], total: 0 } });
  });
}

test.describe('Enterprise AI finance workflow proof (#310)', () => {
  test('P2P path uses business prompts, reviews vendor invoice exceptions, and approves bill-pay proposal', async ({ page }) => {
    const state = createState();
    await installAiFinanceMocks(page, state);
    await authenticate(page, 'admin');

    await sendCopilotBusinessPrompt(page, p2pPrompt);
    await expect(page.getByText('I routed the vendor invoice exception to Inbox')).toBeVisible();
    expect(state.prompts).toContain(p2pPrompt);
    assertBusinessPrompt(state.prompts[0]);

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: /^Bills$/ }).click();

    const invoiceCard = page.getByRole('article', { name: 'Review duplicate vendor invoice from Aster Cloud Services' });
    await expect(invoiceCard).toBeVisible();
    await expect(invoiceCard.getByText('AP review evidence')).toBeVisible();
    await expect(invoiceCard.getByText('Duplicate reason required')).toBeVisible();
    await expect(invoiceCard.getByText('possible_duplicate', { exact: true })).toBeVisible();
    await expect(invoiceCard.getByText('6000 Software Subscriptions (84%)')).toBeVisible();

    await invoiceCard.getByRole('button', { name: /^Approve Review duplicate/i }).click();
    await expect(page.getByRole('dialog', { name: /Edit Review duplicate vendor invoice/i })).toBeVisible();
    await page.locator('#edit-duplicate-review-reason').fill('Separate June service period confirmed against contract and prior invoice.');
    await page.getByRole('button', { name: /Save & approve/i }).click();
    await expect(invoiceCard).toHaveCount(0);
    expect(state.p2pEdits[0]['duplicate_review']).toMatchObject({
      approved_duplicate: true,
      reason: 'Separate June service period confirmed against contract and prior invoice.',
    });

    await page.goto(`${BASE}/app/bills/bill-ai-310`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'BILL-AI-310' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'AP review evidence' })).toBeVisible();
    await expect(page.getByText('Approved duplicate - Separate June service period confirmed against contract and prior invoice.')).toBeVisible();
    await expect(page.getByText('6000 Software Subscriptions (84%)')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Decision timeline' })).toBeVisible();
    await expect(page.getByText('Approved With Edits')).toBeVisible();

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: /^Payments$/ }).click();
    const paymentCard = page.getByRole('article', { name: 'Review AI bill-pay run for Aster Cloud Services' });
    await expect(paymentCard).toBeVisible();
    await expect(paymentCard.getByText('Admin approval')).toBeVisible();
    await expect(paymentCard.getByText('total amount:')).toBeVisible();
    await paymentCard.getByRole('button', { name: /Approve Review AI bill-pay run/i }).click();
    await expect(paymentCard).toHaveCount(0);

    await page.goto(`${BASE}/app/billing-runs`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Pay Bills' })).toBeVisible();
    await expect(page.getByText('BILL-AI-310')).toBeVisible();
    await expect(page.getByText('1,180.00')).toBeVisible();
  });

  test('R2R path uses business prompts, records close override, ties statements to ledger evidence', async ({ page }) => {
    const state = createState();
    await installAiFinanceMocks(page, state);
    await authenticate(page, 'admin');

    await sendCopilotBusinessPrompt(page, r2rPrompt);
    await expect(page.getByText('I prepared the June close review')).toBeVisible();
    expect(state.prompts).toContain(r2rPrompt);
    assertBusinessPrompt(state.prompts[0]);

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: /^Close$/ }).click();
    const closeCard = page.getByRole('article', { name: 'Review June 2026 month-end close package' });
    await expect(closeCard).toBeVisible();
    await expect(closeCard.getByText('lock blocker count:')).toBeVisible();
    await expect(closeCard.getByText('pending review count:')).toBeVisible();
    await closeCard.getByRole('button', { name: /Approve Review June 2026 month-end close package/i }).click();
    await expect(closeCard).toHaveCount(0);

    await page.goto(`${BASE}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /Journal Entries/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /^Month-end close$/i })).toBeVisible();
    await page.getByRole('button', { name: /Close package/i }).click();
    await expect(page.getByText('Net income', { exact: true })).toBeVisible();
    await expect(page.getByText('Open AR/AP')).toBeVisible();
    await expect(page.getByText('AP exposure remains low after Aster Cloud bill review.')).toBeVisible();

    await page.getByLabel('Close blocker to override').selectOption('close_tasks');
    await page.getByPlaceholder('Reason and evidence reviewed').fill(closeOverride.reason);
    await page.getByRole('button', { name: /^Record$/ }).click();
    await expect(page.getByText('Close override recorded for Close tasks.')).toBeVisible();
    await expect(page.getByText(closeOverride.reason)).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Close approval timeline' })).toBeVisible();
    await expect(page.getByText('Approved', { exact: true })).toBeVisible();

    await page.goto(`${BASE}/app/reports`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
    await page.getByRole('tab', { name: /Balance Sheet/i }).click();
    await expect(page.getByText('Balance sheet balances')).toBeVisible();
    await page.getByRole('tab', { name: /Income Statement/i }).click();
    await expect(page.getByText('Net Income')).toBeVisible();
    await expect(page.getByText('18,250.00')).toBeVisible();
    await page.getByRole('tab', { name: /Statutory Pack/i }).click();
    await expect(page.getByText('Tax Payable')).toBeVisible();

    await page.goto(`${BASE}/app/settings`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Agent Run Ledger' })).toBeVisible();
    await expect(page.getByText('Finance Ops Manager', { exact: true })).toBeVisible();
    await page.getByText('Finance Ops Manager', { exact: true }).click();
    await expect(page.getByText('process_vendor_invoice')).toBeVisible();
    await expect(page.getByText('propose_bill_payment_batch')).toBeVisible();
    await expect(page.getByText('prepare_month_end_close')).toBeVisible();
    await expect(page.getByText('generate_financial_statement_package')).toBeVisible();
  });
});
