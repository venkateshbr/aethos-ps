/**
 * Retained Ishantech production journey.
 *
 * Safety contract:
 * - Runs only through playwright.production-ui.config.ts.
 * - Uses one Playwright BrowserContext and one page for the entire tenant.
 * - All product writes are performed by clicking/typing in visible UI.
 * - No request fixture, route interception, direct storage writes, API seeding, or teardown.
 * - Raw video/trace stay in the ignored, mode-0700 private evidence directory.
 */

import { expect, test, type BrowserContext, type Locator, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';

const ORIGIN = 'https://aethos.ishirock.tech';
const TIMESHEET_ORIGIN = 'https://timesheet.aethos.ishirock.tech';
const CONFIG_MARKER = 'ishantech-retained-v1';
const RUN_ID = process.env.AETHOS_ISHANTECH_RUN_ID ?? '';
const EXPECTED_SHA = process.env.AETHOS_EXPECTED_DEPLOY_SHA ?? '';
const TAG = RUN_ID;

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const CREDENTIAL_PATH = path.join(REPO_ROOT, 'ishantech_e2e_credentials.json');
const PRIVATE_ROOT = path.join(REPO_ROOT, 'ishantech_e2e_private_evidence', RUN_ID);
const SCREENSHOT_ROOT = path.join(PRIVATE_ROOT, 'screenshots');
const RUN_STATE_PATH = path.join(PRIVATE_ROOT, 'run-state.json');
const REPORT_PATH = path.join(PRIVATE_ROOT, 'execution-report.md');

const EXPECTED_ROLE_CODES = [
  'tenant_owner',
  'tenant_admin',
  'cfo',
  'finance_controller',
  'finance_ops_manager',
  'finance_approver',
  'finance_operator',
  'procurement_manager',
  'buyer_requester',
  'ap_manager',
  'ap_clerk',
  'ar_manager',
  'billing_specialist',
  'collections_specialist',
  'gl_accountant',
  'close_manager',
  'engagement_manager',
  'resource_manager',
  'auditor',
  'executive_viewer',
  'ai_ops_admin',
  'timesheet_employee',
] as const;

type RoleCode = typeof EXPECTED_ROLE_CODES[number];
type StepStatus = 'PASS' | 'FAIL' | 'BLOCKED' | 'SKIPPED';

interface CredentialAccount {
  code: RoleCode;
  label: string;
  legacy_role: string;
  email: string;
  password: string;
  pending_password?: string | null;
  must_change_password: boolean;
  status: string;
  user_id: string | null;
}

interface CredentialManifest {
  schema_version: number;
  run_id: string;
  company: string;
  environment: string;
  production_url: string;
  tenant_id: string | null;
  created_at: string | null;
  retained: boolean;
  notes: string[];
  accounts: CredentialAccount[];
}

interface StepResult {
  id: string;
  title: string;
  status: StepStatus;
  started_at: string;
  finished_at: string;
  url: string;
  detail?: string;
  evidence?: string;
}

interface NetworkFinding {
  at: string;
  kind: 'http' | 'requestfailed' | 'console';
  status?: number;
  url?: string;
  detail?: string;
  expected?: boolean;
  method?: string;
  resource_type?: string;
  step?: string;
}

interface ExpectedHttpRule {
  status: number;
  url: RegExp;
}

interface PersistedRunState {
  run_id?: string;
  expected_sha?: string;
  records?: Record<string, string>;
}

interface FxProvenance {
  from_currency: string;
  to_currency: string;
  rate: string;
  requested_rate_date: string;
  rate_date: string;
  fx_rate_id: string | null;
  source: string;
  staleness_days: number;
}

interface ExpectedJournalLine {
  direction: 'DR' | 'CR';
  accountCode: string;
  amount: string;
  currency: string;
  baseAmount: string;
  fxRateId: string | null;
}

interface ExpectedJournalPosting {
  referenceType: string;
  referenceId?: string;
  rowText?: string;
  lines: ExpectedJournalLine[];
}

interface VisibleJournalPosting {
  journalId: string;
  entryNumber: string;
}

interface MonthlyCloseOracle {
  month: string;
  label: string;
  income: string;
  cash: string;
  ar: string;
  ap: string;
  asOf: string;
}

class BlockedError extends Error {}
class SkippedError extends Error {}

const DATA = {
  company: 'Ishantech Advisory Pte. Ltd.',
  customers: [
    `${TAG} Merlion Health Pte. Ltd.`,
    `${TAG} Pacific Vector LLC`,
  ],
  vendors: [
    `${TAG} Cloud Harbor SG`,
    `${TAG} Kinetic Contractors SG`,
    `${TAG} LedgerCloud SG`,
    `${TAG} Vector Data Inc.`,
  ],
  services: [
    { code: 'ISH-MFO', name: `${TAG} Monthly Finance Operations`, line: 'accounting', unit: 'retainer', rate: '12000', currency: 'SGD' },
    { code: 'ISH-TA', name: `${TAG} Transformation Advisory`, line: 'advisory', unit: 'hour', rate: '300', currency: 'SGD' },
    { code: 'ISH-IMPL', name: `${TAG} Implementation Milestone`, line: 'advisory', unit: 'milestone', rate: '25000', currency: 'SGD' },
  ],
  engagements: [
    { name: `${TAG} Merlion Finance Operations`, customer: `${TAG} Merlion Health Pte. Ltd.`, billing: 'retainer', currency: 'SGD', value: '36000', terms: '12000', start: '2026-04-01', service: `${TAG} Monthly Finance Operations` },
    { name: `${TAG} Merlion Transformation Advisory`, customer: `${TAG} Merlion Health Pte. Ltd.`, billing: 'time_and_materials', currency: 'SGD', value: '18000', terms: '', start: '2026-05-01', service: `${TAG} Transformation Advisory` },
    { name: `${TAG} Merlion Implementation`, customer: `${TAG} Merlion Health Pte. Ltd.`, billing: 'milestone', currency: 'SGD', value: '25000', terms: '25000', start: '2026-06-01', service: `${TAG} Implementation Milestone` },
    { name: `${TAG} Pacific Vector Advisory`, customer: `${TAG} Pacific Vector LLC`, billing: 'fixed_fee', currency: 'USD', value: '5000', terms: '5000', start: '2026-05-01', service: `${TAG} Transformation Advisory` },
  ],
  projects: [
    { name: `${TAG} Merlion Monthly Close`, engagement: `${TAG} Merlion Finance Operations` },
    { name: `${TAG} Merlion Transformation`, engagement: `${TAG} Merlion Transformation Advisory` },
    { name: `${TAG} Merlion Implementation Phase 1`, engagement: `${TAG} Merlion Implementation` },
  ],
  employee: { first: 'Ishan', last: 'Consultant', title: 'Transformation Consultant' },
};

function loadCredentials(): CredentialManifest {
  const manifest = JSON.parse(fs.readFileSync(CREDENTIAL_PATH, 'utf8')) as CredentialManifest;
  if (manifest.run_id !== RUN_ID || manifest.accounts.length !== 22) {
    throw new Error('Credential manifest does not belong to this exact 22-role run.');
  }
  return manifest;
}

function saveCredentials(manifest: CredentialManifest): void {
  const temporary = `${CREDENTIAL_PATH}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(manifest, null, 2)}\n`, { mode: 0o600 });
  fs.chmodSync(temporary, 0o600);
  fs.renameSync(temporary, CREDENTIAL_PATH);
  fs.chmodSync(CREDENTIAL_PATH, 0o600);
}

function account(manifest: CredentialManifest, code: RoleCode): CredentialAccount {
  const found = manifest.accounts.find(item => item.code === code);
  if (!found) throw new Error(`Credential manifest is missing role ${code}.`);
  return found;
}

function finalPassword(): string {
  return `${randomBytes(18).toString('base64url')}Aa1!`;
}

function sanitize(value: unknown): string {
  const raw = value instanceof Error ? `${value.name}: ${value.message}` : String(value ?? '');
  return raw
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '<redacted-email>')
    .replace(/(access_token|refresh_token|authorization|apikey|password)["'=:\s]+[^\s",}]+/gi, '$1=<redacted>')
    .replace(/https?:\/\/[^\s]+(?:token|code|access_token)=[^\s&]+/gi, '<redacted-token-url>')
    .slice(0, 1000);
}

function safeUrl(raw: string): string {
  try {
    const parsed = new URL(raw);
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return sanitize(raw);
  }
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80);
}

function redactedAlias(email: string): string {
  const [local, domain = ''] = email.split('@');
  return `${local.slice(0, Math.min(4, local.length))}***@${domain}`;
}

function divideHalfEven(numerator: bigint, denominator: bigint): bigint {
  if (denominator <= 0n) throw new Error('Decimal denominator must be positive.');
  const sign = numerator < 0n ? -1n : 1n;
  const absolute = numerator < 0n ? -numerator : numerator;
  const quotient = absolute / denominator;
  const remainder = absolute % denominator;
  const comparison = remainder * 2n - denominator;
  const roundUp = comparison > 0n || (comparison === 0n && quotient % 2n !== 0n);
  return sign * (roundUp ? quotient + 1n : quotient);
}

function decimalRatio(value: string): { coefficient: bigint; denominator: bigint } {
  const match = /^(\d+)(?:\.(\d+))?$/.exec(value.trim());
  if (!match) throw new Error(`Invalid positive decimal: ${value}`);
  const fraction = match[2] ?? '';
  return {
    coefficient: BigInt(`${match[1]}${fraction}`),
    denominator: 10n ** BigInt(fraction.length),
  };
}

function moneyCents(value: string): bigint {
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(value.trim());
  if (!match) throw new Error(`Invalid non-negative money amount: ${value}`);
  return BigInt(match[1]) * 100n + BigInt((match[2] ?? '').padEnd(2, '0'));
}

function formatCents(value: bigint): string {
  const sign = value < 0n ? '-' : '';
  const absolute = value < 0n ? -value : value;
  return `${sign}${absolute / 100n}.${String(absolute % 100n).padStart(2, '0')}`;
}

function convertForeignToBase(amount: string, rate: string): bigint {
  const foreignCents = moneyCents(amount);
  const ratio = decimalRatio(rate);
  return divideHalfEven(foreignCents * ratio.coefficient, ratio.denominator);
}

function foreignAmountForTargetBase(targetBase: string, rate: string): string {
  const targetCents = moneyCents(targetBase);
  const ratio = decimalRatio(rate);
  const estimate = targetCents * ratio.denominator / ratio.coefficient;
  for (let offset = 0n; offset <= 10_000n; offset += 1n) {
    for (const candidate of offset === 0n ? [estimate] : [estimate - offset, estimate + offset]) {
      if (candidate <= 0n) continue;
      if (divideHalfEven(candidate * ratio.coefficient, ratio.denominator) === targetCents) {
        return formatCents(candidate);
      }
    }
  }
  throw new Error(`No two-decimal foreign amount maps exactly to ${targetBase} at rate ${rate}.`);
}

function loadCheckpointRecords(): Record<string, string> {
  if (fs.existsSync(RUN_STATE_PATH)) {
    const state = JSON.parse(fs.readFileSync(RUN_STATE_PATH, 'utf8')) as PersistedRunState;
    throw new Error(
      `Run ${state.run_id ?? RUN_ID} already has a private checkpoint. `
      + 'This retained test is intentionally non-resumable so each tenant has exactly one browser session; '
      + 'preserve the partial tenant and use a new run ID/tenant for a clean retest.',
    );
  }
  return {};
}

function isExpectedNegativeFinding(finding: NetworkFinding): boolean {
  if (finding.kind !== 'http') return false;
  const url = finding.url ?? '';
  return (
    finding.status === 409 && /\/api\/v1\/auth\/signup$/.test(url)
  ) || (
    finding.status === 400 && /\/auth\/v1\/token$/.test(url)
  );
}

class Journey {
  readonly results: StepResult[] = [];
  readonly findings: NetworkFinding[] = [];
  private sequence = 0;
  private expectedHttpRules: ExpectedHttpRule[] = [];
  private activeStepId: string | null = null;

  constructor(
    readonly page: Page,
    readonly context: BrowserContext,
    readonly credentials: CredentialManifest,
    readonly records: Record<string, string>,
  ) {
    fs.mkdirSync(SCREENSHOT_ROOT, { recursive: true, mode: 0o700 });
    fs.chmodSync(PRIVATE_ROOT, 0o700);
    fs.chmodSync(SCREENSHOT_ROOT, 0o700);

    page.on('response', response => {
      if (response.status() >= 400) {
        const url = safeUrl(response.url());
        this.findings.push({
          at: new Date().toISOString(),
          kind: 'http',
          status: response.status(),
          url,
          expected: this.expectedHttpRules.some(rule => rule.status === response.status() && rule.url.test(url)),
          method: response.request().method(),
          resource_type: response.request().resourceType(),
          step: this.activeStepId ?? undefined,
        });
      }
      if (
        response.status() === 200
        && response.request().method() === 'GET'
        && /\/api\/v1\/tenant-users$/.test(safeUrl(response.url()))
      ) {
        void response.json().then((payload: { items?: Array<{
          tenant_id?: string;
          user_id?: string;
          email?: string | null;
          status?: string;
          must_change_password?: boolean;
        }> }) => {
          for (const observed of payload.items ?? []) {
            const matched = this.credentials.accounts.find(item => item.email === observed.email);
            if (!matched) continue;
            if (observed.user_id) {
              matched.user_id = observed.user_id;
              this.records[`USER_${matched.code}`] = observed.user_id;
            }
            if (observed.tenant_id) this.credentials.tenant_id = observed.tenant_id;
            if (observed.status && matched.status !== 'active') matched.status = observed.status;
            if (typeof observed.must_change_password === 'boolean' && matched.status !== 'active') {
              matched.must_change_password = observed.must_change_password;
            }
          }
          saveCredentials(this.credentials);
        }).catch(() => {});
      }
    });
    page.on('requestfailed', request => {
      const detail = sanitize(request.failure()?.errorText);
      this.findings.push({
        at: new Date().toISOString(),
        kind: 'requestfailed',
        url: safeUrl(request.url()),
        detail,
        expected: request.method() === 'GET' && detail.includes('net::ERR_ABORTED'),
        method: request.method(),
        resource_type: request.resourceType(),
        step: this.activeStepId ?? undefined,
      });
    });
    page.on('console', message => {
      if (message.type() === 'error') {
        this.findings.push({
          at: new Date().toISOString(),
          kind: 'console',
          detail: sanitize(message.text()),
          step: this.activeStepId ?? undefined,
        });
      }
    });
  }

  private async screenshot(id: string, title: string): Promise<string | undefined> {
    if (this.page.isClosed()) return undefined;
    const filename = `${String(++this.sequence).padStart(3, '0')}-${slug(id)}-${slug(title)}.png`;
    const destination = path.join(SCREENSHOT_ROOT, filename);
    try {
      await this.page.screenshot({
        path: destination,
        fullPage: false,
        mask: [this.page.locator('input[type="password"], input[type="email"]')],
      });
      fs.chmodSync(destination, 0o600);
      return path.relative(PRIVATE_ROOT, destination);
    } catch {
      return undefined;
    }
  }

  async step(
    id: string,
    title: string,
    action: () => Promise<void>,
    options: { fatal?: boolean; screenshot?: boolean } = {},
  ): Promise<StepResult> {
    const started = new Date().toISOString();
    this.activeStepId = id;
    let status: StepStatus = 'PASS';
    let detail: string | undefined;
    try {
      await test.step(`${id} · ${title}`, action);
    } catch (error) {
      status = error instanceof BlockedError
        ? 'BLOCKED'
        : error instanceof SkippedError
          ? 'SKIPPED'
          : 'FAIL';
      detail = sanitize(error);
    }
    const evidence = options.screenshot === false ? undefined : await this.screenshot(id, title);
    const result: StepResult = {
      id,
      title,
      status,
      started_at: started,
      finished_at: new Date().toISOString(),
      url: safeUrl(this.page.url()),
      detail,
      evidence,
    };
    this.results.push(result);
    this.persistState();
    this.activeStepId = null;
    if (options.fatal && status !== 'PASS') {
      throw new Error(`${id} is ${status}: ${detail ?? title}`);
    }
    return result;
  }

  block(message: string): never {
    throw new BlockedError(message);
  }

  skip(message: string): never {
    throw new SkippedError(message);
  }

  passed(id: string): boolean {
    return this.results.some(result => result.id === id && result.status === 'PASS');
  }

  require(ids: string[]): void {
    const missing = ids.filter(id => !this.passed(id));
    if (missing.length) this.block(`Prerequisite step(s) did not pass: ${missing.join(', ')}`);
  }

  async expectHttp<T>(rules: ExpectedHttpRule[], action: () => Promise<T>): Promise<T> {
    this.expectedHttpRules.push(...rules);
    try {
      return await action();
    } finally {
      this.expectedHttpRules.splice(this.expectedHttpRules.length - rules.length, rules.length);
    }
  }

  private persistState(): void {
    fs.writeFileSync(RUN_STATE_PATH, `${JSON.stringify({
      run_id: RUN_ID,
      expected_sha: EXPECTED_SHA,
      tenant_id: this.credentials.tenant_id,
      updated_at: new Date().toISOString(),
      results: this.results,
      network_findings: this.findings,
      records: this.records,
    }, null, 2)}\n`, { mode: 0o600 });
    fs.chmodSync(RUN_STATE_PATH, 0o600);
  }

