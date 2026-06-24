/**
 * Demo v2 — full engagement-to-cash browser walkthrough via UI only.
 *
 * CRITICAL: ALL data is created through the browser UI exactly as a real user
 * would. No direct API calls for data creation. Auth is loaded from the saved
 * o2c-tenant.json state (skip login).
 *
 * Scenario: Nexus Consulting (Brightwater client) — T&M engagement
 *   1.  Load saved auth state (skip login)
 *   2.  Contacts  — create "Nexus Consulting" (customer)
 *   3.  People    — create "Alderton Thornton" employee (Senior Consultant, $200/hr)
 *   4.  Engagements — create T&M engagement for Nexus
 *   5.  Projects  — create project linked to the engagement
 *   6.  Time      — log billable hours via the Time Entries form
 *   7.  Copilot   — ask about active engagements; verify AI responds
 *   8.  Engagement detail — draft invoice from the engagement
 *   9.  Invoices  — list loads; approve draft; send; mark paid (where buttons exist)
 *  10.  Inbox     — renders (HITL cards visible if any)
 *  11.  Bills     — bills list renders
 *  12.  Billing Runs — AP Pay Bills stepper renders
 *  13.  Reports   — all 6 tabs (AR Aging, AP Aging, Project P&L, Utilization, WIP, Revenue, Trial Balance)
 *  14.  Accounting/Journals — list renders; post a manual adjustment journal
 *
 * For each form: screenshot before submit. Gap findings are documented inline.
 *
 * Run headless (no display):
 *   cd frontend && npx playwright test e2e/demo-v2-full-scenario.spec.ts --reporter=list
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

// ─── Config ───────────────────────────────────────────────────────────────────

const WEB = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';
const AUTH_STATE      = path.join(__dirname, '.auth', 'o2c-tenant.json');
const AUTH_META       = path.join(__dirname, '.auth', 'o2c-tenant.meta.json');

const RUN_ID = Date.now().toString().slice(-6);

// ─── Auth helpers ─────────────────────────────────────────────────────────────

/** Returns true if the saved JWT is still valid (expiry > now + 60s). */
function authTokenValid(): boolean {
  if (!fs.existsSync(AUTH_STATE)) return false;
  try {
    const state = JSON.parse(fs.readFileSync(AUTH_STATE, 'utf-8'));
    for (const origin of state.origins ?? []) {
      for (const ls of origin.localStorage ?? []) {
        if (ls.name?.endsWith('-auth-token')) {
          const token = JSON.parse(ls.value)?.access_token ?? '';
          if (!token) continue;
          const parts = token.split('.');
          if (parts.length !== 3) continue;
          const payload = Buffer.from(parts[1], 'base64').toString('utf-8');
          const { exp } = JSON.parse(payload);
          return exp > Date.now() / 1000 + 60;
        }
      }
    }
  } catch { /* */ }
  return false;
}

/** Reads login credentials from the meta.json file beside o2c-tenant.json. */
function readCreds(): { email: string; password: string } | null {
  if (!fs.existsSync(AUTH_META)) return null;
  try {
    const meta = JSON.parse(fs.readFileSync(AUTH_META, 'utf-8'));
    if (meta.email && meta.password) return { email: meta.email, password: meta.password };
  } catch { /* */ }
  return null;
}

