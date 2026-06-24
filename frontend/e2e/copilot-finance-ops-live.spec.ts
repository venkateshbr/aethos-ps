/**
 * Live Copilot finance-ops verification for #260, #261, #262, #264, #265, #266, and #267.
 *
 * Browser flows:
 * - Copilot chat -> daily finance-ops command center -> report/action surfaces.
 * - Copilot chat -> collections reminders -> Inbox approval -> email send materialisation.
 * - Copilot chat -> bill-pay proposal -> Inbox approval -> payment batch.
 * - Copilot chat -> month-end close review -> Inbox approval -> close tasks UI.
 * - Copilot chat -> financial statement package tool -> Reports UI.
 * - Copilot document upload -> extraction Inbox task -> approval -> Bills UI.
 * - Copilot engagement-letter upload -> Inbox approval -> client/engagement/project records.
 */

import { test, expect, APIRequestContext, APIResponse, Locator, Page } from '@playwright/test';
import { Buffer } from 'node:buffer';
import { randomUUID } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';
const API = process.env.AETHOS_PS_API_URL ?? 'http://localhost:8011';
const STORAGE_PATH = path.join(__dirname, '.auth', 'o2c-tenant.json');
const META_PATH = path.join(__dirname, '.auth', 'o2c-tenant.meta.json');
const API_REQUEST_TIMEOUT = 90_000;
const CLOSE_PERIOD = '2026-06';

type AuthContext = { token: string; tenantId: string; userId: string };
type LoginCredentials = { email: string; password: string };
type SupabaseAdminConfig = { url: string; serviceRoleKey: string };
type ClientRow = { id: string; name: string };
type EngagementRow = {
  id: string;
  name: string;
  client_id?: string;
  billing_arrangement?: string;
  currency?: string;
  total_value?: string;
  status?: string;
  source_document_id?: string;
};
type ProjectRow = {
  id: string;
  name: string;
  engagement_id?: string;
  currency?: string;
  budget?: string;
  status?: string;
};
type InvoiceRow = {
  id: string;
  invoice_number?: string;
  status?: string;
  total?: string;
  currency?: string;
};
type BillRow = { id: string; bill_number?: string; status?: string; total?: string };
type HitlTaskRow = {
  id: string;
  title: string;
  kind: string;
  payload?: Record<string, unknown>;
  agent_suggestion_id?: string;
};
type SuggestionRow = { id: string; status: string };
type BatchItemRow = { batch_id: string; bill_id: string };
type BatchRow = { id: string; status: string; total: string | number; currency: string };
type DocumentRow = {
  id: string;
  status: string;
  original_filename: string;
  document_type?: string;
};
type ToolInvocationRow = {
  id: string;
  tool_name: string;
  status: string;
  input_snapshot?: Record<string, unknown>;
  output_snapshot?: Record<string, unknown>;
};