  writeReport(): void {
    const rows = this.results.map(result => (
      `| ${result.id} | ${result.status} | ${result.title.replace(/\|/g, '\\|')} | ${result.detail?.replace(/\|/g, '\\|') ?? ''} | ${result.evidence ?? ''} |`
    ));
    const roleRows = this.credentials.accounts.map(item => (
      `| ${item.code} | ${redactedAlias(item.email)} | ${item.status} | ${item.must_change_password ? 'yes' : 'no'} |`
    ));
    const fiveHundreds = this.findings.filter(item => item.kind === 'http' && (item.status ?? 0) >= 500);
    const recordRows = Object.entries(this.records).sort(([left], [right]) => left.localeCompare(right)).map(([key, value]) => (
      `| ${sanitize(key).replace(/\|/g, '\\|')} | ${sanitize(value).replace(/\|/g, '\\|')} |`
    ));
    const body = [
      `# Ishantech production browser execution — ${RUN_ID}`,
      '',
      `- Origin: ${ORIGIN}`,
      `- Expected/deployed SHA: ${EXPECTED_SHA}`,
      `- Tenant ID: ${this.credentials.tenant_id ?? 'not captured'}`,
      `- Browser model: one continuous Playwright BrowserContext; sequential logout/login for every role`,
      `- Tenant retained: ${String(this.credentials.retained)}`,
      `- Completed: ${new Date().toISOString()}`,
      `- HTTP 5xx observed: ${fiveHundreds.length}`,
      '',
      '| Step | Result | Browser action | Detail | Private screenshot |',
      '| --- | --- | --- | --- | --- |',
      ...rows,
      '',
      '| Record | Browser-observed identifier/status |',
      '| --- | --- |',
      ...recordRows,
      '',
      '| Role | Redacted account | Credential state | Password change pending |',
      '| --- | --- | --- | --- |',
      ...roleRows,
      '',
      'Raw video, trace, screenshots, JSON, and credentials are intentionally ignored and must remain mode 0600/0700.',
      '',
    ].join('\n');
    fs.writeFileSync(REPORT_PATH, body, { mode: 0o600 });
    fs.chmodSync(REPORT_PATH, 0o600);
    this.persistState();
  }
}

async function selectOptionContaining(select: Locator, text: string): Promise<string> {
  await expect.poll(async () => select.locator('option').evaluateAll((options, expected) => {
    const match = options.find(option => option.textContent?.includes(expected as string));
    return match instanceof HTMLOptionElement ? match.value : '';
  }, text), { timeout: 30_000 }).not.toBe('');
  const value = await select.locator('option').evaluateAll((options, expected) => {
    const match = options.find(option => option.textContent?.includes(expected as string));
    return match instanceof HTMLOptionElement ? match.value : '';
  }, text);
  await select.selectOption(value);
  return value;
}

async function login(page: Page, credentials: CredentialAccount, expected: RegExp = /\/app\/(?:copilot|profile)/): Promise<void> {
  await page.goto(`${ORIGIN}/login`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /^sign in$/i })).toBeVisible();
  await page.locator('#email').fill(credentials.email);
  await page.locator('#password').fill(credentials.password);
  await page.getByRole('button', { name: /^sign in$/i }).click();
  await page.waitForURL(expected, { timeout: 60_000 });
}

async function logout(page: Page): Promise<void> {
  if (new URL(page.url()).origin !== ORIGIN || !page.url().includes('/app/')) {
    await page.goto(`${ORIGIN}/app/profile`, { waitUntil: 'domcontentloaded' });
  } else if (!page.url().includes('/app/profile')) {
    await page.goto(`${ORIGIN}/app/profile`, { waitUntil: 'domcontentloaded' });
  }
  const signOut = page.getByRole('button', { name: /^sign out$/i });
  await expect(signOut).toBeVisible();
  await signOut.click();
  await page.waitForURL(/\/login$/, { timeout: 30_000 });
}

async function rotatePassword(page: Page, current: string, next: string, initialRequired = true): Promise<void> {
  await expect(page).toHaveURL(/\/app\/profile/);
  if (initialRequired) {
    await expect(page.getByRole('alert')).toContainText(/change your initial password/i);
  }
  const component = page.locator('app-change-password');
  await component.locator('#current_password').fill(current);
  await component.locator('#new_password').fill(next);
  await component.locator('#confirm_password').fill(next);
  await component.getByRole('button', { name: /^update password$/i }).click();
  await expect(component.getByRole('status').or(component.getByText(/password updated/i))).toBeVisible({ timeout: 30_000 });
}

async function optionValues(select: Locator): Promise<string[]> {
  return select.locator('option[value]').evaluateAll(options => options
    .map(option => (option as HTMLOptionElement).value)
    .filter(Boolean));
}

async function fillStripeField(page: Page, fieldName: string, value: string, required = true): Promise<void> {
  const frames = page.locator('iframe[name^="__privateStripeFrame"]');
  await expect(frames.first()).toBeVisible({ timeout: 30_000 });
  const count = await frames.count();
  for (let index = 0; index < count; index += 1) {
    const input = page.frameLocator('iframe[name^="__privateStripeFrame"]').nth(index).locator(`input[name="${fieldName}"]`);
    if (await input.count()) {
      await input.fill(value);
      return;
    }
  }
  if (required) throw new Error(`Stripe field ${fieldName} was not visible.`);
}

async function signupIshantech(
  page: Page,
  owner: CredentialAccount,
  onTenantCreated: (tenantId: string) => void,
): Promise<void> {
  await page.goto(`${ORIGIN}/signup`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /create your firm/i })).toBeVisible();

  await page.locator('#firm').fill(DATA.company);
  await page.locator('#email').fill(owner.email);
  await page.locator('#password').fill(owner.password);
  await page.locator('#confirm_password').fill(owner.password);
  await page.locator('#country').selectOption('SG');
  await page.getByRole('button', { name: /continue to plan/i }).click();

  await expect(page.getByRole('heading', { name: /pick a plan/i })).toBeVisible({ timeout: 60_000 });
  const tenantId = await page.evaluate(() => localStorage.getItem('aethos_tenant_id'));
  expect(tenantId).toMatch(/^[0-9a-f-]{36}$/i);
  onTenantCreated(tenantId as string);
  const interval = page.getByRole('radiogroup', { name: /billing interval/i });
  if (await interval.count()) {
    await interval.getByRole('radio', { name: /monthly/i }).click();
  }
  const plans = page.getByRole('radiogroup', { name: /plan tier/i });
  await expect(plans).toBeVisible();
  await plans.getByRole('radio', { name: /^growth\b/i }).click();
  await page.getByRole('button', { name: /continue to card/i }).click();

  await expect(page.getByRole('heading', { name: /confirm your card/i })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/test mode/i)).toBeVisible();
  await fillStripeField(page, 'cardnumber', '4242 4242 4242 4242');
  await fillStripeField(page, 'exp-date', '12 / 34');
  await fillStripeField(page, 'cvc', '123');
  await fillStripeField(page, 'postal', '018989', false);
  const startTrial = page.getByRole('button', { name: /start 14-day trial/i });
  await expect(startTrial).toBeEnabled({ timeout: 30_000 });
  await startTrial.click();
  await page.waitForURL(/\/app\/copilot(?:\?.*)?$/, { timeout: 90_000 });
  await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible();
}

async function inviteTenantUser(page: Page, target: CredentialAccount): Promise<void> {
  const component = page.locator('app-tenant-users');
  const table = component.locator('table[aria-label="Tenant users"]');
  await expect(table).toBeVisible();
  const existing = table.locator('tr').filter({ hasText: target.email });
  if (await existing.count()) {
    await expect(existing.first()).toContainText(target.label);
    return;
  }

  const form = component.locator('form').filter({ hasText: /invite user/i });
  await page.addStyleTag({
    content: 'app-tenant-users [role="status"] .font-mono, app-tenant-users [role="status"] a{filter:blur(8px)!important;user-select:none!important;}',
  });
  await form.getByLabel('Email', { exact: true }).fill(target.email);
  await form.getByLabel('Display name', { exact: true }).fill(`${target.label} · Ishantech`);
  await form.getByLabel('Role', { exact: true }).selectOption(target.code);
  await form.getByLabel('Temporary password', { exact: true }).fill(target.password);
  await form.getByRole('button', { name: /^create user$/i }).click();
  await expect(component.getByRole('status')).toContainText(/user invited/i, { timeout: 60_000 });
  await expect(table.locator('tr').filter({ hasText: target.email })).toContainText(target.label, { timeout: 30_000 });
}

const ROLE_SURFACES: Record<Exclude<RoleCode, 'tenant_owner' | 'timesheet_employee'>, { route: string; anchor: RegExp }> = {
  tenant_admin: { route: '/app/settings', anchor: /^settings$/i },
  cfo: { route: '/app/reports', anchor: /^reports$/i },
  finance_controller: { route: '/app/accounting/journals', anchor: /journal entries/i },
  finance_ops_manager: { route: '/app/inbox', anchor: /inbox/i },
  finance_approver: { route: '/app/approvals', anchor: /approvals/i },
  finance_operator: { route: '/app/invoices', anchor: /^invoices$/i },
  procurement_manager: { route: '/app/bills', anchor: /^bills$/i },
  buyer_requester: { route: '/app/bills', anchor: /^bills$/i },
  ap_manager: { route: '/app/billing-runs', anchor: /pay bills/i },
  ap_clerk: { route: '/app/bills', anchor: /^bills$/i },
  ar_manager: { route: '/app/invoices', anchor: /^invoices$/i },
  billing_specialist: { route: '/app/invoices', anchor: /^invoices$/i },
  collections_specialist: { route: '/app/payments', anchor: /payments/i },
  gl_accountant: { route: '/app/accounting/journals', anchor: /journal entries/i },
  close_manager: { route: '/app/accounting/journals', anchor: /month-end close|journal entries/i },
  engagement_manager: { route: '/app/engagements', anchor: /^engagements$/i },
  resource_manager: { route: '/app/people', anchor: /^people$/i },
  auditor: { route: '/app/reports', anchor: /^reports$/i },
  executive_viewer: { route: '/app/reports', anchor: /^reports$/i },
  ai_ops_admin: { route: '/app/settings', anchor: /^settings$/i },
};

async function ensureTaxRate(page: Page, name: string, rate: string): Promise<void> {
  await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
  const component = page.locator('app-tax-rates');
  await expect(component.getByLabel('Loading tax rates')).toHaveCount(0, { timeout: 60_000 });
  const table = component.locator('table[aria-label="Tax Rates"]');
  if (await table.getByText(name, { exact: true }).count()) return;
  await component.getByRole('button', { name: /add new tax rate/i }).click();
  const dialog = page.getByRole('dialog', { name: /add tax rate/i });
  await dialog.locator('#tr-name').fill(name);
  await dialog.locator('#tr-rate').fill(rate);
  await dialog.locator('#tr-market').selectOption('SG');
  await dialog.getByRole('button', { name: /^add tax rate$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(component.locator('table[aria-label="Tax Rates"]').getByText(name, { exact: true })).toBeVisible();
}

async function lookupFxProvenance(page: Page, requestedDate: string): Promise<FxProvenance> {
  const component = page.locator('app-fx-rates-inspector');
  await expect(component.getByRole('heading', { name: /historical fx provenance/i })).toBeVisible();
  await component.locator('#fx-from-currency').selectOption('USD');
  await component.locator('#fx-to-currency').selectOption('SGD');
  await component.locator('#fx-rate-date').fill(requestedDate);
  const lookup = page.waitForResponse(response => {
    const url = new URL(response.url());
    return response.request().method() === 'GET'
      && url.pathname === '/api/v1/fx-rates/USD/SGD'
      && url.searchParams.get('rate_date') === requestedDate;
  });
  await component.getByRole('button', { name: /^lookup$/i }).click();
  const response = await lookup;
  expect(response.ok()).toBe(true);
  const provenance = await response.json() as FxProvenance;
  const visible = component.getByLabel('Matched FX rate provenance');
  await expect(visible).toContainText(provenance.rate);
  await expect(visible).toContainText(provenance.requested_rate_date);
  await expect(visible).toContainText(provenance.rate_date);
  await expect(visible).toContainText(provenance.fx_rate_id ?? 'Identity rate');
  await expect(visible).toContainText(provenance.source);
  return provenance;
}

async function ensureService(page: Page, service: typeof DATA.services[number]): Promise<void> {
  await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
  const component = page.locator('app-services');
  await expect(component).toBeVisible();
  await expect(component.getByLabel('Loading services')).toHaveCount(0, { timeout: 60_000 });
  if (await component.getByText(service.name, { exact: true }).count()) return;
  await component.getByRole('button', { name: /add new service/i }).click();
  const dialog = page.getByRole('dialog', { name: /add service/i });
  await dialog.locator('#svc-code').fill(service.code);
  await dialog.locator('#svc-name').fill(service.name);
  await dialog.locator('#svc-line').selectOption(service.line);
  await dialog.locator('#svc-billing').selectOption(service.unit);
  await dialog.locator('[formcontrolname="default_currency"]').selectOption(service.currency);
  await dialog.locator('#svc-rate').fill(service.rate);
  await dialog.locator('#svc-desc').fill(`${TAG} deterministic launch-readiness service`);
  await dialog.getByRole('button', { name: /^add service$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  await expect(component.getByText(service.name, { exact: true })).toBeVisible();
}

async function ensureContact(page: Page, name: string, kind: 'customer' | 'vendor'): Promise<void> {
  await page.goto(`${ORIGIN}/app/clients`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /^contacts$/i })).toBeVisible();
  await expect(page.getByLabel('Loading contacts')).toHaveCount(0, { timeout: 60_000 });
  if (await page.getByRole('button', { name: `View ${name}`, exact: true }).count()) return;
  await page.getByRole('button', { name: /new contact|add first contact/i }).first().click();
  const dialog = page.getByRole('dialog', { name: /new contact/i });
  await dialog.locator('#client-name').fill(name);
  await dialog.locator('#client-kind').selectOption(kind);
  await dialog.locator('#contact-phone').fill('+65 6000 2026');
  await dialog.locator('#contact-website').fill('https://example.test');
  await dialog.getByRole('button', { name: /^create contact$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  await expect(page.getByRole('button', { name: `View ${name}`, exact: true })).toBeVisible();
}

async function ensureEngagement(page: Page, engagement: typeof DATA.engagements[number]): Promise<void> {
  await page.goto(`${ORIGIN}/app/engagements`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /^engagements$/i })).toBeVisible();
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 60_000 });
  if (await page.getByRole('button', { name: `Open engagement ${engagement.name}`, exact: true }).count()) return;
  await page.getByRole('button', { name: /create new engagement/i }).click();
  const dialog = page.getByRole('dialog', { name: /new engagement/i });
  await dialog.locator('#eng-name').fill(engagement.name);
  await selectOptionContaining(dialog.locator('#eng-client'), engagement.customer);
  await selectOptionContaining(dialog.locator('#eng-service'), engagement.service);
  const service = DATA.services.find(item => item.name === engagement.service);
  await dialog.locator('#eng-service-line').selectOption(service?.line ?? 'advisory');
  await dialog.locator('#eng-billing').selectOption(engagement.billing);
  await dialog.locator('#eng-currency').selectOption(engagement.currency);
  await dialog.locator('#eng-value').fill(engagement.value);
  if (engagement.billing === 'retainer') await dialog.locator('#eng-retainer-monthly').fill(engagement.terms);
  if (engagement.billing === 'milestone') await dialog.locator('#eng-milestone-total').fill(engagement.terms);
  if (engagement.billing === 'fixed_fee') await dialog.locator('#eng-fixed-fee').fill(engagement.terms);
  await dialog.locator('#eng-start-date').fill(engagement.start);
  await dialog.locator('#eng-description').fill(`${TAG} deterministic engagement for production E2E`);
  await dialog.getByRole('button', { name: /^create engagement$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  await expect(page.getByRole('button', { name: `Open engagement ${engagement.name}`, exact: true })).toBeVisible();
}

async function ensureProject(page: Page, project: typeof DATA.projects[number]): Promise<void> {
  await page.goto(`${ORIGIN}/app/projects`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /^projects$/i })).toBeVisible();
  await expect(page.getByLabel('Loading projects')).toHaveCount(0, { timeout: 60_000 });
  const table = page.locator('table[aria-label="Projects"]');
  if (await table.getByText(project.name, { exact: true }).count()) return;
  await page.getByRole('button', { name: /create new project/i }).click();
  const dialog = page.getByRole('dialog', { name: /new project/i });
  await dialog.locator('#proj-name').fill(project.name);
  await selectOptionContaining(dialog.locator('#proj-engagement'), project.engagement);
  await dialog.locator('#ps-status').selectOption('active');
  await dialog.locator('#ps-budget').fill('30000');
  await dialog.locator('#ps-budget-hours').fill('120');
  await dialog.getByRole('button', { name: /^create project$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  await expect(table.getByText(project.name, { exact: true })).toBeVisible();
}

async function assignEmployeeToProject(page: Page, projectName: string, employeeName: string): Promise<void> {
  await page.goto(`${ORIGIN}/app/projects`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: `Manage team for ${projectName}`, exact: true }).click();
  const dialog = page.getByRole('dialog', { name: /project team/i });
  if (await dialog.getByText(employeeName, { exact: true }).count()) {
    await dialog.getByRole('button', { name: /close panel/i }).click();
    return;
  }
  await selectOptionContaining(dialog.locator('[formcontrolname="employee_id"]'), employeeName);
  await dialog.locator('[formcontrolname="role"]').fill('Consultant');
  await dialog.locator('[formcontrolname="override_rate"]').fill('300');
  await dialog.getByRole('button', { name: /add to project/i }).click();
  await expect(dialog.getByText(employeeName, { exact: true })).toBeVisible({ timeout: 60_000 });
  await dialog.getByRole('button', { name: /close panel/i }).click();
}

async function switchMainRole(page: Page, manifest: CredentialManifest, code: RoleCode): Promise<void> {
  if (new URL(page.url()).origin === ORIGIN && page.url().includes('/app/')) {
    await logout(page);
  }
  await login(page, account(manifest, code), /\/app\/copilot/);
}

async function ensureVendorControls(page: Page, name: string, remittanceEmail: string): Promise<void> {
  await page.goto(`${ORIGIN}/app/clients`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: `View ${name}`, exact: true }).click();
  await page.waitForURL(/\/app\/clients\/[0-9a-f-]+$/i, { timeout: 60_000 });
  await expect(page.getByLabel('Loading contact')).toHaveCount(0, { timeout: 60_000 });
  if (await page.getByRole('button', { name: /edit contact/i }).count()) {
    await page.getByRole('button', { name: /edit contact/i }).click();
    const dialog = page.getByRole('dialog', { name: /edit contact/i });
    if (await dialog.locator('#edit-email').count()) await dialog.locator('#edit-email').fill(remittanceEmail);
    await dialog.locator('#edit-vendor-onboarding').selectOption('pending');
    await dialog.locator('#edit-vendor-bank').selectOption('verified');
    await dialog.locator('#edit-vendor-tax').selectOption('valid');
    await dialog.locator('#edit-vendor-sanctions').selectOption('clear');
    await dialog.locator('#edit-vendor-remittance').selectOption('verified');
    await dialog.locator('#edit-vendor-remittance-email').fill(remittanceEmail);
    await dialog.getByRole('button', { name: /save changes/i }).click();
    await expect(dialog).toBeHidden({ timeout: 60_000 });
  }
  const approve = page.getByRole('button', { name: /approve vendor onboarding/i });
  await expect(approve).toBeVisible({ timeout: 60_000 });
  if (await approve.isEnabled()) {
    await approve.click();
    await expect(page.getByRole('status').filter({ hasText: /vendor onboarding approved/i })).toBeVisible({ timeout: 60_000 });
  }
  await expect(page.locator('section[aria-labelledby="vendor-onboarding-heading"]')).toContainText(/approved for payment runs/i);
}

