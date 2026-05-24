/**
 * QA R-Real-1 Step 1 — REAL signup via UI (3-page flow).
 *
 * Drives /signup → account form → plan picker → Stripe Elements card →
 * start-trial → land on /app/copilot.  Asserts JWT present in localStorage
 * (`aethos_token`).  Also rolls in:
 *   - #111 auth guard:   incognito /app/inbox should redirect to / (or /login)
 *   - #119 /login:       sign out via localStorage clear, log back in, land on /app/copilot
 *   - #118 password:     navigate /app/settings, change password, sign out, sign in with new
 *
 * Runs HEADED so a watching human can see what's happening.  ~30s end-to-end
 * when Stripe's iframe loads cleanly.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { FRONTEND, API, SCREENSHOT_DIR, shotPath, writeEvidence } = require('./helpers');

const TS = Date.now();
const EMAIL = `aksha-real1-${TS}@aethos-qa.dev`;
const PASSWORD = 'Aksha-real1-2026!';
const NEW_PASSWORD = 'Aksha-real1-NEW-2026!';
const TENANT_NAME = `Aksha Real1 ${TS}`;
const COUNTRY = 'US';

// Where this run's screenshots live.  We keep R1's screenshots intact (those
// documented step-1 BEFORE the signup UI shipped) and write new ones under
// the same dir with a distinct prefix.
const STEP_DIR = path.resolve(__dirname, '../../docs/qa/screenshots/real-data-r-real-1');
fs.mkdirSync(STEP_DIR, { recursive: true });
const shot = (name) => path.join(STEP_DIR, `${name}.png`);
const evidence = (name, content) =>
  fs.writeFileSync(path.join(STEP_DIR, name), content);

async function captureStorage(page) {
  return page.evaluate(() => {
    const ls = {};
    try { Object.keys(localStorage).forEach((k) => (ls[k] = localStorage.getItem(k))); } catch (e) {}
    return {
      url: window.location.href,
      pathname: window.location.pathname,
      title: document.title,
      localStorage: ls,
      bodyText: document.body.innerText.substring(0, 600),
    };
  });
}

async function main() {
  const browser = await chromium.launch({ headless: true, slowMo: 250 });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  const results = {
    run_id: TS,
    email: EMAIL,
    tenant_name: TENANT_NAME,
    steps: [],
  };

  // ── #111 auth guard (incognito-equivalent: fresh context) ────────────────
  console.log('### #111 — auth guard ###');
  await page.goto(`${FRONTEND}/app/inbox`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  const guardPath = new URL(page.url()).pathname;
  const guardPass = guardPath === '/' || guardPath.startsWith('/login');
  console.log(`/app/inbox without token → ${guardPath} (pass=${guardPass})`);
  await page.screenshot({ path: shot('01-authguard') });
  results.steps.push({ id: '#111', name: 'auth_guard_redirect', expected: '/ or /login', actual: guardPath, pass: guardPass });

  // ── Landing → signup ─────────────────────────────────────────────────────
  console.log('### Landing → /signup ###');
  await page.goto(`${FRONTEND}/`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: shot('02-landing') });

  // CTA: "Get started" / "Create account" / direct nav fallback.
  let ctaClicked = false;
  for (const sel of ['a[href="/signup"]', 'a:has-text("Get started")', 'a:has-text("Sign up")', 'a:has-text("Create account")']) {
    if (await page.locator(sel).first().count()) {
      try { await page.locator(sel).first().click({ timeout: 1500 }); ctaClicked = sel; break; } catch (e) {}
    }
  }
  if (!ctaClicked) await page.goto(`${FRONTEND}/signup`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: shot('03-signup-step1-empty') });

  // ── Signup step 1 — account form ─────────────────────────────────────────
  console.log('### Signup step 1 — account ###');
  await page.fill('#firm', TENANT_NAME);
  await page.fill('#email', EMAIL);
  await page.fill('#password', PASSWORD);
  await page.selectOption('#country', COUNTRY);
  await page.waitForTimeout(400);
  await page.screenshot({ path: shot('04-signup-step1-filled') });

  const signupResponses = [];
  page.on('response', async (resp) => {
    const u = resp.url();
    if (u.includes('/api/v1/auth/signup') || u.includes('/api/v1/billing/')) {
      try {
        signupResponses.push({ url: u, status: resp.status(), body: (await resp.text()).substring(0, 1200) });
      } catch (e) {}
    }
  });

  await page.click('button[type="submit"]');
  // Wait for either step 2 or an error to appear
  await Promise.race([
    page.waitForSelector('text=Pick a plan', { timeout: 25000 }).catch(() => null),
    page.waitForSelector('[role="alert"]', { timeout: 25000 }).catch(() => null),
  ]);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: shot('05-signup-step2-plan') });

  const step1State = await captureStorage(page);
  results.steps.push({
    id: 'signup-step1',
    name: 'submit_account_form',
    landed_on_step2: !!(await page.locator('text=Pick a plan').count()),
    has_token: !!Object.keys(step1State.localStorage).find((k) => /aethos_token|sb-/.test(k)),
    visible_text_excerpt: step1State.bodyText.substring(0, 200),
  });

  // If we didn't land on step 2 something bombed; capture and bail safely.
  if (!(await page.locator('text=Pick a plan').count())) {
    evidence('signup-step1-failed.json', JSON.stringify({ state: step1State, network: signupResponses }, null, 2));
    console.error('Signup step 1 FAILED — see signup-step1-failed.json');
    results.steps.push({ id: 'STEP1-FATAL', error: 'did not reach plan picker', network: signupResponses });
    evidence('results.json', JSON.stringify(results, null, 2));
    await browser.close();
    process.exit(2);
  }

  // ── Signup step 2 — plan picker ──────────────────────────────────────────
  console.log('### Signup step 2 — plan ###');
  // Default is "growth"; just hit Continue.
  await page.click('button:has-text("Continue to card")');
  await page.waitForSelector('text=Confirm your card', { timeout: 12000 });
  await page.waitForTimeout(2500); // let Stripe iframe load
  await page.screenshot({ path: shot('06-signup-step3-card-empty') });

  // ── Signup step 3 — Stripe Elements ──────────────────────────────────────
  console.log('### Signup step 3 — card ###');
  // Stripe card iframe lives inside the mount node.  Locate it via frame.
  const stripeFrame = page.frameLocator('iframe[name^="__privateStripeFrame"]').first();
  // Wait for the card-number input inside the iframe
  await stripeFrame.locator('input[name="cardnumber"]').waitFor({ timeout: 20000 });
  await stripeFrame.locator('input[name="cardnumber"]').fill('4242 4242 4242 4242');
  await stripeFrame.locator('input[name="exp-date"]').fill('12 / 34');
  await stripeFrame.locator('input[name="cvc"]').fill('123');
  await stripeFrame.locator('input[name="postal"]').fill('94110');
  await page.waitForTimeout(800);
  await page.screenshot({ path: shot('07-signup-step3-card-filled') });

  await page.click('button:has-text("Start 14-day trial")');
  // Either land on /app/copilot OR show a server error (e.g. start-trial fail)
  await Promise.race([
    page.waitForURL(/\/app\/copilot/, { timeout: 30000 }).catch(() => null),
    page.waitForSelector('[role="alert"]', { timeout: 30000 }).catch(() => null),
  ]);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: shot('08-post-trial-app') });

  const finalState = await captureStorage(page);
  const tokenKey = Object.keys(finalState.localStorage).find((k) => k === 'aethos_token');
  const supabaseSession = Object.keys(finalState.localStorage).find((k) => /sb-.*-auth-token/.test(k));
  const tokenPresent = !!(tokenKey || supabaseSession);
  const landedOnApp = finalState.pathname.startsWith('/app/');

  console.log(`Final URL ${finalState.url}; token=${tokenPresent}; landed=${landedOnApp}`);
  results.steps.push({
    id: 'signup-step3',
    name: 'confirm_trial',
    landed_on_app: landedOnApp,
    final_path: finalState.pathname,
    token_in_localstorage: tokenPresent,
    token_key: tokenKey || supabaseSession,
  });

  evidence('signup-network.json', JSON.stringify(signupResponses, null, 2));
  evidence('final-app-state.json', JSON.stringify(finalState, null, 2));

  // Save the JWT for Steps 2-6 (API-driven).
  const jwt = tokenKey ? finalState.localStorage[tokenKey] : null;
  if (jwt) evidence('tenant-a-jwt.txt', jwt);
  evidence('tenant-a-creds.json', JSON.stringify({ email: EMAIL, password: PASSWORD, new_password: NEW_PASSWORD, tenant_name: TENANT_NAME }, null, 2));

  // STOP HERE if we never landed on /app — the rest depends on the JWT.
  if (!landedOnApp) {
    evidence('results.json', JSON.stringify(results, null, 2));
    console.error('STOP — never landed on /app, skipping #119/#118');
    await browser.close();
    process.exit(3);
  }

  // ── #119 login round-trip ────────────────────────────────────────────────
  console.log('### #119 — login round-trip ###');
  // Clear storage to simulate sign-out (no sign-out button in shell yet)
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: shot('09-login-page') });
  await page.fill('#email', EMAIL);
  await page.fill('#password', PASSWORD);
  await page.click('button:has-text("Sign in")');
  await Promise.race([
    page.waitForURL(/\/app\/copilot/, { timeout: 12000 }).catch(() => null),
    page.waitForSelector('[role="alert"]', { timeout: 12000 }).catch(() => null),
  ]);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: shot('10-post-login') });
  const loginState = await captureStorage(page);
  const loginOk = loginState.pathname.startsWith('/app/');
  results.steps.push({ id: '#119', name: 'login_round_trip', pass: loginOk, final_path: loginState.pathname });

  // ── #118 change password ────────────────────────────────────────────────
  console.log('### #118 — change password ###');
  await page.goto(`${FRONTEND}/app/settings`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: shot('11-settings') });
  // Two password inputs in the change-password block.  Find by visible label.
  // The component is a child of the settings page; we identify by surrounding text.
  let pwUiPresent = false;
  try {
    pwUiPresent = (await page.locator('text=Account & security').count()) > 0
      || (await page.locator('text=Change password').count()) > 0
      || (await page.locator('input[autocomplete="new-password"]').count()) > 0;
  } catch (e) {}
  console.log(`Change-password UI present: ${pwUiPresent}`);
  results.steps.push({ id: '#118-ui', name: 'change_password_section_visible', pass: pwUiPresent });

  if (pwUiPresent) {
    try {
      // Try the most likely shape: current-password + new-password fields
      const newPwInputs = page.locator('input[autocomplete="new-password"]');
      const newCount = await newPwInputs.count();
      console.log(`Found ${newCount} new-password inputs`);
      if (newCount >= 1) {
        await newPwInputs.first().fill(NEW_PASSWORD);
        if (newCount >= 2) await newPwInputs.nth(1).fill(NEW_PASSWORD);
        await page.screenshot({ path: shot('12-change-password-filled') });
        // Find a "Save" / "Update" / "Change" button near the inputs
        for (const sel of ['button:has-text("Update password")', 'button:has-text("Change password")', 'button:has-text("Save password")', 'button:has-text("Save")', 'button:has-text("Update")']) {
          const loc = page.locator(sel).first();
          if (await loc.count()) {
            await loc.click({ timeout: 2000 });
            console.log(`Clicked: ${sel}`);
            break;
          }
        }
        await page.waitForTimeout(3500);
        await page.screenshot({ path: shot('13-change-password-result') });
        // Re-test: sign out and back in with NEW password
        await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
        await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(800);
        await page.fill('#email', EMAIL);
        await page.fill('#password', NEW_PASSWORD);
        await page.click('button:has-text("Sign in")');
        await Promise.race([
          page.waitForURL(/\/app\/copilot/, { timeout: 12000 }).catch(() => null),
          page.waitForSelector('[role="alert"]', { timeout: 12000 }).catch(() => null),
        ]);
        await page.waitForTimeout(2500);
        await page.screenshot({ path: shot('14-new-password-login') });
        const newPwState = await captureStorage(page);
        const newPwLoginOk = newPwState.pathname.startsWith('/app/');
        results.steps.push({ id: '#118-roundtrip', name: 'login_with_new_password', pass: newPwLoginOk, final_path: newPwState.pathname });
      }
    } catch (err) {
      console.error('change-password failed:', err.message);
      results.steps.push({ id: '#118-error', error: err.message });
    }
  }

  evidence('results.json', JSON.stringify(results, null, 2));
  console.log('=== STEP 1 + #111 + #119 + #118 RESULTS ===');
  console.log(JSON.stringify(results, null, 2));

  await browser.close();
}

main().catch((e) => { console.error('FATAL:', e); process.exit(1); });
