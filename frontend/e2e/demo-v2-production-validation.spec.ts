/**
 * Demo Guide v2 production browser validation.
 *
 * This is intentionally an evidence recorder, not a smoke test:
 * - authenticates through the public app
 * - visits every major Demo Guide v2 surface
 * - sends the guide's real Atlas prompts
 * - uploads the real demo PDFs
 * - records screenshots, response excerpts, network failures, and visible gaps
 *
 * Run:
 *   AETHOS_PS_WEB_URL=https://aethos.ishirock.tech \
 *   AETHOS_TS_WEB_URL=https://timesheet.aethos.ishirock.tech \
 *   npx playwright test e2e/demo-v2-production-validation.spec.ts --project=chromium
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const WEB = process.env.AETHOS_PS_WEB_URL ?? 'https://aethos.ishirock.tech';
const TIMESHEET = process.env.AETHOS_TS_WEB_URL ?? 'https://timesheet.aethos.ishirock.tech';
const RUN_ID = new Date().toISOString().replace(/[:.]/g, '-');
const REPO_ROOT = path.resolve(__dirname, '../..');
const AUTH_STATE = path.join(__dirname, '.auth', 'o2c-tenant.json');
const AUTH_META = path.join(__dirname, '.auth', 'o2c-tenant.meta.json');
const QA_DIR = path.join(REPO_ROOT, 'docs', 'qa', `demo-v2-production-${RUN_ID}`);
const SHOT_DIR = path.join(QA_DIR, 'screenshots');
const REPORT_PATH = path.join(QA_DIR, 'report.md');
const JSON_PATH = path.join(QA_DIR, 'results.json');

type Status = 'PASS' | 'FAIL' | 'WARN' | 'SKIP';
type Evidence = {
  id: string;
  section: string;
  action: string;
  status: Status;
  prompt?: string;
  response?: string;
  screenshot?: string;
  notes?: string[];
  validation?: BusinessValidation;
};
type PromptStep = {
  id: string;
  section: string;
  prompt: string;
  attachment?: string;
  timeoutMs?: number;
  expected?: RegExp[];
  sameThread?: boolean;
};
type ValidationRule = {
  criteria: string[];
  required: RegExp[];
  minRequired?: number;
  forbidden?: RegExp[];
};
type BusinessValidation = {
  verdict: Status;
  criteria: string[];
  matchedRequired: string[];
  missingRequired: string[];
  forbiddenHits: string[];
  summary: string;
};

const evidence: Evidence[] = [];
const consoleErrors: string[] = [];
const networkFailures: string[] = [];

function rel(file: string): string {
  return path.relative(REPO_ROOT, file);
}

function record(item: Evidence): void {
  evidence.push(item);
  const icon = item.status === 'PASS' ? 'PASS' : item.status;
  console.log(`[${icon}] ${item.id} ${item.section} - ${item.action}`);
  if (item.notes?.length) console.log(`      ${item.notes.join(' | ')}`);
}

async function screenshot(page: Page, id: string): Promise<string> {
  const file = path.join(SHOT_DIR, `${id.replace(/[^a-zA-Z0-9_.-]/g, '-')}.png`);
  await page.screenshot({ path: file, fullPage: false }).catch(() => undefined);
  return rel(file);
}

async function authenticate(page: Page): Promise<void> {
  const meta = JSON.parse(fs.readFileSync(AUTH_META, 'utf-8')) as {
    email: string;
    password: string;
    tenantName?: string;
    tenantId?: string;
  };
  await page.goto(`${WEB}/login`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible({ timeout: 30_000 });
  await page.locator('#email, input[type="email"]').first().fill(meta.email);
  await page.locator('#password, input[type="password"]').first().fill(meta.password);
  await screenshot(page, 'auth-login-filled');
  await page.getByRole('button', { name: /^sign in$/i }).click();
  await page.waitForURL(/\/app\/copilot(\?.*)?$/, { timeout: 90_000 });
  await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible({ timeout: 30_000 });
  await page.context().storageState({ path: AUTH_STATE });
  record({
    id: 'auth',
    section: 'Authentication',
    action: `Logged into ${WEB}`,
    status: 'PASS',
    screenshot: rel(path.join(SHOT_DIR, 'auth-login-filled.png')),
    notes: [
      `Tenant: ${meta.tenantName ?? 'unknown'}`,
      `Tenant ID: ${meta.tenantId ?? 'unknown'}`,
      `User: ${meta.email}`,
    ],
  });
}

async function gotoAndRecord(page: Page, id: string, label: string, url: string): Promise<void> {
  const notes: string[] = [];
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => undefined);
    await page.waitForTimeout(750);
    const shot = await screenshot(page, `route-${id}`);
    const bodyText = (await page.locator('body').innerText({ timeout: 5_000 }).catch(() => '')).slice(0, 500);
    const errorText = /error loading|failed to load|something went wrong/i.test(bodyText);
    if (errorText) notes.push('Visible page text contains an error/loading failure marker.');
    record({
      id: `route-${id}`,
      section: 'Route Coverage',
      action: label,
      status: errorText ? 'WARN' : 'PASS',
      screenshot: shot,
      notes: [`URL: ${url}`, `Body excerpt: ${bodyText.replace(/\s+/g, ' ').slice(0, 180)}`].concat(notes),
    });
  } catch (err) {
    record({
      id: `route-${id}`,
      section: 'Route Coverage',
      action: label,
      status: 'FAIL',
      notes: [`URL: ${url}`, String(err).slice(0, 300)],
    });
  }
}

async function startNewChat(page: Page): Promise<void> {
  await page.goto(`${WEB}/app/copilot`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
  const button = page.getByRole('button', { name: /new chat|start new chat/i }).first();
  if (await button.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await button.click();
    await page.waitForTimeout(600);
  }
}

async function attachDocument(page: Page, step: PromptStep): Promise<string[]> {
  const notes: string[] = [];
  if (!step.attachment) return notes;
  const filePath = path.join(REPO_ROOT, step.attachment);
  if (!fs.existsSync(filePath)) {
    notes.push(`Attachment missing locally: ${step.attachment}`);
    return notes;
  }
  const input = page.locator('input[type="file"][aria-label="Attach document"]').first();
  await input.setInputFiles(filePath);
  await expect(page.getByText(/Attached.*add instructions and send to process/i)).toBeVisible({
    timeout: 30_000,
  });
  await page.waitForTimeout(5_000);
  const banner = await page.locator('[role="status"]').last().innerText().catch(() => '');
  notes.push(`Attachment banner before prompt: ${banner.replace(/\s+/g, ' ')}`);
  if (/Processing|Processed|Inbox/i.test(banner)) {
    notes.push('WARNING: attachment appeared to process before prompt submission.');
  } else {
    notes.push('Attachment did not start extraction before prompt submission.');
  }
  await screenshot(page, `${step.id}-attachment`);
  return notes;
}

const commonInvalidAnswerPatterns = [
  /temporarily unavailable|server error|stack trace|traceback|HTTP 400|validation errors?/i,
  /\bI (?:do not|don't) (?:have|see|find|locate|know|have direct access)\b/i,
  /couldn'?t locate|not showing up|not found|no .* on file|need .* from you|need .* details|need more information|need some details/i,
  /can you provide|can you confirm|do you want me to|please provide|once you provide/i,
  /not exposed|requires? access to .*outside|would require access|contact your infrastructure team/i,
  /context_ref|raw payload|policy reason code|aethos\.[a-z0-9_.]+/i,
];

function rule(criteria: string[], required: RegExp[], minRequired = required.length, forbidden: RegExp[] = []): ValidationRule {
  return { criteria, required, minRequired, forbidden };
}

function validateBusinessAnswer(
  step: PromptStep,
  response: string,
  notes: string[],
  visibleToolCardDelta: number,
): BusinessValidation {
  const validationRule = validationRules[step.id] ?? rule(
    [
      'Answers the user prompt directly.',
      'Includes the expected business terms for this scenario.',
      'Does not ask the user to do work the AI should perform.',
    ],
    step.expected ?? [],
  );
  const matchedRequired = validationRule.required
    .filter((pattern) => pattern.test(response))
    .map((pattern) => `/${pattern.source}/${pattern.flags}`);
  const missingRequired = validationRule.required
    .filter((pattern) => !pattern.test(response))
    .map((pattern) => `/${pattern.source}/${pattern.flags}`);
  const forbiddenHits = commonInvalidAnswerPatterns
    .concat(validationRule.forbidden ?? [])
    .filter((pattern) => pattern.test(response))
    .map((pattern) => `/${pattern.source}/${pattern.flags}`);

  if (visibleToolCardDelta > 0) {
    forbiddenHits.push(`Visible tool-call cards: ${visibleToolCardDelta}`);
  }
  if (notes.some((note) => /appeared to process before prompt submission/i.test(note))) {
    forbiddenHits.push('Attachment processed before prompt submission.');
  }

  let verdict: Status = 'PASS';
  if (!response.trim()) {
    verdict = 'FAIL';
    forbiddenHits.push('No Atlas response captured.');
  } else if (matchedRequired.length < (validationRule.minRequired ?? validationRule.required.length)) {
    verdict = 'FAIL';
  } else if (forbiddenHits.length) {
    verdict = 'FAIL';
  }

  const summary = verdict === 'PASS'
    ? `Business-valid answer: matched ${matchedRequired.length}/${validationRule.required.length} required signals.`
    : `Business validation failed: matched ${matchedRequired.length}/${validationRule.required.length} required signals; forbidden hits ${forbiddenHits.length}.`;
  notes.push(summary);
  if (missingRequired.length) notes.push(`Missing required signals: ${missingRequired.join(', ')}`);
  if (forbiddenHits.length) notes.push(`Invalid answer signals: ${forbiddenHits.join(', ')}`);

  return {
    verdict,
    criteria: validationRule.criteria,
    matchedRequired,
    missingRequired,
    forbiddenHits,
    summary,
  };
}

async function sendAtlasPrompt(page: Page, step: PromptStep): Promise<void> {
  if (!step.sameThread) await startNewChat(page);
  const notes = await attachDocument(page, step);
  const beforeAssistant = await page.locator('[aria-label^="Atlas:"]').count();
  const beforeToolCards = await page.locator('[aria-label^="Running tool:"], [aria-label^="Tool completed:"]').count();
  try {
    const input = page.getByLabel('Message input');
    await expect(input).toBeEnabled({ timeout: 45_000 });
    await input.fill(step.prompt);
    await screenshot(page, `${step.id}-prompt`);
    await page.getByRole('button', { name: /send message/i }).click();
    await page.locator('[aria-label^="Atlas:"]').nth(beforeAssistant).waitFor({
      state: 'visible',
      timeout: step.timeoutMs ?? 180_000,
    }).catch(() => undefined);
    await expect(input).toBeEnabled({ timeout: step.timeoutMs ?? 180_000 }).catch(() => undefined);
    await page.waitForTimeout(1_000);
    const shot = await screenshot(page, `${step.id}-response`);
    const response = await page.locator('[aria-label^="Atlas:"]').last().innerText().catch(() => '');
    const afterToolCards = await page.locator('[aria-label^="Running tool:"], [aria-label^="Tool completed:"]').count();
    const matched = (step.expected ?? []).filter((pattern) => pattern.test(response)).length;
    if ((step.expected ?? []).length && matched < (step.expected ?? []).length) {
      notes.push(`Expected response signals matched ${matched}/${step.expected?.length ?? 0}.`);
    }
    if (afterToolCards > beforeToolCards) {
      notes.push(`Tool-call cards visible to user: ${afterToolCards - beforeToolCards}.`);
    }
    if (/context_ref|traceback|stack trace|aethos\.[a-z0-9_.]+/i.test(response)) {
      notes.push('Response may expose internal context/tool/trace terminology.');
    }
    const validation = validateBusinessAnswer(step, response, notes, afterToolCards - beforeToolCards);
    record({
      id: step.id,
      section: step.section,
      action: 'Atlas prompt',
      status: validation.verdict,
      prompt: step.prompt,
      response,
      screenshot: shot,
      notes,
      validation,
    });
  } catch (err) {
    const shot = await screenshot(page, `${step.id}-failed`);
    record({
      id: step.id,
      section: step.section,
      action: 'Atlas prompt',
      status: 'FAIL',
      prompt: step.prompt,
      screenshot: shot,
      notes: notes.concat(String(err).slice(0, 500)),
    });
  }
}

function writeReport(): void {
  const counts = evidence.reduce<Record<Status, number>>(
    (acc, item) => {
      acc[item.status] += 1;
      return acc;
    },
    { PASS: 0, WARN: 0, FAIL: 0, SKIP: 0 },
  );
  const rows = evidence.map((item) => (
    `| ${item.id} | ${item.section} | ${item.action.replace(/\|/g, '/')} | ${item.status} | ${item.screenshot ? `[screenshot](${path.relative(QA_DIR, path.join(REPO_ROOT, item.screenshot)).replace(/\\/g, '/')})` : ''} | ${(item.notes ?? []).join('<br>').replace(/\|/g, '/')} |`
  )).join('\n');
  const prompts = evidence
    .filter((item) => item.prompt)
    .map((item) => [
      `## ${item.id} - ${item.section}`,
      '',
      '**Prompt**',
      '',
      '```text',
      item.prompt,
      '```',
      '',
      '**Observed Atlas Response**',
      '',
      '```text',
      (item.response ?? '').slice(0, 3000) || '(no response captured)',
      '```',
      '',
      '**Business Validation**',
      '',
      item.validation
        ? [
          `Verdict: ${item.validation.verdict}`,
          `Summary: ${item.validation.summary}`,
          `Criteria: ${item.validation.criteria.join(' | ')}`,
          `Matched required signals: ${item.validation.matchedRequired.length ? item.validation.matchedRequired.join(', ') : 'none'}`,
          `Missing required signals: ${item.validation.missingRequired.length ? item.validation.missingRequired.join(', ') : 'none'}`,
          `Invalid answer signals: ${item.validation.forbiddenHits.length ? item.validation.forbiddenHits.join(', ') : 'none'}`,
        ].join('\n')
        : 'No business validation was recorded for this entry.',
      '',
      item.screenshot ? `Screenshot: [${item.screenshot}](${path.relative(QA_DIR, path.join(REPO_ROOT, item.screenshot)).replace(/\\/g, '/')})` : '',
    ].join('\n'))
    .join('\n\n');

  const report = [
    '# Demo Guide v2 Production Browser Validation',
    '',
    `Run ID: \`${RUN_ID}\``,
    `Base URL: \`${WEB}\``,
    `Timesheet URL: \`${TIMESHEET}\``,
    `Generated: \`${new Date().toISOString()}\``,
    '',
    'This report was generated from a real browser session against production. It uses the production demo tenant credentials stored in `frontend/e2e/.auth/o2c-tenant.meta.json` and uploads the PDF files from `docs/demo-assets`.',
    '',
    `Summary: PASS ${counts.PASS}, WARN ${counts.WARN}, FAIL ${counts.FAIL}, SKIP ${counts.SKIP}`,
    '',
    '## Evidence Table',
    '',
    '| ID | Section | Action | Status | Screenshot | Notes |',
    '| --- | --- | --- | --- | --- | --- |',
    rows,
    '',
    '## Prompt Transcript',
    '',
    prompts,
    '',
    '## Browser Console Errors',
    '',
    consoleErrors.length ? consoleErrors.map((err) => `- \`${err.slice(0, 220)}\``).join('\n') : '_None captured_',
    '',
    '## Network Failures And 5xx Responses',
    '',
    networkFailures.length ? networkFailures.map((err) => `- \`${err.slice(0, 260)}\``).join('\n') : '_None captured_',
    '',
  ].join('\n');

  fs.mkdirSync(QA_DIR, { recursive: true });
  fs.writeFileSync(REPORT_PATH, report);
  fs.writeFileSync(JSON_PATH, JSON.stringify({ runId: RUN_ID, web: WEB, timesheet: TIMESHEET, evidence, consoleErrors, networkFailures }, null, 2));
  console.log(`Report: ${REPORT_PATH}`);
  console.log(`Results JSON: ${JSON_PATH}`);
}

const routes = [
  ['copilot', 'Aethos Atlas', `${WEB}/app/copilot`],
  ['documents', 'Documents', `${WEB}/app/documents`],
  ['inbox', 'Inbox', `${WEB}/app/inbox`],
  ['engagements', 'Engagements', `${WEB}/app/engagements`],
  ['projects', 'Projects', `${WEB}/app/projects`],
  ['invoices', 'Invoices', `${WEB}/app/invoices`],
  ['clients', 'Contacts', `${WEB}/app/clients`],
  ['expenses', 'Expenses', `${WEB}/app/expenses`],
  ['bills', 'Bills', `${WEB}/app/bills`],
  ['billing-runs', 'Billing Runs / Pay Bills', `${WEB}/app/billing-runs`],
  ['time', 'Time', `${WEB}/app/time`],
  ['approvals', 'Approvals', `${WEB}/app/approvals`],
  ['payments', 'Payments', `${WEB}/app/payments`],
  ['people', 'People', `${WEB}/app/people`],
  ['reports', 'Reports', `${WEB}/app/reports`],
  ['journals', 'Accounting / Journal Entries', `${WEB}/app/accounting/journals`],
  ['settings', 'Settings', `${WEB}/app/settings`],
  ['timesheet', 'Timesheet portal', TIMESHEET],
] as const;

const promptSteps: PromptStep[] = [
  {
    id: '1-1-engagement-letter',
    section: '1.1 Engagement letter onboarding',
    attachment: 'docs/demo-assets/nexus_engagement_letter.pdf',
    prompt: 'Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.',
    expected: [/Nexus|engagement|billing|Inbox/i],
  },
  {
    id: '1-2-engagement-structure',
    section: '1.2 Project structure',
    prompt: 'Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.',
    expected: [/Nexus|project|billing/i],
  },
  {
    id: '1-3-log-time',
    section: '1.3 Time entry',
    prompt: 'Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling',
    expected: [/time|hours|Nexus|review|Inbox|logged/i],
  },
  {
    id: '1-3a-delivery-data',
    section: '1.3A People and WIP',
    prompt: "Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.",
    expected: [/Alice|time|WIP|utilization|Nexus/i],
  },
  {
    id: '1-4-billing-run',
    section: '1.4 Mixed model invoice',
    prompt: 'Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending.',
    expected: [/Nexus|invoice|Inbox|billing/i],
  },
  {
    id: '1-5-revenue-recognition',
    section: '1.5 Revenue recognition',
    prompt: 'Explain how Nexus June revenue is recognized across fixed-fee milestone, retainer, T&M advisory WIP, and expenses. Tie the explanation to invoice-backed journals and Project P&L.',
    expected: [/revenue|journal|WIP|Project/i],
  },
  {
    id: '1-6-capped-tax',
    section: '1.6 Capped tax engagement',
    prompt: 'Create an engagement for Nexus - Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun',
    expected: [/Nexus|Tax|engagement|cap|Inbox|created/i],
  },
  {
    id: '1-7-o2c-readiness',
    section: '1.7 O2C controls',
    prompt: 'Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval.',
    expected: [/Nexus|invoice|WIP|collections|tax|rate/i],
  },
  {
    id: '1-7-collections-read',
    section: '1.7 Collections read pack',
    prompt: 'Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.',
    expected: [/invoice|due|aging|balance|collections/i],
  },
  {
    id: '1-7-invoice-drilldown',
    section: '1.7 Invoice drilldown',
    prompt: 'Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action.',
    expected: [/INV-1001|invoice|due|payment|recommended/i],
  },
  {
    id: '1-7-draft-reminders',
    section: '1.7 Collections controlled write',
    prompt: 'Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.',
    expected: [/Inbox|reminder|invoice|email/i],
  },
  {
    id: '2-1-retainer',
    section: '2.1 Monthly retainer billing',
    prompt: 'Prepare Brightwater Manufacturing monthly retainer billing for June 2026. Show the draft invoice, any tax, and route it to Inbox before sending.',
    expected: [/Brightwater|invoice|retainer|Inbox/i],
  },
  {
    id: '2-2-milestone',
    section: '2.2 Annual accounts milestone',
    prompt: 'Prepare the Brightwater Annual Accounts FY2025 milestone invoice. Include the milestone basis, tax treatment, and approval path before sending.',
    expected: [/Brightwater|Annual|milestone|invoice/i],
  },
  {
    id: '2-3-payroll',
    section: '2.3 Payroll billing',
    prompt: 'Prepare Brightwater payroll billing for June 2026 based on active employee count. Show per-employee billing, invoice total, and any approval needed.',
    expected: [/Brightwater|payroll|employee|invoice/i],
  },
  {
    id: '2-4-vendor-invoice',
    section: '2.4 Vendor invoice intake',
    attachment: 'docs/demo-assets/brightwater_subcontractor_invoice.pdf',
    prompt: 'Process this vendor invoice for Brightwater. Match it to the right vendor and project, flag duplicate risk, code it to the right account, compare any PO or service-order evidence, and send exceptions to Inbox.',
    expected: [/Brightwater|vendor|bill|Inbox|duplicate/i],
  },
  {
    id: '2-4-payment-risk-read',
    section: '2.4 P2P read pack',
    prompt: 'Which vendor bills are due soon, which are blocked, and what evidence supports payment? Show vendor, bill number, amount, due date, status, coding evidence, source document, duplicate risk, PO/service-order match, payment-batch state, blockers, and next action. Do not create a payment batch yet.',
    expected: [/vendor|bill|payment|blocked|evidence/i],
  },
  {
    id: '2-4-single-bill',
    section: '2.4 Single bill drilldown',
    prompt: 'Review bill BILL-1001. Show due date, amount, vendor invoice number, coding status, source document, duplicate signals, PO/service-order match, approval state, payment readiness, existing batch status, and recommended next action.',
    expected: [/BILL-1001|bill|payment|recommended/i],
  },
  {
    id: '2-5-bill-pay',
    section: '2.5 Payment controls',
    prompt: "Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox.",
    expected: [/bill|payment|Inbox|approved/i],
  },
  {
    id: '2-5-payment-packet',
    section: '2.5 Payment approval packet',
    prompt: 'Prepare a payment approval packet for bills due in the next 10 days. Include vendor, amount, due date, coding evidence, duplicate status, cash impact, and the approver role required for the batch.',
    expected: [/vendor|amount|due|approver|payment/i],
  },
  {
    id: '3-1-family-office',
    section: '3.1 Family office structure',
    prompt: 'Show the Alderton Family Office structure. List each engagement, service line, billing model, currency, open projects, and missing setup before billing.',
    expected: [/Alderton|engagement|billing|currency/i],
  },
  {
    id: '3-2-scope-creep',
    section: '3.2 Scope creep risk',
    prompt: 'Review Alderton bespoke tax return scope. Compare actual time, fixed fee, expected margin, open WIP, and recommend whether we need a fee adjustment before billing.',
    expected: [/Alderton|scope|WIP|margin|fee/i],
  },
  {
    id: '3-3-sgd-journal',
    section: '3.3 Multi-currency trust accounts',
    prompt: 'Prepare an SGD 18,000 dividend income journal for Alderton Trust for June 2026. Show the GBP base-currency impact, FX rate provenance, required approval role, and route it to Inbox before posting.',
    expected: [/SGD|GBP|FX|journal|Inbox/i],
  },
  {
    id: '3-4-cosec-reminders',
    section: '3.4 COSEC reminders',
    prompt: 'Review COSEC filing reminders for Alderton entities. Show upcoming filing dates, missing evidence, billing impact, and which reminders need approval before sending.',
    expected: [/COSEC|filing|Alderton|reminder/i],
  },
  {
    id: '4-1-usd-engagement',
    section: '4.1 USD-billed engagement',
    prompt: 'Explain Thornton June billing and cash position in USD and GBP. Show invoice amount, base-currency journal impact, FX rate provenance, AR status, and cash-flow effect after payment.',
    expected: [/Thornton|USD|GBP|FX|invoice/i],
  },
  {
    id: '4-2-series-a',
    section: '4.2 Series A milestone',
    prompt: 'Thornton Series A closed at $14.2M. Update the milestone amount and invoice. Route any revenue or billing change to Inbox before sending.',
    expected: [/Thornton|Series A|milestone|invoice|Inbox/i],
  },
  {
    id: '4-3-cosec-instruction',
    section: '4.3 COSEC instruction',
    attachment: 'docs/demo-assets/thornton_cosec_instruction.pdf',
    prompt: 'Review this COSEC instruction for Thornton. Identify the company change, create the required filing/project work item, identify billing impact, and route any external filing or invoice action to Inbox.',
    expected: [/Thornton|COSEC|filing|Inbox/i],
  },
  {
    id: '5-1-close-readiness',
    section: '5.1 Pre-close checklist',
    prompt: 'Run June 2026 pre-close checks. Show AR, AP, WIP, unposted journals, close tasks, missing approvals, and what needs to happen before the period can be locked.',
    expected: [/AR|AP|WIP|journal|close/i],
  },
  {
    id: '5-2-period-lock',
    section: '5.2 Period lock',
    prompt: 'Can we lock June 2026? Show the period-lock readiness result, blockers, overrides if any, and what a Controller or Owner must review before locking.',
    expected: [/lock|June 2026|blocker|ready|override/i],
  },
  {
    id: '5-3-trial-balance',
    section: '5.3 Trial Balance',
    prompt: 'Show the June 2026 Trial Balance. Confirm whether debits equal credits, summarize the largest account movements, and flag suspense or unbalanced items.',
    expected: [/Trial Balance|debit|credit|balanced|account/i],
  },
  {
    id: '5-4-management-reporting',
    section: '5.4 Management reporting',
    prompt: 'Alice is at 64% utilisation in June. Which clients have unbilled WIP tied to Alice?',
    expected: [/Alice|utili|WIP|client/i],
  },
  {
    id: '5-5-management-pack',
    section: '5.5 R2R management pack',
    prompt: 'Give me the June 2026 month-end management pack. Explain the major variances versus May 2026, show revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers. Do not post journals or lock the period.',
    expected: [/June 2026|May 2026|variance|journal|blocker/i],
  },
  {
    id: '5-5-management-drilldown',
    section: '5.5 R2R blocker drilldown',
    prompt: 'Drill into the draft journals and close task blockers for June 2026. Which ones block close, who owns them, and what should happen next?',
    expected: [/journal|task|block|owner|next/i],
  },
  {
    id: '5-5-statement-package',
    section: '5.5 Financial statement package',
    prompt: 'Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and evidence-backed management commentary. Compare it to May 2026 and show the variances.',
    expected: [/Trial Balance|Balance Sheet|Income Statement|Cash Flow|variance/i],
  },
  {
    id: '5-5-year-end',
    section: '5.5 Year-end close',
    prompt: 'Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.',
    expected: [/year-end|retained earnings|Inbox|journal|2026/i],
  },
  {
    id: '5-6-manual-journal',
    section: '5.6 Manual journal lifecycle',
    prompt: 'Review this manual journal proposal for balance, account validity, period lock status, business reason, supporting evidence, approval role, and whether the approver is different from the submitter. Do not post it without Inbox approval.',
    expected: [/journal|balance|approval|period|reason/i],
  },
  {
    id: '5-6-reversal',
    section: '5.6 Manual journal reversal',
    prompt: 'Prepare a reversal packet for this posted manual journal. Explain why reversal is appropriate, propose an open-period reversal date, show the flipped debit and credit lines, and confirm the reversal will create a new journal rather than editing the original.',
    expected: [/reversal|journal|debit|credit|new/i],
  },
  {
    id: '6-1-finance-ops-check',
    section: '6.1 Finance Ops Manager',
    prompt: "Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.",
    expected: [/billing|payment|collections|close|Inbox/i],
  },
  {
    id: '6-1-action-plan',
    section: '6.1 Finance Ops action plan',
    prompt: 'Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.',
    expected: [/finance ops|work items|Inbox|review/i],
  },
  {
    id: '6-2-scheduled-control-room',
    section: '6.2 Scheduled Finance Ops Manager',
    prompt: 'Before enabling a scheduled Finance Ops Manager run, show the current cadence, escalation windows, last run, open scheduled plans, and approval boundary for resulting work.',
    expected: [/scheduled|cadence|escalation|approval|plan/i],
  },
  {
    id: '7-1-approval-controls',
    section: '7.1 Approval policy and personas',
    prompt: 'What am I allowed to approve, what requires Owner approval, and which Inbox items are high risk? Include my finance personas, effective thresholds, pending high-risk tasks, and why each item needs review. Do not show tool names, policy reason codes, raw payloads, traces, logs, or context IDs.',
    expected: [/approve|Owner|threshold|persona|Inbox/i],
  },
  {
    id: '7-2-decision-trail',
    section: '7.2 Decision trail',
    prompt: 'Show the decision trail for the latest bill, invoice, payment batch, journal, or close record. Include the related Inbox task, actor role, decision type, timestamp, and before/after review summary.',
    expected: [/decision|Inbox|actor|timestamp|review/i],
  },
  {
    id: '7-3-operational-health',
    section: '7.3 Operational Health',
    prompt: 'Show operational health for the platform today. Include degraded health, public endpoint abuse, background failure spikes, and agent/tool/workflow failure spikes. Do not expose secrets, traces, raw logs, or stack traces.',
    expected: [/health|failure|workflow|agent|alert/i],
  },
  {
    id: '7-4-documents-audit',
    section: '7.4 Documents and source evidence',
    prompt: 'Show documents that support recent engagements, bills, invoices, journals, and Inbox decisions. For each, show the linked business record, source filename, extraction state, and what I should review next.',
    expected: [/document|source|engagement|bill|Inbox/i],
  },
  {
    id: '7-5-config-telemetry',
    section: '7.5 Configuration and telemetry',
    prompt: 'Review configuration and telemetry readiness. Show approval controls, scheduled Finance Ops Manager settings, Atlas runtime, Langfuse observability status, operational alerts, and any public abuse-path controls that need attention.',
    expected: [/approval|Finance Ops|Atlas|Langfuse|alerts/i],
  },
];

const validationRules: Record<string, ValidationRule> = {
  '1-1-engagement-letter': rule(
    [
      'Extracts the uploaded Nexus engagement letter instead of asking the user to retype it.',
      'Creates or prepares client, engagement, billing terms, rate card, and first project.',
      'Routes risky or incomplete items to Inbox.',
    ],
    [/Nexus/i, /client/i, /engagement/i, /billing|fixed|retainer|T&M|time and materials|mixed/i, /rate card|rate/i, /project/i, /Inbox|review|risk/i],
    6,
    [/don'?t have direct access|provide these details|need to know the key information/i],
  ),
  '1-2-engagement-structure': rule(
    ['Lists Nexus workstreams/projects, billing model by workstream, and missing setup before billing.'],
    [/Nexus/i, /project|workstream/i, /billing model|fixed|retainer|T&M|time and materials/i, /missing|ready|before billing|setup/i],
  ),
  '1-3-log-time': rule(
    ['Logs or prepares a 4.5 hour Nexus CFO Advisory time entry with the stated work description.'],
    [/4\.5|4\.50/i, /Nexus/i, /CFO Advisory|board pack|cash flow/i, /time|hours/i, /logged|created|Inbox|approval/i],
  ),
  '1-3a-delivery-data': rule(
    ['Summarizes Alice Chen June delivery, utilization, WIP, expenses, and invoice readiness for Nexus.'],
    [/Alice Chen|Alice/i, /June/i, /approved time|pending time|hours/i, /utili[sz]ation/i, /WIP/i, /expense/i, /invoice|invoiced/i],
    6,
  ),
  '1-4-billing-run': rule(
    ['Prepares Nexus June billing run with fixed fee, retainer, T&M hours, expenses, draft invoice lines, and Inbox routing.'],
    [/Nexus/i, /June 2026|June/i, /fixed fee/i, /retainer/i, /T&M|time and materials|hour/i, /expense/i, /invoice line|draft invoice/i, /Inbox|approval/i],
    7,
  ),
  '1-5-revenue-recognition': rule(
    ['Explains Nexus revenue recognition across milestone/fixed fee, retainer, T&M WIP, expenses, journals, and Project P&L.'],
    [/Nexus/i, /revenue/i, /fixed fee|milestone/i, /retainer/i, /T&M|WIP|time and materials/i, /expense/i, /journal/i, /Project P&L|project/i],
    7,
  ),
  '1-6-capped-tax': rule(
    ['Creates or prepares Nexus capped tax engagement with fixed fee, cap, and Inbox approval if required.'],
    [/Nexus/i, /Corporation Tax|Tax Return|FY2025/i, /18,?500|18500/i, /22,?000|22000|cap/i, /engagement/i, /Inbox|approval|created/i],
  ),
  '1-7-o2c-readiness': rule(
    ['Reviews Nexus O2C readiness across service catalogue, rate card, tax, invoices, payment links, WIP, and collections approvals.'],
    [/Nexus/i, /service catalogue|catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link|public invoice/i, /WIP/i, /collections/i],
    7,
  ),
  '1-7-collections-read': rule(
    ['Shows collections customers with balances, invoices, due dates, aging, reminders, blockers, and next action without drafting.'],
    [/customer/i, /balance/i, /invoice/i, /due date|due/i, /aging|overdue/i, /reminder/i, /blocker|blocked/i, /next action/i],
    7,
  ),
  '1-7-invoice-drilldown': rule(
    ['Reviews INV-1001 with due date, aging, balance, paid status, payment link, reminders, blockers, and next action.'],
    [/INV-1001/i, /due date|due/i, /aging|overdue/i, /balance/i, /paid|payment/i, /reminder/i, /blocker|blocked/i, /next action|recommend/i],
    7,
  ),
  '1-7-draft-reminders': rule(
    ['Drafts customer-specific reminders for invoices over 30 days overdue and routes them to Inbox before sending.'],
    [/reminder/i, /invoice/i, /30 days|overdue/i, /customer/i, /Inbox|approval/i, /draft/i],
  ),
  '2-1-retainer': rule(
    ['Prepares Brightwater monthly retainer billing with draft invoice, tax, and Inbox routing.'],
    [/Brightwater/i, /retainer/i, /June 2026|June/i, /invoice/i, /tax/i, /Inbox|approval/i],
  ),
  '2-2-milestone': rule(
    ['Prepares Brightwater Annual Accounts milestone invoice with basis, tax treatment, and approval path.'],
    [/Brightwater/i, /Annual Accounts|FY2025/i, /milestone/i, /invoice/i, /tax/i, /approval/i],
  ),
  '2-3-payroll': rule(
    ['Prepares Brightwater payroll billing from active employee count with total and approval need.'],
    [/Brightwater/i, /payroll/i, /employee/i, /count/i, /invoice|billing/i, /total/i, /approval/i],
    6,
  ),
  '2-4-vendor-invoice': rule(
    [
      'Extracts the uploaded Brightwater subcontractor invoice.',
      'Matches vendor/project, codes account, checks duplicate and PO/service-order evidence, and routes exceptions to Inbox.',
    ],
    [/Brightwater/i, /vendor|subcontractor/i, /bill|invoice/i, /project/i, /duplicate/i, /account|code/i, /PO|purchase order|service-order|service order/i, /Inbox|exception/i],
    7,
  ),
  '2-4-payment-risk-read': rule(
    ['Shows due/blocked vendor bills with evidence, duplicate risk, PO match, payment state, blockers, and next action without batching.'],
    [/vendor/i, /bill/i, /due date|due soon|overdue/i, /blocked|blocker/i, /evidence|source document/i, /duplicate/i, /PO|service order/i, /payment/i, /next action/i],
    8,
  ),
  '2-4-single-bill': rule(
    ['Reviews BILL-1001 with due date, vendor invoice number, coding, source, duplicate, approval, payment readiness, and next action.'],
    [/BILL-1001/i, /due date|due/i, /vendor invoice/i, /coding|coded|account/i, /source document|source/i, /duplicate/i, /approval/i, /payment readiness|payment/i, /next action|recommend/i],
    8,
  ),
  '2-5-bill-pay': rule(
    ['Prepares a bill-pay run for due/overdue approved bills, excludes disputed items, explains rationale, and routes batch to Inbox.'],
    [/bill-pay|payment/i, /due|overdue/i, /approved/i, /disputed|exclude/i, /rationale|reason/i, /batch/i, /Inbox|approval/i],
    6,
  ),
  '2-5-payment-packet': rule(
    ['Prepares payment approval packet with vendor, amount, due date, coding evidence, duplicate status, cash impact, and approver role.'],
    [/vendor/i, /amount/i, /due date|due/i, /coding evidence|coding/i, /duplicate/i, /cash impact|cash/i, /approver|approval role/i],
  ),
  '3-1-family-office': rule(
    ['Shows Alderton family office engagements, service lines, billing models, currency, projects, and missing setup.'],
    [/Alderton/i, /engagement/i, /service line|service/i, /billing model|fixed|retainer|T&M/i, /currency|GBP|SGD|USD/i, /project/i, /missing|setup/i],
    6,
  ),
  '3-2-scope-creep': rule(
    ['Compares Alderton bespoke tax actual time, fixed fee, expected margin, WIP, and fee adjustment recommendation.'],
    [/Alderton/i, /bespoke tax|tax return/i, /actual time|hours/i, /fixed fee/i, /margin/i, /WIP/i, /fee adjustment|recommend/i],
    6,
  ),
  '3-3-sgd-journal': rule(
    ['Prepares SGD dividend income journal with GBP impact, FX provenance, approval role, and Inbox routing before posting.'],
    [/SGD/i, /18,?000|18000/i, /dividend/i, /journal/i, /GBP/i, /FX|exchange rate/i, /approval role|approval/i, /Inbox/i],
    7,
  ),
  '3-4-cosec-reminders': rule(
    ['Reviews Alderton COSEC filing reminders, evidence gaps, billing impact, and approvals before sending.'],
    [/Alderton/i, /COSEC/i, /filing/i, /date|deadline/i, /evidence|missing/i, /billing impact|billing/i, /approval|before sending/i],
    6,
  ),
  '4-1-usd-engagement': rule(
    ['Explains Thornton June billing/cash in USD and GBP with invoice, FX provenance, AR status, and cash-flow effect.'],
    [/Thornton/i, /June/i, /USD/i, /GBP/i, /invoice/i, /FX|exchange rate/i, /AR|accounts receivable/i, /cash[- ]flow|cash flow/i],
    7,
  ),
  '4-2-series-a': rule(
    ['Updates or prepares Thornton Series A milestone invoice for $14.2M and routes revenue/billing changes to Inbox.'],
    [/Thornton/i, /Series A/i, /14\.2M|14,?200,?000|\$14\.2/i, /milestone/i, /invoice/i, /Inbox|approval/i],
  ),
  '4-3-cosec-instruction': rule(
    ['Extracts Thornton COSEC instruction, identifies company change, creates filing/project work item, billing impact, and Inbox routing.'],
    [/Thornton/i, /COSEC/i, /company change|change/i, /filing/i, /project|work item/i, /billing impact|billing/i, /Inbox|approval/i],
    6,
  ),
  '5-1-close-readiness': rule(
    ['Runs June pre-close checks across AR, AP, WIP, unposted journals, close tasks, approvals, and period-lock blockers.'],
    [/June 2026|June/i, /AR|accounts receivable/i, /AP|accounts payable/i, /WIP/i, /unposted journal|journal/i, /close task|close/i, /approval/i, /lock|period/i],
    7,
  ),
  '5-2-period-lock': rule(
    ['Assesses June 2026 period-lock readiness with blockers, overrides, and Controller/Owner review.'],
    [/June 2026/i, /lock|period/i, /readiness|ready/i, /blocker/i, /override/i, /Controller|Owner/i],
  ),
  '5-3-trial-balance': rule(
    ['Shows June 2026 Trial Balance, debit/credit balance, largest movements, and suspense/unbalanced items.'],
    [/June 2026/i, /Trial Balance/i, /debit/i, /credit/i, /balance|balanced/i, /movement|largest/i, /suspense|unbalanced/i],
    6,
  ),
  '5-4-management-reporting': rule(
    ['Identifies clients with unbilled WIP tied to Alice at 64 percent utilization.'],
    [/Alice/i, /64%|64 percent|utili[sz]ation/i, /unbilled/i, /WIP/i, /client/i],
  ),
  '5-5-management-pack': rule(
    ['Produces June management pack comparing May with variances, revenue, expenses, margins, utilization, AR/AP, journals, and blockers without posting.'],
    [/June 2026/i, /May 2026/i, /variance/i, /revenue/i, /expense/i, /margin/i, /utili[sz]ation/i, /AR|AP/i, /journal/i, /blocker/i],
    9,
  ),
  '5-5-management-drilldown': rule(
    ['Drills into draft journals and close task blockers with owner, close impact, and next action.'],
    [/draft journal|journal/i, /close task|task/i, /block|blocker/i, /owner/i, /next action|should happen/i],
  ),
  '5-5-statement-package': rule(
    ['Generates financial statement package with TB, BS, IS, cash flow, retained earnings, statutory pack, warnings, commentary, and May variance.'],
    [/Trial Balance/i, /Balance Sheet/i, /Income Statement/i, /Cash Flow/i, /Retained Earnings/i, /Statutory Pack/i, /warning|close-readiness/i, /variance|May 2026/i],
    7,
  ),
  '5-5-year-end': rule(
    ['Prepares FY2026 year-end close with retained earnings, P&L activity, locked periods, duplicate risk, statement movement, and Inbox routing.'],
    [/2026|FY2026/i, /year-end|year end/i, /retained earnings/i, /P&L|profit and loss/i, /locked period|period/i, /duplicate/i, /statement movement|prior year/i, /Inbox|approval/i],
    7,
  ),
  '5-6-manual-journal': rule(
    ['Reviews manual journal proposal for balance, account validity, period lock, reason, evidence, approval role, and segregation of duties.'],
    [/journal/i, /balance|balanced/i, /account/i, /period lock|locked period/i, /business reason|reason/i, /evidence|support/i, /approval role|approval/i, /approver.*submitter|different from submitter|segregation/i],
    7,
  ),
  '5-6-reversal': rule(
    ['Prepares reversal packet with reason, open-period date, flipped debit/credit lines, and new journal rather than editing original.'],
    [/reversal/i, /journal/i, /reason|appropriate/i, /open period|date/i, /debit/i, /credit/i, /new journal|not edit|rather than editing/i],
    6,
  ),
  '6-1-finance-ops-check': rule(
    ['Runs finance ops check separating read-only findings from Inbox-gated actions across billing, payment, collections, close, and review.'],
    [/billing/i, /payment/i, /collections/i, /close/i, /review/i, /read-only|read only/i, /Inbox|approval/i],
    6,
  ),
  '6-1-action-plan': rule(
    ['Creates at most five manager-reviewed finance ops work items and routes action plan to Inbox without approving sensitive actions.'],
    [/finance ops/i, /work item|action plan/i, /five|5|at most/i, /manager-reviewed|review/i, /Inbox|approval/i, /invoice|payment|journal|email/i],
    5,
  ),
  '6-2-scheduled-control-room': rule(
    ['Shows scheduled Finance Ops cadence, escalation windows, last run, open plans, and approval boundary before enablement.'],
    [/scheduled|cadence/i, /Finance Ops/i, /escalation/i, /last run/i, /open .*plan|scheduled plan/i, /approval boundary|approval/i],
  ),
  '7-1-approval-controls': rule(
    ['Explains approval permissions, Owner approval thresholds, high-risk Inbox items, personas, and reasons without exposing internals.'],
    [/approve|approval/i, /Owner/i, /threshold/i, /persona|role/i, /Inbox/i, /high risk|risk/i, /review/i],
    6,
    [/tool name|raw payload|trace|log|context ID|policy reason code/i],
  ),
  '7-2-decision-trail': rule(
    ['Shows decision trail with related Inbox task, actor role, decision type, timestamp, and before/after summary.'],
    [/decision/i, /Inbox/i, /actor role|role/i, /decision type|type/i, /timestamp|time/i, /before\/after|before and after|review summary/i],
  ),
  '7-3-operational-health': rule(
    ['Shows operational health with degraded status, public abuse, background failures, agent/tool/workflow failures, and no secrets/logs/traces.'],
    [/health/i, /degraded|status/i, /public endpoint|abuse/i, /background/i, /agent|tool|workflow/i, /failure|spike|alert/i],
    5,
    [/secret|raw log|stack trace|traceback/i],
  ),
  '7-4-documents-audit': rule(
    ['Shows source documents linked to engagements, bills, invoices, journals, and Inbox decisions with extraction state and next review.'],
    [/document|source/i, /engagement/i, /bill/i, /invoice/i, /journal/i, /Inbox/i, /extraction state|extracted|processing/i, /review next|next review|what .* review/i],
    7,
  ),
  '7-5-config-telemetry': rule(
    ['Reviews approval controls, scheduled Finance Ops, Atlas runtime, Langfuse observability, operational alerts, and abuse controls.'],
    [/approval controls|approval/i, /scheduled Finance Ops|Finance Ops/i, /Atlas runtime|Atlas/i, /Langfuse/i, /observability|telemetry/i, /alert/i, /abuse|public/i],
    6,
  ),
};

test.describe('Demo Guide v2 production browser validation', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('records complete Demo Guide v2 behavior on production', async ({ page }) => {
    test.setTimeout(7_200_000);
    fs.mkdirSync(SHOT_DIR, { recursive: true });
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('response', (response) => {
      if (response.status() >= 500) {
        networkFailures.push(`${response.status()} ${response.url()}`);
      }
    });
    page.on('requestfailed', (request) => {
      networkFailures.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
    });

    await authenticate(page);

    for (const [id, label, url] of routes) {
      await gotoAndRecord(page, id, label, url);
    }

    for (const step of promptSteps) {
      await sendAtlasPrompt(page, step);
      writeReport();
    }

    await gotoAndRecord(page, 'inbox-after-prompts', 'Inbox after Atlas prompts', `${WEB}/app/inbox`);
    await gotoAndRecord(page, 'documents-after-prompts', 'Documents after Atlas uploads', `${WEB}/app/documents`);
    await gotoAndRecord(page, 'workflow-runs-after-prompts', 'Settings / workflow and observability surfaces', `${WEB}/app/settings`);
    writeReport();

    const failures = evidence.filter((item) => item.status === 'FAIL');
    expect(failures, `Critical browser failures: ${failures.map((f) => f.id).join(', ')}`).toHaveLength(0);
  });
});