async function loginViaUi(page: Page): Promise<void> {
  const creds = readCreds();
  if (!creds) {
    throw new Error('Saved auth expired and no credentials were found in o2c-tenant.meta.json.');
  }

  await page.goto(`${WEB}/login`, { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible({ timeout: 15_000 });
  await page.fill('#email', creds.email);
  await page.fill('#password', creds.password);
  await shot(page, '01a-login-filled');
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/app\//, { timeout: 30_000 });
}

// Demo v2 data — distinctive names so they stand out in the UI
const CONTACT_NAME  = `Nexus Consulting ${RUN_ID}`;
const EMP_FIRST     = 'Alderton';
const EMP_LAST      = `Thornton${RUN_ID}`;
const EMP_EMAIL     = `alderton.thornton.${RUN_ID}@nexusconsulting.com`;
const ENG_NAME      = `Brightwater Advisory ${RUN_ID}`;
const PROJ_NAME     = `Brightwater Phase 1 ${RUN_ID}`;

// ─── Screenshot helpers ────────────────────────────────────────────────────────

const SHOT_DIR = `test-results/demo-v2-${RUN_ID}`;
fs.mkdirSync(SHOT_DIR, { recursive: true });

async function shot(page: Page, name: string): Promise<void> {
  await page.screenshot({
    path: `${SHOT_DIR}/${name}.png`,
    fullPage: false,
  });
}

/** Wait for Angular/Material loading spinners / aria-busy to clear. */
async function settled(page: Page, timeout = 20_000): Promise<void> {
  // Angular skeleton loaders use aria-busy="true"
  await page
    .locator('[aria-busy="true"]')
    .waitFor({ state: 'hidden', timeout })
    .catch(() => {
      /* not present — fine */
    });
}

/** Wait until the top nav bar (Engagements link) is visible — confirms the SPA shell loaded. */
async function navReady(page: Page): Promise<void> {
  await expect(
    page.getByRole('link', { name: 'Engagements' }),
  ).toBeVisible({ timeout: 20_000 });
}

// ─── Gap tracker ──────────────────────────────────────────────────────────────

interface GapFinding {
  screen: string;
  finding: string;
}

const gaps: GapFinding[] = [];

function noteGap(screen: string, finding: string, page: Page): void {
  const msg = `[GAP] ${screen}: ${finding}`;
  gaps.push({ screen, finding });
  test.info().annotations.push({ type: 'gap', description: msg });
  console.warn(msg);
}

// ─── Suite ────────────────────────────────────────────────────────────────────

test.describe('Demo v2 — full UI-driven engagement-to-cash walkthrough', () => {
  // If the saved auth token is still valid, skip login; otherwise use empty session
  // and log in during step 1.
  test.use({
    storageState: authTokenValid()
      ? AUTH_STATE
      : { cookies: [], origins: [] },
  });

  test('complete demo v2 scenario in one browser session', async ({ page }) => {
    test.setTimeout(480_000); // 8 min — generous for a full walkthrough

    // ── 1. Login or verify app loads with saved auth ──────────────────────
    await test.step('1. Login (or verify saved auth state)', async () => {
      await page.goto(`${WEB}/app/copilot`, { waitUntil: 'domcontentloaded' });

      const shellReady = await page
        .getByRole('link', { name: 'Engagements' })
        .isVisible({ timeout: 8_000 })
        .catch(() => false);

      if (!shellReady) {
        await loginViaUi(page);
      }

      await navReady(page);
      await shot(page, '01-app-loaded');
    });

    // ── 2. Contacts — create "Nexus Consulting" ───────────────────────────
    await test.step('2. Contacts — create Nexus Consulting (customer)', async () => {
      await page.goto(`${WEB}/app/clients`, { waitUntil: 'domcontentloaded' });

      // Heading should say "Contacts" (renamed in #201)
      const heading = page.getByRole('heading', { level: 1 });
      await expect(heading).toBeVisible({ timeout: 15_000 });
      const headingText = await heading.textContent();
      if (!/contacts/i.test(headingText ?? '')) {
        noteGap('Contacts', `H1 says "${headingText}" — expected "Contacts" after #201 rename`, page);
      }

      await settled(page);
      await shot(page, '02-contacts-list');

      // Open the create panel
      const newBtn = page.getByRole('button', { name: /new contact/i }).first();
      const altBtn = page.getByLabel('Create new contact');
      const createBtn = await newBtn.isVisible({ timeout: 5_000 }).catch(() => false)
        ? newBtn
        : altBtn;
      await createBtn.click();

      // Panel should slide in — identified by the aside dialog element
      await expect(
        page.locator('[aria-labelledby="create-contact-title"]'),
      ).toBeVisible({ timeout: 10_000 });

      // -- Observe form fields before filling --
      await shot(page, '03-contact-form-empty');

      // Check for missing fields (industry, website, phone — demo guide may need these)
      const hasWebsite = await page.locator('#contact-website, [formcontrolname="website"]').isVisible({ timeout: 2_000 }).catch(() => false);
      const hasPhone   = await page.locator('#contact-phone, [formcontrolname="phone"]').isVisible({ timeout: 2_000 }).catch(() => false);
      if (!hasWebsite) noteGap('Contacts/create', 'No "Website" field — demo may need it for Nexus Consulting profile', page);
      if (!hasPhone)   noteGap('Contacts/create', 'No "Phone" field — demo may need it for contact detail', page);

      // Fill: Name
      await page.locator('#client-name, #contact-name, [formcontrolname="name"]').fill(CONTACT_NAME);

      // Fill: Kind = customer
      const kindSelect = page.locator('#client-kind, #contact-kind, [formcontrolname="kind"]');
      if (await kindSelect.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await kindSelect.selectOption('customer');
      }
      if (hasPhone) {
        await page.locator('#contact-phone, [formcontrolname="phone"]').fill('+1 555 0188');
      }
      if (hasWebsite) {
        await page.locator('#contact-website, [formcontrolname="website"]').fill('https://nexus-consulting.example');
      }

      await shot(page, '04-contact-form-filled');

      // Submit
      await page.getByRole('button', { name: /create contact/i }).click();

      // Contact should appear in the list
      await expect(page.getByText(CONTACT_NAME)).toBeVisible({ timeout: 15_000 });
      await shot(page, '05-contact-created');
    });

    // ── 3. People — create Alderton Thornton (Senior Consultant, $200/hr) ──
    await test.step('3. People — create employee Alderton Thornton', async () => {
      await page.goto(`${WEB}/app/people`, { waitUntil: 'domcontentloaded' });

      await navReady(page);
      await settled(page);
      await shot(page, '06-people-list');

      // Open create panel — button label is "Add new employee" (aria-label) or text "New employee"
      const addBtn = page.getByLabel('Add new employee')
        .or(page.getByRole('button', { name: /new employee/i }))
        .first();
      await expect(addBtn).toBeVisible({ timeout: 10_000 });
      await addBtn.click();

      // Panel slides in — identified by aria-labelledby (aside dialog)
      await expect(
        page.locator('[aria-labelledby="emp-panel-title"]'),
      ).toBeVisible({ timeout: 10_000 });

      await shot(page, '07-employee-form-empty');

      // Check for missing fields relevant to demo guide (practice area, seniority)
      const hasPracticeArea = await page.locator('[formcontrolname="practice_area"], #practice-area').isVisible({ timeout: 2_000 }).catch(() => false);
      const hasSeniority    = await page.locator('[formcontrolname="seniority"], #seniority').isVisible({ timeout: 2_000 }).catch(() => false);
      if (!hasPracticeArea) noteGap('People/create', 'No "Practice area" field — demo guide v2 needs Consulting / Advisory service lines', page);
      if (!hasSeniority)    noteGap('People/create', 'No "Seniority" field — useful for rate cards', page);

      // Fill the form using formControlName selectors (no id on most fields)
      await page.locator('[formcontrolname="first_name"]').fill(EMP_FIRST);
      await page.locator('[formcontrolname="last_name"]').fill(EMP_LAST);
      await page.locator('[formcontrolname="email"]').fill(EMP_EMAIL);
      await page.locator('[formcontrolname="title"]').fill('Senior Consultant');
      await page.locator('[formcontrolname="employment_type"]').selectOption('full_time');
      if (hasPracticeArea) {
        await page.locator('[formcontrolname="practice_area"]').selectOption('advisory');
      }
      if (hasSeniority) {
        await page.locator('[formcontrolname="seniority"]').selectOption('senior');
      }
      await page.locator('[formcontrolname="default_bill_rate"]').fill('200');
      await page.locator('[formcontrolname="default_bill_rate_currency"]').fill('USD');

      await shot(page, '08-employee-form-filled');

      // Click Create employee — wait for the button to be enabled first
      const createEmpBtn = page.getByRole('button', { name: /create employee/i });
      await expect(createEmpBtn).toBeEnabled({ timeout: 5_000 });
      await createEmpBtn.click();

      // Panel should close on success (closePanel called in next callback)
      const panel = page.locator('[aria-labelledby="emp-panel-title"]');
      const panelClosed = await panel
        .waitFor({ state: 'hidden', timeout: 15_000 })
        .then(() => true)
        .catch(() => false);

      if (!panelClosed) {
        // Panel still open — check for error message
        const panelErr = page.locator('[role="alert"]');
        if (await panelErr.isVisible({ timeout: 2_000 }).catch(() => false)) {
          const errText = await panelErr.textContent();
          noteGap('People/create', `Employee creation error: ${errText}`, page);
        }
        // Force close to continue the test
        await page.getByRole('button', { name: /cancel/i }).click();
      }

      await shot(page, '09-employee-created');

      // Employee should appear in the list — either full name or just first name
      const empInList = page.getByText(`${EMP_FIRST} ${EMP_LAST}`).or(page.getByText(EMP_FIRST)).first();
      if (panelClosed) {
        // Panel closed means save succeeded — verify the employee appears
        await expect(empInList).toBeVisible({ timeout: 10_000 });
      } else {
        // If creation failed, note it but continue
        noteGap('People/create', `Employee panel did not close after "Create employee" click — save may have failed`, page);
      }
    });

    // ── 4. Engagements — create T&M engagement for Nexus ─────────────────
    await test.step('4. Engagements — create T&M engagement for Nexus Consulting', async () => {
      await page.goto(`${WEB}/app/engagements`, { waitUntil: 'domcontentloaded' });

      await expect(
        page.getByRole('heading', { name: /engagements/i, level: 1 }),
      ).toBeVisible({ timeout: 15_000 });
      await settled(page);
      await shot(page, '10-engagements-list');

      // Check for missing fields on engagement form before opening
      // (we'll note during form open)
      await page
        .getByRole('button', { name: /new engagement|create.*engagement/i })
        .first()
        .click();

      await expect(
        page.getByRole('heading', { name: /new engagement/i }),
      ).toBeVisible({ timeout: 10_000 });

      await shot(page, '11-engagement-form-empty');

      // Check for missing fields: service line, start/end date, default rate card
      const hasServiceLine  = await page.locator('#eng-service-line, [formcontrolname="service_line"]').isVisible({ timeout: 2_000 }).catch(() => false);
      const hasStartDate    = await page.locator('#eng-start-date, [formcontrolname="start_date"]').isVisible({ timeout: 2_000 }).catch(() => false);
      const hasEndDate      = await page.locator('#eng-end-date, [formcontrolname="end_date"]').isVisible({ timeout: 2_000 }).catch(() => false);
      const hasRateCard     = await page.locator('#eng-rate-card, [formcontrolname="rate_card_id"]').isVisible({ timeout: 2_000 }).catch(() => false);

      if (!hasServiceLine) noteGap('Engagements/create', 'No "Service line" field — demo guide v2 needs Advisory / Consulting / Tax service lines', page);
      if (!hasStartDate)   noteGap('Engagements/create', 'No "Start date" field — engagement duration not captured at create time', page);
      if (!hasEndDate)     noteGap('Engagements/create', 'No "End date" field — engagement duration not captured at create time', page);
      if (!hasRateCard)    noteGap('Engagements/create', 'No "Rate card" field — no way to attach rate card at engagement creation', page);

      // Fill engagement form
      await page.locator('#eng-name').fill(ENG_NAME);

      // Wait for client options to load, then select Nexus Consulting
      await page
        .locator('#eng-client option:not([value=""])')
        .first()
        .waitFor({ state: 'attached', timeout: 10_000 });

      // Select by label text
      const clientValue = await page.evaluate(
        (name: string) => {
          const sel = document.querySelector('#eng-client') as HTMLSelectElement | null;
          if (!sel) return '';
          for (const opt of Array.from(sel.options)) {
            if (opt.text.includes(name)) return opt.value;
          }
          return '';
        },
        CONTACT_NAME,
      );
      if (clientValue) {
        await page.locator('#eng-client').selectOption({ value: clientValue });
      } else {
        // Fallback: pick first non-empty option
        const firstOpt = await page
          .locator('#eng-client option:not([value=""])')
          .first()
          .getAttribute('value');
        if (firstOpt) await page.locator('#eng-client').selectOption({ value: firstOpt });
        noteGap('Engagements/create', `Could not find "${CONTACT_NAME}" in client dropdown — freshly created contact may not appear until page reload`, page);
      }

      await page.locator('#eng-billing').selectOption('time_and_materials');
      await page.locator('#eng-currency').selectOption('USD');
      if (hasServiceLine) {
        await page.locator('#eng-service-line, [formcontrolname="service_line"]').selectOption('advisory');
      }
      const totalValueInput = page.locator('#eng-total-value, [formcontrolname="total_value"]');
      if (await totalValueInput.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await totalValueInput.fill('48000');
      }
      if (hasStartDate) {
        await page.locator('#eng-start-date, [formcontrolname="start_date"]').fill(new Date().toISOString().split('T')[0]);
      }
      if (hasEndDate) {
        const endDate = new Date();
        endDate.setMonth(endDate.getMonth() + 6);
        await page.locator('#eng-end-date, [formcontrolname="end_date"]').fill(endDate.toISOString().split('T')[0]);
      }

      await shot(page, '12-engagement-form-filled');

      await page.getByRole('button', { name: /create engagement/i }).click();
      await expect(page.getByText(ENG_NAME)).toBeVisible({ timeout: 15_000 });
      await shot(page, '13-engagement-created');
    });

    // ── 5. Projects — create project linked to the engagement ─────────────
    let engagementUrl = '';
    await test.step('5. Projects — create Brightwater Phase 1 project', async () => {
      await page.goto(`${WEB}/app/projects`, { waitUntil: 'domcontentloaded' });

      await navReady(page);
      await settled(page);
      await shot(page, '14-projects-list');

      // Open create project panel
      await page
        .getByRole('button', { name: /new project/i })
        .or(page.getByLabel('Create new project'))
        .first()
        .click();

      // Wait for the project panel dialog to appear
      await expect(
        page.locator('[aria-labelledby="create-project-title"]'),
      ).toBeVisible({ timeout: 10_000 });

      await shot(page, '15-project-form-empty');

      // Check for missing fields
      const hasBudgetHours  = await page.locator('#ps-budget-hours, [formcontrolname="budget_hours"]').isVisible({ timeout: 2_000 }).catch(() => false);
      const hasBudgetAmount = await page.locator('#ps-budget, [formcontrolname="budget"], [formcontrolname="budget_amount"]').isVisible({ timeout: 2_000 }).catch(() => false);
      if (!hasBudgetHours)  noteGap('Projects/create', 'No "Budget hours" field — utilization reporting will lack baseline', page);
      if (!hasBudgetAmount) noteGap('Projects/create', 'No "Budget amount" field — Project P&L has no budget line', page);

      // Fill: Name — works for both projects-list (#proj-name) and projects-standalone (#ps-name)
      const nameInput = page.locator('#proj-name, #ps-name').first();
      await nameInput.fill(PROJ_NAME);

      // Engagement select — id is either proj-engagement or ps-engagement
      const engSelect = page.locator('#proj-engagement, #ps-engagement').first();
      const engOptLoaded = await engSelect
        .locator('option:not([value=""])')
        .first()
        .waitFor({ state: 'attached', timeout: 10_000 })
        .then(() => true)
        .catch(() => false);

      if (engOptLoaded) {
        const engValue = await page.evaluate(
          (name: string) => {
            const sel =
              (document.querySelector('#proj-engagement') as HTMLSelectElement | null) ??
              (document.querySelector('#ps-engagement') as HTMLSelectElement | null);
            if (!sel) return '';
            for (const opt of Array.from(sel.options)) {
              if (opt.text.includes(name)) return opt.value;
            }
            return '';
          },
          ENG_NAME,
        );
        if (engValue) {
          await engSelect.selectOption({ value: engValue });
        } else {
          const firstVal = await engSelect
            .locator('option:not([value=""])')
            .first()
            .getAttribute('value');
          if (firstVal) await engSelect.selectOption({ value: firstVal });
          noteGap('Projects/create', `Could not find engagement "${ENG_NAME}" in dropdown — auto-created General project may already exist`, page);
        }
      }

      if (hasBudgetAmount) {
        await page.locator('#ps-budget, [formcontrolname="budget"], [formcontrolname="budget_amount"]').first().fill('24000');
      }
      if (hasBudgetHours) {
        await page.locator('#ps-budget-hours, [formcontrolname="budget_hours"]').first().fill('120');
      }

      await shot(page, '16-project-form-filled');

      await page.getByRole('button', { name: /create project/i }).click();
      await expect(page.getByText(PROJ_NAME)).toBeVisible({ timeout: 15_000 });
      await shot(page, '17-project-created');
    });

    // ── 6. Time Entries — log billable hours ──────────────────────────────
    await test.step('6. Time Entries — log 8h billable hours for Alderton Thornton', async () => {
      await page.goto(`${WEB}/app/time`, { waitUntil: 'domcontentloaded' });

      await navReady(page);
      await settled(page);
      await shot(page, '18-time-entries-list');

      // Check for missing prereq warnings
      const missingMsg = page.getByText(/please create.*first|no projects|no employees/i);
      if (await missingMsg.isVisible({ timeout: 3_000 }).catch(() => false)) {
        noteGap('Time Entries', 'Missing prereq warning shown — project or employee not loaded yet', page);
      }

      // Quick-add form
      const formRegion = page.getByRole('region', { name: /add time entry/i });
      await expect(formRegion).toBeVisible({ timeout: 10_000 });

      // Project select
      const projSelect = page.locator('#entry-project');
      if (await projSelect.isVisible({ timeout: 5_000 }).catch(() => false)) {
        const projOptLoaded = await projSelect
          .locator('option:not([value=""])')
          .first()
          .waitFor({ state: 'attached', timeout: 10_000 })
          .then(() => true)
          .catch(() => false);

        if (projOptLoaded) {
          const projValue = await page.evaluate(
            (name: string) => {
              const sel = document.querySelector('#entry-project') as HTMLSelectElement | null;
              if (!sel) return '';
              for (const opt of Array.from(sel.options)) {
                if (opt.text.includes(name)) return opt.value;
              }
              return '';
            },
            PROJ_NAME,
          );
          if (projValue) {
            await projSelect.selectOption({ value: projValue });
          } else {
            // Fall back to first available project
            const firstVal = await projSelect
              .locator('option:not([value=""])')
              .first()
              .getAttribute('value');
            if (firstVal) await projSelect.selectOption({ value: firstVal });
            noteGap('Time Entries', `Project "${PROJ_NAME}" not found in dropdown — may need page reload`, page);
          }
        }
      }

      // Employee select
      const empSelect = page.locator('#entry-employee');
      if (await empSelect.isVisible({ timeout: 5_000 }).catch(() => false)) {
        const empOptLoaded = await empSelect
          .locator('option:not([value=""])')
          .first()
          .waitFor({ state: 'attached', timeout: 10_000 })
          .then(() => true)
          .catch(() => false);

        if (empOptLoaded) {
          const empValue = await page.evaluate(
            (last: string) => {
              const sel = document.querySelector('#entry-employee') as HTMLSelectElement | null;
              if (!sel) return '';
              for (const opt of Array.from(sel.options)) {
                if (opt.text.includes(last)) return opt.value;
              }
              return '';
            },
            EMP_LAST,
          );
          if (empValue) {
            await empSelect.selectOption({ value: empValue });
          } else {
            // Fall back to first option
            const firstVal = await empSelect
              .locator('option:not([value=""])')
              .first()
              .getAttribute('value');
            if (firstVal) await empSelect.selectOption({ value: firstVal });
            noteGap('Time Entries', `Employee "${EMP_FIRST} ${EMP_LAST}" not found in dropdown — may need page reload`, page);
          }
        }
      }

      const today = new Date().toISOString().split('T')[0];
      await page.locator('#entry-date').fill(today);
      await page.locator('#entry-hours').fill('8');
      await page.locator('#entry-description').fill('Brightwater — initial discovery and stakeholder interviews');

      await shot(page, '19-time-entry-form-filled');

      await page.getByRole('button', { name: /add time entry/i }).click();

      // Entry appears in the list
      await expect(
        page.getByText(/brightwater.*discovery|discovery.*brightwater/i).first(),
      ).toBeVisible({ timeout: 15_000 });
      await shot(page, '20-time-entry-created');
    });

    // ── 7. Copilot — ask about active engagements ─────────────────────────
    await test.step('7. Copilot — send query, verify AI responds', async () => {
      await page.goto(`${WEB}/app/copilot`, { waitUntil: 'domcontentloaded' });

      const copilotReady = page
        .getByRole('button', { name: /new chat/i })
        .or(page.getByPlaceholder(/message aethos/i));
      await expect(copilotReady.first()).toBeVisible({ timeout: 20_000 });
      await shot(page, '21-copilot-fresh');

      // Start a new chat if needed
      const newChatBtn = page.getByRole('button', { name: /new chat/i });
      if (await newChatBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await newChatBtn.click();
        await expect(
          page.getByPlaceholder(/message aethos/i),
        ).toBeVisible({ timeout: 10_000 });
      }

      const composer = page.getByPlaceholder(/message aethos/i);
      await expect(composer).toBeVisible({ timeout: 10_000 });
      await composer.fill(
        `I just created a T&M engagement called "${ENG_NAME}" for Nexus Consulting. How many active engagements does the firm have right now?`,
      );
      await shot(page, '22-copilot-query');

      await page.keyboard.press('Enter');

      // Wait for assistant reply or visible tool progress. Some local runs have
      // LLM/tool dependencies disabled, so record that as a demo gap instead
      // of failing the rest of the walkthrough.
      const assistantOutput = page
        .locator('[aria-label^="Aethos:"], [aria-label^="Tool completed"], [aria-label^="Running tool"]')
        .last();
      if (!(await assistantOutput.isVisible({ timeout: 60_000 }).catch(() => false))) {
        noteGap('Copilot', 'No assistant response or tool output visible after query', page);
      }

      await shot(page, '23-copilot-response');

      // Check for missing copilot features (time logging via chat)
      const logTimeBtn = page.getByRole('button', { name: /log time/i });
      if (!(await logTimeBtn.isVisible({ timeout: 2_000 }).catch(() => false))) {
        noteGap('Copilot', 'No "Log time" quick-action button — demo guide v2 shows logging time via chat', page);
      }
    });

    // ── 8. Engagement detail — draft invoice ──────────────────────────────
    let createdInvoiceHref = '';
    await test.step('8. Engagement detail — navigate and draft an invoice', async () => {
      await page.goto(`${WEB}/app/engagements`, { waitUntil: 'domcontentloaded' });
      await settled(page);

      // Click the engagement row for ENG_NAME
      const engRow = page
        .getByText(ENG_NAME)
        .first();
      await expect(engRow).toBeVisible({ timeout: 10_000 });
      await engRow.click();

      // Navigate to engagement detail URL
      await page.waitForURL(/\/app\/engagements\/[0-9a-f-]+/, { timeout: 15_000 });
      await settled(page);
      await shot(page, '24-engagement-detail');

      // Check for missing engagement detail fields
      const hasBudgetSummary = await page.getByText(/budget|total value/i).first().isVisible({ timeout: 3_000 }).catch(() => false);
      const hasServiceLine   = await page.getByText(/service line/i).first().isVisible({ timeout: 3_000 }).catch(() => false);
      if (!hasBudgetSummary) noteGap('Engagement detail', 'No budget/total value summary visible on detail page', page);
      if (!hasServiceLine)   noteGap('Engagement detail', 'No service line displayed', page);

      // Draft invoice button
      const draftInvBtn = page.getByRole('button', { name: /draft.*invoice|create.*invoice/i });
      if (await draftInvBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await draftInvBtn.click();

        // Drawer/panel opens
        // Wait for the invoice drawer to appear (identified by dialog role)
        await expect(
          page.getByRole('dialog', { name: /draft invoice/i }),
        ).toBeVisible({ timeout: 10_000 });

        await shot(page, '25-draft-invoice-form');

        // Fill dates
        const today = new Date();
        const due   = new Date(today);
        due.setDate(today.getDate() + 30);
        const fmt = (d: Date) => d.toISOString().split('T')[0];

        const issueDateInput = page.locator('#inv-issue-date');
        const dueDateInput   = page.locator('#inv-due-date');
        if (await issueDateInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
          await issueDateInput.fill(fmt(today));
        }
        if (await dueDateInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
          await dueDateInput.fill(fmt(due));
        }

        // Optional extra line toggle
        const extraToggle = page.locator('input[name="inv-extra-on"]');
        if (await extraToggle.isVisible({ timeout: 2_000 }).catch(() => false)) {
          await extraToggle.check();
          const descInput  = page.locator('[name="inv-extra-desc"]');
          const qtyInput   = page.locator('[name="inv-extra-qty"]');
          const priceInput = page.locator('[name="inv-extra-price"]');
          await descInput.click();
          await descInput.pressSequentially('Brightwater kickoff workshop');
          await qtyInput.click({ clickCount: 3 });
          await qtyInput.pressSequentially('1');
          await priceInput.click({ clickCount: 3 });
          await priceInput.pressSequentially('1600');
          await priceInput.press('Tab');
        }

        await shot(page, '26-draft-invoice-filled');

        await page.getByRole('button', { name: /create draft invoice/i }).click();

        // Drawer closes
        await expect(
          page.getByRole('heading', { name: /draft invoice/i }),
        ).toBeHidden({ timeout: 20_000 });
        await shot(page, '27-invoice-drafted');
      } else {
        noteGap('Engagement detail', 'No "Draft invoice" button found on engagement detail page', page);
        await shot(page, '24b-no-draft-invoice-btn');
      }
    });

    // ── 9. Invoices — list, approve, send, mark paid ─────────────────────
    await test.step('9a. Invoices — list renders with Invoices table', async () => {
      await page.goto(`${WEB}/app/invoices`, { waitUntil: 'domcontentloaded' });

      await expect(
        page.getByRole('heading', { name: /^invoices$/i, level: 1 }),
      ).toBeVisible({ timeout: 15_000 });
      await settled(page);
      await shot(page, '28-invoices-list');

      // Table must be visible
      const invTable = page.locator('table[aria-label="Invoices"]');
      await expect(invTable).toBeVisible({ timeout: 10_000 });

      // Check for missing columns
      const hasClientCol = await invTable.getByText(/client|customer/i).isVisible({ timeout: 3_000 }).catch(() => false);
      if (!hasClientCol) noteGap('Invoices list', 'No "Client" column visible in invoices table', page);
    });

    await test.step('9b. Invoices — approve draft invoice', async () => {
      // Approve buttons appear in-row on the list
      const approveBtn = page.locator('button').filter({ hasText: /^approve/i }).first();
      if (await approveBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await approveBtn.click();
        await expect(
          page.getByText(/approved/i).first(),
        ).toBeVisible({ timeout: 15_000 });
        await shot(page, '29-invoice-approved');
      } else {
        test.info().annotations.push({
          type: 'info',
          description: 'No "Approve" button visible in invoice list — may need to open invoice detail.',
        });
        await shot(page, '29-no-approve-btn');

        // Try navigating to the first invoice detail
        const firstInvLink = page
          .locator('table[aria-label="Invoices"] tbody tr')
          .first()
          .getByRole('link');
        if (await firstInvLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
          await firstInvLink.click();
          await page.waitForURL(/\/app\/invoices\//, { timeout: 10_000 });
          await shot(page, '29b-invoice-detail');

          const approveDetailBtn = page.getByRole('button', { name: /approve/i });
          if (await approveDetailBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
            await approveDetailBtn.click();
            await expect(page.getByText(/approved/i)).toBeVisible({ timeout: 15_000 });
            await shot(page, '29c-invoice-approved-detail');
          }
          await page.goto(`${WEB}/app/invoices`);
        }
      }
    });

    await test.step('9c. Invoices — send approved invoice', async () => {
      await page.reload();
      await settled(page);
      const sendBtn = page.locator('button').filter({ hasText: /^send/i }).first();
      if (await sendBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await sendBtn.click();
        await expect(sendBtn).toBeHidden({ timeout: 10_000 }).catch(() => {
          // Send may open a confirmation dialog
        });
        await shot(page, '30-invoice-sent');
      } else {
        test.info().annotations.push({
          type: 'info',
          description: 'No "Send" button visible — invoice may not be in approved state or Stripe Connect not configured.',
        });
      }
    });

    await test.step('9d. Invoices — mark as paid', async () => {
      await page.reload();
      await settled(page);

      const paidBtn = page
        .locator('button')
        .filter({ hasText: /mark paid|record payment/i })
        .first();
      if (await paidBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await paidBtn.click();

        // Dialog may appear
        const dialogHeading = page.getByRole('heading', { name: /mark.*paid|record payment/i });
        if (await dialogHeading.isVisible({ timeout: 5_000 }).catch(() => false)) {
          const payInput = page.locator('#pay-amount');
          const curVal = await payInput.inputValue().catch(() => '');
          if (!curVal || curVal === '0') await payInput.fill('1600.00');

          const payDate = page.locator('#pay-date');
          if (await payDate.isVisible({ timeout: 2_000 }).catch(() => false)) {
            await payDate.fill(new Date().toISOString().split('T')[0]);
          }

          await shot(page, '31-mark-paid-dialog');
          await page.getByRole('button', { name: /record payment|confirm|save/i }).last().click();
          await expect(page.getByText(/paid/i).first()).toBeVisible({ timeout: 15_000 });
          await shot(page, '32-invoice-paid');
        }
      } else {
        test.info().annotations.push({
          type: 'info',
          description: 'No "Mark paid" button — invoice not yet in "sent" state.',
        });
      }
    });

    // ── 10. Inbox — HITL cards ────────────────────────────────────────────
    await test.step('10. Inbox — renders (HITL cards visible if any)', async () => {
      await page.goto(`${WEB}/app/inbox`, { waitUntil: 'domcontentloaded' });
      await navReady(page);
      await settled(page);
      await shot(page, '33-inbox');

      // The inbox should have an h1 or identifiable heading
      const inboxHeading = page.getByRole('heading', { name: /inbox|tasks|approvals/i });
      if (!(await inboxHeading.isVisible({ timeout: 5_000 }).catch(() => false))) {
        noteGap('Inbox', 'No clear heading on the inbox page — hard to identify section', page);
      }
    });

    // ── 11. Bills — bills list renders ────────────────────────────────────
    await test.step('11. Bills — bills list renders', async () => {
      await page.goto(`${WEB}/app/bills`, { waitUntil: 'domcontentloaded' });
      await navReady(page);
      await settled(page);
      await shot(page, '34-bills-list');

      const billsHeading = page.getByRole('heading', { name: /bills|vendor bills|payables/i });
      if (!(await billsHeading.isVisible({ timeout: 5_000 }).catch(() => false))) {
        noteGap('Bills', 'No clear heading on the bills page', page);
      }

      // Check for "New bill" / manual entry option
      const newBillBtn = page.getByRole('button', { name: /new bill|create bill|add bill/i });
      if (!(await newBillBtn.isVisible({ timeout: 3_000 }).catch(() => false))) {
        noteGap('Bills', 'No "New bill" button — manual bill entry not available; only Copilot upload works', page);
      }
    });

    // ── 12. Billing Runs — AP Pay Bills stepper ───────────────────────────
    await test.step('12. Billing Runs — AP Pay Bills stepper renders', async () => {
      await page.goto(`${WEB}/app/billing-runs`, { waitUntil: 'domcontentloaded' });

      const billsHeading = page.getByRole('heading', { name: /pay bills|billing runs/i });
      await expect(billsHeading).toBeVisible({ timeout: 15_000 });

      // Stepper or any recognizable content must appear
      const stepperOrContent = page.locator('mat-stepper, [class*="stepper"]').first();
      const hasStepperOrContent = await stepperOrContent.isVisible({ timeout: 15_000 }).catch(() => false);
      if (!hasStepperOrContent) {
        const payBillsContent = page
          .getByRole('heading', { name: /pay bills/i })
          .or(page.getByText(/select bills|no approved bills|failed to load approved bills|run billing/i).first());
        await expect(payBillsContent.first()).toBeVisible({ timeout: 5_000 });
      }
      await shot(page, '35-billing-runs');

      // Check for missing "New billing run" option
      const newRunBtn = page.getByRole('button', { name: /new.*run|create.*run|run billing/i });
      if (!(await newRunBtn.isVisible({ timeout: 3_000 }).catch(() => false))) {
        noteGap('Billing Runs', 'No "New billing run" / "Run billing" button — cannot initiate retainer billing from this page', page);
      }
    });

    // ── 13. Reports — all tabs render ─────────────────────────────────────
    await test.step('13. Reports — all 7 tabs render without errors', async () => {
      await page.goto(`${WEB}/app/reports`, { waitUntil: 'domcontentloaded' });

      await expect(
        page.getByRole('heading', { name: /^reports$/i }),
      ).toBeVisible({ timeout: 15_000 });
      await settled(page);
      await shot(page, '36-reports-ar-aging');

      const tabs = [
        'AR Aging',
        'AP Aging',
        'Project P&L',
        'Utilization',
        'WIP',
        'Revenue',
        'Trial Balance',
      ];

      for (const tabLabel of tabs) {
        const tabBtn = page.getByRole('tab', { name: tabLabel });
        if (await tabBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
          await tabBtn.click();
          // Wait for any loading to settle
          await settled(page, 10_000);
          await shot(page, `37-reports-${tabLabel.toLowerCase().replace(/[^a-z0-9]/g, '-')}`);

          const tabHasSuccessSurface = tabLabel === 'Trial Balance'
            && await page.locator('table[aria-label="Trial Balance"]').isVisible({ timeout: 1_000 }).catch(() => false)
            && await page.getByText(/balanced/i).first().isVisible({ timeout: 1_000 }).catch(() => false);
          if (tabHasSuccessSurface) {
            continue;
          }

          // Verify no hard error state in the active tab. Angular Material keeps
          // inactive tab bodies in the DOM, so a page-wide text locator can
          // match stale hidden error text from a previous eager load.
          const activeTabPanel = page
            .locator('mat-tab-body.mat-mdc-tab-body-active, [role="tabpanel"]:not([aria-hidden="true"])')
            .last();
          const errorScope = await activeTabPanel.isVisible({ timeout: 1_000 }).catch(() => false)
            ? activeTabPanel
            : page.locator('body');
          const errorMsg = errorScope.getByText(/failed to load|error loading|500/i).first();
          if (await errorMsg.isVisible({ timeout: 3_000 }).catch(() => false)) {
            noteGap(`Reports/${tabLabel}`, `Error loading ${tabLabel} tab content`, page);
          }
        } else {
          noteGap('Reports', `Tab "${tabLabel}" not found in the reports tab group`, page);
        }
      }
    });

    // ── 14. Accounting / Journals — list + post manual journal ───────────
    await test.step('14. Accounting / Journals — list renders + post manual adjustment', async () => {
      await page.goto(`${WEB}/app/accounting/journals`, { waitUntil: 'domcontentloaded' });

      await navReady(page);
      await settled(page);

      // Heading: "Journal Entries"
      const jrnHeading = page.getByRole('heading', { name: /journal entries/i });
      await expect(jrnHeading).toBeVisible({ timeout: 15_000 });
      await shot(page, '38-journals-list');

      // Post new manual journal button
      const postBtn = page.getByLabel('Post new manual journal entry')
        .or(page.getByRole('button', { name: /post.*journal|new.*journal|manual.*journal/i }))
        .first();

      if (await postBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await postBtn.click();

        // Journal form slide-in
        const formPanel = page.locator('[aria-labelledby="journal-form-title"]');
        await expect(formPanel).toBeVisible({ timeout: 10_000 });
        await shot(page, '39-journal-form-empty');

        // Fill description and date
        const descInput = page.locator('[formcontrolname="description"]');
        await descInput.fill(`Demo v2 adjustment — Brightwater kickoff expense ${RUN_ID}`);

        const today = new Date().toISOString().split('T')[0];
        const dateInput = page.locator('[formcontrolname="entry_date"]');
        if (await dateInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
          await dateInput.fill(today);
        }

        // Add a balanced debit + credit pair using the account picker.
        // Line 1 — Debit: Expenses (5000), $500
        // Line 2 — Credit: Bank (1100), $500
        const selectAccountLine = async (line: number, code: string) => {
          const input = formPanel.getByLabel(`Account for line ${line}`);
          await input.fill(code);
          const listbox = page.getByRole('listbox', { name: `Account suggestions for line ${line}` });
          await expect(listbox).toBeVisible({ timeout: 10_000 });
          await listbox.getByRole('option', { name: new RegExp(`^${code}`) }).click();
          await expect(input).toHaveValue(new RegExp(`^${code}\\s+—`));
        };

        await selectAccountLine(1, '5000');
        await formPanel.getByLabel('Direction for line 1').selectOption('DR');
        await formPanel.getByLabel('Amount for line 1').fill('500');

        await selectAccountLine(2, '1100');
        await formPanel.getByLabel('Direction for line 2').selectOption('CR');
        await formPanel.getByLabel('Amount for line 2').fill('500');

        await shot(page, '40-journal-form-filled');

        // Submit — button enabled only when balanced
        const submitBtn = page.getByRole('button', { name: /post journal|submit|save/i }).last();
        if (await submitBtn.isEnabled({ timeout: 5_000 }).catch(() => false)) {
          await submitBtn.click();
          // Form closes on success
          await expect(formPanel).toBeHidden({ timeout: 15_000 });
          await shot(page, '41-journal-posted');
        } else {
          noteGap('Journals/create', 'Post journal button not enabled — journal lines may not be balanced or account codes invalid', page);
          await shot(page, '41-journal-not-posted');
        }
      } else {
        noteGap('Journals', 'No "Post new manual journal entry" button found', page);
        await shot(page, '38b-no-journal-post-btn');
      }
    });

    // ── Final summary ─────────────────────────────────────────────────────
    await test.step('Final — back to Copilot + gap summary', async () => {
      await page.goto(`${WEB}/app/copilot`, { waitUntil: 'domcontentloaded' });
      await navReady(page);
      await shot(page, '42-final-copilot');

      // Print gap summary to test output
      if (gaps.length > 0) {
        const summary = gaps
          .map((g, i) => `  ${i + 1}. [${g.screen}] ${g.finding}`)
          .join('\n');
        test.info().annotations.push({
          type: 'gap-summary',
          description: `\n${gaps.length} UX gap(s) found:\n${summary}`,
        });
        console.log(`\n=== Demo v2 UX Gap Report (${gaps.length} findings) ===\n${summary}\n`);
      } else {
        console.log('\n=== Demo v2 UX Gap Report: No gaps found ===\n');
      }
    });
  });
});