function mondayIso(date: Date): string {
  const result = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const weekday = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - weekday);
  return `${result.getFullYear()}-${String(result.getMonth() + 1).padStart(2, '0')}-${String(result.getDate()).padStart(2, '0')}`;
}

async function openTimesheetWeek(page: Page, targetMonday: string): Promise<void> {
  await expect(page.locator('.animate-spin')).toHaveCount(0, { timeout: 60_000 });
  const current = new Date(`${mondayIso(new Date())}T00:00:00`);
  const target = new Date(`${targetMonday}T00:00:00`);
  const weeks = Math.round((target.getTime() - current.getTime()) / (7 * 86_400_000));
  const button = weeks < 0
    ? page.getByRole('button', { name: /previous week/i })
    : page.getByRole('button', { name: /next week/i });
  for (let index = 0; index < Math.abs(weeks); index += 1) {
    const previous = await page.getByRole('heading', { name: /my week/i }).locator('..').locator('p').innerText();
    const loaded = page.waitForResponse(response => (
      response.request().method() === 'GET'
      && /\/api\/v1\/timesheet\/entries$/.test(new URL(response.url()).pathname)
    ));
    await button.click();
    expect((await loaded).ok()).toBe(true);
    await expect(page.locator('.animate-spin')).toHaveCount(0, { timeout: 60_000 });
    await expect.poll(async () => page.getByRole('heading', { name: /my week/i }).locator('..').locator('p').innerText()).not.toBe(previous);
  }
}

async function nextTimesheetWeek(page: Page): Promise<void> {
  const previous = await page.getByRole('heading', { name: /my week/i }).locator('..').locator('p').innerText();
  const loaded = page.waitForResponse(response => (
    response.request().method() === 'GET'
    && /\/api\/v1\/timesheet\/entries$/.test(new URL(response.url()).pathname)
  ));
  await page.getByRole('button', { name: /next week/i }).click();
  expect((await loaded).ok()).toBe(true);
  await expect(page.locator('.animate-spin')).toHaveCount(0, { timeout: 60_000 });
  await expect.poll(async () => page.getByRole('heading', { name: /my week/i }).locator('..').locator('p').innerText()).not.toBe(previous);
}

async function enterAndSubmitWeek(page: Page, projectName: string, hours: number[]): Promise<void> {
  const row = page.locator('tbody tr').filter({ hasText: projectName }).first();
  await expect(row).toBeVisible();
  const inputs = row.locator('input[type="number"]');
  expect(await inputs.count()).toBe(7);
  for (let index = 0; index < hours.length; index += 1) {
    if (hours[index] <= 0) continue;
    const saved = page.waitForResponse(response => (
      /\/api\/v1\/timesheet\/entries(?:\/[0-9a-f-]{36})?$/.test(safeUrl(response.url()))
      && ['POST', 'PATCH'].includes(response.request().method())
    ));
    await inputs.nth(index).fill(String(hours[index]));
    await inputs.nth(index).blur();
    expect((await saved).ok()).toBe(true);
  }
  await expect(row.locator('td').last()).toHaveText(String(hours.reduce((total, value) => total + value, 0)));
  await expect(page.getByRole('alert')).toHaveCount(0);
  const submit = page.getByRole('button', { name: /submit week/i });
  await expect(submit).toBeEnabled({ timeout: 60_000 });
  await submit.click();
  await expect(page.getByText(/submitted and awaiting approval/i)).toBeVisible({ timeout: 60_000 });
}

async function draftManualInvoice(
  page: Page,
  options: {
    engagement: string;
    client: string;
    issue: string;
    due: string;
    description: string;
    amount: string;
    taxRateName?: string;
    selectTime?: boolean;
  },
): Promise<string> {
  await page.goto(`${ORIGIN}/app/invoices`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading invoices')).toHaveCount(0, { timeout: 60_000 });
  let row = page.locator('table[aria-label="Invoices"] tbody tr')
    .filter({ hasText: options.client })
    .filter({ hasText: options.due });
  if (await row.count()) return (await row.first().locator('td').first().innerText()).trim();

  await page.goto(`${ORIGIN}/app/engagements`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: `Open engagement ${options.engagement}`, exact: true }).click();
  await page.waitForURL(/\/app\/engagements\/[0-9a-f-]+$/i, { timeout: 60_000 });
  await page.getByRole('button', { name: /draft an invoice for this engagement/i }).click();
  const dialog = page.getByRole('dialog', { name: /draft invoice/i });
  await dialog.locator('#inv-issue-date').fill(options.issue);
  await dialog.locator('#inv-due-date').fill(options.due);
  if (options.taxRateName) await selectOptionContaining(dialog.locator('#inv-tax-rate'), options.taxRateName);
  if (options.selectTime) {
    await expect(dialog.getByRole('button', { name: /select all/i })).toBeVisible({ timeout: 60_000 });
    await dialog.getByRole('button', { name: /select all/i }).click();
  } else {
    await dialog.locator('[name="inv-extra-on"]').check();
    await dialog.locator('[name="inv-extra-desc"]').fill(options.description);
    await dialog.locator('[name="inv-extra-qty"]').fill('1');
    await dialog.locator('[name="inv-extra-price"]').fill(options.amount);
    await dialog.locator('[name="inv-extra-price"]').blur();
  }
  await expect(dialog.getByRole('button', { name: /create draft invoice/i })).toBeEnabled();
  await dialog.getByRole('button', { name: /create draft invoice/i }).click();
  await page.waitForURL(/\/app\/invoices(?:\?.*)?$/, { timeout: 60_000 });
  await expect(page.getByLabel('Loading invoices')).toHaveCount(0, { timeout: 60_000 });
  row = page.locator('table[aria-label="Invoices"] tbody tr')
    .filter({ hasText: options.client })
    .filter({ hasText: options.due });
  await expect(row.first()).toBeVisible();
  return (await row.first().locator('td').first().innerText()).trim();
}

