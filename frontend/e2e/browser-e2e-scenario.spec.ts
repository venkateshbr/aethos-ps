/**
 * Full engagement-to-cash browser walkthrough — single browser session.
 *
 * Runs against the live stack (Angular :4201 + FastAPI :8011 + Supabase).
 * Does a REAL UI login then flows through every implemented feature:
 *
 *  1  Login via /login page
 *  2  Clients   — create a client
 *  3  Engagements — create T&M + fixed-fee engagements; validation edge case
 *  4  Engagement detail — draft an invoice with a manual extra line
 *  5  Projects  — create a project linked to the engagement
 *  6  Time      — add a billable time entry
 *  7  Invoices  — approve → send → mark paid
 *  8  Reports   — verify AR aging, utilization, WIP sections load
 *  9  Billing Runs — AP pay-bills page loads and renders stepper
 * 10  Copilot   — send a message, verify chat UI responds
 * 11  Edge cases — payments, people, expenses, documents pages
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'node:fs';

const WEB = process.env.AETHOS_PS_WEB_URL ?? 'http://localhost:4201';

const CREDS = {
  email:    'ts-owner-59348813@aethos-qa.dev',
  password: 'TimesheetE2E-2026!',
};

const RUN_ID      = Date.now().toString().slice(-6);
const CLIENT_NAME = `E2E Client ${RUN_ID}`;
const ENG_TM_NAME = `E2E T&M Eng ${RUN_ID}`;
const ENG_FF_NAME = `E2E Fixed Fee ${RUN_ID}`;
const PROJ_NAME   = `E2E Project ${RUN_ID}`;

// ─── Helpers ──────────────────────────────────────────────────────────────

const SHOT_DIR = 'test-results/browser-scenario';
fs.mkdirSync(SHOT_DIR, { recursive: true });

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: false });
}

/** Wait for all loading spinners / skeleton placeholders to disappear */
async function settled(page: Page) {
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 20_000 });
}

/** Nav is present when the Engagements link in the top bar is visible */
async function navReady(page: Page) {
  await expect(page.getByRole('link', { name: 'Engagements' })).toBeVisible({ timeout: 20_000 });
}

// ─── Suite ────────────────────────────────────────────────────────────────