function envValue(name: string): string {
  if (process.env[name]) return process.env[name]!;
  for (const file of [
    path.join(__dirname, '..', '..', '.env'),
    path.join(__dirname, '..', '..', 'backend', '.env'),
  ]) {
    if (!fs.existsSync(file)) continue;
    const line = fs
      .readFileSync(file, 'utf-8')
      .split(/\r?\n/)
      .find((row) => row.trim().startsWith(`${name}=`));
    if (!line) continue;
    return line.slice(line.indexOf('=') + 1).trim().replace(/^['"]|['"]$/g, '');
  }
  return '';
}

function loadLoginMeta(): LoginCredentials | null {
  if (!fs.existsSync(META_PATH)) return null;
  try {
    const meta = JSON.parse(fs.readFileSync(META_PATH, 'utf-8'));
    if (meta.email && meta.password) return { email: meta.email, password: meta.password };
  } catch {
    /* no-op */
  }
  return null;
}

function parseJwtSub(token: string): string {
  const [, payload] = token.split('.');
  if (!payload) return '';
  try {
    return String(JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8')).sub ?? '');
  } catch {
    return '';
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function expectSummaryEntry(card: Locator, key: string, value: string): Promise<void> {
  await expect(card.getByText(new RegExp(`${escapeRegExp(key)}:\\s*${escapeRegExp(value)}`))).toBeVisible();
}

function getAuthFromStorage(): AuthContext | null {
  if (!fs.existsSync(STORAGE_PATH)) return null;
  try {
    const state = JSON.parse(fs.readFileSync(STORAGE_PATH, 'utf-8'));
    let token = '';
    let tenantId = '';
    for (const origin of state.origins ?? []) {
      for (const ls of origin.localStorage ?? []) {
        if (ls.name?.startsWith('sb-') && ls.name?.endsWith('-auth-token')) {
          try {
            token = JSON.parse(ls.value)?.access_token ?? token;
          } catch {
            /* no-op */
          }
        }
        if (!token && ls.name === 'aethos_token') token = ls.value;
        if (ls.name === 'aethos_tenant_id') tenantId = ls.value;
      }
    }
    const userId = parseJwtSub(token);
    if (token && tenantId && userId) return { token, tenantId, userId };
  } catch {
    /* no-op */
  }
  return null;
}

function supabaseAdminConfig(): SupabaseAdminConfig | null {
  const url = envValue('SUPABASE_URL');
  const serviceRoleKey = envValue('SUPABASE_SERVICE_ROLE_KEY');
  if (!url || !serviceRoleKey) return null;
  return { url, serviceRoleKey };
}

function apiHeaders(auth: AuthContext): Record<string, string> {
  return {
    Authorization: `Bearer ${auth.token}`,
    'X-Tenant-ID': auth.tenantId,
    'Content-Type': 'application/json',
  };
}

function supabaseAdminHeaders(config: SupabaseAdminConfig, extra: Record<string, string> = {}) {
  return {
    apikey: config.serviceRoleKey,
    Authorization: `Bearer ${config.serviceRoleKey}`,
    'Content-Type': 'application/json',
    ...extra,
  };
}

function restUrl(config: SupabaseAdminConfig, table: string, params: Record<string, string>): string {
  const url = new URL(`${config.url}/rest/v1/${table}`);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  return url.toString();
}

async function expectOk(resp: APIResponse, context: string): Promise<void> {
  if (resp.ok()) return;
  const body = await resp.text().catch(() => '');
  throw new Error(`${context} failed: HTTP ${resp.status()} ${body.slice(0, 500)}`);
}

async function restSelect<T>(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  table: string,
  params: Record<string, string>,
): Promise<T[]> {
  const resp = await request.get(restUrl(config, table, params), {
    headers: supabaseAdminHeaders(config),
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(resp, `select ${table}`);
  return await resp.json() as T[];
}

async function restPatch<T>(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  table: string,
  params: Record<string, string>,
  payload: Record<string, unknown>,
): Promise<T[]> {
  const resp = await request.patch(restUrl(config, table, params), {
    headers: supabaseAdminHeaders(config, { Prefer: 'return=representation' }),
    data: payload,
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(resp, `patch ${table}`);
  return await resp.json() as T[];
}

async function ensureAppRoute(page: Page, route: string): Promise<void> {
  await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded' });
  const shellReady = await page
    .getByRole('navigation', { name: /main navigation/i })
    .isVisible({ timeout: 10_000 })
    .catch(() => false);
  if (shellReady) return;

  const meta = loadLoginMeta();
  if (!meta) throw new Error('No login metadata found for refreshed UI session');
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('#email').fill(meta.email);
  await page.locator('#password').fill(meta.password);
  await page.getByRole('button', { name: /^sign in$/i }).click();
  await page.waitForURL(/\/app\//, { timeout: 60_000 });
  await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded' });
}

async function sendCopilotPrompt(page: Page, prompt: string): Promise<void> {
  await ensureAppRoute(page, '/app/copilot');
  await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: /new chat/i }).click();
  await page.getByLabel('Message input').fill(prompt);
  await page.getByRole('button', { name: /send message/i }).click();
}

async function approveInboxTask(page: Page, taskId: string): Promise<void> {
  await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /^inbox$/i })).toBeVisible({ timeout: 30_000 });
  const taskCard = page.locator(`#task-${taskId}`);
  await expect(taskCard).toBeVisible({ timeout: 30_000 });
  await taskCard.getByRole('button', { name: /^approve/i }).click();
  await expect(taskCard).toBeHidden({ timeout: 45_000 });
}

async function createApprovedVendorBill(
  request: APIRequestContext,
  auth: AuthContext,
): Promise<{ vendor: ClientRow; bill: BillRow; amount: string }> {
  const suffix = randomUUID().slice(0, 8);
  const amount = '432.10';
  const vendorName = `Copilot Bill Pay Vendor ${suffix} [E2E]`;
  const clientResp = await request.post(`${API}/api/v1/clients`, {
    headers: apiHeaders(auth),
    data: {
      name: vendorName,
      legal_name: vendorName,
      kind: 'vendor',
      currency: 'USD',
    },
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(clientResp, 'create bill-pay vendor');
  const vendor = await clientResp.json() as ClientRow;

  const billResp = await request.post(`${API}/api/v1/bills`, {
    headers: apiHeaders(auth),
    data: {
      client_id: vendor.id,
      vendor_invoice_number: `COPILOT-BILLPAY-${suffix}`,
      issue_date: '2026-06-20',
      due_date: '2026-06-25',
      currency: 'USD',
      lines: [
        {
          description: 'Finance operations subscription',
          quantity: '1',
          unit_price: amount,
          amount,
        },
      ],
    },
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(billResp, 'create bill-pay bill');
  const bill = await billResp.json() as BillRow;

  const approveResp = await request.patch(`${API}/api/v1/bills/${bill.id}/approve`, {
    headers: apiHeaders(auth),
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(approveResp, 'approve bill-pay bill');
  return { vendor, bill, amount };
}

async function createOverdueCustomerInvoice(
  request: APIRequestContext,
  auth: AuthContext,
  config: SupabaseAdminConfig,
): Promise<{ client: ClientRow; engagement: EngagementRow; invoice: InvoiceRow; recipient: string }> {
  const suffix = randomUUID().slice(0, 8);
  const amount = '1250.00';
  const recipient = `collections-${suffix}@aethos-qa.dev`;
  const clientName = `Copilot Collections Customer ${suffix} [E2E]`;
  const clientResp = await request.post(`${API}/api/v1/clients`, {
    headers: apiHeaders(auth),
    data: {
      name: clientName,
      legal_name: clientName,
      kind: 'customer',
      email: recipient,
      billing_address: { email: recipient },
      payment_terms_days: 30,
    },
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(clientResp, 'create collections customer');
  const client = await clientResp.json() as ClientRow;

  const engagementResp = await request.post(`${API}/api/v1/engagements`, {
    headers: apiHeaders(auth),
    data: {
      client_id: client.id,
      name: `Collections Advisory ${suffix}`,
      billing_arrangement: 'fixed_fee',
      currency: 'USD',
      total_value: amount,
      service_line: 'accounting',
    },
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(engagementResp, 'create collections engagement');
  const engagement = await engagementResp.json() as EngagementRow;

  const invoiceResp = await request.post(`${API}/api/v1/invoices`, {
    headers: apiHeaders(auth),
    data: {
      engagement_id: engagement.id,
      client_id: client.id,
      issue_date: '2025-01-01',
      due_date: '2025-01-15',
      currency: 'USD',
      lines: [
        {
          description: 'Overdue collections proof invoice',
          quantity: '1',
          unit_price: amount,
        },
      ],
    },
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(invoiceResp, 'create overdue collections invoice');
  const invoice = await invoiceResp.json() as InvoiceRow;

  const patched = await restPatch<InvoiceRow>(request, config, 'invoices', {
    id: `eq.${invoice.id}`,
    tenant_id: `eq.${auth.tenantId}`,
  }, {
    status: 'sent',
    sent_at: new Date().toISOString(),
  });
  return { client, engagement, invoice: patched[0] ?? invoice, recipient };
}

async function createAdditionalOverdueInvoice(
  request: APIRequestContext,
  auth: AuthContext,
  config: SupabaseAdminConfig,
  seed: { client: ClientRow; engagement: EngagementRow },
): Promise<InvoiceRow> {
  const invoiceResp = await request.post(`${API}/api/v1/invoices`, {
    headers: apiHeaders(auth),
    data: {
      engagement_id: seed.engagement.id,
      client_id: seed.client.id,
      issue_date: '2025-01-02',
      due_date: '2025-01-16',
      currency: 'USD',
      lines: [
        {
          description: 'Second overdue collections proof invoice',
          quantity: '1',
          unit_price: '990.00',
        },
      ],
    },
    timeout: API_REQUEST_TIMEOUT,
  });
  await expectOk(invoiceResp, 'create second overdue collections invoice');
  const invoice = await invoiceResp.json() as InvoiceRow;
  const patched = await restPatch<InvoiceRow>(request, config, 'invoices', {
    id: `eq.${invoice.id}`,
    tenant_id: `eq.${auth.tenantId}`,
  }, {
    status: 'sent',
    sent_at: new Date().toISOString(),
  });
  return patched[0] ?? invoice;
}

async function listOpenTasks(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  kind: string,
): Promise<HitlTaskRow[]> {
  return await restSelect<HitlTaskRow>(request, config, 'hitl_tasks', {
    select: 'id,title,kind,payload,agent_suggestion_id,created_at',
    tenant_id: `eq.${tenantId}`,
    kind: `eq.${kind}`,
    status: 'eq.open',
    order: 'created_at.desc',
    limit: '50',
  });
}

function payloadObject(row: HitlTaskRow): Record<string, unknown> {
  return row.payload ?? {};
}

async function findBatchForBill(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  billId: string,
): Promise<BatchRow | null> {
  const items = await restSelect<BatchItemRow>(request, config, 'bill_payment_items', {
    select: 'batch_id,bill_id,created_at',
    tenant_id: `eq.${tenantId}`,
    bill_id: `eq.${billId}`,
    order: 'created_at.desc',
    limit: '1',
  });
  const batchId = items[0]?.batch_id;
  if (!batchId) return null;
  const batches = await restSelect<BatchRow>(request, config, 'bill_payment_batches', {
    select: 'id,status,total,currency',
    tenant_id: `eq.${tenantId}`,
    id: `eq.${batchId}`,
    limit: '1',
  });
  return batches[0] ?? null;
}

async function findDocumentByFilename(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  filename: string,
): Promise<DocumentRow | null> {
  const rows = await restSelect<DocumentRow>(request, config, 'documents', {
    select: 'id,status,original_filename,document_type,created_at',
    tenant_id: `eq.${tenantId}`,
    original_filename: `eq.${filename}`,
    order: 'created_at.desc',
    limit: '1',
  });
  return rows[0] ?? null;
}

async function findClientById(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  clientId: string,
): Promise<ClientRow | null> {
  const rows = await restSelect<ClientRow>(request, config, 'clients', {
    select: 'id,name,kind',
    tenant_id: `eq.${tenantId}`,
    id: `eq.${clientId}`,
    deleted_at: 'is.null',
    limit: '1',
  });
  return rows[0] ?? null;
}

async function findEngagementById(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  engagementId: string,
): Promise<EngagementRow | null> {
  const rows = await restSelect<EngagementRow>(request, config, 'engagements', {
    select: 'id,name,client_id,billing_arrangement,currency,total_value,status,source_document_id',
    tenant_id: `eq.${tenantId}`,
    id: `eq.${engagementId}`,
    deleted_at: 'is.null',
    limit: '1',
  });
  return rows[0] ?? null;
}

async function findProjectById(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  projectId: string,
): Promise<ProjectRow | null> {
  const rows = await restSelect<ProjectRow>(request, config, 'projects', {
    select: 'id,name,engagement_id,currency,budget,status',
    tenant_id: `eq.${tenantId}`,
    id: `eq.${projectId}`,
    deleted_at: 'is.null',
    limit: '1',
  });
  return rows[0] ?? null;
}

async function findBillBySourceDocument(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  documentId: string,
): Promise<BillRow | null> {
  const rows = await restSelect<BillRow>(request, config, 'bills', {
    select: 'id,bill_number,status,total,source_document_id,created_at',
    tenant_id: `eq.${tenantId}`,
    source_document_id: `eq.${documentId}`,
    deleted_at: 'is.null',
    order: 'created_at.desc',
    limit: '1',
  });
  return rows[0] ?? null;
}

test.describe('Copilot finance-ops live flows (#260 #261 #262 #264 #265 #266 #267)', () => {
  test.use({ storageState: STORAGE_PATH });

  test.beforeEach(() => {
    test.skip(!fs.existsSync(STORAGE_PATH), 'no signed-in O2C tenant session');
    test.skip(!supabaseAdminConfig(), 'Supabase admin config missing');
    test.skip(!envValue('OPENROUTER_API_KEY'), 'OPENROUTER_API_KEY missing');
  });

  test('runs daily finance ops check through Copilot and report/action surfaces (#265)', async ({ page, request }) => {
    test.setTimeout(240_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');
    const startedAt = new Date(Date.now() - 5_000).toISOString();

    await sendCopilotPrompt(page, [
      `Run today's finance ops check for ${CLOSE_PERIOD}.`,
      'Use the run_finance_ops_check tool with limit 5.',
      'Separate read-only findings from recommended actions that require Inbox approval.',
      'Include AR, AP, WIP, close readiness, action queue, and recent agent/workflow status.',
    ].join(' '));

    await expect
      .poll(async () => {
        const rows = await restSelect<ToolInvocationRow>(request, config!, 'agent_tool_invocations', {
          select: 'id,tool_name,status,input_snapshot,output_snapshot,created_at',
          tenant_id: `eq.${auth!.tenantId}`,
          tool_name: 'eq.run_finance_ops_check',
          created_at: `gte.${startedAt}`,
          order: 'created_at.desc',
          limit: '10',
        });
        const match = rows.find((row) => {
          const output = row.output_snapshot ?? {};
          const findings = output['read_only_findings'];
          const actions = output['recommended_actions'];
          return row.status === 'succeeded'
            && row.input_snapshot?.['period'] === CLOSE_PERIOD
            && output['finance_ops_check'] === true
            && findings !== null
            && typeof findings === 'object'
            && Object.keys(findings as Record<string, unknown>).length >= 3
            && Array.isArray(actions);
        });
        return match?.id ?? '';
      }, {
        timeout: 150_000,
        message: 'Copilot should invoke the daily finance ops command-center tool successfully',
      })
      .not.toBe('');

    await page.goto(`${BASE}/app/reports`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /reports/i })).toBeVisible({ timeout: 30_000 });
    await page.getByRole('tab', { name: /action queue/i }).click();
    await expect(page.getByRole('button', { name: /finance/i })).toBeVisible({ timeout: 30_000 });

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^inbox$/i })).toBeVisible({ timeout: 30_000 });
  });

  test('drafts collections reminders through Copilot, Inbox approval, and rejection (#266)', async ({ page, request }) => {
    test.setTimeout(300_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');

    const seed = await createOverdueCustomerInvoice(request, auth!, config!);
    const secondInvoice = await createAdditionalOverdueInvoice(request, auth!, config!, seed);
    const targetInvoiceIds = new Set([seed.invoice.id, secondInvoice.id]);
    const startedAt = new Date(Date.now() - 5_000).toISOString();

    await sendCopilotPrompt(page, [
      'Draft collections reminders for invoices more than 30 days overdue.',
      'Use the draft_collection_reminders tool with minimum_days_overdue 30 and limit 10.',
      `Set client_name to "${seed.client.name}" so only this E2E customer is considered.`,
      'Create Inbox review tasks only. Do not send any email without review.',
    ].join(' '));

    let tasks: HitlTaskRow[] = [];
    await expect
      .poll(async () => {
        const rows = await listOpenTasks(request, config!, auth!.tenantId, 'send_email');
        tasks = rows.filter((task) => targetInvoiceIds.has(String(payloadObject(task)['invoice_id'] ?? '')));
        return tasks.length;
      }, {
        timeout: 150_000,
        message: 'Copilot should create collections send_email Inbox tasks for both seed invoices',
      })
      .toBeGreaterThanOrEqual(2);

    await expect
      .poll(async () => {
        const rows = await restSelect<ToolInvocationRow>(request, config!, 'agent_tool_invocations', {
          select: 'id,tool_name,status,input_snapshot,output_snapshot,created_at',
          tenant_id: `eq.${auth!.tenantId}`,
          tool_name: 'eq.draft_collection_reminders',
          created_at: `gte.${startedAt}`,
          order: 'created_at.desc',
          limit: '10',
        });
        const match = rows.find((row) =>
          row.status === 'skipped'
          && Number(row.output_snapshot?.['created_review_tasks'] ?? 0) >= 2
        );
        return match?.id ?? '';
      }, {
        timeout: 60_000,
        message: 'Copilot ledger should record the collections tool as review-routed',
      })
      .not.toBe('');

    await expect
      .poll(async () => {
        const rows = await restSelect<ToolInvocationRow>(request, config!, 'agent_tool_invocations', {
          select: 'id,tool_name,status,input_snapshot,output_snapshot,created_at',
          tenant_id: `eq.${auth!.tenantId}`,
          tool_name: 'eq.send_email',
          created_at: `gte.${startedAt}`,
          order: 'created_at.desc',
          limit: '10',
        });
        const match = rows.find((row) =>
          row.status === 'skipped'
          && Number(row.output_snapshot?.['review_tasks_created'] ?? 0) >= 2
        );
        return match?.id ?? '';
      }, {
        timeout: 60_000,
        message: 'Collections-agent ledger should record send_email as skipped pending Inbox approval',
      })
      .not.toBe('');

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^inbox$/i })).toBeVisible({ timeout: 30_000 });
    const approveTask = tasks[0];
    const rejectTask = tasks[1];
    const approvePayload = payloadObject(approveTask);
    const approveCard = page.locator(`#task-${approveTask.id}`);
    await expect(approveCard).toBeVisible({ timeout: 30_000 });
    await expectSummaryEntry(approveCard, 'invoice number', String(approvePayload['invoice_number']));
    await expectSummaryEntry(approveCard, 'client name', seed.client.name);
    await expectSummaryEntry(approveCard, 'client email', seed.recipient);
    await expect(approveCard.getByText(/tone:\s*(final|firm|gentle)/i)).toBeVisible();
    await expectSummaryEntry(approveCard, 'subject', String(approvePayload['subject']));
    await expectSummaryEntry(approveCard, 'body preview', String(approvePayload['body_preview']).slice(0, 40));

    const approveResp = await request.post(`${API}/api/v1/inbox/tasks/${approveTask.id}/approve`, {
      headers: apiHeaders(auth!),
      timeout: API_REQUEST_TIMEOUT,
    });
    await expectOk(approveResp, 'approve collections reminder');
    const approved = await approveResp.json() as { materialisation?: Record<string, unknown> };
    expect(approved.materialisation?.['entity_type']).toBe('collections_email');
    expect(approved.materialisation?.['entity_id']).toBe(String(approvePayload['invoice_id']));
    expect(['sent', 'skipped']).toContain(String(approved.materialisation?.['send_status']));

    const rejectResp = await request.post(`${API}/api/v1/inbox/tasks/${rejectTask.id}/reject`, {
      headers: apiHeaders(auth!),
      data: { reason: 'E2E collections rejection proof' },
      timeout: API_REQUEST_TIMEOUT,
    });
    await expectOk(rejectResp, 'reject collections reminder');

    const approvedSuggestion = await restSelect<SuggestionRow>(request, config!, 'agent_suggestions', {
      select: 'id,status',
      tenant_id: `eq.${auth!.tenantId}`,
      id: `eq.${approveTask.agent_suggestion_id}`,
      limit: '1',
    });
    const rejectedSuggestion = await restSelect<SuggestionRow>(request, config!, 'agent_suggestions', {
      select: 'id,status',
      tenant_id: `eq.${auth!.tenantId}`,
      id: `eq.${rejectTask.agent_suggestion_id}`,
      limit: '1',
    });
    expect(approvedSuggestion[0]?.status).toBe('approved');
    expect(rejectedSuggestion[0]?.status).toBe('rejected');
  });

  test('proposes bill pay through Copilot, Inbox approval, and payment batch UI (#262)', async ({ page, request }) => {
    test.setTimeout(300_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');

    const seed = await createApprovedVendorBill(request, auth!);
    await expect
      .poll(async () => await findBatchForBill(request, config!, auth!.tenantId, seed.bill.id), {
        timeout: 5_000,
        message: 'seed bill should not already be in a payment batch',
      })
      .toBeNull();

    await sendCopilotPrompt(page, [
      'Prepare a bill-pay run for approved vendor bills due within 7 days.',
      'Use the propose_bill_payment_batch tool with due_within_days 7.',
      `Make sure the approved bill ${seed.bill.id} is included if eligible.`,
      'Create the Inbox review task without asking a follow-up question.',
    ].join(' '));

    let taskId = '';
    await expect
      .poll(async () => {
        const tasks = await listOpenTasks(request, config!, auth!.tenantId, 'create_bill_payment_batch');
        const match = tasks.find((task) => {
          const payload = payloadObject(task);
          const ids = payload['proposed_bill_ids'];
          return payload['tool_name'] === 'propose_bill_payment_batch'
            && Array.isArray(ids)
            && ids.map(String).includes(seed.bill.id);
        });
        taskId = match?.id ?? '';
        return taskId;
      }, {
        timeout: 150_000,
        message: 'Copilot should create a bill-pay HITL task that includes the seed bill',
      })
      .not.toBe('');

    await approveInboxTask(page, taskId);

    let batch: BatchRow | null = null;
    await expect
      .poll(async () => {
        batch = await findBatchForBill(request, config!, auth!.tenantId, seed.bill.id);
        return batch?.id ?? '';
      }, {
        timeout: 45_000,
        message: 'approved bill-pay task should create a payment batch',
      })
      .not.toBe('');
    expect(batch?.status).toBe('draft');
    expect(batch?.currency).toBe('USD');

    await page.goto(`${BASE}/app/billing-runs`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^billing$/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /^pay bills$/i })).toBeVisible({ timeout: 30_000 });
  });

  test('prepares month-end close through Copilot and Inbox approval (#260)', async ({ page, request }) => {
    test.setTimeout(300_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');

    await sendCopilotPrompt(page, [
      `Prepare month-end close for ${CLOSE_PERIOD}.`,
      'Use the prepare_month_end_close tool.',
      'Create the Inbox review task without asking a follow-up question.',
      'Do not lock the period.',
    ].join(' '));

    let taskId = '';
    await expect
      .poll(async () => {
        const tasks = await listOpenTasks(request, config!, auth!.tenantId, 'copilot_prepare_month_end_close');
        const match = tasks.find((task) => {
          const payload = payloadObject(task);
          return payload['tool_name'] === 'prepare_month_end_close'
            && payload['period'] === CLOSE_PERIOD;
        });
        taskId = match?.id ?? '';
        return taskId;
      }, {
        timeout: 150_000,
        message: 'Copilot should create a month-end close HITL task',
      })
      .not.toBe('');

    await approveInboxTask(page, taskId);

    await expect
      .poll(async () => {
        const resp = await request.get(`${API}/api/v1/accounting/periods/${CLOSE_PERIOD}/close-tasks`, {
          headers: apiHeaders(auth!),
          timeout: API_REQUEST_TIMEOUT,
        });
        await expectOk(resp, 'list close tasks');
        const data = await resp.json() as { tasks?: unknown[] };
        return data.tasks?.length ?? 0;
      }, {
        timeout: 45_000,
        message: 'approved close task should bootstrap close tasks',
      })
      .toBeGreaterThan(0);

    await page.goto(`${BASE}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /journal entries/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /^month-end close$/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(CLOSE_PERIOD)).toBeVisible({ timeout: 30_000 });
  });

  test('generates financial statement package through Copilot and Reports UI (#261)', async ({ page, request }) => {
    test.setTimeout(240_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');
    const startedAt = new Date(Date.now() - 5_000).toISOString();

    await sendCopilotPrompt(page, [
      `Generate the financial statement package for ${CLOSE_PERIOD}.`,
      'Use the generate_financial_statement_package tool.',
      'Include trial balance, balance sheet, income statement, cash flow, retained earnings, and tax controls.',
    ].join(' '));

    await expect
      .poll(async () => {
        const rows = await restSelect<ToolInvocationRow>(request, config!, 'agent_tool_invocations', {
          select: 'id,tool_name,status,input_snapshot,output_snapshot,created_at',
          tenant_id: `eq.${auth!.tenantId}`,
          tool_name: 'eq.generate_financial_statement_package',
          created_at: `gte.${startedAt}`,
          order: 'created_at.desc',
          limit: '10',
        });
        const match = rows.find((row) =>
          row.status === 'succeeded'
          && row.input_snapshot?.['period_start'] === CLOSE_PERIOD
          && row.output_snapshot?.['generated_statement_package'] === true
        );
        return match?.id ?? '';
      }, {
        timeout: 150_000,
        message: 'Copilot should invoke the financial statement package tool successfully',
      })
      .not.toBe('');

    await page.goto(`${BASE}/app/reports`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /reports/i })).toBeVisible({ timeout: 30_000 });
    await page.getByRole('tab', { name: /balance sheet/i }).click();
    await expect(page.getByText(/Balance sheet balances|Balance sheet does not balance/i)).toBeVisible({ timeout: 30_000 });
    await page.getByRole('tab', { name: /income statement/i }).click();
    await expect(page.getByText('Net Income')).toBeVisible({ timeout: 30_000 });
    await page.getByRole('tab', { name: /statutory pack/i }).click();
    await expect(page.getByText(/Tax Payable|Statutory/i)).toBeVisible({ timeout: 30_000 });
  });

  test('uploads vendor invoice in Copilot, approves Inbox task, and creates bill (#264)', async ({ page, request }) => {
    test.setTimeout(360_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');

    const suffix = randomUUID().slice(0, 8);
    const filename = `copilot-vendor-invoice-${suffix}.txt`;
    const vendorName = `Copilot Upload Vendor ${suffix}`;
    const invoiceNumber = `DOC-${suffix.toUpperCase()}`;
    const invoiceText = [
      'Vendor invoice',
      `Vendor: ${vendorName}`,
      `Invoice number: ${invoiceNumber}`,
      'Issue date: 2026-06-21',
      'Due date: 2026-06-28',
      'Currency: USD',
      'Line item: Finance operations support, amount 321.09',
      'Subtotal: 321.09',
      'Tax: 0.00',
      'Total: 321.09',
      'Payment terms: Net 7',
    ].join('\n');

    await ensureAppRoute(page, '/app/copilot');
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });
    await page.locator('input[type="file"][aria-label="Attach document"]').setInputFiles({
      name: filename,
      mimeType: 'text/plain',
      buffer: Buffer.from(invoiceText, 'utf-8'),
    });
    await expect(page.getByText(filename)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('link', { name: /^documents$/i })).toBeVisible({ timeout: 90_000 });

    let documentId = '';
    await expect
      .poll(async () => {
        const doc = await findDocumentByFilename(request, config!, auth!.tenantId, filename);
        documentId = doc?.id ?? '';
        return doc?.status ?? '';
      }, {
        timeout: 150_000,
        message: 'uploaded document should be extracted',
      })
      .toBe('extracted');

    let taskId = '';
    await expect
      .poll(async () => {
        const tasks = await listOpenTasks(request, config!, auth!.tenantId, 'create_bill_draft');
        const match = tasks.find((task) => {
          const payload = payloadObject(task);
          return payload['original_document_id'] === documentId
            || payload['vendor_invoice_number'] === invoiceNumber
            || payload['vendor_name'] === vendorName;
        });
        taskId = match?.id ?? '';
        return taskId;
      }, {
        timeout: 90_000,
        message: 'vendor invoice extraction should create a bill draft HITL task',
      })
      .not.toBe('');

    await approveInboxTask(page, taskId);

    let bill: BillRow | null = null;
    await expect
      .poll(async () => {
        bill = await findBillBySourceDocument(request, config!, auth!.tenantId, documentId);
        return bill?.id ?? '';
      }, {
        timeout: 45_000,
        message: 'approved document extraction task should materialise a bill',
      })
      .not.toBe('');

    await page.goto(`${BASE}/app/bills`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^bills$/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(bill!.bill_number ?? bill!.id).first()).toBeVisible({ timeout: 30_000 });
  });

  test('uploads engagement letter in Copilot, approves Inbox task, and creates onboarding records (#267)', async ({ page, request }) => {
    test.setTimeout(360_000);
    const auth = getAuthFromStorage();
    const config = supabaseAdminConfig();
    test.skip(!auth || !config, 'auth or Supabase admin config missing');

    const suffix = randomUUID().slice(0, 8);
    const filename = `copilot-engagement-letter-${suffix}.txt`;
    const clientName = `Copilot Onboarding Client ${suffix}`;
    const engagementName = `AI Finance Ops Implementation ${suffix}`;
    const projectName = `Phase 1 Finance Ops Setup ${suffix}`;
    const scopeSummary = 'Configure finance operations workflows, reporting cadence, and implementation controls.';
    const letterText = [
      'ENGAGEMENT LETTER',
      `Client: ${clientName}`,
      `Engagement: ${engagementName}`,
      `First project: ${projectName}`,
      'Billing arrangement: Fixed fee',
      'Currency: USD',
      'Total fee: USD 12345.67',
      'Start date: 2026-07-01',
      'End date: 2026-09-30',
      'Senior Consultant: USD 350 / hour',
      'Analyst: USD 175 / hour',
      `Scope: ${scopeSummary}`,
    ].join('\n');

    await ensureAppRoute(page, '/app/copilot');
    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });
    await page.locator('input[type="file"][aria-label="Attach document"]').setInputFiles({
      name: filename,
      mimeType: 'text/plain',
      buffer: Buffer.from(letterText, 'utf-8'),
    });
    await expect(page.getByText(filename)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('link', { name: /^documents$/i })).toBeVisible({ timeout: 90_000 });

    let documentId = '';
    await expect
      .poll(async () => {
        const doc = await findDocumentByFilename(request, config!, auth!.tenantId, filename);
        documentId = doc?.id ?? '';
        return `${doc?.document_type ?? ''}:${doc?.status ?? ''}`;
      }, {
        timeout: 150_000,
        message: 'uploaded engagement letter should be classified and extracted',
      })
      .toBe('engagement_letter:extracted');

    let task: HitlTaskRow | null = null;
    await expect
      .poll(async () => {
        const tasks = await listOpenTasks(request, config!, auth!.tenantId, 'create_engagement_draft');
        task = tasks.find((candidate) => {
          const payload = payloadObject(candidate);
          return payload['original_document_id'] === documentId
            || payload['client_name'] === clientName
            || payload['engagement_name'] === engagementName;
        }) ?? null;
        return task?.id ?? '';
      }, {
        timeout: 90_000,
        message: 'engagement letter extraction should create an engagement draft HITL task',
      })
      .not.toBe('');

    const extractedPayload = payloadObject(task!);
    expect(String(extractedPayload['first_project_name'] ?? '')).not.toBe('');
    expect(String(extractedPayload['engagement_name'] ?? '')).not.toBe('');

    await page.goto(`${BASE}/app/inbox`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: /^inbox$/i })).toBeVisible({ timeout: 30_000 });
    const card = page.locator(`#task-${task!.id}`);
    await expect(card).toBeVisible({ timeout: 30_000 });
    await expectSummaryEntry(card, 'first project name', String(extractedPayload['first_project_name']));

    const correctedPayload = {
      ...extractedPayload,
      original_document_id: documentId,
      client_name: clientName,
      engagement_name: engagementName,
      billing_arrangement: 'fixed_fee',
      currency: 'USD',
      total_value: '12345.67',
      start_date: '2026-07-01',
      end_date: '2026-09-30',
      first_project_name: projectName,
      first_project_description: scopeSummary,
      scope_summary: scopeSummary,
    };
    const approveResp = await request.post(`${API}/api/v1/inbox/tasks/${task!.id}/approve-with-edits`, {
      headers: apiHeaders(auth!),
      data: { corrected_payload: correctedPayload },
      timeout: API_REQUEST_TIMEOUT,
    });
    await expectOk(approveResp, 'approve engagement onboarding with edits');
    const approved = await approveResp.json() as { materialisation?: Record<string, unknown> };
    const materialisation = approved.materialisation ?? {};
    expect(materialisation['entity_type']).toBe('engagement');
    expect(String(materialisation['entity_id'] ?? '')).not.toBe('');
    expect(String(materialisation['client_id'] ?? '')).not.toBe('');
    expect(String(materialisation['project_id'] ?? '')).not.toBe('');

    let client: ClientRow | null = null;
    let engagement: EngagementRow | null = null;
    let project: ProjectRow | null = null;
    await expect
      .poll(async () => {
        client = await findClientById(request, config!, auth!.tenantId, String(materialisation['client_id']));
        engagement = await findEngagementById(request, config!, auth!.tenantId, String(materialisation['entity_id']));
        project = await findProjectById(request, config!, auth!.tenantId, String(materialisation['project_id']));
        return client?.name === clientName
          && engagement?.name === engagementName
          && engagement?.source_document_id === documentId
          && project?.name === projectName
          && project?.engagement_id === engagement?.id;
      }, {
        timeout: 45_000,
        message: 'approved engagement draft should materialise client, engagement, and project records',
      })
      .toBe(true);

    await page.goto(`${BASE}/app/clients`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText(clientName).first()).toBeVisible({ timeout: 30_000 });
    await page.goto(`${BASE}/app/engagements`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText(engagementName).first()).toBeVisible({ timeout: 30_000 });
    await page.goto(`${BASE}/app/projects`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText(projectName).first()).toBeVisible({ timeout: 30_000 });
  });
});
