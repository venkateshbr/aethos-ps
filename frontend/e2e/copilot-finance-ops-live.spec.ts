/**
 * Live Copilot finance-ops verification for #260, #261, #262, and #264.
 *
 * Browser flows:
 * - Copilot chat -> bill-pay proposal -> Inbox approval -> payment batch.
 * - Copilot chat -> month-end close review -> Inbox approval -> close tasks UI.
 * - Copilot chat -> financial statement package tool -> Reports UI.
 * - Copilot document upload -> extraction Inbox task -> approval -> Bills UI.
 */

import { test, expect, APIRequestContext, APIResponse, Page } from '@playwright/test';
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
type BillRow = { id: string; bill_number?: string; status?: string; total?: string };
type HitlTaskRow = {
  id: string;
  title: string;
  kind: string;
  payload?: Record<string, unknown>;
};
type BatchItemRow = { batch_id: string; bill_id: string };
type BatchRow = { id: string; status: string; total: string | number; currency: string };
type DocumentRow = { id: string; status: string; original_filename: string };
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

async function listOpenTasks(
  request: APIRequestContext,
  config: SupabaseAdminConfig,
  tenantId: string,
  kind: string,
): Promise<HitlTaskRow[]> {
  return await restSelect<HitlTaskRow>(request, config, 'hitl_tasks', {
    select: 'id,title,kind,payload,created_at',
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
    select: 'id,status,original_filename,created_at',
    tenant_id: `eq.${tenantId}`,
    original_filename: `eq.${filename}`,
    order: 'created_at.desc',
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

test.describe('Copilot finance-ops live flows (#260 #261 #262 #264)', () => {
  test.use({ storageState: STORAGE_PATH });

  test.beforeEach(() => {
    test.skip(!fs.existsSync(STORAGE_PATH), 'no signed-in O2C tenant session');
    test.skip(!supabaseAdminConfig(), 'Supabase admin config missing');
    test.skip(!envValue('OPENROUTER_API_KEY'), 'OPENROUTER_API_KEY missing');
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
});