async function approveAndSendInvoice(page: Page, invoiceNumber: string): Promise<void> {
  await page.goto(`${ORIGIN}/app/invoices`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading invoices')).toHaveCount(0, { timeout: 60_000 });
  const row = page.locator('table[aria-label="Invoices"] tbody tr').filter({ hasText: invoiceNumber });
  const approve = row.getByRole('button', { name: `Approve invoice ${invoiceNumber}`, exact: true });
  if (await approve.count()) {
    await approve.click();
    await expect(row.getByRole('button', { name: `Send invoice ${invoiceNumber}`, exact: true })).toBeVisible({ timeout: 60_000 });
  }
  const send = row.getByRole('button', { name: `Send invoice ${invoiceNumber}`, exact: true });
  if (await send.count()) {
    await send.click();
    await expect(page.getByRole('status').filter({ hasText: /invoice sent/i })).toBeVisible({ timeout: 60_000 });
  }
  await expect(row).toContainText(/\bsent\b/i, { timeout: 60_000 });
  await expect(row.getByRole('button', { name: `Send invoice ${invoiceNumber}`, exact: true })).toHaveCount(0);
}

async function captureInvoiceId(page: Page, invoiceNumber: string): Promise<string> {
  await page.goto(`${ORIGIN}/app/invoices`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading invoices')).toHaveCount(0, { timeout: 60_000 });
  await page.locator('table[aria-label="Invoices"] tbody tr').filter({ hasText: invoiceNumber }).click();
  await page.waitForURL(/\/app\/invoices\/[0-9a-f-]{36}$/i, { timeout: 60_000 });
  const id = new URL(page.url()).pathname.split('/').pop() ?? '';
  expect(id).toMatch(/^[0-9a-f-]{36}$/i);
  return id;
}

async function captureBillId(page: Page, billNumber: string): Promise<string> {
  await page.goto(`${ORIGIN}/app/bills`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading bills')).toHaveCount(0, { timeout: 60_000 });
  await page.getByRole('button', { name: `View bill ${billNumber}`, exact: true }).click();
  await page.waitForURL(/\/app\/bills\/[0-9a-f-]{36}$/i, { timeout: 60_000 });
  const id = new URL(page.url()).pathname.split('/').pop() ?? '';
  expect(id).toMatch(/^[0-9a-f-]{36}$/i);
  return id;
}

async function recordInvoicePayment(
  page: Page,
  invoiceNumber: string,
  amount: string,
  date: string,
  reference: string,
): Promise<string> {
  await page.goto(`${ORIGIN}/app/invoices`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading invoices')).toHaveCount(0, { timeout: 60_000 });
  const row = page.locator('table[aria-label="Invoices"] tbody tr').filter({ hasText: invoiceNumber });
  await row.getByRole('button', { name: `Mark invoice ${invoiceNumber} paid`, exact: true }).click();
  const dialog = page.getByRole('dialog', { name: new RegExp(`mark ${invoiceNumber} paid`, 'i') });
  await dialog.locator('#pay-amount').fill(amount);
  await dialog.locator('#pay-date').fill(date);
  await dialog.locator('#pay-notes').fill(`${TAG} ${reference}`);
  await dialog.getByRole('button', { name: /^record payment$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  return (await row.innerText()).toLowerCase();
}

async function createProcurementOrder(
  page: Page,
  vendor: string,
  issueDate: string,
  amount: string,
  tax: string,
): Promise<string> {
  await page.goto(`${ORIGIN}/app/bills`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading procurement documents')).toHaveCount(0, { timeout: 60_000 });
  const section = page.locator('section[aria-labelledby="procurement-heading"]');
  const existing = section.locator('div.grid').filter({ hasText: vendor });
  if (await existing.count()) {
    const match = (await existing.last().innerText()).match(/(?:PO|SO|PR)-[A-Z0-9-]+/i);
    if (match) return match[0];
  }
  await page.getByRole('button', { name: /create new purchase order or service order/i }).click();
  const dialog = page.getByRole('dialog', { name: /new procurement/i });
  await dialog.locator('#order-type').selectOption('service_order');
  await dialog.locator('#order-currency').selectOption('SGD');
  await selectOptionContaining(dialog.locator('#order-vendor'), vendor);
  await dialog.locator('#order-issue-date').fill(issueDate);
  await dialog.locator('#order-service-start').fill('2026-05-01');
  await dialog.locator('#order-service-end').fill('2026-05-31');
  await dialog.locator('#order-line-desc-0').fill(`${TAG} TX-09 contractor services`);
  await dialog.locator('#order-line-qty-0').fill('1');
  await dialog.locator('#order-line-price-0').fill(amount);
  await dialog.locator('#order-line-tax-0').fill(tax);
  await dialog.getByRole('button', { name: /^create$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  const row = section.locator('div.grid').filter({ hasText: vendor }).last();
  await expect(row).toBeVisible();
  const match = (await row.innerText()).match(/(?:PO|SO|PR)-[A-Z0-9-]+/i);
  if (!match) throw new Error('Created procurement document number was not visible.');
  return match[0];
}

async function approveProcurementOrder(page: Page, documentNumber: string): Promise<void> {
  await page.goto(`${ORIGIN}/app/bills`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading procurement documents')).toHaveCount(0, { timeout: 60_000 });
  const section = page.locator('section[aria-labelledby="procurement-heading"]');
  const row = section.locator('div.grid').filter({ hasText: documentNumber }).last();
  await expect(row).toBeVisible({ timeout: 60_000 });
  const approve = row.getByRole('button', { name: /^approve$/i });
  if (await approve.count()) {
    await approve.click();
    await expect(row).toContainText(/approved/i, { timeout: 60_000 });
  } else {
    await expect(row).toContainText(/approved/i);
  }
}

interface BillInput {
  vendor: string;
  vendorInvoice: string;
  issue: string;
  due: string;
  currency: string;
  description: string;
  amount: string;
  tax: string;
  purchaseOrder?: string;
  prepaid?: { start: string; end: string };
}

async function createBill(page: Page, input: BillInput): Promise<string> {
  await page.goto(`${ORIGIN}/app/bills`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading bills')).toHaveCount(0, { timeout: 60_000 });
  const table = page.locator('table[aria-label="Bills"]');
  let row = table.locator('tbody tr').filter({ hasText: input.vendor }).filter({ hasText: input.issue });
  if (await row.count()) return (await row.first().locator('td').first().innerText()).trim();

  await page.getByRole('button', { name: /create new bill/i }).click();
  const dialog = page.getByRole('dialog', { name: /new bill/i });
  await selectOptionContaining(dialog.locator('#bill-vendor'), input.vendor);
  if (input.purchaseOrder) await selectOptionContaining(dialog.locator('#bill-purchase-order'), input.purchaseOrder);
  await dialog.locator('#bill-inv-num').fill(input.vendorInvoice);
  await dialog.locator('#bill-issue-date').fill(input.issue);
  await dialog.locator('#bill-due-date').fill(input.due);
  await dialog.locator('#bill-currency').selectOption(input.currency);
  await dialog.locator('#bill-notes').fill(`${TAG} deterministic production E2E bill`);
  await dialog.locator('#line-desc-0').fill(input.description);
  await dialog.locator('#line-qty-0').fill('1');
  await dialog.locator('#line-price-0').fill(input.amount);
  await dialog.locator('#line-tax-0').fill(input.tax);
  if (input.prepaid) {
    await dialog.locator('[formcontrolname="is_prepaid"]').check();
    await dialog.locator('#line-service-start-0').fill(input.prepaid.start);
    await dialog.locator('#line-service-end-0').fill(input.prepaid.end);
  }
  await dialog.getByRole('button', { name: /^create bill$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  row = table.locator('tbody tr').filter({ hasText: input.vendor }).filter({ hasText: input.issue });
  await expect(row.first()).toBeVisible();
  return (await row.first().locator('td').first().innerText()).trim();
}

async function approveBill(page: Page, billNumber: string): Promise<void> {
  await page.goto(`${ORIGIN}/app/bills`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: `View bill ${billNumber}`, exact: true }).click();
  await page.waitForURL(/\/app\/bills\/[0-9a-f-]+$/i, { timeout: 60_000 });
  await expect(page.getByLabel('Loading bill')).toHaveCount(0, { timeout: 60_000 });
  const approve = page.getByRole('button', { name: /^approve$/i });
  if (await approve.count()) {
    await approve.click();
    await expect(page.getByText(/approved/i).first()).toBeVisible({ timeout: 60_000 });
  } else {
    await expect(page.getByText(/approved/i).first()).toBeVisible();
  }
}

async function settleBill(page: Page, billNumber: string, paymentDate: string): Promise<void> {
  await page.goto(`${ORIGIN}/app/billing-runs`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /pay bills/i })).toBeVisible();
  const bill = page.getByRole('checkbox', { name: `Select bill ${billNumber}`, exact: true });
  await expect(bill).toBeVisible({ timeout: 60_000 });
  await bill.check();
  await page.getByRole('button', { name: /next: batch details/i }).click();
  await page.locator('#pay-date').fill(paymentDate);
  await page.locator('#bank-label').fill(`${TAG} Fictional Operating Account`);
  await page.getByRole('button', { name: /^create batch$/i }).click();
  await expect(page.getByRole('button', { name: /^approve batch$/i })).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: /^approve batch$/i }).click();
  const csvButton = page.getByRole('button', { name: /download csv/i });
  await expect(csvButton).toBeEnabled({ timeout: 60_000 });
  const downloadPromise = page.waitForEvent('download');
  await csvButton.click();
  const download = await downloadPromise;
  const target = path.join(PRIVATE_ROOT, `${billNumber}-${paymentDate}-payment-batch.csv`);
  await download.saveAs(target);
  fs.chmodSync(target, 0o600);
  await page.getByRole('button', { name: /mark as sent to bank/i }).click();
  await expect(page.getByRole('button', { name: /confirm settlement/i })).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: /confirm settlement/i }).click();
  await expect(page.getByRole('heading', { name: /batch settled/i })).toBeVisible({ timeout: 60_000 });
}

async function chooseJournalAccount(dialog: Locator, line: number, code: string): Promise<void> {
  const input = dialog.getByRole('textbox', { name: `Account for line ${line}`, exact: true });
  await input.fill(code);
  const suggestions = dialog.getByRole('listbox', { name: `Account suggestions for line ${line}`, exact: true });
  await expect(suggestions).toBeVisible();
  const option = suggestions.getByRole('option').filter({ hasText: new RegExp(`^${code}\\b`) }).first();
  await expect(option).toBeVisible();
  await option.click();
}

async function postManualJournal(
  page: Page,
  options: {
    description: string;
    reason: string;
    date: string;
    reference: string;
    debitCode: string;
    creditCode: string;
    amount: string;
  },
): Promise<'posted' | 'pending'> {
  await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
  const existing = page.locator('table').filter({ hasText: options.reference });
  if (await existing.count()) return 'posted';
  await page.getByRole('button', { name: /new journal entry/i }).click();
  const dialog = page.getByRole('dialog', { name: /post manual journal entry/i });
  await expect(dialog.getByLabel('Manual journal currency')).toHaveValue('SGD');
  await dialog.locator('#jnl-desc').fill(options.description);
  await dialog.locator('#jnl-reason').fill(options.reason);
  await dialog.locator('#jnl-date').fill(options.date);
  await dialog.locator('#jnl-ref').fill(options.reference);
  await chooseJournalAccount(dialog, 1, options.debitCode);
  await dialog.getByRole('combobox', { name: /direction for line 1/i }).selectOption('DR');
  await dialog.getByRole('textbox', { name: /amount for line 1/i }).fill(options.amount);
  await dialog.getByRole('textbox', { name: /note for line 1/i }).fill(options.reference);
  await chooseJournalAccount(dialog, 2, options.creditCode);
  await dialog.getByRole('combobox', { name: /direction for line 2/i }).selectOption('CR');
  await dialog.getByRole('textbox', { name: /amount for line 2/i }).fill(options.amount);
  await dialog.getByRole('textbox', { name: /note for line 2/i }).fill(options.reference);
  await expect(dialog.getByRole('status', { name: /balanced/i }).or(dialog.getByText(/^balanced$/i))).toBeVisible();
  await dialog.getByRole('button', { name: /^post journal entry$/i }).click();
  await expect(dialog).toBeHidden({ timeout: 60_000 });
  const toast = page.getByRole('status').filter({ hasText: /journal|inbox/i }).last();
  await expect(toast).toBeVisible();
  const text = (await toast.innerText()).toLowerCase();
  return text.includes('routed to inbox') ? 'pending' : 'posted';
}

async function assertVisibleJournalPosting(
  page: Page,
  expected: ExpectedJournalPosting,
): Promise<VisibleJournalPosting> {
  if (!!expected.referenceId === !!expected.rowText) {
    throw new Error('Journal evidence requires exactly one reference ID or visible row text.');
  }

  await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading journal entries')).toHaveCount(0, { timeout: 60_000 });

  let rows = page.locator(
    `[data-testid="journal-entry-row"][data-reference-type="${expected.referenceType}"]`,
  );
  if (expected.referenceId) {
    rows = page.locator(
      `[data-testid="journal-entry-row"]`
      + `[data-reference-type="${expected.referenceType}"]`
      + `[data-journal-reference="${expected.referenceId}"]`,
    );
  } else {
    rows = rows.filter({ hasText: expected.rowText });
  }
  await expect(rows).toHaveCount(1, { timeout: 60_000 });
  const row = rows.first();
  const journalId = await row.getAttribute('data-journal-id');
  const entryNumber = await row.getAttribute('data-journal-entry-number');
  expect(journalId).toMatch(/^[0-9a-f-]{36}$/i);
  expect(entryNumber).toBeTruthy();

  const toggle = page.locator(
    `[data-testid="journal-expand-toggle"][data-journal-id="${journalId}"]`,
  );
  await expect(toggle).toHaveAttribute('aria-label', 'Expand journal lines');
  await toggle.click();

  const lines = page.locator(
    `[data-testid="journal-lines"][data-journal-id="${journalId}"]`,
  );
  await expect(lines).toBeVisible();
  await expect(lines.locator('[data-testid="journal-line"]')).toHaveCount(expected.lines.length);
  for (const expectedLine of expected.lines) {
    const line = lines.locator(
      `[data-testid="journal-line"]`
      + `[data-direction="${expectedLine.direction}"]`
      + `[data-account-code="${expectedLine.accountCode}"]`,
    );
    await expect(line).toHaveCount(1);
    await expect(line).toHaveAttribute('data-amount', expectedLine.amount);
    await expect(line).toHaveAttribute('data-currency', expectedLine.currency);
    await expect(line).toHaveAttribute('data-base-amount', expectedLine.baseAmount);
    await expect(line).toContainText(expectedLine.accountCode);
    await expect(line).toContainText(`${expectedLine.currency} ${expectedLine.amount}`);
    await expect(line).toContainText(`Base ${expectedLine.baseAmount}`);
    if (expectedLine.fxRateId) {
      await expect(line).toHaveAttribute('data-fx-rate-id', expectedLine.fxRateId);
      await expect(line).toContainText(`FX ${expectedLine.fxRateId}`);
    } else {
      expect(await line.getAttribute('data-fx-rate-id')).toBeNull();
      await expect(line).toContainText('No FX conversion');
    }
  }

  return {
    journalId: journalId!,
    entryNumber: entryNumber!,
  };
}

async function assertVisibleCurrentAgingOracle(
  page: Page,
  report: 'AR' | 'AP',
  expectedTotal: string,
): Promise<void> {
  await page.goto(`${ORIGIN}/app/reports`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByTestId('reporting-currency')).toHaveText('SGD base currency', {
    timeout: 60_000,
  });

  await page.getByRole('tab', { name: new RegExp(`^${report} Aging$`, 'i') }).click();
  const cards = report === 'AR'
    ? page.getByTestId('ar-aging-cards')
    : page.getByTestId('ap-aging-cards');
  const total = report === 'AR'
    ? cards.getByTestId('ar-aging-total')
    : cards.getByTestId('ap-aging-total');
  const unallocated = report === 'AR'
    ? cards.getByTestId('ar-aging-unallocated')
    : cards.getByTestId('ap-aging-unallocated');

  await expect(cards).toBeVisible({ timeout: 60_000 });
  await expect(cards.getByText(`Total open ${report} · SGD base currency`, { exact: true })).toBeVisible();
  await expect(total).toContainText('SGD');
  await expect(total).toContainText(expectedTotal);
  await expect(unallocated).toContainText('SGD');
  await expect(unallocated).toContainText('0.00');
}

async function proveLockedPeriodRejectsJournal(page: Page, period: string): Promise<void> {
  await page.getByRole('button', { name: /new journal entry/i }).click();
  const dialog = page.getByRole('dialog', { name: /post manual journal entry/i });
  const reference = `${TAG} LOCK-NEGATIVE-${period}`;
  await dialog.locator('#jnl-desc').fill(`${reference} must be rejected`);
  await dialog.locator('#jnl-reason').fill(`${reference} verifies the locked-period accounting guard`);
  await dialog.locator('#jnl-date').fill(`${period}-28`);
  await dialog.locator('#jnl-ref').fill(reference);
  await chooseJournalAccount(dialog, 1, '1100');
  await dialog.getByRole('combobox', { name: /direction for line 1/i }).selectOption('DR');
  await dialog.getByRole('textbox', { name: /amount for line 1/i }).fill('0.01');
  await dialog.getByRole('textbox', { name: /note for line 1/i }).fill(reference);
  await chooseJournalAccount(dialog, 2, '3100');
  await dialog.getByRole('combobox', { name: /direction for line 2/i }).selectOption('CR');
  await dialog.getByRole('textbox', { name: /amount for line 2/i }).fill('0.01');
  await dialog.getByRole('textbox', { name: /note for line 2/i }).fill(reference);
  await expect(dialog.getByRole('status', { name: /balanced/i }).or(dialog.getByText(/^balanced$/i))).toBeVisible();
  const rejected = page.waitForResponse(response => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/v1/accounting/journal-entries'
  ));
  await dialog.getByRole('button', { name: /^post journal entry$/i }).click();
  const response = await rejected;
  expect(response.status()).toBe(422);
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('alert')).toContainText(/locked|period_locked/i);
  await dialog.getByRole('button', { name: /^cancel$/i }).click();
}

async function approveInboxTask(page: Page, titleFragment: string): Promise<void> {
  await page.goto(`${ORIGIN}/app/inbox`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByLabel('Loading inbox tasks')).toHaveCount(0, { timeout: 60_000 });
  const card = page.getByRole('article').filter({ hasText: titleFragment }).first();
  await expect(card).toBeVisible();
  const approve = card.getByRole('button', { name: /approve/i }).first();
  await expect(approve).toBeEnabled();
  await approve.click();
  await expect(card).toBeHidden({ timeout: 60_000 });
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function assertVisibleClosePackageOracle(
  section: Locator,
  oracle: MonthlyCloseOracle,
): Promise<void> {
  const heading = section.getByText('Period-end AR/AP', { exact: true });
  await expect(heading).toBeVisible();
  const card = heading.locator('xpath=..');
  await expect(card).toContainText(new RegExp(
    `${escapeRegExp(oracle.ar)}\\s*\\/\\s*[^\\d-]*${escapeRegExp(oracle.ap)}`,
  ));
  await expect(card).toContainText(`SGD base-currency GL · as of ${oracle.asOf}`);
}

async function exerciseCloseChecklist(
  page: Page,
  period: string,
  oracle: MonthlyCloseOracle,
): Promise<void> {
  await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
  const section = page.locator('section[aria-labelledby="close-tasks-title"]');
  const periodInput = section.getByRole('textbox', { name: /close period/i });
  const tasksLoaded = page.waitForResponse(response => (
    response.request().method() === 'GET'
    && new URL(response.url()).pathname === `/api/v1/accounting/periods/${period}/close-tasks`
  ));
  await periodInput.fill(period);
  await periodInput.blur();
  expect((await tasksLoaded).ok()).toBe(true);
  const start = section.getByRole('button', { name: /start checklist/i });
  if (await start.count()) {
    const bootstrap = page.waitForResponse(response => (
      response.request().method() === 'POST'
      && new URL(response.url()).pathname === `/api/v1/accounting/periods/${period}/close-tasks/bootstrap`
    ));
    await start.click();
    expect((await bootstrap).ok()).toBe(true);
  }

  const closePackageButton = section.getByRole('button', { name: /^close package$/i });
  const preReview = page.waitForResponse(response => (
    response.request().method() === 'GET'
    && new URL(response.url()).pathname === `/api/v1/accounting/periods/${period}/close-package`
  ));
  await closePackageButton.click();
  const preReviewResponse = await preReview;
  expect(preReviewResponse.ok()).toBe(true);
  await assertVisibleClosePackageOracle(section, oracle);
  const preReviewPackage = await preReviewResponse.json() as {
    close_status?: { ready_to_lock?: boolean; lock_blockers?: string[] };
  };
  const unexpectedBlockers = (preReviewPackage.close_status?.lock_blockers ?? [])
    .filter(blocker => blocker !== 'close_tasks');
  if (unexpectedBlockers.length) {
    throw new BlockedError(
      `Close package still has non-checklist blocker(s): ${unexpectedBlockers.join(', ')}.`,
    );
  }

  // Each review item is completed only after the close package has visibly
  // reconciled the ledger/subledgers. The period_lock item represents the
  // subsequent action and is completed by the successful lock endpoint.
  const reviewTasks = [
    'Reconcile AR/AP subledgers',
    'Review accruals',
    'Review deferred revenue release',
    'Review recurring journals',
    'Review trial balance and close package',
  ];
  for (const title of reviewTasks) {
    const taskTitle = section.getByText(title, { exact: true });
    await expect(taskTitle).toBeVisible();
    const taskRow = taskTitle.locator('xpath=ancestor::div[button[normalize-space(.)="Done"]][1]');
    const done = taskRow.getByRole('button', { name: /^done$/i });
    if (!(await done.count())) continue;
    const updated = page.waitForResponse(response => (
      response.request().method() === 'PATCH'
      && new URL(response.url()).pathname.startsWith(`/api/v1/accounting/periods/${period}/close-tasks/`)
    ));
    await done.click();
    expect((await updated).ok()).toBe(true);
    await expect(done).toHaveCount(0);
  }

  const postReview = page.waitForResponse(response => (
    response.request().method() === 'GET'
    && new URL(response.url()).pathname === `/api/v1/accounting/periods/${period}/close-package`
  ));
  await closePackageButton.click();
  const postReviewResponse = await postReview;
  expect(postReviewResponse.ok()).toBe(true);
  const postReviewPackage = await postReviewResponse.json() as {
    close_status?: { ready_to_lock?: boolean; lock_blockers?: string[] };
  };
  expect(postReviewPackage.close_status?.ready_to_lock).toBe(true);
  expect(postReviewPackage.close_status?.lock_blockers ?? []).toEqual([]);
}

async function setStatementRange(page: Page, from: string, to: string): Promise<void> {
  const active = page.locator('mat-tab-body.mat-mdc-tab-body-active');
  const start = active.getByLabel(/statement period start/i);
  const end = active.getByLabel(/statement period end/i);
  // Clear/blur both controls first. This guarantees the final end blur emits
  // one valid range change even when the requested range equals the values
  // copied into a newly selected report tab.
  await start.fill('');
  await start.blur();
  await end.fill('');
  await end.blur();
  await start.fill(from);
  await start.blur();
  await end.fill(to);
  const expectedResponses = [
    `/api/v1/reports/balance-sheet?as_of_period=${to}`,
    `/api/v1/reports/retained-earnings-roll-forward?period=${to}`,
    `/api/v1/reports/income-statement?period_start=${from}&period_end=${to}`,
    `/api/v1/reports/cash-flow?period_start=${from}&period_end=${to}`,
    `/api/v1/reports/statutory-pack?period_start=${from}&period_end=${to}`,
  ].map(expected => page.waitForResponse(response => `${new URL(response.url()).pathname}${new URL(response.url()).search}` === expected));
  await end.blur();
  for (const response of await Promise.all(expectedResponses)) expect(response.ok()).toBe(true);
  await expect(start).toHaveValue(from);
  await expect(end).toHaveValue(to);
}

async function verifyMonthlyCloseOracle(
  page: Page,
  oracle: MonthlyCloseOracle,
): Promise<void> {
  await page.goto(`${ORIGIN}/app/reports`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('tab', { name: /^income statement$/i }).click();
  await setStatementRange(page, oracle.month, oracle.month);
  await expect(page.locator('mat-tab-body.mat-mdc-tab-body-active')).toContainText(oracle.income);

  await page.getByRole('tab', { name: /^balance sheet$/i }).click();
  await setStatementRange(page, oracle.month, oracle.month);
  const balanceSheet = page.locator('mat-tab-body.mat-mdc-tab-body-active');
  await expect(balanceSheet).toContainText(oracle.cash);
  await expect(balanceSheet).toContainText(oracle.ar);
  await expect(balanceSheet).toContainText(oracle.ap);

  await page.getByRole('tab', { name: /^cash flow$/i }).click();
  await setStatementRange(page, oracle.month, oracle.month);
  await expect(page.locator('mat-tab-body.mat-mdc-tab-body-active')).toContainText(oracle.cash);
}

test.skip(
  process.env.AETHOS_PRODUCTION_UI_CONFIG !== CONFIG_MARKER,
  'Retained production journey can run only with playwright.production-ui.config.ts.',
);

test('Ishantech — one recorded production browser session', async ({ page, context }) => {
  test.setTimeout(4 * 60 * 60 * 1000);
  const credentials = loadCredentials();
  if (credentials.tenant_id) {
    throw new Error(
      'The credential manifest already belongs to a retained tenant. '
      + 'Use a new run ID and fresh 22-account manifest so this tenant keeps exactly one recorded browser session.',
    );
  }
  const records = loadCheckpointRecords();
  const journey = new Journey(page, context, credentials, records);

  try {
    await journey.step('PF-01', 'Exact production origin and public liveness', async () => {
      const response = await page.goto(`${ORIGIN}/health`, { waitUntil: 'domcontentloaded' });
      expect(response?.status()).toBe(200);
      expect(new URL(page.url()).origin).toBe(ORIGIN);
      const health = JSON.parse(await page.locator('body').innerText()) as { status?: string; build_sha?: string };
      expect(health.status).toBe('ok');
      expect(health.build_sha).toBe(EXPECTED_SHA);
    }, { fatal: true });

    await journey.step('PF-02', 'Reviewed deployment, worker queue, and database readiness', async () => {
      await page.goto(`${ORIGIN}/health/ready`, { waitUntil: 'domcontentloaded' });
      const readiness = JSON.parse(await page.locator('body').innerText()) as {
        status?: string;
        build_sha?: string;
        checks?: {
          db?: { status?: string };
          queue?: { status?: string; configured?: boolean; required?: boolean };
          billing?: { status?: string; configured?: boolean; mode?: string };
        };
      };
      expect(readiness.status).toBe('ready');
      expect(readiness.build_sha).toBe(EXPECTED_SHA);
      expect(readiness.checks?.db?.status).toBe('ok');
      expect(readiness.checks?.queue).toMatchObject({ status: 'ok', configured: true, required: true });
    }, { fatal: true });

    await journey.step('PF-03', 'Stripe test-mode proof before tenant creation', async () => {
      await page.goto(`${ORIGIN}/health/signup-ready`, { waitUntil: 'domcontentloaded' });
      const readiness = JSON.parse(await page.locator('body').innerText()) as {
        status?: string;
        build_sha?: string;
        checks?: {
          billing?: {
            status?: string;
            configured?: boolean;
            mode?: string;
            account_reachable?: boolean;
            prices_checked?: number;
          };
        };
      };
      expect(readiness.status).toBe('ready');
      expect(readiness.build_sha).toBe(EXPECTED_SHA);
      expect(readiness.checks?.billing).toEqual({
        status: 'ok',
        configured: true,
        mode: 'test',
        account_reachable: true,
        prices_checked: 30,
      });
      await page.goto(`${ORIGIN}/signup`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByRole('heading', { name: /create your firm/i })).toBeVisible();
      expect(new URL(page.url()).origin).toBe(ORIGIN);
    }, { fatal: true });

    await journey.step('PF-04', 'Clean single BrowserContext baseline', async () => {
      expect(context.pages()).toHaveLength(1);
      const storage = await page.evaluate(() => ({
        token: localStorage.getItem('aethos_token'),
        tenant: localStorage.getItem('aethos_tenant_id'),
      }));
      expect(storage).toEqual({ token: null, tenant: null });
    }, { fatal: true });

    const owner = account(credentials, 'tenant_owner');
    await journey.step('SU-01', 'Register Ishantech owner and tenant through the public UI', async () => {
      if (credentials.tenant_id) {
        await login(page, owner);
      } else {
        await signupIshantech(page, owner, tenantId => {
          credentials.tenant_id = tenantId;
          credentials.created_at = new Date().toISOString();
          owner.status = 'created';
          saveCredentials(credentials);
        });
      }
    }, { fatal: true });

    await journey.step('SU-02', 'Growth trial and test card remain active after refresh', async () => {
      await page.goto(`${ORIGIN}/app/profile`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByText(DATA.company, { exact: true })).toBeVisible();
      await expect(page.getByText('Singapore', { exact: true })).toBeVisible();
      await expect(page.getByText('Growth', { exact: true })).toBeVisible();
      await expect(page.getByText(/trialing|active/i).first()).toBeVisible();
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.getByText(DATA.company, { exact: true })).toBeVisible();
    }, { fatal: true });

    await journey.step('SU-03', 'Owner rotates the signup password in the visible profile', async () => {
      if (owner.status === 'active' && !owner.must_change_password) {
        await page.goto(`${ORIGIN}/app/profile`, { waitUntil: 'domcontentloaded' });
        await expect(page.getByText(DATA.company, { exact: true })).toBeVisible();
        return;
      }
      const next = finalPassword();
      owner.pending_password = next;
      owner.status = 'password_rotation_pending';
      saveCredentials(credentials);
      await page.goto(`${ORIGIN}/app/profile`, { waitUntil: 'domcontentloaded' });
      await rotatePassword(page, owner.password, next, false);
      owner.password = next;
      owner.pending_password = null;
      owner.must_change_password = false;
      owner.status = 'active';
      saveCredentials(credentials);
    }, { fatal: true });

    await journey.step('SU-04', 'Owner can sign out and sign back in with the retained credential', async () => {
      await logout(page);
      await login(page, owner, /\/app\/copilot/);
      await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible();
    }, { fatal: true });

    await journey.step('RB-00', 'Live assignable role catalog is exactly the reviewed 22 roles', async () => {
      await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
      const users = page.locator('app-tenant-users');
      await expect(users.getByRole('heading', { name: /tenant users/i })).toBeVisible();
      await expect(users.getByLabel('Loading tenant users')).toHaveCount(0, { timeout: 60_000 });
      const inviteForm = users.locator('form').filter({ hasText: /invite user/i });
      const actual = (await optionValues(inviteForm.getByLabel('Role', { exact: true }))).sort();
      expect(actual).toEqual([...EXPECTED_ROLE_CODES].sort());

      const catalog = page.locator('app-security-roles');
      await expect(catalog.getByText(/security roles/i).first()).toBeVisible();
      await expect(catalog.getByLabel('Loading security roles')).toHaveCount(0, { timeout: 60_000 });
    }, { fatal: true });

    const erpInvitees = credentials.accounts.filter(item => (
      item.code !== 'tenant_owner' && item.code !== 'timesheet_employee'
    ));
    for (const target of erpInvitees) {
      await journey.step(`RB-01-${target.code}`, `Create ${target.label} through Tenant Users`, async () => {
        await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
        await inviteTenantUser(page, target);
        if (target.status !== 'active') target.status = 'invited';
        saveCredentials(credentials);
      });
    }

    const timesheetAccount = account(credentials, 'timesheet_employee');
    await journey.step('RB-01-timesheet_employee', 'Create linked Timesheet Employee through People portal invite', async () => {
      await page.goto(`${ORIGIN}/app/people`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByRole('heading', { name: /^people$/i })).toBeVisible();
      await expect(page.getByLabel('Loading employees')).toHaveCount(0, { timeout: 60_000 });

      let employeeRow = page.locator('app-people-list .space-y-2 > div').filter({ hasText: timesheetAccount.email });
      if (!(await employeeRow.count())) {
        await page.getByRole('button', { name: /add new employee/i }).click();
        const dialog = page.getByRole('dialog', { name: /new employee/i });
        await dialog.locator('[formcontrolname="first_name"]').fill(DATA.employee.first);
        await dialog.locator('[formcontrolname="last_name"]').fill(DATA.employee.last);
        await dialog.locator('[formcontrolname="email"]').fill(timesheetAccount.email);
        await dialog.locator('[formcontrolname="title"]').fill(DATA.employee.title);
        await dialog.locator('[formcontrolname="department"]').fill('Advisory');
        await dialog.locator('[formcontrolname="employment_type"]').selectOption('full_time');
        await dialog.locator('#practice-area').selectOption('advisory');
        await dialog.locator('#seniority').selectOption('associate');
        await dialog.locator('[formcontrolname="default_bill_rate"]').fill('300');
        await dialog.locator('[formcontrolname="default_bill_rate_currency"]').fill('SGD');
        await dialog.locator('[formcontrolname="cost_rate"]').fill('120');
        await dialog.locator('[formcontrolname="target_billable_utilization_pct"]').fill('75');
        await dialog.getByRole('button', { name: /^create employee$/i }).click();
        await expect(dialog).toBeHidden({ timeout: 60_000 });
        employeeRow = page.locator('app-people-list .space-y-2 > div').filter({ hasText: timesheetAccount.email });
        await expect(employeeRow).toBeVisible();
      }

      if (!(await employeeRow.getByText(/portal/i).count())) {
        // The modal contains a recovery token and one-time password. This CSS
        // keeps those values out of the shareable video; raw trace stays private.
        await page.addStyleTag({ content: 'app-people-list input[readonly]{color:transparent!important;text-shadow:0 0 8px #111827!important;}' });
        page.once('dialog', dialog => dialog.accept());
        await employeeRow.getByRole('button', { name: /invite to timesheet portal/i }).click();
        const inviteDialog = page.getByRole('dialog', { name: /portal access granted/i });
        await expect(inviteDialog).toBeVisible({ timeout: 60_000 });
        const passwordLabel = inviteDialog.getByText(/temporary password \(shown once\)/i);
        const temporaryPassword = await passwordLabel.locator('..').locator('input[readonly]').inputValue();
        expect(temporaryPassword.length).toBeGreaterThanOrEqual(12);
        timesheetAccount.password = temporaryPassword;
        await inviteDialog.getByRole('button', { name: /^done$/i }).click();
      }
      if (timesheetAccount.status !== 'active') timesheetAccount.status = 'invited';
      saveCredentials(credentials);
    });

    for (const target of erpInvitees) {
      await journey.step(`RB-02-${target.code}`, `${target.label} first login, forced password rotation, and allowed surface`, async () => {
        if (page.url().includes('/app/')) await logout(page);
        if (target.status === 'active' && !target.must_change_password) {
          await login(page, target, /\/app\/copilot/);
        } else {
          await login(page, target, /\/app\/profile/);
          const next = finalPassword();
          target.pending_password = next;
          target.status = 'password_rotation_pending';
          saveCredentials(credentials);
          await rotatePassword(page, target.password, next);
          target.password = next;
          target.pending_password = null;
          target.must_change_password = false;
          target.status = 'active';
          saveCredentials(credentials);
        }

        const surface = ROLE_SURFACES[target.code as Exclude<RoleCode, 'tenant_owner' | 'timesheet_employee'>];
        await page.goto(`${ORIGIN}${surface.route}`, { waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('heading', { name: surface.anchor }).first()).toBeVisible({ timeout: 60_000 });
      });

      await journey.step(`RB-04-${target.code}`, `${target.label} visible forbidden-action boundary`, async () => {
        if (target.legacy_role === 'owner' || target.legacy_role === 'admin') {
          await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
          const roleSelect = page.locator('app-tenant-users form').filter({ hasText: /invite user/i }).getByLabel('Role', { exact: true });
          const values = await optionValues(roleSelect);
          expect(values).not.toContain('platform_admin');
        } else {
          await journey.expectHttp(
            [{ status: 403, url: /\/api\/v1\// }],
            async () => {
              await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
              const createUser = page.locator('app-tenant-users').getByRole('button', { name: /^create user$/i });
              await expect(createUser).toBeDisabled();
              await expect(page.locator('app-tenant-users').getByRole('status')).toContainText(/require admin or owner/i);
              await page.waitForLoadState('networkidle', { timeout: 60_000 });
            },
          );
        }
      });
    }

    await journey.step('RB-02A-timesheet_employee-firewall', 'Timesheet Employee main ERP login redirects to the Timesheet portal', async () => {
      if (page.url().includes('/app/')) await logout(page);
      await page.goto(`${ORIGIN}/login`, { waitUntil: 'domcontentloaded' });
      await page.locator('#email').fill(timesheetAccount.email);
      await page.locator('#password').fill(timesheetAccount.password);
      await page.getByRole('button', { name: /^sign in$/i }).click();
      await page.waitForURL(`${TIMESHEET_ORIGIN}/login`, { timeout: 60_000 });
      expect(new URL(page.url()).origin).toBe(TIMESHEET_ORIGIN);
      expect(new URL(page.url()).pathname).toBe('/login');
    });

    await journey.step('RB-02-timesheet_employee', 'Timesheet Employee first login, forced password rotation, and sign out', async () => {
      await page.goto(`${TIMESHEET_ORIGIN}/login`, { waitUntil: 'domcontentloaded' });
      await page.locator('[formcontrolname="email"]').fill(timesheetAccount.email);
      await page.locator('[formcontrolname="password"]').fill(timesheetAccount.password);
      await page.getByRole('button', { name: /^sign in$/i }).click();
      if (timesheetAccount.status === 'active' && !timesheetAccount.must_change_password) {
        await page.waitForURL(`${TIMESHEET_ORIGIN}/timesheet`, { timeout: 60_000 });
      } else {
        await page.waitForURL(`${TIMESHEET_ORIGIN}/change-password`, { timeout: 60_000 });
        const next = finalPassword();
        timesheetAccount.pending_password = next;
        timesheetAccount.status = 'password_rotation_pending';
        saveCredentials(credentials);
        await page.locator('#ts-current-password').fill(timesheetAccount.password);
        await page.locator('#ts-new-password').fill(next);
        await page.locator('#ts-confirm-password').fill(next);
        await page.getByRole('button', { name: /^update password$/i }).click();
        await page.waitForURL(`${TIMESHEET_ORIGIN}/timesheet`, { timeout: 60_000 });
        timesheetAccount.password = next;
        timesheetAccount.pending_password = null;
        timesheetAccount.must_change_password = false;
        timesheetAccount.status = 'active';
        saveCredentials(credentials);
      }
      await expect(page.getByRole('heading', { name: /my week/i })).toBeVisible();
      await page.getByRole('button', { name: /sign out/i }).click();
      await page.waitForURL(/\/login$/, { timeout: 30_000 });
    });

    await journey.step('RB-07', 'Platform Administrator absence is recorded, not simulated', async () => {
      await page.goto(`${ORIGIN}/login`, { waitUntil: 'domcontentloaded' });
      await login(page, owner, /\/app\/copilot/);
      await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
      const text = await page.locator('body').innerText();
      expect(text.toLowerCase()).not.toContain('platform administrator');
      journey.block('No platform-admin role, lifecycle, or control-plane UI exists in the deployed product.');
    });

    await journey.step('MD-01A', 'Signup-derived company, country, base currency, and tax jurisdiction persist', async () => {
      await switchMainRole(page, credentials, 'tenant_owner');
      await page.goto(`${ORIGIN}/app/profile`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByText(DATA.company, { exact: true })).toBeVisible();
      await expect(page.getByText('Singapore', { exact: true })).toBeVisible();
      await expect(page.getByText('Growth', { exact: true })).toBeVisible();
    });

    await journey.step('MD-01B', 'Legal entity, fiscal year, timezone, invoice prefix, and payment terms configuration', async () => {
      await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
      const body = (await page.locator('body').innerText()).toLowerCase();
      const requiredControls = ['legal name', 'fiscal year', 'invoice prefix', 'payment terms'];
      const missing = requiredControls.filter(label => !body.includes(label));
      if (missing.length) journey.block(`No visible tenant configuration controls for: ${missing.join(', ')}.`);
    });

    await journey.step('MD-02A', 'Create Singapore GST and zero-rated tax treatments', async () => {
      await switchMainRole(page, credentials, 'tenant_admin');
      await ensureTaxRate(page, `${TAG} Singapore GST 9%`, '9');
      await ensureTaxRate(page, `${TAG} Zero-rated 0%`, '0');
    });

    for (const service of DATA.services) {
      await journey.step(`MD-02-${service.code}`, `Create service ${service.name}`, async () => {
        await ensureService(page, service);
      });
    }

    await journey.step('MD-03A', 'Create two deterministic customers', async () => {
      await switchMainRole(page, credentials, 'engagement_manager');
      for (const customer of DATA.customers) await ensureContact(page, customer, 'customer');
    });

    await journey.step('MD-03B', 'Create four deterministic vendors', async () => {
      for (const vendor of DATA.vendors) await ensureContact(page, vendor, 'vendor');
    });

    for (const [index, vendor] of DATA.vendors.entries()) {
      await journey.step(`MD-03-vendor-${index + 1}`, `Verify fictional vendor controls for ${vendor}`, async () => {
        await switchMainRole(page, credentials, 'tenant_admin');
        await ensureVendorControls(page, vendor, `vendor-${index + 1}-${TAG.toLowerCase()}@ishirock.tech`);
      });
    }

    await journey.step('MD-04', 'Timesheet employee master and login are linked', async () => {
      await switchMainRole(page, credentials, 'resource_manager');
      await page.goto(`${ORIGIN}/app/people`, { waitUntil: 'domcontentloaded' });
      const row = page.locator('app-people-list .space-y-2 > div').filter({ hasText: timesheetAccount.email });
      await expect(row).toContainText(`${DATA.employee.first} ${DATA.employee.last}`);
      await expect(row).toContainText(/portal/i);
    });

    await journey.step('MD-05A', 'Create four deterministic engagements with all billing models', async () => {
      await switchMainRole(page, credentials, 'engagement_manager');
      for (const engagement of DATA.engagements) await ensureEngagement(page, engagement);
    });

    await journey.step('MD-05B', 'Create three deterministic projects', async () => {
      for (const project of DATA.projects) await ensureProject(page, project);
    });

    await journey.step('MD-05C', 'Assign the Timesheet Employee to the T&M project', async () => {
      await assignEmployeeToProject(
        page,
        `${TAG} Merlion Transformation`,
        `${DATA.employee.first} ${DATA.employee.last}`,
      );
    });

    await journey.step('MD-07A', 'Required chart-of-accounts mapping is visible', async () => {
      await switchMainRole(page, credentials, 'finance_controller');
      await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
      const accountsLoaded = page.waitForResponse(response => (
        response.request().method() === 'GET'
        && new URL(response.url()).pathname === '/api/v1/accounts'
      ));
      await page.getByRole('button', { name: /new journal entry/i }).click();
      expect((await accountsLoaded).ok()).toBe(true);
      const dialog = page.getByRole('dialog', { name: /post manual journal entry/i });
      const accountInput = dialog.getByRole('textbox', { name: /account for line 1/i });
      const requiredAccounts = [
        'Bank', 'Accounts Receivable', 'Accounts Payable', 'Revenue', 'Expenses',
        'Prepaid Expenses', 'Input Tax Recoverable', 'Sales Tax Payable',
        'Payroll Accrual', 'Accumulated Depreciation', 'Depreciation Expense',
      ];
      const missing: string[] = [];
      for (const name of requiredAccounts) {
        await accountInput.fill(name);
        const suggestions = dialog.getByRole('listbox', { name: /account suggestions for line 1/i });
        if (!(await suggestions.getByRole('option', { name: new RegExp(name, 'i') }).count())) missing.push(name);
        await accountInput.fill('');
      }
      await dialog.getByRole('button', { name: /close|cancel/i }).first().click();
      if (missing.length) journey.block(`Standard tenant chart lacks required accounts: ${missing.join(', ')}.`);
    });

    await journey.step('MD-07B', 'Frozen historical and receipt-date USD/SGD provenance is visible in the UI', async () => {
      await switchMainRole(page, credentials, 'finance_controller');
      await page.goto(`${ORIGIN}/app/settings`, { waitUntil: 'domcontentloaded' });
      const approval = await lookupFxProvenance(page, '2026-05-20');
      expect(approval.from_currency).toBe('USD');
      expect(approval.to_currency).toBe('SGD');
      expect(approval.staleness_days).toBeLessThanOrEqual(3);
      expect(approval.fx_rate_id).toMatch(/^[0-9a-f-]{36}$/i);
      records.FX_APPROVAL_RATE = approval.rate;
      records.FX_APPROVAL_RATE_ID = approval.fx_rate_id ?? '';
      records.FX_APPROVAL_MATCHED_DATE = approval.rate_date;
      records.FX_APPROVAL_SOURCE = approval.source;

      const payment = await lookupFxProvenance(page, '2026-07-12');
      expect(payment.rate_date).toBe('2026-07-12');
      expect(payment.staleness_days).toBe(0);
      expect(payment.fx_rate_id).toMatch(/^[0-9a-f-]{36}$/i);
      records.FX_PAYMENT_RATE = payment.rate;
      records.FX_PAYMENT_RATE_ID = payment.fx_rate_id ?? '';
      records.FX_PAYMENT_MATCHED_DATE = payment.rate_date;
      records.FX_PAYMENT_SOURCE = payment.source;

      records.TX08_FOREIGN_AMOUNT_USD = foreignAmountForTargetBase('6750.00', approval.rate);
      records.TX16_FOREIGN_AMOUNT_USD = foreignAmountForTargetBase('1350.00', approval.rate);
      const paymentBase = convertForeignToBase(records.TX08_FOREIGN_AMOUNT_USD, payment.rate);
      const fxDelta = paymentBase - moneyCents('6750.00');
      if (fxDelta === 0n) journey.block('Approval-date and receipt-date rates produce no realised FX edge case.');
      records.TX12_PAYMENT_BASE_SGD = formatCents(paymentBase);
      records.TX12_FX_DELTA_SGD = formatCents(fxDelta);
      records.TX12_FX_DIRECTION = fxDelta > 0n ? 'gain' : 'loss';
    });

    await journey.step('MD-07C', 'Required deterministic ledger accounts are visible to the journal composer', async () => {
      await switchMainRole(page, credentials, 'finance_controller');
      await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
      const accountsLoaded = page.waitForResponse(response => (
        response.request().method() === 'GET'
        && new URL(response.url()).pathname === '/api/v1/accounts'
      ));
      await page.getByRole('button', { name: /new journal entry/i }).click();
      expect((await accountsLoaded).ok()).toBe(true);
      const dialog = page.getByRole('dialog', { name: /post manual journal entry/i });
      const input = dialog.getByRole('textbox', { name: 'Account for line 1', exact: true });
      const suggestions = dialog.getByRole('listbox', { name: 'Account suggestions for line 1', exact: true });
      const required = [
        'Owner Capital',
        'Payroll Expense',
        'Payroll Accrual',
        'Equipment',
        'Accumulated Depreciation',
        'Depreciation Expense',
        'Software Expense',
      ];
      const missing: string[] = [];
      for (const name of required) {
        await input.fill(name);
        if (!(await suggestions.getByRole('option').filter({ hasText: name }).count())) missing.push(name);
      }
      await dialog.getByRole('button', { name: /^cancel$/i }).click();
      if (missing.length) journey.block(`Required chart accounts are absent from the visible journal composer: ${missing.join(', ')}.`);
    });

    await journey.step('LEDGER-GATE', 'Accounting prerequisites pass before any posting action', async () => {
      journey.require(['MD-07B', 'MD-07C']);
    });

    await journey.step('O2C-02A', 'Billing Specialist drafts April GST retainer invoice TX-02', async () => {
      await switchMainRole(page, credentials, 'billing_specialist');
      records.TX02 = await draftManualInvoice(page, {
        engagement: `${TAG} Merlion Finance Operations`,
        client: `${TAG} Merlion Health Pte. Ltd.`,
        issue: '2026-04-05',
        due: '2026-05-05',
        description: `${TAG} TX-02 April monthly finance operations`,
        amount: '12000',
        taxRateName: `${TAG} Singapore GST 9%`,
      });
      expect(records.TX02).toMatch(/^INV-/);
      records.TX02_ID = await captureInvoiceId(page, records.TX02);
    });

    await journey.step('O2C-02B', 'Finance Approver is denied direct invoice posting by catalog policy', async () => {
      journey.require(['O2C-02A']);
      await switchMainRole(page, credentials, 'finance_approver');
      await page.goto(`${ORIGIN}/app/invoices`, { waitUntil: 'domcontentloaded' });
      const row = page.locator('table[aria-label="Invoices"] tbody tr').filter({ hasText: records.TX02 });
      const approve = row.getByRole('button', { name: `Approve invoice ${records.TX02}`, exact: true });
      await expect(approve).toBeDisabled();
      await expect(row).toContainText(/draft/i);
    });

    await journey.step('O2C-02C', 'Billing Specialist posts and sends TX-02 with catalog privileges', async () => {
      journey.require(['O2C-02A', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'billing_specialist');
      await approveAndSendInvoice(page, records.TX02);
    });

    await journey.step('O2C-03A', 'AR Manager records full April receipt TX-03 with catalog privileges', async () => {
      journey.require(['O2C-02C']);
      await switchMainRole(page, credentials, 'ar_manager');
      const state = await recordInvoicePayment(page, records.TX02, '13080', '2026-04-25', 'TX-03 full receipt');
      expect(state).toContain('paid');
    });

    await journey.step('O2C-03B', 'Finance Controller verifies the TX-03 receipt journal and paid state', async () => {
      journey.require(['O2C-03A']);
      await switchMainRole(page, credentials, 'finance_controller');
      await page.goto(`${ORIGIN}/app/invoices`, { waitUntil: 'domcontentloaded' });
      const row = page.locator('table[aria-label="Invoices"] tbody tr').filter({ hasText: records.TX02 });
      await expect(row).toContainText(/paid/i);
      await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('table').filter({ hasText: `Payment received for invoice ${records.TX02}` }))
        .toBeVisible({ timeout: 60_000 });
    });

    await journey.step('O2C-04A', 'Timesheet Employee enters and submits 60 May hours in the portal', async () => {
      if (page.url().includes('/app/')) await logout(page);
      await page.goto(`${TIMESHEET_ORIGIN}/login`, { waitUntil: 'domcontentloaded' });
      await page.locator('[formcontrolname="email"]').fill(timesheetAccount.email);
      await page.locator('[formcontrolname="password"]').fill(timesheetAccount.password);
      await page.getByRole('button', { name: /^sign in$/i }).click();
      await page.waitForURL(`${TIMESHEET_ORIGIN}/timesheet`, { timeout: 60_000 });
      await openTimesheetWeek(page, '2026-05-04');
      await enterAndSubmitWeek(page, `${TAG} Merlion Transformation`, [8, 8, 8, 8, 8]);
      await nextTimesheetWeek(page);
      await enterAndSubmitWeek(page, `${TAG} Merlion Transformation`, [4, 4, 4, 4, 4]);
      await page.getByRole('button', { name: /sign out/i }).click();
      await page.waitForURL(/\/login$/, { timeout: 30_000 });
    });

    await journey.step('O2C-04B', 'Resource Manager approves both submitted May weeks', async () => {
      journey.require(['O2C-04A']);
      await switchMainRole(page, credentials, 'resource_manager');
      await page.goto(`${ORIGIN}/app/approvals`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByLabel('Loading')).toHaveCount(0, { timeout: 60_000 });
      for (const week of ['2026-05-04', '2026-05-11']) {
        const group = page.locator('app-approvals .bg-surface.border').filter({
          hasText: `${DATA.employee.first} ${DATA.employee.last}`,
        }).filter({ hasText: `Week of ${week}` });
        await expect(group).toBeVisible();
        await group.getByRole('button', { name: /^approve$/i }).click();
        await expect(group).toBeHidden({ timeout: 60_000 });
      }
    });

    await journey.step('O2C-04C', 'Billing Specialist creates May T&M invoice TX-06 from approved time', async () => {
      journey.require(['O2C-04B']);
      await switchMainRole(page, credentials, 'billing_specialist');
      records.TX06 = await draftManualInvoice(page, {
        engagement: `${TAG} Merlion Transformation Advisory`,
        client: `${TAG} Merlion Health Pte. Ltd.`,
        issue: '2026-05-31',
        due: '2026-06-30',
        description: `${TAG} TX-06 transformation delivery`,
        amount: '18000',
        taxRateName: `${TAG} Singapore GST 9%`,
        selectTime: true,
      });
      expect(records.TX06).toMatch(/^INV-/);
      records.TX06_ID = await captureInvoiceId(page, records.TX06);
    });

    await journey.step('O2C-04D', 'Finance Controller approves and sends TX-06', async () => {
      journey.require(['O2C-04C', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'finance_controller');
      await approveAndSendInvoice(page, records.TX06);
    });

    await journey.step('O2C-05', 'Record partial receipt TX-07 and preserve remaining AR 9,620', async () => {
      journey.require(['O2C-04D', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'finance_controller');
      const state = await recordInvoicePayment(page, records.TX06, '10000', '2026-05-31', 'TX-07 partial receipt');
      expect(state).toContain('sent');
      expect(state).not.toContain('paid');
      records.TX07_STATUS = 'receipt_recorded; invoice_sent; remaining_SGD_9620';
    });

    await journey.step('O2C-06A', 'Billing Specialist creates TX-08 at a frozen SGD 6,750 historical base', async () => {
      journey.require(['MD-07B']);
      await switchMainRole(page, credentials, 'billing_specialist');
      records.TX08 = await draftManualInvoice(page, {
        engagement: `${TAG} Pacific Vector Advisory`,
        client: `${TAG} Pacific Vector LLC`,
        issue: '2026-05-20',
        due: '2026-06-19',
        description: `${TAG} TX-08 Pacific Vector advisory`,
        amount: records.TX08_FOREIGN_AMOUNT_USD,
      });
      expect(records.TX08).toMatch(/^INV-/);
      records.TX08_ID = await captureInvoiceId(page, records.TX08);
    });

    await journey.step('O2C-06B', 'Finance Controller approves and sends USD TX-08', async () => {
      journey.require(['O2C-06A', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'finance_controller');
      await approveAndSendInvoice(page, records.TX08);
      const posting = await assertVisibleJournalPosting(page, {
        referenceType: 'invoice',
        referenceId: records.TX08_ID,
        lines: [
          {
            direction: 'DR',
            accountCode: '1200',
            amount: records.TX08_FOREIGN_AMOUNT_USD,
            currency: 'USD',
            baseAmount: '6750.00',
            fxRateId: records.FX_APPROVAL_RATE_ID,
          },
          {
            direction: 'CR',
            accountCode: '4000',
            amount: records.TX08_FOREIGN_AMOUNT_USD,
            currency: 'USD',
            baseAmount: '6750.00',
            fxRateId: records.FX_APPROVAL_RATE_ID,
          },
        ],
      });
      records.TX08_JOURNAL_ID = posting.journalId;
      records.TX08_JOURNAL_ENTRY_NUMBER = posting.entryNumber;
    });

    await journey.step('O2C-07', 'Post remaining receipt TX-11 against partially paid TX-06', async () => {
      journey.require(['O2C-05', 'O2C-04D', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'finance_controller');
      const state = await recordInvoicePayment(page, records.TX06, '9620', '2026-06-15', 'TX-11 remaining receipt');
      expect(state).toContain('paid');
      records.TX11_STATUS = 'receipt_recorded; invoice_paid; remaining_SGD_0';
    });

    await journey.step('O2C-08', 'Settle USD TX-08 on July 12 and post the captured realised FX delta', async () => {
      journey.require(['MD-07B', 'O2C-06B']);
      await switchMainRole(page, credentials, 'finance_controller');
      const state = await recordInvoicePayment(
        page,
        records.TX08,
        records.TX08_FOREIGN_AMOUNT_USD,
        '2026-07-12',
        `TX-12 USD receipt; expected base SGD ${records.TX12_PAYMENT_BASE_SGD}`,
      );
      expect(state).toContain('paid');
      const paymentPosting = await assertVisibleJournalPosting(page, {
        referenceType: 'payment',
        referenceId: records.TX08_ID,
        lines: [
          {
            direction: 'DR',
            accountCode: '1100',
            amount: records.TX08_FOREIGN_AMOUNT_USD,
            currency: 'USD',
            baseAmount: records.TX12_PAYMENT_BASE_SGD,
            fxRateId: records.FX_PAYMENT_RATE_ID,
          },
          {
            direction: 'CR',
            accountCode: '1200',
            amount: records.TX08_FOREIGN_AMOUNT_USD,
            currency: 'USD',
            baseAmount: records.TX12_PAYMENT_BASE_SGD,
            fxRateId: records.FX_PAYMENT_RATE_ID,
          },
        ],
      });
      records.TX12_PAYMENT_JOURNAL_ID = paymentPosting.journalId;
      records.TX12_PAYMENT_JOURNAL_ENTRY_NUMBER = paymentPosting.entryNumber;

      const fxAmount = records.TX12_FX_DELTA_SGD.replace(/^-/, '');
      const fxLines: ExpectedJournalLine[] = records.TX12_FX_DIRECTION === 'gain'
        ? [
            { direction: 'DR', accountCode: '1200', amount: fxAmount, currency: 'SGD', baseAmount: fxAmount, fxRateId: null },
            { direction: 'CR', accountCode: '7900', amount: fxAmount, currency: 'SGD', baseAmount: fxAmount, fxRateId: null },
          ]
        : [
            { direction: 'DR', accountCode: '7900', amount: fxAmount, currency: 'SGD', baseAmount: fxAmount, fxRateId: null },
            { direction: 'CR', accountCode: '1200', amount: fxAmount, currency: 'SGD', baseAmount: fxAmount, fxRateId: null },
          ];
      const fxPosting = await assertVisibleJournalPosting(page, {
        referenceType: 'fx_gain_loss',
        referenceId: records.TX08_ID,
        lines: fxLines,
      });
      records.TX12_FX_JOURNAL_ID = fxPosting.journalId;
      records.TX12_FX_JOURNAL_ENTRY_NUMBER = fxPosting.entryNumber;
    });

    await journey.step('O2C-09A', 'Billing Specialist creates June milestone invoice TX-13', async () => {
      await switchMainRole(page, credentials, 'billing_specialist');
      records.TX13 = await draftManualInvoice(page, {
        engagement: `${TAG} Merlion Implementation`,
        client: `${TAG} Merlion Health Pte. Ltd.`,
        issue: '2026-06-10',
        due: '2026-07-10',
        description: `${TAG} TX-13 implementation milestone`,
        amount: '25000',
        taxRateName: `${TAG} Singapore GST 9%`,
      });
      expect(records.TX13).toMatch(/^INV-/);
      records.TX13_ID = await captureInvoiceId(page, records.TX13);
    });

    await journey.step('O2C-09B', 'Finance Controller approves and sends TX-13 while leaving it unpaid', async () => {
      journey.require(['O2C-09A', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'finance_controller');
      await approveAndSendInvoice(page, records.TX13);
      const row = page.locator('table[aria-label="Invoices"] tbody tr').filter({ hasText: records.TX13 });
      await expect(row).not.toContainText(/^paid$/i);
    });

    await journey.step('MD-06A', 'Procurement Manager creates exact-match Kinetic service order', async () => {
      await switchMainRole(page, credentials, 'procurement_manager');
      records.PO09 = await createProcurementOrder(
        page,
        `${TAG} Kinetic Contractors SG`,
        '2026-05-01',
        '8000',
        '720',
      );
      expect(records.PO09).toBeTruthy();
    });

    await journey.step('MD-06B', 'Procurement Manager cannot self-approve its service order', async () => {
      journey.require(['MD-06A']);
      const section = page.locator('section[aria-labelledby="procurement-heading"]');
      const row = section.locator('div.grid').filter({ hasText: records.PO09 }).last();
      await expect(row.getByRole('button', { name: /^approve$/i })).toBeDisabled();
    });

    await journey.step('MD-06C', 'Finance Approver approves the Kinetic service order with catalog privilege', async () => {
      journey.require(['MD-06A']);
      await switchMainRole(page, credentials, 'finance_approver');
      await approveProcurementOrder(page, records.PO09);
    });

    await journey.step('MD-06D', 'Goods receipt and three-way match control is available', async () => {
      await page.goto(`${ORIGIN}/app/bills`, { waitUntil: 'domcontentloaded' });
      const body = (await page.locator('body').innerText()).toLowerCase();
      if (!body.includes('goods receipt') && !body.includes('receive goods')) {
        journey.block('No visible goods receipt/GRN control exists; only order-to-bill line matching is implemented.');
      }
    });

    await journey.step('P2P-01A', 'AP Clerk creates April Cloud Harbor bill TX-04', async () => {
      await switchMainRole(page, credentials, 'ap_clerk');
      records.TX04 = await createBill(page, {
        vendor: `${TAG} Cloud Harbor SG`,
        vendorInvoice: `${TAG}-CH-APR`,
        issue: '2026-04-08',
        due: '2026-05-08',
        currency: 'SGD',
        description: `${TAG} TX-04 April cloud expense`,
        amount: '3000',
        tax: '270',
      });
      expect(records.TX04).toMatch(/^BILL-/i);
      records.TX04_ID = await captureBillId(page, records.TX04);
    });

    await journey.step('P2P-01B', 'AP Manager approves TX-04 and posts AP with catalog privileges', async () => {
      journey.require(['P2P-01A', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'ap_manager');
      await approveBill(page, records.TX04);
    });

    await journey.step('P2P-01C', 'Finance Controller verifies TX-04 approval before payment', async () => {
      journey.require(['P2P-01B']);
      await switchMainRole(page, credentials, 'finance_controller');
      await page.goto(`${ORIGIN}/app/bills`, { waitUntil: 'domcontentloaded' });
      await page.getByRole('button', { name: `View bill ${records.TX04}`, exact: true }).click();
      await expect(page.getByText(/^approved$/i)).toBeVisible({ timeout: 60_000 });
    });

    await journey.step('P2P-01D', 'AP Manager settles April bill as TX-05', async () => {
      journey.require(['P2P-01C']);
      await switchMainRole(page, credentials, 'ap_manager');
      await settleBill(page, records.TX04, '2026-04-28');
    });

    await journey.step('P2P-02A', 'AP Clerk creates exact-match Kinetic bill TX-09 against service order', async () => {
      journey.require(['MD-06C']);
      await switchMainRole(page, credentials, 'ap_clerk');
      records.TX09 = await createBill(page, {
        vendor: `${TAG} Kinetic Contractors SG`,
        vendorInvoice: `${TAG}-KIN-MAY`,
        issue: '2026-05-10',
        due: '2026-06-09',
        currency: 'SGD',
        description: `${TAG} TX-09 May contractor services`,
        amount: '8000',
        tax: '720',
        purchaseOrder: records.PO09,
      });
      expect(records.TX09).toMatch(/^BILL-/i);
      records.TX09_ID = await captureBillId(page, records.TX09);
    });

    await journey.step('P2P-02B', 'AP Manager approves matched TX-09 with catalog privileges', async () => {
      journey.require(['P2P-02A', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'ap_manager');
      await approveBill(page, records.TX09);
      await expect(page.getByText(/matched|approved/i).first()).toBeVisible();
    });

    await journey.step('P2P-03', 'AP Manager settles Kinetic TX-09 as June payment TX-10', async () => {
      journey.require(['P2P-02B']);
      await switchMainRole(page, credentials, 'ap_manager');
      await settleBill(page, records.TX09, '2026-06-05');
    });

    await journey.step('P2P-04A', 'AP Clerk creates prepaid LedgerCloud bill TX-14', async () => {
      await switchMainRole(page, credentials, 'ap_clerk');
      records.TX14 = await createBill(page, {
        vendor: `${TAG} LedgerCloud SG`,
        vendorInvoice: `${TAG}-LC-ANNUAL`,
        issue: '2026-06-01',
        due: '2026-07-01',
        currency: 'SGD',
        description: `${TAG} TX-14 annual prepaid software`,
        amount: '12000',
        tax: '1080',
        prepaid: { start: '2026-06-01', end: '2027-05-31' },
      });
      expect(records.TX14).toMatch(/^BILL-/i);
      records.TX14_ID = await captureBillId(page, records.TX14);
    });

    await journey.step('P2P-04B', 'AP Manager approves prepaid TX-14 with catalog privileges', async () => {
      journey.require(['P2P-04A', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'ap_manager');
      await approveBill(page, records.TX14);
      await expect(page.getByText(/prepaid/i).first()).toBeVisible();
    });

    await journey.step('P2P-04C', 'AP Manager settles prepaid TX-14 as TX-15', async () => {
      journey.require(['P2P-04B']);
      await switchMainRole(page, credentials, 'ap_manager');
      await settleBill(page, records.TX14, '2026-06-02');
    });

    await journey.step('P2P-05A', 'AP Clerk creates TX-16 at a frozen SGD 1,350 historical base', async () => {
      journey.require(['MD-07B']);
      await switchMainRole(page, credentials, 'ap_clerk');
      records.TX16 = await createBill(page, {
        vendor: `${TAG} Vector Data Inc.`,
        vendorInvoice: `${TAG}-VD-JUN`,
        issue: '2026-05-20',
        due: '2026-06-19',
        currency: 'USD',
        description: `${TAG} TX-16 foreign data expense`,
        amount: records.TX16_FOREIGN_AMOUNT_USD,
        tax: '0',
      });
      expect(records.TX16).toMatch(/^BILL-/i);
      records.TX16_ID = await captureBillId(page, records.TX16);
    });

    await journey.step('P2P-05B', 'AP Manager approves TX-16 at the captured SGD 1,350 base value and leaves it unpaid', async () => {
      journey.require(['P2P-05A', 'LEDGER-GATE']);
      await switchMainRole(page, credentials, 'ap_manager');
      await approveBill(page, records.TX16);
      const posting = await assertVisibleJournalPosting(page, {
        referenceType: 'bill',
        referenceId: records.TX16_ID,
        lines: [
          {
            direction: 'DR',
            accountCode: '5000',
            amount: records.TX16_FOREIGN_AMOUNT_USD,
            currency: 'USD',
            baseAmount: '1350.00',
            fxRateId: records.FX_APPROVAL_RATE_ID,
          },
          {
            direction: 'CR',
            accountCode: '2000',
            amount: records.TX16_FOREIGN_AMOUNT_USD,
            currency: 'USD',
            baseAmount: '1350.00',
            fxRateId: records.FX_APPROVAL_RATE_ID,
          },
        ],
      });
      records.TX16_JOURNAL_ID = posting.journalId;
      records.TX16_JOURNAL_ENTRY_NUMBER = posting.entryNumber;
    });

    await journey.step('O2C-01A', 'GL Accountant posts opening capital TX-01 through manual journal UI', async () => {
      journey.require(['MD-07C']);
      await switchMainRole(page, credentials, 'gl_accountant');
      records.TX01_OUTCOME = await postManualJournal(page, {
        description: `${TAG} TX-01 opening capital`,
        reason: `${TAG} fictional company opening capital for the retained launch-readiness test`,
        date: '2026-04-01',
        reference: `${TAG} TX-01`,
        debitCode: '1100',
        creditCode: '3100',
        amount: '100000',
      });
      expect(['posted', 'pending']).toContain(records.TX01_OUTCOME);
    });

    await journey.step('O2C-01B', 'Owner separately approves opening journal when routed', async () => {
      journey.require(['O2C-01A']);
      if (records.TX01_OUTCOME !== 'pending') journey.skip('Opening journal posted directly; no separate Inbox approval was created.');
      await switchMainRole(page, credentials, 'tenant_owner');
      await approveInboxTask(page, `${TAG} TX-01`);
      records.TX01_OUTCOME = 'posted';
    });

    await journey.step('O2C-01C', 'Opening capital uses dedicated Owner Capital account', async () => {
      journey.require(['O2C-01A']);
      if (records.TX01_OUTCOME !== 'posted') journey.block('TX-01 still awaits its required separate approval.');
      const posting = await assertVisibleJournalPosting(page, {
        referenceType: 'manual',
        rowText: `${TAG} TX-01`,
        lines: [
          { direction: 'DR', accountCode: '1100', amount: '100000.00', currency: 'SGD', baseAmount: '100000.00', fxRateId: null },
          { direction: 'CR', accountCode: '3100', amount: '100000.00', currency: 'SGD', baseAmount: '100000.00', fxRateId: null },
        ],
      });
      records.TX01_JOURNAL_ID = posting.journalId;
      records.TX01_JOURNAL_ENTRY_NUMBER = posting.entryNumber;
    });

    await journey.step('R2R-01A', 'GL Accountant submits June payroll accrual TX-17', async () => {
      journey.require(['MD-07C']);
      await switchMainRole(page, credentials, 'gl_accountant');
      records.TX17_OUTCOME = await postManualJournal(page, {
        description: `${TAG} TX-17 June payroll accrual`,
        reason: `${TAG} accrue fictional June payroll before the retained month-end close`,
        date: '2026-06-30',
        reference: `${TAG} TX-17`,
        debitCode: '5300',
        creditCode: '2150',
        amount: '15000',
      });
      expect(['posted', 'pending']).toContain(records.TX17_OUTCOME);
    });

    await journey.step('R2R-01B', 'Owner separately approves payroll accrual when routed', async () => {
      journey.require(['R2R-01A']);
      if (records.TX17_OUTCOME !== 'pending') journey.skip('Payroll journal posted directly; no separate Inbox approval was created.');
      await switchMainRole(page, credentials, 'tenant_owner');
      await approveInboxTask(page, `${TAG} TX-17`);
      records.TX17_OUTCOME = 'posted';
    });

    await journey.step('R2R-01C', 'Payroll accrual uses dedicated payroll expense and liability accounts', async () => {
      journey.require(['R2R-01A']);
      if (records.TX17_OUTCOME !== 'posted') journey.block('TX-17 still awaits its required separate approval.');
      const posting = await assertVisibleJournalPosting(page, {
        referenceType: 'manual',
        rowText: `${TAG} TX-17`,
        lines: [
          { direction: 'DR', accountCode: '5300', amount: '15000.00', currency: 'SGD', baseAmount: '15000.00', fxRateId: null },
          { direction: 'CR', accountCode: '2150', amount: '15000.00', currency: 'SGD', baseAmount: '15000.00', fxRateId: null },
        ],
      });
      records.TX17_JOURNAL_ID = posting.journalId;
      records.TX17_JOURNAL_ENTRY_NUMBER = posting.entryNumber;
    });

    await journey.step('R2R-00', 'Create the fictional SGD 600 fixed asset and non-cash capital contribution', async () => {
      journey.require(['MD-07C']);
      await switchMainRole(page, credentials, 'gl_accountant');
      records.TX16A_OUTCOME = await postManualJournal(page, {
        description: `${TAG} TX-16A contributed equipment`,
        reason: `${TAG} recognize fictional equipment contributed in kind at fair value`,
        date: '2026-06-01',
        reference: `${TAG} TX-16A`,
        debitCode: '1600',
        creditCode: '3100',
        amount: '600',
      });
      expect(records.TX16A_OUTCOME).toBe('posted');
      const posting = await assertVisibleJournalPosting(page, {
        referenceType: 'manual',
        rowText: `${TAG} TX-16A`,
        lines: [
          { direction: 'DR', accountCode: '1600', amount: '600.00', currency: 'SGD', baseAmount: '600.00', fxRateId: null },
          { direction: 'CR', accountCode: '3100', amount: '600.00', currency: 'SGD', baseAmount: '600.00', fxRateId: null },
        ],
      });
      records.TX16A_JOURNAL_ID = posting.journalId;
      records.TX16A_JOURNAL_ENTRY_NUMBER = posting.entryNumber;
    });

    await journey.step('R2R-02', 'Post June depreciation TX-18 with dedicated accumulated depreciation', async () => {
      journey.require(['R2R-00']);
      await switchMainRole(page, credentials, 'gl_accountant');
      records.TX18_OUTCOME = await postManualJournal(page, {
        description: `${TAG} TX-18 June equipment depreciation`,
        reason: `${TAG} record one month depreciation for the fictional contributed equipment`,
        date: '2026-06-30',
        reference: `${TAG} TX-18`,
        debitCode: '6100',
        creditCode: '1690',
        amount: '600',
      });
      expect(records.TX18_OUTCOME).toBe('posted');
      const posting = await assertVisibleJournalPosting(page, {
        referenceType: 'manual',
        rowText: `${TAG} TX-18`,
        lines: [
          { direction: 'DR', accountCode: '6100', amount: '600.00', currency: 'SGD', baseAmount: '600.00', fxRateId: null },
          { direction: 'CR', accountCode: '1690', amount: '600.00', currency: 'SGD', baseAmount: '600.00', fxRateId: null },
        ],
      });
      records.TX18_JOURNAL_ID = posting.journalId;
      records.TX18_JOURNAL_ENTRY_NUMBER = posting.entryNumber;
    });

    await journey.step('R2R-03', 'GL Accountant posts one-month prepaid amortization TX-19', async () => {
      journey.require(['P2P-04C', 'MD-07C']);
      await switchMainRole(page, credentials, 'gl_accountant');
      records.TX19_OUTCOME = await postManualJournal(page, {
        description: `${TAG} TX-19 June prepaid software amortization`,
        reason: `${TAG} recognize one month of the fictional annual software subscription`,
        date: '2026-06-30',
        reference: `${TAG} TX-19`,
        debitCode: '6000',
        creditCode: '1500',
        amount: '1000',
      });
      expect(records.TX19_OUTCOME).toBe('posted');
      const posting = await assertVisibleJournalPosting(page, {
        referenceType: 'manual',
        rowText: `${TAG} TX-19`,
        lines: [
          { direction: 'DR', accountCode: '6000', amount: '1000.00', currency: 'SGD', baseAmount: '1000.00', fxRateId: null },
          { direction: 'CR', accountCode: '1500', amount: '1000.00', currency: 'SGD', baseAmount: '1000.00', fxRateId: null },
        ],
      });
      records.TX19_JOURNAL_ID = posting.journalId;
      records.TX19_JOURNAL_ENTRY_NUMBER = posting.entryNumber;
    });

    await journey.step('R2R-04A', 'Controller visibly reconciles current AR aging in SGD after TX-12 and TX-13', async () => {
      journey.require(['O2C-08', 'O2C-09B']);
      await switchMainRole(page, credentials, 'finance_controller');
      await assertVisibleCurrentAgingOracle(page, 'AR', '27,250.00');
      records.CURRENT_AR_AGING_SGD = '27250.00';
    });

    await journey.step('R2R-04B', 'Controller visibly reconciles current AP aging in SGD after TX-16', async () => {
      journey.require(['P2P-05B']);
      await switchMainRole(page, credentials, 'finance_controller');
      await assertVisibleCurrentAgingOracle(page, 'AP', '1,350.00');
      records.CURRENT_AP_AGING_SGD = '1350.00';
    });

    const monthlyOracles: MonthlyCloseOracle[] = [
      { month: '2026-04', label: 'April', income: '9,000.00', cash: '109,810.00', ar: '0.00', ap: '0.00', asOf: '2026-04-30' },
      { month: '2026-05', label: 'May', income: '15,400.00', cash: '119,810.00', ar: '16,370.00', ap: '10,070.00', asOf: '2026-05-31' },
      { month: '2026-06', label: 'June', income: '8,400.00', cash: '107,630.00', ar: '34,000.00', ap: '1,350.00', asOf: '2026-06-30' },
    ];

    for (const [period, label, prerequisites] of [
      ['2026-04', 'April', ['O2C-01C', 'O2C-03B', 'P2P-01D']],
      ['2026-05', 'May', ['O2C-05', 'O2C-06B', 'P2P-02B', 'P2P-05B']],
      ['2026-06', 'June', ['P2P-03', 'O2C-07', 'O2C-08', 'O2C-09B', 'P2P-04C', 'P2P-05B', 'R2R-00', 'R2R-01C', 'R2R-02', 'R2R-03']],
    ] as const) {
      await journey.step(`CL-${period}-01`, `${label} close checklist and close package`, async () => {
        const incomplete = prerequisites.filter(id => !journey.passed(id));
        if (incomplete.length) {
          journey.block(
            `${label} close was not started because ledger prerequisites are not PASS: ${incomplete.join(', ')}. `
            + 'No checklist task was falsely marked complete.',
          );
        }
        const oracle = monthlyOracles.find(row => row.month === period)
          ?? journey.block(`Pre-lock statement control is not configured for ${period}.`);
        await switchMainRole(page, credentials, 'finance_controller');
        await verifyMonthlyCloseOracle(page, oracle);
        await switchMainRole(page, credentials, 'close_manager');
        await exerciseCloseChecklist(page, period, oracle);
      });

      await journey.step(`CL-${period}-02`, `${label} period lock through visible UI`, async () => {
        journey.require([`CL-${period}-01`]);
        await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
        const section = page.locator('section[aria-labelledby="close-tasks-title"]');
        const periodInput = section.getByRole('textbox', { name: /close period/i });
        const periodLoaded = page.waitForResponse(response => (
          response.request().method() === 'GET'
          && new URL(response.url()).pathname === `/api/v1/accounting/periods/${period}/close-tasks`
        ));
        await periodInput.fill(period);
        await periodInput.blur();
        expect((await periodLoaded).ok()).toBe(true);
        const lock = page.getByRole('button', { name: /lock period/i });
        if (!(await lock.count())) journey.block('No visible Lock Period control exists; backend-only endpoint cannot count as browser E2E.');
        await lock.click();
        const confirmation = page.getByRole('alertdialog', { name: new RegExp(`Lock ${period}\\?`, 'i') });
        await expect(confirmation).toBeVisible();
        const locked = page.waitForResponse(response => (
          response.request().method() === 'POST'
          && new URL(response.url()).pathname === `/api/v1/accounting/periods/${period}/lock`
        ));
        await confirmation.getByRole('button', { name: /Confirm lock/i }).click();
        expect((await locked).ok()).toBe(true);
        await expect(section.locator('[aria-label="Period close status"]')).toContainText('Locked');
      });

      await journey.step(`CL-${period}-03`, `${label} locked-period write rejection`, async () => {
        journey.require([`CL-${period}-02`]);
        await journey.expectHttp(
          [{ status: 422, url: /\/api\/v1\/accounting\/journal-entries$/ }],
          () => proveLockedPeriodRejectsJournal(page, period),
        );
      }, { fatal: true });
    }

    await journey.step('CL-2026-04-04', 'Owner unlocks and relocks April through visible UI', async () => {
      journey.require(['CL-2026-04-03']);
      await switchMainRole(page, credentials, 'tenant_owner');
      await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
      const section = page.locator('section[aria-labelledby="close-tasks-title"]');
      const periodInput = section.getByRole('textbox', { name: /close period/i });
      const periodLoaded = page.waitForResponse(response => (
        response.request().method() === 'GET'
        && new URL(response.url()).pathname === '/api/v1/accounting/periods/2026-04/close-tasks'
      ));
      await periodInput.fill('2026-04');
      await periodInput.blur();
      expect((await periodLoaded).ok()).toBe(true);

      const unlock = section.getByRole('button', { name: /unlock period/i });
      await expect(unlock).toBeVisible();
      await unlock.click();
      const unlockConfirmation = page.getByRole('alertdialog', { name: /Unlock 2026-04\?/i });
      await expect(unlockConfirmation).toBeVisible();
      const unlocked = page.waitForResponse(response => (
        response.request().method() === 'POST'
        && new URL(response.url()).pathname === '/api/v1/accounting/periods/2026-04/unlock'
      ));
      await unlockConfirmation.getByRole('button', { name: /Confirm unlock/i }).click();
      expect((await unlocked).ok()).toBe(true);
      await expect(section.locator('[aria-label="Period close status"]')).toContainText('Open');

      const relock = section.getByRole('button', { name: /lock period/i });
      await expect(relock).toBeVisible();
      await relock.click();
      const relockConfirmation = page.getByRole('alertdialog', { name: /Lock 2026-04\?/i });
      await expect(relockConfirmation).toBeVisible();
      const relocked = page.waitForResponse(response => (
        response.request().method() === 'POST'
        && new URL(response.url()).pathname === '/api/v1/accounting/periods/2026-04/lock'
      ));
      await relockConfirmation.getByRole('button', { name: /Confirm lock/i }).click();
      expect((await relocked).ok()).toBe(true);
      await expect(section.locator('[aria-label="Period close status"]')).toContainText('Locked');
      records.APRIL_OWNER_UNLOCK_RELOCK = '2026-04 open_then_locked';
    }, { fatal: true });

    for (const oracle of monthlyOracles) {
      await journey.step(`R2R-06-${oracle.month}-IS`, `${oracle.label} Income Statement matches net-income oracle`, async () => {
        await switchMainRole(page, credentials, 'finance_controller');
        await page.goto(`${ORIGIN}/app/reports`, { waitUntil: 'domcontentloaded' });
        await page.getByRole('tab', { name: /^income statement$/i }).click();
        await setStatementRange(page, oracle.month, oracle.month);
        await expect(page.getByText(/net income/i).first()).toBeVisible({ timeout: 60_000 });
        await expect(page.locator('mat-tab-body.mat-mdc-tab-body-active')).toContainText(oracle.income);
      });

      await journey.step(`R2R-06-${oracle.month}-BS`, `${oracle.label} Balance Sheet matches cash, AR, and AP oracles`, async () => {
        await page.getByRole('tab', { name: /^balance sheet$/i }).click();
        await setStatementRange(page, oracle.month, oracle.month);
        const active = page.locator('mat-tab-body.mat-mdc-tab-body-active');
        await expect(active.getByText(/balance sheet balances/i)).toBeVisible({ timeout: 60_000 });
        await expect(active).toContainText(oracle.cash);
        await expect(active).toContainText(oracle.ar);
        await expect(active).toContainText(oracle.ap);
      });

      await journey.step(`R2R-06-${oracle.month}-CF`, `${oracle.label} Cash Flow matches ending-cash oracle`, async () => {
        await page.getByRole('tab', { name: /^cash flow$/i }).click();
        await setStatementRange(page, oracle.month, oracle.month);
        const active = page.locator('mat-tab-body.mat-mdc-tab-body-active');
        await expect(active.getByText(/ending cash/i).first()).toBeVisible({ timeout: 60_000 });
        await expect(active).toContainText(oracle.cash);
      });
    }

    await journey.step('R2R-08A', 'Q2 Apr–Jun Income Statement matches SGD 32,800 net income', async () => {
      await page.getByRole('tab', { name: /^income statement$/i }).click();
      await setStatementRange(page, '2026-04', '2026-06');
      const active = page.locator('mat-tab-body.mat-mdc-tab-body-active');
      await expect(active).toContainText('61,750.00');
      await expect(active).toContainText('32,800.00');
    });

    await journey.step('R2R-08B', 'Q2 ending Balance Sheet matches SGD 154,700 gross presentation', async () => {
      await page.getByRole('tab', { name: /^balance sheet$/i }).click();
      await setStatementRange(page, '2026-04', '2026-06');
      const active = page.locator('mat-tab-body.mat-mdc-tab-body-active');
      await expect(active).toContainText('107,630.00');
      await expect(active).toContainText(/154,700\.00|152,630\.00/);
      await expect(active.getByText(/balance sheet balances/i)).toBeVisible();
    });

    await journey.step('R2R-08C', 'Q2 Cash Flow matches SGD 107,630 ending cash', async () => {
      await page.getByRole('tab', { name: /^cash flow$/i }).click();
      await setStatementRange(page, '2026-04', '2026-06');
      await expect(page.locator('mat-tab-body.mat-mdc-tab-body-active')).toContainText('107,630.00');
    });

    await journey.step('R2R-08D', 'Q2 Trial Balance balances at SGD 184,250', async () => {
      await page.getByRole('tab', { name: /^trial balance$/i }).click();
      await page.locator('#tb-period').fill('2026-06');
      await page.locator('#tb-period').blur();
      const active = page.locator('mat-tab-body.mat-mdc-tab-body-active');
      await expect(active.getByText(/balanced.*dr equals cr/i)).toBeVisible({ timeout: 60_000 });
      await expect(active).toContainText('184,250.00');
    });

    await journey.step('R2R-08E', 'Q2 Statutory Pack uses the true Apr–Jun range', async () => {
      await page.getByRole('tab', { name: /^statutory pack$/i }).click();
      await setStatementRange(page, '2026-04', '2026-06');
      const active = page.locator('mat-tab-body.mat-mdc-tab-body-active');
      await expect(active).toContainText(/Singapore|SG/i);
      await expect(active).toContainText(/SGD/i);
      await expect(active.getByText('Net Income', { exact: true })).toBeVisible();
      await expect(active.getByText('Ending Cash', { exact: true })).toBeVisible();
      await expect(active.getByText('Ending RE', { exact: true })).toBeVisible();
      await expect(active.getByText('Tax Payable', { exact: true })).toBeVisible();
    });

    await journey.step('R2R-08F', 'Quarterly statements can be exported by an end user', async () => {
      const exportControl = page.getByRole('button', { name: /export|download|print|pdf|csv/i });
      if (!(await exportControl.count())) journey.block('No report export, print, PDF, or CSV control exists.');
    });

    for (const role of ['auditor', 'executive_viewer'] as const) {
      await journey.step(`R2R-09-${role}`, `${account(credentials, role).label} can view reports but cannot mutate finance`, async () => {
        await switchMainRole(page, credentials, role);
        await page.goto(`${ORIGIN}/app/reports`, { waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('heading', { name: /^reports$/i })).toBeVisible();
        await page.getByRole('tab', { name: /^income statement$/i }).click();
        await setStatementRange(page, '2026-04', '2026-06');
        await expect(page.getByText(/net income/i).first()).toBeVisible({ timeout: 60_000 });
        await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('button', { name: /new journal entry/i })).toHaveCount(0);
      });
    }

    await journey.step('R2R-10', 'Statement totals drill through to journal and source IDs', async () => {
      await switchMainRole(page, credentials, 'finance_controller');
      await page.goto(`${ORIGIN}/app/reports`, { waitUntil: 'domcontentloaded' });
      const drill = page.getByRole('link', { name: /drill|journal|source/i }).or(page.getByRole('button', { name: /drill|journal|source/i }));
      if (!(await drill.count())) journey.block('Financial statement totals have no visible drill-through to journals/source records.');
    });

    await journey.step('EDGE-SIGNUP-01', 'Duplicate owner signup is rejected without a second tenant', async () => {
      await logout(page);
      await page.goto(`${ORIGIN}/signup`, { waitUntil: 'domcontentloaded' });
      await page.locator('#firm').fill(DATA.company);
      await page.locator('#email').fill(owner.email);
      await page.locator('#password').fill(owner.password);
      await page.locator('#confirm_password').fill(owner.password);
      await page.locator('#country').selectOption('SG');
      await page.getByRole('button', { name: /continue to plan/i }).click();
      await expect(page.getByRole('alert')).toContainText(/already|exists|registered/i, { timeout: 60_000 });
      await expect(page).toHaveURL(/\/signup$/);
    });

    await journey.step('EDGE-AUTH-01', 'Wrong password is denied and the valid owner credential still works', async () => {
      await page.goto(`${ORIGIN}/login`, { waitUntil: 'domcontentloaded' });
      await page.locator('#email').fill(owner.email);
      await page.locator('#password').fill(`${owner.password}wrong`);
      await page.getByRole('button', { name: /^sign in$/i }).click();
      await expect(page.getByRole('alert')).toContainText(/incorrect/i, { timeout: 30_000 });
      await page.locator('#password').fill(owner.password);
      await page.getByRole('button', { name: /^sign in$/i }).click();
      await page.waitForURL(/\/app\/copilot/, { timeout: 60_000 });
    });

    await journey.step('EDGE-CONTACT-01', 'Blank contact cannot be submitted', async () => {
      await page.goto(`${ORIGIN}/app/clients`, { waitUntil: 'domcontentloaded' });
      await page.getByRole('button', { name: /new contact/i }).click();
      const dialog = page.getByRole('dialog', { name: /new contact/i });
      await expect(dialog.getByRole('button', { name: /^create contact$/i })).toBeDisabled();
      await dialog.getByRole('button', { name: /^cancel$/i }).click();
    });

    await journey.step('EDGE-ENGAGEMENT-01', 'Incomplete engagement remains blocked client-side', async () => {
      await page.goto(`${ORIGIN}/app/engagements`, { waitUntil: 'domcontentloaded' });
      await page.getByRole('button', { name: /create new engagement/i }).click();
      const dialog = page.getByRole('dialog', { name: /new engagement/i });
      await dialog.locator('#eng-name').fill(`${TAG}-EDGE incomplete`);
      await expect(dialog.getByRole('button', { name: /^create engagement$/i })).toBeDisabled();
      await dialog.getByRole('button', { name: /^cancel$/i }).click();
    });

    await journey.step('EDGE-BILL-01', 'Blank vendor bill cannot be submitted', async () => {
      await page.goto(`${ORIGIN}/app/bills`, { waitUntil: 'domcontentloaded' });
      await page.getByRole('button', { name: /create new bill/i }).click();
      const dialog = page.getByRole('dialog', { name: /new bill/i });
      await expect(dialog.getByRole('button', { name: /^create bill$/i })).toBeDisabled();
      await dialog.getByRole('button', { name: /^cancel$/i }).click();
    });

    await journey.step('EDGE-JOURNAL-01', 'Imbalanced manual journal cannot be posted', async () => {
      await page.goto(`${ORIGIN}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });
      await page.getByRole('button', { name: /new journal entry/i }).click();
      const dialog = page.getByRole('dialog', { name: /post manual journal entry/i });
      await dialog.locator('#jnl-desc').fill(`${TAG}-EDGE imbalance`);
      await dialog.locator('#jnl-reason').fill(`${TAG} deliberate imbalance validation`);
      await dialog.locator('#jnl-date').fill('2026-06-30');
      await dialog.getByRole('textbox', { name: /amount for line 1/i }).fill('100');
      await dialog.getByRole('textbox', { name: /amount for line 2/i }).fill('99');
      await expect(dialog.getByRole('alert')).toContainText(/out of balance/i);
      await expect(dialog.getByRole('button', { name: /^post journal entry$/i })).toBeDisabled();
      await dialog.getByRole('button', { name: /^cancel$/i }).click();
    });

    await journey.step('EDGE-UI-01', 'Core reports survive narrow viewport and hard refresh', async () => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto(`${ORIGIN}/app/reports`, { waitUntil: 'domcontentloaded' });
      await page.reload({ waitUntil: 'domcontentloaded' });
      await expect(page.getByRole('heading', { name: /^reports$/i })).toBeVisible();
      await page.setViewportSize({ width: 1440, height: 900 });
    });

    await journey.step('EDGE-MATRIX-GAPS', 'All remaining launch edge cases have executable visible UI', async () => {
      journey.block(
        'No UI exists for several required cases: FX rate administration/write UI, credit/refund/write-off, '
        + 'goods receipt, report export/drilldown, platform admin, and safe cross-tenant direct-ID validation. '
        + 'The concurrent period lock/write race remains unexercised; ordinary lock, write rejection, and Owner unlock/relock are browser-tested. '
        + 'These cannot be bypassed with API/DB mutation in a browser-only run.',
      );
    });

    await journey.step('FIN-01', 'Full-run console, network, worker, and 5xx review', async () => {
      const fiveHundreds = journey.findings.filter(item => item.kind === 'http' && (item.status ?? 0) >= 500);
      expect(fiveHundreds, `Unexpected 5xx responses: ${JSON.stringify(fiveHundreds)}`).toEqual([]);
      const requestFailures = journey.findings.filter(item => item.kind === 'requestfailed' && !item.expected);
      expect(requestFailures, `Unexpected request failures: ${JSON.stringify(requestFailures)}`).toEqual([]);
      const consoleErrors = journey.findings.filter(item => item.kind === 'console');
      expect(consoleErrors, `Unexpected console errors: ${JSON.stringify(consoleErrors)}`).toEqual([]);
      const unexpectedFourHundreds = journey.findings.filter(item => (
        item.kind === 'http'
        && (item.status ?? 0) >= 400
        && (item.status ?? 0) < 500
        && !item.expected
        && !isExpectedNegativeFinding(item)
      ));
      expect(unexpectedFourHundreds, `Unexpected 4xx responses: ${JSON.stringify(unexpectedFourHundreds)}`).toEqual([]);
    });

    await journey.step('FIN-02', 'Monthly, quarterly, AR/AP/GL, GST, FX, cash, and equity reconciliation', async () => {
      const required = [
        'O2C-01C', 'O2C-05', 'O2C-08', 'P2P-05B', 'R2R-00', 'R2R-01C', 'R2R-02',
        'CL-2026-04-02', 'CL-2026-05-02', 'CL-2026-06-02',
        'R2R-08A', 'R2R-08B', 'R2R-08C', 'R2R-08D',
      ];
      const incomplete = required.filter(id => !journey.passed(id));
      if (incomplete.length) journey.block(`Reconciliation cannot sign off because required steps are not PASS: ${incomplete.join(', ')}.`);
    });

    await journey.step('FIN-03', 'Retain tenant and secure credentials/evidence', async () => {
      expect(credentials.retained).toBe(true);
      expect(credentials.tenant_id).toMatch(/^[0-9a-f-]{36}$/i);
      expect(fs.statSync(CREDENTIAL_PATH).mode & 0o077).toBe(0);
      expect(fs.statSync(PRIVATE_ROOT).mode & 0o077).toBe(0);
      expect(credentials.accounts.every(item => item.status === 'active')).toBe(true);
      expect(credentials.accounts.every(item => !item.pending_password)).toBe(true);
      expect(new Set(credentials.accounts.map(item => item.password)).size).toBe(22);
    });

    await journey.step('FIN-04', 'Evidence index and launch verdict are complete', async () => {
      const unresolved = journey.results.filter(result => ['FAIL', 'BLOCKED'].includes(result.status));
      if (unresolved.length) journey.block(`${unresolved.length} unresolved failed/blocked steps require issues and retest before launch.`);
    });

    const blockers = journey.results.filter(result => ['FAIL', 'BLOCKED'].includes(result.status));
    expect(
      blockers.map(result => `${result.id}: ${result.detail ?? result.title}`),
      'Launch sign-off requires zero failed or blocked required browser steps.',
    ).toEqual([]);
  } finally {
    journey.writeReport();
  }
});