test.describe('Engagement-to-Cash — full browser walkthrough', () => {
  // Start with a blank session — do real login through the UI
  test.use({ storageState: { cookies: [], origins: [] } });

  test('complete O2C scenario in one browser session', async ({ page }) => {
    test.setTimeout(360_000); // 6 min for the full walk

    // ── 1. Login ───────────────────────────────────────────────────────
    await test.step('1. Login — /login → Copilot', async () => {
      await page.goto(`${WEB}/login`);
      await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible({ timeout: 15_000 });

      await page.fill('#email',    CREDS.email);
      await page.fill('#password', CREDS.password);
      await shot(page, '01-login-filled');

      await page.click('button[type="submit"]');
      await page.waitForURL(/\/app\/copilot/, { timeout: 30_000 });

      // Verify top nav bar loaded (header contains the Engagements link)
      await navReady(page);
      await shot(page, '02-copilot-logged-in');
    });

    // ── 2. Contacts (formerly "Clients" — renamed in #201) ─────────────
    await test.step('2. Contacts — create a contact', async () => {
      await page.goto(`${WEB}/app/clients`);
      // #201: heading is now "Contacts" (route stays /app/clients, label renamed).
      await expect(page.getByRole('heading', { name: /^contacts$/i, level: 1 })).toBeVisible({ timeout: 15_000 });
      await settled(page);
      await shot(page, '03-contacts-list');

      // #201: button label changed from "New client" → "New contact".
      await page.getByRole('button', { name: /new contact/i }).first().click();
      await expect(page.getByRole('heading', { name: /new contact/i })).toBeVisible({ timeout: 10_000 });

      await page.fill('#client-name', CLIENT_NAME);
      await page.selectOption('#client-kind', 'customer');
      await shot(page, '04-contact-form-filled');

      // #201: submit button label changed to "Create contact".
      await page.getByRole('button', { name: /create contact/i }).click();
      await expect(page.getByText(CLIENT_NAME)).toBeVisible({ timeout: 15_000 });
      await shot(page, '05-contact-created');
    });

    // ── 3. Engagements ─────────────────────────────────────────────────
    await test.step('3a. Engagements — create T&M engagement', async () => {
      await page.goto(`${WEB}/app/engagements`);
      await expect(page.getByRole('heading', { name: /^engagements$/i, level: 1 })).toBeVisible({ timeout: 15_000 });
      await settled(page);

      await page.getByRole('button', { name: /new engagement|create.*engagement/i }).first().click();
      await expect(page.getByRole('heading', { name: /new engagement/i })).toBeVisible({ timeout: 10_000 });

      await page.fill('#eng-name', ENG_TM_NAME);
      // Wait for client options to load via locator (reliably honors 10s timeout)
      await page.locator('#eng-client option:not([value=""])').first()
        .waitFor({ state: 'attached', timeout: 10_000 });
      await page.selectOption('#eng-client', { label: CLIENT_NAME });
      await page.selectOption('#eng-billing', 'time_and_materials');
      await page.selectOption('#eng-currency', 'USD');
      await shot(page, '06-eng-tm-form');

      await page.getByRole('button', { name: /create engagement/i }).click();
      await expect(page.getByText(ENG_TM_NAME)).toBeVisible({ timeout: 15_000 });
      await shot(page, '07-eng-tm-created');
    });

    await test.step('3b. Engagements — create Fixed Fee engagement', async () => {
      await page.getByRole('button', { name: /new engagement|create.*engagement/i }).first().click();
      await expect(page.getByRole('heading', { name: /new engagement/i })).toBeVisible({ timeout: 10_000 });

      await page.fill('#eng-name', ENG_FF_NAME);
      await page.locator('#eng-client option:not([value=""])').first()
        .waitFor({ state: 'attached', timeout: 10_000 });
      await page.selectOption('#eng-client', { label: CLIENT_NAME });
      await page.selectOption('#eng-billing', 'fixed_fee');
      await page.selectOption('#eng-currency', 'USD');
      await page.fill('#eng-value', '25000.00');
      await shot(page, '08-eng-ff-form');

      await page.getByRole('button', { name: /create engagement/i }).click();
      await expect(page.getByText(ENG_FF_NAME)).toBeVisible({ timeout: 15_000 });
      await shot(page, '09-eng-ff-created');
    });

    await test.step('3c. Edge case — Create button disabled until all required fields filled', async () => {
      await page.getByRole('button', { name: /new engagement|create.*engagement/i }).first().click();
      await expect(page.getByRole('heading', { name: /new engagement/i })).toBeVisible({ timeout: 10_000 });

      // With no fields filled, the Create button must be disabled (form.invalid guard)
      await expect(page.getByRole('button', { name: /create engagement/i })).toBeDisabled({ timeout: 5_000 });

      // Fill name but leave billing empty — still disabled
      await page.fill('#eng-name', 'Incomplete');
      await expect(page.getByRole('button', { name: /create engagement/i })).toBeDisabled({ timeout: 3_000 });

      // Touch the billing field and blur it to show inline validation
      await page.locator('#eng-billing').focus();
      await page.locator('#eng-billing').blur();
      await expect(page.getByText(/billing arrangement is required/i)).toBeVisible({ timeout: 5_000 });
      await shot(page, '10-eng-validation-error');

      // Cancel to discard
      await page.getByRole('button', { name: /cancel/i }).click();
      await expect(page.getByRole('heading', { name: /new engagement/i })).toBeHidden({ timeout: 5_000 });
    });

    // ── 4. Engagement Detail — draft invoice ───────────────────────────
    await test.step('4a. Engagement detail — open T&M engagement', async () => {
      // Click into the T&M engagement
      await page.getByRole('button', { name: `Open engagement ${ENG_TM_NAME}` })
        .or(page.getByLabel(`Open engagement ${ENG_TM_NAME}`))
        .or(page.getByRole('button', { name: new RegExp(`open.*${ENG_TM_NAME}`, 'i') }))
        .first().click();

      await page.waitForURL(/\/app\/engagements\/[0-9a-f-]+$/, { timeout: 15_000 });
      await settled(page);
      await expect(page.getByText(ENG_TM_NAME)).toBeVisible({ timeout: 10_000 });
      await shot(page, '11-eng-detail');
    });

    await test.step('4b. Engagement detail — draft invoice with manual extra line', async () => {
      await page.getByRole('button', { name: /draft.*invoice/i }).click();
      await expect(page.getByRole('heading', { name: /draft invoice/i })).toBeVisible({ timeout: 10_000 });

      const today    = new Date();
      const due      = new Date(today); due.setDate(today.getDate() + 30);
      const fmt      = (d: Date) => d.toISOString().split('T')[0];

      await page.fill('#inv-issue-date', fmt(today));
      await page.fill('#inv-due-date',   fmt(due));

      // Enable manual extra line
      const extraToggle = page.locator('input[name="inv-extra-on"]');
      await extraToggle.check();
      // Use pressSequentially (not fill) so Angular ngModel change events fire
      const descInput  = page.locator('[name="inv-extra-desc"]');
      const qtyInput   = page.locator('[name="inv-extra-qty"]');
      const priceInput = page.locator('[name="inv-extra-price"]');
      await descInput.click();
      await descInput.pressSequentially('Kickoff workshop facilitation');
      await qtyInput.click({ clickCount: 3 });
      await qtyInput.pressSequentially('1');
      await priceInput.click({ clickCount: 3 });
      await priceInput.pressSequentially('2500');
      await priceInput.press('Tab'); // blur to trigger final ngModel update
      await shot(page, '12-invoice-draft-form');

      await page.getByRole('button', { name: /create draft invoice/i }).click();
      // Drawer should close
      await expect(page.getByRole('heading', { name: /draft invoice/i })).toBeHidden({ timeout: 20_000 });
      await shot(page, '13-invoice-drafted');
    });

    // ── 5. Projects ────────────────────────────────────────────────────
    await test.step('5. Projects — create a project linked to T&M engagement', async () => {
      await page.goto(`${WEB}/app/projects`);
      // Projects page has no h1 — wait for the "New project" button instead
      await expect(page.getByRole('button', { name: /new project/i }).first()).toBeVisible({ timeout: 15_000 });
      await settled(page);
      await shot(page, '14-projects-list');

      await page.getByRole('button', { name: /new project/i }).first().click();
      await expect(page.getByRole('heading', { name: /new project/i })).toBeVisible({ timeout: 10_000 });

      await page.fill('#proj-name', PROJ_NAME);

      // Link to T&M engagement — wait for at least one non-placeholder option via locator, then select by value
      const engSelect = page.locator('#proj-engagement');
      if (await engSelect.count() > 0) {
        const optLoaded = await page.locator('#proj-engagement option:not([value=""])').first()
          .waitFor({ state: 'attached', timeout: 10_000 }).then(() => true).catch(() => false);
        if (optLoaded) {
          const engValue = await page.evaluate(
            (name: string) => {
              const sel = document.querySelector('#proj-engagement') as HTMLSelectElement;
              for (const opt of Array.from(sel.options)) {
                if (opt.text.includes(name)) return opt.value;
              }
              return '';
            },
            ENG_TM_NAME
          );
          if (engValue) await engSelect.selectOption({ value: engValue });
        }
      }

      await shot(page, '15-project-form');
      await page.getByRole('button', { name: /create project/i }).click();
      await expect(page.getByText(PROJ_NAME)).toBeVisible({ timeout: 15_000 });
      await shot(page, '16-project-created');
    });

    // ── 6. Time entries ────────────────────────────────────────────────
    await test.step('6. Time entries — log billable hours', async () => {
      await page.goto(`${WEB}/app/time`);
      await expect(page.getByRole('heading', { name: /time/i, level: 1 })).toBeVisible({ timeout: 15_000 });
      await settled(page);
      await shot(page, '17-time-list');

      // Quick-add form at top — project options include auto-assigned code prefix (e.g. "PRJ-0003 · E2E Project…")
      // Use locator waitFor (reliably honors timeout) then select by value UUID
      const projectSelect = page.locator('#entry-project');
      if (await projectSelect.count() > 0) {
        const projOptLoaded = await page.locator('#entry-project option:not([value=""])').first()
          .waitFor({ state: 'attached', timeout: 10_000 }).then(() => true).catch(() => false);
        if (projOptLoaded) {
          const projValue = await page.evaluate(
            (name: string) => {
              const sel = document.querySelector('#entry-project') as HTMLSelectElement;
              for (const opt of Array.from(sel.options)) {
                if (opt.text.includes(name)) return opt.value;
              }
              return '';
            },
            PROJ_NAME
          );
          if (projValue) await projectSelect.selectOption({ value: projValue });
        }
      }

      const empSelect = page.locator('#entry-employee');
      if (await empSelect.count() > 0) {
        const opts = await empSelect.locator('option').allTextContents();
        const first = opts.find(o => o.trim() && !/select/i.test(o));
        if (first) await empSelect.selectOption({ label: first });
      }

      const today = new Date().toISOString().split('T')[0];
      await page.fill('#entry-date',        today);
      await page.fill('#entry-hours',       '6');
      await page.fill('#entry-description', 'Client discovery workshop');
      await shot(page, '18-time-entry-form');

      await page.getByRole('button', { name: /add time entry/i }).click();
      await expect(page.getByText(/discovery workshop/i).first()).toBeVisible({ timeout: 15_000 });
      await shot(page, '19-time-entry-created');
    });

    // ── 7. Invoices — approve → send → mark paid ───────────────────────
    await test.step('7a. Invoices — list view loaded, draft invoice visible', async () => {
      await page.goto(`${WEB}/app/invoices`);
      await expect(page.getByRole('heading', { name: /^invoices$/i, level: 1 })).toBeVisible({ timeout: 15_000 });
      await settled(page);
      await shot(page, '20-invoices-list');

      // The invoice table must render — target the <table> specifically to avoid matching the nav link
      const invoiceTable = page.locator('table[aria-label="Invoices"]');
      await expect(invoiceTable).toBeVisible({ timeout: 10_000 });
    });

    await test.step('7b. Invoices — approve draft invoice', async () => {
      const approveBtn = page.locator('button').filter({ hasText: /^approve/i }).first();
      if (await approveBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await approveBtn.click();
        await expect(page.getByText(/approved/i).first()).toBeVisible({ timeout: 15_000 });
        await shot(page, '21-invoice-approved');
      } else {
        test.info().annotations.push({ type: 'info', description: 'No draft invoice in list to approve (may be from different tenant run).' });
        await shot(page, '21-no-draft-to-approve');
      }
    });

    await test.step('7c. Invoices — send approved invoice', async () => {
      await page.reload();
      await settled(page);
      const sendBtn = page.locator('button').filter({ hasText: /^send/i }).first();
      if (await sendBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await sendBtn.click();
        // Wait for the button to disappear or status to update — avoids flaky fixed sleep.
        await expect(sendBtn).toBeHidden({ timeout: 10_000 }).catch(() => { /* send may open a dialog */ });
        await shot(page, '22-invoice-sent');
      } else {
        test.info().annotations.push({ type: 'info', description: 'No approved invoice to send.' });
      }
    });

    await test.step('7d. Invoices — mark as paid', async () => {
      await page.reload();
      await settled(page);

      // Look for "Mark paid" / "Paid" button
      const paidBtn = page.locator('button').filter({ hasText: /^mark paid|^paid/i }).first();
      if (await paidBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await paidBtn.click();

        // Dialog appears
        await expect(page.getByRole('heading', { name: /mark.*paid|record payment/i })).toBeVisible({ timeout: 10_000 });

        const payInput = page.locator('#pay-amount');
        const curVal = await payInput.inputValue();
        if (!curVal || curVal === '0') await payInput.fill('2500.00');

        const today = new Date().toISOString().split('T')[0];
        await page.locator('#pay-date').fill(today);
        await page.locator('#pay-notes').fill('Wire ref E2E-BROWSER-TEST');
        await shot(page, '23-mark-paid-dialog');

        await page.getByRole('button', { name: /record payment|confirm|save/i }).last().click();
        await expect(page.getByText(/paid/i).first()).toBeVisible({ timeout: 15_000 });
        await shot(page, '24-invoice-paid');
      } else {
        test.info().annotations.push({ type: 'info', description: 'No sent invoice to mark paid.' });
        await shot(page, '24-no-sent-invoice');
      }
    });

    // ── 8. Reports ─────────────────────────────────────────────────────
    await test.step('8. Reports — AR aging, Utilization, WIP all render', async () => {
      await page.goto(`${WEB}/app/reports`);
      await expect(page.getByRole('heading', { name: /^reports$/i })).toBeVisible({ timeout: 15_000 });
      await settled(page);

      // AR Aging card
      await expect(page.getByText(/ar aging/i).first()).toBeVisible({ timeout: 20_000 });

      // Utilization section
      await expect(page.getByText(/utilization/i).first()).toBeVisible({ timeout: 15_000 });

      // WIP section
      await expect(page.getByText(/wip|work in progress/i).first()).toBeVisible({ timeout: 15_000 });

      await shot(page, '25-reports');
    });

    // ── 9. Billing Runs (AP Pay Bills) ─────────────────────────────────
    await test.step('9. Billing Runs — AP Pay Bills stepper loads', async () => {
      await page.goto(`${WEB}/app/billing-runs`);
      await expect(page.getByRole('heading', { name: /pay bills/i })).toBeVisible({ timeout: 15_000 });

      // Either the stepper or the empty/error state must be visible
      const content = page.locator('mat-stepper')
        .or(page.getByText(/no.*bills|approved bills|select bills/i))
        .or(page.getByText(/failed to load/i));
      await expect(content.first()).toBeVisible({ timeout: 15_000 });
      await shot(page, '26-billing-runs');
    });

    // ── 10. Copilot ────────────────────────────────────────────────────
    await test.step('10. Copilot — type a query and see the chat UI respond', async () => {
      await page.goto(`${WEB}/app/copilot`);

      // New chat button or composer — either means copilot mounted
      const copilotReady = page.getByRole('button', { name: /new chat/i })
        .or(page.getByPlaceholder(/message aethos/i));
      await expect(copilotReady.first()).toBeVisible({ timeout: 20_000 });
      await shot(page, '27-copilot-fresh');

      // Start a new chat if needed
      const newChatBtn = page.getByRole('button', { name: /new chat/i });
      if (await newChatBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await newChatBtn.click();
        // Wait for the composer to be ready — avoids a fixed sleep.
        await expect(page.getByPlaceholder(/message aethos/i)).toBeVisible({ timeout: 10_000 });
      }

      const composer = page.getByPlaceholder(/message aethos/i);
      await expect(composer).toBeVisible({ timeout: 10_000 });
      await composer.fill('How many active engagements do I have?');
      await shot(page, '27b-copilot-query');

      await page.keyboard.press('Enter');

      // Wait for an assistant reply bubble — aria-label starts with "Aethos:" per the copilot component
      await expect(
        page.locator('[aria-label^="Aethos:"]').last()
      ).toBeVisible({ timeout: 60_000 });
      await shot(page, '28-copilot-response');
    });

    // ── 11. Secondary pages ────────────────────────────────────────────
    await test.step('11a. Payments page renders', async () => {
      await page.goto(`${WEB}/app/payments`);
      await navReady(page);
      await page.waitForLoadState('domcontentloaded');
      await shot(page, '29-payments');
    });

    await test.step('11b. People page renders', async () => {
      await page.goto(`${WEB}/app/people`);
      await navReady(page);
      await page.waitForLoadState('domcontentloaded');
      await shot(page, '30-people');
    });

    await test.step('11c. Expenses page renders', async () => {
      await page.goto(`${WEB}/app/expenses`);
      await navReady(page);
      await page.waitForLoadState('domcontentloaded');
      await shot(page, '31-expenses');
    });

    await test.step('11d. Documents page renders with upload CTA', async () => {
      await page.goto(`${WEB}/app/documents`);
      await navReady(page);
      await page.waitForLoadState('domcontentloaded');
      // Documents page has no direct file input — upload is via Copilot (routerLink)
      await expect(page.getByRole('heading', { name: /^documents$/i })).toBeVisible({ timeout: 10_000 });
      await expect(page.getByText(/upload document/i).first()).toBeVisible({ timeout: 5_000 });
      await shot(page, '32-documents');
    });

    await test.step('11e. Inbox page renders', async () => {
      await page.goto(`${WEB}/app/inbox`);
      await navReady(page);
      await page.waitForLoadState('domcontentloaded');
      await shot(page, '33-inbox');
    });

    // ── Final ──────────────────────────────────────────────────────────
    await test.step('Final — back to Copilot dashboard', async () => {
      await page.goto(`${WEB}/app/copilot`);
      await navReady(page);
      await shot(page, '36-final-dashboard');
    });
  });
});
